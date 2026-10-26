# Talk 1 — "Edge Intelligence" — Slide Plan

40-minute slot. 26 timed slides, plus 3 untimed courtesy slides (Waitroom, Title, Thank You). Built from the Explorer's Journey narrative over
`docs/BITNET-POSTMORTEM.md` and `docs/PI4-RUNBOOK.md`, plus intro material
grounded in `docs/CANON.md`,
`shared/fleet-telemetry-model/src/fleet_telemetry_model/schemas.py`,
`talks/talk1-edge-intelligence/src/talk1_edge_intelligence/coprocessor.py`,
`triage_function.py`, and `deploy/README.md`.


**Revision (2026-09-30) — synced from the built deck:**
- Community-conference build: all Datadog branding removed (logos, eyebrow labels). Phase names below are narrative structure only and no longer appear on slides.
- Added untimed Waitroom and Title slides before the narrative.
- Old Slide 1 (Truck 47 / SLOWDOWN definition) replaced by three fleet-level slides: 1 "Watching the Whole Fleet", 2 "Every Truck Reports In", 3 "What a Truck Senses: One Telemetry Event". All later slides shift by +2. The SLOWDOWN formula no longer appears on screen.
- Introduction stays at 8 min across 6 slides (1 / 1 / 1.5 / 1.5 / 1.5 / 1.5).
- Added Slides 4–5 (Before / After architecture). All later slides shift by a further +2. `[NEEDS: time budget — the two new slides add ~3 min over the 40-min slot]`
- Slide 5 reworked for commodity hardware ("Democratizing the Edge with Resource-Constrained Hardware"); new Slide 6 teaser plate pointing to Talk 2; old "Any Constrained Device" slide replaced by Slides 25 (Now) and 26 (Dream). Performance numbers are deferred to Talk 2 — see `docs/TALK2-HANDOFF-FROM-TALK1.md`.
- Title, Section (10, 17) and Closing plates share the Waitroom's purple-to-blue faceted background.

**Style Profile: `DATADOG_MARKETING_DECK`** (tech-slide-planner skill,
reference config) — switched from the sibling `DATADOG_PRESENTATION_2026`
profile specifically because this talk is code/runbook-heavy: this profile
has a dedicated `Metric` ("Code + KPI") type and a dedicated `Timeline` type
for numbered sequential steps, neither of which its sibling has natively.
`Suggested Layout` below is a **Native Slide Type** name straight from this
profile's real inventory (`Title, Section, Content, Stats, Quote, Comparison,
Product, Agenda, Three-up, Integrations, Timeline, Statement, Metric,
Closing`). Per the skill's Deck rhythm constraints, plate types (`Title`,
`Section`, `Quote`, `Product`, `Statement`, `Closing`) never sit back to back
— this plan's only two in-narrative plates (Slides 6, 10 and 17) are each isolated between
content-bearing slides.

**Where this plan deliberately does not follow the Content Affinity Map's
top-ranked match** — flagged per the accuracy guardrail rather than forcing
a slide shape that would need a fabricated number to fill it:
- The Content Affinity Map's top pick for `Code_Block` is `Metric` (Code +
  KPI), but `Metric` structurally needs a real produced number next to the
  code. Slides 11, 14, 20 show code/output with no accompanying measured
  metric at that point in the story (a custom kernel declaration, a garbage
  token stream, a build command) — forcing a KPI callout onto them would
  mean inventing a number. They use `Content` instead. Slide 13 *does* have
  a real number (`~5 tokens/sec`) and uses `Metric` as intended.
- Slides 20–23 ("Step 1" – "Step 4" of the pivot runbook) all use `Timeline`
  — not just the ones that read as a literal linear step — because they are,
  together, one numbered runbook sequence, which is exactly what this
  profile's `Timeline` type is built for. Each slide shows the same 4-step
  rail with its own step highlighted, so the audience always sees where
  they are in the runbook.

Two open items remain, flagged rather than fabricated — fill in before final
build. (A third, Slide 21's coherence-check command, is now resolved — see
below.)
- Slide 24 needs the actual demo recording. Broker placement is resolved —
  `deploy/README.md` documents "Broker OFF the Pi (default)," matching the
  `pulsar://<broker-host>:6650` command already on this slide — but no
  source gives the recording itself. Also: no native slide type or Visual
  Manifest `Type` in this system covers an embedded/played video, so it's
  built as `Content` with the entry-point command displayed and the
  recording flagged as missing, not faked as a static screenshot.
- Slides 5, 25, 26 carry unsourced cost/scale figures, shown as visible NEEDS callouts (list in `docs/TALK2-HANDOFF-FROM-TALK1.md`).

---

## Untimed opening slides (before the 40-min narrative)

