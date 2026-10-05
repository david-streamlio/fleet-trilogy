# Talk 2: the Edge Triage Pipeline on a Raspberry Pi 4 as a real stream (edge-node00, 2026-10-05)

What one triage call costs on the Pi 4 when every event is different, measured at the
wall. The published Pi row (Table II: 31.7 s, 154 J per call) repeated one event, so
llama-server answered from a prompt it already had cached: a best case no stream of
real events gets.

## Setup
- Raspberry Pi 4 Model B Rev 1.4, 4 cores, 8 GB, kernel 6.18.50, model on the USB data
  drive (`/mnt/data`). Fan on.
- **Same as the published Pi row:** llama-server from `/mnt/data/tools/llama.cpp`
  (`8212c78`, built 2026-09-24, unchanged since), its default server settings, 4
  threads, the same GGUF: bartowski `Phi-3.5-mini-instruct-Q4_K_M.gguf`, sha256
  `e4165e3a71af97f1b4820da61079826d8752a2088e313af0c7d346796c38eff5` (identical to the
  M4 Max's copy).
- **Different from it, on purpose:**
  - `--vary-events`: consecutive calls carry different operational contexts (the three
    escalation scenarios, round-robin);
  - `--triage-prompt event-last`: `EVENT_LAST_PROMPT_TEMPLATE`, the published prompt with
    the event's fields moved after the rules (one word changed to match; see
    `triage_function.py`);
  - 18 calls (`--model-eval-runs 9 --model-confirm-multiplier 1`) instead of 60.
- Code: the working tree that became commit `8955af8`, rsynced into
  `/mnt/data/fleet-trilogy-talk3wip` (`SOURCE_COMMIT`) before that commit's
  `--model-server-args` option and `llm_extra_args` existed; this run used neither.
- Window script: `pi_power_trial_realstream.sh` (this folder), the 2026-10-02 protocol:
  meter zeroed by hand, one photo at the end, a 30 s temperature/clock/throttle trace.

```
./pi_power_trial_realstream.sh edge-triage phi35 9 --model-backend server --vary-events \
    --triage-prompt event-last --model-confirm-multiplier 1
```

## Results

| | Value |
|---|---|
| Meter (one photo, read together) | 3,883 mWh, 761 mAh, 31:46 (1,906 s); 5.10 V average |
| Energy at the wall | 3,883 × 3.6 = 13,979 J |
| Idle | 3.403 W (mean of the 3.405 / 3.401 W baselines) × 1,906 s = 6,486 J |
| **Energy above idle** | **7,493 J → 416 J per call** (18 calls) |
| Average draw during the run | ~7.73 W (the 2026-10-02 runs: 7.3-7.4 W) |
| Latency per call | **p50 82.2 s**, mean 95.1 s, p95 156 s |
| Prompt tokens read per call (median) | **148 of 514**; the rest came from the KV cache |
| Prompt reading / generating (median) | **50.5 s** (2.9 tok/s) / **31.1 s** (42 tokens, 1.35 tok/s) |
| Accuracy | 100% format (9), 0% escalation mismatch (9) |
| Throttling | 19 of 58 trace samples at the soft temperature limit, peak 84.2 °C; mean ARM clock 1.776 GHz, 1.3% below 1.800 |

Artifacts: `compare-edge-triage-edge-node00-20261005T170923Z.json`,
`power_edge-triage-phi35-n9-server-event-last-vary-20261005T164031Z.log`,
`trace_…164031Z.log`. The meter line is also in the Pi's
`/mnt/data/fleet-trilogy/pi_power_trial.log`.

## Reading it
- **A real stream costs 2.7× the published best case on the Pi, even with the
  cache-friendly prompt:** 416 vs 154 J per call, 82 vs 31.7 s. The generation part
  hardly changed (31.1 s against the best case's ~31 s). The difference is reading the
  prompt: 148 tokens at 2.9 tok/s is 50 s, more than the answer takes to write.
- **The published prompt would cost about twice this (an estimate, not measured).**
  With a different event per call it re-reads ~400 of its 514 tokens (measured on the
  M4 Max with the same llama-server settings as below: 400; in-process: 405). At the
  Pi's measured 2.9 tok/s that is ~137 s of reading plus ~31 s of writing: ~170 s per
  call, against 82 s with the event fields last.
- **Why the count is valid here.** This llama-server build keeps a host-RAM cache of
  earlier prompts (`--cache-ram`, default 8 GB) and several slots. On the M4 Max that
  restored each of the three *recurring* events whole for the published prompt (1 token
  read per call), so those runs needed `-np 1 --cache-ram 0` to behave like a stream.
  With event-last the three events share 71% of their tokens, the server kept one slot,
  and each call re-read 148 tokens: the same count as the M4 Max's single-slot,
  no-RAM-cache run (148). So the server defaults didn't change this result.
- **Per-call energy includes setup**, as in the published rows: one llama-server start
  and one cold first call (it reads all 514 tokens: roughly 160-180 s, from the total
  prompt time less 17 median calls, or 514 tokens at 2.9 tok/s), spread over 18 calls here
  against 60 in the published run. The median call (82 s) at the run's average
  4.3 W above idle is ~360 J, a steady-state figure for comparison.
- **The throttling didn't matter:** the clock averaged 1.3% below full speed.
- Resident memory of llama-server: 6.7 GB peak (RUSAGE_CHILDREN), from the same build's
  default settings as the published row.
