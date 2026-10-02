#!/usr/bin/env bash
# deploy/windows/telemetry.sh -- raw truck-telemetry input, pretty-printed,
# for one of the 4 output windows deploy/record-demo.sh records.
#
# Usage:
#   ./deploy/windows/telemetry.sh [broker-url]
set -uo pipefail

BROKER_URL="${1:-pulsar://localhost:6650}"

printf '\033]0;Telemetry Data From Truck Sensors\007'

pulsar-client --url "$BROKER_URL" consume persistent://public/default/truck-telemetry \
  -s manual-demo-telemetry -n 0 -p Latest 2>&1 \
  | perl -pe 'BEGIN{$|=1} s/\e\[[0-9;]*m//g' \
  | grep --line-buffered 'content:' \
  | sed -u 's/^.*content://' \
  | while IFS= read -r line; do echo "[Truck Telemetry]"; printf '%s\n' "$line" | jq -C .; echo; done
