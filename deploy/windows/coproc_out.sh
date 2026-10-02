#!/usr/bin/env bash
# deploy/windows/coproc_out.sh -- coprocessor's probable-slowdown output
# (triage-payloads topic), pretty-printed, for one of the 4 output windows
# deploy/record-demo.sh records.
#
# Usage:
#   ./deploy/windows/coproc_out.sh [broker-url]
set -uo pipefail

BROKER_URL="${1:-pulsar://localhost:6650}"

printf '\033]0;Probable-Slowdown Events Forwarded to Triage\007'

pulsar-client --url "$BROKER_URL" consume persistent://public/default/triage-payloads \
  -s manual-demo-coproc -n 0 -p Latest 2>&1 \
  | perl -pe 'BEGIN{$|=1} s/\e\[[0-9;]*m//g' \
  | grep --line-buffered 'content:' \
  | sed -u 's/^.*content://' \
  | while IFS= read -r line; do echo "[Flagged Event]"; printf '%s\n' "$line" | jq -C .; echo; done
