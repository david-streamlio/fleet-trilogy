#!/bin/bash
# Talk 2 power-measurement window for the Edge Triage Pipeline real-stream re-measure
# (2026-10-05): a different event per call (--vary-events), optionally with the event-last
# prompt (--triage-prompt event-last) or the in-process backend. Same window protocol as the
# 2026-10-02 runs' /mnt/data/fleet-trilogy/pi_power_trial.sh (docs/TALK2-POWER-
# MEASUREMENT-PLAN.md): the meter is zeroed by hand before, read once from a photo
# after; this script logs Pi-side timestamps and a 30 s temperature/clock/throttle trace
# to the same log as those runs. Runs from the repo copy whose venv has llama-cpp-python
# built (needed only for the in-process backend).
#   ./pi_power_trial_realstream.sh idle <seconds>
#   ./pi_power_trial_realstream.sh edge-triage phi35 <eval_runs> [extra pytest args...]
# e.g. ./pi_power_trial_realstream.sh edge-triage phi35 9 --model-backend server --vary-events \
#        --triage-prompt event-last --model-confirm-multiplier 1
set -uo pipefail
cd /mnt/data/fleet-trilogy-talk3wip
export PATH="$HOME/.local/bin:$PATH"
LOG=/mnt/data/fleet-trilogy/pi_power_trial.log
BIN=/mnt/data/tools/llama.cpp/build/bin/llama-completion

snap() { echo "$1 utc=$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ) epoch=$(date +%s.%3N) $(vcgencmd measure_temp) $(vcgencmd get_throttled) arm_hz=$(vcgencmd measure_clock arm | cut -d= -f2) load=$(cut -d" " -f1-3 /proc/loadavg)" | tee -a "$LOG"; }
trace() { while :; do echo "$(date +%s.%3N) $(vcgencmd measure_temp) arm_hz=$(vcgencmd measure_clock arm | cut -d= -f2) $(vcgencmd get_throttled)" >> "$1"; sleep 30; done; }
trace_summary() {  # live throttle bits are the low nibble of get_throttled
  awk '{ n++; if (substr($4, length($4)) != "0") live++
         t = $2; sub(/temp=/, "", t); sub(/.C/, "", t); if (t + 0 > max) max = t + 0 }
       END { printf "TRACE samples=%d live_throttled=%d peak_temp=%.1fC\n", n, live, max }' "$1"
}

# In-process, the model runs inside pytest, so check for that as well as llama.cpp's own processes.
if pgrep -f "llama-(server|completion)|pytest" >/dev/null; then echo "REFUSING: a llama or pytest process is already running" | tee -a "$LOG"; exit 2; fi

mode="$1"
if [ "$mode" = idle ]; then
  secs="$2"; label="idle-${secs}s-$(date -u +%Y%m%dT%H%M%SZ)"
else
  task="$mode"; model="$2"; runs="$3"; shift 3
  case "$model" in
    phi35) id=phi-3.5-mini-instruct-q4km; benv=LLM_BINARY_PATH_PHI35_MINI; menv=LLM_MODEL_PATH_PHI35_MINI
           mpath=/mnt/data/models/Phi-3.5-mini-instruct-GGUF/Phi-3.5-mini-instruct-Q4_K_M.gguf ;;
    *) echo "unknown model $model"; exit 2 ;;
  esac
  case "$task" in
    edge-triage) test=tests/model/test_compare_edge_triage_models.py ;;
    *) echo "unknown task $task"; exit 2 ;;
  esac
  backend=inprocess; prompt=default; vary=""
  for arg in "$@"; do
    case "$arg" in --vary-events) vary="-vary" ;; esac
  done
  prev=""
  for arg in "$@"; do
    [ "$prev" = "--model-backend" ] && backend="$arg"
    [ "$prev" = "--triage-prompt" ] && prompt="$arg"
    prev="$arg"
  done
  label="${task}-${model}-n${runs}-${backend}-${prompt}${vary}-$(date -u +%Y%m%dT%H%M%SZ)"
fi

TRACE="trace_${label}.log"
echo "=== $label ===" | tee -a "$LOG"; snap START; t0=$(date +%s.%3N)
trace "$TRACE" & trace_pid=$!
if [ "$mode" = idle ]; then
  sleep "$secs"; rc=0
else
  # The harness runs llama-server from this binary's directory; in-process ignores it.
  env "$benv=$BIN" "$menv=$mpath" uv run --no-sync pytest "$test" -m model -s \
    --model-eval-runs "$runs" --model-threads 4 --model-timeout-seconds 600 \
    --only-model-ids "$id" "$@" > "power_${label}.log" 2>&1
  rc=$?
fi
kill "$trace_pid" 2>/dev/null; wait "$trace_pid" 2>/dev/null
t1=$(date +%s.%3N); snap END
trace_summary "$TRACE" | tee -a "$LOG"
echo "DONE $label exit=$rc elapsed_s=$(awk "BEGIN{printf \"%.3f\", $t1 - $t0}")" | tee -a "$LOG"
