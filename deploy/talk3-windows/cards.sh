#!/usr/bin/env bash
# deploy/talk3-windows/cards.sh -- enrichment cards arriving from the edge
# (enrichment-cards topic, Tier 2's input), pretty-printed, for one of the 3
# output windows deploy/record-talk3-demo.sh records.
#
# Usage:
#   ./deploy/talk3-windows/cards.sh [broker-url]
set -uo pipefail

BROKER_URL="${1:-pulsar://localhost:6650}"

printf '\033]0;Cards Arriving From the Fleet\007'
# Clear screen + scrollback: the recorder captures this window's content area, so
# Terminal's "Last login" banner and the echoed launch command must not be on it.
printf '\033[2J\033[3J\033[H'

pulsar-client --url "$BROKER_URL" consume persistent://public/default/enrichment-cards \
  -s talk3-demo-cards -n 0 -p Latest 2>&1 \
  | perl -pe 'BEGIN{$|=1} s/\e\[[0-9;]*m//g' \
  | grep --line-buffered 'content:' \
  | sed -u 's/^.*content://' \
  | while IFS= read -r line; do
      echo "[Card from $(printf '%s' "$line" | jq -r .truck_id)]"
      printf '%s\n' "$line" | jq -C .
      echo
    done