### Waitroom
**Suggested Layout:** Title *(lobby plate — shown while attendees join)*
**Visual Manifest:**
  - Type: Typography_Only
  - Spec: purple-to-blue faceted background (shared with the Title, Section and Closing plates); left: eyebrow "Edge Intelligence for Connected Fleets", welcome headline, subline, countdown badge; right: auto-rotating Apache Pulsar facts card with prev/next arrows, dots, counter and progress bar. Countdown length (default 5 min) and rotation interval (default 12 s) are tweakable.
**On-Screen Text:**
```
Welcome! We'll begin shortly.
Grab a coffee and settle in. While you wait, here are some interesting facts about Apache Pulsar
STARTING IN 5:00
```
**Rotating facts:**
  - Apache Pulsar was created at Yahoo in 2012.
  - Apache Pulsar became a top-level ASF project in 2017
  - Apache Pulsar has over 400 committers `[VERIFY: committer count]`
  - Apache Pulsar is used by three automotive manufacturers in production today.
**Speaker Notes:** Lobby slide. Leave up while attendees join; the countdown and Pulsar facts run on their own.
**Time:** 0 min

### Title
**Suggested Layout:** Title *(plate)*
**On-Screen Text:**
```
Edge Intelligence for Connected Fleets: 1-Bit LLMs Inside Apache Pulsar Functions
David Kjerrumgaard
Apache Pulsar Committer
```
**Speaker Notes:** Untimed title slide. Introduce yourself, then go straight into the use case.
**Time:** 0 min

---

## Phase: Introduction — ~12.5 min (9 slides)

### Slide 1 — "Watching the Whole Fleet"
**Suggested Layout:** Content *(full-bleed image, title + caption on a bottom text plate)*
**Core Message:** The use case, from the highest level: a control center observes an entire fleet of class 8 trucks (semi-trucks), not a single vehicle. A slowing truck becomes a signal for the rest of the fleet to reroute.
**Visual Manifest:**
  - Type: Image
  - Spec: full-bleed image — a fleet of trucks dispatched across a map, plus a control center with operators watching metrics and communicating with the trucks (think NASA flight control / air traffic control). `[NEEDS: image — to be generated outside the deck and dropped into the placeholder]`
**On-Screen Text:**
```
Watching the Whole Fleet
A control center observes every class 8 truck at once. When one truck slows down, that becomes a signal for the rest of the fleet to reroute.
```
**Speaker Notes:** Start at the highest level: this talk is about observing an entire fleet of class 8 trucks, semi-trucks, not a single vehicle. A control center watches every truck at once, much like flight control or air traffic control. The point of watching is to catch a vehicle that is slowing down and use it as a signal to the rest of the fleet: reroute before they reach the same stretch of road.
**Time:** Introduction, ~1 min

### Slide 2 — "Every Truck Reports In"
**Suggested Layout:** Content *(full-bleed image, title + caption on a bottom text plate)*
**Core Message:** Each truck carries a small onboard computer that collects sensor readings and sends them to the control center over cellular.
**Visual Manifest:**
  - Type: Image
  - Spec: full-bleed side-angle view of a semi tractor rig, sensors emitting small sonar-style waves from points on the truck, a cellular antenna, and a small onboard computer. `[NEEDS: image — to be generated outside the deck and dropped into the placeholder]`
**On-Screen Text:**
```
Every Truck Reports In
A small onboard computer collects sensor readings from across the rig and sends them back to the control center over cellular.
```
**Speaker Notes:** Zoom in to one truck. Each rig carries a small onboard computer that collects readings from sensors across the tractor and sends them back to the control center over cellular. That onboard computer is where this talk's code runs.
**Time:** Introduction, ~1 min

### Slide 3 — "What a Truck Senses: One Telemetry Event"
**Suggested Layout:** Metric *(Code + KPI)*
**Core Message:** One `TelemetryEvent` on the wire, and the scale behind it: more than 2k sensor readings per truck.
**Visual Manifest:**
  - Type: Code_Block
  - Spec: dark code panel with an example `TelemetryEvent` JSON payload (fields per `shared/fleet-telemetry-model/src/fleet_telemetry_model/schemas.py`; illustrative values for a truck mid-slowdown; simulation-only `_ground_truth` omitted), KPI callout beside it.
**On-Screen Text:**
```
{
  "timestamp": "2026-10-14T14:32:05Z",
  "truck_id": "truck-47",
  "speed_mph": 33.8,
  "gps": { "lat": 33.9612, "lon": -84.4000 },
  "heading": 0.0,
  "route_segment": "I-95N-segment-4",
  "corridor": "I-95N",
  "planned_eta": "2026-10-14T15:05:00Z",
  "current_eta": "2026-10-14T15:12:12Z",
  "signals": {
    "rolling_avg_speed": 36.1,
    "eta_slip_min": 7.2,
    "stop_go_index": 0.74
  },
  "brake_events": 1,
  "downshift_events": 1,
  "peak_deceleration_g": 0.31,
  "abs_engaged": false
}

> 2k  sensor readings per truck
```
**Speaker Notes:** This is what one of those readings looks like on the wire: a single TelemetryEvent, published to the truck-telemetry topic. Speed, GPS, heading, route segment and corridor, planned versus current ETA, cheap-math signals, and raw braking readings. Values shown are illustrative of a truck mid-slowdown. Each truck carries more than 2,500 sensor readings in total. Every schema and pipeline stage that follows exists to turn this stream into a reroute decision.
**Time:** Introduction, ~1.5 min

