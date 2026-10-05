# TODO: run Tier 2 on one Pi core

**Status:** done (2026-10-05) — `eval-results/talk3-single-core-pi4-20261004/`.
One Pi 4 core: 6 min 17 s per warning (model kept); four cores: 1 min 54 s. Slide
22 reports it. The steps below are kept for a re-run.

## Why
Slide 22 (`docs/TALK3-SLIDE-PLAN.md`) shows "~1 min per warning on a Pi 5-class
core" as a **prediction**: llama-bench puts a Graviton2 core (the Pi 5 stand-in)
4–5x slower than an M4 core for Gemma-3-4B-it, times the M4 Max's measured 12.0 s.
The same kind of estimate undershot the M4 by 2x (README in
`eval-results/talk3-single-core-m4max-20261004/`), and a Pi 4 core is slower than
a Pi 5's. The talk should say what really happens, including "it failed" or "too
slow to be useful".

## Steps (on the Pi)
1. `git pull` the `talk3-wip` branch, then `uv sync` at the repo root. This
   compiles llama-cpp-python for ARM (the `inprocess` dependency group) and may
   take a long time on a Pi; do it before the run, with the fan on.
2. Point at the model on the data drive — `/mnt/data`, per the Pi's earlier
   results (`eval-results/compare-edge-node00-*.json`), not the runbook's
   `/mnt/ssd`. Download it there first if it's missing (unsloth
   `gemma-3-4b-it-Q4_K_M.gguf`, sha256 `04a43a22…7d19`):
   ```bash
   export LLM_MODEL_PATH=/mnt/data/models/gemma-3-4b-it-GGUF/gemma-3-4b-it-Q4_K_M.gguf
   ```
3. Run the same measurement as the M4 Max, fewer calls (each may take minutes;
   the script's timeout is 600 s per call):
   ```bash
   OUT=eval-results/talk3-single-core-pi4-$(date +%Y%m%d)
   mkdir -p $OUT
   for s in kept_t1 fresh_t1 kept_t4; do
     uv run --no-sync python eval-results/talk3-single-core-m4max-20261004/measure_inprocess.py $s 5 $OUT/runs_inprocess.jsonl
   done
   python3 eval-results/talk3-single-core-m4max-20261004/summarize_inprocess.py $OUT/runs_inprocess.jsonl | tee $OUT/summary_inprocess.txt
   ```
   Also note `vcgencmd measure_temp` and `vcgencmd get_throttled` before and
   after: Talk 2 found the Pi throttles without its fan.
4. If a setup fails (out of memory, a timeout, a crash), keep the error output
   in `$OUT` — that's the result.
5. Commit `$OUT` with a README like the M4 Max one.

## Then
- Replace slide 22's `~1 min` tile and its `[NEEDS: Pi run]` flag with the real
  number, or with "it failed: <why>".
- Remove the Pi item from the outline's "Not yet decided".
- If the per-call time is near or over 60 s, the Function's default
  `timeout_seconds` would kill it on stage: say so on slide 22, and set
  `LLM_TIMEOUT_SECONDS` for any Pi demo.

## Done when
- `eval-results/talk3-single-core-pi4-<date>/` exists, and slide 22 reports it.
