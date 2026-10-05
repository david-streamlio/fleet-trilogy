#!/usr/bin/env bash
# Round 3 follow-up, run ON a Mac proxy: thinking with budget forcing (round3_eval.py mode
# chat-budget: reason up to BUDGET tokens, </think> appended if the budget runs out, then the card
# under the grammar) for the Qwen models, both tasks. Added 2026-10-04 after Qwen3.5-9B's
# unbudgeted chat-on reasoning ran past 2,048 tokens without closing </think>. Same machinery
# and artifact mapping as bench_round3.sh.
# Qwen3.5-9B is downloaded first if missing; the 12-14B models come from test I's
# models-phase2/. Artifacts: <repo>/eval-results/compare-round3-*.json, mapped per window in
# results/round3-<ts>/artifacts.txt.
#
#   bench_budget.sh <base> <repo> [n-per-cell] [budget]
set -uo pipefail

BASE="$1"
REPO="$2"
N="${3:-2}"
BUDGET="${4:-1024}"
SERVER="$BASE/llama.cpp/build/bin/llama-server"  # Metal
OUT="$BASE/results/round3-budget-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$OUT" "$BASE/models-round3"
exec > >(tee -a "$OUT/bench.log") 2>&1
echo "round 3 budget-forcing run $(basename "$OUT"), n per cell $N, budget $BUDGET"
{ echo "llama.cpp commit: $(cat "$BASE/llama_cpp_commit.txt")"; uname -a; sysctl -n machdep.cpu.brand_string; } > "$OUT/system.txt"

[ -f "$BASE/models-round3/Qwen3.5-9B-Q4_K_M.gguf" ] || {
  curl -fL --retry 5 --retry-delay 5 -sS -o "$BASE/models-round3/Qwen3.5-9B-Q4_K_M.gguf.part" \
    "https://huggingface.co/unsloth/Qwen3.5-9B-GGUF/resolve/main/Qwen3.5-9B-Q4_K_M.gguf" \
    && mv "$BASE/models-round3/Qwen3.5-9B-Q4_K_M.gguf.part" "$BASE/models-round3/Qwen3.5-9B-Q4_K_M.gguf"
}

# <label> <gguf> <modes>
MODELS="phi-3.5-mini $BASE/models/Phi-3.5-mini-instruct-Q4_K_M.gguf raw
gemma-3-4b $BASE/models/gemma-3-4b-it-Q4_K_M.gguf raw
llama-3.1-8b $BASE/models/Llama-3.1-8B-Instruct-Q4_K_M.gguf raw
glm-4-9b $BASE/models/GLM-4-9B-0414-Q4_K_M.gguf raw
qwen3-8b $BASE/models/qwen3-8b-q4_k_m.gguf raw,chat-off,chat-on
gemma-3-12b $BASE/models-phase2/gemma-3-12b-it-Q4_K_M.gguf raw
gemma-4-12b $BASE/models-phase2/gemma-4-12b-it-Q4_K_M.gguf raw
qwen3-14b $BASE/models-phase2/Qwen3-14B-Q4_K_M.gguf raw,chat-off,chat-on
qwen3.5-9b $BASE/models-round3/Qwen3.5-9B-Q4_K_M.gguf raw,chat-off,chat-on"
echo "$MODELS" | while read -r label gguf modes; do echo "model $label $gguf $modes $([ -f "$gguf" ] && echo present || echo MISSING)"; done >> "$OUT/system.txt"

now() { python3 -c 'import time; print(f"{time.time():.3f}")'; }
window() {
  local label="$1"; shift
  local t0; t0=$(now)
  "$@"
  local rc=$?
  echo "$label start=$t0 end=$(now) exit=$rc" >> "$OUT/windows.log"
  return $rc
}
session() {  # session <label> <gguf> <task> <mode>
  local lab="round3_$1_$3_$4" before
  [ -f "$2" ] || { echo "skip $lab: $2 missing"; return; }
  echo "== $lab"
  before=$(ls -1 eval-results/ 2>/dev/null | sort)
  window "$lab" /opt/homebrew/bin/uv run --no-sync pytest tests/model/test_round3_tasks.py -m model -s -q \
    --round3-server "$SERVER" --round3-gguf "$2" --round3-task "$3" --round3-mode "$4" --round3-n "$N" --round3-think-budget "$BUDGET" \
    --model-threads 4 < /dev/null > "$OUT/pytest_$lab.log" 2>&1
  grep -E "^  (all_ok|action_ok)|^  p50" "$OUT/pytest_$lab.log" | head -2
  echo "$lab $(comm -13 <(echo "$before") <(ls -1 eval-results/ | sort) | tr '\n' ' ')" >> "$OUT/artifacts.txt"
  window "idle-gap_$lab" sleep 20
}

cd "$REPO" || exit 1
sudo powermetrics --samplers cpu_power,gpu_power,thermal -i 500 -o "$OUT/powermetrics.txt" &
PM_PID=$!
sleep 5
window idle-pre sleep 30
echo "$MODELS" | while read -r label gguf modes; do
  case "$modes" in *chat-on*) ;; *) continue ;; esac
  for task in narrow full; do session "$label" "$gguf" "$task" chat-budget; done
done
window idle-post sleep 30
sudo pkill -INT -P "$PM_PID" -x powermetrics  # see bench.sh: sudo won't relay our signal
wait "$PM_PID" 2>/dev/null
echo "done $(basename "$OUT")"
