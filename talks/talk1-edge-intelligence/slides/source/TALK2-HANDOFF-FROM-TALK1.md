# Talk 2 handoff from Talk 1

Talk 1 ("Edge Intelligence for Connected Fleets: 1-Bit LLMs Inside Apache Pulsar
Functions") covers framing only: the fleet problem, the Before/After edge
architecture, how Pulsar Functions fit, the BitNet detour, and the cost story.
**All performance numbers (accuracy, latency, RAM, power) are deferred to Talk 2.**
Talk 1 Slide 6 is a teaser plate, "Does it actually work on a Pi? See Talk 2", with
no numbers on it.

## Deferred to Talk 2

### 1. The "Experimental Proof" slide
Proposed during the Talk 1 rework as a three-card KPI grid:
- **Hardware & cost efficiency:** Raspberry Pi 4 test platform (4-core Arm
  Cortex-A72; 8GB RAM per `docs/CANON.md`). Price not yet sourced.
- **Operational latency:** local inference time for critical telematics anomalies.
- **Diagnostic accuracy:** how much diagnostic reasoning survives quantization.

The example values in the drafting prompt ("42ms", "91.4%") were placeholders, not
data. Don't use them. The prompt's proposed footer ("evaluated on localized
synthetic CAN bus fault-injection streams") doesn't describe this repo: the
evaluation runs on `shared/fleet-simulator` telemetry. Reword it before using it.

### 2. Real Pi 4 numbers already in the repo
Sources: `docs/TALK2-MODEL-LEDGER.html`, `docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md`,
`docs/TALK2-GREENEST-TOKEN-REPORT.html`, `docs/TALK2-0.5B-CAPABILITY-CLIFF.md`,
`eval-results/`.
- Phi-3.5-mini-instruct on Pi 4: 0.0% severity mismatch, 35.7s p50 / 157.8s p95, RAM 93%.
- Gemma-3-4B-it on Pi 4: 2.2% mismatch, 77.1s p50 / 101.4s p95, RAM 96%.
- Llama-3.1-8B-Instruct on Pi 4: 0.0% mismatch (n=45), 74.7s p50 / 232.3s p95, RAM 91%.
- M4 to Pi 4, same stack: 38–200x latency slowdown, accuracy delta of 5.6pp or less.
  Hardware changes speed, not accuracy.
- Qwen2.5-0.5B / 1.5B: 70.7s / 111.5s median on Pi 4, and both rejected at gate 1
  (capability cliff; 76.7% format parse rate).

### 3. Tension to resolve with Talk 1
Talk 1 Slide 5 ("After") and its scorecard promise **"Sub-second Local Action"** /
**"Sub-second"** decision latency. Measured Pi 4 LLM latency is tens of seconds to
minutes. Talk 2 should reconcile the two, for example: cheap-math detection
(`is_probable_slowdown()`, co-processor gate) acts sub-second on the device, and LLM
triage follows in tens of seconds with no cloud round-trip.

### 4. Model naming
The Talk 1 slides say "1-bit / small quantized LLMs" to cover both the BitNet
aspiration and the Qwen2.5 / Q4_K_M pivot. Talk 2 should name the models it
actually measured.

### 5. Unsourced figures flagged in Talk 1 (visible NEEDS callouts)
Resolve these if Talk 2 reuses them:
- "sub-$100 commodity hardware"; "95% hardware deployment cost reduction vs AV platforms" (Slide 5)
- Tesla HW4 specs (TOPS, cores, RAM, power) (Slide 25)
- "+$10,000 retail price impact" (Slide 25)
- "$15 OBD-II dongle", "1.4 billion existing consumer cars", "<$100 retail" (Slide 26)
- "97%+ deployment cost drop, 100% of drivers" (Slide 26)
- "90% bandwidth savings" / "95% noise data" (Slides 4–5)
- NVIDIA DRIVE Thor specs and chip price estimates (Slide 25): cited to NVIDIA docs
  and MarketResearch.com (2025), still to be double-checked.
