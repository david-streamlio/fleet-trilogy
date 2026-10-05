#!/usr/bin/env bash
# The M4 Max (this MacBook) counterpart of bench_workload.sh: Talk 2's real workload with the
# same pairs, flags and 3 repetitions as mac2's test C, on llama.cpp v0.5.0 (the build mac2
# and the proxies run), so the M4 Max column matches M1's. The 2026-10-02 M4 Max runs used
# b10931 and covered two pairs; the published five-model numbers (2026-09-26) came from one
# multi-model session that measured Phi 2x slower than its own runs. The last window repeats
# that five-model session (same build, same day) to tell the two explanations apart.
#
# powermetrics runs separately, started by the user (it needs sudo):
#   sudo powermetrics --samplers cpu_power,gpu_power -i 500 -o /tmp/m4max-powermetrics.txt
#
#   [GATE_PM=<powermetrics file>] [ORDER=reverse] bench_workload_m4max.sh <repo> <out-dir> [<label regex> [<reps>]]
#
# The optional regex runs only the matching sessions (e.g. to resume an interrupted run);
# <reps> is the repetition list, default "1 2 3".
# GATE_PM: before every session, wait until that live trace (powermetrics with the thermal
# sampler) shows 60 s of Nominal thermal pressure; the wait is logged as a cool-wait window.
# A MacBook reaches Heavy pressure within ~12 min of this workload, so without the gate a
# fixed pair order measures the later models warmer (test log, M4 Max caffeinated rerun).
# ORDER=reverse runs the pairs last-to-first, as a check that order no longer matters.
set -uo pipefail

# An idle MacBook sleeps after 10 minutes (the first run lost its last two sessions that
# way): hold the display, idle and system awake for the whole run.
[ -n "${CAFFEINATED:-}" ] || exec env CAFFEINATED=1 caffeinate -dims "$0" "$@"

REPO="$1"
OUT="$2"
ONLY="${3:-.}"
REPS="${4:-1 2 3}"
SRC="$HOME/tools/llama.cpp-v0.5.0"
BIN="$SRC/build/bin/llama-completion"
mkdir -p "$OUT"
exec > >(tee -a "$OUT/bench.log") 2>&1
pmset -g batt | head -1 | grep -q "AC Power" || { echo "on battery power: plug in first"; exit 1; }
{ echo "llama.cpp commit: $(git -C "$SRC" rev-parse HEAD)"; uname -a; sysctl -n machdep.cpu.brand_string; pmset -g batt | head -1; pmset -g | grep -i powermode; } > "$OUT/system.txt"

now() { python3 -c 'import time; print(f"{time.time():.3f}")'; }
window() {
  local label="$1"; shift
  local t0; t0=$(now)
  "$@"
  local rc=$?
  echo "$label start=$t0 end=$(now) exit=$rc" >> "$OUT/windows.log"
  return $rc
}

# The weights stay where models.toml's defaults point (~/tools/models/...); only the binary
# changes, to v0.5.0.
export LLM_BINARY_PATH_PHI35_MINI="$BIN" LLM_BINARY_PATH_GEMMA3_4B="$BIN" LLM_BINARY_PATH_LLAMA31_8B="$BIN" \
  LLM_BINARY_PATH_GLM4_9B="$BIN" LLM_BINARY_PATH_QWEN3_8B="$BIN"

PAIRS="test_compare_edge_triage_models.py phi-3.5-mini-instruct-q4km 15
test_compare_tier2_models.py gemma-3-4b-it-q4km 30
test_compare_edge_triage_models.py gemma-3-4b-it-q4km 15
test_compare_edge_triage_models.py llama-3.1-8b-instruct-q4km 15
test_compare_edge_triage_models.py glm-4-9b-0414-q4km 15
test_compare_edge_triage_models.py qwen3-8b-q4km 15"
FIVE="phi-3.5-mini-instruct-q4km,gemma-3-4b-it-q4km,llama-3.1-8b-instruct-q4km,glm-4-9b-0414-q4km,qwen3-8b-q4km"

wait_cool() {  # wait_cool <label>: block until GATE_PM's last 120 samples (60 s) are all Nominal
  [ -n "${GATE_PM:-}" ] || return 0
  until [ -f "$GATE_PM" ] && [ "$(tail -c 4000000 "$GATE_PM" | grep 'Current pressure level' | tail -n 120 | grep -c 'Nominal')" -ge 120 ]; do
    sleep 5
  done
}

run() {  # run <label> <pytest file> <ids> <eval runs>: one pytest session in its own window
  local label="$1" test="$2" ids="$3" runs="$4" before
  echo "$label" | grep -qE "$ONLY" || return 0
  window "cool-wait_$label" wait_cool "$label"
  echo "== $label"
  before=$(ls -1 eval-results/ | sort)
  # No --model-threads: the default (12, tuned for this machine) is what the 2026-10-02 runs used.
  # --model-backend server: what the published runs used; the harness default is in-process since 2026-10-05.
  window "$label" uv run --no-sync pytest "tests/model/$test" -m model -s -q \
    --only-model-ids "$ids" --model-eval-runs "$runs" --model-backend server < /dev/null > "$OUT/pytest_$label.log" 2>&1
  tail -n 2 "$OUT/pytest_$label.log"
  echo "$label $(comm -13 <(echo "$before") <(ls -1 eval-results/ | sort) | tr '\n' ' ')" >> "$OUT/artifacts.txt"
  window "idle-gap_$label" sleep 20
}

cd "$REPO" || exit 1
[ "${ORDER:-}" = reverse ] && PAIRS=$(echo "$PAIRS" | awk '{ l[NR] = $0 } END { for (i = NR; i > 0; i--) print l[i] }')
{ echo "order: ${ORDER:-forward}"; echo "gate: ${GATE_PM:-none}"; } >> "$OUT/system.txt"
window idle-pre sleep 60
echo "$PAIRS" | while read -r test id runs; do
  task=$(echo "$test" | sed -E 's/test_compare_(.*)_models\.py/\1/')
  for r in $REPS; do run "${task}_${id}_r$r" "$test" "$id" "$runs"; done
done
run edge_triage_five-model-session test_compare_edge_triage_models.py "$FIVE" 15
window idle-post sleep 60
echo "done $(basename "$OUT")"
