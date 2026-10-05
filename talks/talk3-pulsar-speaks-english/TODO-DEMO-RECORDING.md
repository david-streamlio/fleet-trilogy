# TODO: record a new take of the Talk 3 demo

**Status:** open (2026-10-04). Record it on the machine that recorded take 4: it
already has the broker, `pulsar-admin`/`pulsar-client`, Piper, ffmpeg, the external
display and the screen-recording permissions. An attempt on the M4 Max laptop may
come first (see "Trying it on the M4 Max" below).

## Why a new take
Take 4 (`deploy/recordings/talk3-demo-20261002-174855.mp4`) no longer shows what the
talk claims:
- It ran llama.cpp as a fresh subprocess per call with no device flags, which on a
  Mac means the **Metal GPU**. The talk now promises one CPU core, no GPU.
- It predates the in-process backend: the model now lives inside
  `GlobalSynthesisFunction` (`llm_backend=inprocess`).
- It predates the fact check (`fact_check.py`): a warning with a number the cards
  don't support is now regenerated once, then replaced by a plain-code warning.

The slide plan uses the new take for the cold-open audio (slide 3) and as the
fallback for the live demo (slide 25). See `docs/TALK3-SLIDE-PLAN.md` "Open items".

## Steps (on the recording machine)
1. `git pull` the `talk3-wip` branch.
2. `uv sync` at the repo root. The first sync compiles llama-cpp-python (the
   `inprocess` dependency group) with Metal: a few minutes.
3. Check the model is where `deploy/talk3-windows/tier2.sh` expects it
   (`~/tools/models/gemma-3-4b-it-GGUF/gemma-3-4b-it-Q4_K_M.gguf`) or set
   `LLM_MODEL_PATH`.
4. Run `./deploy/record-talk3-demo.sh --teardown`. `tier2.sh` now defaults to
   `LLM_BACKEND=inprocess` and `LLM_THREADS=1` (CPU only); don't override them.
5. In the Tier 2 window's log, confirm no `failed the fact check` /
   `plain-code warning` lines, or note them: if the fallback was used, the take
   shows it, and the talk should say so.
6. Expect the first warning ~15 s after the third card (model load plus an empty
   prompt cache), vs. a couple of seconds on the GPU in take 4. Extend
   `--tail` if the end gets cut off.
7. Save the transcript of the spoken warning (the speaker window's text) next to
   the recording; slides 3 and 25 quote it.

## Trying it on the M4 Max
The laptop has the model, llama-cpp-python and `jq`, but is missing:
- a Pulsar broker (Docker, or a Pulsar distribution + Java) and
  `pulsar-admin`/`pulsar-client`;
- Piper and the `norman` voice (`README.md` "Speaking the warning");
- ffmpeg/ffprobe (the export);
- an external display (the recorder places its windows on one).

## Done when
- A new recording exists in `deploy/recordings/`, made with the current defaults,
  with its transcript.
- `docs/TALK3-SLIDE-PLAN.md` slides 3 and 25 point at it, and their `[NEEDS: new
  take]` flags are gone.
