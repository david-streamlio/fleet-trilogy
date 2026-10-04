# Talk 2 hardware-spectrum test catalog

**The question:** can phones democratize edge intelligence? Measure the same models across the consumer computing spectrum (Pi → phones → laptops), 5 years on from the Pi 4 baseline.

This is the index of every test: done, running, proposed, deferred and rejected. Results live in `eval-results/`. Measured rows go into `TALK2-DATA-ENGINEERING-IMPACT-TRACK.md`. Last updated 2026-10-04 19:45 UTC.

## Done

| Test | Where | Result / location |
|---|---|---|
| Pi 4 per-call accuracy, latency and energy (inline USB-C meter), no fan → first fan → external fan | Pi 4 | Impact track rows 22-26 |
| M4 Max per-call energy (`powermetrics`, chip only) | the user's M4 Max laptop | Impact track row 24 (contrast) |
| Uplink data + radio energy (what per-call energy leaves out) | analysis | Impact track row 28, `tests/model/uplink_budget.py` |
| Proxy smoke test, c9g (1 model, 1 rep) | android-flagship | `eval-results/phone-proxies/android-flagship/20261003T180853Z/` |
| mac2 smoke test; it caught 3 bugs, all fixed | iphone-older | `eval-results/phone-proxies/iphone-older/20261003T190533Z/` |
| **Phase 1 full suite, mac2 (M1)**: 17 models, 3 reps, Metal + CPU (t=4), energy per token | iphone-older | `eval-results/phone-proxies/iphone-older/20261003T191829Z/`; `scripts/summarize.py` |

**mac2 headline:** on the two calibration models, M1's Metal generation matches published iPhone 17 Pro figures:

| Model | M1 Metal | iPhone 17 Pro (published, apple-silicon-llm-bench) |
|---|---|---|
| Gemma-4-E2B | 35.4 tok/s, 0.28 J/tok | 38.8 tok/s, 0.26 J/tok |
| Qwen3.5-2B | 39.7 tok/s | 39.1 tok/s |

Memory bandwidth is close: M1 68 GB/s, A19 Pro 76.8 GB/s.
- So mac2 is a good stand-in for **iPhone 17 Pro generation speed**.
- For the **iPhone 12** (A14, 34 GB/s), it overstates generation about 2×.

Caveat: the published runtime and measurement method aren't verified to match ours.

## Running

**Round 1 is complete.** Every run had finished by 2026-10-04 03:53 UTC (§ below kept as the run record). Collection: c9g 01:17, c7g and mac2 ~04:20 UTC.

**Round 2 (2026-10-04, second test suites): complete.** mac2 collected 07:20, the mac-m4 14:55 UTC (all checks pass; results in the test log §5 Round 2). These are additions; round-1 data is kept unchanged. Labels and the retention rule are in the test log §5 "Round 2".
- **C-reverse** (mac2): order-effect check.
- **C-q4_0** (mac2): the Q4_0 accuracy check, with energy.
- **M4 Max gated-reverse:** thermal-gated, reverse order.
- **iphone-flagship full suite** (mac-m4.metal, us-west-2b, ≥ $29.52, releasable 2026-10-05 04:29 UTC).
- Android proxies destroyed 04:26 UTC after collection.

