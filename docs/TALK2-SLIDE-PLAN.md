# Talk 2 — "The Greenest Token" — Slide Plan

No deck built yet — this is the plan the deck gets built from. Reconciles
`docs/TALK2-OUTLINE.md` (the narrative outline, unchanged in its own
structure) with a pasted 10-slide "Green Edge" sustainability draft, per the
reconciliation session on 2026-09-30. Every fact below cites the repo doc
that backs it, same discipline as `docs/TALK1-SLIDE-PLAN.md`.

40-minute slot. Narrative slide count after the 2026-09-30 trim pass: **24**
(slides 3–26) — matches `TALK1-SLIDE-PLAN.md`'s own 24-slide narrative pace
(also slides 3–26, same 40-minute slot) exactly. Four merges got it there;
see "Open items" for the list.

## Structure
0. **Act 0 — The Green Edge** (new, slides 3–6): the sustainability framing
   and recap bridge from Talk 1 — why decarbonizing vehicle AI means pushing
   compute onto commodity CPUs, not adding GPUs.
1. **Act 1 — The Dream** (7–8): BitNet makes real LLM reasoning inside a
   Pulsar Function look newly possible. Unchanged from the outline.
2. **Act 2 — Two Walls** (9–13): BitNet's garbage output on ARM, the real
   engineering cost of getting mainline llama.cpp onto the Pi 4, and the 0.5B
   capability cliff.
3. **Act 3 — The Methodology Funnel** (14–22): the layered eval funnel, gate
   1 through gate 2, ending in the real Pi 4 decision-grade results and the
   two-winners finding. Unchanged from the outline.
4. **Act 3.5 — The Green Payoff** (23, new): what "greenest" actually costs
   and buys, in the real numbers Act 3 just produced — not fabricated
   watts/accuracy figures.
5. **Act 4 — Why This Generalizes** (24–26): the reusable funnel, the
   thesis line paid off, the close. Unchanged from the outline.

## How the pasted "Green Edge" draft was reconciled

The pasted content was a 10-slide sustainability-framed draft with its own
dark eco-tech visual spec and an "under 2 minutes per slide" pacing note.
Visual design isn't this draft's call: per your instruction, this deck uses
Talk 1's actual, already-built design system — DRUIDS tokens plus the
`DATADOG_MARKETING_DECK` native slide types (see
`talks/talk1-edge-intelligence/slides/`) — not the pasted draft's dark
eco-tech theme. The pacing intent (keep each slide light, ~2 min or under)
is retained as a content-density goal, not a visual spec.
Four conflicts were raised and resolved before drafting, plus two more found
during fact-checking against the repo:

1. **Target file & ground truth.** Reconcile against `TALK2-OUTLINE.md`,
   create this file. *(User decision.)*
2. **Slides 6–10's model story.** The pasted draft assumed a single working
   "1-bit optimized LLM" with placeholder numbers. Repo reality
   (`docs/BITNET-POSTMORTEM.md`): the 1-bit attempt produced garbage output
   and was abandoned — it's Act 2's cautionary wall, not a shipped result.
   Reframed slides 6–10 around the real winners: Phi-3.5-mini-instruct (Flow
   B) and Gemma-3-4B-it (Tier 2), both Q4_K_M, both with real Pi 4 numbers.
   *(User decision.)*
3. **Where the sustainability material lives.** Slotted in alongside Act 3's
   existing methodology funnel, not instead of it — Act 3 is untouched; the
   green framing wraps around it (Act 0 before, Act 3.5 after). *(User
   decision.)*
