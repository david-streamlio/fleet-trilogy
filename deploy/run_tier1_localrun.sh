#!/usr/bin/env bash
# Launch the Tier 1 edge function (talk1_edge_intelligence.function.EdgeEnrichmentFunction)
# via `pulsar-admin functions localrun`, pointed at a configurable broker.
#
# Usage:
#   ./run_tier1_localrun.sh [service-url] [admin-url]
#
# Defaults point at a broker on the same machine (laptop dev with docker-compose up).
# On stage, run this ON THE PI and pass the real broker's addresses:
#   ./run_tier1_localrun.sh pulsar://<broker-host>:6650 http://<broker-host>:8080
#
# Requires pulsar-admin (ships with a Pulsar distribution) and LLM_MODEL_PATH pointing
# at a GGUF model on this machine. The model runs inside the Function (llama-cpp-python,
# loaded once; LLM_THREADS default 4, LLM_GPU_LAYERS default 0 = CPU only) unless
# LLM_BACKEND=subprocess, which runs LLM_BINARY_PATH (llama-completion) once per call.
# Set LLM_MOCK=1 to run the function in mock mode without an LLM runtime.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

SERVICE_URL="${1:-pulsar://localhost:6650}"
ADMIN_URL="${2:-http://localhost:8080}"

USER_CONFIG=$(cat <<EOF
{"llm_backend": "${LLM_BACKEND:-}", "llm_binary_path": "${LLM_BINARY_PATH:-}", "llm_model_path": "${LLM_MODEL_PATH:-}", "threads": "${LLM_THREADS:-}", "llm_gpu_layers": "${LLM_GPU_LAYERS:-}"}
EOF
)

pulsar-admin --admin-url "${ADMIN_URL}" functions localrun \
  --py "${REPO_ROOT}/talks/talk1-edge-intelligence/src/talk1_edge_intelligence/function.py" \
  --classname talk1_edge_intelligence.function.EdgeEnrichmentFunction \
  --inputs persistent://public/default/truck-telemetry \
  --output persistent://public/default/enrichment-cards \
  --broker-service-url "${SERVICE_URL}" \
  --user-config "${USER_CONFIG}"
