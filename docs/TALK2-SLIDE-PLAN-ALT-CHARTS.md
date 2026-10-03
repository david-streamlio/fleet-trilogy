# Talk 2 — "The Greenest Token" — Alternative Slide Plan (Charts-First)

**Status: a parallel option, not a replacement.** `docs/TALK2-SLIDE-PLAN.md`
is untouched and remains the primary plan. This file exists to compare
side-by-side a version of the same talk where real data drives the visual
language directly — charts and stat tiles instead of the primary plan's
dense tables — in the section of the talk that actually has numbers to show
(Act 3 / Act 3.5). Same facts, same sources, same honesty corrections. If
you pick this version, the intent is to replace the primary plan with it,
not merge the two.

Built from the same source docs as the primary plan, re-queried in full for
this pass: `docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md` (the actual
per-model latency/RAM/mismatch dataset) and `models.toml` (the 16-entry
manifest). **No energy, wattage, or Joules/token figures appear anywhere in
this file** — `docs/TALK2-POWER-MEASUREMENT-PLAN.md` is still "not started."
That axis stays out until the single-model instrumented test run (planned
separately, after this file) produces a real number.

40-minute slot, 26 slides total (1 Waitroom + 1 Title + 24 narrative,
slides 3–26) — same pacing envelope as the primary plan and as
`TALK1-SLIDE-PLAN.md`.

## Scope decision: what's actually different here

Acts 0, 1, and 2 (slides 3–13) and Act 4 (24–26) carry no per-model numeric
data — they're the sustainability framing, the BitNet pivot story, and the
generalization close. Re-deriving them wouldn't produce a meaningfully
different plan, so they're reproduced here **condensed**, same facts, same
corrected claims, with a pointer back to the primary plan's fuller speaker
notes rather than duplicating paragraphs that wouldn't change. One exception:
Slide 4's compute-spectrum bullet list becomes a small real chart (see
below), since it already cites real TOPS figures from Talk 1.

**Act 3 (14–22) and Act 3.5 (23) are fully redesigned.** The primary plan
carries three dense data tables there (M4 gate result, Pi 4 numbers,
hardware-delta table) plus a prose "payoff" slide. This version replaces all
four with four charts/stat-tile slides built directly from the same
underlying numbers — no new data, no fabricated axis, just a different
visual language for data this project actually measured. One of the four
also **corrects a real bug**: the primary plan's hardware-delta table
(its Slide 21) has the accuracy-delta sign backwards — this was flagged in
`docs/TALK2-DECK-BUILD-PROMPT.md`'s "known content issues" list, and this
plan fixes it at the source instead of patching it after deck generation.

## Resolved: the "14 candidates" reconciliation

`models.toml` has 16 `[[models]]` entries. The M4 Edge Triage Pipeline gate table everyone
cites as "14 candidates" is 16 minus two explicit exclusions, confirmed in
`docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md`'s "Full M4 gate result"
section:
- **Gemma-3-1B-it** — already run and rejected in an earlier 7-model
  fixed-harness pass (51.1% escalation mismatch, the only one of 7 to fail
  gate 2), so it isn't re-run in the 14-candidate sweep.
