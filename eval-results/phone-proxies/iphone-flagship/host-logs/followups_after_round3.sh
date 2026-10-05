#!/usr/bin/env bash
# One-off (2026-10-04), runs ON iphone-flagship (mac-m4.metal): once round 3 here ends, run the two
# follow-ups queued on the M4 Max as well, to use the host's paid 24 h (earliest release 05:29Z):
#   1. the round 3 prompt ablation (test_round3_ablation.py), the same 4 models x 7 variants as
#      bench_ablation_m4max.sh;
#   2. the think-budget re-run: Qwen3.5-9B narrow and full chat-on at --round3-think-budget 4096.
# Proxy conventions from bench_round3.sh: Metal llama-server, --model-threads 4, the run's own
# powermetrics trace, idle/idle-gap windows (the Mac minis never throttled, so no thermal gate).
# The ablation files and the updated conftest.py (one added option, --round3-variant) are staged
# and copied into the repo only after round 3 exits, so the running round 3 never sees them.
# No new cell starts after CUTOFF; skipped cells are logged.
set -uo pipefail

BASE=/Users/ec2-user/phoneproxy
REPO=/Users/ec2-user/fleet-trilogy
STAGE=$BASE/followups/staging
SERVER="$BASE/llama.cpp/build/bin/llama-server"  # Metal
N=2
BUDGET=4096
CUTOFF=$(date -j -u -f "%Y-%m-%dT%H:%M:%SZ" "2026-10-05T04:30:00Z" +%s)

while pgrep -f "phoneproxy/[b]ench_round3.sh" >/dev/null; do sleep 60; done

cp "$REPO/tests/model/conftest.py" "$STAGE/conftest.py.before-followups"
cp "$STAGE/round3_ablation.py" "$STAGE/test_round3_ablation.py" "$STAGE/conftest.py" "$REPO/tests/model/"

OUT="$BASE/results/followups-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$OUT"
exec > >(tee -a "$OUT/bench.log") 2>&1
echo "round 3 finished; follow-ups $(basename "$OUT"), n per cell $N, think budget $BUDGET, cutoff 2026-10-05T04:30:00Z"
{ echo "llama.cpp commit: $(cat "$BASE/llama_cpp_commit.txt")"; uname -a; sysctl -n machdep.cpu.brand_string
  (cd "$REPO/tests/model" && shasum -a 256 round3_eval.py round3_ablation.py test_round3_tasks.py test_round3_ablation.py conftest.py)
} > "$OUT/system.txt"

VARIANTS="base facts tables template examples temp0 grammar"
MODELS="phi-3.5-mini $BASE/models/Phi-3.5-mini-instruct-Q4_K_M.gguf
gemma-3-4b $BASE/models/gemma-3-4b-it-Q4_K_M.gguf
llama-3.1-8b $BASE/models/Llama-3.1-8B-Instruct-Q4_K_M.gguf
qwen3-14b $BASE/models-phase2/Qwen3-14B-Q4_K_M.gguf"
QWEN35="$BASE/models-round3/Qwen3.5-9B-Q4_K_M.gguf"
echo "$MODELS" | while read -r label gguf; do echo "model $label $gguf $([ -f "$gguf" ] && echo present || echo MISSING)"; done >> "$OUT/system.txt"
echo "model qwen3.5-9b $QWEN35 chat-on think_budget=$BUDGET $([ -f "$QWEN35" ] && echo present || echo MISSING)" >> "$OUT/system.txt"

now() { python3 -c 'import time; print(f"{time.time():.3f}")'; }
window() {
  local label="$1"; shift
  local t0; t0=$(now)
  "$@"
  local rc=$?
  echo "$label start=$t0 end=$(now) exit=$rc" >> "$OUT/windows.log"
  return $rc
}
cell() {  # cell <label> <pytest args...>
  local lab="$1" before; shift
  [ "$(date -u +%s)" -lt "$CUTOFF" ] || { echo "skip $lab: past cutoff"; return; }
  echo "== $lab"
  before=$(ls -1 eval-results/ 2>/dev/null | sort)
  window "$lab" /opt/homebrew/bin/uv run --no-sync pytest "$@" -m model -s -q --round3-server "$SERVER" \
    --round3-n "$N" --model-threads 4 < /dev/null > "$OUT/pytest_$lab.log" 2>&1
  grep -E "^  (action_ok|all_ok)|^  p50" "$OUT/pytest_$lab.log" | head -2
  echo "$lab $(comm -13 <(echo "$before") <(ls -1 eval-results/ | sort) | tr '\n' ' ')" >> "$OUT/artifacts.txt"
  window "idle-gap_$lab" sleep 20
}

cd "$REPO" || exit 1
sudo powermetrics --samplers cpu_power,gpu_power,thermal -i 500 -o "$OUT/powermetrics.txt" &
PM_PID=$!
sleep 5
window idle-pre sleep 30
# 1. Ablation, variant-major within each model (as bench_ablation_m4max.sh).
echo "$MODELS" | while read -r label gguf; do
  [ -f "$gguf" ] || { echo "skip $label: $gguf missing"; continue; }
  for v in $VARIANTS; do
    cell "ablation_${label}_$v" tests/model/test_round3_ablation.py --round3-gguf "$gguf" --round3-variant "$v"
  done
done
# 2. Think-budget re-run.
for task in narrow full; do
  cell "round3_qwen3.5-9b_${task}_chat-on_think$BUDGET" tests/model/test_round3_tasks.py --round3-gguf "$QWEN35" \
    --round3-task "$task" --round3-mode chat-on --round3-think-budget "$BUDGET"
done
window idle-post sleep 30
sudo pkill -INT -P "$PM_PID" -x powermetrics  # see bench.sh: sudo won't relay our signal
wait "$PM_PID" 2>/dev/null
echo "done $(basename "$OUT")"
