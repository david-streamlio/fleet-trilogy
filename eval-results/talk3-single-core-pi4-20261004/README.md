# Talk 3: Tier 2's LLM call on a Raspberry Pi 4 (edge-node00, 2026-10-05)

The real run behind slide 22, replacing its "~1 min, predicted" with what
happened. Same script and prompt as the M4 Max run
(`eval-results/talk3-single-core-m4max-20261004/measure_inprocess.py`), on the Pi.

## Setup
- Raspberry Pi 4 Model B Rev 1.4, 4 cores, 8 GB, Debian (kernel 6.18.50), model on
  the USB data drive (`/mnt/data`). Fan on.
- Code: `talk3-wip` at `ced65e2`, copied with `git archive` into
  `/mnt/data/fleet-trilogy-talk3wip` (the Pi's own `/mnt/data/fleet-trilogy` is a
  plain copy holding Talk 2's Pi logs, left untouched).
- llama-cpp-python 0.3.36, compiled on the Pi by `uv sync` (CPU only).
- Model: unsloth `gemma-3-4b-it-Q4_K_M.gguf`, sha256 `04a43a22…7d19` (same file
  as the M4 Max run).
- Prompt: the three demo cards on a rotating corridor, 361 tokens; consecutive
  calls share 98 tokens of fixed instructions.

## Results

| Setup | First call | Median [min–max] | n | Cores busy |
|---|---|---|---|---|
| `kept_t1`: model kept in the Function, 1 thread | 7 min 52 s | **6 min 17 s** (376.7 s) [363–393 s] | 5 | 1.00 |
| `fresh_t1`: new model every call, 1 thread | 7 min 57 s | 8 min 1 s (480.5 s) | 1 | 1.00 |
| `kept_t4`: model kept, 4 threads | 2 min 31 s | **1 min 54 s** (113.9 s) [108–125 s] | 5 | 3.99 |
| native `llama-completion`, 4 threads, per call (`native_llama_completion_t4.txt`) | — | ~2 min 25 s – 2 min 32 s | 2 | — |

- **On one Pi 4 core: about 6 minutes per warning.** The talk's prediction (~1
  min, from a Graviton2 core standing in for a Pi 5) was 6x too optimistic. With
  the Function's default 60 s timeout, every call would have failed.
- **Keeping the model in the Function helps more here than on the Mac:** ~8 min →
  6 min 17 s on one thread (the model reloads from a USB drive), and on four
  threads 1 min 54 s in-process vs. ~2.5 min through the Pi's own native
  `llama-completion` (5.5 s load + 99 s reading the prompt + 41–48 s writing).
  So the native build is not faster than llama-cpp-python's here.
- On four threads the Pi reads the prompt at 3.7 tok/s: the 361-token prompt alone
  takes ~99 s. **Talk 2's published Pi 4 Tier 2 median (43.7 s, 4 threads) is a
  best case, not a comparable number.** Its prompts are only 10–25% shorter
  (1,004–1,202 chars vs. 1,313), but its comparison harness
  (`tests/model/test_compare_tier2_models.py`) ran through `llama-server`, which
  reuses matching prompt prefixes, and repeated each scenario's identical prompt
  n times. After the first trial nearly the whole prompt was cached, leaving
  mostly generation: ~56 tokens at the 1.4 tok/s measured here is ~40 s. A stream
  of different incidents only shares the fixed instructions, as measured here.
  Flagged in `talks/talk2-greenest-token/TODO-INPROCESS-LLM.md`.
- `fresh_t1` was stopped on purpose after 1 timed call (the log's "FAILED" is
  that stop); the one-core conclusion didn't need more.
- Peak memory: ~3 GB in-process (the records say `3` because the script divided
  Linux's kilobytes as if they were bytes; fixed in `measure_inprocess.py` since).
- Every call returned a parseable `spoken_warning`.

## Thermal (`thermal.log`)
41 °C at the start; one thread peaked ~53 °C, never throttled. The 4-thread run
ended at 71.5 °C with `throttled=0x80000` (the soft temperature limit was reached
at some point), so `kept_t4` may be slightly pessimistic; the native comparison
ended the same way.

## Files
- `runs_inprocess.jsonl` (every call, with its warning), `runs_inprocess.log`,
  `summary_inprocess.txt`, `thermal.log`, `system.txt`,
  `native_llama_completion_t4.txt`.
