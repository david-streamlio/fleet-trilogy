#!/usr/bin/env bash
# Catalog test C, run ON a Mac proxy: Talk 2's real workload (the Edge Triage Pipeline and
# Tier 2 comparison evals from tests/model/) under powermetrics. It's the same model/task
# pairs and flags as the M4 Max contrast in impact-track row 24 (--model-eval-runs 15 for
# the Edge Triage Pipeline = 60 calls, 30 for Tier 2), plus the other three external-fan
# Edge Triage candidates (row 25), 3 repetitions each.
#
# Runs in a pause of bench_extras.sh: it touches $BASE/PAUSE, waits until the queue is
# idle between tests (no powermetrics, no bench.sh), runs, then removes PAUSE so the
# queue resumes. The eval artifacts land in <repo>/eval-results/ as usual; this run's
# results/C-workload-<ts>/ holds powermetrics.txt, windows.log and artifacts.txt (which
# artifact each window wrote).
#
#   [ORDER=reverse] [QUANT=q4_0] bench_workload.sh <base> <repo> [--quick]
#   (--quick: Phi only, 1 eval run, 1 rep)
#
# ORDER=reverse runs the pairs last-to-first (an order-effect check; mac2 doesn't throttle).
# QUANT=q4_0 points the five candidates at their Q4_0 files in models-quant/, downloaded first
# if missing (TODO-Q4_0-ACCURACY-CHECK.md: accuracy, latency and energy of Q4_0 vs Q4_K_M).
set -uo pipefail

BASE="$1"
REPO="$2"
QUICK="${3:-}"
BIN="$BASE/llama.cpp/build/bin/llama-completion"  # Metal; the harness finds llama-server beside it
REPS=3
[ "$QUICK" = "--quick" ] && REPS=1

# The Q4_0 files (repos as in MODELS.lock.tsv), fetched before any measurement window.
Q4_0="PHI35_MINI bartowski/Phi-3.5-mini-instruct-GGUF Phi-3.5-mini-instruct-Q4_0.gguf
GEMMA3_4B unsloth/gemma-3-4b-it-GGUF gemma-3-4b-it-Q4_0.gguf
LLAMA31_8B unsloth/Llama-3.1-8B-Instruct-GGUF Llama-3.1-8B-Instruct-Q4_0.gguf
GLM4_9B unsloth/GLM-4-9B-0414-GGUF GLM-4-9B-0414-Q4_0.gguf
QWEN3_8B bartowski/Qwen_Qwen3-8B-GGUF Qwen_Qwen3-8B-Q4_0.gguf"
if [ "${QUANT:-}" = q4_0 ]; then
  mkdir -p "$BASE/models-quant"
  echo "$Q4_0" | while read -r _var repo file; do
    [ -f "$BASE/models-quant/$file" ] && continue
    curl -fL --retry 5 --retry-delay 5 -sS -o "$BASE/models-quant/$file.part" "https://huggingface.co/$repo/resolve/main/$file" \
      && mv "$BASE/models-quant/$file.part" "$BASE/models-quant/$file"
  done
fi

touch "$BASE/PAUSE"
until ! pgrep -x powermetrics >/dev/null && ! pgrep -f "$BASE/[b]ench.sh" >/dev/null; do sleep 15; done

OUT="$BASE/results/C-workload-$(date -u +%Y%m%dT%H%M%SZ)${QUICK:+-quick}${QUANT:+-$QUANT}${ORDER:+-$ORDER}"
mkdir -p "$OUT"
exec > >(tee -a "$OUT/bench.log") 2>&1
echo "C workload run $(basename "$OUT"), reps=$REPS"
{ echo "llama.cpp commit: $(cat "$BASE/llama_cpp_commit.txt")"; uname -a; sysctl -n machdep.cpu.brand_string; } > "$OUT/system.txt"

now() { python3 -c 'import time; print(f"{time.time():.3f}")'; }
window() {
  local label="$1"; shift
  local t0; t0=$(now)
  "$@"
  local rc=$?
  echo "$label start=$t0 end=$(now) exit=$rc" >> "$OUT/windows.log"
  return $rc
}

