# TODO: check Q4_0 accuracy on the Talk 2 tasks

**Status:** not started. Raised 2026-10-03 from the L3 results (`docs/TALK2-HARDWARE-SPECTRUM-TEST-CATALOG.md`).

## Why
On the flagship-Android proxy (c9g, 8 threads), Q4_0 beat the Q4_K_M files we've used everywhere. This is consistent with llama.cpp repacking Q4_0 into interleaved ARM layouts at load time:

| Model | Generation, Q4_K_M → Q4_0 | Prompt processing, Q4_K_M → Q4_0 |
|---|---|---|
| Phi-3.5-mini | 38.1 → 64.2 tok/s | 100 → 154 tok/s |
| Gemma-3-4B | 35.6 → 50.4 | 112 → 166 |
| Llama-3.1-8B | 20.0 → 31.4 | 59 → 91 |
| Gemma-3-1B | 96 → 165 | 219 → 550 |

That's 1.4-1.7× faster generation and 1.5-2.5× faster prompt processing. If accuracy holds, Q4_0 is the format to ship on an Android or Pi CPU.

Q4_0 is a simpler 4-bit scheme than Q4_K_M: no k-quant super-blocks, usually slightly worse perplexity. Nobody has measured it on our tasks.

## Check
- Run the Talk 2 evals on the Q4_0 files of the candidates, with the same flags as their Q4_K_M runs. Compare each against its own Q4_K_M numbers.
  - **Edge Triage Pipeline:** `test_compare_edge_triage_models.py`, `--model-eval-runs 15` as in row 24. Raise n if a difference needs confirming.
  - **Tier 2:** `test_compare_tier2_models.py`, n=30.
- Point the existing `models.toml` ids at the Q4_0 files through their `LLM_MODEL_PATH_*` variables for the run. No new manifest entries needed.

| Model (models.toml id) | Q4_0 file |
|---|---|
| `phi-3.5-mini-instruct-q4km` | bartowski/Phi-3.5-mini-instruct-GGUF `Phi-3.5-mini-instruct-Q4_0.gguf` |
| `gemma-3-4b-it-q4km` | unsloth/gemma-3-4b-it-GGUF `gemma-3-4b-it-Q4_0.gguf` |
| `llama-3.1-8b-instruct-q4km` | unsloth/Llama-3.1-8B-Instruct-GGUF `Llama-3.1-8B-Instruct-Q4_0.gguf` |
| `glm-4-9b-0414-q4km` | unsloth/GLM-4-9B-0414-GGUF `GLM-4-9B-0414-Q4_0.gguf` |
| `qwen3-8b-q4km` | bartowski/Qwen_Qwen3-8B-GGUF `Qwen_Qwen3-8B-Q4_0.gguf` |

- **Where:** accuracy doesn't depend on hardware, so the M4 Max is fastest. Running on an ARM CPU (a Graviton proxy, or the Pi 4) also captures Q4_0's per-call latency on the real workload.
- **Optional:** IQ4_NL is also repacked on ARM. It was a little faster than Q4_0 at generating on the 1B, but slower at prompt processing.

## Output
A row in `docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md`: per model, format / mismatch (Edge Triage) or structured / speakability / grounding (Tier 2), for Q4_K_M vs Q4_0, plus latency where it was measured on ARM.
