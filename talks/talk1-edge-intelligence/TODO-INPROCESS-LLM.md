# TODO: review moving Talk 1's Functions to the in-process LLM

**Status:** decided 2026-10-05: in-process is the default for both Functions
(`llm_backend=server` / `subprocess` keep the old backends; see
`docs/INPROCESS-LLM.md`, "Default everywhere"). Still open: the Pi measurement
(item 2) and the slide check (item 4). Background and Talk 3's numbers:
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

## Done so far (2026-10-05)
- Item 1: both Functions default to `InProcessLlmBackend`, CPU only.
  `LlmTriageFunction` keeps `llm_backend=server`; `EdgeEnrichmentFunction` keeps
  `llm_backend=subprocess`. The localrun scripts pass `LLM_BACKEND`,
  `LLM_THREADS` and `LLM_GPU_LAYERS` through.
- On a Mac, the old llama-server default ran on the Metal GPU; in-process is CPU
  only unless `LLM_GPU_LAYERS=99`. Check the demo's pacing on whichever one the
  recording uses.
- Item 3: llama-cpp-python 0.3.36 is already built on the Pi
  (`/mnt/data/fleet-trilogy-talk3wip`, from Talk 3's Pi run).
- Item 2, `LlmTriageFunction` measured on the Pi both ways (2026-10-05,
  `eval-results/edge-triage-event-last-pi4-20261005/`, runs A and C; event-last
  prompt, a different event per call, inline meter): llama-server 82 s / 416 J per
  call, in-process 87 s / 429 J. Same cost within noise, in-process with less memory
  (4.0 vs 6.7 GB). Unlike Talk 3's Tier 2 run, llama-cpp-python wasn't faster here.
- **But the backends decide differently in borderline cases**
  (`eval-results/edge-triage-backend-accuracy-m4max-20261005/`, 45 escalation calls
  per cell): in-process leans to "lower". With the published prompt
  (`DEFAULT_PROMPT_TEMPLATE`, what the demo uses) it stays correct (0/45; the
  de-escalate-worthy case goes hold → lower, which is accepted). With
  `EVENT_LAST_PROMPT_TEMPLATE` it flips the benign case to "lower" (15/45). So keep the
  published prompt with the in-process default, or re-validate before combining them.

## Still open
- Item 4 (the slides' "hosts the small LLM on a CPU runtime" claim): now literally true
  by default.

## Done when
- Both Functions have been measured on the Pi with the current backend and
  in-process, on the same build, and the faster/simpler one is the default — or
  the reason not to switch is written down here.
