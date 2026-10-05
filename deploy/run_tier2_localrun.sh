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
# Requires pulsar-admin (ships with a Pulsar distribution) and LLM_MODEL_PATH pointing
# at a GGUF model on this machine (plus LLM_BINARY_PATH for LLM_BACKEND=subprocess).
# Set LLM_MOCK=1 to run the function in mock mode without an LLM runtime.
# Optional: LLM_BACKEND (`inprocess`, the default since 2026-10-05: llama-cpp-python
# inside the Function, model loaded once; or `subprocess`: a llama.cpp process per
# call), LLM_EXTRA_ARGS (subprocess only: the model's one-shot flags from models.toml,
# e.g. "-no-cnv" for Gemma-3-4B-it), CORRIDOR_THRESHOLD (cards per corridor before
# synthesizing; the function's default is 2), LLM_THREADS (default 4, 1 = one CPU
# core), LLM_TIMEOUT_SECONDS (per call; default 60) and LLM_GPU_LAYERS (inprocess
# only; default 0 = CPU only) -- all passed through --user-config.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
# localrun's Python runtime must import this workspace's packages, same as the
# Talk 1 localrun scripts.
export PATH="${REPO_ROOT}/.venv/bin:${PATH}"

SERVICE_URL="${1:-pulsar://localhost:6650}"
ADMIN_URL="${2:-http://localhost:8080}"

USER_CONFIG=$(cat <<EOF
{"llm_binary_path": "${LLM_BINARY_PATH:-}", "llm_model_path": "${LLM_MODEL_PATH:-}", "llm_extra_args": "${LLM_EXTRA_ARGS:-}", "corridor_threshold": "${CORRIDOR_THRESHOLD:-}", "threads": "${LLM_THREADS:-}", "timeout_seconds": "${LLM_TIMEOUT_SECONDS:-}", "llm_backend": "${LLM_BACKEND:-}", "llm_gpu_layers": "${LLM_GPU_LAYERS:-}"}
EOF
)

pulsar-admin --admin-url "${ADMIN_URL}" functions localrun \
  --py "${REPO_ROOT}/talks/talk3-pulsar-speaks-english/src/talk3_pulsar_speaks_english/function.py" \
  --classname talk3_pulsar_speaks_english.function.GlobalSynthesisFunction \
  --inputs persistent://public/default/enrichment-cards \
  --output persistent://public/default/incidents \
  --broker-service-url "${SERVICE_URL}" \
  --user-config "${USER_CONFIG}"
