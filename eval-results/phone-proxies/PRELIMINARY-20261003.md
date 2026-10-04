# Phone-proxy preliminary results (2026-10-03 ~23:00 UTC)

Generated from eval-results/phone-proxies/ while L5-L7, A-I and G/H were still running. Proxies, not phones: see docs/TALK2-HARDWARE-SPECTRUM-TEST-CATALOG.md for caveats.

## 1. Generation speed, tg128 tok/s (Q4_K_M unless noted)

| Model | Pi 5 proxy t=4 | c7g t=8 | c9g t=8 | M1 CPU t=4 | M1 Metal | iPhone 17 Pro (pub.) |
|---|---|---|---|---|---|---|
| granite-4.0-h-350m-Q8_0 | 115.1 | 210.5 | 212.8 | 123.0 | 74.6 |  |
| LFM2.5-350M-RLCD-Q8_0 | 153.9 | 308.6 | 277.9 | 151.2 | 138.1 |  |
| qwen2.5-0.5b-instruct-q4_k_m | 65.1 | 150.5 | 183.3 | 126.2 | 111.2 |  |
| qwen3-0.6b-q8_0 | 83.9 | 176.7 | 163.4 | 87.0 | 82.6 |  |
| gemma-3-1b-it-Q4_K_M | 34.5 | 79.8 | 96.4 | 63.0 | 60.6 |  |
| Llama-3.2-1B-Instruct-Q4_K_M | 36.6 | 75.9 | 109.2 | 68.9 | 69.6 |  |
| qwen2.5-1.5b-instruct-q4_k_m | 30.5 | 60.5 | 87.7 | 55.1 | 54.3 |  |
| Qwen3.5-2B-Q4_K_M | 19.5 | 40.6 | 58.1 | 38.7 | 39.7 | 39.1 |
| Llama-3.2-3B-Instruct-Q4_K_M | 15.6 | 32.2 | 46.1 | 27.6 | 28.1 |  |
| qwen2.5-3b-instruct-q4_k_m | 16.2 | 33.0 | 46.7 | 28.7 | 29.3 |  |
| Phi-3.5-mini-instruct-Q4_K_M | 12.2 | 27.0 | 38.1 | 23.9 | 24.3 |  |
| gemma-3-4b-it-Q4_K_M | 12.1 | 24.6 | 35.6 | 22.1 | 22.9 |  |
| gemma-4-E2B-it-Q4_K_M | 18.8 | 40.4 | 54.6 | 31.7 | 35.4 | 38.8 |
| Ling-3.0-tiny-Q4_K_M | 30.5 | 58.6 | 81.3 | 56.9 | 48.7 |  |
| Llama-3.1-8B-Instruct-Q4_K_M | 7.2 | 14.6 | 20.0 | 12.4 | 12.7 |  |
| qwen3-8b-q4_k_m | 6.9 | 14.4 | 19.7 | 12.2 | 12.5 |  |
| GLM-4-9B-0414-Q4_K_M | 6.1 | 13.8 | 19.5 | 9.9 | 10.1 |  |

## 2. Prompt processing, pp512 tok/s

