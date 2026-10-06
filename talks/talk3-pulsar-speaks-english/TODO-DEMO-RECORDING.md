# TODO: record a new take of the Talk 3 demo

**Status:** take 8 recorded (2026-10-05 evening) on the M4 Max's **GPU**, with
the spoken-warning prompt's reroute fix; needs review, and a decision on the
talk's "one CPU core, no GPU" claim (below). Takes 5-7 won't be used unless
that claim stays: then re-take on the CPU (the fix works there too). Slide 24's
raw/normalized clips are done too (`deploy/recordings/.talk3-slide24-clips/`).

## Take 8 (M4 Max + external display, GPU, reroute fix)
- `deploy/recordings/talk3-demo-20261005-174611.mp4`: 36.8 s, 1890×1006, H.264 +
  AAC; transcript `talk3-demo-20261005-174611.txt` beside it; raw capture and WAV
  in `.raw-talk3-…` / `.talk3-audio-20261005-174611/`. **Gitignored: only on the
  M4 Max.**
- Recorded with `LLM_GPU_LAYERS=99 ./deploy/record-talk3-demo.sh --teardown`
  (the script now passes `LLM_GPU_LAYERS` / `LLM_THREADS` to the Tier 2 window).
  Function config from its log: `llm_backend=inprocess`, `threads=1`,
  `llm_gpu_layers=99`, `corridor_threshold=3`.
- Model loaded at 17:47:04; incident published ~1 s later. No fact-check
  failures, no plain-code warning.
- Transcript:
  > Drivers approaching I-95N, we're seeing a slowdown affecting multiple trucks.
  > It is recommended that you consider rerouting around I-95N as three trucks are
  > experiencing significant delays, with an estimated impact of up to 9 minutes.
- **The reroute is now a recommendation**, matching `reroute_recommended: true`.
  The prompt adds "A reroute is only ever a recommendation, never already
  happening…" when a reroute is recommended (`prompting.py`); measured 0 of 30
  warnings stating it as done, against 8-9 with the old prompt, on CPU and GPU
  (`eval-results/talk3-reroute-wording-20261005/`).
- **To decide:** the talk promises one CPU core, no GPU (see "Why a new take"
  below). This take used the GPU: either the slides change, or re-take with the
  default `./deploy/record-talk3-demo.sh --teardown` (one CPU core, ~15 s to the
  warning). No truck numbers, like take 6.

## Take 7 (M4 Max + external display, one CPU core)
- `deploy/recordings/talk3-demo-20261005-172916.mp4`: 52.9 s, 1890×1006;
  transcript beside it. Gitignored. `llm_backend=inprocess`, `threads=1`, no GPU.
  Warning ~15 s after the model load; fact check passed first time.
- Transcript:
  > Drivers approaching I-95 North, we're seeing a slowdown affecting multiple
  > trucks. Traffic is rerouted around the corridor due to a correlated slowdown
  > with three trucks reporting significant delays. Please proceed with caution and
  > expect potential congestion.
- "Traffic is rerouted" again, the second take in a row: what led to the prompt
  fix used in take 8. It said "I-95 North" (Piper speaks it naturally).

## Take 6 (external-display machine, two displays)
- `deploy/recordings/talk3-demo-20261005-090519.mp4`: 52.5 s, 1890×1006, H.264 +
  AAC. Raw capture, WAV (13.3 s) and `playback.log` in `.raw-talk3-…` /
  `.talk3-audio-20261005-090519/`. **Gitignored: only on this machine.**
- Function config from its log: `llm_backend=inprocess`, `threads=1`,
  `llm_gpu_layers` unset (0, CPU only), `corridor_threshold=3`.
- Model loaded at 09:06:16; incident published at 09:06:31, ~15 s. No
  `failed the fact check` / `plain-code warning` lines: the fact check passed
  first time.
