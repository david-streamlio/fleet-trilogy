#!/bin/bash
# User decision 2026-10-04 ~20:58Z, runs ON iphone-flagship: skip the follow-ups' round3_qwen3.5-9b_full_chat-on_think4096
# cell. On the M4 Max the same cell truncated 35 of 36 calls at the 4,096-token thinking budget (0% all_ok); on this slower
# M4 it would repeat that in ~2.5 h. The narrow cell, the informative one, still runs. followups_after_round3.sh can't be
# edited while it runs (bash reads scripts incrementally), so: once the narrow cell's artifact line is written, the GGUF is
# set aside (the next cell starts after a 20 s idle gap). The full cell's llama-server then exits at startup, the backend
# raises at once, and pytest exits non-zero with no artifact. The GGUF is restored as soon as that cell's window is logged,
# before the queued budget re-run needs it.
B=$HOME/phoneproxy
D=$(ls -1td "$B"/results/followups-* | head -1)
F=$B/models-round3/Qwen3.5-9B-Q4_K_M.gguf
until grep -q "^round3_qwen3.5-9b_narrow_chat-on_think4096 " "$D/artifacts.txt" 2>/dev/null; do sleep 2; done
mv "$F" "$F.set-aside"
printf '%s\n' "SKIPPED by user decision ($(date -u +%Y-%m-%dT%H:%M:%SZ)): round3_qwen3.5-9b_full_chat-on_think4096." \
  "Its window in windows.log has a non-zero exit and no artifact: the GGUF was set aside on purpose, so llama-server exited at startup." \
  "Reason: on the M4 Max the same cell truncated 35 of 36 calls at the 4,096-token budget (0% all_ok); here it would repeat that in ~2.5 h." \
  > "$D/SKIPPED-qwen3.5-9b-full-think4096.txt"
until grep -q "^round3_qwen3.5-9b_full_chat-on_think4096 " "$D/windows.log" 2>/dev/null; do sleep 2; done
mv "$F.set-aside" "$F"
echo "restored $(date -u +%H:%M:%SZ)" >> "$D/SKIPPED-qwen3.5-9b-full-think4096.txt"