| Model | Pi 5 proxy t=4 | c7g t=8 | c9g t=8 | M1 CPU t=4 | M1 Metal |
|---|---|---|---|---|---|
| granite-4.0-h-350m-Q8_0 | 369.4 | 1004.9 | 1538.2 | 918.9 | 1113.8 |
| LFM2.5-350M-RLCD-Q8_0 | 467.4 | 1153.1 | 1854.3 | 1443.2 | 3104.1 |
| qwen2.5-0.5b-instruct-q4_k_m | 102.8 | 232.4 | 364.0 | 856.7 | 2015.6 |
| qwen3-0.6b-q8_0 | 236.8 | 265.2 | 389.3 | 767.4 | 1757.0 |
| gemma-3-1b-it-Q4_K_M | 56.4 | 139.1 | 218.7 | 466.4 | 1087.2 |
| Llama-3.2-1B-Instruct-Q4_K_M | 96.7 | 242.3 | 361.1 | 332.5 | 885.3 |
| qwen2.5-1.5b-instruct-q4_k_m | 70.4 | 164.5 | 244.7 | 238.1 | 639.5 |
| Qwen3.5-2B-Q4_K_M | 58.0 | 171.1 | 263.3 | 191.6 | 534.4 |
| Llama-3.2-3B-Instruct-Q4_K_M | 33.3 | 81.8 | 121.4 | 116.2 | 304.8 |
| qwen2.5-3b-instruct-q4_k_m | 34.0 | 83.3 | 125.6 | 117.0 | 309.4 |
| Phi-3.5-mini-instruct-Q4_K_M | 24.8 | 64.1 | 100.0 | 86.0 | 224.1 |
| gemma-3-4b-it-Q4_K_M | 29.3 | 74.2 | 112.0 | 101.4 | 266.8 |
| gemma-4-E2B-it-Q4_K_M | 34.5 | 70.6 | 113.6 | 156.5 | 406.9 |
| Ling-3.0-tiny-Q4_K_M | 61.7 | 81.7 | 158.5 | 180.9 | 593.9 |
| Llama-3.1-8B-Instruct-Q4_K_M | 14.0 | 38.9 | 58.7 | 49.2 | 126.1 |
| qwen3-8b-q4_k_m | 13.9 | 38.0 | 56.7 | 48.9 | 124.7 |
| GLM-4-9B-0414-Q4_K_M | 9.7 | 27.0 | 41.1 | 42.2 | 106.7 |

## 3. Talk 2 real workload on M1 (Metal), mean of 3 reps; idle 40 mW subtracted

| Task / model | Calls/rep | J/call above idle (range) | Avg power W | p50 / p95 s | Format | Mismatch |
|---|---|---|---|---|---|---|
| edge_triage_phi-3.5-mini-instruct-q4km | 60 | **20.0** (19.9-20.1) | 9.5 | 1.91 / 2.21 | 100% | 0.0% |
| tier2_gemma-3-4b-it-q4km | 30 | **27.1** (26.9-27.4) | 9.1 | 2.67 / 3.68 | 100% |  |
| edge_triage_gemma-3-4b-it-q4km | 60 | **46.9** (46.7-47.3) | 9.2 | 5.02 / 6.11 | 100% | 0.0% |
| edge_triage_llama-3.1-8b-instruct-q4km | 60 | **42.5** (41.7-43.9) | 8.7 | 4.32 / 7.68 | 100% | 3.7% |
| edge_triage_glm-4-9b-0414-q4km | 60 | **52.0** (50.9-52.9) | 8.1 | 5.74 / 9.62 | 100% | 5.9% |
| edge_triage_qwen3-8b-q4km | 60 | **66.9** (65.8-67.8) | 8.7 | 7.31 / 9.66 | 100% | 0.0% |

## 4. L1 RAM capacity (c9g, cgroup caps, weights resident)

model,file_gb,peak_rss_gb,4G,6G,8G,12G
granite-4.0-h-350m-Q8_0,0.37,0.55,fit,fit,fit,fit
LFM2.5-350M-RLCD-Q8_0,0.38,0.53,fit,fit,fit,fit
qwen2.5-0.5b-instruct-q4_k_m,0.49,0.60,fit,fit,fit,fit
qwen3-0.6b-q8_0,0.80,0.95,fit,fit,fit,fit
gemma-3-1b-it-Q4_K_M,0.81,1.25,fit,fit,fit,fit
Llama-3.2-1B-Instruct-Q4_K_M,0.81,1.18,fit,fit,fit,fit
qwen2.5-1.5b-instruct-q4_k_m,1.12,1.27,fit,fit,fit,fit
Qwen3.5-2B-Q4_K_M,1.28,1.89,fit,fit,fit,fit
Llama-3.2-3B-Instruct-Q4_K_M,2.02,2.56,fit,fit,fit,fit
qwen2.5-3b-instruct-q4_k_m,2.10,2.27,fit,fit,fit,fit
Phi-3.5-mini-instruct-Q4_K_M,2.39,2.71,fit,fit,fit,fit
gemma-3-4b-it-Q4_K_M,2.49,3.26,fit,fit,fit,fit
gemma-4-E2B-it-Q4_K_M,3.11,3.57,fit,fit,fit,fit
Ling-3.0-tiny-Q4_K_M,4.82,5.01,fail(137),fit,fit,fit
Llama-3.1-8B-Instruct-Q4_K_M,4.92,5.20,fail(137),fit,fit,fit
qwen3-8b-q4_k_m,5.03,5.29,fail(137),fit,fit,fit
GLM-4-9B-0414-Q4_K_M,6.17,6.38,fail(137),fit,fit,fit
Qwen3-14B-Q4_K_M,9.00,9.30,fail(137),fail(137),fail(137),fit
gemma-3-12b-it-Q4_K_M,7.30,8.52,fail(137),fail(137),fit,fit
gemma-4-12b-it-Q4_K_M,7.12,8.12,fail(137),fail(137),fit,fit

