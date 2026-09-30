#!/usr/bin/env bash
# The single script that runs Talk 1's "See It Running" demo end-to-end, so
# the recording (talks/talk1-edge-intelligence/TODO-DEMO-RECORDING.md) can be
# repeated identically.
#
# This wires up FLOW B (coprocessor -> LLM triage -> uplink gate), not
# run_tier1_localrun.sh's single-stage EdgeEnrichmentFunction: Tier 1 has no
# co-processor gate, no severity escalation, and no local-only topic, so it
# cannot produce the "raised to high and uplinked" + "stays local" pair the
# recording needs. See deploy/README.md's Flow B section.
#
# Usage:
#   ./deploy/demo.sh [broker-url] [--simulator-host HOST]
#
#   broker-url         Default: pulsar://localhost:6650. This script and both
#                       Flow B functions run against this broker. When
#                       --simulator-host is NOT given, fleet-simulator also
#                       runs against this same URL, from this machine.
#   --simulator-host    Use when this script runs on the Pi with the broker
#                       colocated there (see TODO-DEMO-RECORDING.md: "Broker
#                       placement for this take: on the Pi") and
#                       fleet-simulator runs separately on the laptop
#                       (fleet-simulator never runs on the Pi itself -- see
#                       deploy/README.md). Give the Pi's LAN address, as
#                       reachable FROM the laptop. Instead of launching
#                       fleet-simulator, this script prints the exact command
#                       to run on the laptop and waits for Ctrl-C.
#
# Scenario: deploy/demo-scenario.env (checked in, fixed seed) -- truck-47 /
# I-95N, expected to produce both a card raised to "high" (uplinked) and at
# least one card lowered/held (stays on the local-only topic). See that
# file's comments for why, and for the honest caveat that the "raise" is a
# real model decision each run, not scripted for the recording.
#
# Requires on this machine: pulsar-admin, pulsar-client (both ship with a
# Pulsar distribution), docker (only if the broker needs to be started
# locally), curl, uv. Set LLM_BINARY_PATH / LLM_MODEL_PATH before running for
# real -- see run_flowb_triage_localrun.sh.
#
# Teardown: Ctrl-C always tears down every process this script started
# (never fleet-simulator on a separate laptop). Without --simulator-host,
# teardown also happens automatically once fleet-simulator finishes. A
# broker this script started via docker compose is left running (other demo
# takes may reuse it) -- stop it with `docker compose -f
# deploy/docker-compose.yml down` when done for the day.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SCENARIO_FILE="${SCRIPT_DIR}/demo-scenario.env"

BROKER_URL="pulsar://localhost:6650"
SIMULATOR_HOST=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --simulator-host)
      SIMULATOR_HOST="${2:?--simulator-host requires a value}"
      shift 2
      ;;
    --simulator-host=*)
      SIMULATOR_HOST="${1#*=}"
      shift
      ;;
    *)
      BROKER_URL="$1"
      shift
      ;;
  esac
done

for tool in pulsar-admin pulsar-client curl uv; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "[demo] required tool not found on PATH: ${tool}" >&2
    exit 1
  fi
done

BROKER_HOST="${BROKER_URL#pulsar://}"
BROKER_HOST="${BROKER_HOST%%:*}"
ADMIN_URL="http://${BROKER_HOST}:8080"

LOG_DIR="$(mktemp -d "${TMPDIR:-/tmp}/flowb-demo.XXXXXX")"
echo "[demo] broker: ${BROKER_URL}  admin: ${ADMIN_URL}"
echo "[demo] logs: ${LOG_DIR}"

