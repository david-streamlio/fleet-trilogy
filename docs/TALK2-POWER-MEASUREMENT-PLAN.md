# Talk 2 power/energy measurement plan: real Pi 4 draw for the two winners

**Status: done (2026-10-02).** Results: `docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md`
row 24 and its "Pi 4 power measurement" section — idle 3.40 W; Phi-3.5-mini on the
Edge Triage Pipeline ≈154 J/call above idle; Gemma-3-4B-it on Tier 2 ≈208 J/call;
Mac M4 contrast ≈15 / ≈23 J/call (chip only). The plan below is kept as written,
with corrections from the real run marked **(as run)**.

## Why

`talks/talk2-greenest-token/src/talk2_greenest_token/efficiency.py`'s module
docstring says it plainly: "no real Pi 4 power draw has ever been measured."
`SMALL_MODEL_CPU.power_watts` is exactly as illustrative today as it was
before the Pi 4 decision-grade runs replaced its `latency_s` guess (which
turned out to be off by ~124x). This plan closes that gap with a real
measurement, on the same target hardware already used everywhere else in
this repo (`edge-node00`).

## Scope boundary

- **Exactly 2 models, each on its own winning task only — not a 2x2 grid.**
  Per `docs/TALK2-OUTLINE.md`'s "Final model recommendation" section:
  - **Phi-3.5-mini-instruct** on the Edge Triage Pipeline (escalation-direction decision).
  - **Gemma-3-4B-it** on Tier 2 (corridor paraphrase / spoken warning).
- What gets computed is **marginal energy per call and per token (joules)**,
  not raw instantaneous watts. Power alone doesn't answer "greenest" —
  energy does, especially given row 15's finding that the Pi is 38-200x
  slower than the M4 for the same stack. A model that draws less power but
  takes proportionally longer isn't necessarily the greener one.
- Optional secondary: an M4 `powermetrics` contrast for the same 2
  models/tasks, reusing the exact mechanism `docs/TALK2-GPU-BENCHMARK-PLAN.md`
  already specifies — explicitly framed as "different classes of machine,"
  not a fair benchmark. That plan's own non-goal applies here too.
- Does **not** require touching `tests/model/test_compare_models.py`'s
  multi-model harness. Reuse the existing single-model eval paths
  (`tests/model/eval_lib.py` for the Edge Triage Pipeline, `tests/model/tier2_eval_lib.py` for
  Tier 2) to generate real load while the meter samples — this is a
  measurement pass layered on top of runs that already exist, not a new
  comparison harness.

## 0. Device: confirmed

- First device (a KEWEISI dual-port inline meter): ruled out, two
  disqualifying problems — no logging/accumulator/mode button (pure
  instantaneous display), and it was seated in one of the Pi 4's 4 USB-A
  peripheral ports (back edge, next to Ethernet) instead of the USB-C
  power-input port, confirmed by the readings themselves (0.00A / 5.28V,
  an unloaded downstream rail).
