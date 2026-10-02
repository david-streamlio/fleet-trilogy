#!/usr/bin/env bash
# deploy/windows/simulator.sh -- fleet-simulator driving the demo's traffic,
# for the one Terminal.app window in the manual multi-window Edge Triage
# Pipeline demo that exists to generate load, not for the audience --
# deploy/record-demo.sh never includes this window in the recorded region.
#
# Uses the checked-in deploy/demo-scenario.env, same as deploy/demo.sh, plus
# a warmup period (calm telemetry before the incident ramps up, see
# fleet_simulator/cli.py's --warmup-ticks) so the output windows have
# something normal-looking on screen before the recording's interesting
# part starts.
#
# Usage:
#   ./deploy/windows/simulator.sh [broker-url] [rate]
#
# [rate] overrides demo-scenario.env's RATE (events/sec) -- e.g. a slower
# rate for a recording, so each pretty-printed JSON message is readable
# before the next one arrives. Optional WARMUP_TICKS env var overrides the
# warmup length (default 25).
set -uo pipefail

WINDOWS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${WINDOWS_DIR}/../.." && pwd)"
SCENARIO_FILE="${REPO_ROOT}/deploy/demo-scenario.env"

BROKER_URL="${1:-pulsar://localhost:6650}"
RATE_OVERRIDE="${2:-}"

printf '\033]0;Fleet Simulator (Generates Truck Telemetry)\007'

# shellcheck source=../demo-scenario.env
. "$SCENARIO_FILE"
RATE="${RATE_OVERRIDE:-$RATE}"

cd "$REPO_ROOT"
uv run fleet-simulate --service-url "$BROKER_URL" \
  --fleet-size "${FLEET_SIZE}" \
  --incident-corridor "${INCIDENT_CORRIDOR}" \
  --incident-trucks "${INCIDENT_TRUCKS}" \
  --seed "${SEED}" \
  --rate "${RATE}" \
  --duration "${DURATION}" \
  --warmup-ticks "${WARMUP_TICKS:-25}"
