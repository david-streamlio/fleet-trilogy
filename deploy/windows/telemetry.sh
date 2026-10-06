#!/usr/bin/env bash
# deploy/windows/telemetry.sh -- raw truck-telemetry input, pretty-printed,
# for one of the 4 output windows deploy/record-demo.sh records.
#
# Usage:
#   ./deploy/windows/telemetry.sh [broker-url] [--compact | --compact=off]
#
# --compact (deploy/record-demo.sh's spotlight default) shows only the six
# fields the talk points at, plus a dim "… +N more fields" line, so a message
# fits in ~12 rows at the recording's 28pt font; --compact=off (the default)
# prints the full 26-line JSON, for troubleshooting.
# EVENT_LOG=<file>, when set, gets one "epoch<TAB>role<TAB>truck_id<TAB>summary"
# line per message as it's printed -- record-demo.sh's spotlight edit switches
# windows on those times.
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

TITLE='Telemetry Data From Truck Sensors'
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

pulsar-client --url "$BROKER_URL" consume persistent://public/default/truck-telemetry \
  -s manual-demo-telemetry -n 0 -p Latest 2>&1 \
  | perl -pe 'BEGIN{$|=1} s/\e\[[0-9;]*m//g' \
  | grep --line-buffered 'content:' \
  | sed -u 's/^.*content://' \
  | while IFS= read -r line; do
      echo "[Truck Telemetry]"
      if [[ -n "$COMPACT" ]]; then
        printf '%s\n' "$line" | jq -C '{truck_id, speed_mph: ((.speed_mph // 0) * 10 | round / 10), brake_events, downshift_events, peak_deceleration_g: ((.peak_deceleration_g // 0) * 100 | round / 100), abs_engaged}'
        more="$(printf '%s\n' "$line" | jq -r 'keys | length - 6')"
        printf '\033[2m… +%s more fields\033[0m\n' "$more"
      else
        printf '%s\n' "$line" | jq -C .
      fi
      echo
      if [[ -n "${EVENT_LOG:-}" ]]; then
        printf '%s\ttelemetry\t%s\n' "$(perl -MTime::HiRes=time -e 'printf "%.3f", time')" \
          "$(printf '%s\n' "$line" | jq -r '"\(.truck_id)\t\((.speed_mph // 0) * 10 | round / 10) mph, \(.brake_events) brakes, \(.downshift_events) downshifts"')" \
          >> "$EVENT_LOG"
      fi
    done
