# Talk 2 / Talk 1: does the in-process backend decide differently from llama-server? (M4 Max CPU, 2026-10-05)

Found on the Pi 4 the same day (`../edge-triage-event-last-pi4-20261005/`, run C):
`LlmTriageFunction` in-process (llama-cpp-python) with the event-last prompt answered
"lower" on all 3 benign calls, where the harness expects "hold"; llama-server on the
same prompt and device answered "hold". This checks it at a larger n, both prompt
orders, on one machine.

## Setup
- M4 Max, **CPU only for both backends:** llama-server (llama.cpp `v0.5.0`, `7fe450e`)
  with `-np 1 --cache-ram 0 -dev none -ngl 0`; in-process llama-cpp-python 0.3.36 with
  `gpu_layers=0` (its own vendored llama.cpp). 12 threads, temperature 0.2, the same
  sampling settings (llama-cpp-python's defaults match llama-server's: top-k 40, top-p
  0.95, min-p 0.05, no repeat penalty).
- Phi-3.5-mini Q4_K_M (sha256 `e4165e3a…eff5`), `--vary-events`, `--model-eval-runs 15`:
  15 format + 45 escalation calls per session, 15 per scenario.
- Script: `run_backend_accuracy.sh`. Code: commit `8955af8`.

## Results

| Prompt | Backend | Mismatch | escalate-worthy (raise) | benign (hold) | de-escalate-worthy (lower or hold) | p50 |
|---|---|---|---|---|---|---|
| published (`default`) | llama-server | 0/45 | raise 15 | hold 15 | hold 15 | 2.13 s |
| published (`default`) | in-process | 0/45 | raise 15 | hold 15 | **lower 15** | 2.59 s |
| `event-last` | llama-server | 0/45 | raise 15 | hold 15 | hold 11, lower 4 | 1.29 s |
| `event-last` | in-process | **15/45** | raise 15 | **lower 15** | lower 15 | 1.55 s |

Format 100% in all four. Prompt tokens read per call: 400 (published), 148 (event-last),
the same for both backends.

## Reading it
- **The in-process backend leans to "lower" in the two borderline cases, every time.**
  Same model file, prompt and sampling settings; the difference is the llama.cpp build
  and sampler code inside llama-cpp-python. At temperature 0.2 both backends are nearly
  deterministic, so a small numerical difference flips a near-tie the same way on every
  call. The Pi 4 shows the same shift (3/3), so it follows the runtime, not the hardware.
- **The published prompt is safe on both backends** (0/45): in-process moves the
  de-escalate-worthy case from hold to lower, which that scenario accepts. That is the
  Edge Triage demo's configuration (in-process default since `8955af8`, published prompt).
- **The event-last prompt is safe on llama-server only.** In-process, it tips the benign
  case (clear, dry freight, on schedule) to lower. The prompt's own rule for lower ("none
  of the fields are risk multipliers, and at least one positively indicates safe,
  controlled conditions") arguably admits that reading, but the harness's answer key
  says hold, and the published order keeps it.
- **So a prompt change and a runtime change each need their own accuracy check,** like a
  quantization change: "accuracy doesn't depend on the hardware" held within one runtime,
  not across two.
- In-process was ~20% slower than llama-server on this CPU (2.59 vs 2.13 s; 1.55 vs
  1.29 s), and 6% slower on the Pi 4 (87 vs 82 s).