### Slide 4 — "Current Architecture: Cloud-Centric Observability Bottlenecks"
**Suggested Layout:** Comparison *(BEFORE half of a matching Before/After pair; tab toggle at top jumps between Slides 4 and 5)*
**Core Message:** Without edge intelligence, every truck streams raw telemetry over cellular to an overloaded cloud core, so decisions are slow, bandwidth is wasted, and dead zones mean blindness.
**Visual Manifest:**
  - Type: Mermaid_Architecture
  - Spec: split layout — bullets left, diagram right. Fleet of trucks labeled "Dumb Edge" emitting thick, overlapping crimson arrows (RPM, GPS, Brake wear) across a "High-Latency Cellular Pipeline" gap into a large "Cloud Core" (badge "Overloaded") containing Ingestion Queues (Overloaded), Stream Processing (Lagging), Data Lakes (95% Noise Data). Crimson/amber accents. Scorecard footer: Decision Latency / Data Efficiency / Network Risk, Before row highlighted.
**On-Screen Text:**
```
• High Decision Latency (10s – Minutes): Critical safety events must make a full cloud round-trip before any action is taken.
• Bandwidth Bleed: Massive cellular costs incurred by continuously transmitting normal, repetitive readings.
• Network Dependencies: Total loss of visibility and real-time tracking when a vehicle enters a cellular dead zone.

Decision Latency: 10s – minutes | Data Efficiency: 95% noise data | Network Risk: Visibility lost in dead zones
```
**Speaker Notes:** This is how fleet observability works today without edge intelligence. Every truck is a dumb edge: it streams raw, unfiltered telemetry, RPM, GPS, brake wear, continuously, over a high-latency cellular pipeline into one cloud core. That core has to ingest, queue, process and store all of it, and most of it is normal, repetitive readings. Three costs follow. Decision latency: a critical safety event has to make a full cloud round-trip, tens of seconds to minutes, before anyone acts. Bandwidth bleed: you pay cellular costs to ship noise. And network dependency: when a truck drives into a dead zone, you lose it entirely. Next, the same fleet with the intelligence moved onto the truck.
**Time:** Introduction, ~1.5 min

### Slide 5 — "Democratizing the Edge with Resource-Constrained Hardware"
**Suggested Layout:** Comparison *(AFTER half; matching split layout; Before/After tab toggle)*
**Core Message:** Edge intelligence doesn't need a mobile supercomputer: a commodity Pi-class node running a 1-bit / small quantized LLM can act as the truck's gatekeeper.
**Visual Manifest:**
  - Type: Mermaid_Architecture
  - Spec: callout box across the top: "Commodity Edge Node (Raspberry Pi 4 Class Hardware / 4GB-8GB RAM)" with an inner layer "Quantized 1-bit / small LLM · Edge Diagnostics Model". Below it, the "Smart Edge" fleet (each truck with a node chip and a local loop, "Sub-second Local Action"), thin emerald arrows labeled "Filtered Anomalies Only (90%+ Bandwidth Savings)" into a "Lean Cloud Core" with an "Operations Control Center" badge. Same scorecard footer as Slide 4, with the After row highlighted.
**On-Screen Text:**
```
• Algorithmic Efficiency over Raw Power: Utilizing highly optimized 1-bit / small quantized LLMs to run complex diagnostic reasoning on sub-$100 commodity hardware. [NEEDS: price source]
• Localized Diagnostic Autonomy: The Raspberry Pi acts as an intelligent gatekeeper, running real-time inference on vehicle telematics without a cloud connection.
• Frictionless Fleet Scaling: Shifting to low-footprint hardware drives down hardware deployment costs by 95% compared to traditional AV computing platforms. [NEEDS: source for 95%]
```
**Speaker Notes:** Now the same fleet with edge intelligence, and the point of this talk: it doesn't take a mobile supercomputer. Each truck gets a commodity edge node, Raspberry Pi 4 class hardware with 4 to 8 GB of RAM, running a 1-bit or small quantized LLM as a lightweight diagnostics layer. The node acts as a gatekeeper: it runs inference on the truck's telematics locally, with no cloud connection required, and only filtered anomalies go over cellular. Massive compute is not what buys the bandwidth savings; putting judgment at the edge does. Whether it really performs on a Pi is the next question.
**Time:** Introduction, ~1.5 min
**Note:** "Sub-second" (diagram + scorecard) conflicts with measured Pi 4 LLM latency — see `docs/TALK2-HANDOFF-FROM-TALK1.md` §3.

