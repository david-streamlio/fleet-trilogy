# TODO: check Q4_0 accuracy on the Talk 2 tasks

**Status:** first answer in, 2026-10-04: **accuracy depends on the model.**
- Measured on M1 Metal (mac2, run `C-workload-20261004T055729Z-q4_0`), against Q4_K_M's forward and reverse C runs. Same pairs and flags, 3 reps.
- **Reproduced on M4 Metal** (mac-m4, `C-workload-20261004T120252Z-q4_0`): Gemma-3-4B Edge Triage mismatch 0/135 → 43/135; Llama 11 → 16/135; GLM 10 → 4/135; Qwen3 0 → 2/135; Phi 0 → 0. J/call -10 to -36%.
- **Confirmed at n=45** (mac-m4, `Q-confirm-20261004T150321Z-n45`: 2 runs per format, 270 escalation calls each, Edge Triage Pipeline).

  | Model | Q4_K_M | Q4_0 | IQ4_XS | IQ4_NL |
  |---|---|---|---|---|
  | Gemma-3-4B | **0.0%** | **30.4%** | 23.3% | 16.7% |
  | Llama-3.1-8B | 6.3% | **14.4%** | — | — |

  Format was 90/90 in every case. **Every non-k 4-bit format degrades Gemma-3-4B's calibration; Q4_K_M alone stays clean.** Llama's Q4_0 shift is real (2.3×). Per-call latency within ~10% across formats.
- Still open: ARM-CPU latency for Q4_0 on the real workload.

Raised 2026-10-03 from the L3 results (`docs/TALK2-HARDWARE-SPECTRUM-TEST-CATALOG.md`).

## Result (M1, 2026-10-04)

| Pair | Escalation mismatch Q4_K_M → Q4_0 | Format | p50 s Q4_K_M → Q4_0 | J/call Q4_K_M → Q4_0 |
|---|---|---|---|---|
| Phi-3.5-mini, Edge Triage | 0/270 → 0/135 | 100% → 100% | 1.92 → 1.75 | 20.0 → 13.8 |
| Gemma-3-4B, Tier 2 | (structured 30/30, speakability 0/30, grounding 0.00 in all 9 runs) | 100% → 100% | 2.68 → 2.40 | 27.2 → 21.3 |
| **Gemma-3-4B, Edge Triage** | **0/270 → 41/135 (30%)** | 100% → 100% | 5.0 → 4.7 | 46.9 → 33.6 |
| Llama-3.1-8B, Edge Triage | 14/270 (5.2%) → 7/135 (5.2%) | 100% → 100% | 4.2 → 3.6 | 42.3 → 24.9 |
| GLM-4-9B, Edge Triage | 23/270 (8.5%) → 2/135 (1.5%) | 100% → 100% | 5.7 → 5.5 | 51.6 → 39.4 |
| Qwen3-8B, Edge Triage | 0/270 → 1/135 (0.7%) | 100% → 100% | 7.4 → 7.9 | 66.8 → 57.2 |

**What it shows:**
- On Metal, Q4_0 cuts energy per call by 14-41%, with latency within -17%/+8%.
- Quality holds or improves for four of five models. **Gemma-3-4B's escalation calibration on the Edge Triage Pipeline degrades badly**, though its Tier 2 quality is untouched. So "ship Q4_0" is a per-model, per-task decision.
- The Q4_K_M column pools 6 runs (forward + reverse, 270 escalation calls); Q4_0 is 3 runs (135).


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
