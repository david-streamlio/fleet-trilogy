#!/usr/bin/env bash
# deploy/windows/uplink.sh -- cards the uplink gate escalated to the control
# center (enrichment-cards topic), pretty-printed, for one of the 4 output
# windows deploy/record-demo.sh records.
#
# Usage:
#   ./deploy/windows/uplink.sh [broker-url] [--compact | --compact=off]
#
# --compact shows truck_id, escalation, severity and the first sentence of
# risk_synthesis, cut to the window's width so nothing wraps; --compact=off (the
# default) prints the full JSON. EVENT_LOG: see telemetry.sh.
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

TITLE='Triaged Events Sent to Control Center'
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

# First sentence of risk_synthesis, at most $max characters (… when cut).
CARD_FILTER='def first_sentence: (capture("^(?<s>.+?[.!?])(\\s|$)").s? // .);
  def fit($n): if length > $n then .[0:($n - 1)] + "…" else . end;
  ((.risk_synthesis // "") | first_sentence | fit($max)) as $why'

pulsar-client --url "$BROKER_URL" consume persistent://public/default/enrichment-cards \
  -s manual-demo-uplink -n 0 -p Latest 2>&1 \
  | perl -pe 'BEGIN{$|=1} s/\e\[[0-9;]*m//g' \
  | grep --line-buffered 'content:' \
  | sed -u 's/^.*content://' \
  | while IFS= read -r line; do
      echo "[Uplinked Card]"
      # The pretty-printed line is `  "risk_synthesis": "…"`: 23 columns around the text.
      cols="$( { stty size < /dev/tty; } 2>/dev/null | awk '{print $2}')"
      max=$(( ${cols:-100} - 24 ))
      if [[ -n "$COMPACT" ]]; then
        printf '%s\n' "$line" | jq -C --argjson max "$max" "${CARD_FILTER} | {truck_id, escalation, severity, risk_synthesis: \$why}"
      else
        printf '%s\n' "$line" | jq -C .
      fi
      echo
      if [[ -n "${EVENT_LOG:-}" ]]; then
        printf '%s\tuplink\t%s\n' "$(perl -MTime::HiRes=time -e 'printf "%.3f", time')" \
          "$(printf '%s\n' "$line" | jq -r --argjson max 200 "${CARD_FILTER} | \"\(.truck_id)\t\(.escalation) → \(.severity): \(\$why)\"")" \
          >> "$EVENT_LOG"
      fi
    done
