#!/usr/bin/env bash
# Round 3 prompt ablation on the M4 Max (this MacBook): every variant in
# tests/model/round3_ablation.py for the models that struggled on the full task plus one strong
# model as a ceiling, each model x variant its own pytest session and energy window. Same
# machine conditions as bench_round3_m4max.sh: caffeinate, AC power, and a thermal gate before
# every session (GATE_PM: the user's powermetrics trace with the thermal sampler).
#
#   GATE_PM=/tmp/m4max-powermetrics-4.txt bench_ablation_m4max.sh <repo> <out-dir> [n-per-cell]
set -uo pipefail

[ -n "${CAFFEINATED:-}" ] || exec env CAFFEINATED=1 caffeinate -dims "$0" "$@"

REPO="$1"
OUT="$2"
N="${3:-2}"
: "${GATE_PM:?set GATE_PM to the running powermetrics trace}"
SRC="$HOME/tools/llama.cpp-v0.5.0"
SERVER="$SRC/build/bin/llama-server"
M="$HOME/tools/models"
VARIANTS="base facts tables template examples temp0 grammar"
MODELS="phi-3.5-mini $M/Phi-3.5-mini-instruct-GGUF/Phi-3.5-mini-instruct-Q4_K_M.gguf
gemma-3-4b $M/gemma-3-4b-it-GGUF/gemma-3-4b-it-Q4_K_M.gguf
llama-3.1-8b $M/Llama-3.1-8B-Instruct-GGUF/Llama-3.1-8B-Instruct-Q4_K_M.gguf
qwen3-14b $M/Qwen3-14B-GGUF/Qwen3-14B-Q4_K_M.gguf"
mkdir -p "$OUT"
exec > >(tee -a "$OUT/bench.log") 2>&1
pmset -g batt | head -1 | grep -q "AC Power" || { echo "on battery power: plug in first"; exit 1; }
echo "round 3 ablation on the M4 Max: $(basename "$OUT"), n per cell $N, variants: $VARIANTS"
{ echo "llama.cpp commit: $(git -C "$SRC" rev-parse HEAD)"; uname -a; sysctl -n machdep.cpu.brand_string; echo "gate: $GATE_PM"
  echo "$MODELS" | while read -r label gguf; do echo "model $label $gguf $([ -f "$gguf" ] && echo present || echo MISSING)"; done
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
wait_cool() {  # 120 samples (60 s) of Nominal; 4 MB holds ~480 samples (incident 21)
  until [ -f "$GATE_PM" ] && [ "$(tail -c 4000000 "$GATE_PM" | grep 'Current pressure level' | tail -n 120 | grep -c 'Nominal')" -ge 120 ]; do
    sleep 5
  done
}

cd "$REPO" || exit 1
window idle-pre sleep 60
# Variant-major order within each model, so a model's variants are measured close together.
echo "$MODELS" | while read -r label gguf; do
  [ -f "$gguf" ] || { echo "skip $label: $gguf missing"; continue; }
  for v in $VARIANTS; do
    lab="ablation_${label}_$v"
    window "cool-wait_$lab" wait_cool
    echo "== $lab"
    before=$(ls -1 eval-results/ | sort)
    window "$lab" uv run --no-sync pytest tests/model/test_round3_ablation.py -m model -s -q \
      --round3-server "$SERVER" --round3-gguf "$gguf" --round3-variant "$v" --round3-n "$N" \
      < /dev/null > "$OUT/pytest_$lab.log" 2>&1
    grep -E "^  (action_ok|all_ok)|^  p50" "$OUT/pytest_$lab.log" | head -2
    echo "$lab $(comm -13 <(echo "$before") <(ls -1 eval-results/ | sort) | tr '\n' ' ')" >> "$OUT/artifacts.txt"
    window "idle-gap_$lab" sleep 20
  done
done
window idle-post sleep 60
echo "done $(basename "$OUT")"
