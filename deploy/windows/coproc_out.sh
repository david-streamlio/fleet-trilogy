#!/usr/bin/env bash
# deploy/windows/coproc_out.sh -- coprocessor's probable-slowdown output
# (triage-payloads topic), pretty-printed, for one of the 4 output windows
# deploy/record-demo.sh records.
#
# Usage:
#   ./deploy/windows/coproc_out.sh [broker-url] [--compact | --compact=off]
#
# --compact shows only truck_id, baseline_severity and the three contextual
# triggers the LLM weighs; --compact=off (the default) prints the full JSON.
# EVENT_LOG, HEARTBEAT: see telemetry.sh.
set -uo pipefail

BROKER_URL="pulsar://localhost:6650"
COMPACT=""
for arg in "$@"; do
  case "$arg" in
    --compact|--compact=on) COMPACT="1" ;;
    --compact=off) COMPACT="" ;;
    *) BROKER_URL="$arg" ;;
  esac
done

TITLE='Probable-Slowdown Events Forwarded to Triage'
printf '\033]0;%s\007' "$TITLE"
# Clear the screen and scrollback: otherwise the window opens on Terminal's echo of
# the launch command and the shell prompt (account name, hostname, paths), which a
# quiet window -- one uplinked card -- never scrolls away on camera.
printf '\033[2J\033[3J\033[H'
# HEARTBEAT=1 (record-demo.sh's spotlight and per-window takes): keep changing
# the window title, 4 times a second. screencapture -v writes variable-frame-rate
# video whose duration ends at the window's last CHANGED frame, so a quiet window's
# clip would end early and the spotlight edit, which aligns clips on stop time minus
# duration, would place it seconds off. The title bar is cropped out of the video.
if [[ -n "${HEARTBEAT:-}" ]]; then
  (
    spin='-\|/'
    i=0
    while printf '\033]0;%s %s\007' "$TITLE" "${spin:$(( i % 4 )):1}" > /dev/tty 2>/dev/null; do
      i=$(( i + 1 ))
      sleep 0.25
    done
  ) &
fi

pulsar-client --url "$BROKER_URL" consume persistent://public/default/triage-payloads \
  -s manual-demo-coproc -n 0 -p Latest 2>&1 \
  | perl -pe 'BEGIN{$|=1} s/\e\[[0-9;]*m//g' \
  | grep --line-buffered 'content:' \
  | sed -u 's/^.*content://' \
  | while IFS= read -r line; do
      echo "[Flagged Event]"
      if [[ -n "$COMPACT" ]]; then
        printf '%s\n' "$line" | jq -C '{truck_id, baseline_severity, contextual_triggers: ((.contextual_triggers // {}) | {weather_condition, cargo_type, dispatch_status})}'
      else
        printf '%s\n' "$line" | jq -C .
      fi
      echo
      if [[ -n "${EVENT_LOG:-}" ]]; then
        printf '%s\tcoproc-out\t%s\n' "$(perl -MTime::HiRes=time -e 'printf "%.3f", time')" \
          "$(printf '%s\n' "$line" | jq -r '(.contextual_triggers // {}) as $c | "\(.truck_id)\tbaseline \(.baseline_severity); \($c.weather_condition); \($c.cargo_type); \($c.dispatch_status)"')" \
          >> "$EVENT_LOG"
      fi
    done
