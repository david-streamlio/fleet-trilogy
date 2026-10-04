#!/bin/bash
# One-off (2026-10-04 ~20:25Z), runs ON iphone-flagship: re-run bench_budget.sh. The first run
# (results/round3-budget-20261004T194143Z-FAILED) failed every session with pytest exit 4:
# followups_after_round3.sh, queued earlier by the user's other Claude session, installed at 19:40:55
# a conftest.py it had staged at 18:53, which lacks `--round3-mode chat-budget`. conftest.py was
# restored by copy-then-rename (the only difference: that added choice, so the running follow-ups
# are unaffected). This waits for the follow-ups to end, so the GPU runs one job at a time.
# (A first version also refused to start after 01:45Z, to finish before the scheduled 04:37Z
# teardown; the user cancelled that teardown at ~20:30Z, so the cutoff was removed.)
B=$HOME/phoneproxy
while pgrep -f "$B/[f]ollowups_after_round3.sh" >/dev/null; do sleep 60; done
exec "$B/bench_budget.sh" "$B" "$HOME/fleet-trilogy" 2 1024
