# Talk 2 GPU benchmark plan: replacing illustrative FULL_PRECISION_GPU numbers

**Status: not started — blocked on the Mac Studio M4 (lab GPU host) being back
online.** This is a plan to execute once it is, not a runbook for something
already set up (contrast with `docs/PI4-RUNBOOK.md`, which is live).

## Why

`talks/talk2-greenest-token/src/talk2_greenest_token/efficiency.py` currently
compares two approaches — `SMALL_MODEL_CPU` and `FULL_PRECISION_GPU` — using
hand-picked, clearly-labeled **illustrative** constants (latency/power/cost per
call), documented in the module docstring as "not benchmarked numbers." That's
fine for telling the efficiency story on stage today, but the user has a Mac
Studio M4 in their home lab capable of actually hosting a full-precision GPU
model, so `FULL_PRECISION_GPU` can become a real measurement instead of an
assumption — same upgrade `docs/PI4-RUNBOOK.md` did for the CPU side (M4
laptop quality-only run → Pi 4 decision-grade run).

## Scope boundary

This plan produces **one real data point**: full-precision-model-on-GPU
latency/power/cost for the same Tier 1 interpretation call shape
(`ENRICHMENT_CARD_PROMPT` in `llm_inference.structured`), on one specific
machine. It does **not**:
- change `SMALL_MODEL_CPU`'s numbers (those are the Pi's — a separate axis,
  covered by `docs/PI4-RUNBOOK.md` / `tests/model/`),
- try to make the comparison "fair" across wildly different hardware classes —
  the whole point of the talk is that they're different classes of machine,
- require touching `tests/model/test_compare_models.py`'s Pi-deciding harness
  at all; that harness picks the *stage* model (small quantized CPU
  candidates only). This is a different, smaller harness for a different
  purpose (the Talk 2 efficiency contrast), and should not be built by
  reusing `test_compare_models.py`'s multi-model-comparison machinery —
  it's one model, one host, a handful of runs.

## 1. Model choice

Pick a full-precision (fp16) instruct model clearly in a different capability
class than the Pi's quantized Qwen2.5-1.5B/0.5B — that contrast is the point.
Candidates, in order of preference:

- **Qwen2.5-7B-Instruct (fp16)** — same model family as the Pi candidates
  (apples-to-apples prompt behavior, different scale/precision), runs
  comfortably on an M4 Studio's unified memory.
- Llama-3.1-8B-Instruct (fp16) as a fallback if Qwen2.5-7B's chat template
  causes grounding issues analogous to the ones `structured.py`'s v1→v2 fix
  already solved for the small models — re-check grounding behavior on
  whichever model is chosen, don't assume it transfers.

Decide the exact model when the machine is back online and weights can
actually be pulled/tested; don't pre-commit further than "7-8B fp16,
Qwen2.5 family preferred" here.

## 2. Runtime choice

Two real options on Apple silicon:

- **mainline llama.cpp, Metal backend** (`-DGGML_METAL=ON` at build time,
  default on macOS builds) — reuses the exact same `SubprocessLlmBackend` /
  `-m -p -n -t --temp` CLI contract already used everywhere else in this repo
  (`shared/llm-inference/src/llm_inference/client.py`). Preferred: zero new
  backend code, same `LlmBackend` interface, same eval helpers in
  `tests/model/eval_lib.py` become reusable as-is.
- MLX (Apple's own framework) — likely faster on M-series, but would need a
  new `LlmBackend` implementation (`InProcessLlmBackend` is reserved for
  exactly this kind of future binding per `docs/CANON.md`, but is not
  implemented). Only pursue this if llama.cpp/Metal turns out too slow to be
  a credible "GPU" data point — that would be a finding worth reporting on
  its own, not silently worked around.

Default plan: llama.cpp + Metal. Build with GPU layers offloaded
(`-ngl <all>` / whatever mainline llama.cpp's current flag is at build time —
check current docs, flag names drift) so the run is genuinely GPU-bound, not
accidentally CPU-only again.

## 3. What to measure, and how

Three numbers feed `ApproachProfile` (`latency_s`, `power_watts`,
`cost_per_call_usd`):

- **`latency_s`**: reuse `tests/model/eval_lib.py`'s `run_enrichment_trials`
  pattern directly (same prompt, same parsing) — this is exactly what it's
  for. Run ~30 trials, take the mean or p50 wall-clock per call, same as the
  Pi/M4-laptop evals already do. No new harness code needed for this part.
- **`power_watts`**: macOS's `powermetrics` (`sudo powermetrics --samplers
  gpu_power,cpu_power -i 1000 -n <N>` while a batch of calls runs
  back-to-back) gives real GPU+CPU package power in watts. Sample throughout
  a batch of calls (not a single call — too short/noisy) and average.
  Requires `sudo`; note this explicitly as a manual step, not something to
  automate into CI/eval code.
- **`cost_per_call_usd`**: this one has no clean "measure it" step — decide
  and document an amortization method up front (e.g. hardware cost / expected
  service-life hours, or a cloud-equivalent-instance $/hr as a stand-in), the
  same way the current illustrative constant documents its assumption in a
  comment. Real power draw feeds into it (electricity cost component), but
  the hardware-amortization component is inherently a modeling choice, not a
  measurement — say so in the constant's comment, same style as today's.

## 4. Steps, once the Mac Studio is back online

1. Confirm SSH/local access; `git clone` (or reuse existing checkout) +
   `uv sync`; `make test` should pass in mock mode with zero models present
   (sanity check, same first step as the Pi runbook).
2. Build llama.cpp with Metal: `cmake -B build -DCMAKE_BUILD_TYPE=Release
   -DGGML_METAL=ON && cmake --build build --config Release -j"$(nproc)"`.
3. Pull the chosen fp16 model weights (not committed to the repo, same
   `.gitignore` rule as the GGUF quantized weights).
4. Coherence check first, same discipline as `PI4-RUNBOOK.md` step 1 — a
   quick prompt, confirm real text, not garbage, before trusting any
   timing/power number.
5. Run a small `--model-eval-runs=5`-scale smoke test first (same lesson
   learned from the Pi 4 timeout bug this session — validate real per-call
   latency against whatever `timeout_seconds` is configured before
   committing to a larger sample).
6. Run the real sample (~30 calls) for latency, with `powermetrics` sampling
   concurrently in a second terminal/session for power.
7. Update `FULL_PRECISION_GPU` in `efficiency.py` with the measured
   `latency_s`/`power_watts`, and a documented `cost_per_call_usd`
   methodology — change its comment from "illustrative assumption" to state
   what was measured, on what hardware, when, and how (mirroring how
   `docs/PI4-RUNBOOK.md`'s artifacts are dated and host-labeled). Keep
   `SMALL_MODEL_CPU` untouched.
8. Re-run `make test` (talk2's existing tests assert relative ordering, e.g.
   small-model-cpu uses less energy — confirm that still holds with real
   numbers; if a real measurement flips an assumption the tests/talk
   narrative depended on, that's a finding to report, not to quietly patch
   around).

## 5. What comes back from this

A short note (or an update to this doc) stating: model used, llama.cpp/Metal
build flags, measured latency (mean + spread over N runs), measured power
(mean watts, sampling method), the chosen cost-amortization method and
resulting `$/call`, and the diff to `efficiency.py`. Human decides whether the
real numbers still tell the same story as the illustrative ones did, same
"human decides, nothing auto-picks" spirit as the Pi comparison's
recommendation text.
