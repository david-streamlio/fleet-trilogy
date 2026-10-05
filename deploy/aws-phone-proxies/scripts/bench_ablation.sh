#!/usr/bin/env bash
# Round 3 prompt ablation, run ON a Mac proxy: the proxy version of bench_ablation_m4max.sh. The given
# variants (default: all seven in tests/model/round3_ablation.py) for Phi-3.5-mini, Gemma-3-4B,
# Llama-3.1-8B and Qwen3-14B, each model x variant its own pytest session and powermetrics window,
# variant-major within each model. Same machinery as bench_budget.sh: Metal llama-server,
# --model-threads 4, the run's own powermetrics trace, idle windows, no thermal gate (the Mac minis
# never throttled). Artifacts: <repo>/eval-results/compare-round3-ablation-*.json, mapped per window in
# results/round3-ablation-<ts>/artifacts.txt.
#
#   bench_ablation.sh <base> <repo> [n-per-cell] ["variant variant ..."]
set -uo pipefail

BASE="$1"
REPO="$2"
N="${3:-2}"
VARIANTS="${4:-base facts tables template examples temp0 grammar}"
SERVER="$BASE/llama.cpp/build/bin/llama-server"  # Metal
OUT="$BASE/results/round3-ablation-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$OUT"
exec > >(tee -a "$OUT/bench.log") 2>&1
echo "round 3 ablation run $(basename "$OUT"), n per cell $N, variants: $VARIANTS"

# <label> <gguf>
MODELS="phi-3.5-mini $BASE/models/Phi-3.5-mini-instruct-Q4_K_M.gguf
gemma-3-4b $BASE/models/gemma-3-4b-it-Q4_K_M.gguf
llama-3.1-8b $BASE/models/Llama-3.1-8B-Instruct-Q4_K_M.gguf
qwen3-14b $BASE/models-phase2/Qwen3-14B-Q4_K_M.gguf"
{ echo "llama.cpp commit: $(cat "$BASE/llama_cpp_commit.txt")"; uname -a; sysctl -n machdep.cpu.brand_string
  echo "variants: $VARIANTS"
  (cd "$REPO/tests/model" && shasum -a 256 round3_eval.py round3_ablation.py test_round3_ablation.py conftest.py)
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
cell() {  # cell <label> <gguf> <variant>
  local lab="ablation_$1_$3" before
  [ -f "$2" ] || { echo "skip $lab: $2 missing"; return; }
  echo "== $lab"
  before=$(ls -1 eval-results/ 2>/dev/null | sort)
  window "$lab" /opt/homebrew/bin/uv run --no-sync pytest tests/model/test_round3_ablation.py -m model -s -q \
    --round3-server "$SERVER" --round3-gguf "$2" --round3-variant "$3" --round3-n "$N" \
    --model-threads 4 < /dev/null > "$OUT/pytest_$lab.log" 2>&1
  grep -E "^  (action_ok|all_ok)|^  p50" "$OUT/pytest_$lab.log" | head -2
  echo "$lab $(comm -13 <(echo "$before") <(ls -1 eval-results/ | sort) | tr '\n' ' ')" >> "$OUT/artifacts.txt"
  window "idle-gap_$lab" sleep 20
}

cd "$REPO" || exit 1
sudo powermetrics --samplers cpu_power,gpu_power,thermal -i 500 -o "$OUT/powermetrics.txt" &
PM_PID=$!
sleep 5
window idle-pre sleep 30
echo "$MODELS" | while read -r label gguf; do
  for v in $VARIANTS; do cell "$label" "$gguf" "$v"; done
done
window idle-post sleep 30
sudo pkill -INT -P "$PM_PID" -x powermetrics  # see bench.sh: sudo won't relay our signal
wait "$PM_PID" 2>/dev/null
echo "done $(basename "$OUT")"
