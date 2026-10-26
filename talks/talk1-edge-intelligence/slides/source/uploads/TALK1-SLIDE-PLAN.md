# Talk 1 — "Edge Intelligence" — Slide Plan

40-minute slot. 20 slides + 1 closing courtesy slide, ~2.0 min/slide average
across the 20 timed slides. Built from the Explorer's Journey narrative over
`docs/BITNET-POSTMORTEM.md` and `docs/PI4-RUNBOOK.md`, plus intro material
grounded in `docs/CANON.md`,
`shared/fleet-telemetry-model/src/fleet_telemetry_model/schemas.py`,
`talks/talk1-edge-intelligence/src/talk1_edge_intelligence/coprocessor.py`,
`triage_function.py`, and `deploy/README.md`.

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
— this plan's only two plates (Slides 5 and 12) are each isolated between
content-bearing slides.

**Where this plan deliberately does not follow the Content Affinity Map's
top-ranked match** — flagged per the accuracy guardrail rather than forcing
a slide shape that would need a fabricated number to fill it:
- The Content Affinity Map's top pick for `Code_Block` is `Metric` (Code +
  KPI), but `Metric` structurally needs a real produced number next to the
  code. Slides 6, 9, 15 show code/output with no accompanying measured
  metric at that point in the story (a custom kernel declaration, a garbage
  token stream, a build command) — forcing a KPI callout onto them would
  mean inventing a number. They use `Content` instead. Slide 8 *does* have
  a real number (`~5 tokens/sec`) and uses `Metric` as intended.
- Slides 15–18 ("Step 1" – "Step 4" of the pivot runbook) all use `Timeline`
  — not just the ones that read as a literal linear step — because they are,
  together, one numbered runbook sequence, which is exactly what this
  profile's `Timeline` type is built for. Each slide shows the same 4-step
  rail with its own step highlighted, so the audience always sees where
  they are in the runbook.

Two open items remain, flagged rather than fabricated — fill in before final
build. (A third, Slide 16's coherence-check command, is now resolved — see
below.)
- Slide 19 needs the actual demo recording. Broker placement is resolved —
  `deploy/README.md` documents "Broker OFF the Pi (default)," matching the
  `pulsar://<broker-host>:6650` command already on this slide — but no
  source gives the recording itself. Also: no native slide type or Visual
  Manifest `Type` in this system covers an embedded/played video, so it's
  built as `Content` with the entry-point command displayed and the
  recording flagged as missing, not faked as a static screenshot.
- Slide 20's RAM/compute figures for device classes other than the Pi 4.
  `docs/CANON.md` confirms the Pi 4 itself: **8GB RAM** — now used on that
  slide. Pi Zero / smartphone-tier / laptop-CPU figures aren't documented
  anywhere in this repo, so those three points on the spectrum stay flagged.

---

## Phase: Introduction — 8 min (4 slides)

### Slide 1 — "The Use Case: Truck 47, I-95N, One Kind of Incident"
**Suggested Layout:** Content
**Core Message:** The system exists to catch one specific anomaly — a SLOWDOWN — defined as three signals co-occurring, not any one alone.
**Visual Manifest:**
  - Type: Mermaid_Architecture
  - Spec: node/arrow convergence grammar built in the content column — three input nodes ("sustained ~35mph", "stop/go oscillation (brake/downshift events)", "slipping ETA") arrows converging into one node labeled "SLOWDOWN," captioned "any one alone is noise; the combination is the incident."
**On-Screen Text:**
```
SLOWDOWN = sustained ~35mph
         + stop/go oscillation
         + slipping ETA
```
**Speaker Notes:** The canonical use case is connected delivery fleet telemetry — canonical vehicle Truck 47, canonical corridor I-95N. A SLOWDOWN is the co-occurrence of sustained low speed, a stop/go oscillation (corroborated by real brake/downshift event counts, not speed alone), and a slipping ETA. Any one alone is noise; the combination is the incident. Everything else in this talk — every schema, every pipeline stage — exists to serve this one definition, starting with the schema itself on the next slide.
**Time:** Introduction, ~2 min

### Slide 2 — "One Schema, Two Gates Before the LLM Ever Runs"
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
**Speaker Notes:** Picking up from the SLOWDOWN definition just shown — there's exactly one telemetry schema for the whole trilogy. The co-processor sits upstream of the LLM: it reuses the same cheap-math detection, applies a magnitude gate so trivial or already-catastrophic slowdowns never waste LLM compute, and computes a deterministic baseline severity before the LLM runs at all. The LLM's job is bounded from there — raise, hold, or lower that baseline using context a lookup table can't capture, never re-deriving severity from scratch. That bounded LLM role is the same shape the rest of the talk will stress-test on real edge hardware — starting with what actually runs this pipeline, next.
**Time:** Introduction, ~2 min