- **Qwen3.8-27B** — excluded for confirmed Pi 4 thermal issues at its
  weight class (`models.toml`'s own elimination note).

16 − 2 = 14. This is now settled; no open reconciliation item remains.

## Executive summary

Four real findings carry this talk, same as the primary plan, now stated as
the chart punchlines instead of table rows:
1. **Format reliability is solved across the whole 14-model spectrum** —
   13 of 14 hit exactly 1.000 parse rate. Size and family stopped mattering
   for this axis.
2. **A real five-model clean tier exists at ≤6.7% escalation mismatch** on
   the M4 gate, spanning 3.8B–9B parameters — the richest candidate pool in
   this project.
3. **Moving from M4 to the real Pi 4 target changes speed, not accuracy** —
   latency drops 38–200x; accuracy moves at most 7.9 percentage points, in
   either direction, plausibly noise at this sample size.
4. **The ranking flips entirely between tasks** — Phi-3.5-mini-instruct
   wins the Edge Triage Pipeline's escalation decision; Gemma-3-4B-it wins Tier 2's spoken
   warning. Neither is "the" greenest model — the greenest model is
   task-conditional.

The honesty correction carried over unchanged from the primary plan: the Pi
4 is tested as a **worst-case proxy, not a measurement of**, faster real
targets (smartphone NPUs, automotive SoCs). Nothing in this project
guarantees headroom on those devices — there is no structural reason to
expect a device with 35–80 TOPS of dedicated silicon to do worse than one
with zero, but that is an expectation this funnel sets up to test, not a
claim this project can back today.

---

### Slide 1 — Welcome! We'll begin shortly.
**Label:** Waitroom

**On-screen text:**
```
The Greenest Token
Grab a coffee and settle in.
```

**Speaker notes:** Untimed lobby slide, same as the primary plan.

### Slide 2 — The Greenest Token: An Evaluation & Deployment Methodology for Edge Execution Engines
**Label:** Title

**On-screen text:**
```
David Kjerrumgaard
Apache Pulsar Committer
```

**Speaker notes:** Same cold open as the primary plan: "I thought I was
building a next-gen edge AI Pulsar function. I ended up building something
way more important: an evaluation framework." Say it once, don't explain
it.

## Act 0 — The Green Edge

### Slide 3 — The Green Edge
**Label:** Section: The Green Edge

**On-screen text:**
```
The Green Edge
Decarbonizing Vehicle AI via the Ubiquitous CPU
```

**Design note:** Talk 1's real, already-built design system — DRUIDS tokens
(Noto Sans, 4px/8px radii, `--ui-status-*` color tokens) plus the
`DATADOG_MARKETING_DECK` native slide types. Purple-to-blue faceted gradient
plate, reserved for Title/Section/Closing/Waitroom only — matches
`talks/talk1-edge-intelligence/slides/source/Talk 1 Edge Intelligence.dc.html`.

**Speaker notes:** Same as primary plan Slide 3: every real number this
talk produces is also a sustainability number — decarbonizing vehicle AI
means not needing the data-center call at all, not building a greener one.

### Slide 4 — Centralized AI's Carbon Bottleneck, and Where the Pi 4 Sits
**Label:** The Cost of the Cloud — and the Way Out

**On-screen text:** replace the primary plan's bullet list with a small
horizontal bar chart — **the compute spectrum by TOPS**:
```
Luxury AV Silicon        ███████████████████████████████████  500+ TOPS
Smartphone NPU           ███                                   35–80 TOPS
Raspberry Pi 4           ·                                     0 TOPS  ← tested today
```
`[bracket over Smartphone NPU + Pi 4] "The Democratization Target Zone"`

**Design note:** `Comparison`-affinity content region (per
`DATADOG_MARKETING_DECK`'s content-affinity map, `Bar_Comparison` →
`Comparison`), white background, bars colored with DRUIDS neutral tokens
except the Pi 4 bar, which gets `--ui-status-warning` (amber) to flag "this
is the one we actually measured, and it's the floor of the spectrum."
Cloud GPU clusters are deliberately left off this chart — no bounded TOPS
figure exists for "a cluster," and Talk 1 never gave one either.

**Speaker notes:** Same source as the primary plan's Slide 4 — Talk 1
Slide 10's spectrum (500+ TOPS luxury AV, 35–80 TOPS smartphone NPU, 0
dedicated AI TOPS for the Pi 4). The "up to 95% noise data" structural-waste
claim from the primary plan's Slide 4 is dropped here rather than carried
forward with its `[NEEDS: source]` tag still unresolved — it isn't load-
bearing for this chart, and an unsourced number has no place next to three
sourced ones on the same slide. If you want it back, it needs a real
source first, same bar the rest of this chart clears.

### Slide 5 — The Sustainability Blueprint
**Label:** Embodied Compute, Not New Compute

**On-screen text:** unchanged from primary plan Slide 5 (three-column
scorecard: Zero Manufacturing Footprint / Decentralized Ingestion / The
Handheld Target). No numeric data to chart here — see primary plan for full
text.

**Speaker notes:** Unchanged. The greenest token is the one that runs on
hardware that already exists.

### Slide 6 — The Extreme Constraint Proxy, and What We Actually Tested
**Label:** Why Test the Worst Case

