#!/bin/bash
# One-off launcher (2026-10-04): fetch the four models round 3 needs that this MacBook lacks,
# then run deploy/aws-phone-proxies/scripts/bench_round3_m4max.sh, detached from Claude's tool.
set -uo pipefail
REPO=/Users/david.kjerrumgaard/clone-zone/davidkj-datadog/fleet-trilogy
M=$HOME/tools/models
while read -r repo dir file; do
  mkdir -p "$M/$dir"; [ -f "$M/$dir/$file" ] && { echo "have $file"; continue; }
  curl -fL --retry 5 --retry-delay 5 -sS -o "$M/$dir/$file.part" "https://huggingface.co/$repo/resolve/main/$file" \
    && mv "$M/$dir/$file.part" "$M/$dir/$file" && echo "got $file $(stat -f %z "$M/$dir/$file")"
done <<LIST
unsloth/gemma-3-12b-it-GGUF gemma-3-12b-it-GGUF gemma-3-12b-it-Q4_K_M.gguf
unsloth/gemma-4-12b-it-GGUF gemma-4-12b-it-GGUF gemma-4-12b-it-Q4_K_M.gguf
unsloth/Qwen3-14B-GGUF Qwen3-14B-GGUF Qwen3-14B-Q4_K_M.gguf
unsloth/Qwen3.5-9B-GGUF Qwen3.5-9B-GGUF Qwen3.5-9B-Q4_K_M.gguf
LIST
echo "downloads done $(date -u +%H:%M:%SZ)"
cd "$REPO" && GATE_PM=/tmp/m4max-powermetrics-4.txt deploy/aws-phone-proxies/scripts/bench_round3_m4max.sh "$REPO" "$REPO/eval-results/phone-proxies/m4max-macbook/$(date -u +%Y%m%dT%H%M%SZ)-round3" 2