- **Confirmed replacement: YEREADW KWS-2303C USB-C tester** ($13.79,
  Amazon ASIN B0DFBSFL38). Native USB-C, one male plug end + one female
  receptacle end — no adapter needed, sits directly inline between the
  Pi's official power-supply cable and the Pi's USB-C power-in port.
  - Range: 4-30V, 0-12A — comfortably covers the Pi 4 (~5V, ≤3A).
    Accuracy ±(1%+5): fine for a directional talk number, not a lab
    instrument.
  - Main screen shows **voltage, current, and power simultaneously**,
    plus, in smaller readouts on the same screen: accumulated **mAh**,
    accumulated **mWh** (energy — the number this protocol actually
    wants), and an elapsed-**time** counter, all live-updating together.
    A "double-click to rotate" button cycles to other screens (max-V/
    max-A/max-W, D+/D- line voltage, the meter's own CPU temp) if needed,
    but the default screen already has everything this protocol uses.
  - No Bluetooth/app/PC logging — this is a read-the-display device, not
    a data-logger. That's fine: the built-in `mWh` + elapsed-time
    accumulator does the power-integration work in hardware, so
    continuous logging isn't needed — just a reading before and after
    each measurement window (see step 3).
  - **(as run)** Confirmed from the manual (KOWSI-branded, same KWS-2303C):
    a 3-second button hold zeroes mAh, mWh and the timer (not the MAX
    readings). mWh is a whole-number counter (1 mWh resolution), the timer
    whole seconds. It uses a TI INA226 and measures current in both
    directions, with a direction arrow. Every window was reset at its start,
    then read once at the end from a single phone photo — both values from
    the same instant.
  - Reading caution: the "CPU" field on the meter's rotated screens is the
    **meter's own onboard chip temperature**, not the Pi's — don't
    conflate it with `vcgencmd measure_temp`'s reading of the Pi itself.
- **Where it goes:** inline between the wall power supply and the Pi's
  **USB-C power-in port** — the single USB-C port next to the two
  micro-HDMI ports — not any of the 4 USB-A peripheral ports on the
  Ethernet edge.
- **(as run)** The manual's orientation is **male end toward the power
  source, female end toward the device**. The first wiring read 4.63 V /
  0.00 A while the Pi ran — the meter wasn't carrying the Pi's power;
  re-wiring so the supply feeds the meter and the meter feeds the Pi gave
  5.218 V / 0.650 A / 3.392 W at idle. Every re-wire cuts the Pi's power: it
  reboots, and on Wi-Fi it took ~25 minutes to rejoin once — wire once,
  then leave it.

## 1. Coherence check before anything else

Same discipline as `docs/PI4-RUNBOOK.md` step 1: don't trust a number
before sanity-checking the setup itself.

- With the Pi idling, confirm the meter reads something in the ballpark of
  5.0-5.2V and 0.4-1.3A (2-6.5W) on the port that now carries the real
  load. If it reads 0.00A, it's in the wrong port again — stop and recheck
  placement before running anything.

## 2. Idle baseline

- Let the Pi settle with no inference active.
- Confirm thermal state first: `vcgencmd measure_temp` and `vcgencmd
  get_throttled`. This Pi has a documented throttling history (row 10 of
  `docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md` — 83.7°C, ARM clock cut to
  600MHz, fixed with a fan). A throttled idle state understates real power.
- Read the meter's `mWh` and elapsed-`time` values, wait ≥2 minutes, then
  read them again. **(as run)** 10 minutes, before each model: at 1 mWh /
  1 s resolution a 3-minute window is only good to ~±1%, a 10-minute one to
  ~±0.2%. The two baselines came out at 3.405 W and 3.401 W.
  `P_idle_W = ((mWh_end - mWh_start) * 3.6) / (time_end - time_start)`.
- Result: `P_idle_W`.

## 3. Per-model batch run

For each of the two models, on its own task only:

- **Phi-3.5-mini-instruct**: Edge Triage Pipeline escalation batch.
  **(as run)** `--model-eval-runs 15` (60 calls: 15 format + 45 escalation) —
  what the published row 11 run actually used, not n=30.
- **Gemma-3-4B-it**: Tier 2 spoken-warning batch, n=30 across the 3
  scenarios (comparable to row 22).
- Read and note the meter's `mWh` and elapsed-`time` values the instant
  before starting the batch. Start the batch.
- Read the same two values the instant the batch finishes. One reading
  before, one after, for the whole batch — not per-call; a single call is
  too short/noisy to read reliably off a live display, same reasoning
  `docs/TALK2-GPU-BENCHMARK-PLAN.md` gives for `powermetrics` batch
  sampling.
- Record: `batch_energy_mWh = mWh_end - mWh_start`,
  `batch_duration_s = time_end - time_start` (cross-check this against
  the harness's own reported wall-clock duration for the batch — they
  should be close; a large mismatch means a reading was fumbled, not that
  the run behaved differently).

## 4. Compute the real numbers

- `batch_energy_J = batch_energy_mWh * 3.6` (1 mWh = 3.6 J).
- `idle_energy_for_duration_J = P_idle_W * batch_duration_s` (from step
  2's idle baseline).
- `marginal_energy_J = batch_energy_J - idle_energy_for_duration_J`.
- `energy_per_call_J = marginal_energy_J / 30`. **(as run)** Divide by the run's
  actual call count — the artifact's `latency.n` (60 for Phi's Edge Triage run,
  30 for Gemma's Tier 2 run), since an Edge Triage eval run makes ~4 calls.
- `energy_per_token_J = energy_per_call_J / mean_output_tokens` — reuse
  each model's already-known output length from row 23 (Phi
  ~19 words on the Edge Triage Pipeline, Gemma ~33 words on Tier 2; convert word count to
  tokens at ~1.3-1.4 tok/word, or pull an exact count from the harness's
  completion length if available).

## 5. Optional: M4 contrast

- Same 2 models, same 2 tasks, `sudo powermetrics --samplers
  gpu_power,cpu_power -i 1000 -n <N>` per `docs/TALK2-GPU-BENCHMARK-PLAN.md`
  step 3, same idle-subtraction method as above.
- Present as energy-per-call / energy-per-token, explicitly labeled
  "different classes of machine, not a fair benchmark" — the established
  framing already used for the Pi/M4 latency contrast, not a new hedge.

## 6. What to bring back

- Real `P_idle_W` and per-model `energy_per_call_J` / `energy_per_token_J`
  numbers for the Pi (and optionally the M4).
- These feed `efficiency.py`'s `SMALL_MODEL_CPU.power_watts`. Open design
  question for whoever writes the real number in: that dataclass has one
  profile per approach, not one per task, but row 23 already found the
  greenest model is a property of task as well as model — decide whether
  to anchor the constant on one task's number (with a comment saying
  which) or represent both, rather than quietly collapsing them.
- Nothing in this repo auto-picks a number here either — write the real
  measurement into `docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md` as a new
  row once it exists, same as every other real Pi result in that log.