**Round 3 (2026-10-04): a harder task, and thinking on vs off. Running.** Details, run IDs and first results: test log §5 "Round 3". Tabulate with `scripts/round3_report.py`.
- **Task:** undo the Pi-era narrowing. The LLM classifies the baseline severity, decides the escalation, and derives the final severity and action, scored exactly against the deterministic code. The production (narrow) task runs alongside as the baseline.
- **Modes:** raw (production), Qwen chat format with thinking off, on (2,048-token budget), and budget-forced (1,024).
- **Done:** M4 Max, 10 models, 15:37-19:00 UTC. Accuracy valid; latency and energy wait on the context-size check (test log incident 23).
- **Done:** mac2 (20:13, collected 20:15) and the mac-m4 (19:40), 28 sessions each (Qwen3.5-9B chat-on skipped by user decision).
- **Running:** the M4 Max 4,096-token think-budget re-run; on the mac-m4, the follow-ups (the same ablation and think-budget re-run; queued by the other session, now owned here).
- **Queued:** M4 Max context-size check → prompt ablation (4 models × 7 variants) → budget forcing. mac-m4 budget forcing re-run after its follow-ups (the first attempt failed: test log incident 24).
- **First finding:** the narrowing was justified (raw full task ≤ 58% end to end; the small models 11-22%). The chat format lifts Qwen3-14B and Qwen3.5-9B to 72%; thinking adds little for 4-11× the latency; Qwen3.5-9B's thinking runs away.

**Phase 1 full suite on the Linux proxies:** 17 models, 3 reps, a thread sweep, and STREAM bandwidth at each thread count. Each is collected automatically when it finishes.
All three finished 2026-10-03 and are collected.
- android-flagship (c9g, Graviton5): ~20:25 UTC.
- android-mainstream (c7g, Graviton3): ~21:05 UTC. All 17 models are complete. `bench.sh` was overwritten in place by `start-extras` while the run was finishing, so its last lines failed: no `LATEST`, and an empty stray `llama-bench_cpu_GLM…json` (removed). Recorded in that run's `NOTE.txt`. `proxyctl.sh` now pushes by copy-then-rename, which can't corrupt a running script.
- pi5 (c6g, Graviton2): 21:33 UTC, all 17 models verified. The instance was shut down 22:39 UTC (teardown below).

Partial results (generation tok/s at full threads; c9g/c7g at t=8):

| Model | c9g | c7g | M1 Metal | iPhone 17 Pro (published) |
|---|---|---|---|---|
| Qwen3.5-2B | 58.1 | 40.6 | 39.7 | 39.1 |
| Gemma-4-E2B | 54.6 | 40.4 | 35.4 | 38.8 |
| Gemma-3-4B | 35.6 | 24.6 | 22.9 | — |

- **c9g is ~1.4-1.5x an iPhone 17 Pro,** in line with its higher bandwidth (~120 vs ~77-85 GB/s). Read it as an upper bound for flagship phones.
- **c7g has the most bandwidth (202 GB/s) yet generates slower.** Its speed still scales almost linearly with threads, so its older cores' compute is the limit. A bandwidth-ratio correction would have got this wrong.

**mac2 extras queue, unattended** (`scripts/bench_extras.sh`, started 2026-10-03 20:01 UTC): E → A → B → D → E → F → I → E, ~5.5-6 h of tests.
- Test I runs Gemma-3-12B, **Gemma-4-12B** and Qwen3-14B.
- B uses 80M-element arrays: macOS's linker can't hold the Linux proxies' 200M. A quick check gave 58 GB/s at 1 thread, 48 GB/s at 8, against a 68 GB/s peak.
- D reports speed only: llama-bench re-fills the context, untimed, before every repetition, so energy can't be separated from it.

