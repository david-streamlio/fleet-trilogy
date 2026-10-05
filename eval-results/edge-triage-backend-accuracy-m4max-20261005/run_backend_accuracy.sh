#!/usr/bin/env bash
# Backend accuracy check (2026-10-05): does llama-cpp-python (in-process) decide differently from
# llama-server on the Edge Triage escalation scenarios? Found on the Pi 4: in-process + event-last
# answered "lower" on all 3 benign calls (expected "hold"); llama-server answered "hold".
# Both backends on the M4 Max CPU (no GPU), both prompt orders, a different event per call,
# --model-eval-runs 15 (15 format + 45 escalation calls, 15 per scenario), default 12 threads.
set -uo pipefail
cd "$1" || exit 1
OUT="$2"
export LLM_BINARY_PATH_PHI35_MINI="$HOME/tools/llama.cpp-v0.5.0/build/bin/llama-completion"
for prompt in default event-last; do
  for backend in server inprocess; do
    label="${backend}_${prompt}"
    if [ "$backend" = server ]; then extra=(--model-backend server --model-server-args "-np 1 --cache-ram 0 -dev none -ngl 0"); else extra=(--model-backend inprocess --model-gpu-layers 0); fi
    before=$(ls -1 eval-results/ | sort)
    uv run --no-sync pytest tests/model/test_compare_edge_triage_models.py -m model -s -q --only-model-ids phi-3.5-mini-instruct-q4km \
      --model-eval-runs 15 --vary-events --triage-prompt "$prompt" "${extra[@]}" < /dev/null > "$OUT/pytest_$label.log" 2>&1
    echo "$label exit=$? $(comm -13 <(echo "$before") <(ls -1 eval-results/ | sort) | tr '\n' ' ')" | tee -a "$OUT/artifacts.txt"
  done
done
