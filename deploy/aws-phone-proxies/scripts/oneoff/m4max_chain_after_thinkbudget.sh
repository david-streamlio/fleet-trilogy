#!/bin/bash
# One-off (2026-10-04): this MacBook's remaining runs, strictly in order and with a fixed context.
# 1) wait for the other session's /tmp/thinkbudget_after_ablation.sh run to end;
# 2) a context-size check (Phi and Llama on the Edge Triage Pipeline at 8k, gated, 3 reps: what the
#    128k default did to the earlier M4 Max latency and energy); 3) the ablation; 4) budget forcing. Both with LLAMA_ARG_CTX_SIZE=8192: with no
# context size llama-server sized Phi-3.5's KV cache to its 128k training context (51 GB, swap).
REPO=/Users/david.kjerrumgaard/clone-zone/davidkj-datadog/fleet-trilogy
R=$REPO/eval-results/phone-proxies/m4max-macbook
export GATE_PM=/tmp/m4max-powermetrics-4.txt LLAMA_ARG_CTX_SIZE=8192
while pgrep -f "[t]hinkbudget_after_ablation" >/dev/null; do sleep 30; done
cd "$REPO" || exit 1
note() { mkdir -p "$1"; echo "LLAMA_ARG_CTX_SIZE=$LLAMA_ARG_CTX_SIZE (exported for every llama-server this run starts; set after the 128k-context default filled RAM in the first ablation attempt)" > "$1/CONTEXT-SIZE.txt"; }
K="$R/$(date -u +%Y%m%dT%H%M%SZ)-ctx8192-check"; note "$K"
deploy/aws-phone-proxies/scripts/bench_workload_m4max.sh "$REPO" "$K" '^edge_triage_(phi-3.5-mini-instruct-q4km|llama-3.1-8b-instruct-q4km)_r[0-9]+$' "1 2 3"
A="$R/$(date -u +%Y%m%dT%H%M%SZ)-ablation"; note "$A"
deploy/aws-phone-proxies/scripts/bench_ablation_m4max.sh "$REPO" "$A" 2
B="$R/$(date -u +%Y%m%dT%H%M%SZ)-round3-budget"; note "$B"
deploy/aws-phone-proxies/scripts/bench_budget_m4max.sh "$REPO" "$B" 2 1024
