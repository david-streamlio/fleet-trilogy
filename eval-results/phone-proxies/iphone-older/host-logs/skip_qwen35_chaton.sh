#!/bin/bash
# User decision 2026-10-04 ~18:55 UTC: skip round 3's Qwen3.5-9B chat-on sessions on this host.
# On the M4 Max they reasoned past the 2,048-token budget without closing </think> (12/18 narrow,
# 36/36 full truncated); here they would only repeat that on slower hardware. Capped thinking is
# measured instead with the budget-forcing mode. bench_round3.sh skips a session whose GGUF is
# missing, so the file is set aside after the chat-off sessions and restored when the run ends.
B=$HOME/phoneproxy
D=$(ls -1td $B/results/round3-* | head -1)
F=$B/models-round3/Qwen3.5-9B-Q4_K_M.gguf
until grep -q "^round3_qwen3.5-9b_full_chat-off " "$D/artifacts.txt" 2>/dev/null; do sleep 2; done
mv "$F" "$F.set-aside"
printf '%s\n' "SKIPPED by user decision ($(date -u +%Y-%m-%dT%H:%M:%SZ)): round3_qwen3.5-9b_narrow_chat-on and round3_qwen3.5-9b_full_chat-on." \
  "The \"skip ... missing\" lines in bench.log are this: the GGUF was set aside on purpose, then restored after the run." \
  "Reason: on the M4 Max, Qwen3.5-9B's chat-on reasoning ran past the 2,048-token budget without closing </think>; capped thinking is measured with budget forcing instead." > "$D/SKIPPED-qwen3.5-9b-chat-on.txt"
while pgrep -f "$B/[b]ench_round3.sh" >/dev/null; do sleep 30; done
mv "$F.set-aside" "$F"
echo "restored $(date -u +%H:%M:%SZ)" >> "$D/SKIPPED-qwen3.5-9b-chat-on.txt"