### Slide 6 — "Does it actually work on a Pi?"
**Suggested Layout:** Section *(plate — teaser)*
**Core Message:** Performance on real Pi-class hardware is Talk 2's subject; this talk stays on framing.
**On-Screen Text:**
```
Does it actually work on a Pi?
See Talk 2
The Greenest Token: a model evaluation & deployment methodology for edge execution engines
```
**Speaker Notes:** The obvious question after that promise: does any of this actually run on a Pi-class device? That answer, with real accuracy, latency and resource numbers from the Pi 4, is the subject of Talk 2, The Greenest Token. This talk stays on the problem and on how Pulsar Functions fit into the edge architecture.
**Time:** Introduction, ~0.5 min

### Slide 7 — "One Schema, Two Gates Before the LLM Ever Runs"
**Suggested Layout:** Content
**Core Message:** A single `TelemetryEvent` schema flows through cheap-math detection and a dedicated co-processor gate before an LLM sees anything.
**Visual Manifest:**
  - Type: Mermaid_Architecture
  - Spec: node/arrow linear-flow grammar, full content width: `TelemetryEvent` → `is_probable_slowdown()` → `TelemetryCoprocessorFunction` (magnitude gate + baseline severity) → `LlmTriageFunction` (raise/hold/lower).
**On-Screen Text:**
```
TelemetryEvent → is_probable_slowdown()
              → TelemetryCoprocessorFunction (gate)
              → LlmTriageFunction (raise/hold/lower)
```
**Speaker Notes:** Picking up from the edge-intelligence promise just shown — there's exactly one telemetry schema for the whole trilogy. The co-processor sits upstream of the LLM: it reuses the same cheap-math detection, applies a magnitude gate so trivial or already-catastrophic slowdowns never waste LLM compute, and computes a deterministic baseline severity before the LLM runs at all. The LLM's job is bounded from there — raise, hold, or lower that baseline using context a lookup table can't capture, never re-deriving severity from scratch. That bounded LLM role is the same shape the rest of the talk will stress-test on real edge hardware — starting with what actually runs this pipeline, next.
**Time:** Introduction, ~1.5 min

### Slide 8 — "What's a Pulsar Function?"
**Suggested Layout:** Content
**Core Message:** A Pulsar Function is a small class implementing `process(self, input, context)` — the same interface runs in a managed cluster or standalone on a single edge device.
**Visual Manifest:**
  - Type: Mermaid_Architecture
  - Spec: content column split top/bottom (diagram-then-code, no gradient-panel asymmetry): flow diagram `telemetry topic → EdgeEnrichmentFunction (process(input, context)) → output topic` with two small deployment-target tags branching off ("managed cluster" / "`localrun` on device"), then the code block below it.
**On-Screen Text:**
```
class EdgeEnrichmentFunction:
    def process(self, input, context) -> str | None:
```
**Speaker Notes:** Picking up from the pipeline just shown — a Pulsar Function matches a specific Python API, a class with `process(self, input, context)`. The exact same code runs today via `pulsar-admin functions localrun`, and later in managed mode, with no changes to the logic underneath. That portability is what makes the rest of this talk possible — including running unchanged on the actual target hardware, next.
**Time:** Introduction, ~1.5 min

### Slide 9 — "Why This Fits IoT Gateways and Pi's"
**Suggested Layout:** Content
**Core Message:** Because the real pipeline logic has no Pulsar import and no I/O, it deploys unchanged from a laptop to a Raspberry Pi at the edge — building directly on prior edge-ML-via-Pulsar-Functions work.
**Visual Manifest:**
  - Type: Mermaid_Architecture
  - Spec: vertical layered-node stack — `process_event` (pure logic, unit-tested with a mock backend) at the core, wrapped by either `pulsar_adapter.py` or `function.py`, deployed via `deploy/run_tier1_localrun.sh` onto a Pi-labeled node at the bottom.
**On-Screen Text:**
```
./deploy/run_tier1_localrun.sh pulsar://<broker-host>:6650
```
**Speaker Notes:** This is a natural extension of earlier talks on running ML models at the edge with Pulsar Functions. Cheap-math detection runs first and only gates the LLM step once a real anomaly is confirmed — so the constrained device's compute goes to the moments that actually need it. With the "what" and "why" established, here's what actually happened building it — starting with the plan as it looked on day one.
**Time:** Introduction, ~1.5 min

---

## Phase: Initial Compass — 3 min (2 slides)

### Slide 10 — "The Plan: 1-Bit, Zero GPU, One Truck"
**Suggested Layout:** Section *(plate — phase-opening beat)*
**Core Message:** The goal was a real 1-bit-class model running inline on a Pi, no GPU anywhere, validated on an M4 first.
**Visual Manifest:**
  - Type: Typography_Only
  - Spec: title + subtitle only, per the plate-type constraint — no content region on this slide.
