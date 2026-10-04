# Paper outline (IEEE style, Markdown draft)

**Working title:** *Can Phones Democratize Edge Intelligence? Latency, Energy and Capacity of Small Language Models Across the Consumer Hardware Spectrum*

**Status:** outline, started 2026-10-04 after rounds 1-2 of the hardware-spectrum runs.
- Talk 2 presents this study; the paper is the standalone, reviewable artifact.
- Numbers below marked **[prelim]** come from `eval-results/phone-proxies/PRELIMINARY-20261003.md` and the test log. A final analysis script must regenerate every figure and table from the raw data before submission.
- Sources:
  - methods, run IDs and incidents: `TALK2-HARDWARE-SPECTRUM-TEST-LOG.md`
  - the index: `TALK2-HARDWARE-SPECTRUM-TEST-CATALOG.md`
  - reproduction: `deploy/aws-phone-proxies/REPRODUCE.md`

---

## Abstract (≈200 words, write last)

Contents, in order:
1. **Problem.** Edge intelligence for connected fleets: an LLM triages telemetry on the vehicle instead of streaming raw data to the cloud.
2. **Question.** Is phone-class hardware now capable and efficient enough to make that broadly accessible?
3. **Method.** Identical models and runtime (llama.cpp v0.5.0; 17 GGUF models, 0.35-9.4B parameters) across a Raspberry Pi 4, EC2 stand-ins for a Pi 5 and mainstream/flagship Android CPUs, Apple M1 and M4 Mac minis (iPhone-class SoCs), and an M4 Max laptop. Synthetic throughput, a real two-task workload with ground truth, chip-level energy, memory-capacity limits, and software levers (quantization format, runtime, ISA, context size).
4. **Headline results** [prelim]:
   - Phone-class silicon answers the triage call in ~1-2 s vs ~32 s on the Pi 4, at ~8× less energy per call.
   - Q4_0 cuts energy per call 10-41% but breaks one model's calibration.
   - Laptop thermals trade speed for energy.
5. **Takeaway.** The hardware gap has closed; deployment details (quantization, context defaults, thermals) now decide outcomes.

**Index terms:** edge AI, small language models, energy efficiency, mobile inference, llama.cpp, quantization, benchmarking.

---

## I. Introduction

- **Motivation.** Fleet telemetry; the cost of streaming everything to the cloud: uplink data and radio energy (impact-track row 28: an LTE radio tail of ~12.8 J per isolated uplink, Huang et al. 2012). Talk 1's Edge Triage Pipeline as the concrete workload.
- **The 2021 baseline.** A Raspberry Pi 4 needed the task narrowed (impact-track row 5: severity and action moved to deterministic code; the LLM kept a bounded escalation) and still took ~32-129 s per call, throttling without a fan.
- **The question.** Five years on, can the device most people already carry, a phone, do this job?

**Research questions:**

| | Question |
|---|---|
| RQ1 (speed) | How do identical small LMs perform across the consumer spectrum, for prompt processing and generation? |
| RQ2 (energy) | What does one real triage decision cost in energy per call on each class of device? |
| RQ3 (capacity) | Which model sizes fit which device memory classes? |
| RQ4 (software levers) | How much do quantization format, inference runtime, ISA-targeted builds and server defaults move speed, energy and accuracy? |
| RQ5 (sustained behaviour) | How do thermals change speed and energy under sustained load? |
| RQ6 (quality) | Does task accuracy hold across hardware and quantization? |

**Contributions:**
1. A cross-spectrum measurement on one runtime and one model set. EC2 proxies are chosen by core lineage, and their fidelity is quantified by measured bandwidth, ISA and calibration against published phone figures.
2. Chip-level energy per call on a real workload with ground truth, compared with a wall-metered Pi 4.
3. Negative and confounding findings that matter for deployment:
   - multi-model sessions double latency;
   - default context sizes OOM-kill 16 GB CPU hosts;
   - Q4_0 can silently break calibration;
   - laptop thermal regimes.
4. A fully reproducible artifact: Terraform, scripts, pinned versions, 105 model hashes, raw data.

## II. Background and related work

