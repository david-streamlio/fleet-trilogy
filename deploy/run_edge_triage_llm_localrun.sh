#!/usr/bin/env bash
# Launch the Edge Triage Pipeline's second stage (talk1_edge_intelligence.
# triage_function.LlmTriageFunction) via `pulsar-admin functions localrun`,
# pointed at a configurable broker.
#
# Usage:
#   ./run_edge_triage_llm_localrun.sh [service-url] [admin-url]
#
# Consumes the Edge Triage Pipeline's intermediate topic (produced by
# run_edge_triage_coprocessor_localrun.sh) and applies the uplink gate
# (slides 20-21, talks/talk1-edge-intelligence/TODO-TRIAGE-UPLINK-GATE.md):
# only cards whose final severity meets uplink_min_severity (default "high")
# are returned as this function's output (--output enrichment-cards, the
# same topic Flow A's Tier 1 function writes to); everything else is
# published directly by the function to the local-only topic
# (fleet_telemetry_model.topics.LOCAL_TRIAGE_TOPIC) instead, never leaving
# this broker.
#
# Requires LLM_BINARY_PATH / LLM_MODEL_PATH pointing at a built llama.cpp-
# family binary and model on this machine. Optional UPLINK_MIN_SEVERITY
# overrides the gate threshold (default "high" -- one of low/medium/high).
# Optional LOG_TOPIC publishes this function's logger output (including
# build_card's LLM_INPUT_BEGIN/END prompt dump) to a Pulsar topic via
# --log-topic, since Pulsar's python-instance logger otherwise writes only to
# a per-function log file on disk, never to this script's own stdout -- see
# deploy/demo-tmux.sh's llm-input pane, which depends on this.
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
printf '\033]0;LLM Triage Function (Local Model)\007'

SERVICE_URL="${1:-pulsar://localhost:6650}"
ADMIN_URL="${2:-http://localhost:8080}"

USER_CONFIG=$(cat <<EOF
{"llm_binary_path": "${LLM_BINARY_PATH:-}", "llm_model_path": "${LLM_MODEL_PATH:-}", "uplink_min_severity": "${UPLINK_MIN_SEVERITY:-}"}
EOF
)

LOG_TOPIC_ARGS=()
if [[ -n "${LOG_TOPIC:-}" ]]; then
  LOG_TOPIC_ARGS=(--log-topic "${LOG_TOPIC}")
fi

pulsar-admin --admin-url "${ADMIN_URL}" functions localrun \
  --py "${REPO_ROOT}/talks/talk1-edge-intelligence/src/talk1_edge_intelligence/triage_function.py" \
  --classname talk1_edge_intelligence.triage_function.LlmTriageFunction \
  --inputs persistent://public/default/triage-payloads \
  --output persistent://public/default/enrichment-cards \
  --broker-service-url "${SERVICE_URL}" \
  --user-config "${USER_CONFIG}" \
  ${LOG_TOPIC_ARGS[@]+"${LOG_TOPIC_ARGS[@]}"}