# models.toml reads each model's binary and weights from these variables.
export LLM_BINARY_PATH_PHI35_MINI="$BIN" LLM_MODEL_PATH_PHI35_MINI="$BASE/models/Phi-3.5-mini-instruct-Q4_K_M.gguf"
export LLM_BINARY_PATH_GEMMA3_4B="$BIN" LLM_MODEL_PATH_GEMMA3_4B="$BASE/models/gemma-3-4b-it-Q4_K_M.gguf"
export LLM_BINARY_PATH_LLAMA31_8B="$BIN" LLM_MODEL_PATH_LLAMA31_8B="$BASE/models/Llama-3.1-8B-Instruct-Q4_K_M.gguf"
export LLM_BINARY_PATH_GLM4_9B="$BIN" LLM_MODEL_PATH_GLM4_9B="$BASE/models/GLM-4-9B-0414-Q4_K_M.gguf"
export LLM_BINARY_PATH_QWEN3_8B="$BIN" LLM_MODEL_PATH_QWEN3_8B="$BASE/models/qwen3-8b-q4_k_m.gguf"

# <pytest file> <models.toml id> <--model-eval-runs>
PAIRS="test_compare_edge_triage_models.py phi-3.5-mini-instruct-q4km 15
test_compare_tier2_models.py gemma-3-4b-it-q4km 30
test_compare_edge_triage_models.py gemma-3-4b-it-q4km 15
test_compare_edge_triage_models.py llama-3.1-8b-instruct-q4km 15
test_compare_edge_triage_models.py glm-4-9b-0414-q4km 15
test_compare_edge_triage_models.py qwen3-8b-q4km 15"
[ "$QUICK" = "--quick" ] && PAIRS="test_compare_edge_triage_models.py phi-3.5-mini-instruct-q4km 1"
[ "${ORDER:-}" = reverse ] && PAIRS=$(echo "$PAIRS" | awk '{ l[NR] = $0 } END { for (i = NR; i > 0; i--) print l[i] }')
if [ "${QUANT:-}" = q4_0 ]; then  # same models.toml ids, Q4_0 weights
  while read -r var _repo file; do export "LLM_MODEL_PATH_$var=$BASE/models-quant/$file"; done <<< "$Q4_0"
fi
{ echo "order: ${ORDER:-forward}"; echo "quant: ${QUANT:-q4_k_m}"; env | grep '^LLM_MODEL_PATH_'; } >> "$OUT/system.txt"

cd "$REPO"
sudo powermetrics --samplers cpu_power,gpu_power -i 500 -o "$OUT/powermetrics.txt" &
PM_PID=$!
sleep 5
window idle-pre sleep 30
echo "$PAIRS" | while read -r test id runs; do
  task=$(echo "$test" | sed -E 's/test_compare_(.*)_models\.py/\1/')
  for r in $(seq 1 "$REPS"); do
    echo "== $task $id rep $r"
    before=$(ls -1 eval-results/ 2>/dev/null | sort)
    # --model-backend server --tier2-prompt published: what the published runs used (harness defaults since 2026-10-05: in-process, the current Tier 2 prompt).
    window "${task}_${id}_r$r" /opt/homebrew/bin/uv run --no-sync pytest "tests/model/$test" -m model -s -q \
      --only-model-ids "$id" --model-eval-runs "$runs" --model-threads 4 --model-backend server --tier2-prompt published < /dev/null > "$OUT/pytest_${task}_${id}_r$r.log" 2>&1
    tail -n 3 "$OUT/pytest_${task}_${id}_r$r.log"
    new=$(comm -13 <(echo "$before") <(ls -1 eval-results/ | sort) | tr '\n' ' ')
    echo "${task}_${id}_r$r $new" >> "$OUT/artifacts.txt"
    window "idle-gap_${task}_${id}_r$r" sleep 20
  done
done
window idle-post sleep 30
sudo pkill -INT -P "$PM_PID" -x powermetrics  # see bench.sh: sudo won't relay our signal
wait "$PM_PID" 2>/dev/null
echo "done $(basename "$OUT")"
# A quick run is the smoke test before the full one: stay paused for it.
[ "$QUICK" = "--quick" ] || rm -f "$BASE/PAUSE"
