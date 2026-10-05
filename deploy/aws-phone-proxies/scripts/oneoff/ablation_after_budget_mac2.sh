#!/bin/bash
# Scheduled step (user-approved 2026-10-04 ~20:30 UTC: "start 1 now and do 2 later"), runs ON mac2
# (iphone-older): once its budget-forcing run (results/round3-budget-20261004T203000Z) ends, a reduced
# prompt ablation for latency and energy on the iPhone-17-Pro-class stand-in; accuracy only replicates
# the M4 Max and mac-m4 ablations. Variants chosen 2026-10-04 ~23:50Z from those two runs (they agree
# closely): base; template (facts + lookup tables + the model's own chat template), the large
# consistent gain (+36-42 points for Phi-3.5, Llama-3.1-8B and Qwen3-14B); examples (worked examples,
# which nearly double the prompt to ~1,400 tokens and help Gemma-3-4B), the prompt-length cost worth
# measuring where prompt processing is slow. temp0 and grammar added nothing measurable.
# Launched as `exec -a bench-ablation-waiter …` so collect_when_done.sh (which waits while anything
# matching "bench" runs) can't collect in the gap between the two runs.
B=$HOME/phoneproxy
while pgrep -f "$B/[b]ench_budget.sh" >/dev/null; do sleep 60; done
exec "$B/bench_ablation.sh" "$B" "$HOME/fleet-trilogy" 2 "base template examples"
