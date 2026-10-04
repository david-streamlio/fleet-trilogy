#!/bin/bash
# One-off (2026-10-04): once the ablation (queued by /tmp/ablation_after_round3.sh) ends, re-run the
# round-3 cells Qwen3.5-9B narrow and full chat-on with a 4096-token think budget instead of the default 2048,
# to tell thinking runaway from a tight budget. Same conditions as bench_round3_m4max.sh: caffeinate,
# AC power, the thermal gate on the powermetrics trace, and idle/cool-wait windows in windows.log.
set -uo pipefail
[ -n "${CAFFEINATED:-}" ] || exec env CAFFEINATED=1 caffeinate -dims "$0" "$@"

REPO=/Users/david.kjerrumgaard/clone-zone/davidkj-datadog/fleet-trilogy
GATE_PM=/tmp/m4max-powermetrics-4.txt
SERVER=$HOME/tools/llama.cpp-v0.5.0/build/bin/llama-server
GGUF=$HOME/tools/models/Qwen3.5-9B-GGUF/Qwen3.5-9B-Q4_K_M.gguf
BUDGET=4096
N=2

while pgrep -f "[a]blation_after_round3.sh" >/dev/null || pgrep -f "scripts/[b]ench_ablation_m4max.sh" >/dev/null; do sleep 60; done

OUT="$REPO/eval-results/phone-proxies/m4max-macbook/$(date -u +%Y%m%dT%H%M%SZ)-thinkbudget$BUDGET"
mkdir -p "$OUT"
exec > >(tee -a "$OUT/bench.log") 2>&1
echo "ablation finished $(date -u +%H:%M:%SZ); think-budget $BUDGET re-run, n per cell $N, gate $GATE_PM"
pmset -g batt | head -1 | grep -q "AC Power" || { echo "on battery power: plug in first"; exit 1; }
pgrep -x powermetrics >/dev/null || { echo "powermetrics is not running: start it first"; exit 1; }
[ -f "$GGUF" ] || { echo "missing $GGUF"; exit 1; }
{ echo "llama.cpp commit: $(git -C "$HOME/tools/llama.cpp-v0.5.0" rev-parse HEAD)"; uname -a; sysctl -n machdep.cpu.brand_string
  pmset -g batt | head -1; echo "gate: $GATE_PM"; echo "model qwen3.5-9b $GGUF chat-on narrow,full think_budget=$BUDGET n=$N"; } > "$OUT/system.txt"

now() { python3 -c 'import time; print(f"{time.time():.3f}")'; }
window() {
  local label="$1"; shift
  local t0; t0=$(now)
  "$@"
  local rc=$?
  echo "$label start=$t0 end=$(now) exit=$rc" >> "$OUT/windows.log"
  return $rc
}
wait_cool() {  # same gate as bench_round3_m4max.sh: 120 samples (60 s) of Nominal
  until [ -f "$GATE_PM" ] && [ "$(tail -c 4000000 "$GATE_PM" | grep 'Current pressure level' | tail -n 120 | grep -c 'Nominal')" -ge 120 ]; do
    sleep 5
  done
}

session() {  # session <task>
  local lab="round3_qwen3.5-9b_$1_chat-on_think$BUDGET" before
  window "cool-wait_$lab" wait_cool
  echo "== $lab"
  before=$(ls -1 eval-results/ | sort)
  window "$lab" uv run --no-sync pytest tests/model/test_round3_tasks.py -m model -s -q \
    --round3-server "$SERVER" --round3-gguf "$GGUF" --round3-task "$1" --round3-mode chat-on --round3-n "$N" \
    --round3-think-budget "$BUDGET" < /dev/null > "$OUT/pytest_$lab.log" 2>&1
  grep -E "^  (all_ok|action_ok)|^  p50" "$OUT/pytest_$lab.log" | head -2
  echo "$lab $(comm -13 <(echo "$before") <(ls -1 eval-results/ | sort) | tr '\n' ' ')" >> "$OUT/artifacts.txt"
  window "idle-gap_$lab" sleep 20
}

cd "$REPO" || exit 1
window idle-pre sleep 60
for task in narrow full; do session "$task"; done
window idle-post sleep 60
echo "done $(basename "$OUT")"