### Slide 3 — "What's a Pulsar Function?"
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
**Time:** Introduction, ~2 min

### Slide 4 — "Why This Fits IoT Gateways and Pi's"
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
**Time:** Introduction, ~2 min

---

## Phase: Initial Compass — 3 min (2 slides)

### Slide 5 — "The Plan: 1-Bit, Zero GPU, One Truck"
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

### Slide 6 — "The Fork's Custom Building Blocks"
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

### Slide 7 — "Two Bugs, Fixed in a Few Lines"
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

### Slide 8 — "It Builds. It Loads. It Runs."
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

### Slide 9 — "Then: '@@@@@@@@,' Every Time"
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

### Slide 10 — "Ruling Out the Easy Answers"
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

### Slide 11 — "Mainline Can't Load It, and the Pi Doesn't Get a Pass"
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

### Slide 12 — "What This Cost Us to Learn"
**Suggested Layout:** Section *(plate — phase-opening beat; the only other plate in this deck, isolated on both sides per the no-two-plates rule)*
**Core Message:** Four lessons, paid for in two failed debugging days — worth carrying into the next project before the runbook that follows.
**Visual Manifest:**
  - Type: Typography_Only
  - Spec: title + subtitle only.
**On-Screen Text:** *(none — title card)*
**Speaker Notes:** Out of everything the Hidden Valley section just showed, four things are worth taking with you. Here they are, together.
**Time:** Hard-Won Map, ~1.5 min

### Slide 13 — "Four Lessons"
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

### Slide 14 — "The Pivot: Small, Mainline, Quantized"
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

### Slide 15 — "Step 1: Build Mainline for ARM"
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

### Slide 16 — "Step 2: One Coherence Check Before You Trust Any Benchmark"
**Suggested Layout:** Timeline *(step 2 of 4)*
**Core Message:** Run the same `@@@@`-style check first — if it fails here too, stop, don't trust the eval.
**Visual Manifest:**
  - Type: Decision_Tree
  - Spec: `Timeline` rail with step 2 active; detail region holds a small pass/fail branch node ("pass → continue to benchmark" / "fail → stop, don't trust eval," echoing the Rough Terrain failure mode from Slide 9), plus a `[NEEDS: ...]` note in place of the literal command.
**On-Screen Text:** `[NEEDS: exact coherence-check command — source notes refer to "the coherence-check command" without giving its literal text]`
**Speaker Notes:** Before trusting any benchmark, run one coherence check — same `@@@@`-style failure here means stop, don't trust the eval. This is the guard that would have caught the BitNet failure sooner if it had existed then. With that gate passed, the models themselves need to get onto the actual device.
**Time:** Blazed Trail, ~2 min

### Slide 17 — "Step 3: Get the Models Onto the Target"
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

### Slide 18 — "Step 4: The Artifact Decides Which Run Counts"
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

### Slide 19 — "See It Running, End-to-End"
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

## Phase: Broader Horizon — 2 min (1 slide)

### Slide 20 — "Same Approach, Any Constrained Device"
**Suggested Layout:** Content
**Core Message:** The mainline-plus-quantized-plus-coherence-check runbook isn't Pi-specific — it scales down toward phones and up toward any resource-constrained gateway.
**Visual Manifest:**
  - Type: Device_Spectrum
  - Spec: custom SVG axis (built in the content region, not a native chart type) — device class on the X-axis (e.g., Pi Zero, Pi 4, mid-range smartphone, laptop CPU, cloud GPU), RAM/compute headroom on the Y-axis, with Qwen2.5-0.5B/1.5B Q4_K_M's footprint marked to show where it comfortably fits.
**On-Screen Text:** `[NEEDS: RAM/compute figures per device class — Pi 4, Pi Zero, smartphone tier, etc. — to plot the spectrum accurately]`
**Speaker Notes:** Zooming out from the truck-and-Pi case that's carried the whole talk — the same small-quantized-model-on-mainline-runtime approach applies to any resource-constrained device across this spectrum, phones included.
**Time:** ~2 min

---

## Slide 21 — "Thank You" (closing courtesy slide, outside the timed 40-min narrative)
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

**Total: 40 min across 20 timed slides (target: 40 min), 2.0 min/slide average, plus 1 untimed closing slide.**
