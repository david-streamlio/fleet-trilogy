# The LLM inside the Pulsar Function: llama-cpp-python (2026-10-04)

What changed for Talk 3, why, what it measured, and what Talks 1 and 2 should
review. Decision recorded in `docs/CANON.md` ("Language and libraries").

## The change
All three talks promise a small LLM *inside* a Pulsar Function. Until 2026-10-04
the code ran the model next to the Function instead, two ways:

| Backend | How the model runs | Model loads | Used by (before) |
|---|---|---|---|
| `SubprocessLlmBackend` | a new `llama-completion` process per call | every call | Talk 1 `EdgeEnrichmentFunction`, Talk 3 `GlobalSynthesisFunction`, the eval harness (`tests/model/conftest.py`) |
| `LlmServerBackend` | a `llama-server` process started once beside the Function, called over HTTP | once | Talk 1 `LlmTriageFunction` (Edge Triage Pipeline) |
| **`InProcessLlmBackend`** (new) | llama.cpp inside the Function's own Python process via **llama-cpp-python** (MIT) | **once, kept on `self`** | Talk 3 `GlobalSynthesisFunction` with `llm_backend=inprocess` |

`InProcessLlmBackend` (`shared/llm-inference/src/llm_inference/client.py`):
- Loads the model on the first call and keeps it; each later call reuses the part
  of the prompt the previous call already read (llama-cpp-python's KV cache, no
  extra code).
- `threads` and `gpu_layers` are load-time settings. `gpu_layers=0` (default) is
  truly CPU only: it also turns off llama.cpp's automatic GPU offloads
  (`op_offload`, `offload_kqv`), which otherwise use a Mac's GPU anyway.
- Seeds sampling randomly unless `seed=` is given. llama-cpp-python's default
  seed made every process produce identical text.
- `timeout_seconds` is enforced between generated tokens; prompt reading can't
  be interrupted in-process.
- Installed from the root `inprocess` dependency group (a default group, so a
  plain `uv sync` keeps it). PyPI ships only source, so the first sync compiles
  llama.cpp: a few minutes on a Mac, longer on a Pi.

## What it measured (Talk 3, M4 Max, Gemma-3-4B-it Q4_K_M, one CPU thread)

| How the model runs | Seconds per warning |
|---|---|
| Subprocess per call, Homebrew `llama-completion` | 29.0 |
| New model each call, llama-cpp-python built locally | 15.5 |
| **Model kept in the Function** | **12.0** |

- Same build, kept vs. reloaded: −22% (no ~1 s load, 98 of 361 prompt tokens
  reused). The bigger drop, 29.0 → 15.5 s, is the **build**: Homebrew's generic
  bottle vs. one compiled for this machine. Cause not isolated.
- Details and raw data: `eval-results/talk3-single-core-m4max-20261004/`.

## Two traps found on the way
1. **"No GPU flags" isn't CPU only.** A llama.cpp built with Metal uses the GPU
   unless told otherwise: `-dev none -ngl 0` for the CLI, `gpu_layers=0` plus
   the offload switches in-process. Talk 3's recorded take 4 ran on the GPU while
   its slides said "No GPU". Any CPU-only claim in Talks 1 and 2 needs checking
   against the flags its runs actually used. (On a Pi there's no Metal, so Pi
   numbers are CPU regardless.)
2. **Build differences can be bigger than design differences.** Compare backends
   on the same llama.cpp build, or the comparison measures the build.

## Default everywhere (2026-10-05)
After the review, `InProcessLlmBackend` became the default for every Function and
eval harness; the old backends stay available as options:

| Where | Default now | Option for the old backend |
|---|---|---|
| Talk 1 `LlmTriageFunction` (Edge Triage Pipeline) | in-process, CPU only, 12 threads, 4096 context | user config `llm_backend=server` (`LLM_BACKEND=server`) |
| Talk 1 `EdgeEnrichmentFunction` | in-process, CPU only, 4 threads | `llm_backend=subprocess` |
| Talk 3 `GlobalSynthesisFunction` | in-process, CPU only, 4 threads | `llm_backend=subprocess` |
| Eval harnesses (Edge Triage, Tier 2) | `--model-backend inprocess` | `--model-backend server` |
| Round 3 harness | llama-server, always | none: it calls llama-server's HTTP API directly |

- `InProcessLlmBackend` gained `start()`/`close()`, the same lifecycle as
  `LlmServerBackend`, so callers can hold either.
- After each call, `last_timings` records how many prompt tokens llama.cpp
  actually evaluated (the rest came from the previous call's KV cache) and the
  milliseconds spent reading the prompt vs. generating.
- **Mac GPU:** llama-server with no GPU flags ran on a Mac's Metal GPU, while
  in-process defaults to CPU only. For the old speed on a Mac, set
  `llm_gpu_layers=99` (`LLM_GPU_LAYERS=99`, harness `--model-gpu-layers 99`).
- **Reproducing published numbers:** every Talk 2 hardware-spectrum run before
  2026-10-05 used llama-server. The study's runner scripts
  (`deploy/aws-phone-proxies/scripts/bench_*.sh`) now pass
  `--model-backend server`.
- **Harness `--vary-events`:** the Edge Triage evals repeated one payload n
  times, so after the first call the whole prompt came from the cache and latency
  was generation alone. With `--vary-events`, consecutive calls carry different
  operational contexts (`eval_lib.run_edge_triage_trials_interleaved`). In
  `DEFAULT_PROMPT_TEMPLATE` the event's fields come *before* the long rules block,
  so a different event re-reads nearly the whole prompt (~400 of 514 tokens);
  `--triage-prompt event-last` (`EVENT_LAST_PROMPT_TEMPLATE`) moves them after the
  rules (148). With `--model-backend server`, also pass `--model-server-args "-np 1
  --cache-ram 0"`: llama-server's slots and host-RAM prompt cache otherwise restore
  each of the three recurring test events whole (1 token read). Results: the test
  log's "Real-stream re-measure" section and the paper's Table IV.

## To review in Talks 1 and 2
- Talk 1: `talks/talk1-edge-intelligence/TODO-INPROCESS-LLM.md`
- Talk 2: `talks/talk2-greenest-token/TODO-INPROCESS-LLM.md`
