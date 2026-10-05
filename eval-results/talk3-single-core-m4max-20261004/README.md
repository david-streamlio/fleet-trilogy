# Talk 3: Tier 2's LLM call on one CPU core (M4 Max, 2026-10-04)

Backs the Talk 3 promise "AI-enriched streams on a single CPU core" and its
resource-profile slide. Two rounds: the original subprocess path (a
`llama-completion` process per call), then `InProcessLlmBackend` (llama-cpp-python
inside the Function, model loaded once).

## Headline: seconds per warning on one CPU core

| How the model runs | Build | Median (n=10) |
|---|---|---|
| Subprocess per call (as Talk 3 shipped) | Homebrew `llama-completion` 0.5.0 | 28.96 s |
| New model every call (subprocess-style) | llama-cpp-python 0.3.36, compiled here | 15.52 s |
| **Model kept inside the Function** | llama-cpp-python 0.3.36, compiled here | **12.04 s** |

- Same build, kept vs. reloaded: 15.5 s → 12.0 s (−22%): no ~1 s model load,
  and 98 of the prompt's 361 tokens (the fixed instructions) reused from the
  previous call.
- Homebrew build vs. local build, both reloading every call: 29.0 s → 15.5 s. The
  cause isn't isolated (different llama.cpp versions and compile flags; the
  Homebrew bottle is a generic build). Don't present it as a subprocess cost.
- Best case, not typical: the same corridor's cards twice in a row reuse almost
  the whole prompt; that second call took 4.9 s end to end through
  `GlobalSynthesisFunction` (`llm_backend=inprocess`, `threads=1`).

## Round 1: subprocess per call

### What was measured

The exact command `SubprocessLlmBackend` builds for Tier 2 (`-m -p -n 256 -t N
--temp 0.7 -no-cnv`), on the real demo prompt: `render_synthesis_prompt()` over
the three cards in `deploy/talk3-demo-cards.jsonl` (361 tokens). Each call is a
fresh `llama-completion` process, as in `GlobalSynthesisFunction.process()`.
10 timed calls per setup after 1 untimed warm-up.

- Host: MacBook Pro, Apple M4 Max (12 performance + 4 efficiency cores), 128 GB.
- llama.cpp: Homebrew 0.5.0, commit `7fe450e19` (the same commit as the Talk 2
  hardware-spectrum runs).
- Model: unsloth `gemma-3-4b-it-Q4_K_M.gguf`, sha256 `04a43a22…7d19` (matches
  `eval-results/phone-proxies/*/model-sha256*.txt`).
- Setups:
  - `default_t4`: the Function's real default on a Mac. No device flags, so
    llama.cpp offloads to the **Metal GPU**.
  - `cpu_t4`: `-t 4 -dev none -ngl 0`, CPU only.
  - `cpu_t1`: `-t 1 -dev none -ngl 0`, CPU only, one compute thread.
- Wall time from Python; phase times from llama.cpp's own `common_perf_print`;
  CPU time and memory from `/usr/bin/time -l` per process.

### Results (median [min–max], n=10)

| Setup | Wall per warning | Cores busy (CPU ÷ wall) | Prompt tok/s | Output tok/s | Output tokens | Model load | Memory footprint |
|---|---|---|---|---|---|---|---|
| Metal GPU, default | **1.23 s** [1.20–1.44] | 0.47 | 1729 | 127 | 58 | 0.24 s | 3.0 GB |
| CPU, 4 threads | **9.01 s** [8.59–9.15] | 3.63 | 62.5 | 33.8 | 67 | 0.93 s | 5.4 GB |
| CPU, 1 thread | **28.96 s** [28.27–29.59] | **1.00** | 16.9 | 9.8 | 61 | 1.07 s | 5.4 GB |

- Peak resident set: 5.3 GB (GPU) and 7.7 GB (CPU); it counts the memory-mapped
  model file, which the "footprint" column doesn't.
- One thread really is one core: CPU time equals wall time (28.95 s vs 28.96 s).
- On one thread, reading the 361-token prompt is ~21 s of the ~29 s; writing
  the ~60-token answer is ~6 s; loading the model ~1 s.
- All 30 calls exited 0 and returned a parseable `spoken_warning`.
- The pre-measurement estimate for one M4 core was ~14 s
  (from llama-bench `-t 1`, M4 Mac mini). Measured is ~2x that, so treat
  llama-bench-based one-core estimates for other hardware as optimistic.

### Accuracy of the 30 warnings (hand-checked)

The input: truck-47 high/9 min, truck-12 high/7 min, truck-31 medium/6 min; code
decided corridor-wide plus reroute. 7 of 30 warnings have a factual slip:

- "9 to 12 minutes" / "9-12 minutes" (3: `default_t4` 7, `cpu_t4` 2 and 6).
  No input says 12; probably truck-12's number read as minutes.
