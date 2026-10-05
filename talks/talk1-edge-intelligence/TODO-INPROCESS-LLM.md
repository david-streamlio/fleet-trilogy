# TODO: review moving Talk 1's Functions to the in-process LLM

**Status:** flagged for review (2026-10-04). Background and Talk 3's numbers:
`docs/INPROCESS-LLM.md`.

## Why
Talk 1's story is a small LLM inside a Pulsar Function on the edge. Neither of its
Functions actually holds the model:

- `LlmTriageFunction` (`triage_function.py`, the Edge Triage Pipeline) starts a
  `llama-server` process beside itself (`LlmServerBackend`) and calls it over
  HTTP. The model stays loaded, which already fixed the per-call reload
  (2026-09-26), but it's a separate server, not the Function.
- `EdgeEnrichmentFunction` (`function.py`) starts a new `llama-completion`
  process per call (`SubprocessLlmBackend`), reloading the model every time.

Talk 3 moved its Function to `InProcessLlmBackend` (llama-cpp-python, model kept
on `self`): on one M4 Max core, 15.5 s → 12.0 s per call against reloading, on the
same build.

## What to review
1. **Design:** switch both Functions to `InProcessLlmBackend`, behind a user-config
   option like Talk 3's `llm_backend`, keeping the current backend as an option.
   That makes "the LLM inside the Function" literally true and removes the
   server's process lifecycle (`close()`, ports, startup timeouts).
2. **Performance on the Pi:** measure before switching. Against
   `LlmServerBackend` the gain is likely small (both keep the model loaded and
   reuse prompt prefixes); against `SubprocessLlmBackend` it should be large.
   Compare on the **same llama.cpp build** — on the M4 Max a Homebrew build was
   2x slower than a locally compiled one, which would swamp the design difference.
3. **Build on the Pi:** llama-cpp-python compiles from source on `uv sync`; check
   its build time and that it picks up the Pi's CPU features (ARM NEON/dotprod).
4. **Slides:** `docs/TALK1-SLIDE-PLAN.md` describes the Function hosting the model
   ("A Pulsar Function ... hosts the small LLM on a CPU runtime"). Keep that
   claim true, or reword it, whichever way the review goes.

## Done when
- Both Functions have been measured on the Pi with the current backend and
  in-process, on the same build, and the faster/simpler one is the default — or
  the reason not to switch is written down here.
