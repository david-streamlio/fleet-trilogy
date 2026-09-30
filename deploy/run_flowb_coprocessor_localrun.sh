#!/usr/bin/env bash
# Launch Flow B's first stage (talk1_edge_intelligence.coprocessor.
# TelemetryCoprocessorFunction) via `pulsar-admin functions localrun`, pointed
# at a configurable broker.
#
# Usage:
#   ./run_flowb_coprocessor_localrun.sh [service-url] [admin-url]
#
# Consumes the same truck-telemetry topic Flow A's Tier 1 function does, and
# emits Flow B's intermediate topic (fleet_telemetry_model.topics.
# TRIAGE_PAYLOADS_TOPIC) for run_flowb_triage_localrun.sh to consume. Purely
# cheap-math gating (is_probable_slowdown + an eta_slip_min magnitude window,
# see coprocessor.py) -- no LLM runtime involved at this stage.
#
# Optional COPROCESSOR_MIN_ETA_SLIP_MIN / COPROCESSOR_MAX_ETA_SLIP_MIN env vars
# override the eta_slip_min gate bounds (defaults: 3.0 / 60.0).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

SERVICE_URL="${1:-pulsar://localhost:6650}"
ADMIN_URL="${2:-http://localhost:8080}"

USER_CONFIG=$(cat <<EOF
{"min_eta_slip_min": "${COPROCESSOR_MIN_ETA_SLIP_MIN:-}", "max_eta_slip_min": "${COPROCESSOR_MAX_ETA_SLIP_MIN:-}"}
EOF
)

pulsar-admin --admin-url "${ADMIN_URL}" functions localrun \
  --py "${REPO_ROOT}/talks/talk1-edge-intelligence/src/talk1_edge_intelligence/coprocessor.py" \
  --classname talk1_edge_intelligence.coprocessor.TelemetryCoprocessorFunction \
  --inputs persistent://public/default/truck-telemetry \
  --output persistent://public/default/triage-payloads \
  --broker-service-url "${SERVICE_URL}" \
  --user-config "${USER_CONFIG}"
