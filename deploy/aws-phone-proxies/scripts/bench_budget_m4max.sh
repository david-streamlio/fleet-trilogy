#!/usr/bin/env bash
# Round 3 budget forcing on the M4 Max (this MacBook): bench_budget.sh's sessions (the Qwen models,
# both tasks, mode chat-budget at BUDGET thinking tokens), with this machine's conditions built in:
# - re-execs under caffeinate -dims (an idle MacBook sleeps after 10 min);
# - refuses battery power;
# - GATE_PM (required): the user's powermetrics trace with the thermal sampler. Before every
#   session it waits for 60 s of Nominal thermal pressure, logged as a cool-wait window, since
#   this laptop throttles under sustained load and the throttled state trades speed for energy.
#   The same trace gives the energy windows (no sudo here).
# Models: models.toml's default paths under ~/tools/models, plus the 12-14B models and
# Qwen3.5-9B if they are present; Qwen3.8-27B (only this machine holds it) runs at n=1.
#
#   GATE_PM=/tmp/m4max-powermetrics-4.txt bench_budget_m4max.sh <repo> <out-dir> [n-per-cell] [budget]
#   (start first: sudo powermetrics --samplers cpu_power,gpu_power,thermal -i 500 -o "$GATE_PM")
set -uo pipefail

[ -n "${CAFFEINATED:-}" ] || exec env CAFFEINATED=1 caffeinate -dims "$0" "$@"

REPO="$1"
OUT="$2"
N="${3:-2}"
BUDGET="${4:-1024}"
: "${GATE_PM:?set GATE_PM to the running powermetrics trace}"
SRC="$HOME/tools/llama.cpp-v0.5.0"
SERVER="$SRC/build/bin/llama-server"
M="$HOME/tools/models"
mkdir -p "$OUT"
exec > >(tee -a "$OUT/bench.log") 2>&1
pmset -g batt | head -1 | grep -q "AC Power" || { echo "on battery power: plug in first"; exit 1; }
echo "round 3 budget forcing on the M4 Max: $(basename "$OUT"), n per cell $N, budget $BUDGET, gate $GATE_PM"

# <label> <gguf> <modes> <n>
MODELS="phi-3.5-mini $M/Phi-3.5-mini-instruct-GGUF/Phi-3.5-mini-instruct-Q4_K_M.gguf raw $N
gemma-3-4b $M/gemma-3-4b-it-GGUF/gemma-3-4b-it-Q4_K_M.gguf raw $N
llama-3.1-8b $M/Llama-3.1-8B-Instruct-GGUF/Llama-3.1-8B-Instruct-Q4_K_M.gguf raw $N
glm-4-9b $M/GLM-4-9B-0414-GGUF/GLM-4-9B-0414-Q4_K_M.gguf raw $N
qwen3-8b $M/Qwen3-8B-GGUF/qwen3-8b-q4_k_m.gguf raw,chat-off,chat-on $N
gemma-3-12b $M/gemma-3-12b-it-GGUF/gemma-3-12b-it-Q4_K_M.gguf raw $N
gemma-4-12b $M/gemma-4-12b-it-GGUF/gemma-4-12b-it-Q4_K_M.gguf raw $N
qwen3-14b $M/Qwen3-14B-GGUF/Qwen3-14B-Q4_K_M.gguf raw,chat-off,chat-on $N
qwen3.5-9b $M/Qwen3.5-9B-GGUF/Qwen3.5-9B-Q4_K_M.gguf raw,chat-off,chat-on $N
qwen3.8-27b $M/Qwen3.8-27B-GGUF/Qwen3.8-27B-UD-Q4_K_M.gguf raw,chat-off,chat-on 1"
{ echo "llama.cpp commit: $(git -C "$SRC" rev-parse HEAD)"; uname -a; sysctl -n machdep.cpu.brand_string; pmset -g batt | head -1
  echo "gate: $GATE_PM"
  echo "$MODELS" | while read -r label gguf modes n; do echo "model $label $gguf $modes n=$n $([ -f "$gguf" ] && echo present || echo MISSING)"; done
} > "$OUT/system.txt"

now() { python3 -c 'import time; print(f"{time.time():.3f}")'; }
window() {
  local label="$1"; shift
  local t0; t0=$(now)
  "$@"
  local rc=$?
  echo "$label start=$t0 end=$(now) exit=$rc" >> "$OUT/windows.log"
  return $rc
}
wait_cool() {  # 120 samples (60 s) of Nominal; 4 MB holds ~480 samples at ~8 KB each (incident 21)
  until [ -f "$GATE_PM" ] && [ "$(tail -c 4000000 "$GATE_PM" | grep 'Current pressure level' | tail -n 120 | grep -c 'Nominal')" -ge 120 ]; do
    sleep 5
  done
}
session() {  # session <label> <gguf> <task> <mode> <n>
  local lab="round3_$1_$3_$4" before
  [ -f "$2" ] || { echo "skip $lab: $2 missing"; return; }
  window "cool-wait_$lab" wait_cool
  echo "== $lab"
  before=$(ls -1 eval-results/ | sort)
  # No --model-threads: the default (12) as in every other M4 Max run.
  window "$lab" uv run --no-sync pytest tests/model/test_round3_tasks.py -m model -s -q \
    --round3-server "$SERVER" --round3-gguf "$2" --round3-task "$3" --round3-mode "$4" --round3-n "$5" --round3-think-budget "$BUDGET" \
    < /dev/null > "$OUT/pytest_$lab.log" 2>&1
  grep -E "^  (all_ok|action_ok)|^  p50" "$OUT/pytest_$lab.log" | head -2
  echo "$lab $(comm -13 <(echo "$before") <(ls -1 eval-results/ | sort) | tr '\n' ' ')" >> "$OUT/artifacts.txt"
  window "idle-gap_$lab" sleep 20
}

cd "$REPO" || exit 1
window idle-pre sleep 60
echo "$MODELS" | while read -r label gguf modes n; do
  case "$modes" in *chat-on*) ;; *) continue ;; esac
  for task in narrow full; do session "$label" "$gguf" "$task" chat-budget "$n"; done
done
window idle-post sleep 60
echo "done $(basename "$OUT")"