PIDS=()
LAST_BG_PID=""

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  echo
  echo "[demo] tearing down..."
  if [[ ${#PIDS[@]} -gt 0 ]]; then
    for pid in "${PIDS[@]}"; do
      kill "$pid" >/dev/null 2>&1 || true
    done
    for pid in "${PIDS[@]}"; do
      wait "$pid" 2>/dev/null || true
    done
  fi
  echo "[demo] stopped. Full logs kept at ${LOG_DIR}"
  # Without an explicit exit here, a trap fired by Ctrl-C during the
  # `while true; do sleep 3600; done` wait loop (--simulator-host case) would
  # return control to that loop instead of ending the script.
  exit "$exit_code"
}
trap cleanup EXIT INT TERM

start_bg() {
  # start_bg <logfile> <command...> -- sets LAST_BG_PID, appends to PIDS
  local logfile="$1"
  shift
  ("$@" >"$logfile" 2>&1) &
  LAST_BG_PID=$!
  PIDS+=("$LAST_BG_PID")
}

start_labeled_tail() {
  # start_labeled_tail <label> <logfile> -- streams logfile to stdout, prefixed
  local label="$1" logfile="$2"
  : >"$logfile"
  (tail -n +1 -f "$logfile" 2>/dev/null | sed -u "s/^/[${label}] /") &
  PIDS+=("$!")
}

if [[ "$BROKER_HOST" == "localhost" || "$BROKER_HOST" == "127.0.0.1" ]]; then
  if ! curl -sf -o /dev/null "${ADMIN_URL}/admin/v2/clusters"; then
    echo "[demo] broker not reachable at ${ADMIN_URL}, starting via docker compose..."
    (cd "${REPO_ROOT}" && docker compose -f deploy/docker-compose.yml up -d)
    ready=""
    for _ in $(seq 1 30); do
      if curl -sf -o /dev/null "${ADMIN_URL}/admin/v2/clusters"; then
        ready="1"
        break
      fi
      sleep 1
    done
    if [[ -z "$ready" ]]; then
      echo "[demo] broker still not reachable after 30s, aborting" >&2
      exit 1
    fi
  fi
else
  if ! curl -sf -o /dev/null "${ADMIN_URL}/admin/v2/clusters"; then
    echo "[demo] broker not reachable at ${ADMIN_URL} -- start it there first (this script only auto-starts a LOCAL broker)" >&2
    exit 1
  fi
fi
echo "[demo] broker reachable."

echo "[co-processor] starting..."
start_bg "${LOG_DIR}/coprocessor.log" \
  "${SCRIPT_DIR}/run_flowb_coprocessor_localrun.sh" "${BROKER_URL}" "${ADMIN_URL}"
echo "[co-processor] launched (pid ${LAST_BG_PID}, log: ${LOG_DIR}/coprocessor.log)"

echo "[llm] starting..."
start_bg "${LOG_DIR}/triage.log" \
  "${SCRIPT_DIR}/run_flowb_triage_localrun.sh" "${BROKER_URL}" "${ADMIN_URL}"
echo "[llm] launched (pid ${LAST_BG_PID}, log: ${LOG_DIR}/triage.log)"

echo "[demo] waiting ${FUNCTION_STARTUP_GRACE_SECONDS:-6}s for both functions to come up..."
sleep "${FUNCTION_STARTUP_GRACE_SECONDS:-6}"

# Topic names come from fleet_telemetry_model.topics, not hardcoded here, so
# this script can't drift from the single source of truth every function and
# test in the repo already uses.
ENRICHMENT_CARDS_TOPIC="$(cd "${REPO_ROOT}" && uv run python -c \
  'from fleet_telemetry_model import ENRICHMENT_CARDS_TOPIC as t; print(t)')"
LOCAL_TRIAGE_TOPIC="$(cd "${REPO_ROOT}" && uv run python -c \
  'from fleet_telemetry_model import LOCAL_TRIAGE_TOPIC as t; print(t)')"

start_bg "${LOG_DIR}/uplink-raw.log" \
  pulsar-client --url "${BROKER_URL}" consume "${ENRICHMENT_CARDS_TOPIC}" \
    -s "demo-uplink-$$" -n 0 -p Latest
start_labeled_tail "uplink" "${LOG_DIR}/uplink-raw.log"

start_bg "${LOG_DIR}/local-raw.log" \
  pulsar-client --url "${BROKER_URL}" consume "${LOCAL_TRIAGE_TOPIC}" \
    -s "demo-local-$$" -n 0 -p Latest
start_labeled_tail "local" "${LOG_DIR}/local-raw.log"

# shellcheck source=demo-scenario.env
. "${SCENARIO_FILE}"
FLEET_SIM_ARGS=(
  --fleet-size "${FLEET_SIZE}"
  --incident-corridor "${INCIDENT_CORRIDOR}"
  --incident-trucks "${INCIDENT_TRUCKS}"
  --seed "${SEED}"
  --rate "${RATE}"
  --duration "${DURATION}"
)

if [[ -n "$SIMULATOR_HOST" ]]; then
  echo "[demo] broker + Flow B functions are up here, reachable from the laptop at ${SIMULATOR_HOST}."
  echo "[demo] On the LAPTOP, run:"
  echo "  uv run fleet-simulate --service-url pulsar://${SIMULATOR_HOST}:6650 ${FLEET_SIM_ARGS[*]}"
  echo "[demo] Watching enrichment-cards / triage-local-only below. Press Ctrl-C here when the take is done."
  while true; do
    sleep 3600
  done
else
  echo "[demo] running fleet-simulator against ${BROKER_URL}..."
  (cd "${REPO_ROOT}" && uv run fleet-simulate --service-url "${BROKER_URL}" "${FLEET_SIM_ARGS[@]}")
  echo "[demo] fleet-simulator finished. Watching a few more seconds for trailing cards..."
  sleep 5
fi
