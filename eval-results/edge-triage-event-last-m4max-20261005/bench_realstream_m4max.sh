#!/usr/bin/env bash
# Talk 2 real-stream re-measure on the M4 Max (2026-10-05): Phi-3.5-mini on the Edge
# Triage Pipeline with a different event on every call (--vary-events), for both prompt
# orders -- the published one (`default`) and the event fields moved after the rules
# (`event-last`). Everything else matches the published M4 Max row (the caffeinated run,
# eval-results/phone-proxies/m4max-macbook/20261004T005747Z-caffeinated, made by
# deploy/aws-phone-proxies/scripts/bench_workload_m4max.sh): llama.cpp v0.5.0,
# llama-server on the GPU, --model-eval-runs 15 (60 calls), 12 threads, 3 reps, a
# Nominal-thermal gate before each session, idle windows before and after.
# The two prompts alternate rep by rep, so thermal drift can't favour either one.
# llama-server runs with one slot and no host-RAM prompt cache (-np 1 --cache-ram 0), so
# each call can reuse only the previous call's prompt prefix, as in a stream of events
# that never repeat. Run 1 (realstream-run1-cache-ram-on) used the server defaults: its
# cache of earlier prompts restored each of the three recurring events whole, so the
# default prompt read 1 of 514 tokens per call -- a best case again, not a stream.
#
# powermetrics runs separately, started by the user (it needs sudo):
#   sudo powermetrics --samplers cpu_power,gpu_power,thermal -i 500 -o /tmp/m4max-powermetrics-3.txt
#
#   GATE_PM=/tmp/m4max-powermetrics-3.txt bench_realstream_m4max.sh <repo> <out-dir>
set -uo pipefail

# An idle MacBook sleeps after 10 minutes: hold the display, idle and system awake.
[ -n "${CAFFEINATED:-}" ] || exec env CAFFEINATED=1 caffeinate -dims "$0" "$@"

REPO="$1"
OUT="$2"
SRC="$HOME/tools/llama.cpp-v0.5.0"
BIN="$SRC/build/bin/llama-completion"  # the harness runs llama-server, its sibling
mkdir -p "$OUT"
exec > >(tee -a "$OUT/bench.log") 2>&1
pmset -g batt | head -1 | grep -q "AC Power" || { echo "on battery power: plug in first"; exit 1; }
{ echo "llama.cpp commit: $(git -C "$SRC" rev-parse HEAD)"; uname -a; sysctl -n machdep.cpu.brand_string; pmset -g batt | head -1; pmset -g | grep -i powermode; echo "gate: ${GATE_PM:-none}"; } > "$OUT/system.txt"

now() { python3 -c 'import time; print(f"{time.time():.3f}")'; }
window() {
  local label="$1"; shift
  local t0; t0=$(now)
  "$@"
  local rc=$?
  echo "$label start=$t0 end=$(now) exit=$rc" >> "$OUT/windows.log"
  return $rc
}
wait_cool() {  # block until GATE_PM's last 120 samples (60 s) are all Nominal
  [ -n "${GATE_PM:-}" ] || return 0
  until [ -f "$GATE_PM" ] && [ "$(tail -c 4000000 "$GATE_PM" | grep 'Current pressure level' | tail -n 120 | grep -c 'Nominal')" -ge 120 ]; do
    sleep 5
  done
}

export LLM_BINARY_PATH_PHI35_MINI="$BIN"
run() {  # run <prompt> <rep>
  local prompt="$1" r="$2" label before
  label="edge_triage_phi-3.5-mini-instruct-q4km_realstream_${prompt}_r$r"
  window "cool-wait_$label" wait_cool
  echo "== $label"
  before=$(ls -1 eval-results/ | sort)
  window "$label" uv run --no-sync pytest tests/model/test_compare_edge_triage_models.py -m model -s -q \
    --only-model-ids phi-3.5-mini-instruct-q4km --model-eval-runs 15 --model-backend server \
    --vary-events --triage-prompt "$prompt" --model-server-args "-np 1 --cache-ram 0" < /dev/null > "$OUT/pytest_$label.log" 2>&1
  tail -n 2 "$OUT/pytest_$label.log"
  echo "$label $(comm -13 <(echo "$before") <(ls -1 eval-results/ | sort) | tr '\n' ' ')" >> "$OUT/artifacts.txt"
  window "idle-gap_$label" sleep 20
}

cd "$REPO" || exit 1
window idle-pre sleep 60
for r in 1 2 3; do
  run default "$r"
  run event-last "$r"
done
window idle-post sleep 60
echo "done $(basename "$OUT")"
