#!/bin/bash
# Start bench_budget.sh once this host's round-3 run and the Qwen3.5 skip watcher are done.
B=$HOME/phoneproxy
while pgrep -f "$B/[b]ench_round3.sh" >/dev/null || pgrep -f "[s]kip_qwen35_chaton" >/dev/null; do sleep 60; done
exec $B/bench_budget.sh $B $HOME/fleet-trilogy 2 1024