## 5. L3 ARM quants on c9g, t=8 (vs Phase 1 Q4_K_M)

| File | pp512 | tg128 |
|---|---|---|
| GLM-4-9B-0414-IQ4_NL | 54.1 | 26.0 |
| GLM-4-9B-0414-Q4_0 | 76.5 | 26.9 |
| GLM-4-9B-0414-Q8_0 | 70.7 | 18.5 |
| Llama-3.1-8B-Instruct-IQ4_NL | 64.2 | 30.0 |
| Llama-3.1-8B-Instruct-Q4_0 | 91.1 | 31.4 |
| Meta-Llama-3.1-8B-Instruct-Q8_0 | 88.4 | 21.7 |
| Phi-3.5-mini-instruct-Q4_0 | 154.4 | 64.2 |
| Phi-3.5-mini-instruct-Q8_0 | 151.6 | 41.9 |
| Qwen3-8B-IQ4_NL | 62.4 | 29.1 |
| Qwen3-8B-Q8_0 | 84.5 | 21.4 |
| Qwen_Qwen3-8B-Q4_0 | 88.8 | 30.6 |
| gemma-3-1b-it-IQ4_NL | 429.5 | 170.4 |
| gemma-3-1b-it-Q4_0 | 549.8 | 164.7 |
| gemma-3-1b-it-Q8_0 | 541.1 | 136.0 |
| gemma-3-4b-it-IQ4_NL | 122.6 | 48.6 |
| gemma-3-4b-it-Q4_0 | 165.5 | 50.4 |
| gemma-3-4b-it-Q8_0 | 162.6 | 39.9 |

Phase 1 Q4_K_M at t=8 for reference: gemma-3-1b-it-Q4_K_M: pp 218.7 / tg 96.4, Phi-3.5-mini-instruct-Q4_K_M: pp 100.0 / tg 38.1, gemma-3-4b-it-Q4_K_M: pp 112.0 / tg 35.6, Llama-3.1-8B-Instruct-Q4_K_M: pp 58.7 / tg 20.0, GLM-4-9B-0414-Q4_K_M: pp 41.1 / tg 19.5, qwen3-8b-q4_k_m: pp 56.7 / tg 19.7

## 6. L4 12-14B on c9g

| Model | pp512 t=4 | pp512 t=8 | tg128 t=4 | tg128 t=8 |
|---|---|---|---|---|
| Qwen3-14B-Q4_K_M | 17.0 | 31.6 | 8.1 | 13.9 |
| gemma-3-12b-it-Q4_K_M | 19.8 | 35.6 | 9.2 | 15.6 |
| gemma-4-12b-it-Q4_K_M | 18.1 | 32.4 | 9.8 | 16.5 |

## 7. L2 Cortex-X1 ISA build vs native on c7g, t=8 (partial)

