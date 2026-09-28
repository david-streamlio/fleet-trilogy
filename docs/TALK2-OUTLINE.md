# Talk outline — "The Greenest Token": a model evaluation & deployment
# methodology for edge execution engines

**The thesis line (cold open and closer):**

> "I thought I was building a next-gen edge AI Pulsar function. I ended up
> building something way more important: an evaluation framework."

Everything in this talk is either setup for that line or payoff from it.
Say it once at the top as a promise, then don't explain it — let Act 2 (the
two walls) earn it, and say it again, now fully loaded, as the last line of
the talk. The fleet-telemetry pipeline (`talk1-edge-intelligence` →
`talk2-greenest-token` → `talk3-pulsar-speaks-english`) is the one worked
example carried end to end; it is not itself the subject — the methodology
is. Don't over-explain the thesis line when you first say it; the whole point
is the audience doesn't fully get it until Act 3.

Every beat below cites the artifact/doc that already backs it — this is drawn
from what's actually in the repo, not invented for the outline.

## Act 1 — The dream: a natural next step

- Prior work: hosting ML models inside Pulsar Functions in resource-constrained
  environments.
- The hook: 1-bit LLMs (BitNet) make "real LLM reasoning at the edge, inside a
  serverless function" look newly possible. Natural progression, not a
  left-field idea.
- Framing for the audience: this is a "let's just make it work" starting
  point — a how-to talk, at first.
- Backing: `talks/talk1-edge-intelligence/` — `function.py` is the literal
  Pulsar Functions wrapper (`process(self, input, context)`) around the
  cheap-math-gate + LLM-enrichment pipeline (`processor.py`).

## Act 2 — Two walls, same shape

**Wall 1 — BitNet garbage output on ARM.**
- Built `microsoft/BitNet` (bitnet.cpp) from source for Apple Silicon, fixed
  two real upstream bugs to get it compiling (undefined `dequantize_row_i2_s`/
  `quantize_i2_s` symbols; `src1_cont` scope bug).
- It loads, runs at a plausible ~5 tok/s — and every generation degenerates
  into `@@@@@@@@...` regardless of prompt/seed/temperature. Ruled out AVX2
  path and sampling artifacts specifically before stopping.
- Checked whether mainline llama.cpp could rescue the same weights: no — a
  tensor type-ID collision (slot 36 means `I2_S` in the fork, something else
  in mainline) and mainline has zero BitNet architecture support at all.
- The call: this is a go/no-go signal on the demo timeline, not a bug to chase
  blind inside unowned, lightly-exercised SIMD kernels.
- Pivot: mainline llama.cpp + small quantized instruct models (Qwen2.5-1.5B/
  0.5B, Q4_K_M).
- Backing: `docs/BITNET-POSTMORTEM.md` (full account, already talk-framed).

**Wall 2 — the 0.5B capability cliff.**
- Naive expectation: smaller model, same task, just slower accuracy dropoff.
- Actual Pi 4 decision-grade numbers (30 calls/model):
  | axis | 1.5B | 0.5B |
  |---|---|---|
  | format_parse_rate | 0.733 | **0.033** |
  | grounding_violation_rate | 0.000 | 0.200 |
  | tokens/sec | 1.71 | 4.04 |
- 1.5B's failures: near-miss formatting (prose wrapper, code fences,
  single-quoted lists) — fixable parser gaps, not comprehension failures.
- 0.5B's failures: degenerate repetition — echoing the prompt's own
  placeholder template, or looping the filled shape with fields scrambled,
  until the token cap. Not "close but malformed" — an instruction-following
  collapse. No parser fix recovers an answer that was never generated.
- The point for the talk: it's a cliff, not a slope. Don't smooth this into
  "small models are always fine."
- Backing: `docs/TALK2-0.5B-CAPABILITY-CLIFF.md`.

**The turn (end of Act 2):** two independent failures, same underlying
lesson — "does it work" isn't a yes/no question you answer once by trying a
model on your laptop. It's a question that needs a method, because the
failure modes are specific, varied, and easy to miss if you're only
eyeballing a few completions. This is the moment to callback the cold open,
half-loaded: *I set out to ship a function. What I actually needed first was
a way to know if any model deserved to be inside it.*

## Act 3 — Building the methodology

