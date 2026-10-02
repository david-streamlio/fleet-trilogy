#!/usr/bin/env bash
# deploy/windows/setup.sh -- combined coprocessor + LLM triage log, for the
# one Terminal.app window in the manual multi-window Edge Triage Pipeline
# demo (deploy/record-demo.sh, deploy/RUNBOOK-EDGE-TRIAGE-MANUAL.md) that
# exists for troubleshooting, not for the audience -- record-demo.sh never
# includes this window in the recorded region.
#
# Usage:
#   ./deploy/windows/setup.sh [broker-url] [admin-url]
#
# Requires LLM_BINARY_PATH / LLM_MODEL_PATH, same as
# run_edge_triage_llm_localrun.sh (see that script's own header).
set -uo pipefail

WINDOWS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "${WINDOWS_DIR}/.." && pwd)"

BROKER_URL="${1:-pulsar://localhost:6650}"
ADMIN_URL="${2:-http://localhost:8080}"

printf '\033]0;Setup: Coprocessor + LLM Triage (combined log)\007'

LOG="$(mktemp -t edge-triage-setup-log)"
cleanup() {
  kill -TERM -- -"${COPRO_PID:-}" -"${TRIAGE_PID:-}" 2>/dev/null
  pkill -f 'talk1_edge_intelligence\.coprocessor\.TelemetryCoprocessorFunction' 2>/dev/null
  pkill -f 'talk1_edge_intelligence\.triage_function\.LlmTriageFunction' 2>/dev/null
  pkill -f 'llama-server' 2>/dev/null
}
trap cleanup EXIT INT TERM

"${DEPLOY_DIR}/run_edge_triage_coprocessor_localrun.sh" "$BROKER_URL" "$ADMIN_URL" \
  > >(sed -u 's/^/[coprocessor] /' >> "$LOG") 2>&1 &
COPRO_PID=$!
"${DEPLOY_DIR}/run_edge_triage_llm_localrun.sh" "$BROKER_URL" "$ADMIN_URL" \
  > >(sed -u 's/^/[triage] /' >> "$LOG") 2>&1 &
TRIAGE_PID=$!

echo "combined log: $LOG"
tail -f "$LOG"