**On-screen text:** unchanged from primary plan Slide 6 — Pi 4 spec line
($55, 4-core Cortex-A72/BCM2711[^bcm], 8GB RAM test unit, 1.5GHz stock
clock, 0 dedicated AI TOPS), the worst-case-proxy framing, "14 Q4_K_M
candidates, 350M–9B parameters," and the explicit "not tested: cloud-class
FP16 baseline" caveat.

`[^bcm]: Raspberry Pi Foundation spec sheet — external fact, not
independently cited elsewhere in this repo. Same convention applies below
to model parameter counts: see the footnote on Slide 20.`

**Speaker notes:** Unchanged — this is the slide that already carries the
honesty correction in the primary plan ("worst-case-proxy reasoning, not a
guarantee," replacing the pasted draft's "guarantees flawless deployment on
cell phones" line). Nothing to change here; this version's correction lives
on Slide 23 instead, where the primary plan's version didn't have one yet.

## Act 1 — The Dream

### Slide 7 — Act 1
**Label:** Section: The Dream

**On-screen text:**
```
The Dream: A Natural Next Step
```

**Speaker notes:** Section divider, unchanged.

### Slide 8 — 1-Bit LLMs Make This Look Newly Possible
**Label:** A How-To Talk, At First

**On-screen text / speaker notes:** unchanged from primary plan Slide 8 —
no numeric data to chart; see primary plan for full text.

## Act 2 — Two Walls

### Slide 9 — Act 2
**Label:** Section: Two Walls

**On-screen text:**
```
Two Walls
```

### Slide 10 — Wall 1: BitNet's Garbage Output on ARM
### Slide 11 — The Real Engineering Cost: Getting Mainline onto the Pi 4
### Slide 12 — Wall 2: The 0.5B Capability Cliff
### Slide 13 — The Turn

**On-screen text / speaker notes (10–13):** unchanged from the primary
plan — this is the BitNet postmortem and the 0.5B cliff, narrative/
qualitative content with no per-model comparison numbers to chart. See
primary plan Slides 10–13 for full text.

## Act 3 — Building the Methodology

### Slide 14 — Act 3
**Label:** Section: The Methodology Funnel

**On-screen text:**
```
Building the Methodology
```

**Speaker notes:** Unchanged — present as a layered funnel, cheap checks
first.

### Slide 15 — Layer 0: Can It Even Run Here?
### Slide 16 — Layers 1–2: Setup, Format Reliability & Grounding
### Slide 17 — Layer 3–4: Directional Accuracy & Severity Calibration
### Slide 18 — The Architectural Pivot

**On-screen text / speaker notes (15–18):** unchanged from the primary
plan — these are process/conceptual slides (what each layer checks and
why), not data tables, so there's nothing to re-render as a chart. See
primary plan Slides 15–18 for full text. Backing:
`docs/TALK2-MODEL-SPECTRUM-ACCURACY-PLAN.md`, `models.toml`,
`docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md` section 5.

### Slide 19 — The Full Spectrum: Where Every Candidate Lands
**Label:** Layer 5, Gate 1 — The M4 Quality Gate

**Visual (primary content, replaces the primary plan's text table):**
horizontal bar chart, one bar per model, 14 models, sorted ascending by
escalation-mismatch rate:

```
Qwen3-8B                 ▏ 0.0%
Phi-3.5-mini-instruct    ▏ 0.0%
Gemma-3-4B-it            ▏ 0.0%
Llama-3.1-8B-Instruct    ▎ 5.6%
GLM-4-9B-0414            ▎ 6.7%
Qwen2.5-0.5B-Instruct    ████████ 33.3%
Qwen2.5-1.5B-Instruct    █████████ 36.6%
Llama-3.2-1B-Instruct    █████████▌ 38.9%
Ling-3.0-tiny (7.9B-A1.3B)██████████▌ 42.2%
Llama-3.2-3B-Instruct    ██████████▌ 42.2%
Qwen2.5-3B-Instruct      ███████████▌ 46.7%
                         ┊┊┊┊┊┊┊┊┊┊┊┊┊ ← 50% reject bar
LFM2.5-350M              ████████████████ 64.4%
Qwen3-0.6B               ████████████████▌ 66.7%
Granite-4.0-H-350M       ████████████████▌ 66.7%
```

X-axis: escalation-mismatch rate, 0–70%. A dashed reference line at 50%
marks the reject threshold. Bar color by verdict tier, DRUIDS status
tokens: `--ui-status-success` (≤6.7%, "clean"), a lighter success/neutral
tint (5.6–46.7%, "passes, weakening toward the line"),
`--ui-status-danger` (>50%, "reject"). All 14 bars get a small format-
parse-rate badge (Lucide check-circle) except Qwen2.5-1.5B-Instruct, whose
badge reads "0.967" instead of a plain check — the one model not at a clean
1.000.

**On-screen callout, top-right:**
```
13 of 14: exactly 1.000 format-parse rate.
11 of 14 clear the 50% reject bar.
Only the three smallest (≤0.6B) fail it.
```

**Speaker notes:** Backing: `docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md`,
"Full M4 gate result: all 14 candidates" (`compare-edge-triage-COMP-J2D9D71YNJ-
20260926T215201Z.json`). Don't blend the two different thresholds the
primary plan's version of this slide risked blending — "≤6.7% clean tier"
and "the 50% reject bar" are two separate claims, now visually separated by
the dashed line instead of living in the same sentence. Qwen2.5-0.5B-
Instruct passing at 33.3% — better than several 1–3B models — is worth a
beat live: size correlates with this task, it doesn't determine it
model-by-model.

### Slide 20 — The Pareto Frontier: Size vs. Speed, on the Real Target
**Label:** Layer 5, Gate 2 — The Pi 4 Decision Grade

**Visual (primary content):** scatter/bubble chart, the five M4-cleared
candidates, **all real, all on the Pi 4**:

| Model | Params[^params] | Pi p50 latency | Escalation mismatch |
|---|---|---|---|
| Phi-3.5-mini-instruct | 3.8B | 31.7s (35.7s first run, throttled start) | 0.0% |
| Gemma-3-4B-it | 4B | 77.1s | 2.2% |
| Llama-3.1-8B-Instruct | 8B | 74.7s | 0.0% |
| Qwen3-8B (post-fan) | 8B | 127.0s | 0.0% |
| GLM-4-9B-0414 | 9B | 94.3s | 14.6% |

X-axis: parameter count (B), log scale. Y-axis: Pi 4 p50 latency (seconds) —
**inverted**, so "better" (faster) plots higher, matching the conventional
Pareto-frontier reading of "up and to the left is good." Bubble color:
escalation mismatch, same status-token scale as Slide 19
(`--ui-status-success` at 0.0–2.2%, `--ui-status-warning` at 14.6%). Draw
and label the frontier explicitly: Phi-3.5-mini-instruct is the only point
no other point dominates on both axes — smallest, fastest, and tied for
best accuracy. Annotate tokens/sec directly on the three points where it's
actually measured for this task (Phi-3.5-mini-instruct 0.467, Gemma-3-4B-it
0.867, Llama-3.1-8B-Instruct 0.499); label the other two points "tok/s not
reported for this task" rather than omitting them or inventing a number.

`[^params]: publisher-stated parameter counts (model name / HF card) —
external facts, same convention as the BCM2711 footnote on Slide 6; not
independently re-measured in this repo.`

**Speaker notes:** Backing: `docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md`,
the top-5 Pi 4 decision-grade summary. This replaces the primary plan's
Slide 20 table with the same five numbers, framed as a tradeoff instead of
a list — the punchline is visual: Phi-3.5-mini-instruct sits alone at the
dominant corner. Worth a line on the thermal story: Qwen3-8B's point is the
*post-fan* re-run — its first Pi attempt failed gate 1 outright from
throttling, not a model problem (see Slide 11/the primary plan's Slide 20
note).

### Slide 21 — Hardware Changes Speed, Not Accuracy — Corrected
**Label:** M4 → Pi 4, Same Stack, All Five Models

**Visual (primary content):** grouped bar chart, five models, two bars each
(M4 accuracy% and Pi 4 accuracy%, where accuracy = 100 − escalation-
mismatch rate), with a delta callout per model:

| Model | M4 accuracy | Pi 4 accuracy | Accuracy delta (Pi − M4) |
|---|---|---|---|
| Qwen3-8B | 100.0% | 100.0% | 0.0pp |
| Phi-3.5-mini-instruct | 100.0% | 100.0% | 0.0pp |
| Llama-3.1-8B-Instruct | 94.4% | 100.0% | **+5.6pp** |
| Gemma-3-4B-it | 100.0% | 97.8% | −2.2pp |
| GLM-4-9B-0414 | 93.3% | 85.4% | **−7.9pp** |

**This corrects a real sign bug.** The primary plan's equivalent table
(its Slide 21) computed the delta backwards — a model whose mismatch rate
*improved* on the Pi showed up as a *negative* accuracy delta, which reads
as a regression. The convention here is unambiguous: delta = Pi accuracy −
M4 accuracy, so positive always means "got more accurate on the Pi." Under
the corrected convention, Llama-3.1-8B-Instruct's real +5.6pp move reads
correctly as an improvement (the primary plan showed this as "−5.6pp");
GLM-4-9B-0414's −7.9pp is a newly-surfaced finding not in the primary
plan's three-model version of this table at all (it only covered Phi-3.5-
mini-instruct, Gemma-3-4B-it, and Llama-3.1-8B-Instruct — this version adds
the other two M4-cleared models now that both have Pi numbers).

**Speaker notes:** Backing: `docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md`,
"Decision-tree data point" and the top-5 Pi 4 summary. Deltas span −7.9pp to
+5.6pp, in both directions, on n=41–90 samples small enough that this is
plausibly noise around a stable true rate rather than a real hardware
effect — say that explicitly, don't let the chart imply more precision than
the sample size supports. The actual finding: moving from M4 to Pi 4 is a
speed and resource decision for this stack, not an accuracy one. GLM-4-9B's
larger move is flagged in the source doc as the first of the five to show a
real gap rather than a near-identical number — worth naming live as the one
exception to watch, not smoothing over.

### Slide 22 — Final Model Recommendation: Two Tasks, Two Winners
**Label:** The Greenest Model Isn't a Property of the Model

**Visual:** two-tile stat comparison (`Stats`/`Comparison`-affinity
content, not a chart — this is a qualitative pairing, not a numeric axis):
```
┌─────────────────────────┐   ┌─────────────────────────┐
│ EDGE TRIAGE (escalation)│   │ TIER 2 (spoken warning)  │
│ Phi-3.5-mini-instruct   │   │ Gemma-3-4B-it             │
│ 0.0% mismatch            │   │ 0.0%/0.0% ground+speak   │
│ fastest Pi p50 (31.7s)  │   │ fastest of four (43.7s)  │
└─────────────────────────┘   └─────────────────────────┘
Same four models clear both gates. The ranking flips entirely.
```

**Speaker notes:** Phi's p50 is the 2026-10-02 re-run (31.7s); its first,
throttled-start run measured 35.7s (impact-track row 26) — both kept. Otherwise
unchanged from primary plan Slide 22 — Phi-3.5-mini-
instruct is the Edge Triage Pipeline winner but the *slowest* of four on Tier 2 (it pads
its open-ended `risk_synthesis` field); Gemma-3-4B-it wins Tier 2 because it
respects the "2–3 sentence" bound Phi-3.5-mini ignores. Backing:
`docs/TALK2-OUTLINE.md`'s "Final model recommendation" and
`docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md`'s cross-task latency
comparison. Thesis line: the greenest model isn't a property of the model —
it's a property of the model for a given task.

## Act 3.5 — The Green Payoff

### Slide 23 — The Green Payoff: Real Numbers, as Stat Tiles
**Label:** What "Greenest" Actually Bought Us

**Visual (primary content, replaces the primary plan's prose paragraph):**
four big-number stat tiles (`Stats` native type), one row:

```
$55            0 TOPS         0.0%–14.6%      6.81–7.26GB
hardware cost  dedicated AI   mismatch range   peak RAM of 8GB
(2GB unit)     silicon used   across clean 5    (84–96% used)
```

**On-screen callout, below the tiles:**
```
No GPU. No NPU. No cloud round-trip.
No cloud FP16 baseline exists yet to normalize a "% accuracy retained"
figure against — that comparison hasn't been run (TALK2-GPU-BENCHMARK-
PLAN.md, not started).
```

**The correction, stated explicitly here (same correction the primary plan
applies on its own Slide 6, now restated at the payoff beat where the
pasted draft's original claim actually lived):** this project has not
measured power draw anywhere (`docs/TALK2-POWER-MEASUREMENT-PLAN.md`:
not started) and has not run a GPU/NPU comparison
(`docs/TALK2-GPU-BENCHMARK-PLAN.md`: not started). The Pi 4's real numbers
above are a **worst-case-proxy expectation** for how this stack behaves on
faster, more capable hardware — not a guarantee, and not a measurement this
project has made on a phone NPU or an automotive SoC. What's real and
load-bearing on its own: four to nine billion parameters, quantized to
Q4_K_M, landing at 0.0–14.6% mismatch on $55 of commodity CPU, with no
dedicated AI silicon at all.

**Speaker notes:** Backing:
`docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md`'s top-5 Pi 4 summary (RAM
range recomputed here across all five models, not just the three the
primary plan's Slide 23 cited). The honest frame: an instrumented energy
test run is planned next, starting with a single model — this slide
states the expectation the project is testing, not a result it already
has.

## Act 4 — Why This Generalizes

### Slide 24 — Act 4
**Label:** Section: Beyond One Fleet Demo

**On-screen text:**
```
Why This Generalizes
```

### Slide 25 — The Reusable Artifact Is the Funnel, Not the Model
### Slide 26 — Conclusion: The Greenest Token Is Task-Conditional

**On-screen text / speaker notes (25–26):** unchanged from the primary
plan — no numeric comparison data to chart here, and the primary plan's
Slide 25 already carries the correct worst-case-proxy correction in its own
speaker notes ("we have not directly measured smartphone NPU performance
... there is no structural reason to expect [worse] ... that is an
expectation this funnel sets up to be tested next, not a ... claim this
project can back today"). Slide 26's closing repo-link placeholder is the
same open item as the primary plan — see Open items below; don't render
`[Insert Repo URL Pointer]` as visible text on either version.

---

## Evaluation Framework — copy-paste methodology

A reusable description of the two-gate funnel this talk is actually built
on, grounded in what this project measured (not the pasted draft's version
of this section, which assumed capabilities — like a completed energy test
suite — this project doesn't have yet):

```
GATE 1 — M4 quality gate (cheap, fast iteration hardware)
  Run every candidate model against task-derived ground truth
  (not hand-labeled, not a generic leaderboard).
  Check format-parse rate first — a model that can't produce
  parseable structured output never reaches gate 2.
  Check escalation/severity-direction mismatch rate against a
  fixed bar (this project used 50%).
  Output: a ranked candidate pool, cheap to produce, NOT yet
  validated on the real target device.

GATE 2 — Decision-grade run (the real target device)
  Take only the gate-1 survivors and re-run the identical harness
  on the actual deployment hardware, one model at a time (shared
  GPU/Metal memory contention between concurrently-running models
  corrupts results — this project hit that bug twice before
  adopting "one model fully finishes before the next loads").
  Capture format-parse rate, mismatch rate, p50/p95 latency,
  tokens/sec, and resident RAM on THIS run, not the gate-1 run —
  dev-machine numbers do not transfer.
  Check the target's thermal state (get_throttled, measure_temp)
  before trusting any latency number as the hardware's real
  capability rather than a throttled fraction of it.
  Output: the actual deployment decision, per task — not
  "the best model," since gate-2 winners can flip entirely between
  two different tasks run against the same candidate pool.
```

Sourced in full from `docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md`; this is
the methodology Slides 15–22 above dramatize, written as a standalone
checklist rather than talk narration.

---

## Open items (carried over / new)

- **Energy measurement — explicitly out of scope for this file.** A single-
  model instrumented test run is planned next, separately from this
  planning pass; a full sweep and possibly a more-instrumented redesign may
  follow depending on what that first run needs. Nothing here should be
  read as anticipating that data.
- **Repo URL placeholder (Slide 26)** — same open item as the primary plan;
  needs a real value before either version ships, not a rendered bracket.
- **"Up to 95% noise data" claim** — dropped from this version's Slide 4
  rather than carried forward unsourced (see that slide's design note). The
  primary plan still carries it with its `[NEEDS: source]` tag; reconcile
  the two versions' treatment of this one claim if you pick this file.
- **Chart rendering** — every chart slide above (19, 20, 21, and Slide 4's
  spectrum bar) specifies axes, real data points, and DRUIDS status-token
  color encoding in enough detail to hand to a build tool directly; none of
  them are native PPTX chart objects — they're custom SVG/Canvas content
  regions inside a `Content`-type slide, same as Talk 1's actual
  `.dc.html` build, not a different rendering approach.
