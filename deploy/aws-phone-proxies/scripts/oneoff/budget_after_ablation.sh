#!/bin/bash
# One-off (2026-10-04): run round 3's budget-forcing sessions on this MacBook after the ablation.
REPO=/Users/david.kjerrumgaard/clone-zone/davidkj-datadog/fleet-trilogy
sleep 120  # let the ablation waiter start the ablation first
# Also wait for /tmp/thinkbudget_after_ablation.sh (another session's queued Qwen3.5-9B 4096-token
# re-run, triggered by the same ablation end): two benchmark runs at once would share the GPU.
while pgrep -f "scripts/[b]ench_round3_m4max.sh" >/dev/null || pgrep -f "[a]blation_after_round3" >/dev/null || pgrep -f "scripts/[b]ench_ablation_m4max.sh" >/dev/null || pgrep -f "[t]hinkbudget_after_ablation" >/dev/null; do sleep 60; done
echo "ablation finished $(date -u +%H:%M:%SZ); starting budget forcing"
cd "$REPO" && GATE_PM=/tmp/m4max-powermetrics-4.txt deploy/aws-phone-proxies/scripts/bench_budget_m4max.sh "$REPO" "$REPO/eval-results/phone-proxies/m4max-macbook/$(date -u +%Y%m%dT%H%M%SZ)-round3-budget" 2 1024
