#!/usr/bin/env bash
# deploy/talk3-windows/decision.sh -- Tier 2's output (incidents topic), split the
# way the talk explains it: the decision plain code made (scope, trucks, reroute),
# then the sentence the model wrote for it. One of the 3 output windows
# deploy/record-talk3-demo.sh records.
#
# Usage:
#   ./deploy/talk3-windows/decision.sh [broker-url]
set -uo pipefail

BROKER_URL="${1:-pulsar://localhost:6650}"

printf '\033]0;Tier 2: Decision (Code) + Wording (LLM)\007'
# Clear screen + scrollback: the recorder captures this window's content area, so
# Terminal's "Last login" banner and the echoed launch command must not be on it.
printf '\033[2J\033[3J\033[H'

pulsar-client --url "$BROKER_URL" consume persistent://public/default/incidents \
  -s talk3-demo-decision -n 0 -p Latest 2>&1 \
  | perl -pe 'BEGIN{$|=1} s/\e\[[0-9;]*m//g' \
  | grep --line-buffered 'content:' \
  | sed -u 's/^.*content://' \
  | while IFS= read -r line; do
      echo "[Decided by code]"
      printf '%s\n' "$line" | jq -C '{corridor, scope, affected_truck_ids, reroute_recommended, reroute_detail}'
      echo
      echo "[Worded by the LLM]"
      printf '%s\n' "$line" | jq -r .spoken_warning | fold -s -w 70
      echo
    done
