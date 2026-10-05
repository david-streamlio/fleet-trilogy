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

## To review in Talks 1 and 2
- Talk 1: `talks/talk1-edge-intelligence/TODO-INPROCESS-LLM.md`
- Talk 2: `talks/talk2-greenest-token/TODO-INPROCESS-LLM.md`