- Transcript (`talk3-demo-20261005-090519.txt` beside the video, from the
  `incidents` topic's `spoken_warning`):
  > Approaching I-95N, we're seeing a slowdown impacting multiple trucks.
  > Traffic is being rerouted to avoid the congestion, with three trucks
  > experiencing significant delays. Please follow the reroute instructions for
  > a smoother journey.
- To check when reviewing: no truck numbers (take 5 named 47, 12 and 31), and
  "Traffic is being rerouted" states as done what the decision only
  recommends (`reroute_recommended: true`). Re-take if either matters for the
  cold open.

## Take 5 (M4 Max, one display)
- `deploy/recordings/talk3-demo-20261004-182716.mp4`: 54.6 s, 1314×876, H.264 +
  AAC. Raw capture, WAV and `playback.log` in `.raw-talk3-…` /
  `.talk3-audio-20261004-182716/`. **Gitignored: only on the M4 Max** — copy it
  across if the deck is built elsewhere.
- Current defaults: Pulsar 4.2.4 standalone, `GlobalSynthesisFunction` via
  localrun, `llm_backend=inprocess`, one CPU thread, Gemma-3-4B-it Q4_K_M, Piper
  `norman`.
- Third card → incident: 16.7 s, one LLM call including the model load. The fact
  check passed first time (no retry, no fallback).
- Transcript (`talk3-demo-20261004-182716.txt` beside the video):
  > Drivers approaching I-95N, be advised that there's a slowdown affecting
  > multiple trucks within the corridor. We're recommending you reroute traffic
  > around I-95N due to a correlated slowdown, particularly with trucks 47, 12,
  > and 31, who are experiencing significant delays.
- To check when reviewing: thin Terminal scrollbar edges show at the windows'
  right edges; the cards arrive ~7 s apart (4 s interval plus `pulsar-client`
  start-up).

### What the M4 Max needed (done 2026-10-04)
- Pulsar 4.2.4 (`~/tools/apache-pulsar-4.2.4`, sha512-checked) on Homebrew's
  `openjdk@21`, with `pulsar`, `pulsar-admin` and `pulsar-client` wrappers in
  `~/.local/bin` that set `JAVA_HOME`. Start the broker with `pulsar standalone`.
- `brew install ffmpeg openjdk@21`; Piper in `~/tools/piper/.venv` with the
  `norman` voice.
- `deploy/record-talk3-demo.sh` now falls back to one display: recorded windows
  on its right 70%, the Tier 2 log and the replay window on its left 30%.
- The first attempt failed at screen-capture detection, most likely while macOS
  Screen Recording permission was being granted; the retry worked.

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

## Steps for a re-take (on the take-4 machine)
1. `git pull` on `main` (`talk3-wip` was merged into it on 2026-10-05 and deleted).
2. `uv sync` at the repo root. The first sync compiles llama-cpp-python (the
   `inprocess` dependency group) with Metal: a few minutes.
3. Check the model is where `deploy/talk3-windows/tier2.sh` expects it
   (`~/tools/models/gemma-3-4b-it-GGUF/gemma-3-4b-it-Q4_K_M.gguf`) or set
   `LLM_MODEL_PATH`.
4. Run `./deploy/record-talk3-demo.sh --teardown`. `tier2.sh` sets
   `LLM_BACKEND=inprocess` (also the Function's own default since 2026-10-05)
   and `LLM_THREADS=1` (CPU only); don't override them.
5. In the Tier 2 window's log, confirm no `failed the fact check` /
   `plain-code warning` lines, or note them: if the fallback was used, the take
   shows it, and the talk should say so.
6. Expect the first warning ~15 s after the third card (model load plus an empty
   prompt cache), vs. a couple of seconds on the GPU in take 4. Extend
   `--tail` if the end gets cut off.
7. Save the transcript of the spoken warning (the speaker window's text) next to
   the recording; slides 3 and 25 quote it.

## Done when
- A new recording exists in `deploy/recordings/`, made with the current defaults,
  with its transcript.
- `docs/TALK3-SLIDE-PLAN.md` slides 3 and 25 point at it, and their `[NEEDS: new
  take]` flags are gone.
