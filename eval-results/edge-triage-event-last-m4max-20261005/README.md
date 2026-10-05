# Talk 2: the Edge Triage Pipeline on the M4 Max as a real stream, both prompt orders (2026-10-05)

What one triage call costs on the M4 Max GPU when every event is different, with the
published prompt and with the event fields moved after the rules. Everything else
matches the published M4 Max row (Table II: 0.36 s, ~15 J per call, from
`phone-proxies/m4max-macbook/20261004T005747Z-caffeinated`).

## Setup
- MacBook Pro, Apple M4 Max, on AC power, `caffeinate -dims`.
- llama.cpp `v0.5.0` (`7fe450e`), llama-server on the GPU (Metal), 12 threads; the same
  GGUF as the Pi: sha256 `e4165e3a…eff5`.
- `--model-eval-runs 15` (60 calls per rep: 15 format + 45 escalation), 3 reps per
  prompt, alternating prompts rep by rep; a gate before each session waits for 60 s of
  Nominal thermal pressure; idle windows before and after.
- Energy: `sudo powermetrics --samplers cpu_power,gpu_power,thermal -i 500` (chip only),
  above the run's own idle (`summarize.energy_j` over each session's window ÷ calls),
  the published convention.
- No context size set, like the published caffeinated row: llama-server reserves Phi's
  full 128k-token training context (~51 GB; test log incident 23). The `-ctx8192-check`
  found that negligible for Phi (same latency and J/call at 8× less memory), and the
  best case reproduces here (run 2 below). Later study runs set `LLAMA_ARG_CTX_SIZE=8192`;
  these deliberately match the published row instead.
- Scripts: `bench_realstream_m4max.sh` (runs) and `report_realstream.py` (table).
- Code: commit `8955af8`. The accuracy check and run 1 ran before its
  `--model-server-args` option existed; run 2 used it.

## Runs in this folder
1. `pytest_accuracy_event-last_repeated.log` + `compare-edge-triage-…163449Z.json`:
   **accuracy check** of the event-last prompt under the published conditions exactly
   (one event repeated, server defaults). 100% format (15), 0% mismatch (45),
   p50 0.357 s. llama-server read **1 of 514** prompt tokens per call: the whole prompt
   came from its cache, the direct evidence that the published per-call numbers are a
   best case.
2. `realstream-run1-cache-ram-on/`: `--vary-events`, server defaults. **Not a stream for
   the published prompt:** it read 1 of 514 tokens per call. This llama-server build
   keeps a host-RAM cache of earlier prompts (`--cache-ram`, default 8 GB) and several
   slots, and the three recurring events don't resemble each other there (114 shared
   tokens), so it restored each one whole from its earlier copy. Its numbers reproduce
   the best case instead (14.7-15.5 J, p50 0.37-0.39 s, against the published
   15.1-15.8 J). Event-last read 148 tokens per call here too (the slot already shared
   71% of each prompt, so the server kept it), and matches run 2.
3. **`realstream-run2-np1-no-cache-ram/`: the result.** Same as run 1 plus
   `--model-server-args "-np 1 --cache-ram 0"`: one slot, no RAM cache, so each call can
   reuse only the previous call's prompt prefix, as in a stream of events that never
   repeat (and as the in-process backend does).

## Results (run 2)

| Prompt | J/call above idle | p50 / mean s | Prompt tokens read / 514 | Prompt ms / gen ms (median) | Accuracy |
|---|---|---|---|---|---|
| Published (`default`) | **25.0** (25.1, 25.0, 25.0) | 0.70 / 0.73 | 400 | 332 / 360 | 100% / 0% |
| `event-last` | **18.5** (18.1, 18.9; Nominal reps) | 0.49 / 0.54 | 148 | 140 / 350 | 100% / 0% |

Idle 355 mW. Per rep, p50: default 0.69 / 0.71 / 0.69 s; event-last 0.49 / 0.85 / 0.50 s.

- **Event-last rep 2 ran hot:** Heavy thermal pressure for 79 of its 98 samples (the
  others: Nominal throughout). Its generation slowed to 16.7 ms/token (others: 8.3-8.6)
  and its energy fell to 15.5 J: slower and cheaper, as the throttled runs in the test
  log were. The table uses the two Nominal reps; all three average 17.5 J.
- **A real stream costs ~65% more than the best case on this GPU** with the published
  prompt (25.0 vs ~15 J; 0.70 vs 0.36 s), and **~22% more with event-last** (18.5 J,
  0.49 s). Moving the event fields last saves 26% of the energy and 29% of the latency.
- **Generation still dominates on the GPU:** answers are the same length (42 tokens)
  with either prompt; the published prompt's extra cost is 252 more prompt tokens at
  ~0.75 ms each. On the Pi 4's CPU the same 148 prompt tokens take 50 s, more than the
  answer (`../edge-triage-event-last-pi4-20261005/`).
