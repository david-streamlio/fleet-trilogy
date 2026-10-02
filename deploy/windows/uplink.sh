#!/usr/bin/env bash
# deploy/windows/uplink.sh -- cards the uplink gate escalated to the control
# center (enrichment-cards topic), pretty-printed, for one of the 4 output
# windows deploy/record-demo.sh records.
#
# Usage:
#   ./deploy/windows/uplink.sh [broker-url]
set -uo pipefail

BROKER_URL="${1:-pulsar://localhost:6650}"

printf '\033]0;Triaged Events Sent to Control Center\007'

pulsar-client --url "$BROKER_URL" consume persistent://public/default/enrichment-cards \
  -s manual-demo-uplink -n 0 -p Latest 2>&1 \
  | perl -pe 'BEGIN{$|=1} s/\e\[[0-9;]*m//g' \
  | grep --line-buffered 'content:' \
  | sed -u 's/^.*content://' \
  | while IFS= read -r line; do echo "[Uplinked Card]"; printf '%s\n' "$line" | jq -C .; echo; done
