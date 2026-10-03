#!/usr/bin/env bash
# deploy/talk3-windows/replay.sh -- publishes the checked-in, fixed edge cards
# (deploy/talk3-demo-cards.jsonl) to Tier 2's input topic, one every few seconds,
# for the one Talk 3 demo window that drives the take rather than being shown --
# deploy/record-talk3-demo.sh never records it.
#
# Only the INPUT is fixed: three trucks' cards on I-95N, disclosed on stage as
# replayed edge output. Everything downstream is live on every take -- Tier 2's
# plain-code scope/reroute decision, Gemma's wording, Piper's voice. (Live
# upstream from Talk 1's Edge Triage Pipeline isn't used: only truck-47 has trip
# context that escalates past the "high" uplink gate, so Tier 2 would only ever
# see one truck -- never the corridor-wide reroute.)
#
# Usage:
#   ./deploy/talk3-windows/replay.sh [broker-url] [seconds-between-cards]
set -uo pipefail

WINDOWS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CARDS_FILE="$(cd "${WINDOWS_DIR}/.." && pwd)/talk3-demo-cards.jsonl"

BROKER_URL="${1:-pulsar://localhost:6650}"
INTERVAL="${2:-3}"

printf '\033]0;Card Replay (Drives the Take)\007'

CARD_TMP="$(mktemp -t talk3-card)"
trap 'rm -f "$CARD_TMP"' EXIT
while IFS= read -r card; do
  [[ -z "$card" ]] && continue
  # -f (file contents = exactly one message), not -m: pulsar-client splits -m on
  # commas by default, and -s takes a REGEX -- `-s '|'` split every card into
  # ~180 one-character messages on the first test run.
  printf '%s' "$card" > "$CARD_TMP"
  pulsar-client --url "$BROKER_URL" produce persistent://public/default/enrichment-cards \
    -f "$CARD_TMP" > /dev/null 2>&1 \
    && echo "$(date +%T) published card from $(printf '%s' "$card" | jq -r .truck_id)" \
    || echo "$(date +%T) FAILED to publish: $card"
  sleep "$INTERVAL"
done < "$CARDS_FILE"
echo "replay done"