- **On-device LLM inference.** llama.cpp/GGML and its quantization formats (k-quants, Q4_0, IQ4); runtime weight repacking on ARM; MLX on Apple silicon.
- **Mobile LLM benchmarking and energy.** MELT (~0.72 J/token on phones) [cite, verify]; community measurements (apple-silicon-llm-bench: iPhone 17 Pro Gemma-4-E2B 38.8 tok/s, 0.26 J/token) [verify provenance and method].
- **Memory-bound generation.** Roofline (Williams et al., CACM 2009) [verify]; STREAM (McCalpin 1995) [verify].
- **Thermal management and DVFS** on mobile and laptop SoCs [cite].
- **Radio energy and the cost of offloading.** Huang et al., MobiSys 2012 (LTE); Nepal et al., arXiv:2601.17656 (LTE-M) [verify].
- **Positioning.** Prior work reports tok/s or J/token on synthetic prompts; this paper measures a task-scored workload across the spectrum, with confounds controlled and published.

## III. Methodology

### A. Workloads
1. **Synthetic:**
   - llama-bench pp512 / tg128, 3 repetitions, plus thread sweeps (A);
   - context depth 0-4096 (D, L5);
   - sustained generation (F);
   - Phase 2: 12-27B models (I, L4).
2. **Real workload (C, L7):** the Edge Triage Pipeline eval and the Tier 2 spoken-warning eval from the talk series.
   - Ground truth: the fleet simulator's incident model.
   - Gates: format reliability → grounding → escalation calibration (gate 2).
   - Run sizes: Edge Triage 60 calls (15 format + 45 escalation), Tier 2 30 calls.
   - Same prompts, harness and flags on every platform.

### B. Platforms and proxy fidelity

Table T1: device, stand-in, cores, RAM, measured STREAM bandwidth, ISA features. Fidelity argument:
- **Core lineage:**

  | Proxy | Stands in for |
  |---|---|
  | Neoverse N1 | Cortex-A76 (Pi 5) |
  | Neoverse V1 | Cortex-X1 class |
  | Neoverse V3 | Cortex-X4 class |
  | M1 | A14 |
  | M4 | A18 |

- **Bandwidth:** the proxies have 1.4-5× the target devices', so their speeds are upper bounds. The M1's generation speed matches published iPhone 17 Pro figures within 2-9% (similar bandwidth).
- **ISA:** a Cortex-X1-faithful build (no SVE or i8mm) was *faster* than native on Graviton3, so the ISA didn't inflate the proxy.
- **A stated preference:** hardware-real measurement over analytic bandwidth "correction".

### C. Energy measurement
- **macOS:** `powermetrics` CPU+GPU+ANE package power at 500 ms.
  - Sample times are rebuilt per gap-free segment.
  - Energy above an idle baseline from interleaved idle windows.
  - Per-test intervals come from llama-bench's per-repetition times; per-call energy is session energy ÷ calls (an upper bound, harness and load included).
- **Pi 4:** an inline USB-C meter (whole board, at the wall).
- **Graviton:** no energy counters, so time only.
- **Different coverage:** chip vs wall is a stated asymmetry (§VI).

### D. Protocol and controls
- **Repetition:** 3 reps; run-to-run variance (E: median 0.1-0.2% on mac2).
- **Order:** a reverse-order C on mac2 showed no effect.
- **Thermals:** M4 Max sessions gated on Nominal thermal pressure, in reverse order. Both Mac minis stayed Nominal throughout.
- **Sessions:** single-model only; five-model sessions doubled latency (§V).
- **Integrity:** model SHA-256 checked on every host against the lock file; JSON validity; window exit codes.

### E. Reproducibility
Terraform stack, pinned versions, `MODELS.lock.tsv`, runbook, raw data with gzipped power traces. Cost ≈ $25-30 plus the Mac hosts' 24 h minima.

## IV. Results (one subsection per RQ; figure/table plan → data)

| RQ | Figure / table | Data |
|---|---|---|
| RQ1 | **F1** tg128 vs measured bandwidth, all platforms; **F2** pp512 Metal vs CPU | Phase 1 runs; STREAM (B, Linux stream_t*) |
| RQ1 | **F3** CPU thread scaling (M1 A; Graviton sweeps) | A, Phase 1 Linux |
| RQ1 | **F4** speed vs context depth | D, L5 |
| RQ2 | **T3** per-call latency p50/p95 + J/call, real workload, by platform | C (mac2, mac-m4), M4 Max reruns, Pi 4 rows 24-26, L7 (latency only) |
| RQ2 | **F5** J/call by platform (log scale) | same |
| RQ3 | **F6** fits matrix (models × 4/6/8/12 GiB) | L1 `fits.csv` |
| RQ4 | **F7** Q4_0 / IQ4 / Q8_0 vs Q4_K_M: speed (ARM CPU, Metal), energy, accuracy | L3, G, C-q4_0, Q-confirm |
| RQ4 | **F8** MLX vs llama.cpp Metal | H |
| RQ4 | **T4** deployment pitfalls (context default OOM, multi-model sessions) | L7 first run, M4 Max five-model session |
| RQ5 | **F9** M4 Max cool vs warm: latency and J/call per model | gated-reverse vs caffeinated |
| RQ5 | **F10** sustained drift (Mac minis) | F (both) |
| RQ6 | **T5** quality by platform and quantization | all C/L7 artifacts, Pi 4 rows |