4. **Unsupported claims.** Dropped or rewritten rather than flagged and
   kept: Slide 9's CPU core-pinning/isolation-core/chip-degradation content
   (zero basis in `docs/BITNET-POSTMORTEM.md` or `docs/PI4-RUNBOOK.md` — not
   mentioned anywhere in either), Slide 10's "10x performance surplus"
   (no smartphone NPU measurement exists anywhere in this repo), and Slide
   5's "guarantees flawless... deployment on standard driver cell phones"
   (contradicts this project's own repeated "different classes of machine,
   not a fair benchmark" caveat). *(User decision.)*
5. **Slides 7–8's headline metrics aren't real.** `docs/TALK2-POWER-MEASUREMENT-PLAN.md`
   and `docs/TALK2-GPU-BENCHMARK-PLAN.md` are both explicitly "not started"
   — no power meter ordered, no GPU comparison run. There is no "4.2W Avg
   Draw" and no "94.2%/89.7% accuracy retention" anywhere in this project.
   Reframed both slides entirely around what IS measured on the real Pi 4:
   latency (p50/p95), tokens/sec, RAM, and escalation-mismatch/grounding
   rates. *(Applying decision 4 above to these two specific slides — not
   separately confirmed with you; flag if you want different treatment.)*
6. **Slides 2–5 duplicate Talk 1.** Talk 1's own Slides 4–10 already cover
   the cloud-bottleneck framing, the luxury-AV cost barrier, the BYOD/
   smartphone dream, and the compute spectrum (with a sourced Pi 4 price and
   spec) — and Talk 1's Slide 8 speaker notes hand off explicitly: "That
   answer... is the subject of Talk 2, The Greenest Token." Kept as a
   standalone recap rather than condensed, so Talk 2 still stands on its own
   if it's ever given without Talk 1 immediately before it — but every
   figure is re-sourced against the real repo docs below rather than
   re-typed from the pasted draft, and the framing is upgraded from Talk 1's
   generic "cost and latency" pitch to this talk's specific carbon/grid-load
   angle, which Talk 1 never makes. *(Editorial call, not something you
   separately confirmed — flag if you'd rather condense or cut this recap.)*

**Facts corrected during reconciliation, not previously confirmed:**
- Pi 4 price: **$55** for the 2GB unit (PiShop.us) — already sourced in
  `docs/TALK1-SLIDE-PLAN.md` slides 5 and 10's footnotes. Reused verbatim,
  not re-guessed.
- Pi 4 stock clock: **1.5GHz** — sourced in
  `docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md`'s thermal-throttling section
  ("against the Pi 4's stock 1.5GHz — a 60% clock reduction"), not the
  pasted draft's unsourced guess.
- Pi 4 CPU: 4-core ARM Cortex-A72, Broadcom BCM2711 — Cortex-A72/4-core/8GB
  RAM confirmed repo-wide (`docs/CANON.md`, `docs/PI4-RUNBOOK.md`,
  `docs/TALK1-SLIDE-PLAN.md`); "BCM2711" itself is the real, public Pi 4
  SoC part number but isn't named in any repo doc — footnoted as an external
  fact (Raspberry Pi Foundation spec sheet), same convention Talk 1 uses for
  Thor/HW4/A18 Pro figures.

---

### Slide 1 — Welcome! We'll begin shortly.
**Label:** Waitroom

**On-screen text:**
```
The Greenest Token
Grab a coffee and settle in.
```

**Speaker notes:** Untimed lobby slide, same convention as Talk 1.

### Slide 2 — The Greenest Token: An Evaluation & Deployment Methodology for Edge Execution Engines
**Label:** Title

**On-screen text:**
```
David Kjerrumgaard
Apache Pulsar Committer
```

**Speaker notes:** Untimed title slide. Cold open immediately after: "I
thought I was building a next-gen edge AI Pulsar function. I ended up
building something way more important: an evaluation framework." Say it
once, don't explain it — Act 2 earns it.

## Act 0 — The Green Edge

### Slide 3 — The Green Edge
**Label:** Section: The Green Edge

**On-screen text:**
```
The Green Edge
Decarbonizing Vehicle AI via the Ubiquitous CPU
```

**Design note:** this deck uses Talk 1's real, already-built design system —
not the pasted draft's dark eco-tech theme. That means DRUIDS tokens (Noto
Sans, 4px/8px radii, `--ui-status-*` color tokens) plus the
`DATADOG_MARKETING_DECK` native slide types, matching
`talks/talk1-edge-intelligence/slides/source/Talk 1 Edge Intelligence.dc.html`:
white content-slide backgrounds with Lucide icon-badge status coding
(danger/warning/success), and the purple-to-blue faceted gradient reserved
for Title/Section/Closing/Waitroom plate slides only — this is a
section-divider slide, so it gets that gradient treatment. Visual: a
minimalist data pipeline splitting from one trunk into handheld-device
icons, rendered in that palette, not emerald/teal/amber.

**Speaker notes:** Talk 1 ended on a cliffhanger: does any of this actually
run on a Pi-class device, with real numbers? That's this talk. But there's a
second thesis riding along with the accuracy one: every one of those real
numbers is also a sustainability number. Decarbonizing vehicle AI doesn't
mean building greener data centers — it means not needing the data center
call at all.

### Slide 4 — Centralized AI's Carbon Bottleneck, and Where the Pi 4 Sits
**Label:** The Cost of the Cloud — and the Way Out

**On-screen text:**
```
Skyrocketing Grid Load
Cloud GPU clusters are straining energy grids and data-center cooling
infrastructure.
Structural Waste
Streaming raw fleet telemetry to the cloud means continuous, high-wattage
stream processing of mostly-normal readings — up to 95% noise data,
by Talk 1's own [NEEDS: source] estimate.
Data Center Clusters → Luxury AV Cores → Smartphone NPUs → Commodity
Embedded CPUs (Raspberry Pi 4)
[bracket over Smartphone/Pi 4] "The Democratization Target Zone"
Goal: push intelligence out of the luxury GPU bracket into everyday
consumer silicon.
```

**Speaker notes:** This is Talk 1's cloud-bottleneck slide, recast through a
carbon lens instead of a cost/latency one. Same "up to 95% noise" figure
Talk 1 used — same caveat applies, it's still not independently sourced,
carried forward with the same "up to" softening rather than restated as a
harder fact than Talk 1 itself claimed. Then the spectrum recap Talk 1
closed Act 1 on (its Slide 10): cloud clusters, 500+ TOPS luxury AV silicon,
35-80 TOPS smartphone NPUs, and the Pi 4 at zero dedicated AI TOPS. If you
were in the room for Talk 1, take this whole slide in one breath — the only
thing that's new is the lens: every step left on this spectrum toward the
Pi 4 is also a step away from grid load.

### Slide 5 — The Sustainability Blueprint
**Label:** Embodied Compute, Not New Compute

**On-screen text:**
```
Zero Manufacturing Footprint
Leverage processors consumers already own — no new silicon to fab, ship,
or discard.
Decentralized Ingestion
Vehicle-grade CPUs flatten the load a central server grid would otherwise
carry.
The Handheld Target
Optimize the software footprint until a smartphone becomes a vehicle
safety engine.
```

**Speaker notes:** Three-column scorecard. The sustainability argument for
edge inference isn't "use a more efficient data center" — it's "don't build
the data center's share of this workload at all." The greenest token is the
one that runs on hardware that already exists.

### Slide 6 — The Extreme Constraint Proxy, and What We Actually Tested
**Label:** Why Test the Worst Case

**On-screen text:**
```
The Baseline: Raspberry Pi 4
$55 (2GB unit, PiShop.us) · 4-core ARM Cortex-A72, Broadcom BCM2711[^bcm]
· 8GB RAM (test unit) · 1.5GHz stock clock · 0 dedicated AI TOPS
Forces bypass of any NPU/GPU pipeline entirely — pure CPU inference or
nothing.
The Smartphone Comparison
Modern mobile NPUs: 35–80 TOPS (Talk 1, Slide 10). We treat the Pi 4 as the
deliberately worst-case proxy — an expectation, not a measurement we've
made.
Not tested: cloud-class FP16 baseline — no GPU comparison host has been
available yet. See TALK2-GPU-BENCHMARK-PLAN.md. [NEEDS: measurement]
Tested for real: 14 Q4_K_M-quantized instruct models, 350M to 9B
parameters, benchmarked on identical diagnostic telemetry prompts.
The wall we hit and left behind: a 1-bit (BitNet) model — real, but
abandoned. Not part of this spectrum. That story is next.
```
`[^bcm]: Raspberry Pi Foundation spec sheet — not independently cited elsewhere in this repo.`

**Speaker notes:** This replaces the pasted draft's "a Pi 4 success
guarantees flawless deployment on cell phones" line, which overclaims —
this project's own convention (see the M4-vs-Pi4 latency numbers in Act 3)
is that different hardware classes are not a fair like-for-like benchmark.
The honest version is weaker but true: worst-case-proxy reasoning, not a
guarantee. Then the honest bridge into Act 1/2: the pasted draft's original
"Workload Matrix" listed FP16 vs. 4-bit vs. 1-bit as three parallel tested
tiers — that's not what happened. FP16 was never run (no GPU host); 1-bit
was tried and failed, not shipped. What's real is a 14-model Q4_K_M
spectrum, which is exactly Act 3's `models.toml`. Don't re-derive Act 3
here — this slide is the appetizer, not the meal.

## Act 1 — The Dream

### Slide 7 — Act 1
**Label:** Section: The Dream

**On-screen text:**
```
The Dream: A Natural Next Step
```

**Speaker notes:** Section divider.

### Slide 8 — 1-Bit LLMs Make This Look Newly Possible
**Label:** A How-To Talk, At First

**On-screen text:**
```
Prior work: hosting ML models inside Pulsar Functions in
resource-constrained environments.
The hook: BitNet's 1-bit LLMs make "real LLM reasoning at the edge, inside
a serverless function" look newly possible.
```

**Speaker notes:** Unchanged from `TALK2-OUTLINE.md` Act 1. Backing:
`talks/talk1-edge-intelligence/` — `function.py`'s `process(self, input,
context)` wrapper around the cheap-math-gate + LLM-enrichment pipeline.
Frame this as "let's just make it work" — a how-to talk, at first.

## Act 2 — Two Walls

### Slide 9 — Act 2
**Label:** Section: Two Walls, Same Shape

**On-screen text:**
```
Two Walls, Same Shape
```

**Speaker notes:** Section divider.

### Slide 10 — Wall 1: BitNet's Garbage Output on ARM
**Label:** The 1-Bit Attempt

**On-screen text:**
```
Built microsoft/BitNet (bitnet.cpp) from source for Apple Silicon. Fixed
two real upstream bugs to get it compiling.
It loads. It runs at ~5 tok/s. Every generation degenerates into
"@@@@@@@@..." — regardless of prompt, seed, or temperature.
Checked: not an AVX2 path issue, not a sampling artifact.
Checked: can mainline llama.cpp rescue the weights? No — a tensor type-ID
collision, and zero BitNet architecture support in mainline at all.
The call: a go/no-go signal on the timeline, not a bug to chase inside
unowned, lightly-exercised SIMD kernels.
```

**Speaker notes:** Unchanged from the outline's Wall 1. Backing:
`docs/BITNET-POSTMORTEM.md`. Never re-tested on the actual Pi 4 — the M4
failure was deemed sufficient, since the Pi 4 is older/weaker ARM, "the
worst case... not a better one." Pivot: mainline llama.cpp + small
quantized instruct models.

### Slide 11 — The Real Engineering Cost: Getting Mainline onto the Pi 4
**Label:** Cross-Compiling for the Bare-Metal Edge

**On-screen text:**
```
The Build
apt install build-essential cmake git
cmake -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build
--config Release -j$(nproc)  — CPU-only, no GPU flags, on ARM.
The Coherence Check
Before trusting any eval number: llama-completion -m <model> -p "The
capital of France is" -n 16 -no-cnv — must NOT produce "@@@@"-style
garbage. The exact failure mode that killed BitNet. A real gate this
project learned the hard way.
Wiring It In
Pull GGUF weights via huggingface_hub. Point models.toml at SSD-mounted
paths via env vars (SD card is too slow for GGUF load + swap). Run
make compare-models.
The Green Takeaway: Cooling Is Part of the Energy Budget
Sustained inference pushed the stock Pi 4 to 83.7°C and cut its clock from
1.5GHz to 600MHz — a 60% reduction, live, mid-benchmark. A ~$10 fan,
added while a run was still in progress, brought it to 76.4°C and a full
1.8GHz boost clock. Same workload, no pause.
```

**Speaker notes:** This replaces the pasted draft's fabricated "core
pinning / isolation cores / chip lifespan extension" content — neither
`docs/BITNET-POSTMORTEM.md` nor `docs/PI4-RUNBOOK.md` mentions any of that.
What's real and better: the build steps and coherence check from
`docs/PI4-RUNBOOK.md`, and the actual thermal-throttling incident from
`docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md` — `vcgencmd measure_temp` /
`get_throttled` / `measure_clock arm`, confirmed live, not inferred. This
also reframes something the project believed going in: `models.toml`
flagged thermal issues only for the largest model tested (Qwen3.8-27B) —
this reading suggests the stock Pi 4 may throttle under *any* sustained
inference load on stock cooling, which is a sharper, cheaper "green"
engineering beat than anything in the original draft: a fan is a more
honest sustainability lever than a software claim with no backing.

### Slide 12 — Wall 2: The 0.5B Capability Cliff
**Label:** Not a Slope

**On-screen text:**
```
Naive expectation: smaller model, same task, just slower accuracy dropoff.
             1.5B      0.5B