| Model | native pp / tg | x1 pp / tg | x1/native pp | x1/native tg |
|---|---|---|---|---|
| granite-4.0-h-350m-Q8_0 | 1004.9 / 210.5 | 1021.8 / 216.7 | 1.02 | 1.03 |
| LFM2.5-350M-RLCD-Q8_0 | 1153.1 / 308.6 | 1341.4 / 310.6 | 1.16 | 1.01 |
| qwen2.5-0.5b-instruct-q4_k_m | 232.4 / 150.5 | 314.0 / 156.6 | 1.35 | 1.04 |
| qwen3-0.6b-q8_0 | 265.2 / 176.7 | 653.5 / 172.9 | 2.46 | 0.98 |
| gemma-3-1b-it-Q4_K_M | 139.1 / 79.8 | 173.6 / 83.2 | 1.25 | 1.04 |
| Llama-3.2-1B-Instruct-Q4_K_M | 242.3 / 75.9 | 255.9 / 84.7 | 1.06 | 1.12 |
| qwen2.5-1.5b-instruct-q4_k_m | 164.5 / 60.5 | 185.3 / 67.8 | 1.13 | 1.12 |
| Qwen3.5-2B-Q4_K_M | 171.1 / 40.6 | 162.8 / 44.3 | 0.95 | 1.09 |
| Llama-3.2-3B-Instruct-Q4_K_M | 81.8 / 32.2 | 87.7 / 35.7 | 1.07 | 1.11 |
| qwen2.5-3b-instruct-q4_k_m | 83.3 / 33.0 | 89.0 / 37.0 | 1.07 | 1.12 |
| Phi-3.5-mini-instruct-Q4_K_M | 64.1 / 27.0 | 68.6 / 29.5 | 1.07 | 1.09 |
| gemma-3-4b-it-Q4_K_M | 74.2 / 24.6 | 76.9 / 27.1 | 1.04 | 1.10 |
| gemma-4-E2B-it-Q4_K_M | 70.6 / 40.4 | 102.3 / 44.6 | 1.45 | 1.10 |
| Ling-3.0-tiny-Q4_K_M | 81.7 / 58.6 | 167.2 / 64.5 | 2.05 | 1.10 |
| Llama-3.1-8B-Instruct-Q4_K_M | 38.9 / 14.6 | 36.0 / 16.3 | 0.93 | 1.12 |

## 8. Repeatability: mac2 Phase 1 vs its first repeat (E)

- metal-tg-tg: median |Δ| 0.2%, max 1.1% over 17 models
- metal-pp-pp: median |Δ| 0.2%, max 3.8% over 17 models
- cpu-tg: median |Δ| 0.1%, max 3.5% over 17 models

## 9. Per-call latency on Talk 2's real workload, p50 / p95 seconds

Edge Triage Pipeline (`--model-eval-runs 15` = 60 calls per run on the Pi 4 and M1):

| Model | Pi 4 (external fan, impact track rows 25-26) | M1 Metal (test C, mean of 3 runs) | M4 Max |
|---|---|---|---|
| Phi-3.5-mini | 31.7 / 38.8 | 1.91 / 2.21 | 0.36 / 0.41 (2026-10-02 single-model runs, mean of 3) |
| Gemma-3-4B | 78.8 / 102.7 | 5.02 / 6.11 | 2.05 / 2.37 † |
| Llama-3.1-8B | 72.5 / 230.3 | 4.32 / 7.68 | 1.25 / 2.12 † |
| GLM-4-9B | 103.6 / 300.1 * | 5.74 / 9.62 | 1.50 / 2.69 † |
| Qwen3-8B | 128.8 / 300.1 * | 7.31 / 9.66 | 2.24 / 2.72 † |

Tier 2 (n=30):

| Model | Pi 4 | M1 Metal | M4 Max |
|---|---|---|---|
| Gemma-3-4B | 43.6 / – | 2.67 / 3.68 | 0.51 / 0.65 (2026-10-02, mean of 3) |

\* 300 s is the per-call timeout: those tails are timeouts.
† The M4 Max's published five-model run (2026-09-26T215201Z, all five models in one session). In that run Phi measured 0.75 s against 0.36 s in its own single-model runs, so † figures likely overstate the M4 Max's per-call time. Undiagnosed; see impact track row 24's detail.
M1 runs, like the 2026-10-02 M4 Max runs, are one model per session with Metal and `--model-threads 4`.
