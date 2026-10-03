#!/usr/bin/env bash
# deploy/talk3-windows/tier2.sh -- Tier 2's GlobalSynthesisFunction via
# `pulsar-admin functions localrun` (deploy/run_tier2_localrun.sh), with the real
# Gemma-3-4B-it model, for the one Talk 3 demo window that exists for
# troubleshooting, not the audience -- deploy/record-talk3-demo.sh never records it.
#
# Usage:
#   ./deploy/talk3-windows/tier2.sh [broker-url] [admin-url]
#
# Defaults to this Mac's ~/tools paths (models.toml's dev-machine defaults);
# override with LLM_BINARY_PATH / LLM_MODEL_PATH. LLM_EXTRA_ARGS defaults to
# Gemma's models.toml flag (-no-cnv), and CORRIDOR_THRESHOLD to 3 -- one card per
# truck in deploy/talk3-demo-cards.jsonl, so the three trucks become one incident.
set -uo pipefail

WINDOWS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "${WINDOWS_DIR}/.." && pwd)"

BROKER_URL="${1:-pulsar://localhost:6650}"
ADMIN_URL="${2:-http://localhost:8080}"

printf '\033]0;Setup: Tier 2 Global Synthesis Function (log)\007'

export LLM_BINARY_PATH="${LLM_BINARY_PATH:-$HOME/tools/llama.cpp/build/bin/llama-completion}"
export LLM_MODEL_PATH="${LLM_MODEL_PATH:-$HOME/tools/models/gemma-3-4b-it-GGUF/gemma-3-4b-it-Q4_K_M.gguf}"
export LLM_EXTRA_ARGS="${LLM_EXTRA_ARGS:--no-cnv}"
export CORRIDOR_THRESHOLD="${CORRIDOR_THRESHOLD:-3}"

exec "${DEPLOY_DIR}/run_tier2_localrun.sh" "$BROKER_URL" "$ADMIN_URL"
