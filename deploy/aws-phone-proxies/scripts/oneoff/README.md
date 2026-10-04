# One-off launchers and helpers (2026-10-04)

Small scripts that queued, sequenced or inspected the round-2 and round-3 runs. They ran from `/tmp` on the operator's MacBook, or from a Mac proxy's home directory, and are kept here verbatim. The run record in `docs/TALK2-HARDWARE-SPECTRUM-TEST-LOG.md` then shows exactly how each run was started.
- **Reproducing a run:** use the main runners in `..` (`REPRODUCE.md` lists them). These files show the order and conditions used, including the hand-offs between runs.
- **Absolute paths** are the operator's (`/Users/david.kjerrumgaard/...`, `~/phoneproxy`). Adjust them before reuse.

**Why waiters at all:** several runs shared one GPU (the MacBook) or one host, so each next run had to start only after the previous one ended.
- Overwriting a script that is running corrupts that run (test log incident 9).
- A `pgrep` pattern that matches the waiter's own command line waits forever (incidents 10 and 21). Every waiter here uses a `[b]racket` pattern for that reason.

| Script | Where it ran | What it did | Status |
|---|---|---|---|
| `round3_local.sh` | MacBook | Downloaded the four models round 3 needed (Gemma-3-12B, Gemma-4-12B, Qwen3-14B, Qwen3.5-9B), then ran `bench_round3_m4max.sh` | used: round 3 `20261004T153710Z-round3` |
| `ablation_after_round3.sh` | MacBook | Started `bench_ablation_m4max.sh` when the local round 3 ended | used. That first ablation was stopped after one cell (context-size issue, incident 23) and is kept as `20261004T190116Z-ablation-ABORTED` |
| `budget_after_ablation.sh` | MacBook | Was to start the budget-forcing run after the ablation | superseded (killed) by `m4max_chain_after_thinkbudget.sh` before it ran |
| `thinkbudget_after_ablation.sh` | MacBook | **Written by another Claude session** at the user's request: re-run Qwen3.5-9B chat-on at a 4,096-token think budget, after the ablation | first run aborted (default context, incident 23) → `…-thinkbudget4096-ABORTED`. Relaunched unchanged with `LLAMA_ARG_CTX_SIZE=8192` by user decision → `20261004T191021Z-thinkbudget4096` |
| `m4max_chain_after_thinkbudget.sh` | MacBook | After the thinkbudget run: the 8k context-size check (`-ctx8192-check`), then the ablation, then budget forcing, all with `LLAMA_ARG_CTX_SIZE=8192` exported and a `CONTEXT-SIZE.txt` in each run dir | queued |
| `skip_qwen35_chaton.sh` | mac2 and mac-m4 | **User decision:** skip round 3's Qwen3.5-9B chat-on sessions on the hosts. It set the GGUF aside after the chat-off sessions, so `bench_round3.sh` skipped them, wrote `SKIPPED-qwen3.5-9b-chat-on.txt` in the run dir, and restored the file afterwards | used |
| `round3_after_qconfirm.sh` | mac-m4 | Started `bench_round3.sh` when the Q4_0 confirmation run (`bench_quant_confirm.sh`) ended. It replaced a first waiter that matched itself (`pgrep -f bench_quant_confirm.sh`) | used |
| `budget_after_round3.sh` | mac-m4 | Started `bench_budget.sh` after round 3 and after `skip_qwen35_chaton.sh` had restored the model file | queued |
| `qconfirm_summary.py` | mac-m4 | Summarised the Q4_0 confirmation run (escalation mismatch per format) | used: results in `talks/talk2-greenest-token/TODO-Q4_0-ACCURACY-CHECK.md` |
| `l7peek.py` | c9g | Printed L7's per-pair latency, format and mismatch from the eval artifacts mid-run | used (diagnosed the OOM, incident 14) |
| `ablation_check.py` | MacBook | Smoke test of all seven ablation variants against a CPU-only Gemma-3-1B server (grammars parse, cards have the right fields) | used |
