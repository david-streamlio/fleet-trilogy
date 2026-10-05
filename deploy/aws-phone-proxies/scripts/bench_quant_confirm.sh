#!/usr/bin/env bash
# Confirmation run for TODO-Q4_0-ACCURACY-CHECK.md, ON a Mac proxy: the Edge Triage Pipeline
# eval at --model-eval-runs 45 (135 escalation calls per run, 3x test C's) on several 4-bit
# formats of the same model, under powermetrics like bench_workload.sh.
# - Gemma-3-4B: Q4_K_M, Q4_0, IQ4_XS, IQ4_NL. Its escalation mismatch rose from 0% to ~30%
#   with Q4_0 on both M1 and M4; are the other formats affected?
# - Llama-3.1-8B: Q4_K_M, Q4_0 (11 -> 16/135 on M4: noise or a shift?).
# Each variant runs 2 reps. Files not already on the host are downloaded first (repos as in
# MODELS.lock.tsv). The models.toml ids stay the same; LLM_MODEL_PATH_* points at the variant.
#
#   bench_quant_confirm.sh <base> <repo>
set -uo pipefail

BASE="$1"
REPO="$2"
BIN="$BASE/llama.cpp/build/bin/llama-completion"
RUNS=45
REPS=2
OUT="$BASE/results/Q-confirm-$(date -u +%Y%m%dT%H%M%SZ)-n$RUNS"
mkdir -p "$OUT" "$BASE/models-quant"
exec > >(tee -a "$OUT/bench.log") 2>&1
echo "quant confirmation run $(basename "$OUT"): --model-eval-runs $RUNS, $REPS reps per variant"
{ echo "llama.cpp commit: $(cat "$BASE/llama_cpp_commit.txt")"; uname -a; sysctl -n machdep.cpu.brand_string; } > "$OUT/system.txt"

# <models.toml id> <env suffix> <label> <repo> <file> <dir under $BASE>
VARIANTS="gemma-3-4b-it-q4km GEMMA3_4B Q4_K_M unsloth/gemma-3-4b-it-GGUF gemma-3-4b-it-Q4_K_M.gguf models
gemma-3-4b-it-q4km GEMMA3_4B Q4_0 unsloth/gemma-3-4b-it-GGUF gemma-3-4b-it-Q4_0.gguf models-quant
gemma-3-4b-it-q4km GEMMA3_4B IQ4_XS unsloth/gemma-3-4b-it-GGUF gemma-3-4b-it-IQ4_XS.gguf models-quant
gemma-3-4b-it-q4km GEMMA3_4B IQ4_NL unsloth/gemma-3-4b-it-GGUF gemma-3-4b-it-IQ4_NL.gguf models-quant
llama-3.1-8b-instruct-q4km LLAMA31_8B Q4_K_M unsloth/Llama-3.1-8B-Instruct-GGUF Llama-3.1-8B-Instruct-Q4_K_M.gguf models
llama-3.1-8b-instruct-q4km LLAMA31_8B Q4_0 unsloth/Llama-3.1-8B-Instruct-GGUF Llama-3.1-8B-Instruct-Q4_0.gguf models-quant"

echo "$VARIANTS" | while read -r _id _var _label repo file dir; do  # downloads, before any window
  [ -f "$BASE/$dir/$file" ] && continue
  curl -fL --retry 5 --retry-delay 5 -sS -o "$BASE/$dir/$file.part" "https://huggingface.co/$repo/resolve/main/$file" \
    && mv "$BASE/$dir/$file.part" "$BASE/$dir/$file"
done
echo "$VARIANTS" | while read -r _id var label _repo file dir; do echo "$label $var $BASE/$dir/$file"; done >> "$OUT/system.txt"

now() { python3 -c 'import time; print(f"{time.time():.3f}")'; }
window() {
  local label="$1"; shift
  local t0; t0=$(now)
  "$@"
  local rc=$?
  echo "$label start=$t0 end=$(now) exit=$rc" >> "$OUT/windows.log"
  return $rc
}

cd "$REPO" || exit 1
sudo powermetrics --samplers cpu_power,gpu_power,thermal -i 500 -o "$OUT/powermetrics.txt" &
PM_PID=$!
sleep 5
window idle-pre sleep 30
echo "$VARIANTS" | while read -r id var label _repo file dir; do
  for r in $(seq 1 "$REPS"); do
    lab="edge_triage_${id}_${label}_r$r"
    echo "== $lab"
    before=$(ls -1 eval-results/ | sort)
    # --model-backend server: what the published runs used; the harness default is in-process since 2026-10-05.
    window "$lab" env "LLM_BINARY_PATH_$var=$BIN" "LLM_MODEL_PATH_$var=$BASE/$dir/$file" \
      /opt/homebrew/bin/uv run --no-sync pytest tests/model/test_compare_edge_triage_models.py -m model -s -q \
      --only-model-ids "$id" --model-eval-runs "$RUNS" --model-threads 4 --model-backend server < /dev/null > "$OUT/pytest_$lab.log" 2>&1
    tail -n 2 "$OUT/pytest_$lab.log"
    echo "$lab $(comm -13 <(echo "$before") <(ls -1 eval-results/ | sort) | tr '\n' ' ')" >> "$OUT/artifacts.txt"
    window "idle-gap_$lab" sleep 20
  done
done
window idle-post sleep 30
sudo pkill -INT -P "$PM_PID" -x powermetrics  # see bench.sh: sudo won't relay our signal
wait "$PM_PID" 2>/dev/null
echo "done $(basename "$OUT")"
