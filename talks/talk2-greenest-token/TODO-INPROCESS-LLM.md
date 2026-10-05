# TODO: review Talk 2's numbers and harness against the in-process LLM

**Status:** reviewed 2026-10-05; the real-stream re-measure is done (Pi 4 and M4 Max,
`docs/TALK2-HARDWARE-SPECTRUM-TEST-LOG.md` § "Real-stream re-measure"). Background and
Talk 3's numbers: `docs/INPROCESS-LLM.md`.

## Findings and decisions (2026-10-05)
- **Backend of every published number:** `LlmServerBackend` (llama-server), model
  loaded once per session, no per-call reload. The `SubprocessLlmBackend` in
  `conftest.py` (point 1 below) only gates the single-model tests on a real model
  being present; the comparison harnesses never used it.
- **Mac "CPU" numbers are CPU:** `build-cpu` was compiled with `-DGGML_METAL=OFF`.
- **Prompt cache (point 2) is real for the Edge Triage numbers too:** the harness
  repeats one payload n times, so the Pi's published 31.7 s / 154 J per call is
  generation with the prompt cached, a lower bound for a stream of different
  events. Round 3 interleaves cells, so it's closer to a stream.
- **Decision:** in-process is the default everywhere (Functions and harnesses).
  The study's runner scripts pin `--model-backend server` so published runs
  reproduce. New harness options: `--model-backend`, `--model-gpu-layers`,
  `--vary-events`.
- **Re-measured as a stream (2026-10-05).** Each device kept its published row's
  backend and build (llama-server), so only the event variation and the prompt order
  changed. The prompt became the cache-friendly `event-last` variant (event fields after
  the rules; same accuracy on llama-server, not in-process: see the backend check below). Pi 4: **416 J, p50 82 s per call** against the best case's
  154 J, 31.7 s; with the published prompt order, **772 J, 160 s** (5×).
- **Backend check (2026-10-05):** in-process on the Pi 4 costs the same as llama-server
  (429 J, 87 s vs 416 J, 82 s) but decides differently in borderline cases: it leans
  to "lower" (`eval-results/edge-triage-backend-accuracy-m4max-20261005/`). With the
  published prompt that stays correct (0/45); with event-last it flips the benign case
  (15/45). The paper and A10 now say "re-check accuracy after reordering". M4 Max GPU: published prompt 25.0 J / 0.70 s, event-last 18.5 J /
  0.49 s, against ~15 J / 0.36 s. In-process wasn't used for these: on the Pi it is a
  different llama.cpp build, which would have confounded the comparison with the
  published row.
- **Next:** the paper (Table II labelled as a best case, the stream result, Fig. 4's
  text) and the talk (a new assumption slide A10 on prompt order and caching; A1's
  caveat).

## Why
Talk 2 measures what it costs to run a small LLM inside the pipeline. Three things
learned on Talk 3 may change what those measurements mean:

1. **Per-call model loads.** The eval harness (`tests/model/conftest.py`) builds a
   `SubprocessLlmBackend`: a new `llama-completion` process, and a model reload,
   for every call. Any latency or energy per call measured through it includes
   that load. On the M4 Max the load was ~1 s of a 15.5 s one-core call; on a Pi
   reading a 2.5 GB model it may be a larger share. (The Edge Triage Pipeline's
   `LlmTriageFunction` uses `LlmServerBackend`, which keeps the model loaded —
   check which backend each published number came from.)
2. **Repeated prompts through a prefix cache.** The Tier 2 comparison
   (`tests/model/test_compare_tier2_models.py`) used `LlmServerBackend`, and
   repeated each scenario's identical prompt n times, so after the first trial
   `llama-server` served almost the whole prompt from its cache. The Pi 4 Tier 2
   median (43.7 s, 4 threads) is therefore close to generation time alone. Talk 3
   measured the same model on the same Pi with different incidents each call
   (only the fixed instructions shared): 1 min 54 s on 4 threads, ~99 s of it
   reading the prompt (`eval-results/talk3-single-core-pi4-20261004/`). Fine for
   ranking models by output length; not a per-call cost for a real stream.
3. **GPU vs. CPU.** A Metal build of llama.cpp uses the Mac's GPU unless run with
   `-dev none -ngl 0`; the harness passes no such flags. Mac numbers presented as
   CPU need checking. Pi numbers are CPU regardless.

## What to review
1. For each published per-call number (the Tier 2 table's Pi p50/p95, the J/call
   figures, the Edge Triage numbers), record which backend produced it, whether
   it includes a model load, and whether repeated prompts were served from a
   prefix cache.
2. Decide whether the deployment Talk 2 recommends is "model kept in the
   Function". If so, re-measure the headline numbers that way —
   `InProcessLlmBackend`, same llama.cpp build as before — and present per-call
   cost without the reload, or show both.
3. Add `InProcessLlmBackend` as a harness option (e.g. a `--backend` flag) so the
   comparison runs can use it.
4. Check every "CPU" label on Mac-measured numbers against the flags used.

## Done when
- Every per-call number in Talk 2's slides says how the model was run, and the
  recommended setup's numbers were measured that way.