- "one reporting high severity and two others" (1: `cpu_t1` 2). Two were high.
- No reroute mentioned although code recommended one (2: `cpu_t1` 6 and 9).
- "impacting all lanes", not in the input (1: `cpu_t4` 5).

Two of the three warm-up calls in `smoke.jsonl` also said all three trucks were
high severity; that didn't recur clearly in the 30 timed calls. Talk 2's 0%
grounding rate came from string checks, which don't catch any of these.

## Round 2: in-process (`measure_inprocess.py`)

`InProcessLlmBackend`, llama-cpp-python 0.3.36 built from source on this Mac
(Metal compiled in). Same model file and prompt shape, but each call is a different
incident: the three demo cards moved to a rotating corridor (I-95N, I-90E, I-80W,
I-5S, I-10E), so consecutive prompts share only the fixed instructions. One process
per setup; 1 untimed first call (includes the model load for `kept_*`), then 10.

| Setup | First call | Median [min–max] | Cores busy | Prefix reused | Peak RSS |
|---|---|---|---|---|---|
| `kept_t1`: model kept, 1 thread, CPU | 15.54 s | **12.04 s** [11.17–13.12] | 1.00 | 98 / 361 tok | 5.3 GB |
| `fresh_t1`: new model every call, 1 thread, CPU | 15.67 s | 15.52 s [15.29–15.79] | 1.00 | 0 | 5.3 GB |
| `kept_t4`: model kept, 4 threads, CPU | 5.14 s | 3.53 s [3.25–3.87] | 3.99 | 98 | 5.3 GB |
| `fresh_t4`: new model every call, 4 threads, CPU | 5.15 s | 5.05 s [4.99–5.14] | 3.52 | 0 | 5.3 GB |
| `kept_gpu`: model kept, all layers on Metal | 1.22 s | 0.72 s [0.66–0.81] | 0.08 | 98 | 2.9 GB |

- CPU only means CPU only here: `gpu_layers=0` also turns off llama.cpp's
  automatic GPU offloads (`op_offload`, `offload_kqv`); cores busy = 1.00 at one
  thread.
- Output: 63–65 tokens median; every call returned a parseable `spoken_warning`,
  named the corridor and mentioned the reroute.
- **Sampling was deterministic per process** (llama-cpp-python's default seed):
  `kept_t1` and `kept_t4` produced the same 10 warnings, and each `fresh_*` setup
  only 5 (one per corridor). 25 distinct warnings in all. `InProcessLlmBackend`
  now seeds randomly unless `seed=` is passed, like `llama-completion`.
- Factual slips in the 25 distinct warnings: 6 (about 1 in 4, as in round 1):
  "9 to 12 minutes" (3), "three trucks … high severity" (2), "one … high
  severity" (2); one warning has two. Files: `runs_inprocess.jsonl`,
  `summary_inprocess.txt` (from `summarize_inprocess.py`).

## Fact check (`fact_check_replay.py`)

`talks/talk3-pulsar-speaks-english/.../fact_check.py`, built after the hand checks
above, run over every distinct warning in this folder (62, counting each
corridor's version separately and including warm-ups and smoke calls): **14 fail**,
every one a real slip — "9 to 12 minutes" (8), a wrong high-severity count (6),
the recommended reroute left out (3); some have more than one. No false flags
(truck IDs like "trucks 47 and 12" are stripped before counting). Not caught:
"impacting all lanes" — the check only covers numbers, the reroute and the
corridor. Output: `fact_check_replay.txt`.

## Gating counts (`gating_counts.py`)

12 trucks × 60 ticks with an incident forced on I-95N (report.py's scenario), 5
seeds: 720 readings → 201–241 pass `is_probable_slowdown` (28–33%); the 3-60 min
ETA-slip gate removes almost nothing more here. The simulator is built to be
incident-heavy, so this is not a real-road ratio.

## Files

- `measure.py` — the measurement; run from the repo root:
  `uv run --no-sync python eval-results/talk3-single-core-m4max-20261004/measure.py 10 runs.jsonl`
  (needs `llama-completion` on PATH and the model under `~/tools/models/`).
- `summarize.py` → `summary.txt`.
- `runs.jsonl` — every call: timings, CPU, memory, the warning text.
- `smoke.jsonl` — the first single-call check of each setup (before the
  `eval time` parsing fix, so its `eval_*` fields repeat the prompt numbers).
- `gating_counts.py` → `gating_counts.txt`.
- `fact_check_replay.py` → `fact_check_replay.txt`.
- `measure_inprocess.py`, `summarize_inprocess.py` → `runs_inprocess.jsonl`,
  `summary_inprocess.txt`, `runs_inprocess.log`.