**C (Talk 2's real workload on M1), approved 2026-10-03; ran 20:31-~22:01 UTC, all 18 windows exit 0** (results/C-workload-20261003T203147Z).
- Smoke test passed: Phi-3.5-mini on the Edge Triage Pipeline (1 eval run), 100% format, 0% mismatch, **1.9 s p50 per call**. For comparison, the Pi 4 does 31.7 s and the M4 Max 0.36 s.
- The H (MLX) smoke test passed in the same pause: Gemma-3-1B 4-bit pp512 1131 tok/s, **tg128 83 tok/s** (llama.cpp Metal Q4_K_M: 1087 / 61).
- `scripts/bench_workload.sh` runs inside a pause of the extras queue, then resumes it.
- It uses the row 24 pairs and flags (Phi on the Edge Triage Pipeline with `--model-eval-runs 15`; Gemma-3-4B on Tier 2 with 30), plus Gemma-3-4B, Llama-3.1-8B, GLM-4-9B and Qwen3-8B on the Edge Triage Pipeline. 3 reps each under `powermetrics`, Metal `llama-completion`, `--model-threads 4`.
- The repo's source (no `.git`, `docs`, `eval-results` or `deploy`) was copied to `~/fleet-trilogy` on mac2 for this. It goes away with the instance.

**G and H, queued 2026-10-03** (`scripts/bench_extras_gh.sh`). They start by themselves when the extras queue writes its `.finished` marker. Their downloads and MLX install run before any measurement window.
- **G:** Q4_0, Q8_0 and IQ4_XS of Gemma-3-1B, Llama-3.2-3B, Phi-3.5-mini and Gemma-3-4B, in Phase 1's four windows per model. The Q4_K_M rows come from Phase 1.
- **H:** `scripts/mlx_bench.py` (mlx-lm 0.32.0, pp512 / tg128, 3 reps, per-trial epoch times for exact energy attribution) on nine mlx-community 4-bit models. MLX 4-bit (~4.5 bits/weight) sits between GGUF Q4_0 and Q4_K_M.
- **Expected order on mac2:** C (in a pause), then the rest of the extras queue, then G, then H. Finishes ≈ 2026-10-04 09:00 UTC, ~10 h before the host can be released.

**M4 Max reruns on the user's MacBook** (`scripts/bench_workload_m4max.sh`, llama.cpp v0.5.0; details in the test log §5):
- `20261003T230334Z`: 17 sessions. The machine idle-slept after 23:30:48.
- `20261004T003435Z-resume`: Qwen3-8B r3, a GLM check rep and the five-model session.
- **Finding:** a five-model session roughly doubles Phi's latency (0.70 vs 0.36 s). That is what inflated the 2026-09-26 numbers, so use single-model sessions only.
- **Finding:** after 16:10 PDT the first run's sessions drew about half the power and ran 15-25% slower than reps held awake. Idle-state scheduling vs heat is unresolved.
- **Re-run in progress:** `…-caffeinated`, all 18 single-model sessions under `caffeinate -dims`, with `powermetrics … thermal` in `/tmp/m4max-powermetrics-2.txt`. Started 2026-10-04 ~00:58 UTC.

**Reproducibility package (2026-10-04):**
- `deploy/aws-phone-proxies/REPRODUCE.md`: runbook with every pinned version.
- `MODELS.lock.tsv`: 105 model files with revision and SHA-256 (104 + round 3's Qwen3.5-9B).
- `docs/TALK2-HARDWARE-SPECTRUM-TEST-LOG.md`: the lab notebook (methods, run IDs, incidents, caveats).
- **Prepared for publishing:** mac2 host identifiers redacted (and no longer recorded); power traces committed as `.txt.gz`.

## Awaiting a decision

- ~~**mac-m4 Phase 1.**~~ Decided 2026-10-04: allocated as iphone-flagship; its full suite ran in round 2.
- **Time box (user, 2026-10-04):** this round ends with the runs now queued. No Phase 2 (larger models), no round 3b (more distinct cells), no real phones, no Pi 5.
- ~~**Phase 2 (larger models).**~~ Not this round (time box). Test I, L4 and round 3 partly cover it (12-14B models and the 27B).
- **Paper (IEEE-quality, Markdown for now).** A separate artifact from the talk. **Outline started 2026-10-04: `docs/TALK2-PAPER-OUTLINE.md`** (research questions, methods, figure/table → data plan, threats to validity, open items).
- ~~**Files from other Claude sessions**~~ The user will recreate or handle them (2026-10-04); this session takes no action and never commits them. (Talk 1 slide plan, images and slides, the Talk 2 deck-build prompt; the misconceptions and Talk 3 docs are referenced but not on disk): commit, keep local, move or delete? See `docs/TODO-OTHER-SESSION-FILES.md` (2026-10-04).
- ~~**Round 3 (harder LLM task on newer hardware).**~~ Decided 2026-10-04: items 1 (undo the narrowing) and 2 (thinking on/off) built and running (above), plus the prompt ablation and budget forcing. The other proposals (root cause, fleet correlation, uplink gate) stay in the paper outline §VII.

### mac2 extra-test menu (all nine selected 2026-10-03)
Estimates are scaled from the 20-minute Phase 1 run.

| # | Test | What it answers | Est. |
|---|---|---|---|
| A | CPU thread sweep `-t 1,2,4,6,8`, all 17 models, energy per thread count | A14 has 2 performance + 4 efficiency cores, M1 4 + 4: same core designs. t=2 ≈ A14's performance cores, t=6 ≈ the whole A14 CPU. A hardware-real "iPhone 12 CPU" point | 1.5 h |
| B | STREAM on macOS (bandwidth by threads) | Measured M1 bandwidth, directly comparable with the Linux proxies' STREAM | 10 min |
| C | Talk 2's real workload: Edge Triage Pipeline eval (accuracy + per-call latency + `powermetrics` energy) on the five candidates | Puts M1 in the existing per-call table next to the Pi 4 meter and M4 Max rows | 1 h setup + 2-4 h |
| D | Context-depth sweep (`-d 0,512,2048,4096`) | How speed and energy fall off at the triage prompt's real context lengths | 1-2 h |
| E | Repeat Phase 1 three times over the day | Run-to-run variance, i.e. error bars for the talk | 1 h total |
| F | Sustained load: 60 min continuous generation on 2-3 models | Whether M1 holds speed and power over time; the baseline for later phone throttling runs. Mac mini has a fan, so these aren't phone thermals | 1-2 h |
| G | Quantization variants (Q4_0, Q8_0, IQ4) on 3-4 models | What phone apps actually ship (Q4_0 has fast ARM paths) vs our Q4_K_M | 1 h + downloads |
| H | MLX vs llama.cpp Metal, same models at 4-bit | Which Apple runtime is greenest. MLX Swift is what many iOS apps use | 2 h |
| I | Phase 2 preview on M1: Gemma-3-12B, Qwen3-14B (fit in 16 GB) | M1 as the "2020 laptop" point on the spectrum | 1 h |

All nine total roughly 11-15 h and fit in the window.

### Android-proxy extra-test menu (all seven queued 2026-10-03)

Measured instruction sets:
- **c9g (Neoverse V3):** SVE2, i8mm, bf16. Close to 2025-26 flagship cores.
- **c7g (Neoverse V1):** 256-bit SVE, i8mm, bf16. A Cortex-X1 phone has neither SVE nor i8mm.
- **c6g (Neoverse N1):** dotprod and fp16 only. Matches the Pi 5's Cortex-A76.

Both Android proxies have 16 GiB of RAM, like a 2026 flagship's 12-16 GB. They auto-stop ≈ 2026-10-04 18:20 UTC.

| # | Test | Proxy | What it answers | Est. |
|---|---|---|---|---|
| L1 | RAM capacity test (`TODO-RAM-CAPACITY-TEST.md`) | c9g | Which models fit 4 / 6 / 8 / 12 GB phones, under a real enforced cap | 1 h |
| L2 | **Phone-ISA build:** llama.cpp rebuilt for a Cortex-X1's instruction set (armv8.2-a + dotprod + fp16: no SVE, no i8mm), Phase 1 re-run | c7g | How much of the c7g's speed comes from server-only instructions; makes it a more faithful mainstream-phone stand-in without any math | 2 h |
| L3 | ARM-repacked quants: Q4_0, IQ4_NL, Q8_0 on the Edge Triage candidates + Gemma-3-1B | c9g, c7g | On ARM CPUs llama.cpp repacks Q4_0 / IQ4_NL into interleaved layouts, often the fastest CPU format: what an Android CPU app should ship. G covers Apple | 45 min each |
| L4 | Phase 2 preview: Gemma-3-12B, Gemma-4-12B, Qwen3-14B | c9g | Can a 16 GB flagship-class CPU run a 12-14B model, and how fast | 45 min |
| L5 | Context-depth sweep (CPU, `-d 0,512,2048,4096`) on the five Edge Triage candidates + Gemma-3-1B | c9g, c7g | How the Android CPU path slows at the triage prompt's real context lengths | 1.5 h each |
| L6 | Repeat Phase 1 | c9g, c7g | Run-to-run variance; shared VMs have noisy neighbours, unlike the dedicated Mac host | 1.6-2 h each |
| L7 | Talk 2's real workload (like C), latency + accuracy only (no energy counters on Graviton) | c9g | Per-call latency on a flagship-class CPU vs the Pi 4's 31.7 s Phi p50. **Needs the repo copied to the instance: separate approval, as for C** | 2-3 h |

**Queued** (`scripts/bench_linux_extras.sh`, each starts when that proxy's Phase 1 finishes):

| Proxy | Order | Started | Notes |
|---|---|---|---|
| android-flagship (c9g) | L4 → L1 → L3 → L5 → L6 → L7 | 2026-10-03 20:30 UTC | Est. 7.5-9 h |
| android-mainstream (c7g) | L2 → L3 → L5 → L6 | after its Phase 1 (~20:50 UTC) | Est. 7-8 h |

Implementation choices:
- **L1** picks the first `-lm` load mode whose peak RSS covers the model file (so weights are resident, as in a phone app), then runs each model under `systemd-run --scope -p MemoryMax=<cap>`, smallest cap first. Output: `fits.csv`.
- **L2** builds `build-x1` with `GGML_NATIVE=OFF`, `-march=armv8.2-a+dotprod+fp16` and logs each build's compiled-in CPU features.
  - **Verified X1-faithful:** native lists `MATMUL_INT8 = 1 | SVE = 1 | SVE_CNT = 32`; x1 lists only NEON, ARM_FMA, FP16_VA, DOTPROD, LLAMAFILE, OPENMP and REPACK.
  - The run's logged WARNING is a false alarm. llama.cpp omits disabled features, and the check looked for `= 0`. The check is fixed, and a correction is appended to the run's `cpu_features.txt`.
- **L3** downloads, measures and deletes one file at a time (the 8-9B Q8_0s are 9-10 GB) at threads 4 and 8. No IQ4_NL of Phi-3.5-mini is published; bartowski supplies Llama-3.1-8B Q8_0 and Qwen3-8B Q4_0.
- **L4** runs threads 4 and 8. Its models are deleted after L1 uses them.
- **L7** uses `--model-threads 8` and 1 rep: there's no energy to average, and each run's 60 or 30 calls give the latency distribution.
  - **First run (2026-10-04 00:29 UTC): Phi-3.5-mini and Llama-3.1-8B scored 0% format** on the Edge Triage Pipeline. `llama-server` was OOM-killed (kernel log: 15.4 GB anon-rss).
    - Cause: the backend passes no context size, so `llama-server` uses each model's full training context. That's 128k for Phi-3.5 (no grouped-query attention, ~50 GB of KV cache) and Llama-3.1 (~17 GB).
    - Metal shrinks the context to fit GPU memory, which is why mac2 and the M4 Max passed; the CPU path doesn't. Gemma (sliding-window attention), GLM and Qwen3 fit.
    - **A real deployment gotcha:** an out-of-the-box server on a 16 GB CPU device runs out of memory on these models.
  - **Re-run queued:** all six pairs with `LLAMA_ARG_CTX_SIZE=8192` (llama-server's env override; no harness or pipeline change), starting automatically after the first L7. The setting is recorded in its `system.txt`. The repo source was copied to `~/fleet-trilogy` on the c9g, approved with the queue.

Not proposed: sustained load (servers don't throttle, so it says nothing about phones) and MLX (Apple-only). The pi5 proxy gets nothing extra: its instruction set already matches, and its gap is bandwidth and caches, which only a real Pi 5 fixes.

## Deferred (TODO files)

- **Real phones on AWS Device Farm: not this round (time box, 2026-10-04).** S26 Ultra, S21, Galaxy A36 and Galaxy A17; iPhones if signing is possible. See `talks/talk2-greenest-token/TODO-REAL-PHONE-BENCHMARKS.md`. Waiting on the proxy results review.
  - **Open:** an Apple Developer account for iOS.
- ~~**Q4_0 accuracy check.**~~ Answered 2026-10-04 (C-q4_0 on both Mac minis, Q-confirm n=45): it depends on the model. Gemma-3-4B regresses 0% → 30.4%, Llama 6.3% → 14.4%, and the others hold. Still open: Q4_0's ARM-CPU latency on the real workload (the Android proxies are gone). See `talks/talk2-greenest-token/TODO-Q4_0-ACCURACY-CHECK.md`.
- ~~**RAM capacity test.**~~ Done as L1 (c9g, 2026-10-03): 20 models × 4/6/8/12 GB caps in `fits.csv`. A cgroup ceiling, not a phone's per-app budget. See `talks/talk2-greenest-token/TODO-RAM-CAPACITY-TEST.md`.

## Ideas not yet discussed

- **A real Raspberry Pi 5:** not this round (time box, 2026-10-04). (~$80-120.) The c6g "pi5" proxy has ~5× a Pi 5's bandwidth (89 vs 17.1 GB/s). A real board with the inline meter would give measured energy like the Pi 4 rows.
- **Apple Neural Engine via Core ML** (e.g. the ANEMLL project). Possibly the most energy-efficient iPhone path, but model conversion is significant work.

## Rejected or fallback only

- **Math "correction" of proxy speeds by bandwidth ratio.** Fallback only: the user prefers hardware-real measurements. If used, show raw and corrected side by side, labeled.
- **Throttling bandwidth on EC2.** Not possible: Nitro doesn't expose Arm MPAM to guests, there's no cpufreq, and cgroups have no bandwidth controller. A co-running bandwidth hog was considered and set aside in favor of real phones.
- **One LLM call per incident in the pipeline.** "Leave the pipeline alone."

## Teardown and cost reminders

- **pi5 proxy: tear down after Phase 1** (user, 2026-10-03).
  - **Done:** results collected and verified (17 complete JSONs), and the instance shut down 2026-10-03 22:39 UTC. That stops compute billing.
  - **Removed** 2026-10-03 ~22:50 UTC with `terraform apply -var 'enabled_proxies=["android-mainstream","android-flagship","iphone-older"]'`. The plan was `0 to add, 0 to change, 1 to destroy` (`aws_instance.linux["pi5"]` only). The instance and its disk are gone.
  - Later applies must keep pi5 out of `enabled_proxies`, or it is recreated.

- **mac2 host:** ~$0.65/h until released. AWS allows release from **2026-10-04 18:46 UTC** (11:46 PDT). Then run `terraform destroy` with `iphone-older` removed from `enabled_proxies`, or a full destroy.
  - Its round 3 ended 20:13 UTC and was collected 20:15 (28 sessions, 36/36 model hashes).
  - **No teardown is scheduled:** the user cancelled the scheduled one 2026-10-04 ~20:25 UTC ("don't delete … until we have collected all of the logs"). Tear down only on the user's word.
- **mac-m4 host (iphone-flagship):** ≥ $29.52 per 24 h; releasable from 2026-10-05 04:29 UTC.
  - Still running the other session's follow-ups (ablation, think budget 4096), then the budget-forcing re-run, until ~03:30 UTC.
  - **No teardown is scheduled:** the user cancelled the 04:37 UTC one at ~20:30 UTC. Collect everything first; tear down only on the user's word.
- **Linux proxies:** destroyed 2026-10-04 04:26 UTC after collection.
- **AWS SSO:** sessions last about 1 h. Run `aws sso login --profile advocacy-dev` before any `terraform` command. Monitoring and collecting don't need it.
