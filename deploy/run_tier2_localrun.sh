#!/usr/bin/env bash
# Launch the Tier 2 cloud function (talk3_pulsar_speaks_english.function.GlobalSynthesisFunction)
# via `pulsar-admin functions localrun`, pointed at a configurable broker.
#
# Usage:
#   ./run_tier2_localrun.sh [service-url] [admin-url]
#
# Defaults point at a broker on the same machine (laptop dev with docker-compose up).
# Tier 2 is cloud-side, not Pi-side — run this on whatever host is standing in for
# "the cloud" in the demo (a laptop, a VM, a real cloud box), pointed at the same
# broker Tier 1's enrichment cards are published to:
#   ./run_tier2_localrun.sh pulsar://<broker-host>:6650 http://<broker-host>:8080
#
# Requires pulsar-admin (ships with a Pulsar distribution) and LLM_BINARY_PATH /
# LLM_MODEL_PATH pointing at a built llama.cpp-family binary and model on this machine.
# Unset both (or set LLM_MOCK=1) to run the function in mock mode without an LLM runtime.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

SERVICE_URL="${1:-pulsar://localhost:6650}"
ADMIN_URL="${2:-http://localhost:8080}"

USER_CONFIG=$(cat <<EOF
{"llm_binary_path": "${LLM_BINARY_PATH:-}", "llm_model_path": "${LLM_MODEL_PATH:-}"}
EOF
)

pulsar-admin --admin-url "${ADMIN_URL}" functions localrun \
  --py "${REPO_ROOT}/talks/talk3-pulsar-speaks-english/src/talk3_pulsar_speaks_english/function.py" \
  --classname talk3_pulsar_speaks_english.function.GlobalSynthesisFunction \
  --inputs persistent://public/default/enrichment-cards \
  --output persistent://public/default/incidents \
  --broker-service-url "${SERVICE_URL}" \
  --user-config "${USER_CONFIG}"