**On-Screen Text:**
```
BitNet b1.58-2B-4T · bitnet.cpp fork · M4 → Pi 4
```
**Speaker Notes:** The plan was clean — a real 1-bit-class quantized model, hand-written 2-bit SIMD kernels, running inline on a Pi bolted to a truck, no GPU anywhere. Validate on an M4 first, before ever touching the target Pi 4. Getting there meant some custom machinery, which is worth a quick look before the story turns.
**Time:** Initial Compass, ~1.5 min

### Slide 11 — "The Fork's Custom Building Blocks"
**Suggested Layout:** Content *(not `Metric` — no produced number exists yet to pair with the code; see note above)*
**Core Message:** Getting there meant a custom tensor type and hand-written SIMD kernels, not stock llama.cpp.
**Visual Manifest:**
  - Type: Code_Block
  - Spec: single high-contrast Roboto Mono block, the fork's custom tensor type and its two kernel entry points, labeled "not in mainline" — no accompanying diagram.
**On-Screen Text:**
```
GGML_TYPE_I2_S
ggml_gemv_i2_i8_s / ggml_gemm_i2_i8_s
```
**Speaker Notes:** This isn't a config flag on top of mainline — it's a fork with its own tensor type and its own hand-written kernel implementations. That's the bespoke surface area the rest of this story runs into, starting with the build itself.
**Time:** Initial Compass, ~1.5 min

---

## Phase: Rough Terrain — 6 min (3 slides)

### Slide 12 — "Two Bugs, Fixed in a Few Lines"
**Suggested Layout:** Content
**Core Message:** The first wall wasn't the model — it was two real upstream build bugs.
**Visual Manifest:**
  - Type: Decision_Tree
  - Spec: two nodes stacked in the content column, each one bug — "Bug 1: symbol defined in one link target, called from another that never linked to it" / "Bug 2: identifier declared inside a dead `#if` block, never compiled in" — both tagged "fixed in a few lines," with the error line as a small code block beside them.
**On-Screen Text:**
```
error: use of undeclared identifier 'src1_cont'
```
**Speaker Notes:** The first wall isn't even the model, it's the build — a symbol defined in one link target and called from another that never linked to it, and an identifier declared inside a dead `#if` block that never got compiled in. Both fixed in a few lines. With the build fixed, here's what happened next.
**Time:** Rough Terrain, ~2 min

### Slide 13 — "It Builds. It Loads. It Runs."
**Suggested Layout:** Metric *(Code + KPI — a real produced number: ~5 tok/s)*
**Core Message:** Throughput looked completely believable — ~5 tokens/sec, exactly what you'd expect from a 2B model on CPU.
**Visual Manifest:**
  - Type: Code_Block
  - Spec: `.codeblock` (generation output) + `.kpi` stat/delta callout side by side — the codeblock is the terminal output, the KPI is the token rate, annotated "believable for a 2B model on CPU."
**On-Screen Text:**
```
~5 tokens/sec
```
**Speaker Notes:** With both bugs fixed, it builds, it loads, and it generates at roughly 5 tokens a second — a completely believable number. Nothing here looks wrong yet. That's exactly the problem.
**Time:** Rough Terrain, ~2 min

### Slide 14 — "Then: '@@@@@@@@,' Every Time"
**Suggested Layout:** Content *(not `Metric` — no real metric, just broken output)*
**Core Message:** Every generation, regardless of prompt, seed, or temperature, degenerates into the same repeated token.
**Visual Manifest:**
  - Type: Code_Block
  - Spec: single centered terminal-style block filled with the repeated character, annotated "same output regardless of prompt, seed, temperature."
**On-Screen Text:**
```
@@@@@@@@@@@@@@@@...
```
**Speaker Notes:** Then every generation, no matter the prompt, seed, or temperature, degenerates into the same repeated token. The believable token rate from the last slide was masking a completely broken output — that gap between "looks fine" and "is fine" is the whole next stretch of this story, which starts with ruling out the obvious suspects.
**Time:** Rough Terrain, ~2 min

---

## Phase: Hidden Valley — 4 min (2 slides)

### Slide 15 — "Ruling Out the Easy Answers"
**Suggested Layout:** Content
**Core Message:** Neither the AVX2 kernel path nor the sampler explains the garbage output — both were ruled out on purpose before trusting the wall.
**Visual Manifest:**
  - Type: Decision_Tree
  - Spec: two-branch diagram converging on one conclusion — `--no-repack` (scalar fallback) → "same garbage"; seed/temperature sweep → "same garbage"; both arrows meeting at "numerical bug in unexercised ARM kernels this project doesn't own upstream."
**On-Screen Text:**
```
--no-repack → same garbage
seed/temp sweep → same garbage
```
**Speaker Notes:** Coming off the previous slide's wall, rule out the obvious suspects on purpose before trusting it. Force the scalar fallback — same garbage, so it's not an AVX2-specific kernel bug, which doesn't even run on ARM anyway. Sweep seed and temperature — same garbage, so it's not a decoding fluke either. What's left is a numerical bug in hand-written, lightly-exercised ARM kernels this project doesn't own upstream — which is exactly what the next slide follows up on.
**Time:** Hidden Valley, ~2 min

