#!/bin/bash
# One-off (2026-10-04): start the prompt ablation on this MacBook once the local round-3 run ends.
REPO=/Users/david.kjerrumgaard/clone-zone/davidkj-datadog/fleet-trilogy
while pgrep -f "scripts/[b]ench_round3_m4max.sh" >/dev/null; do sleep 60; done
echo "round 3 finished $(date -u +%H:%M:%SZ); starting the ablation"
cd "$REPO" && GATE_PM=/tmp/m4max-powermetrics-4.txt deploy/aws-phone-proxies/scripts/bench_ablation_m4max.sh "$REPO" "$REPO/eval-results/phone-proxies/m4max-macbook/$(date -u +%Y%m%dT%H%M%SZ)-ablation" 2
