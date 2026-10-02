#!/usr/bin/env bash
# deploy/windows/local_only.sh -- cards the uplink gate held on the truck
# (triage-local-only topic), pretty-printed, for one of the 4 output windows
# deploy/record-demo.sh records.
#
# Usage:
#   ./deploy/windows/local_only.sh [broker-url]
set -uo pipefail

BROKER_URL="${1:-pulsar://localhost:6650}"

printf '\033]0;Triaged Events Held on the Truck\007'

pulsar-client --url "$BROKER_URL" consume persistent://public/default/triage-local-only \
  -s manual-demo-local -n 0 -p Latest 2>&1 \
  | perl -pe 'BEGIN{$|=1} s/\e\[[0-9;]*m//g' \
  | grep --line-buffered 'content:' \
  | sed -u 's/^.*content://' \
  | while IFS= read -r line; do echo "[local-llm]"; printf '%s\n' "$line" | jq -C .; echo; done
