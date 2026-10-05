# Talk 2: the Edge Triage Pipeline on a Raspberry Pi 4 with changing prompts (edge-node00, 2026-10-05)

What one triage call costs on the Pi 4, at the wall, when its prompt differs from the
previous call's. The published Pi row (Table II: 31.7 s, 154 J per call) repeated one
event, so llama-server answered from a prompt it already had cached. That is the real
cost while one truck's prompt repeats within an incident (the prompt carries the trip
context, not the sensor readings), but not when it changes: a new incident or context,
once-per-incident calling, or one device serving several trucks.

## Setup (all three windows)
- Raspberry Pi 4 Model B Rev 1.4, 4 cores, 8 GB, kernel 6.18.50, model on the USB data
  drive (`/mnt/data`). Fan on (re-aimed before run B).
- bartowski `Phi-3.5-mini-instruct-Q4_K_M.gguf`, sha256
  `e4165e3a71af97f1b4820da61079826d8752a2088e313af0c7d346796c38eff5` (the published
  row's file, identical to the M4 Max's copy). 4 threads.
- `--vary-events` (consecutive calls carry different operational contexts: the three
  escalation scenarios, round-robin), 18 calls (`--model-eval-runs 9
  --model-confirm-multiplier 1`): 9 format + 9 escalation, 3 per scenario.
- Window script: `pi_power_trial_realstream.sh` (this folder), the 2026-10-02 protocol:
  meter zeroed by hand, one photo at the end, a 30 s temperature/clock/throttle trace.
  Idle 3.403 W (mean of the 3.405 / 3.401 W baselines). Energy above idle =
  mWh × 3.6 − 3.403 W × meter seconds; idle time before and after the run cancels.
- Code: `SOURCE_COMMIT`. Run A ran from the working tree that became `8955af8`, before
  its `--model-server-args` option existed; runs B and C from `5f2ccdc` (code as
  `8955af8`).

| Window | Backend | Prompt | Script arguments after `edge-triage phi35 9` |
|---|---|---|---|
| **A** 16:40Z | llama-server (`/mnt/data/tools/llama.cpp`, `8212c78`, the published row's build), default settings | `event-last` | `--model-backend server --vary-events --triage-prompt event-last --model-confirm-multiplier 1` |
| **B** 17:41Z | llama-server, same build, one slot and no RAM prompt cache | published (`default`) | `--model-backend server --model-server-args "-np 1 --cache-ram 0" --vary-events --triage-prompt default --model-confirm-multiplier 1` |
| **C** 18:50Z | in-process (llama-cpp-python 0.3.36, CPU) | `event-last` | `--model-backend inprocess --vary-events --triage-prompt event-last --model-confirm-multiplier 1` |

## Results

| | A: server, event-last | B: server, published | C: in-process, event-last |
|---|---|---|---|
| Meter (one photo) | 3,883 mWh, 761 mAh, 31:46 | 7,559 mWh, 1,483 mAh, 1:05:11 | 3,932 mWh, 772 mAh, 31:28 |
| Energy above idle | 13,979 − 6,486 = 7,493 J | 27,212 − 13,309 = 13,903 J | 14,155 − 6,425 = 7,730 J |
| **J per call** | **416** | **772** | **429** |
| Average draw during the run | 7.73 W | 8.14 W | 7.85 W |
| **p50** / mean / p95 per call | **82.2** / 95.1 / 156 s | **160.3** / 162.4 / 170 s | **87.2** / 96.4 / 136 s |
| Prompt tokens read per call (median) | 148 of 514 | 400 of 514 | 148 of 514 |
| Prompt reading / generating (median) | 50.5 s / 31.1 s (42 tokens) | 128.6 s / 31.0 s (42) | 51.6 s / 31.4 s (41) |
| Format / escalation mismatch | 100% / 0 of 9 | 100% / 0 of 9 | 100% / **3 of 9** (benign → "lower") |
| Throttling (trace samples at the soft limit) | 19/58, peak 84.2 °C, clock −1.3% | 3/98, peak 82.3 °C, clock −0.1% | 0/58, peak 79.8 °C |
| Peak memory | 6.7 GB (llama-server) | — | 4.0 GB (whole test process) |

Artifacts: A `compare-edge-triage-edge-node00-20261005T170923Z.json`, B `…183033Z.json`,
C `…191904Z.json`, each with its `power_…` and `trace_…` logs. The meter lines are also
in the Pi's `/mnt/data/fleet-trilogy/pi_power_trial.log`. B's photo was taken ~16 min
after the run ended; that idle time cancels, and the cooling Pi idling slightly above
3.40 W would add at most ~50 J (<0.5%).

## Reading it
- **A changed prompt costs the Pi 4 about 5× a repeated one with the published prompt**
  (772 J, 160 s against 154 J, 31.7 s), because the event's fields come before the rules
  and it re-reads 400 tokens: 129 s of reading, four times as long as writing the answer.
  **With the fields after the rules, about half that** (416 J, 82 s; 2.7× a repeated
  call): 148 tokens, still 50 s of reading. Generation is the same ~31 s in every case.
- **The estimate made before run B** (~170 s, from run A's reading rate) was 6% high.
- **Why B needed `-np 1 --cache-ram 0`:** this llama-server build keeps a host-RAM cache
  of earlier prompts and several slots. On the M4 Max, with server defaults, it restored
  each of the three recurring events whole for the published prompt (1 token read).
  Event-last's events share 71% of their tokens, so the server kept one slot and run A
  read 148 per call, the same as the M4 Max's single-slot run.
- **In-process vs llama-server (C vs A): same cost, different decisions.** Speed and
  energy match within noise (87 vs 82 s p50, 96 vs 95 s mean; 429 vs 416 J), with
  less memory (4.0 vs 6.7 GB). But in-process answered "lower" on all 3 benign calls
  (expected "hold"). Checked at n=45 on the M4 Max CPU
  (`../edge-triage-backend-accuracy-m4max-20261005/`): the in-process backend leans to
  "lower" in borderline cases on both prompts; with the published prompt that stays
  within the answer key (0/45), with event-last it flips benign (15/45). The event-last
  prompt's accuracy holds on llama-server only.
- **Per-call energy includes setup,** as in the published rows: one model load and one
  cold first call, spread over 18 calls here against 60 there.