Present as a layered funnel, cheap checks first, each layer only evaluating
what survived the last — this mirrors the actual two-stage harness
(`docs/TALK2-MODEL-SPECTRUM-ACCURACY-PLAN.md`'s "M4 is a gate, not a
benchmark").

0. **Layer 0 — can it even run here? (before you spend a single eval cycle.)**
   Every layer below costs real compute: multi-GB downloads, dozens of real
   inference calls per model. That cost is wasted on a model that could never
   have shipped, for reasons no benchmark score would surface. Five checks,
   none of which require running the model:
   - *Does your runtime support the architecture at all?* Not a benchmark
     question — a yes/no gate. `microsoft/BitNet` loaded, ran, and produced
     fluent-*looking* tokens on Apple Silicon; even past the two real
     upstream kernel bugs that caused the garbage output, mainline
     llama.cpp has **zero** BitNet architecture support to fall back to.
     Backing: `docs/BITNET-POSTMORTEM.md`.
   - *Does a real, trustworthy quantized artifact actually exist?* A model
     card's claimed availability isn't the same as a real file. The
     official `meta-llama/Llama-3.1-8B-Instruct` repo has no GGUF files at
     all — the usable artifact is a third-party (unsloth) mirror's
     conversion. Qwen3.8-27B has no plain Q4_K_M file, only an Unsloth
     "Dynamic" quant. Ling-3.0-tiny's own 7.9B-total/1.3B-active parameter
     claim isn't independently confirmed anywhere on HF. Every
     `models.toml` entry carries a verified source link for exactly this
     reason — check the artifact, not the claim.
   - *Does the static footprint fit the device, with margin?* Arithmetic
     you can do before downloading anything: weights + KV cache + runtime
     overhead against the device's *actual* total RAM (Pi 4: 8GB, not "a
     Pi 4"). This manifest spans 0.34GB to 15.33GB of weights alone — most
     of that range was never a Pi 4 candidate on size alone, before any
     accuracy question gets asked.
   - *Can it survive sustained load on the real target, not just complete
     one call?* The sharpest, newest finding in this whole spectrum:
     Qwen3.8-27B is disqualified for confirmed Pi 4 thermal issues at its
     weight class — a fact no single-call latency number or M4 dev-machine
     reading would ever surface, and true regardless of how it scores on
     anything else. A model that completes a benchmark call fine can still
     be the wrong choice for a passively-cooled box running this
     continuously. Backing: `models.toml`'s `qwen3.8-27b-q4km` entry,
     `enabled = false`.
   - *Does it integrate with how you're actually invoking it?* Every
     `models.toml` entry carries `extra_args = ["-no-cnv"]` — disabling
     llama.cpp's automatic chat-template/conversation mode, because this
     harness's runtime-agnostic backend design needs raw completion, not a
     hidden template. Get this wrong and a perfectly capable model looks
     incompetent for reasons that have nothing to do with its judgment. If
     your pipeline depends on grammar-constrained output (Flow B does —
     `triage_function.py`'s `build_grammar`), the same question applies to
     grammar support: verify it against the real runtime's parser, don't
     assume spec compliance.
   - *(Not evidenced in this repo, but real and worth a line on stage:
     licensing/distribution terms for your actual deployment context — a
     gate that has nothing to do with technical capability at all.)*

   **The turn:** none of this requires a single inference call — it's the
   cheapest, highest-leverage filter in the whole funnel, and skipping it is
   how an eval budget gets spent benchmarking a model that could never have
   shipped. This is also the hinge into **harness design**: once a candidate
   list survives this filter, actually running the full comparison across
   it — many models, dozens of trials each, real subprocess calls — is
   itself expensive (the 15-model Flow B pass alone took 54 minutes of CPU
   wall time, with individual calls running up to 25 seconds), which is the
   case for the harness's *own* infrastructure needing a GPU-backed
   environment — separate from, and orthogonal to, whether the deployed
   model ends up running on GPU or CPU at the edge.

1. **Define the spectrum, not one model.** Axes that actually matter for this
   task/environment: quantization level, parameter count, model family,
   extreme-low-end (350M–0.6B) as an explicit boundary probe, not an
   afterthought. `models.toml` is this spectrum, already filtered through
   Layer 0 above.
2. **Derive ground truth from the task, not a generic benchmark.** The task
   here is narrow: classify severity, restate ETA impact faithfully, in valid
   JSON. A leaderboard score answers a different question than "can this
   model do *this* job." Ground truth comes from the fleet simulator's own
   known incident-ramp constants, not hand-labeling or an unrelated dataset.
3. **Layer 1 — format reliability.** Does it even produce parseable
   structured output? (Catches 0.5B outright.)
4. **Layer 2 — grounding.** Does it invent values, or faithfully copy
   `truck_id`/`corridor`/`eta_impact` from the input? (Catches confident
   hallucination that *would* parse fine.)
5. **Layer 3 — directional accuracy.** Sanity-check against simulator ground
   truth — and the honest caveat: this axis turned out to test the
   cheap-math pipeline's flag decision more than the LLM's own output
   (informational, not gating, once that was understood).
6. **Layer 4 — severity calibration (the new, deepest layer).** The real
   judgment test: does the model's severity call match the tier implied by
   the input's own `eta_slip_min`, using a transparent, documented threshold
   scheme tied to the simulator's ramp rate — not an arbitrary cutoff. Early
   smoke-test signal: a model can pass every check above and still call a
   `low`-tier input `high` — confidently wrong in the way that matters most
   for a dispatch decision. *(Once the full-spectrum `make compare-models`
   run finishes, this section gets real cross-model numbers — see Open Data
   below.)*
7. **Layer 5 — resource footprint, on the real target.** Latency/RAM/
   tokens-per-sec, gated on the actual execution engine (Pi 4 here), not the
   dev machine. `_decision_grade()`'s "full (Pi 4 target)" vs.
   "quality-only (non-target hardware)" split is the concrete mechanism.
- Backing: `tests/model/eval_lib.py`, `test_compare_models.py`,
  `docs/TALK2-MODEL-SPECTRUM-ACCURACY-PLAN.md`.

## Act 4 — Why this generalizes beyond one fleet demo

- Pulsar Functions here is a *concrete instance* of the real constraint: a
  lightweight, event-driven execution engine where you can't paper over a bad
  model choice with more compute.
- Same constraint, same method applies to: on-device/smartphone inference,
  other distributed edge topologies, any serverless/constrained host for a
  small model.
- The reusable artifact isn't "use Qwen2.5-1.5B" — it's the funnel itself:
  spectrum → task-derived ground truth → layered checks (format → grounding →
  task accuracy → calibration) → resource gate on the real target.
- Land "greenest token" with its sharpened meaning: not "smallest model," but
  "cheapest model that still passes a task-honest bar you can actually prove."
- **Closer — say the thesis line again, now fully loaded:** "I thought I was
  building a next-gen edge AI Pulsar function. I ended up building something
  way more important: an evaluation framework." The Pulsar function still
  ships — Talk 1 and Talk 3 prove it works end to end — but it's not the
  thing worth remembering. The methodology is what survives past this one
  fleet demo, onto the next model, the next execution engine, the next
  person's edge deployment.

## Real data: the full-spectrum run (2026-09-25, M4)

`eval-results/compare-COMP-J2D9D71YNJ-20260925T165011Z.json` — all 9
`models.toml` entries, 30 trials/model. This replaces the single-model
smoke-test anecdote in Layer 4 with real cross-model numbers, and the result
is a better talk beat than the clean "escalation gets worse as models shrink"
curve I'd guessed at:

| model | severity mismatch rate | format_parse_rate |
|---|---|---|
| Qwen3-8B | **42.9%** (best) | 1.0 |
| Ling-3.0-tiny (1.3B active) | 37.5% (n=8 parsed — small sample) | 0.4 |
| GLM-4-9B-0414 | 56.7% | 1.0 |
| Qwen3-0.6B | 61.5% | 1.0 |
| Qwen2.5-1.5B | 63.0% | 0.933 |
| Llama-3.1-8B | 73.3% | 0.933 |
| Qwen2.5-0.5B | 81.2% (worst, real sample) | 0.533 |
| LFM2.5-350M | no data | **0.0 — zero parseable cards** |
| Granite-4.0-H-350M | no data | **0.0 — zero parseable cards** |

**Two findings, and the second is the sharper one for the talk:**

1. Severity calibration does **not** track model size or family cleanly.
   Qwen3-8B leads; Qwen2.5-0.5B is worst among models that produced any
   output at all; there's no clean monotonic curve to point at. That's
   honest and worth saying plainly rather than forcing a trendline that
   isn't there.
2. **Every model that produced output mismatched severity on at least
   37% of trials — several over 60-80%.** This isn't "some models fail this
   check," it's "the check reveals a gap the whole current field of tested
   models has," which is a stronger argument for *why the framework matters*
   than a single bad model would be: without this axis, every one of these
   models would have looked equally fine on format + grounding alone.

**A third wall, distinct in shape from BitNet and 0.5B:** LFM2.5-350M and
Granite-4.0-H-350M didn't just perform badly on severity — they produced
*zero* parseable JSON across all 30 trials each. The raw completions show
the model echoing the prompt back near-verbatim (including the literal
`<event_name>`/`<low|medium|high>` placeholder shape) rather than attempting
an answer — not the same degenerate-repetition collapse 0.5B showed, and not
reproduced by Qwen3-0.6B under the identical `-no-cnv` invocation, so it's
specific to these two families, not a property of skipping the chat template
in general. Root cause not yet confirmed. Full account:
`docs/TALK2-350M-PROMPT-ECHO.md`.

This means the extreme-low end of the spectrum has **three differently
shaped walls** (BitNet's ARM numerical bug, 0.5B's degenerate repetition,
these two models' prompt-echo), each caught by the same layered funnel but
for completely different underlying reasons — a stronger illustration of
"you need the framework, not just a bigger model" than any single clean
cliff chart would be.

## Update — gate-2-confirmed result, and the field is eliminated to one (2026-09-25, 18:57 UTC)

**Superseded — kept for history, not current status.** This was a 9-model
snapshot under the original `severity_mismatch_rate` metric. Both the
candidate pool and the metric itself have since moved on: the pool widened to
14 candidates, and the architectural pivot that moved `severity`/
`recommended_action` to deterministic cheap math replaced
`severity_mismatch_rate` with `escalation-direction mismatch` as the gate
metric (Qwen3-8B is no longer "the one survivor" — it's one of a five-model
clean tier, all five with real Pi 4 numbers). See "Final model recommendation"
below for the current state, and `docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md`
rows 8-18 for the full run-by-run history in between.

The run above was a first pass — this is the same 9-model spectrum, same
harness, re-run under the v3 severity-threshold prompt with the harness's
gate-2 confirmation logic (`production_candidates` in
`tests/model/test_compare_models.py`: pass requires `format_parse_rate>=80%`
**and** a second, larger confirmation run holding `severity_mismatch_rate<=50%`).
Artifact: `eval-results/compare-COMP-J2D9D71YNJ-20260925T185711Z.json`.

**Exactly one of nine survives gate 2: Qwen3-8B (Q4_K_M)** —
`severity_mismatch_rate` 20.5% (n=88, gate-2 confirmed), a real improvement
over the 42.9% first-pass number above under the same model, attributable to
the v3 prompt's explicit severity-threshold wording. Every other candidate is
eliminated, for one of two distinct reasons — this is the sharper version of
the "not a clean curve" finding above, now with an explicit cut line instead
of a ranked list:

| model | verdict | reason |
|---|---|---|
| **Qwen3-8B (Q4_K_M)** | **PASS** | severity_mismatch 20.5% — the only model to clear gate 2 |
| Qwen2.5-1.5B-Instruct | reject | format_parse_rate 76.7% — never reached gate 2 |
| Qwen2.5-0.5B-Instruct | reject | format_parse_rate 56.7% — never reached gate 2 |
| Qwen3-0.6B (Q8_0) | reject | format_parse_rate 76.7% — never reached gate 2 |
| LFM2.5-350M (Q8_0) | reject | format_parse_rate 0% — zero parseable cards |
| Granite-4.0-H-350M (Q8_0) | reject | format_parse_rate 0% — zero parseable cards |
| Ling-3.0-tiny (7.9B-A1.3B) | reject | format_parse_rate 36.7% — never reached gate 2 |
| Llama-3.1-8B-Instruct | reject | severity_mismatch 50.6% — cleared gate 1, failed gate 2 |
| GLM-4-9B-0414 | reject | severity_mismatch 57.8% — cleared gate 1, failed gate 2 |

Note the shape of the field: five models never even reach gate 2 (format
parsing itself is the wall), and of the four that do, only one clears the
severity-calibration bar — Llama-3.1-8B and GLM-4-9B both parse perfectly
(96.7%/100%) and still get cut on judgment quality alone. That's the
strongest version yet of the talk's point: format/grounding checks alone
would have waved three of these four through.

**At the time, this did not pick a stage model on its own** — it was still a
quality-only run on non-target hardware (the M4), and Qwen3-8B still needed
the actual Pi 4 decision-grade run before its RAM/latency footprint on the
real target hardware was known. That run has since happened — not just for
Qwen3-8B, but for the full five-model clean tier the gate metric pivot later
produced (Qwen3-8B, Phi-3.5-mini-instruct, Gemma-3-4B-it, Llama-3.1-8B-Instruct,
GLM-4-9B-0414). The original framing's worry was correct in spirit, though:
an 8B model (or a 4B/9B one) is a meaningfully heavier Pi 4 footprint than the
1.5B/0.5B pair the original runbook was written for, and the "Final model
recommendation" section below is the resolution — the model that wins on one
task's accuracy is not necessarily the model the resource-budget framing
(Act 3, Slide 15: "small enough to share a Pi 4 with the function runtime")
was written expecting to win, and it isn't even the same model across this
talk's two LLM-driven tasks.

## Final model recommendation: two tasks, two different winners (2026-09-28)

The talk's Flow B (Tier 1 edge triage) and Tier 2 (talk3 spoken warning) gates
each converged to their own real Pi 4 decision-grade dataset (full detail:
`docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md` rows 8-23). Four models clear
*both* gates — Phi-3.5-mini-instruct, Gemma-3-4B-it, Llama-3.1-8B-Instruct,
GLM-4-9B-0414 — but the best model is not the same one for both tasks, and
the reason why is itself a talk beat, not just a footnote.

**Flow B (escalation decision) → Phi-3.5-mini-instruct:**

| Model | Mismatch | Pi p50 | Pi p95 | RAM |
|---|---|---|---|---|
| **Phi-3.5-mini-instruct** | 0.0% | **35.7s** | 157.8s | 7.11GB (93%) |
| Llama-3.1-8B-Instruct | 0.0% | 74.7s | 232.3s | 6.92GB (91%) |
| Gemma-3-4B-it | 2.2% | 77.1s | **101.4s** | 7.26GB (96%) |
| GLM-4-9B-0414 | 14.6% | 94.3s | 300.1s (pinned) | 6.81GB |

Ties for the best accuracy tier (0.0%, same as Llama and Qwen3-8B) and is
more than 2x faster at the median than the next-fastest tied model, on the
smallest model of the clean tier. Caveat worth stating on stage: Gemma-3-4B-it
actually has the better p95 (101.4s vs. 157.8s) despite a slightly worse mean
mismatch — a legitimate counter-argument if worst-case tail latency matters
more than typical-case for a real-time edge decision.

**Tier 2 (corridor paraphrase / spoken warning) → Gemma-3-4B-it:**

| Model | Ground/speak viol | Pi p50 | Pi p95 | RAM |
|---|---|---|---|---|
| **Gemma-3-4B-it** | 0.0% / 0.0% | **43.7s** | **119.3s** | 7049MB |
| GLM-4-9B-0414 | 0.0% / 0.0% | 57.6s | 179.5s | 6808MB |
| Llama-3.1-8B-Instruct | 0.0% / 0.0% | 147.9s | 238.8s | 6815MB |
| Phi-3.5-mini-instruct | 0.0% / 0.0% | 186.0s | 251.6s | 7171MB |

**This is the mirror image of the Flow B pick, and that's the real finding.**
Phi-3.5-mini-instruct — the Flow B winner — is the *slowest* of the four on
Tier 2 (4x Gemma-3-4B-it's median), because it burns most of its token budget
padding a "2-3 sentence" answer, while Gemma-3-4B-it is naturally terse here.
Same models, same Pi 4, same quantization scheme — the ranking flips entirely
between tasks. Root cause (real, not a hardware artifact — reproduces on the
M4 too): Flow B's prompt invites open-ended justification
(`risk_synthesis`), which Gemma-3-4B-it uses at length and Phi-3.5-mini
answers tersely; Tier 2's prompt explicitly bounds scope ("2-3 sentences"),
which Gemma-3-4B-it respects and Phi-3.5-mini doesn't. Full word-count
evidence: `docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md`'s "Cross-task latency
comparison" section.

**Talk beat this earns:** *the greenest model isn't a property of the model —
it's a property of the model or a given task.* A single "pick the best model"
slide would be actively wrong for one of these two tasks; the fact that the
same evaluation funnel, run twice, recommends two different models for two
adjacent tasks in the same pipeline is a stronger argument for the
methodology than either model's individual numbers.

**Worth a mention, not necessarily the headline:** GLM-4-9B-0414 is a close
second for Tier 2 (also 0%/0%, only ~14s slower at the median) and
Gemma-3-1B-it is a live alternative if RAM footprint outweighs raw speed —
1.5GB vs. Gemma-3-4B-it's 7GB (~4.6x smaller), at the cost of a non-zero 10%
grounding/3.3% speakability violation rate and a slightly slower median
(60.1s). Given this talk's efficiency framing, that tradeoff may be worth a
sentence even if Gemma-3-4B-it stays the headline pick.

## Not yet decided / needs your input

- Talk length/format (determines how much stage time Act 2's two postmortems
  get vs. Act 3's methodology walkthrough).
- Whether to do a live demo of the severity-calibration check catching a
  model in the act, or just present the chart.
- Exact closing slide for Act 4 — how far to reach into "smartphones/
  distributed AI" vs. keeping it to one forward-looking sentence.
