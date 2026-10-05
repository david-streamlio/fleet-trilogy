# TODO: review Talk 2's numbers and harness against the in-process LLM

**Status:** flagged for review (2026-10-04). Background and Talk 3's numbers:
`docs/INPROCESS-LLM.md`.

## Why
Talk 2 measures what it costs to run a small LLM inside the pipeline. Two things
learned on Talk 3 may change what those measurements mean:

1. **Per-call model loads.** The eval harness (`tests/model/conftest.py`) builds a
   `SubprocessLlmBackend`: a new `llama-completion` process, and a model reload,
   for every call. Any latency or energy per call measured through it includes
   that load. On the M4 Max the load was ~1 s of a 15.5 s one-core call; on a Pi
   reading a 2.5 GB model it may be a larger share. (The Edge Triage Pipeline's
   `LlmTriageFunction` uses `LlmServerBackend`, which keeps the model loaded —
   check which backend each published number came from.)
2. **GPU vs. CPU.** A Metal build of llama.cpp uses the Mac's GPU unless run with
   `-dev none -ngl 0`; the harness passes no such flags. Mac numbers presented as
   CPU need checking. Pi numbers are CPU regardless.

## What to review
1. For each published per-call number (the Tier 2 table's Pi p50/p95, the J/call
   figures, the Edge Triage numbers), record which backend produced it and
   whether it includes a model load.
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
