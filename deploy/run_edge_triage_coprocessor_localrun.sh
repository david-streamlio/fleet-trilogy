#!/usr/bin/env bash
# Launch the Edge Triage Pipeline's first stage (talk1_edge_intelligence.
# coprocessor.TelemetryCoprocessorFunction) via `pulsar-admin functions
# localrun`, pointed at a configurable broker.
#
# Usage:
#   ./run_edge_triage_coprocessor_localrun.sh [service-url] [admin-url]
#
# Consumes the same truck-telemetry topic Flow A's Tier 1 function does, and
# emits the Edge Triage Pipeline's intermediate topic (fleet_telemetry_model.
# topics.TRIAGE_PAYLOADS_TOPIC) for run_edge_triage_llm_localrun.sh to
# consume. Purely cheap-math gating (is_probable_slowdown + an eta_slip_min
# magnitude window, see coprocessor.py) -- no LLM runtime involved at this
# stage.
#
# Optional COPROCESSOR_MIN_ETA_SLIP_MIN / COPROCESSOR_MAX_ETA_SLIP_MIN env vars
# override the eta_slip_min gate bounds (defaults: 3.0 / 60.0).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# `pulsar-admin functions localrun` forks the function's actual Python side
# by shelling out to a bare `python3`, resolved via *this* process's PATH --
# it has no idea the project uses uv/.venv. Without this, it silently finds
# macOS's system python3 instead, which doesn't have `pulsar-client`
# installed; the subprocess then dies on `import pulsar` before it ever logs
# anything, and the parent LocalRunner JVM just sits there forever retrying.
export PATH="${REPO_ROOT}/.venv/bin:${PATH}"

# Title this terminal window/tab so it's identifiable in the manual
# multi-terminal demo (deploy/RUNBOOK-EDGE-TRIAGE-MANUAL.md) once startup
# logs have scrolled by. \033]0;...\007 is the standard xterm OSC title
# escape, supported by Terminal.app and iTerm2.
printf '\033]0;Coprocessor Function (Cheap-Math Gate)\007'

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