### Slide 16 — "Mainline Can't Load It, and the Pi Doesn't Get a Pass"
**Suggested Layout:** Comparison *(literal two-column before/after — this profile's dedicated fit)*
**Core Message:** Mainline llama.cpp can't even load the same weights, and the real target — an older, narrower Pi 4 — was never going to fare better than the M4 that's already failing.
**Visual Manifest:**
  - Type: Bar_Comparison
  - Spec: `.col.before` (fork): "I2_S = slot 36," `.col.win` (mainline): "slot 36 = IQ4_NL_4_4 (REMOVED)" plus the M4-vs-Pi4 note "weaker hardware, not better" folded into the second column's body text.
**On-Screen Text:**
```
I2_S = slot 36 (fork)
slot 36 = IQ4_NL_4_4 (REMOVED)  (mainline)
```
**Speaker Notes:** Before dropping BitNet entirely, check whether mainline llama.cpp can just load the same weights. It can't — a GGML type-slot collision, and mainline's conversion script has never heard of a "bitnet" architecture at all. And the actual target hardware isn't even the M4 that's already failing — it's a Raspberry Pi 4, an older, narrower ARM core. If the newer chip can't get this right, there's no reason to expect the older one to. That's the pivot point — next up, what this actually cost to learn.
**Time:** Hidden Valley, ~2 min

---

## Phase: Hard-Won Map — 4 min (2 slides)

### Slide 17 — "What This Cost Us to Learn"
**Suggested Layout:** Section *(plate — phase-opening beat; the only other plate in this deck, isolated on both sides per the no-two-plates rule)*
**Core Message:** Four lessons, paid for in two failed debugging days — worth carrying into the next project before the runbook that follows.
**Visual Manifest:**
  - Type: Typography_Only
  - Spec: title + subtitle only.
**On-Screen Text:** *(none — title card)*
**Speaker Notes:** Out of everything the Hidden Valley section just showed, four things are worth taking with you. Here they are, together.
**Time:** Hard-Won Map, ~1.5 min

### Slide 18 — "Four Lessons"
**Suggested Layout:** Content *(no native 4-up grid type in this profile — `Three-up` is 3 cards only; four lessons are hand-built as a 2×2 card grid in the content column)*
**Core Message:** A clean build proves nothing about numeric correctness; rule out causes on purpose; the weaker target never gets a pass; mainline beats bespoke on a deadline.
**Visual Manifest:**
  - Type: Typography_Only
  - Spec: 2×2 grid of plain hairline-bordered cards, one lesson per cell — this replaces the earlier two-separate-lessons-slides split, which put two plate-type slides back to back; one content-bearing grid slide holds all four cleanly.
**On-Screen Text:**
```
• Clean build ≠ correct numerics on your hardware
• Rule out causes on purpose before trusting a wall
• The weaker target device never gets a pass
• Mainline beats bespoke on a deadline
```
**Speaker Notes:** A fork building clean and loading fast tells you nothing about whether its numeric path is correct on your hardware. Rule out causes on purpose before you trust a wall is real — the previous section did exactly that. Your weaker target device doesn't get a pass just because a stronger one might eventually work — if anything, it's the worse case, not a better one. And mainline, broadly-exercised support beats a novel, bespoke kernel every time your timeline doesn't allow for upstream-grade debugging. That's the map — now the actual blueprint that follows it.
**Time:** Hard-Won Map, ~2.5 min

---

## Phase: Blazed Trail — 13 min (6 slides)

### Slide 19 — "The Pivot: Small, Mainline, Quantized"
**Suggested Layout:** Comparison
**Core Message:** Swap the bespoke fork for small quantized instruct models running on mainline llama.cpp's broadly-exercised ARM path.
**Visual Manifest:**
  - Type: Bar_Comparison
  - Spec: `.col.before`: "OUT: bitnet.cpp fork + custom I2_S kernels," `.col.win`: "IN: mainline llama.cpp + Qwen2.5-1.5B / 0.5B, Q4_K_M."
**On-Screen Text:**
```
Qwen2.5-1.5B / 0.5B — Q4_K_M — mainline llama.cpp
```
**Speaker Notes:** Picking up from the blueprint just promised — the pivot is small quantized instruct models, Qwen2.5-1.5B and 0.5B, Q4_K_M, through mainline llama.cpp, which has broad, well-exercised ARM support. Here's the exact runbook that follows from it, step by step.
**Time:** Blazed Trail, ~2 min

### Slide 20 — "Step 1: Build Mainline for ARM"
**Suggested Layout:** Timeline *(step 1 of 4 — see runbook note above)*
**Core Message:** The entire build step is a plain CPU-only cmake build — no custom kernels to maintain.
**Visual Manifest:**
  - Type: Code_Block
  - Spec: `Timeline` 4-step rail (Build → Verify → Deploy → Decide) with step 1 active; detail region below holds a single centered terminal-style code block, nothing else.
**On-Screen Text:**
```
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release -j"$(nproc)"
```
**Speaker Notes:** Step one of the runbook: build mainline llama.cpp for ARM with a plain CPU-only cmake build. That's it — no fork-specific build system to fight. Before trusting anything this build produces, there's one gate to run first.
**Time:** Blazed Trail, ~2 min

### Slide 21 — "Step 2: One Coherence Check Before You Trust Any Benchmark"
**Suggested Layout:** Timeline *(step 2 of 4)*
**Core Message:** Run the same `@@@@`-style check first — if it fails here too, stop, don't trust the eval.
**Visual Manifest:**
  - Type: Decision_Tree
  - Spec: `Timeline` rail with step 2 active; detail region holds a small pass/fail branch node ("pass → continue to benchmark" / "fail → stop, don't trust eval," echoing the Rough Terrain failure mode from Slide 14), with the coherence-check command from `docs/PI4-RUNBOOK.md` above it.
**On-Screen Text:**
```
./build/bin/llama-completion \
  -m /mnt/ssd/models/Qwen2.5-0.5B-Instruct-GGUF/qwen2.5-0.5b-instruct-q4_k_m.gguf \
  -p "The capital of France is" -n 16 -no-cnv
```
**Speaker Notes:** Before trusting any benchmark, run one coherence check — same `@@@@`-style failure here means stop, don't trust the eval. This is the guard that would have caught the BitNet failure sooner if it had existed then. With that gate passed, the models themselves need to get onto the actual device.
**Time:** Blazed Trail, ~2 min

### Slide 22 — "Step 3: Get the Models Onto the Target"
**Suggested Layout:** Timeline *(step 3 of 4)*
**Core Message:** Pull both candidate GGUFs onto the Pi's SSD and point the manifest at them through environment variables.
**Visual Manifest:**
  - Type: Mermaid_Architecture
  - Spec: `Timeline` rail with step 3 active; detail region holds a node/arrow linear flow — two GGUF files → Pi SSD node → env-var arrow to a manifest node.
**On-Screen Text:**
```
LLM_BINARY_PATH / LLM_MODEL_PATH → Pi SSD
```
**Speaker Notes:** Step three: pull both candidate GGUFs onto the Pi's SSD, point the model manifest at those paths through environment variables. Now the exact same harness that ran on the M4 can run here, on the real target — and the artifact it produces is what actually decides things.
**Time:** Blazed Trail, ~2 min

### Slide 23 — "Step 4: The Artifact Decides Which Run Counts"
**Suggested Layout:** Timeline *(step 4 of 4 — closing the runbook rail; the M4-vs-Pi4 contrast lives in this step's detail region rather than promoting it to its own `Comparison` slide, so the 4-step rail stays intact through to the payoff)*
**Core Message:** The comparison artifact's own `decision_grade` field tells you which run actually counts.
**Visual Manifest:**
  - Type: Bar_Comparison
  - Spec: `Timeline` rail with step 4 active; detail region holds a compact two-column contrast — left "M4: `decision_grade: \"quality-only (non-target hardware)\"`," right "Pi 4: `decision_grade: \"full (Pi 4 target)\"`" — same harness, different lane label.
**On-Screen Text:**
```
make compare-models
decision_grade: "full (Pi 4 target)"
```
**Speaker Notes:** Run the exact same comparison harness that already ran on the M4 — and the artifact itself tells you which run actually counts. That's the blueprint, start to finish. What's left is proof it's real, not just a table of numbers.
**Time:** Blazed Trail, ~3 min

### Slide 24 — "See It Running, End-to-End"
**Suggested Layout:** Content
**Core Message:** This isn't a benchmark table — it's a real Pi console running the real pipeline against real telemetry.
**Visual Manifest:**
  - Type: `[NEEDS: new visual type not yet in the supported list — an embedded/played demo-recording visual; no current token (Mermaid_Architecture, Code_Block, etc.) covers a video capture, and this profile has no `Screenshot`-equivalent type either]`
  - Spec: the entry-point command shown as a code block; the demo itself is a Pi terminal running the command against a broker, `fleet-simulator` publishing on the laptop side, `enrichment-cards` output visible on the Pi's console as they're produced.
**On-Screen Text:**
```
./deploy/run_tier1_localrun.sh pulsar://<broker-host>:6650 ...
```
**Speaker Notes:** Everything up to now has been a number on a slide — this is the actual Pi, running the actual function, against actual telemetry, producing actual enrichment cards. `[NEEDS: the recording itself, plus confirmation of which broker placement — on-Pi or off-Pi, per deploy/README.md — was used for the take, so the narration matches what's on screen.]` From here, the last slide zooms out past this one truck.
**Time:** Blazed Trail, ~2 min

---

## Phase: Broader Horizon — 4 min (2 slides)

### Slide 25 — "The 'Now' State: The High-Cost Barrier to Consumer Adoption"
**Suggested Layout:** Comparison *(Now/Dream tab toggle)*
**Core Message:** Advanced vehicle intelligence is locked in luxury tiers today because it needs dedicated, expensive automotive compute.
**Visual Manifest:**
  - Type: Bar_Comparison
  - Spec: left: "The Cost Bottleneck of Luxury Hardware" + 3 bullets. Right: spec table, NVIDIA DRIVE Thor vs Tesla HW4 (AI inference, CPU, accelerator, RAM, power, cost), then 3 stat tiles: ~$3,000+ per vehicle · 140W+ power + liquid cooling · +$10,000 retail impact [NEEDS]. Source line under the table.
**On-Screen Text:**
```
• Prohibitive Unit Economics: Traditional edge intelligence requires dedicated silicon, adding thousands to bill-of-materials (BOM) costs.
• Ecosystem Isolation: Features are tied to the vehicle's manufacturing lifecycle, becoming obsolete within a few years.
• Luxury Gatekeeping: Advanced local diagnostics and safety features remain premium options, locked away from everyday drivers.

                 NVIDIA DRIVE Thor               Tesla HW4 [NEEDS: spec source]
AI inference     1,000–2,000 TOPS                500+ TOPS
CPU              12–14-core Arm Neoverse V3AE    20 Arm cores
Accelerator      Blackwell GPU + Tensor Cores    Dual custom NPUs
RAM              64–128GB LPDDR5X                32–64GB
Power            ~40–130W                        ~144W
Cost             $600–1,300 per chip (est.)      ~$3,640 service unit
```
**Speaker Notes:** Zoom out from fleets to consumer vehicles. Right now, if a car company wants to give a vehicle true local intelligence, it treats the car like a moving data center: dedicated automotive silicon like NVIDIA DRIVE Thor or Tesla's HW4 computer, thousands of dollars per vehicle, liquid cooling, and a large power budget. That keeps advanced local diagnostics and safety features locked in premium tiers.
**Time:** Broader Horizon, ~2 min

### Slide 26 — "The 'Dream' State: Mass Democratization via Handheld Hardware"
**Suggested Layout:** Comparison *(two cards + summary bar; Now/Dream tab toggle)*
**Core Message:** Shrinking the model footprint moves vehicle intelligence onto hardware drivers already own, or a sub-$100 plug-in node. Cost and specs only; no performance claims (those are in Talk 2).
**Visual Manifest:**
  - Type: Three-up *(two cards)*
  - Spec: card 1 "BYOD (Bring Your Own Device)", $0 incremental cost; card 2 "The Handheld Plug-and-Play Node", <$100 retail [NEEDS], with the reference line "Talk 1 test platform: Raspberry Pi 4 · 4-core Arm Cortex-A72 · 8GB RAM". Dark summary bar below.
**On-Screen Text:**
```
BYOD — $0 Incremental Cost — Running optimized 1-bit / small quantized LLMs directly on consumer mobile processors (e.g., standard smartphone NPUs). The phone interfaces with the car via Bluetooth or a cheap $15 OBD-II dongle. [NEEDS] Impact: Instantly turns 1.4 billion existing consumer cars into "smart edge" vehicles overnight. [NEEDS]
Handheld Plug-and-Play Node — <$100 Retail Cost [NEEDS] — A tiny, low-power standalone dongle powered by ultra-affordable chips (like a Raspberry Pi Zero or Pi 4 equivalent footprint) that plugs straight into the dashboard. Impact: Modest algorithmic efficiencies remove the need for fans, heavy wiring, or high battery drain.
Summary: By shifting intelligence from custom automotive silicon to 1-bit / small quantized models on handheld hardware, deployment cost drops by 97%+ while making edge safety accessible to 100% of drivers. [NEEDS]
```
**Speaker Notes:** The dream of democratization happens when we stop trying to change the car's hardware and instead change the software's footprint. Optimize the model down far enough and the compute requirement shrinks to something already in every driver's pocket, their phone, or to a small plug-in dongle in the Pi class. That's how edge intelligence moves from a luxury option toward a universal safety standard.
**Time:** Broader Horizon, ~2 min

---

## Slide 27 — "Thank You" (closing courtesy slide, outside the timed 40-min narrative)
**Suggested Layout:** Closing *(plate — deck-closing beat, one per deck)*
**Core Message:** *(none — courtesy/Q&A transition beat, not a narrative slide)*
**Visual Manifest:**
  - Type: Typography_Only
**On-Screen Text:**
```
Thank you
```
**Speaker Notes:** Transition to Q&A.
**Time:** 0 min (not part of the 40-min talk budget)

---

**Total: ~46 min across 26 timed slides (target: 40 min — `[NEEDS: ~6 min trimmed]`), plus 3 untimed courtesy slides (Waitroom, Title, Thank You).**
