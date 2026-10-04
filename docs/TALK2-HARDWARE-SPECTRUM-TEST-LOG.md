# Talk 2 hardware-spectrum test log

The lab notebook behind `TALK2-HARDWARE-SPECTRUM-TEST-CATALOG.md`. The catalog says *what* was tested and where it stands. This log records *how* each test was run, in enough detail to evaluate the results later or reproduce them:
- environments and builds;
- exact commands and parameters;
- measurement methods;
- every run ID;
- every incident and whether it touched the data.

Times are UTC unless marked PDT. Started 2026-10-03; update it whenever a test runs or a problem is found.

**The question:** can phones democratize edge intelligence? Same models, same llama.cpp, across the consumer spectrum (Pi → phones → laptops). EC2 stands in for devices we don't have; real phones are deferred to AWS Device Farm (`talks/talk2-greenest-token/TODO-REAL-PHONE-BENCHMARKS.md`).

---

## 1. Platforms

| Key | Hardware | CPU | Cores | RAM | OS / kernel | Where | Stands in for |
|---|---|---|---|---|---|---|---|
| `android-flagship` | EC2 c9g.2xlarge | Graviton5, Neoverse-V3 | 8 vCPU, 1 thread/core | 15 GiB | Ubuntu 26.04.1, 7.0.0-1014-aws | us-west-2a, i-01c317884b61a1a55, **terminated 2026-10-04 04:26** | 2025-26 flagship Android (Snapdragon 8 Elite Gen 5 / Dimensity 9500): an upper bound |
| `android-mainstream` | EC2 c7g.2xlarge | Graviton3, Neoverse-V1 | 8 vCPU | 15 GiB | same | us-west-2a, i-06c21408e356914eb, **terminated 2026-10-04 04:26** | mainstream / older Android (Cortex-X1 class) |
| `pi5` | EC2 c6g.2xlarge | Graviton2, Neoverse-N1 | 8 vCPU (sweeps use 1/2/4) | 15 GiB | same | us-west-2a, i-01ee531f56d4e1372, **terminated 2026-10-03 ~22:50** | Raspberry Pi 5 (Cortex-A76 = N1's sibling) |
| `iphone-older` (mac2) | EC2 mac2.metal = Mac mini Macmini9,1 | Apple M1 | 4 performance + 4 efficiency | 16 GB | macOS 26.7 (AMI `ami-0b2ea1252252f73c3`, `amzn-ec2-macos-26.7*`), Darwin 25.6.0 | us-west-2c; host `h-0cd7883f65df1cc96`, allocated 2026-10-03 18:46:02, release ≥ 2026-10-04 18:46:02; instance i-0672a644dd3476d85 | iPhone 12 (A14) by lineage. Its generation speed actually tracks the iPhone 17 Pro (§9) |
| `iphone-flagship` (mac-m4) | EC2 mac-m4.metal = M4 Mac mini | Apple M4 | (recorded in its `system.txt`) | 24 GB | macOS 26.7 (same AMI as mac2) | us-west-2b (2a had no capacity); host `h-0ef56a222e2ebe7fb`, allocated 2026-10-04 04:29:17, release ≥ 2026-10-05 04:29:17; instance i-0ee6011fbe606903f | iPhone 17 Pro / 18 Pro (A19 Pro / A20 Pro); M4 is the A18 generation. Added for round 2 |
| `m4max-macbook` | the user's MacBook Pro | Apple M4 Max | 12 performance + 4 efficiency | 64 GB | macOS 26.7.1 (25G241), Darwin 25.6.0 | local | laptop-class GPU reference |
| Pi 4 (real) | Raspberry Pi 4 | Cortex-A72 | 4 | 8 GB | Pi OS (earlier Talk 2 work) | the user's bench, inline KWS-2303C meter | the 2021 baseline (impact-track rows 22-26) |

**Caches** (lscpu):
- c9g: 64 KiB L1d and 2 MiB L2 per core, 48 MiB L3.
- c7g and c6g: 64 KiB L1d and 1 MiB L2 per core, 32 MiB L3.

**CPU features** (`/proc/cpuinfo`):
- c9g: `fphp asimdhp asimddp sve sve2 svei8mm svebf16 i8mm bf16`, with SVE vector length 128-bit.
- c7g: `fphp asimdhp asimddp sve svei8mm svebf16 i8mm bf16`. 256-bit SVE: llama.cpp reports `SVE_CNT = 32`.
- c6g: `fphp asimdhp asimddp` only.
- A Cortex-X1 has neither SVE nor i8mm. A Cortex-A76 matches N1.

**Memory bandwidth, measured** (STREAM Triad, GB/s):

| Platform | Threads → GB/s | Target device |
|---|---|---|
| c9g | 1: 43, 2: 66, 4: 113, 6: 121, 8: 119 | ~85 GB/s theoretical, flagship phone |
| c7g | 1: 49, 2: 91, 4: 142, 6: 165, 8: 202 | 51.2 GB/s |
| c6g | 1: 25, 2: 49, 4: 89 | Pi 5: 17.1 GB/s |
| M1 | 1: 58, 8: 48 (quick check; test B has the full sweep) | 68 GB/s theoretical |

**Costs (on-demand, us-west-2):**
- c6g $0.272/h, c7g $0.290/h, c9g $0.348/h.
- mac2 ~$0.65/h, with a 24-hour minimum from allocation.
- The Linux instances auto-stop 24 h after boot (stop, not terminate; the disks keep billing until `terraform destroy`).

**Infrastructure:** Terraform in `deploy/aws-phone-proxies/` (README there).
- AWS profile `advocacy-dev` (SSO, ~1 h sessions).
- VPC 10.42.0.0/16 with public subnets 10.42.1.0/24 (2a) and 10.42.12.0/24 (2c). SSH is open only to the operator's /32.
- A dedicated SSH key, `.ssh/`, is generated per stack.

> **Before publishing:** mac2's `system.txt` files (from `system_profiler`) contain the AWS host's serial number, hardware UUID and provisioning UDID. These aren't credentials; redact them if the data goes public.

## 2. Software and builds

**llama.cpp v0.5.0**, commit `7fe450e19305b828c199d602c23a8337aaa1f03b` (2026-09-23; `c13fcbf6` is the annotated tag object). Every proxy and the M4 Max reruns use it. Each run's `system.txt` records the commit.

| Build | Where | Configure / build |
|---|---|---|
| Linux native | all Graviton (`templates/linux_user_data.sh.tftpl`) | `cmake -B build -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=ON`; `cmake --build build --config Release -j$(nproc)` (GCC, Ubuntu 26.04). Native = every CPU feature above, plus llama.cpp's runtime weight repacking |
| Linux Cortex-X1 ISA (L2) | c7g, `llama.cpp/build-x1` | `-DGGML_NATIVE=OFF -DGGML_CPU_ARM_ARCH=armv8.2-a+dotprod+fp16 -DCMAKE_C_FLAGS=-march=armv8.2-a+dotprod+fp16` (same for CXX). Targets `llama-bench llama-completion` |
| macOS Metal | mac2 (`templates/macos_user_data.sh.tftpl`) | `cmake -B build -DCMAKE_BUILD_TYPE=Release` (Metal by default), Homebrew cmake, Apple clang from the AMI's Command Line Tools |
| macOS CPU-only | mac2, `llama.cpp/build-cpu` | `-DGGML_METAL=OFF` |
| M4 Max v0.5.0 | `~/tools/llama.cpp-v0.5.0` (built 2026-10-03 ~23:00) | `cmake -B build -DCMAKE_BUILD_TYPE=Release`; targets `llama-completion llama-server llama-bench`; AppleClang 21.0.0.21000334 |
| M4 Max prior | `~/tools/llama.cpp`, b10931 = `3057bb66c` (2026-09-12) | used by every M4 Max artifact before 2026-10-03 23:00 |

Compiled-in CPU features, from `llama-completion`'s system_info. llama.cpp lists only the enabled ones:
- **c7g native:** `NEON ARM_FMA FP16_VA MATMUL_INT8 SVE DOTPROD SVE_CNT=32 OPENMP REPACK`.
- **c7g x1:** `NEON ARM_FMA FP16_VA DOTPROD LLAMAFILE OPENMP REPACK`.

**STREAM:** `jeffhammond/STREAM` `stream.c` (master at provisioning time), Triad best rate.
- Linux: `gcc -O3 -march=native -fopenmp -DSTREAM_ARRAY_SIZE=200000000 -DNTIMES=20`, run with `OMP_NUM_THREADS=t OMP_PROC_BIND=close`.
- macOS (test B): Apple clang `-O3 -mcpu=native -Xpreprocessor -fopenmp` with Homebrew libomp, `-DSTREAM_ARRAY_SIZE=80000000`. 200M fails to link: Mach-O can't hold 4.8 GB of static arrays. 80M is 1.9 GB of arrays, ~240× M1's caches. No `OMP_PROC_BIND`.

**Python eval harness (tests C, L7, the M4 Max reruns):**
- The repo's `tests/model/` comparison evals, run as `uv run --no-sync pytest tests/model/test_compare_{edge_triage,tier2}_models.py -m model -s -q --only-model-ids <id> --model-eval-runs <n> [--model-threads N]`.
- Models resolve through `models.toml`'s `LLM_BINARY_PATH_*` / `LLM_MODEL_PATH_*` variables.
- The backend (`shared/llm-inference/src/llm_inference/client.py`) starts `llama-server -m <model> --host --port -t <threads>` with **no context size** (see L7).
- **Copies on remote hosts** (the user approved test C and the L-queue; the safety check had flagged the first copy):
  - mac2: `~/fleet-trilogy`, 2026-10-03 ~20:10, `uv sync` via Homebrew uv.
  - c9g: `~/fleet-trilogy`, ~20:26, uv from astral.sh's installer, `uv sync --python 3.12`.
  - Both copies are source only: no `.git`, `docs/`, `eval-results/`, `deploy/`, images or slides. A local scan found no credential-like files (134 files: source plus `.gitignore`, `.DS_Store`, ruff cache).

**MLX (test H):** mlx-lm 0.32.0 in `~/phoneproxy/mlx-venv` (uv, Python 3.12) on mac2. `scripts/mlx_bench.py` follows `mlx_lm.benchmark`'s method; §4 has the details.

**Scripts** (all in `deploy/aws-phone-proxies/scripts/`):

| Script | What it does |
|---|---|
| `bench.sh` | Phase 1 suite on one host |
| `bench_extras.sh` | mac2 extras queue: E A B D E F I E |
| `bench_extras_gh.sh` | mac2 G and H, after the extras queue |
| `bench_workload.sh` | test C on mac2 |
| `bench_workload_m4max.sh` | the M4 Max reruns |
| `bench_linux_extras.sh` | L1-L7 |
| `mlx_bench.py` | H's MLX benchmark |
| `summarize.py` | per-run Markdown tables; energy alignment |
| `prelim_report.py` | `eval-results/phone-proxies/PRELIMINARY-20261003.md` |
| `proxyctl.sh` | list, ssh, status, wait, start, start-extras, progress, extras-progress, bench, collect, start-all |

## 3. Models

**Phase 1** (identical on every platform; `variables.tf` → each host's `models.txt`; the same repos as the original M4 / Pi tests; all files checked HTTP 200 on 2026-10-03):

| # | Repo / file | Params (B) | File (GB) |
|---|---|---|---|
| 1 | unsloth/granite-4.0-h-350m-GGUF / granite-4.0-h-350m-Q8_0 | 0.34 | 0.36 |
| 2 | NANI-Nithin/LFM2.5-350M-RLCD-GGUF / LFM2.5-350M-RLCD-Q8_0 | 0.35 | 0.38 |
| 3 | Qwen/Qwen2.5-0.5B-Instruct-GGUF / qwen2.5-0.5b-instruct-q4_k_m | 0.63 | 0.49 |
| 4 | drmcbride/Qwen3-0.6B-Q8_0-GGUF / qwen3-0.6b-q8_0 | 0.75 | 0.80 |
| 5 | ggml-org/gemma-3-1b-it-GGUF / gemma-3-1b-it-Q4_K_M | 1.00 | 0.80 |
| 6 | unsloth/Llama-3.2-1B-Instruct-GGUF / Llama-3.2-1B-Instruct-Q4_K_M | 1.24 | 0.80 |
| 7 | Qwen/Qwen2.5-1.5B-Instruct-GGUF / qwen2.5-1.5b-instruct-q4_k_m | 1.78 | 1.11 |
| 8 | unsloth/Qwen3.5-2B-GGUF / Qwen3.5-2B-Q4_K_M | 1.88 | 1.27 |
| 9 | unsloth/Llama-3.2-3B-Instruct-GGUF / Llama-3.2-3B-Instruct-Q4_K_M | 3.21 | 2.01 |
| 10 | Qwen/Qwen2.5-3B-Instruct-GGUF / qwen2.5-3b-instruct-q4_k_m | 3.40 | 2.10 |
| 11 | bartowski/Phi-3.5-mini-instruct-GGUF / Phi-3.5-mini-instruct-Q4_K_M | 3.82 | 2.39 |
| 12 | unsloth/gemma-3-4b-it-GGUF / gemma-3-4b-it-Q4_K_M | 3.88 | 2.48 |
| 13 | unsloth/gemma-4-E2B-it-GGUF / gemma-4-E2B-it-Q4_K_M | 4.65 | 3.09 |
| 14 | bloomer010/Ling-3.0-tiny-GGUF / Ling-3.0-tiny-Q4_K_M (mixture-of-experts) | 7.89 | 4.82 |
| 15 | unsloth/Llama-3.1-8B-Instruct-GGUF / Llama-3.1-8B-Instruct-Q4_K_M | 8.03 | 4.91 |
| 16 | Aldaris/Qwen3-8B-Q4_K_M-GGUF / qwen3-8b-q4_k_m | 8.19 | 5.02 |
| 17 | unsloth/GLM-4-9B-0414-GGUF / GLM-4-9B-0414-Q4_K_M | 9.40 | 6.16 |

**Excluded from Phase 1:**
- Qwen3.8-27B (16.5 GB): no phone or 16 GiB proxy can hold it.
- **The `models.toml` `enabled=false` flags are stale** (Llama-3.1-8B and GLM-4-9B later passed the Pi escalation gate), and some of these models fail the task quality gates. Speed and energy don't depend on quality.

**Phase 2 preview (I, L4, L1):**

| Repo | File | Size |
|---|---|---|
| unsloth/gemma-3-12b-it-GGUF | gemma-3-12b-it-Q4_K_M | 7.30 GB |
| unsloth/gemma-4-12b-it-GGUF | gemma-4-12b-it-Q4_K_M | 7.12 GB |
| unsloth/Qwen3-14B-GGUF | Qwen3-14B-Q4_K_M | 9.00 GB |

**Quantization variants:**

| Test | Quants | Files |
|---|---|---|
| G (mac2) | Q4_0, IQ4_XS, Q8_0 | gemma-3-1b-it (unsloth), Llama-3.2-3B-Instruct (unsloth), Phi-3.5-mini-instruct (bartowski), gemma-3-4b-it (unsloth) |
| L3 (c9g, c7g) | Q4_0, IQ4_NL, Q8_0 | Gemma-3-1B, Gemma-3-4B (unsloth); Phi-3.5-mini (bartowski, Q4_0 and Q8_0 only); Llama-3.1-8B (unsloth Q4_0 / IQ4_NL, bartowski `Meta-Llama-3.1-8B-Instruct-Q8_0`); GLM-4-9B-0414 (unsloth); Qwen3-8B (bartowski `Qwen_Qwen3-8B-Q4_0`, unsloth IQ4_NL / Q8_0) |

- Phi-3.5-mini has no published IQ4_NL.
- ggml-org ships only Q4_K_M and Q8_0 of Gemma-3-1B, so the variants come from unsloth.

**MLX 4-bit (H):** these mlx-community repos:
- gemma-3-1b-it-4bit
- Llama-3.2-1B-Instruct-4bit
- Qwen2.5-1.5B-Instruct-4bit
- Qwen3.5-2B-4bit
- Llama-3.2-3B-Instruct-4bit
- Phi-3.5-mini-instruct-4bit
- gemma-3-4b-it-4bit
- Llama-3.1-8B-Instruct-4bit
- Qwen3-8B-4bit

`gemma-4-E2B-it-4bit` redirects (HTTP 307), so it isn't included. MLX 4-bit is about 4.5 bits per weight, between GGUF Q4_0 and Q4_K_M.

## 4. Measurement methods

**llama-bench**, every run: `-p 512 -n 128 -r 3 -o json`.
- Defaults: a small warm-up run before timing, `-b 2048 -ub 512`, f16 KV cache, flash attention auto.
- tok/s = `avg_ts` across the 3 repetitions. `samples_ns` keeps each repetition.
- **Linux:** one process per model with `-t 1,2,4,6,8` (pi5: `1,2,4`), so 10 entries per model (6 for pi5).
- **macOS, per model:** Metal pp (`-ngl 99 -p 512 -n 0`) and Metal tg (`-ngl 99 -p 0 -n 128`) as separate processes, then a 10 s idle gap, then CPU (`build-cpu`, `-ngl 0 -t 4`, pp and tg in one process).
- **Metal warm-up:** one untimed `llama-bench -p 16 -n 4 -r 1` before the first window. The first Metal launch spends ~25 s compiling shaders at CPU power (found in the mac2 smoke test).

**Energy, macOS only** (Graviton has no energy counters, no RAPL in EC2):
- **Capture:** `powermetrics --samplers cpu_power,gpu_power -i 500`, reading the `Combined Power (CPU + GPU + ANE)` line in mW.
  - On mac2 the scripts start it with sudo and stop it with `sudo pkill -INT -P <sudo pid> -x powermetrics`.
  - On the M4 Max the user starts it (`-o /tmp/m4max-powermetrics.txt`).
  - Coverage is chip only: no DRAM, SSD, display or power-supply losses. The Pi 4 meter measures the whole board at the wall. Same caveat as impact-track row 24.
- **Alignment** (`summarize.py: load_powermetrics`):
  - Sample header times have 1 s resolution and mark the end of each sample.
  - Sub-second times are rebuilt from the cumulative `elapsed` field, with an offset fitted so every rebuilt end time falls inside its header's second.
- **Idle baseline:** the mean power of samples wholly inside that run's idle windows.
  - llama-bench runs: 30 s before and after, plus 10 s gaps.
  - Workload runs: 30 s before and after plus 20 s gaps on mac2; 60 s and 20 s on the M4 Max.
- **Energy above idle** = Σ (P − P_idle) × overlap(sample, interval).
- **llama-bench windows:** each test's interval is rebuilt backwards from the window's end using `samples_ns`, so model load and warm-up are excluded. mJ/token = energy ÷ (reps × tokens).
- **Eval-harness windows (C, M4 Max):** the whole pytest session is the interval, startup and model load included, as in the 2026-10-02 M4 Max contrast. J/call = window energy ÷ the artifact's `latency.n`. These are upper bounds.
- **MLX (H):** `mlx_bench.py` records each trial's epoch start and end, so energy covers exactly those intervals.

**RAM capacity (L1):**
- The load mode is the first of `-lm none | dio | mlock` whose peak RSS covers ≥ 90% of a probe model's file size (`/usr/bin/time -v`). `none` passed.
- Each model: one uncapped run for peak RSS, then `sudo systemd-run --scope -p MemoryMax=<cap> -p MemorySwapMax=0 llama-bench -m <m> -lm none -p 512 -n 16 -r 1 -t 8` at caps 4G, 6G, 8G and 12G, smallest first.
- A pass at a smaller cap implies passes at larger caps (marked `fit` without running). A failure is exit 137, OOM-killed.
- Caps are GiB and hard ceilings. A real app's budget is only part of a phone's RAM.
- The KV cache is tiny at `-p 512 -n 16`; longer contexts need more.

**Eval-harness metrics** (from the artifacts' `models.<id>`):
- **Edge Triage Pipeline:** `format_reliability.rate` and `escalation_calibration.mismatch_rate` (gate 2, `gate2_per_scenario_n`).
  - `--model-eval-runs 15` is 15 format trials plus 45 escalation calls, 60 calls in all.
  - A model below 80% format never reaches gate 2.
- **Tier 2:** `format_reliability.structured_rate` / `nonempty_rate`, `speakability.violation_rate`, `grounding.max_violation_rate`; n=30.
- **Latency:** `latency.p50_seconds` and `p95_seconds` per call over all `n` calls.
- `resident_ram_mb_after` is a session-cumulative `ru_maxrss`, a floor for later models in a session.

## 5. Test register

### Phase 1 (identical models on every platform)

| Platform | Run dir (`eval-results/phone-proxies/…`) | Window | Status |
|---|---|---|---|
| c9g smoke (`--quick`: smallest model, 1 rep, first c9g instance) | `android-flagship/20261003T180853Z` | 2026-10-03 18:08 | done |
| c9g | `android-flagship/20261003T184418Z` | 18:44 → ~20:25 | done, 17/17 |
| c7g | `android-mainstream/20261003T184425Z` | 18:44 → ~21:05 | done, 17/17; **see incident 9** |
| c6g / pi5 | `pi5/20261003T184429Z` | 18:44 → 21:33 | done, 17/17 checked |
| mac2 smoke (`--quick`) | `iphone-older/20261003T190533Z` | 19:05 | done after fixes (incidents 3-4) |
| mac2 | `iphone-older/20261003T191829Z` | 19:18 → 19:38 (20 min) | done, 17/17, 70 windows, all exit 0 |

Per-run files:
- `system.txt`, `bench.log` (with `== <model>` lines), `llama-bench_*.json`.
- Linux: `stream_t<N>.txt`.
- macOS: `windows.log` and `powermetrics.txt`.

### mac2 extras queue (`bench_extras.sh`, queue `extras-20261003T200126Z`)

| Test | Run dir (`iphone-older/…`) | Window | Parameters | Status |
|---|---|---|---|---|
| prep | — | 20:01-20:08 | libomp, STREAM build, Phase 2 downloads (23.4 GB at ~75 MB/s), Metal warm-up | done |
| E #1 | `20261003T200756Z` | 20:08-20:28 | `bench.sh` unchanged (Phase 1 repeat) | done |
| (pause for C) | — | 20:28-22:01 | `PAUSE` file; the queue holds between tests | — |
| A | `A-cpu-threads-20261003T220204Z` | 22:02 → ~23:10 | `build-cpu`, `-t 1 2 4 6 8`, one window per model and thread count (`cpu-t<N>_<model>`), 17 models | done |
| B | `B-stream-20261003T231036Z` | 23:10 | STREAM t=1,2,4,6,8, one window each | done |
| D | `D-context-depth-20261003T231154Z` | 23:12 → ~23:51 | Metal, `-d 0,512,2048,4096`, pp512 and tg128 as separate windows per depth, 17 models. llama-bench re-fills the d-token context (untimed) before each rep: **speed exact, energy not separable** | done |
| E #2 | `20261003T235136Z` | 23:51-00:11 | as E #1 | done |
| F | `F-sustained-20261004T001135Z` | 00:11 → 01:41 | powermetrics with `thermal` added. Metal `-p 0 -n 512 -r R` for gemma-3-1b (R=140), Llama-3.2-3B (65) and Llama-3.1-8B (30), then CPU `-t 4` Llama-3.2-3B (65). ~20 min each, 120 s cooldown between. `samples_ns` gives every rep's speed for drift | done |
| I | `I-phase2-preview-20261004T014140Z` | 01:41 → 01:55 | 12-14B models, Phase 1's four windows per model | done |
| E #3 | `20261004T015555Z` | 01:56 → 02:15 | as E #1 (`bench.sh` no longer records host identifiers) | done; queue finished 02:15:53 |
| G | `G-quant-variants-20261004T022838Z` (queue `queue-gh-20261003T201636Z`) | 02:28 → 02:42, after prep (downloads, MLX install) from 02:16 | 12 files (§3), Phase 1's four windows each | done |
| H | `H-mlx-20261004T024249Z` | 02:43 → 02:49 | 9 MLX 4-bit models, `mlx_bench.py`, 3 reps after a warm-up of 1 pp + an 8-token tg, per-trial epoch times | done; queue finished 02:49:31 |

### Test C: Talk 2's real workload on M1 (`bench_workload.sh`)

**Run dirs:**
- quick: `iphone-older/C-workload-20261003T202805Z-quick`, Phi, 1 eval run, 20:28.
- full: `iphone-older/C-workload-20261003T203147Z`, 20:31 → ~22:01, 18 windows, all exit 0.
- Eval artifacts: `iphone-older/C-artifacts/`. Each window's file is in that run's `artifacts.txt`.

**Settings:**
- **Pairs and reps:** the row 24 pairs (Phi on the Edge Triage Pipeline, n=15; Gemma-3-4B on Tier 2, n=30), plus Gemma-3-4B, Llama-3.1-8B, GLM-4-9B and Qwen3-8B on the Edge Triage Pipeline (n=15). 3 reps each.
- **Run flags:** Metal `llama-completion` (the harness finds `llama-server` beside it), `--model-threads 4`, default 180 s timeout.
- **Power:** 30 s idle before and after, 20 s gaps.

### M4 Max reruns (`bench_workload_m4max.sh`, the user's MacBook)

**Why rerun:**
- Only Phi (Edge Triage) and Gemma-3-4B (Tier 2) had single-model M4 Max runs (2026-10-02, b10931).
- The other four came from the published five-model session (2026-09-26T215201Z). In that session Phi measured 0.75 s, against 0.36 s in its own runs.

**Settings:**
- Same pairs, reps and flags as C, on the v0.5.0 build.
- **No `--model-threads`:** the default of 12, as on 2026-10-02.
- **Power:** AC power required. The user ran `powermetrics -i 500` to `/tmp/m4max-powermetrics.txt`. 60 s idle before and after, 20 s gaps.

**Runs:**
- `m4max-macbook/20261003T230334Z`: 23:03-23:29.
  - 17 valid sessions: Phi, Gemma Tier 2, Gemma Edge Triage, Llama and GLM ×3 each; Qwen3-8B ×2.
  - **The MacBook idle-slept at 23:30:48** (incident 13). Evidence: `SLEEP-EVIDENCE.txt`.
- `m4max-macbook/20261004T003435Z-resume`: from 00:34, under `caffeinate -dims`.
  - Qwen3-8B r3, a GLM check rep (r4) and the **five-model session**: all five ids in one pytest session, n=15.
  - The five-model session tells two explanations for the 09-26 gap apart: running in one session vs harness and build changes since then.

**Results** (resume finished 00:42, all sessions exit 0):

| Session (Edge Triage unless noted) | Single-model p50 by rep | Five-model session p50 (00:34 resume) | 09-26 five-model p50 |
|---|---|---|---|
| Phi-3.5-mini | 0.36 / 0.37 / 0.37 | **0.70** | 0.75 |
| Gemma-3-4B | 1.24 / 1.70 / 1.55 | 1.82 | 2.05 |
| Llama-3.1-8B | 1.20 / 1.03 / 1.06 | 1.02 | 1.25 |
| GLM-4-9B | 1.17 / 1.36 / 1.33 (r4, held awake: **1.02**) | 1.57 | 1.50 |
| Qwen3-8B | 1.99 / 2.04 (r3, held awake: **1.50**) | 1.94 | 2.24 |
| Gemma-3-4B, Tier 2 | 0.53 / 0.50 / 0.50 | — | (0.50-0.51 on 10-02) |

**Findings:**
- **Build:** v0.5.0 vs b10931 makes no material difference (Phi 0.36-0.37 vs 0.35-0.36; Gemma Tier 2 0.50-0.53 vs 0.50-0.51).
- **The five-model session is the cause of the 09-26 inflation.** On the same build and day it reproduces Phi at 0.70 s (2× its single-model latency) and slows Gemma, GLM and Qwen. Llama is unaffected.
  - **Use single-model sessions only.** The 09-26 multi-model latencies are not valid per-model numbers.
  - The mechanism is unverified. One candidate is earlier models' `llama-server` processes (and their GPU-resident memory) still alive while later models run.
- **The first run's state drifted.** From `/tmp/m4max-powermetrics.txt`, mean over each session:

  | Sessions | Avg power | GPU clock when busy | GPU busy |
  |---|---|---|---|
  | Phi and Tier 2 (16:03-16:09 PDT) | 28-41 W | ~1,370-1,450 MHz | 69-85% |
  | Gemma Edge Triage r1 | 24.9 W | 1,417 MHz | 70% |
  | **from Gemma Edge Triage r2 (16:10:44 PDT) on** | 13-16 W | 1,144-1,400 MHz, falling | 58-76% |
  | resume (cool, held awake) | 25-28 W | ~1,335 MHz | 79-91% |

  - Less GPU activity at lower power points to the host-side work (harness, `llama-server`'s CPU threads) being slowed.
  - Candidates: (a) macOS lowering the priority or core class of background processes once the user went idle or the display slept. Audio-session holds against display sleep were released at 16:11:30 PDT. (b) Thermal management over a 26-minute sustained load: GPU clocks slid steadily.
  - The trace has no thermal sampler, so it can't tell them apart. See open question 4.

**Caffeinated rerun** (`m4max-macbook/20261004T005747Z-caffeinated`, 00:58-01:28):
- All 18 single-model sessions under `caffeinate -dims`; 38/38 windows exit 0.
- Power trace with thermal pressure: `powermetrics --samplers cpu_power,gpu_power,thermal -i 500` (`/tmp/m4max-powermetrics-2.txt`, snapshot in the run dir). Idle 280 mW.

| Session | p50 / p95 s (r1, r2, r3) | J/call above idle | Avg W | GPU MHz busy | Thermal pressure |
|---|---|---|---|---|---|
| Phi-3.5-mini, Edge Triage | 0.36/0.43, 0.37/0.44, 0.37/0.46 | 15.1, 15.3, 15.8 | 31 | ~1,385 | Nominal |
| Gemma-3-4B, Tier 2 | 0.50/0.63, 0.51/0.62, 0.53/0.69 | 23.5, 24.3, 23.6 | 37-39 | 1,415-1,505 | Nominal |
| Gemma-3-4B, Edge Triage | 2.01/2.36, 1.79/2.12, 1.71/2.00 | 22.0, 24.3, 24.3 | 11-15 | 1,350-1,414 | Nominal |
| Llama-3.1-8B, Edge Triage | 1.14/2.06, 1.07/2.09, 1.12/2.07 | 18.7, 19.1, 19.7 | 13.5-14.5 | 1,215-1,265 | Moderate → Heavy |
| GLM-4-9B, Edge Triage | 1.41/2.42, 1.41/2.61, 1.52/2.49 | 22.0, 22.4, 22.2 | 13-14.5 | 1,110-1,159 | Heavy |
| Qwen3-8B, Edge Triage | 1.96/2.60, 2.07/2.47, 1.99/2.47 | 27.8, 27.6, 28.0 | 13-14 | 1,208-1,230 | Moderate → Heavy |

**Open question 4 resolved: heat, not idle state.**
- Held awake, the MacBook reached Moderate then Heavy thermal pressure within ~12 minutes of sustained load (from Llama, the fourth pair). GPU clocks fell ~15-20%, and the later models' latencies match the first run's slowed sessions (GLM 1.41-1.52 s, Qwen 1.96-2.07 s).
- The resume's faster reps (GLM r4 1.02 s, Qwen r3 1.50 s) ran on a machine that had cooled during an hour of sleep.
- The pair order is fixed, so **later models are measured warmer**. A fair per-model M4 Max comparison needs a cooldown to Nominal before each model.

~~**Energy per call is stable under throttling.**~~ **Superseded by the gated run below:** this was inferred from Phi and Tier 2 alone, which always ran cool. Phi's 15.1-15.8 J does reproduce the 2026-10-02 contrast (15.3 J, b10931), and Gemma Tier 2's 23.5-24.3 J the 22.7 J.

**Gemma-3-4B Edge Triage varies** (1.24-2.01 s p50 across 6 reps at Nominal pressure, 11-25 W). That's unexplained; candidates are output-length variance or host-side work. Its per-call energy is steadier (22-24 J).

**Gated reverse-order rerun** (`m4max-macbook/20261004T043341Z-gated-reverse`, 04:33-05:11; 56 windows, all exit 0):
- Same 18 sessions, last pair first.
- Each session started only after 60 s of Nominal thermal pressure. The `cool-wait_*` windows waited 0-134 s.
- Trace `/tmp/m4max-powermetrics-3.txt` (snapshot in the run dir). Idle 241 mW.
- **"Cool" means starting at Nominal.** Pressure still often rose to Moderate or Heavy within a 90-130 s session.

| Session (Edge Triage unless noted) | Cool p50 s (r1, r2, r3) | Warm p50 s (caffeinated forward run) | Cool J/call | Warm J/call |
|---|---|---|---|---|
| Qwen3-8B (ran first) | 1.37, 1.44, 1.37 | 1.96, 2.07, 1.99 | 40.1, 41.2, 39.8 | 27.8, 27.6, 28.0 |
| GLM-4-9B | 1.13, 1.00, 1.12 | 1.41, 1.41, 1.52 | 29.8, 30.6, 32.4 | 22.0, 22.4, 22.2 |
| Llama-3.1-8B | 0.78, 0.87, 0.79 | 1.14, 1.07, 1.12 | 25.4, 25.6, 25.4 | 18.6, 19.1, 19.7 |
| Gemma-3-4B | 1.14, 1.08, 1.16 | 2.01, 1.79, 1.71 | 36.2, 36.0, 35.4 | 22.0, 24.3, 24.3 |
| Gemma-3-4B, Tier 2 | 0.51, 0.52, 0.53 | 0.50, 0.51, 0.53 | 23.3, 22.9, 23.0 | 23.5, 24.3, 23.6 |
| Phi-3.5-mini (ran last) | 0.37, 0.38, **0.72** | 0.36, 0.37, 0.37 | 14.6, 15.7, **10.2** | 15.1, 15.3, 15.8 |

**Finding: on the M4 Max, thermal state trades speed for energy.**
- Starting cool, the 8-9B models and Gemma's Edge Triage task run 24-77% faster per call, but use 30-60% more energy per call.
- Throttled (lower clocks, lower voltage) the same work is slower and cheaper: the usual DVFS tradeoff.
- For the talk and paper: **report both regimes, labelled** (cool burst vs sustained), never one number per model. The pairs that always ran cool (Phi, Tier 2) agree across every run and with 2026-10-02.
- **Phi r3 is an outlier:** Heavy pressure mid-session, latency doubled, lower J/call. It's consistent with the same tradeoff. Kept, not dropped.

### Android-proxy extras (`bench_linux_extras.sh`)

**c9g, queue `extras-20261003T202613Z`** (L4 L1 L3 L5 L6 L7), started 20:30, finished ~00:40; collected 01:17 with model hashes (17/17 match `MODELS.lock.tsv`):

| Test | Run dir (`android-flagship/…`) | Parameters | Status |
|---|---|---|---|
| L4 | `L4-phase2-preview-20261003T203013Z` | 3 Phase 2 models, `-t 4,8` | done |
| L1 | `L1-ram-capacity-20261003T205135Z` | §4, all 17 Phase 1 + 3 Phase 2 models. Output `fits.csv`, `load_mode.txt` (= `none`), `uncapped_*.time`, `cap*_*.json/.err` | done |
| L3 | `L3-arm-quants-20261003T211135Z` | 17 files, `-t 4,8`; download → measure → delete, one at a time | done |
| L5 | `L5-context-depth-20261003T220426Z` | the five Edge Triage candidates + Gemma-3-1B, `-t 8 -d 0,512,2048,4096` | done |
| L6 | `20261003T225204Z` | `bench.sh` with `1,2,4,6,8` (Phase 1 repeat) | done |
| L7 | `L7-workload-20261004T002907Z` | the C pairs on the native CPU `llama-completion`, `--model-threads 8`, 1 rep. **Phi and Llama 0% format: `llama-server` OOM-killed** (incident 14; `OOM-KERNEL-LOG.txt`, 18 kills). Gemma (both tasks), GLM and Qwen3 ran | done; Phi and Llama invalid |
| L7 at 8k | `L7-workload-20261004T004239Z` (queue `extras-20261004T004239Z`) | the same six pairs with `LLAMA_ARG_CTX_SIZE=8192`, recorded in `system.txt` | done 00:42 → ~01:15. All six pairs ran (Phi 1.08 s p50, 100% format). The eval artifacts for both L7 runs are in `L7-artifacts/` |

**c7g, queue `extras-20261003T202853Z`** (L2 L3 L5 L6). It waited for Phase 1, then started 21:08:

| Test | Run dir (`android-mainstream/…`) | Parameters | Status |
|---|---|---|---|
| L2 | `L2-phone-isa-x1-20261003T210854Z` | x1 build (§2); `cpu_features.txt`; 17 models, `-t 1,2,4,6,8` | done. **Its WARNING is a false alarm** (incident 11); a correction is appended |
| L3 | `L3-arm-quants-20261003T232441Z` | as on c9g | done |
| L5 | `L5-context-depth-20261004T001930Z` | as on c9g | done |
| L6 | `20261004T012911Z` | Phase 1 repeat | done; queue finished 03:53:48 |

L7 artifacts live on c9g at `~/fleet-trilogy/eval-results/`. Collect them into `android-flagship/L7-artifacts/` (as `C-artifacts/` for mac2) before the instance stops.

### Round 2 (2026-10-04): second test suites

Round 2 adds runs; it replaces nothing. **Data-retention rule:** no run directory is ever overwritten or deleted. Each re-run gets a new timestamped directory, labelled by suffix and in its `system.txt`. `proxyctl.sh collect` and `collect_when_done.sh` use rsync without `--delete`, so earlier runs and eval artifacts stay. Each run's `artifacts.txt` names its own eval artifacts, which share `C-artifacts/` with earlier runs. Model-hash files are timestamped (`model-sha256-<ts>.txt`); the round-1 collection's are `model-sha256.txt`.

| Label | Platform | Run dir | Purpose | Status |
|---|---|---|---|---|
| **C-reverse** | mac2 | `iphone-older/C-workload-20261004T042350Z-reverse` (`order: reverse, quant: q4_k_m`) | Order-effect check of test C. mac2 never throttled (F: 10,593 samples, all Nominal; drift ≤ 0.6%), so no cooldown | done 04:23-05:57. **No order effect:** p50 within ~4%, J/call within 2% of the forward run |
| **C-q4_0** | mac2 | `iphone-older/C-workload-20261004T055729Z-q4_0` (`quant: q4_0`; `LLM_MODEL_PATH_*` recorded) | Q4_0 accuracy, latency and energy for the five candidates (`TODO-Q4_0-ACCURACY-CHECK.md`). Phi and Gemma-3-4B Q4_0 from G; Llama, GLM, Qwen3 downloaded first. Same pairs and flags as C | done 05:57-07:20; collected 07:20 (35/35 model hashes match). Results in `TODO-Q4_0-ACCURACY-CHECK.md`: J/call -14 to -41%; Gemma-3-4B Edge Triage mismatch 0% → 30%, the others hold |
| **M4 Max gated-reverse** | m4max-macbook | `m4max-macbook/20261004T043341Z-gated-reverse` (`order: reverse`, `gate: /tmp/m4max-powermetrics-3.txt`). The first attempt is kept as `20261004T042254Z-gated-reverse-ABORTED` (incident 21, no sessions ran) | The 18 single-model sessions last-to-first, each started only after 60 s of Nominal thermal pressure (`GATE_PM`; waits logged as `cool-wait_*` windows). Gives cool per-model numbers to compare with the warm caffeinated rerun | done 04:33-05:11 (results above) |
| **iphone-flagship full suite** | mac-m4 | `iphone-flagship/…` | `scripts/bench_mac_all.sh`, unattended: `bench.sh --quick` smoke → Phase 1 (17 + Qwen3.8-27B) → C smoke → C → extras queue (E A B D E F I E) → G/H → C-reverse → C-q4_0. The same scripts as mac2; repo copied for C | **done 12:56; collected 14:55.** Provisioned in 19 min. Driver log `results/all-20261004T045017Z.log`. Runs:
- Phase 1 `20261004T045158Z` (04:52-05:15)
- C `C-workload-20261004T051713Z` (05:17-06:13)
- extras queue 06:13-10:36: A `…064452Z`, B `…080512Z`, D `…080625Z`, F `…090309Z`, I `…100414Z`, E `20261004T062205Z` / `…084020Z` / `…101410Z`
- G `G-quant-variants-20261004T104633Z`, H `H-mlx-20261004T105726Z`
- C-reverse `C-workload-20261004T110245Z-reverse`, C-q4_0 `C-workload-20261004T120252Z-q4_0`

Checks: 36/36 model hashes match, 502/502 llama-bench JSONs valid, 759/759 windows exit 0, no host identifiers |

**mac-m4 (M4, 24 GB) headline results** (`scripts/summarize.py` on the runs above):

| | M1 (mac2) | M4 (mac-m4) | iPhone 17 Pro (published) |
|---|---|---|---|
| Metal tg128, Qwen3.5-2B | 39.7 tok/s | 67.3 | 39.1 |
| Metal tg128, Gemma-4-E2B | 35.4 | 59.1 | 38.8 |
| Metal tg128, Llama-3.1-8B | 12.7 | 21.7 | — |
| Metal tg128, Qwen3.8-27B (only the M4 holds it) | — | 6.3 | — |
| Test C, Phi Edge Triage: p50 / J per call | 1.91 s / 20.0 J | 1.18 s / 15.2 J | — |
| Test C, Gemma-3-4B Tier 2 | 2.67 s / 27.1 J | 1.66 s / 21.5 J | — |
| C-q4_0, Gemma-3-4B Edge Triage mismatch (Q4_K_M → Q4_0) | 0/270 → 41/135 | 0/135 → 43/135 | — |

- **The M4 overshoots the iPhone 17 Pro's generation speed about 1.5-1.7×** (bandwidth 120 vs 76.8 GB/s), so M1 remains the closer stand-in.
- **On the real workload the M4 is 1.6-1.8× faster than M1, at 10-25% less energy per call.** Its Phi 15.2 J matches the M4 Max laptop running cool.
- **The Gemma-3-4B Q4_0 regression reproduces on a second machine.** Q4_0's J/call drops 10-36% on the M4, against 14-41% on M1.
- **The mac-m4 never throttled:** F's 7,179 thermal samples were all Nominal, so both Mac minis are single-regime. Only the MacBook (M4 Max) throttles.

**Round-2 infrastructure:**
- Both Android proxies destroyed 04:26, after collection and hash checks (17/17 each).
- `enabled_proxies` default = `["iphone-older", "iphone-flagship"]`.

### Round 3 (2026-10-04): a harder task, and thinking on vs off

**Why.** The 2026-09-26 narrowing (impact track row 5) was made for the Pi 4. Small models asked for severity, action and escalation in one call contradicted themselves, so severity and the action moved into deterministic code and the LLM kept only a bounded escalation. Round 3 asks whether newer hardware and bigger models can take the whole job back, and what the chat format and thinking add. Requested by the user 2026-10-04; proposals in the paper outline §VII.

**Harness** (opt-in, entirely in `tests/`; the production pipeline is untouched, and its prompt, grammar and deterministic functions are imported, never modified):
- `tests/model/round3_eval.py`: tasks, modes, grammars, scoring.
- `tests/model/test_round3_tasks.py`: one pytest session = one model × task × mode. Artifact `eval-results/compare-round3-<host>-<ts>.json` with the config, a summary and every call (content, tokens, latency, scores).
- `tests/model/test_round3_scoring.py`: 7 pure tests of the scorer.
- Options in `tests/model/conftest.py`: `--round3-server`, `--round3-gguf`, `--round3-task`, `--round3-mode`, `--round3-n` (2), `--round3-think-budget` (2048), `--round3-temperature` (0.2, production's), `--round3-variant`.

**Tasks:**

| Task | What the LLM does | Cells (n = 2) | Card budget |
|---|---|---|---|
| `narrow` | Production's prompt and grammar: the bounded escalation only | production's gate-2 shape: the canonical event, baseline held at medium, the three `ESCALATION_SCENARIOS`, 3n calls each = 18 | 300 tokens (production's) |
| `full` | The whole job: classify the baseline severity from the physics rules `classify_severity` uses (stated in the prompt), decide the escalation from production's operational rules (verbatim), then derive the final severity and the recommended action | six physics profiles (low, medium-volatile, medium, high-volatile, high-decel, high-abs) × three scenarios × n = 36 | 450 tokens (Phi's full card ran 187-300 in the smoke test, one truncated at 300) |

- **Answer key:** `classify_severity`, `apply_escalation` and `recommended_action_for` for the physics and the derived fields. For the escalation, `ESCALATION_SCENARIOS`' documented expected directions (the production eval's hypothesis, with the same caveat).
- **Scores per call:** `format_ok` and `escalation_ok`. The full task adds `baseline_ok`; `consistent` (severity and action follow from the model's *own* baseline and escalation by the stated rules: the contradiction the narrowing removed); `severity_ok`; and `action_ok`. `all_ok` = all of them. An unparsed card fails every score.

**Modes** (how the prompt reaches the model):
- `raw`: exactly as production, the bare prompt on `llama-server /completion` with no chat template. Qwen3-family models can't think in this mode.
- `chat-off`: the Qwen chat format (user turn, assistant turn pre-filled with the empty `<think>\n\n</think>\n\n` block, as both models' own templates do for `enable_thinking=false`).
- `chat-on`: the assistant turn pre-filled with `<think>\n`; the grammar admits free reasoning up to `</think>`, then the same card. `n_predict` = card budget + think budget (2,048).
- `chat-budget` (added 2026-10-04 after Qwen3.5-9B's runaway, below): budget forcing in two calls. Phase 1 reasons with no grammar and `stop: ["</think>"]`, at most the budget. If the budget runs out, `</think>` is appended for the model (`think_forced` records it). Phase 2 generates the card under the usual grammar.

Everything else (prompt text, temperature, scenarios) is identical across modes. Timeout per call = max(the harness default, 60 s + 0.25 s × `n_predict`). `llama-server` startup timeout 600 s (the 27B model on the MacBook).

**Session machinery:** as test C. Each model × task × mode is its own pytest session and energy window in `windows.log`, mapped to its artifact in `artifacts.txt`, with `idle-pre`, a 20 s `idle-gap_*` after each session, and `idle-post`. On the M4 Max every session also waits for 60 s of Nominal thermal pressure first (`cool-wait_*` windows), as in `-gated-reverse`. The order is part 1 (every model, both tasks, raw), then part 2 (the Qwen models, chat-off and chat-on, both tasks), so a cut-short run still answers the core question.

**Runs:**

| Label | Platform | Run dir (`eval-results/phone-proxies/…`) | What | Status (2026-10-04 19:30) |
|---|---|---|---|---|
| R3 | m4max-macbook | `m4max-macbook/20261004T153710Z-round3` | `bench_round3_m4max.sh`, 10 models (part 1: Phi-3.5-mini, Gemma-3-4B, Llama-3.1-8B, GLM-4-9B, Qwen3-8B, Gemma-3-12B, Gemma-4-12B, Qwen3-14B, Qwen3.5-9B, Qwen3.8-27B; part 2: the four Qwen models). n = 2; Qwen3.8-27B n = 1. 36 sessions | done 15:37-19:00, 110 windows, all exit 0. **Ran at the default context (incident 23): accuracy valid; latency and energy carry the memory-pressure confound** |
| R3 | mac2 | `iphone-older/round3-20261004T152604Z` | `bench_round3.sh … 2`: the same minus Qwen3.8-27B (doesn't fit 16 GB); Qwen3.5-9B chat-on skipped (below). 28 sessions (30 less the 2 skipped) | running: session 26 of 28. Own `powermetrics.txt` |
| R3 | mac-m4 | `iphone-flagship/round3-20261004T164536Z` | as mac2. Started by `oneoff/round3_after_qconfirm.sh` when the Q4_0 confirmation ended | running: session 26 of 28. Harness updated mid-run (below) |
| R3 think 4096 | m4max-macbook | `m4max-macbook/20261004T191021Z-thinkbudget4096`; first attempt `…190719Z-thinkbudget4096-ABORTED` (incident 23) | Qwen3.5-9B chat-on, both tasks, at a 4,096-token think budget, n = 2: runaway or a tight budget? Queued by another Claude session at the user's request (`oneoff/thinkbudget_after_ablation.sh`); this session owns it since 19:14 | running, `LLAMA_ARG_CTX_SIZE=8192` (`CONTEXT-SIZE.txt`). **Narrow done 19:33: all_ok 61% [39-80] (33% at 2,048), 2 of 18 truncated (12 of 18 at 2,048); thinking took 1,405-3,507 tokens where it closed; p50 64 s.** So on the narrow task it is mostly a tight budget, not endless reasoning, and still below chat-off's 72% |
| ctx8192-check | m4max-macbook | `m4max-macbook/<ts>-ctx8192-check` | `bench_workload_m4max.sh`: Phi-3.5-mini and Llama-3.1-8B on the Edge Triage Pipeline, 3 reps, gated, at an 8k context. Against `-gated-reverse` it sizes incident 23's confound | queued (`oneoff/m4max_chain_after_thinkbudget.sh`) |
| R3 ablation | m4max-macbook | `m4max-macbook/<ts>-ablation`; first attempt `20261004T190116Z-ablation-ABORTED` (1 cell, incident 23) | `bench_ablation_m4max.sh … 2`: Phi-3.5-mini, Gemma-3-4B, Llama-3.1-8B (the full task's weakest) and Qwen3-14B (a ceiling) × 7 variants (below), full task, n = 2. 28 sessions | queued after the ctx check, at 8k |
| R3 budget | m4max-macbook | `m4max-macbook/<ts>-round3-budget` | `bench_budget_m4max.sh … 2 1024`: the four Qwen models, both tasks, chat-budget at 1,024 thinking tokens (Qwen3.8-27B n = 1) | queued after the ablation, at 8k |
| R3 budget | mac-m4 | `iphone-flagship/round3-budget-<ts>` | `bench_budget.sh … 2 1024`: Qwen3-8B, Qwen3-14B, Qwen3.5-9B, both tasks, chat-budget at 1,024 | queued behind round 3 (`oneoff/budget_after_round3.sh`) |

How each run was started (waiters, hand-offs, the skip) is in `deploy/aws-phone-proxies/scripts/oneoff/` and its README. Two harness smoke tests on the MacBook before the local run belong to no run dir: `eval-results/compare-round3-COMP-J2D9D71YNJ-20261004T152216Z.json` (Phi-3.5-mini, full, raw, n = 1) and `…152349Z.json` (Qwen3-8B, narrow, chat-on, n = 1). They are kept, not analysed.

**Prompt ablation variants** (`tests/model/round3_ablation.py`, `test_round3_ablation.py`, 7 pure tests in `test_round3_ablation_scoring.py`). They are cumulative and were fixed before any ablation result was seen, so there is no per-variant tuning on the test set. Artifact `compare-round3-ablation-<host>-<ts>.json`.

| Variant | Adds |
|---|---|
| `base` | round 3's full prompt and grammar, exactly |
| `facts` | the grammar makes the model write three physics facts first (`abs_engaged`, `deceleration_band`, `severe_stop_and_go`), and the prompt asks for them; scored as `facts_ok` |
| `tables` | the severity rules, the final-severity shift and the actions as lookup tables |
| `template` | each model's own chat template (`/apply-template`); for the Qwen models the empty think block is pre-filled (thinking off) |
| `examples` | three worked examples whose values and contexts differ from every test cell (one example's dispatch note was reworded so it couldn't leak a scenario's wording) |
| `temp0` | temperature 0 (production uses 0.2) |
| `grammar` | a separate tier on top of `examples`: the grammar computes severity and action from the model's own baseline and escalation ("the model judges, the grammar computes"), so the contradiction class is removed by construction |

**Decisions and changes during round 3:**
- **Qwen3.5-9B chat-on skipped on both hosts** (user decision, ~18:55). On the M4 Max its reasoning ran past the 2,048-token budget without closing `</think>`, and the hosts would only repeat that more slowly. `oneoff/skip_qwen35_chaton.sh` set the GGUF aside after the chat-off sessions, so `bench_round3.sh` logged `skip … missing` for those two sessions, then restored the file when the run ended. Each run dir gets `SKIPPED-qwen3.5-9b-chat-on.txt`. Capped thinking is measured instead by the budget runs.
- **The mac-m4's harness was updated during its round 3** (18:56 UTC, by copy-then-rename): `round3_eval.py`, `test_round3_tasks.py` and `conftest.py` gained `chat-budget` for the queued budget run. A diff against mac2's copy (pushed 15:25, never updated) shows additions only: the new mode, its option choice and a `think_forced` field (default false). `raw`, `chat-off` and `chat-on` are byte-for-byte the same code, so sessions before and after the update are comparable.
- **The thinkbudget4096 run** was written by the user's other Claude session (by mistake in the wrong window), then relaunched by this session unchanged except for the context size (user decision, "option b").

**First results: M4 Max, accuracy** (`scripts/round3_report.py` on `20261004T153710Z-round3`; `all_ok` with 95% Wilson intervals):

| Model | narrow, raw (n = 18) | full, raw (n = 36) | full, chat-off | full, chat-on (2,048) |
|---|---|---|---|---|
| Phi-3.5-mini | 100% [82-100] | 11% [4-25] | | |
| Gemma-3-4B | 100% [82-100] | 22% [12-38] | | |
| Llama-3.1-8B | 94% [74-99] | 14% [6-29] | | |
| GLM-4-9B | 89% [67-97] | 39% [25-55] | | |
| Gemma-3-12B | 72% [49-88] | 58% [42-73] | | |
| Gemma-4-12B | 67% [44-84] | 50% [34-66] | | |
| Qwen3-8B | 100% [82-100] | 36% [22-52] | 44% [30-60] | 47% [32-63] |
| Qwen3-14B | 33% [16-56] | 42% [27-58] | 72% [56-84] | 78% [62-88] |
| Qwen3.5-9B | 56% [34-75] | 22% [12-38] | 72% [56-84] | 0% [0-10], 36/36 truncated |
| Qwen3.8-27B (n = 9 / 18) | 78% [45-94] | 33% [16-56] | 67% [44-84] | 67% [44-84] |

- **The narrowing was justified.** On the full task in production's raw mode, no model exceeds 58% end to end, and the small models (Phi, Gemma-3-4B, Llama) fall to 11-22%, against 94-100% on the narrow task. Every component drops for them: `baseline_ok` 53-78%, `consistent` 47-53% (the contradiction class the narrowing removed), and even `escalation_ok` 53-58%.
- **The chat format is a large lever for the Qwen models.** Thinking off, it lifts the full task from 42% to 72% (Qwen3-14B) and from 22% to 72% (Qwen3.5-9B). That is a prompt-path change, not a model change.
- **Thinking adds little for its cost.** Full task: Qwen3-14B 72% → 78%, Qwen3-8B 44% → 47%, Qwen3.8-27B 67% → 67%, at 4-11× the median latency (Qwen3-14B 5.0 s → 20.3 s; Qwen3-8B 1.45 s → 15.9 s). The exception is Qwen3-14B on the narrow task, 67% → 94%.
- **Qwen3.5-9B's thinking runs away.** It hit the 2,048-token budget on every full-task call and 12 of 18 narrow ones. The thinkbudget4096 run tells runaway from a tight budget; budget forcing measures it capped.
- Latency and energy from this run are not reported yet: incident 23's memory-pressure confound applies until the ctx8192-check sizes it. Within this run, chat-on vs chat-off ratios on one model share the confound.

**Analysis:** `scripts/round3_report.py [--trace <powermetrics>] <run-dir>…` aggregates every round-3-family run dir (round 3, budget, thinkbudget, ablation) across platforms. It gives:
- per platform × model × task × mode: rates with Wilson intervals, latency, tokens, think tokens, truncations, forced closes, and J/call above idle (session window / calls, an upper bound that includes server start);
- narrow-vs-full, thinking-mode and ablation tables;
- a cross-platform agreement table that flags cells whose intervals don't overlap.

Host runs carry their own trace. The MacBook runs share `/tmp/m4max-powermetrics-4.txt` (pass `--trace`; a snapshot is copied into the run dirs afterwards).

## 6. Incident log

Every problem, its effect on the data, and the fix. "No data impact" means no measurement was affected.

| # | When | What happened | Data impact | Fix |
|---|---|---|---|---|
| 1 | 10-03 ~18:20 | First `terraform apply` failed: EC2 rejects apostrophes in security-group descriptions | none | description reworded |
| 2 | 18:25 | `rm -f .bench-*.log && start-all` under the Bash tool's zsh: no matching file aborted the line, so `start-all` never ran, and the job still exited 0 | none (proxies were still provisioning) | re-run under `bash -c` |
| 3 | 19:04 | mac2: macOS `nohup` refuses to start over non-tty SSH ("can't detach from console"); `bench.sh` never ran | none | `( trap '' HUP; exec … ) > log 2>&1 < /dev/null &`; `start` now checks the job is running |
| 4 | 19:06 | mac2: `sudo kill -INT <sudo pid>` didn't stop powermetrics. sudo won't relay a signal from its own process group, the script's, so `bench.sh` hung after its last window | none (all windows complete; stopped by hand) | `sudo pkill -INT -P <sudo pid> -x powermetrics` |
| 5 | 19:07 | First Metal launch: ~25 s of shader compilation at CPU power inside the smoke test's `metal-pp` window | smoke test only (excluded) | untimed Metal warm-up before every run |
| 6 | 18:35-18:46 | mac2 host: `InsufficientHostCapacity` in us-west-2a; the provider retried silently | none; cancelled cleanly, nothing allocated | per-proxy `availability_zone`; mac2 in us-west-2c |
| 7 | 20:10 | Copying the repo to mac2: macOS openrsync misread `ec2-user@IP:fleet-trilogy/` and made a local copy (`ec2-user@<mac2-ip>eet-trilogy/`, 134 identical files) | none; deleted after a diff | tar over SSH |
| 8 | 20:12 | The safety check flagged copying and running repo code on mac2 as possible data exfiltration; denied twice | none; C paused | the user approved C; local credential scan clean |
| 9 | 20:28 | `start-extras` on c7g scp'd `bench.sh` over the copy Phase 1 was still running. bash reads scripts incrementally, so the run's last lines came from the new file: syntax error, no `LATEST`, an empty `llama-bench_cpu_GLM-4-9B-0414-Q4_K_M.json` | **none on measurements:** all 17 models had 10 entries (the model loop was already parsed). Empty file removed; `NOTE.txt` in the run dir | `proxyctl.sh push`: copy to `.<name>.new`, then `mv` (a new inode; a running script keeps the old one) |
| 10 | 20:26 | c9g launch: `chmod … && ( … ) &` backgrounds the whole `&&` list, so SSH held the session open. Then the leftover launch shell's own command line contained `/opt/phoneproxy/bench.sh` and matched the queue's own `pgrep` for Phase 1: deadlock | none; L4 started 20:30 instead of ~20:26 | `;` instead of `&&`; killed the leftover shell |
| 11 | 21:09 | L2's check logged "x1 build still reports SVE or MATMUL_INT8". False alarm: llama.cpp omits disabled features, and the check looked for `= 0` | none; the build is X1-faithful | check now greps for `SVE = 1 | MATMUL_INT8 = 1`; correction appended to `cpu_features.txt` |
| 12 | ~21:20-22:40 | Background watchers (pi5 collect, c7g collect, pi5 collect-and-shutdown) hit the Bash tool's limits. The shutdown job's SSH was also reset by a network drop | none; pi5 collected, checked (17/17 complete) and shut down by hand at 22:39 | — |
| 13 | 23:30:48 | **The MacBook idle-slept** (`pmset`: "Idle Sleep", 10 min) during the M4 Max reruns; it stayed asleep until 00:30:47 | Qwen3-8B r3 and the five-model session lost; the 17 earlier sessions valid (Qwen r2 ended 23:29:35). Display sleep at ~10 min before that may have slowed later reps (open question 4) | `bench_workload_m4max.sh` re-execs itself under `caffeinate -dims`; resume run |
| 14 | 00:29-00:31 | **L7 on c9g: `llama-server` OOM-killed** for Phi-3.5-mini and Llama-3.1-8B (anon-rss 15.4 GB of 15 GiB). The backend sets no context size, so the server uses each model's training context. 128k for both; Phi has no GQA, ~50 GB of KV; Llama ~17 GB. Metal shrinks the context to fit GPU memory, so mac2 and the M4 Max were unaffected | Phi and Llama L7 rows invalid (0% format, n=15); kept as a finding | re-run all six pairs with `LLAMA_ARG_CTX_SIZE=8192` (llama-server's env override; harness and pipeline unchanged) |
| 15 | various | AWS SSO sessions expire after ~1 h | none; only Terraform needs credentials | `aws sso login` before plan/apply |
| 17 | 10-04 01:33 | The first commit attempt failed on SSH commit signing ("communication with agent failed"): the operator was away, and the agent needs them present | none; staged files unstaged so no other session would commit them | committed on the operator's return |
| 18 | 01:34:47 → ~04:10 | **The MacBook idle-slept again** once the caffeinated run ended, which froze the local collection watcher (`collect_when_done.sh`). It was killed at the tool's 2 h limit | none on data: every AWS queue had finished by 03:53, and collection ran on wake | collection now runs under `caffeinate -i` |
| 19 | 10-04 04:26 | mac-m4 AllocateHosts: `InsufficientHostCapacity` in us-west-2a (AWS: capacity in us-west-2b, us-west-2d). The provider retried silently | none; the apply was interrupted after both Android teardowns completed, nothing allocated | `iphone-flagship.availability_zone = "us-west-2b"` |
| 20 | 10-04 04:22-04:32 | `sudo powermetrics` for the gated M4 Max run sat at its password prompt twice, unnoticed | none; the gate waited for the trace file to appear | `sudo -v && sudo powermetrics …` |
| 21 | 10-04 04:22-04:33 | The first gated M4 Max run never left its first cool-wait. The gate read the trace's last 400 KB, but a sample with the thermal sampler is ~8 KB, so the window held ~49 samples against the 120 Nominal it requires | none; only idle-pre ran. Directory kept as `…-gated-reverse-ABORTED` with `ABORTED.txt` | gate reads 4 MB (~480 samples); verified on the live trace before relaunch |
| 22 | 10-04 05:12 (found) | **Analysis bug:** `summarize.py: load_powermetrics` fitted one time offset per trace, assuming no pauses. powermetrics stops while a Mac sleeps, so traces spanning a sleep (M4 Max: `20261003T230334Z`, 23:30-00:30; `-caffeinated` once re-copied in full, 01:34-04:10) were misaligned by over an hour | raw data intact. No reported number was affected: the caffeinated energies came from a pre-sleep snapshot, and the first run's per-session stats used header times. mac2 traces have no gaps | offset fitted per gap-free segment; mac2's Phase 1 energy table is byte-identical before and after |
| 23 | 10-04 19:03 (found; reported by the user's other session) | **M4 Max: `llama-server` at the model's full training context.** With no context size, Phi-3.5's server sized its KV cache to 128,256 tokens: 51.2 GB resident, 58 of 64 GB wired, swap 6.5 of 8.2 GB (checked via `/props` and `ps`). Same root cause as incident 14, but the 64 GB machine lets the allocation succeed and swaps instead of being OOM-killed. The Mac proxies were unaffected (llama.cpp fit the context to memory: mac2 17,408 and mac-m4 40,960 tokens for Qwen3-14B; swap under 0.5 GB) | accuracy: none. **M4 Max latency and energy in every M4 Max run before 19:05 (C reruns, caffeinated, gated-reverse, round 3) carry a memory-pressure confound**; size to be measured by the `-ctx8192-check` run. The first ablation (1 cell) and the other session's first thinkbudget4096 run are kept as `-ABORTED` | `LLAMA_ARG_CTX_SIZE=8192` for every later M4 Max run (`CONTEXT-SIZE.txt` in each run dir); the other session's run relaunched with it by user decision, script unchanged |
| 16 | 22:50 | The default `enabled_proxies` was still the smoke test's `["android-flagship"]`, so a plain `terraform apply` would have destroyed c7g and mac2 mid-run | none (caught) | default = the deployed set; plain plan = no changes |

**Guards added along the way:**
- **AMI drift:** `lifecycle { ignore_changes = [ami] }` on both instance types, so a newer "current" AMI can't replace a proxy mid-run.
- **Uncollected eval artifacts:** C's and L7's eval artifacts live in each host's repo copy. Collect them before teardown.

## 7. Integrity checks done

- **Phase 1:** every model JSON is valid with the expected number of entries (10 on c9g and c7g, 6 on pi5, 2 per Mac file); `windows.log` exit codes are all 0 on mac2.
- **pi5:** all 17 files checked before its shutdown and termination.
- **c7g Phase 1:** all 17 files checked after incident 9.
- **C:** 18/18 windows exit 0. The artifact for each window is mapped in `artifacts.txt`. Rep spread is ≤ ±2% J/call for every pair.
- **mac2 run-to-run** (Phase 1 vs E #1): median |Δ| is 0.2% for Metal tg, 0.2% for Metal pp and 0.1% for CPU tg; the maxima are 1.1%, 3.8% and 3.5%.

## 8. Caveats and open questions for the evaluation

1. **Proxies, not phones.**
   - The Graviton proxies have more memory bandwidth than the devices they stand in for (§1). Treat their generation speeds as upper bounds.
   - mac2 (M1, 68 GB/s) matches published iPhone 17 Pro generation speed (Gemma-4-E2B 35.4 vs 38.8 tok/s; Qwen3.5-2B 39.7 vs 39.1). That source's runtime and method aren't verified, and M1 overstates an iPhone 12 (A14, 34 GB/s) about 2×.
   - The user prefers hardware-real measurements to bandwidth "corrections". Show any correction side by side with the raw number, labeled.
2. **Energy coverage differs.** Mac figures are chip-only (powermetrics) while the Pi 4 is whole-board at the wall. The Android proxies have no energy data at all.
3. **Thermals.** Servers and the Mac mini don't throttle like phones, so F is a steady-state baseline, not phone thermals.
4. **The M4 Max slowdown is thermal (resolved, §5).**
   - Sustained load takes the MacBook to Heavy thermal pressure in ~12 min.
   - The gated reverse-order run shows the cost: cool-start sessions are 24-77% faster but use 30-60% more energy per call than throttled ones. Report both regimes, labelled.
   - A laptop throttling within minutes is itself evidence for the phone-thermals question.
   - mac2 (actively cooled Mac mini, headless) never left Nominal: F's 10,593 samples, drift ≤ 0.6%. Its numbers are single-regime.
5. **The 09-26 five-model numbers are invalid as per-model latencies** (§5): a multi-model session roughly doubles Phi's latency on the M4 Max. Where the impact track uses them (listed 2026-10-04; the impact track is not edited here, the user decides):
   - **Row 15** (M4 → Pi ratio table, "38-200x"): its M4 p50s back out to 0.75 s (Phi), 2.05 s (Gemma-3-4B) and 1.25 s (Llama), the 09-26 values; its p95 ratios come from the same session. With single-model p50s (0.36, 1.24-1.70, 1.03-1.20 s) the p50 ratios become ~99×, ~45-62× and ~62-73×. Recompute after the ctx8192-check (incident 23), which may shift the single-model numbers too.
   - **Row 24's detail section** ends "the Mac's per-call latency today (0.36 s Phi, 0.51 s Gemma p50) is about twice as fast as the published M4 figures (0.75 s, 0.63 s); not yet diagnosed". The Phi half is now diagnosed (the multi-model session). The Gemma Tier 2 0.63 s also came from a multi-model session, likely the same effect but not re-tested.
   - Copies of row 15 outside the impact track: `TALK2-SLIDE-PLAN.md` (the ratio table), `TALK2-SLIDE-PLAN-ALT-CHARTS.md`, `TALK2-POWER-MEASUREMENT-PLAN.md`, `TALK2-GREENEST-TOKEN-REPORT.html` (the 38-200× stat and the 47.5× bar), and the Talk 1 handoff note in the other session's untracked slides.
   - Not affected: row 8 (accuracy only), row 23 (word counts = tokens/s × latency from the same calls, so the inflation cancels), row 24's energy and ratio (10-02 single-model runs).
6. **Q4_0 accuracy** on the Talk 2 tasks is untested. See `TODO-Q4_0-ACCURACY-CHECK.md`.
7. **The x1 build is faster than native on c7g:** +3-12% tg, up to 2.5× pp. Native's SVE paths underperform, so the server-only ISA didn't inflate c7g. The mechanism (NEON or llamafile kernels vs SVE-256) is unverified.
8. **D and L5 (context depth):** speed only. D's energy includes the untimed re-fill.
9. **L1 capacity** is a cgroup ceiling at a tiny context, not an Android or iOS app budget. Device Farm is the ground truth.
10. **Server context-size defaults** (incident 14) are themselves a deployment finding for 16 GB CPU devices.

## 9. Where things are

**Reproducing:**
- `deploy/aws-phone-proxies/REPRODUCE.md` is the step-by-step runbook, with every pinned version: llama.cpp commit, harness commit, AMIs, toolchains, Terraform providers.
- `deploy/aws-phone-proxies/MODELS.lock.tsv` pins 105 model files with repo revision and SHA-256 (`scripts/models_lock.py`; Qwen3.5-9B appended by hand for round 3).


| What | Where |
|---|---|
| Raw results | `eval-results/phone-proxies/<platform>/<run>/` |
| Preliminary tables | `eval-results/phone-proxies/PRELIMINARY-20261003.md` (`scripts/prelim_report.py`) |
| Per-run tables | `python3 deploy/aws-phone-proxies/scripts/summarize.py eval-results/phone-proxies/<platform> [<run>]` |
| Round 3 tables (accuracy, thinking, ablation, cross-platform) | `python3 deploy/aws-phone-proxies/scripts/round3_report.py [--trace <powermetrics>] <run-dir>…` |
| How each run was started (waiters, hand-offs) | `deploy/aws-phone-proxies/scripts/oneoff/` and its README |
| Earlier measurements (Pi 4 meter, M4 Max contrast) | `docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md`, rows 22-28 and their detail sections |
| Plan and status | `docs/TALK2-HARDWARE-SPECTRUM-TEST-CATALOG.md` |
| Deferred work | `talks/talk2-greenest-token/TODO-REAL-PHONE-BENCHMARKS.md`, `TODO-RAM-CAPACITY-TEST.md`, `TODO-Q4_0-ACCURACY-CHECK.md` |

**Committing:** rounds 1-2 are committed (8512294, bca0e0d). Round 3 is committed when its runs end. Never commit `.terraform/`, the state files, `.ssh/` or `.bench-*.log` (`.gitignore` covers them), nor other sessions' files (`docs/TODO-OTHER-SESSION-FILES.md`).