format_parse_rate   0.733    0.033
grounding_violation 0.000    0.200
tokens/sec          1.71     4.04
1.5B's failures: near-miss formatting — fixable parser gaps.
0.5B's failures: degenerate repetition — an instruction-following
collapse. No parser fix recovers an answer that was never generated.
```

**Speaker notes:** Unchanged from the outline. Backing:
`docs/TALK2-0.5B-CAPABILITY-CLIFF.md`. It's a cliff, not a slope — don't
smooth this into "small models are always fine."

### Slide 13 — The Turn
**Label:** From Trying to Measuring

**On-screen text:**
```
Two independent failures, same lesson: "does it work" isn't a yes/no
question you answer once by trying a model on your laptop.
```

**Speaker notes:** Callback the cold open, half-loaded: "I set out to ship
a function. What I actually needed first was a way to know if any model
deserved to be inside it." Unchanged from the outline.

## Act 3 — Building the Methodology

### Slide 14 — Act 3
**Label:** Section: The Methodology Funnel

**On-screen text:**
```
Building the Methodology
```

**Speaker notes:** Section divider. Present as a layered funnel — cheap
checks first, each layer only evaluating what survived the last.

### Slide 15 — Layer 0: Can It Even Run Here?
**Label:** Before You Spend a Single Eval Cycle

**On-screen text:**
```
Five checks, zero inference calls:
Does your runtime support the architecture at all? (BitNet: no fallback
in mainline.)
Does a real, trustworthy quantized artifact actually exist? (Check the
file, not the model card's claim.)
Does the static footprint fit the device, with margin? (0.34GB–15.33GB
across this manifest — most never a Pi 4 candidate on size alone.)
Can it survive sustained load on the real target? (Qwen3.8-27B:
disqualified for confirmed Pi 4 thermal issues at its weight class.)
Does it integrate with how you're actually invoking it? (-no-cnv,
grammar support against the real runtime's parser, not the spec.)
```

**Speaker notes:** Unchanged from the outline. Backing: `models.toml`,
`docs/TALK2-MODEL-SPECTRUM-ACCURACY-PLAN.md`. The cheapest, highest-
leverage filter in the whole funnel.

### Slide 16 — Layers 1–2: Setup, Format Reliability & Grounding
**Label:** Does It Parse? Does It Lie?

**On-screen text:**
```
Define the spectrum, not one model: quantization level, parameter count,
family, and the 350M–0.6B extreme-low end as an explicit boundary probe.
Derive ground truth from the task: the fleet simulator's own known
incident-ramp constants — not hand-labeling, not a generic leaderboard.
Layer 1 — Format reliability: does it produce parseable structured
output at all? (Catches 0.5B outright.)
Layer 2 — Grounding: does it invent values, or faithfully copy
truck_id/corridor/eta_impact from the input? (Catches confident
hallucination that would otherwise parse fine.)
```

**Speaker notes:** Unchanged from the outline, combined into one setup-plus-
check slide: how the spectrum and ground truth get defined, then the first
two layers that run against them.

### Slide 17 — Layer 3–4: Directional Accuracy & Severity Calibration
**Label:** The Real Judgment Test

**On-screen text:**
```
Layer 3 — Directional accuracy: sanity-check against simulator ground
truth (informational, not gating, once understood — it tested the
cheap-math pipeline's flag decision more than the LLM's own output).
Layer 4 — Severity calibration: does the model's call match the tier
implied by eta_slip_min, on a documented threshold scheme? A model can
pass every check above and still call a low-tier input "high" — confident
and wrong in the way that matters most for dispatch.
```

**Speaker notes:** Unchanged from the outline.

### Slide 18 — The Architectural Pivot
**Label:** Severity Stops Being an LLM Output

**On-screen text:**
```
Every severity-classification attempt hit the same ceiling: 10+ rounds,
33-73% mismatch, degenerate constant-output collapses.
The fix: a hand-verified g-force/ABS/volatility matrix
(severity_classifier.py) computes severity perfectly, instantly, for
free. The LLM's job narrows to what's left: escalate, de-escalate, or
confirm, given unstructured operational context.
```

**Speaker notes:** Backing: `docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md`
section 5. This is the talk's sharpest methodology beat: the deterministic
fix is free, reliable, and permanent — the eval framework is what found
the ceiling and pointed at the fix, not a bigger model.

### Slide 19 — Layer 5: Resource Footprint, on the Real Target
**Label:** Latency, RAM, Tokens/Sec — Not the Dev Machine

**On-screen text:**
```
M4 gate result (14 candidates): a real, five-model clean tier at
<=6.7% escalation mismatch — Qwen3-8B & Phi-3.5-mini-instruct &
Gemma-3-4B-it (0.0%), Llama-3.1-8B-Instruct (5.6%), GLM-4-9B-0414 (6.7%).
11 of 14 clear the 50% bar; only the three smallest (<=0.6B) fail it.
Format reliability solved everywhere: 13 of 14 at exactly 1.000.
```

**Speaker notes:** Backing: `docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md`,
"Full M4 gate result: all 14 candidates." The richest candidate pool
anywhere in this project — the actual pick depends on which of these five
fit the Pi 4's real constraints, decided next.

### Slide 20 — Real Pi 4 Numbers: The Full Clean Tier
**Label:** Every M4 Survivor Gets a Real Number

**On-screen text:**
```
Model                     Mismatch  Pi p50   Pi p95    RAM
Phi-3.5-mini-instruct     0.0%      31.7s    38.8s     7.21GB (92%)
  (first run, throttled†) 0.0%      35.7s    157.8s    7.11GB (93%)
Llama-3.1-8B-Instruct     0.0%      74.7s    232.3s    6.92GB (91%)
Gemma-3-4B-it             2.2%      77.1s    101.4s    7.26GB (96%)
GLM-4-9B-0414             14.6%     94.3s    300.1s*   6.81GB
Qwen3-8B (post-fan)       0.0%      127.0s   300.0s*   7.02GB
*pinned at the timeout ceiling   †started on a throttled, fanless Pi
```

**Speaker notes:** Backing: `docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md`,
the top-5 Pi 4 decision-grade summary. Worth one line on the thermal story
from Slide 11: Qwen3-8B's first Pi attempt failed gate 1 outright
(0.667 format_parse_rate) purely from throttling — the post-fan re-run
recovered it to a clean pass, closing that question for real rather than
by inference from a temperature reading alone. Phi-3.5-mini shows both of its
runs: the first started one second after that throttled Qwen3-8B run, before
the fan went in, which inflated its tail (p95 157.8s) and cost it two timeouts;
the 2026-10-02 re-run on a cooled Pi (p95 38.8s, 100% format) is the fair
number — impact-track row 26. Same thermal lesson, second data point.

### Slide 21 — Hardware Changes Speed, Not Accuracy
**Label:** M4 → Pi 4, Same Stack

**On-screen text:**
```
Model                   M4->Pi p50 ratio   M4->Pi p95 ratio  Accuracy delta
Phi-3.5-mini-instruct   47.5x slower       199.0x slower     +0.0pp
Gemma-3-4B-it           37.6x slower       42.7x slower      +2.2pp
Llama-3.1-8B-Instruct   59.9x slower       109.5x slower     -5.6pp
```

**Speaker notes:** Backing: `docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md`.
Latency drops 38-200x depending on model/percentile; accuracy moves at
most 5.6 points, in both directions, on samples small enough this is
plausibly noise. For the "when to use an LLM on the edge" decision: moving
hardware is a speed and resource decision here, not an accuracy one.

### Slide 22 — Final Model Recommendation: Two Tasks, Two Winners
**Label:** The Greenest Model Isn't a Property of the Model

**On-screen text:**
```
Edge Triage Pipeline (escalation decision) -> Phi-3.5-mini-instruct
  0.0% mismatch, tied for best; 2x+ faster at the median than the next
  tied model.
Tier 2 (spoken warning) -> Gemma-3-4B-it
  0.0%/0.0% ground+speak violation; fastest of four (43.7s median).
Same four models clear both gates. The ranking flips entirely between
tasks.
```

**Speaker notes:** Backing: `docs/TALK2-OUTLINE.md`'s "Final model
recommendation." Phi-3.5-mini-instruct is the Edge Triage Pipeline winner but the
*slowest* of four on Tier 2 (4x Gemma's median) — it pads its open-ended
`risk_synthesis` justification. Gemma-3-4B-it wins Tier 2 because it
respects the "2-3 sentence" bound Phi-3.5-mini ignores. The thesis line
for this act: the greenest model isn't a property of the model — it's a
property of the model for a given task.

## Act 3.5 — The Green Payoff

### Slide 23 — The Green Payoff: Real Numbers, Not Fabricated Ones
**Label:** What "Greenest" Actually Bought Us

**On-screen text:**
```
No GPU. No NPU. No cloud round-trip. 4-9B-parameter models, quantized to
Q4_K_M, running on a $55 commodity CPU board — and still landing at
0.0%-2.2% mismatch on the real target hardware for the task each one
wins.
Decoupling speed from model size: Phi-3.5-mini-instruct (3.8B) ties the
top accuracy tier and is the fastest of the clean five at the median.
No cloud FP16 baseline exists to normalize a "% accuracy retained" figure
against — that comparison hasn't been run yet
(TALK2-GPU-BENCHMARK-PLAN.md, not started).
Hardware resilience: the same models moved from M4 to Pi 4 with an
accuracy delta of at most 5.6 points, in either direction — plausibly
noise, not degradation.
```

**Speaker notes:** This merges the pasted draft's Slide 7 ("Empirical
Results") and Slide 8 ("Model Fidelity") into one real-numbers slide. There
is no power measurement in this project yet
(`docs/TALK2-POWER-MEASUREMENT-PLAN.md`, status: not started) and no
full-precision baseline (`docs/TALK2-GPU-BENCHMARK-PLAN.md`, not started) —
what's real is latency, RAM, mismatch rate, and hardware-move resilience,
and that's plenty to make the efficiency argument honestly, instead of the
pasted draft's invented "4.2W Avg Draw" and "94.2%/89.7%" accuracy-retention
bars.

## Act 4 — Why This Generalizes

### Slide 24 — Act 4
**Label:** Section: Beyond One Fleet Demo

**On-screen text:**
```
Why This Generalizes
```

**Speaker notes:** Section divider.

### Slide 25 — The Reusable Artifact Is the Funnel, Not the Model
**Label:** Same Constraint, Same Method

**On-screen text:**
```
Pulsar Functions here is one concrete instance of a real constraint: a
lightweight, event-driven execution engine where you can't paper over a
bad model choice with more compute.
Same constraint, same method applies to: on-device/smartphone inference,
other distributed edge topologies, any serverless/constrained host for a
small model.
The reusable artifact isn't "use Phi-3.5-mini" — it's the funnel: spectrum
-> task-derived ground truth -> layered checks -> resource gate on the
real target.
```

**Speaker notes:** Unchanged from the outline. We validated end to end on
a Pi 4 — the deliberately worst-case proxy on the compute spectrum from
Slides 4/6, zero dedicated AI TOPS. We have not directly measured
smartphone NPU performance (no data exists for that comparison in this
project), but there is no structural reason to expect a device with 35-80
TOPS of dedicated silicon to do worse than one with none. That is an
expectation this funnel sets up to be tested next, not a "10x surplus"
claim this project can back today.

### Slide 26 — Conclusion: The Greenest Token Is Task-Conditional
**Label:** The Close

**On-screen text:**
```
"I thought I was building a next-gen edge AI Pulsar function. I ended up
building something way more important: an evaluation framework."
Two real models, validated end to end on real Pi 4 hardware:
Phi-3.5-mini-instruct for the Edge Triage Pipeline, Gemma-3-4B-it for Tier 2. Not one
model, not a fictional one — the funnel's own honest answer, twice.
Repository code, benchmarks, and the full eval history: [Insert Repo URL
Pointer] [NEEDS: source]
```

**Speaker notes:** The thesis line, fully loaded this time. The Pulsar
function still ships — Talk 1 and Talk 3 prove it works end to end — but
the methodology is what survives past this one fleet demo. Land
"greenest token" with its sharpened meaning: not "smallest model," but
"cheapest model that still passes a task-honest bar you can prove," and
that bar is different for every task you point it at.

---

## Open items
- **Slide count vs. time budget — trimmed 2026-09-30.** Was 28 narrative
  slides (3–30); now 24 narrative slides (3–26), matching Talk 1's own
  24-slide, 40-minute pace exactly. Four merges did it, no content dropped:
  old Slides 4+6 (carbon bottleneck + compute-spectrum recap) into new
  Slide 4; old Slides 7+8 (extreme constraint proxy + real-spectrum bridge)
  into new Slide 6; old Slides 18+19 (spectrum/ground-truth setup + Layers
  1–2 checks) into new Slide 16; old Slides 26+27 (empirical results +
  model fidelity) into new Slide 23. Re-time on an actual read-through once
  the deck exists — merged slides now carry more on-screen text than a
  single-topic slide would.
- ~~Deck design system~~ — **Resolved.** This deck uses Talk 1's actual
  design system (DRUIDS tokens + `DATADOG_MARKETING_DECK` native slide
  types, per `talks/talk1-edge-intelligence/slides/`) — not the pasted
  draft's dark eco-tech theme, and not either standalone corporate profile
  (`datadog_marketing_deck_design_system` / `datadog_presentation_design_system`).
  Build every slide above against the real deck file
  (`Talk 1 Edge Intelligence.dc.html`) as the visual reference: white
  content-slide backgrounds, Lucide icon-badge status coding, purple-to-blue
  gradient reserved for Title/Section/Closing/Waitroom plates only.
- **BCM2711 sourcing.** Named on Slide 6 as an external fact (Raspberry Pi
  Foundation spec sheet) — not independently confirmed in any repo doc, only
  the Cortex-A72/4-core/8GB/1.5GHz specs are repo-sourced. Low risk (public,
  undisputed part number) but flagged per this project's citation discipline.
- **"Up to 95% noise data" (Slide 4).** Still unsourced — carried forward
  from Talk 1's own unresolved open item, not newly introduced here. If
  Talk 1 gets a real source before this deck is built, reuse it here too.
- **Repo URL (Slide 26).** Placeholder, same as the pasted draft — needs
  the actual repo link before this ships.
- **Talk 3 / trilogy-wide "1-bit" language check.** Not verified in this
  session: neither Talk 1's nor Talk 3's current slide/planning material was
  checked for stray "1-bit LLM" framing that might need the same "wall we
  hit, not a shipped result" caveat this plan applies throughout Talk 2.