**Headline numbers so far** [prelim]:
- **Real workload, Phi-3.5-mini, Edge Triage:**

  | Platform | p50 per call | J/call |
  |---|---|---|
  | Pi 4 | 31.7 s | 154 (wall) |
  | M1 | 1.9 s | 20 |
  | M4 | 1.2 s | 15 |
  | M4 Max | 0.36 s | 15 |
  | c9g CPU | 1.08 s | — |

- **Capacity:** ≤ 4B-class fits 4 GiB; 8-9B needs 6 GiB; 12B 8 GiB; 14B 12 GiB.
- **Q4_0:** -10 to -41% J/call on Metal; ARM CPU 1.4-1.7× faster generation; Gemma-3-4B Edge Triage mismatch 0% → ~30% (on M1 and M4).
- **M4 Max:** cool sessions 24-77% faster but 30-60% more J/call than throttled.
- **M4 Mac mini** generation is ~1.5-1.7× the iPhone 17 Pro's; M1 ≈ iPhone 17 Pro.

## V. Discussion

- **Democratization verdict.** Phone-class SoCs clear the latency bar for real-time triage and approach laptop-GPU energy per call. The binding constraints are now memory capacity (an app's share of RAM), thermals and software choices, not raw speed.
- **Economics and energy at fleet scale.** Per-call energy plus the radio energy avoided by not uplinking raw data (row 28). Always-on idle cost on dedicated boxes (Pi idle ≈ half its per-call wall energy).
- **Deployment guidance:**
  - pin the context size;
  - one model per server process;
  - choose the quantization per model and task, and validate quality;
  - budget for thermal regimes.
- **What phones add that proxies can't show:** sustained throttling, app memory budgets, NPU paths.

## VI. Threats to validity

1. **Proxy fidelity:** bandwidth, caches and clocks differ (§III-B). Mitigated by calibration and labelled as upper bounds; resolved only by real devices.
2. **Energy coverage:** chip-only (powermetrics) vs wall (Pi). The direction favours the Macs; ~5× headroom remains after doubling.
3. **Harness overhead in per-call energy:** startup and load included, so upper bounds.
4. **Thermal state and order:** controlled on the M4 Max (gating), absent on the Mac minis; residual within-session heating remains.
5. **Single task domain** (fleet incident triage); quality results may not transfer.
6. **Published comparison numbers:** method and runtime unverified.
7. **Quantization provenance:** different converters (unsloth / bartowski / ggml-org). Pinned by hash, but not one converter.
8. **Sample sizes:** n=45 escalation calls per run; the confirmation run raises Gemma's to 270 new calls per format.

## VII. Future work
- **Real phones** on AWS Device Farm (`TODO-REAL-PHONE-BENCHMARKS.md`): sustained throttling, app memory budgets.
- **A harder task** (round 3), now that hardware allows. Candidates under discussion: un-narrowing the task, reasoning mode on/off, root-cause and fleet correlation, the uplink gate.
- A real Pi 5 with the inline meter; NPU/ANE paths.

## VIII. Conclusion (write last)

## Appendix: artifact availability
Repository paths, commit IDs (`8512294`, `bca0e0d`, later), the runbook, the lock file, and the data layout.

---

## Open items before drafting prose
- [ ] Final analysis script (one command → every figure and table), replacing `prelim_report.py`.
- [ ] Fold in the Q-confirm n=45 run.
- [ ] Decide on round 3 (harder task) and whether it belongs in this paper or a follow-up.
- [ ] Verify every citation marked [verify]. Get the MELT and apple-silicon-llm-bench methods.
- [ ] Re-check impact-track rows that used the invalid 2026-09-26 multi-model M4 latencies.
- [ ] Choose the venue (IEEE conference vs journal), which sets the page budget.
