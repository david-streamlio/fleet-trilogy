# Data engineering vs. model scale — impact track

**The claim this is building evidence for:** what you feed a model is itself a
lever on the "greenest token" efficiency question, not just an accuracy nicety —
sometimes the cheapest model that clears your bar isn't fixed by the model
spectrum alone; upstream data/interface engineering can move the bar itself,
more cheaply than reaching for a bigger model. Every entry below is a real
measurement against real models (see `docs/TALK2-MODEL-TESTING-CYCLE.svg`'s
diagnostic loop for the methodology each one followed), not a projection.

**The load-bearing nuance, refined across four rounds of real experiments:**
the effect is real but *conditional on which real signal you give, and to
which model* — not a universal law, and not even a stable per-model
capacity/categorical split. Velocity-deviation data helped only the two
smallest models and left Gemma-3-1B-it's "low" tier completely unmoved across
nine straight rounds, which looked like a clean "capacity vs. categorical
bias" story. Then brake-intensity data — a genuinely different kind of real
signal — moved Gemma's *medium* tier by 25 points with zero regression, the
first thing that reached it at all, while regressing a model
(LFM2.5-350M) the velocity fix had helped. Don't flatten this to "data
engineering fixes small models," and don't flatten it to "some models just
can't be helped" either — the honest version is sharper than both: **which
specific real signal helps which specific model is not reliably predictable
in advance, and has to be measured, not assumed, per model and per signal.**

---

## Confirmed

### 1. Grammar constraints — structural fix, near-universal within its scope

**Change:** GBNF grammar forcing valid JSON structure (`triage_function.build_grammar`),
replacing free-text generation.

**Impact:** models that were *completely non-functional* under free text became
fully functional under grammar — not incrementally better, unlocked entirely.

| Model | Free-text format-parse rate | Grammar-constrained format-parse rate |
|---|---|---|
| LFM2.5-350M | 0.000 (zero parseable cards, 30/30 trials) | 1.000 |
| Granite-4.0-H-350M | 0.000 | 0.833–1.000 |

**What this tells us:** grammar fixes *structure*, not *judgment* — these same
two models still needed the fixes below to make real severity-calibration
progress. Don't conflate "now it parses" with "now it's accurate."

### 2. Velocity deviation-from-plan — judgment fix, narrow but real

**Change:** `route_plans.py` + `coprocessor.velocity_context` — cheap math
computes `(actual speed vs. a real pre-seeded planned speed) → % deviation`,
and the model receives the already-computed fact ("39 mph observed is 13%
below plan") instead of two raw numbers to subtract itself.

**What was ruled out first** (6 negative rounds, before this worked): removing
signal names, an explicit qualitative assertion (caused a degenerate 100%
overcorrection on one model — see the warning below), missing units, a
mislabeled timestamp, and an extreme-minimal-magnitude control event. None of
these moved anything. Handing the model two *raw* numbers and letting it
compute the deviation itself also did nothing.

**Impact — low severity tier, correct-call rate:**

| Model | Size | Before | After (real deviation fact) |
|---|---|---|---|
| LFM2.5-350M | 0.35 GB | ~0% (0-1/20 across rounds) | 50–60% (10-12/20) |
| Qwen2.5-0.5B-Instruct | 0.46 GB | *not isolated pre-fix; aggregate mismatch was 67.8% (reject)* | 50% (10/20) |
| Gemma-3-1B-it | 0.75 GB | 0% | 0% — unmoved |
| **13 other models, 0.6B–9B** | — | 0% (assumed/measured "always medium or high") | 0% — unmoved, identical to before |

**The tell:** only the two *smallest* models in the entire 15-model manifest
improved. Everything from Qwen3-0.6B up through the 9B models — 13 of 15 — was
completely unmoved by a real, correctly-computed comparative fact. Average
improvement across the full spectrum: 7%.

**Warning example (what NOT to do):** an earlier attempt used a bare
qualitative assertion ("treat this as a borderline, low-magnitude case")
instead of a computed fact. It didn't move Gemma-3-1B-it at all, but it drove
LFM2.5-350M to a suspicious **100% "low"** — a degenerate overcorrection, not
genuine differentiated judgment (contrast with the real fact's 50-60%, which
produces a real mix of low/medium/high outputs). A prompt intervention that
looks like a win on a narrow check can be keyword-latching, not calibration.
Always check the full output distribution, not just the pass rate.

**Caveat on Gemma-3-1B-it specifically:** despite 0% correct "low" calls in
every round tested, its pre-fix *aggregate* Flow B severity mismatch rate was
47.8% — a gate-2 PASS. It compensates on medium/high tiers well enough that a
complete blind spot on one entire severity level doesn't show up in the
aggregate metric. Worth a line on stage: an aggregate calibration number can
hide a 100% failure on one dimension.

---

## In progress

### 3. SEVERITY RULE ENGINE wording

**Hypothesis:** the rule engine's own wording may make "medium" definitionally
true for *every* event that reaches the LLM, regardless of model — the medium
threshold ("noticeable corridor congestion, active delay accumulation") is
trivially satisfied by the mere fact of having been flagged by cheap-math
detection at all, while "low" requires the model to claim "no structural route
alterations required" for an event the system just escalated to it. This would
explain the near-universal 13/15 convergence on medium/high far better than a
per-model capability story would — it's a rule-engine design flaw, not a
capability gap, so it should affect every model family roughly equally
regardless of training.

**Test:** rewritten rule engine (reframes "low" as the expected, common case;
raises medium/high's bar above "was merely detected") against three
stuck-at-medium models (Phi-3.5-mini-instruct, Qwen3-8B, Llama-3.1-8B-Instruct)
plus Gemma-3-1B-it, with a regression check on the two models the velocity fix
already helped (LFM2.5-350M, Qwen2.5-0.5B-Instruct).

**Result (low tier only so far — medium/high verification pending, see caveat
below before trusting this): a dramatic, but not unambiguously clean, win.**

| Model | Old rule engine (low tier) | New rule engine (low tier) |
|---|---|---|
| Phi-3.5-mini-instruct | 0/20 (20/20 medium) | **20/20 low** |
| Qwen3-8B | 0/20 (20/20 medium) | **20/20 low** |
| Llama-3.1-8B-Instruct | 0/20 (20/20 medium) | **20/20 low** |
| Gemma-3-1B-it | 0/20 (19 medium, 1 high) | 0/20 (20/20 medium) — unmoved, still stuck |
| LFM2.5-350M | 14/20 (70%, already improved by fix #2) | 20/20 (100%) |
| Qwen2.5-0.5B-Instruct | 12/20 (60%, already improved by fix #2) | **0/20 (20/20 medium)** — regressed |

Three previously-100%-stuck big models flipped completely, which is strong
support for the hypothesis — this looks like a genuine rule-engine design
flaw, not a per-model capability gap, exactly because it moved three unrelated
model families identically. But two results demand caution before calling
this fixed:

1. **Qwen2.5-0.5B-Instruct regressed** from a real, differentiated 60% correct
   down to 0% — the longer, more nuanced new wording may be harder for a 0.5B
   model to actually follow, even though the same change helped much larger
   models. Not a free win across the spectrum.
2. **Every flip landed at a suspiciously clean 100%.** This experiment only
   tested the low tier. A rule-engine change that just makes every model say
   "low" for everything would look identical to a real fix at this point —
   the same *shape* of failure as round 4's bare "low-magnitude" assertion
   earlier in this investigation (that one was a single prompt-text nudge
   causing a degenerate 100%-low overcorrection, but on the low tier only,
   for one model, LFM2.5-350M — a different experiment, same failure
   pattern to watch for here at full-spectrum scale). Checking medium/high
   tiers on the three flipped models now, before this counts as confirmed.

**Result, medium/high verification (clean re-run, alone on the machine): mostly
confirms the overcorrection fear, not the fix.**

| Model | Low | Medium | High | Verdict |
|---|---|---|---|---|
| Phi-3.5-mini-instruct | 20/20 ✓ | 20/20 wrong (all "low") | 14 low + 6 medium, 0/20 correct | Collapsed to constant "low" |
| Qwen3-8B | 20/20 ✓ | 20/20 wrong | 20/20 wrong (even the most extreme case) | Complete collapse — says "low" unconditionally |
| LFM2.5-350M | 20/20 ✓ | 20/20 wrong | 20/20 wrong | Complete collapse, same shape as Qwen3-8B |
| **Llama-3.1-8B-Instruct** | 20/20 ✓ | 8/20 correct (40%) | **19/20 ✓ (95%)** | **Genuine, differentiated improvement** |

Three of the four models that looked "fixed" on the low-tier-only test are
actually just exhibiting a constant-output function that happens to match
"low" instead of "medium" — not real calibration. This is the SAME rule-engine
rewrite (reframing low as the common/default case, raising medium/high's bar)
tested across all three tiers, not round 4's assertion — but it's the same
*failure shape* round 4 first surfaced: a prompt-text change that nudges hard
enough toward "low" collapses judgment into a constant answer rather than
producing real calibration. Qwen3-8B and LFM2.5-350M now say "low" for every
input regardless of severity, including the single most extreme high-severity
case tested. That is not a fix by any definition.

**Llama-3.1-8B-Instruct is the one genuine exception** — 100%/40%/95% across
the three tiers is real, differentiated judgment, not a collapse. One
confirmed win out of four models, hidden inside what first looked like a
clean sweep across three.

**Revised verdict on the rule-engine wording hypothesis**: the underlying
diagnosis (the old wording made "medium" definitionally satisfied by mere
detection) may still be correct, but the fix as written overcorrected —
instead of producing balanced calibration, it just moved the same
keyword-latching failure mode to a different anchor word for most models. Only
one model in this small sample had enough capability to use the more nuanced
wording for actual reasoning rather than pattern-matching on "most flagged
events ARE low severity." This needs a less aggressive rewrite (raise
medium/high's bar without asserting "low is the common/default answer" so
strongly), not to be abandoned outright given Llama-3.1-8B's result — but it
is not ready to ship as-is.

**Separate, real methodology lesson from the invalidated first attempt at this
check**: running two ad-hoc diagnostic scripts concurrently exhausted this
machine's shared Metal/GPU memory and corrupted every trial in both runs. The
full `make compare-flow-b-models` harness already avoids this (one model
fully finishes before the next loads); hand-rolled diagnostic scripts don't
get that discipline for free and must be run one at a time.

### 4. Brake-intensity (deceleration magnitude)

**Change under test:** `brake_events` exists on `TelemetryEvent` today as a
bare count, and isn't even surfaced in the Flow B payload at all currently.
Tests whether adding a real, physically-grounded intensity signal — peak
deceleration in g-force, compared against a real industry-cited harsh-braking
threshold (~0.35g), the same measurement commercial fleet telematics systems
actually use — has the same kind of effect the velocity fix did. Explicitly
NOT a subjective 1-10 scale (see the conversation this doc is tracking: an
invented severity scale has no real-world anchor and reintroduces the
categorical-vagueness problem grammar and cheap-math fixes have been solving).

**Three conditions**, same models as the velocity fix (LFM2.5-350M,
Qwen2.5-0.5B-Instruct, Gemma-3-1B-it), all three severity tiers:
- A — baseline, no brake data (matches production today)
- B — bare count only ("3 brake events observed")
- C — precomputed magnitude fact ("3 brake events, peak 0.30g — 14% below the
  0.35g harsh-braking threshold")

**Result: not a clean win — a real regression, and a self-inflicted repeat of
an already-learned lesson.** Gemma-3-1B-it's numbers below are noisy (1-4/20
errors per cell from a GPU-memory collision with a concurrently-running
script, see above) and shouldn't be trusted yet; LFM2.5-350M and
Qwen2.5-0.5B-Instruct completed cleanly (0 errors) before that collision
started.

| Model | Tier | Baseline (A) | Precomputed fact (C) |
|---|---|---|---|
| LFM2.5-350M | low | 15/20 (75%) | **20/20 (100%)** |
| LFM2.5-350M | medium | 7/20 correct (35%) | **0/20 correct — 20/20 wrongly "low"** |
| LFM2.5-350M | high | 20/20 (100%) | 18/20 (90%) |
| Qwen2.5-0.5B-Instruct | low | 14/20 (70%) | 17/20 (85%) |
| Qwen2.5-0.5B-Instruct | medium | 4/20 correct (20%) | 2/20 correct (worse) |
| Qwen2.5-0.5B-Instruct | high | 4/20 correct (20%) | **0/20 correct** |

Low tier improved for both models. Medium and high got *worse*, sometimes
badly — LFM2.5-350M's medium-tier calibration collapsed entirely to "low".

**Hypothesized root cause (v1):** `HARSH_BRAKING_THRESHOLD_G = 0.35` put low
(0.15g) *and* medium (0.30g) on the same side of the threshold — both render
as "X% below the harsh-braking threshold," differing only in the percentage.
Looked like the identical failure shape as the original
`traffic_pattern_from_stop_go_index` bug from earlier this session (two tiers
sharing one categorical bucket). Redesigned with two thresholds carving three
genuinely separated bands (normal <0.20g / elevated 0.20-0.40g / harsh
>0.40g), each tier's value placed solidly inside its own band, and re-ran —
clean this time (0 GPU-memory errors, ran alone).

**v2 result: the shared-threshold theory was wrong, and the real finding is
more interesting than either version's headline number.** Net correct calls
across all three tiers (18 rows tested to /60):

| Model | Baseline (A) net | v2 fixed-threshold (C) net | Verdict |
|---|---|---|---|
| LFM2.5-350M | 42/60 (70%) | 39/60 (65%) | **Still a net regression** — medium still collapses to 0/20 "low", identical in degree to v1 despite the fixed threshold design |
| Qwen2.5-0.5B-Instruct | 22/60 (37%) | 24/60 (40%) | Roughly a wash — low much better, high worse |
| **Gemma-3-1B-it** | 28/60 (47%) | **34/60 (57%)** | **Real, non-degenerate improvement, no regressions** |

Giving medium a genuinely distinct third band ("elevated but not harsh
braking... between the thresholds") did NOT fix LFM2.5-350M's medium-tier
collapse — it's still 0/20 correct, all wrongly called "low", same as v1. Even
the bare-count-only condition shows the same pull (17/20 wrongly "low" on
medium). **My v1 root-cause theory (shared threshold side) is falsified by
this result** — something else about this specific model makes it default to
"low" whenever any "Braking Behavior:" line is present at all, regardless of
which band it names. Not yet understood; flagged as open, not chased further
given time already spent on this axis.

**The actual headline finding: Gemma-3-1B-it moved, for the first time in ten
rounds.** Every prior intervention — velocity deviation, signal-name removal,
units, timestamp, the rule-engine rewrite, an extreme-minimal-magnitude
control — left Gemma completely unmoved. Brake-intensity data didn't unlock
its low tier either (still 0/20, rock solid across all ten rounds now), but it
moved medium from 45% to 70% correct with zero regression anywhere else. That
reframes the earlier "Gemma has an intrinsic, unmovable bias" conclusion: the
bias on the *low* tier specifically may be genuinely intrinsic, but the model
is not uniformly unmovable — it just wasn't responsive to the *specific*
kinds of grounding fact tried before. A different real signal (braking
magnitude, not speed deviation) reached a different part of its judgment.

**Takeaway for the talk**: the same real, well-designed intervention can
regress one small model, roughly wash for a second, and produce a genuine win
for a third — including one that ten prior attempts couldn't move at all.
"Feed the model real data" is necessary but not sufficient; *which* real data
matters, and it's model-specific in ways that aren't obviously predictable in
advance. That's a sharper, more honest version of the correlation claim than
"data engineering helps smaller models" — it's closer to "data engineering
helps, unevenly, and you have to measure per-model, per-signal to know which
combinations work."

## 5. The architectural pivot: severity stops being an LLM output entirely

Every intervention above tried to make the LLM classify severity *better*. All of
them ran into the same ceiling: ten-plus rounds, mismatch rates from 33% to 73%,
degenerate constant-output collapses the norm. A round of external review
(Google AI, prompted for industry-grounded telemetry standards — see the
conversation this doc summarizes) converged, after two contradictory proposals and
one confirmed logic bug on Google's side, on the same conclusion this data was
already pointing to: **severity classification is a job for deterministic code, not
an LLM.** A corrected, hand-verified g-force/ABS/volatility matrix
(`severity_classifier.py`, adapted from industry-cited Class 8 truck harsh-braking
ranges) computes it perfectly, instantly, for free — something no model in this
whole investigation ever did reliably.

The LLM's job moved to what's actually left for it to do: given that deterministic
baseline plus genuinely unstructured operational context (weather, cargo type,
dispatch status — `trip_context.py`, none of which reduces to a threshold), decide
whether to **escalate**, **de-escalate**, or **confirm** it, and explain why
(`risk_synthesis`, `recommended_action`). `coprocessor.build_triage_payload` now
computes `baseline_severity` directly; `triage_function.apply_escalation` applies
the model's bounded decision to it in Python, never trusting the model to state a
severity value itself.

**A real bug found on the very first smoke test, before any diagnostic run**:
the initial grammar put `escalation` *before* `risk_synthesis` in the JSON field
order. Grammar-constrained decoding is strictly left-to-right, so field order is
reasoning order — the model had to commit to escalate/confirm/de-escalate before
it had generated the reasoning that would justify the choice. One smoke-test
completion showed `risk_synthesis` arguing clearly for escalation while
`escalation: "de_escalate"` was already locked in. Reordering the grammar
(reasoning fields first, decision last) is a real fix with no cost — a lesson
worth generalizing to any grammar-constrained multi-field output: put the
model's free reasoning before its constrained decision, not after.

**Diagnostic result after the reorder, three scenarios (escalate-worthy /
benign / de-escalate-worthy) x two models, N=15 each — mixed, and informative
in different ways per model:**

| Model | Escalation tracks scenario intent? | Internal self-consistency (escalation vs. recommended_action) |
|---|---|---|
| Gemma-3-1B-it | **Yes** — escalate-worthy 11/15 escalate, benign 6/15, de-escalate-worthy 3/15 escalate: a sensible, graduated ordering | **No** — every contradiction sample is the same pattern: `escalation: "de_escalate"` paired with `recommended_action: "escalate"`. Never picked "confirm" once across 45 trials — the same aversion to a neutral/passive answer found throughout this whole investigation's earlier "low" severity work, now showing up in a completely different task framing. |
| LFM2.5-350M | **No, inverted** — escalate-worthy got the *least* escalation (3/15), de-escalate-worthy got the *most* (9/15) — backwards from sensible judgment | **Yes** — 0 contradictions across 45 trials, but never picked "de_escalate" once (opposite avoidance pattern from Gemma) |

Reordering the grammar was a real, no-cost fix, but didn't fully solve
consistency — Gemma still contradicts itself in a specific, diagnosable way
(one field defaults toward "escalate"-flavored language independent of the
actual decision).

**Vocabulary-rename attempt ("de_escalate"/"escalate"/"confirm" →
"raise"/"lower"/"hold"), tested and disproven.** Hypothesis: the word
"de_escalate" *contains* "escalate" as a substring, priming the model to
write "escalate" into `recommended_action` regardless of its actual decision.
Renamed to a vocabulary with zero shared substrings/letters between any pair,
across the grammar, `apply_escalation`, prompt guidance, and every test. The
identical contradiction shape reappeared unchanged (`escalation: "lower"`
paired with `recommended_action: "raise"`, 13/15 and 6/15 across two
scenarios for Gemma), **and** the rename shifted both models' overall
escalation distributions unpredictably on top of not fixing anything — Gemma
went to 100% "lower" for the escalate-worthy scenario (backwards from its
previous correct-direction behavior), and LFM2.5-350M nearly stopped using
"raise" at all. A real, humbling result: the mechanism is not substring
priming. It looks like a generic "recommend escalating when in doubt" prior
in the free-text field, independent of the specific words used or the
model's own preceding structured decision.

**Actual fix: make `recommended_action` deterministic, not model output at
all.** Rather than keep guessing at wording, `recommended_action` is now a
template lookup keyed on `escalation` (`RECOMMENDED_ACTIONS` in
`triage_function.py`), computed in Python after generation. This removes the
contradiction by construction — verified at runtime in the diagnostic below
(`recommended_action_matches_template=True` on every single scenario/model
cell, 90/90 trials). The model's only remaining free-text output is
`risk_synthesis`.

**Immediate side effect, caught before it shipped: a token-budget
truncation regression.** Re-running the diagnostic after this change showed
Gemma-3-1B-it failing 13/15, 13/15, and 15/15 trials (near-total ERROR rates)
— `risk_synthesis`, now the model's *only* free-text field, runs longer
(~100+ words) than the old three-field shape did, and `DEFAULT_MAX_TOKENS=150`
(already fixed once earlier in this project for a different reason) was too
tight again. Confirmed via a controlled A/B before touching the fix: 150
tokens → 8/10 failures, 300 tokens → 0/10 failures on the same real prompt.
Fixed by raising `DEFAULT_MAX_TOKENS` to 300. Re-running the diagnostic
confirms the fix: zero ERROR trials across both models and all three
scenarios (90/90 clean).

**With truncation fixed and `recommended_action` fully deterministic, the
real question is finally answerable on clean data — and the answer is worse
than before, not better.** Two things break down independently, for both
models:

1. **`escalation` itself doesn't track scenario intent — for either model,
   it points in the wrong direction on two of three scenarios.**

   | Model | escalate-worthy (should raise) | benign (should hold) | de-escalate-worthy (should hold/lower) |
   |---|---|---|---|
   | Gemma-3-1B-it | 3/15 raise (**under-escalates**) | 14/15 hold (correct) | 13/15 raise (**inverted — wrong direction**) |
   | LFM2.5-350M | 3/15 raise (**under-escalates**) | 9/15 hold, 3 lower, 3 raise | 11/15 raise (**inverted — wrong direction**) |

   Both models are directionally backwards on the scenario built to warrant
   de-escalation — a documented defensive maneuver, empty non-hazardous
   trailer, ahead of schedule gets *raised* most of the time, not held or
   lowered. Neither model reliably raises on the scenario built to warrant
   it either. The only scenario either model gets right is the neutral
   "benign" one, which a model that always answers "hold" would also get
   right by default.

2. **`risk_synthesis` frequently contradicts the model's own `escalation`
   value it's supposed to justify** — the exact contradiction problem the
   `recommended_action` fix was meant to solve, resurfacing in the one field
   left uncontrolled:

   | Model | escalate-worthy | benign | de-escalate-worthy |
   |---|---|---|---|
   | Gemma-3-1B-it | 11/15 CONTRADICTS (73%) | 14/15 CONTRADICTS (93%) | 2/15 CONTRADICTS (agrees, but on the wrong decision) |
   | LFM2.5-350M | 9/15 CONTRADICTS (60%) | 4/15 CONTRADICTS (27%) | 5/15 CONTRADICTS (33%) |

   Gemma's benign-scenario contradictions are the starkest example: 14/15
   times it outputs `escalation: "hold"` while `risk_synthesis` argues in
   plain language that risk is significantly elevated and "demands a higher
   level of scrutiny." The free-text field appears to carry a strong,
   scenario-independent prior toward escalate-flavored language, largely
   decoupled from the structured decision it sits next to in the same
   completion — grammar's left-to-right field ordering controls *sequence*,
   not actual coupling between reasoning and decision.

**What this does and doesn't resolve**: severity itself is now completely
solved — zero model dependency, perfect reliability, by construction, and
`recommended_action` is now equally solved by the same move. The escalation
task this was supposed to replace it with — bounded, context-driven, meant to
play to what small LLMs are supposedly good at — is not holding up under
clean measurement. This is a harder result than "needs prompt refinement":
both models tested get the direction backwards on the scenario most likely
to matter operationally (a genuine hazard being explained away by good
conditions elsewhere), which is the risk profile you'd least want a false
negative on.

**One more prompt iteration, tried and re-measured: fixes two failure modes,
opens a third, and reproduces the exact overcorrection shape section 3
already documented.** Rewrote `DEFAULT_PROMPT_TEMPLATE`'s guidance from one
worked example into explicit per-field rules (cargo/weather are risk
multipliers only under stated conditions; a documented defensive/evasive
maneuver is reassurance, not a risk signal; being ahead of/on schedule is
not a risk factor) plus an explicit instruction that `risk_synthesis` must
name the specific field(s) driving the decision and must agree with
`escalation`. Removed the "baseline is reliable, do not re-derive it" line
that may have been an anchoring-toward-hold bias.

| Model | escalate-worthy | benign | de-escalate-worthy |
|---|---|---|---|
| Gemma-3-1B-it | **15/15 raise (100%, was 20%)** — fixed | 11/15 raise, 4/15 lower (was 14/15 hold correct) — **new regression, worse than before** | 9/15 lower, 5/15 raise, 1/15 hold (was 13/15 raise/inverted) — **direction fixed, not unanimous** |
| LFM2.5-350M | 14/15 raise (was 3/15) | 15/15 raise (was 9/15 hold-majority) | 14/15 raise (was 11/15 raise) | 

Gemma: two of three scenarios genuinely improved (escalate-worthy fully
fixed, de-escalate-worthy flipped from majority-wrong to majority-right), but
the previously-easy benign scenario collapsed from 93% correct (14/15 hold)
to 0% correct on the strict reading (0/15 hold — 11 raise, 4 lower). Sample
text shows the model literally misapplying its own rule —
"The weather is a significant risk multiplier due to the clear skies and dry
pavement" — inverting a rule stated in the prompt as its opposite, and
similar boilerplate reappears in the de-escalate-worthy contradiction samples
even when the structured decision is right. The generic "risk multiplier"
framing itself seems to have become a new template phrase the model
attaches to fields regardless of the direction its own rule dictates for
that value.

LFM2.5-350M collapsed completely: **constant "raise" across all three
scenarios, 43/45 trials** — the identical overcorrection shape as section
3's rule-engine rewrite (a longer, more rule-laden prompt that helped bigger
models collapsed a small model into a constant-output function). Worse, two
`risk_synthesis` samples aren't reasoning at all — the model echoed the
instruction template's own placeholder text back verbatim ("SPECIFIC
field(s) driving the decision, reason for raising or lowering, risk_synthesis
text"), a sign the ~250-word instruction block is past this model's ability
to actually follow rather than just pattern-match fragments of.

**Reinforces, rather than resolves, the open question**: making the
instruction more precise to fix one model's specific failure mode
(under/over-escalating) can simultaneously break a different failure mode on
the same model (benign case) and collapse a smaller model outright. This is
the third time this exact overcorrection shape has appeared in this document
(round 4's bare assertion, section 3's rule-engine rewrite, now this) — it
looks less like a fixable prompt-wording bug and more like a structural
property of pushing more rule-following load onto models this small.

**Decision: stop iterating on this prompt.** Three independent rounds
(round 4, section 3, this one) hitting the identical overcorrection shape —
sharper rules help a capable model on some axes while collapsing a smaller
one into a constant-output function, sometimes into literally echoing the
instruction text back — is itself the finding, not a signal that the next
wording attempt will be the one that works. The current prompt (this
section's rewrite) ships as-is: net better for Gemma-3-1B-it in aggregate
(56% vs. 42% direction-correct across the three scenarios, strict scoring),
roughly a wash for LFM2.5-350M in aggregate accuracy (33% vs. 36%) but
qualitatively worse — its outputs include verbatim echoes of the prompt's
own instruction text, which is a stronger red flag about whether it's
reasoning at all than any accuracy number captures. **The escalation task
remains an open, unresolved problem** — unlike severity and
`recommended_action`, it was not moved to cheap math this round, and is
flagged here as a known limitation of the current pipeline rather than a
solved one. The natural next move, if picked back up, is the same "move it
to cheap math" pattern already applied twice in this section — but that
was explicitly not pursued this round.

**Known gap — addressed (2026-09-26).** The pre-existing Flow B eval harness
(`eval_lib.py`'s severity-calibration machinery, `test_flow_b_triage.py`,
`test_compare_flow_b_models.py`, and every number in this document above
section 5) was built to test the *old* question — can the LLM classify
severity from eta_slip_min-driven tiers. Confirmed unrunnable, not just
stale: `flow_b_format_reliability` checked for `event_label`/`dispatch_action`,
fields that no longer exist on the card at all — running it unchanged would
have reported 0% format reliability for every model, a harness bug
masquerading as a universal model failure.

Redesigned rather than patched:

- `flow_b_format_reliability` now checks the current card shape
  (`baseline_severity`/`severity` legal values, `escalation` one of
  raise/hold/lower, `recommended_action` matches its deterministic template —
  a runtime check that the "always agrees by construction" claim actually
  holds, not just in unit tests — `risk_synthesis` non-empty, `eta_impact`/
  `truck_id` hardcoded-correct).
- `check_flow_b_severity_calibration` (severity vs. `eta_slip_min` tiers) is
  gone — severity no longer varies by model at all, so it couldn't
  discriminate between models even in principle. Replaced by
  `check_escalation_direction`: the same three operational-context scenarios
  (escalate-worthy / benign / de-escalate-worthy) this session's ad-hoc
  `diagnose_operational_risk.py` script already validated, formalized into
  the real harness via a new `run_flow_b_trials(..., contextual_trigger_overrides,
  baseline_severity_override)` mechanism that overrides the coprocessor's real
  payload post-hoc rather than needing fictional trip-context entries in
  production code.
- Gate 1/gate 2 structure preserved (format reliability at N, promotes to a
  bigger confirmatory escalation-direction run at `--model-confirm-multiplier`
  × N per scenario) — same two-stage shape as Flow A's
  `test_compare_models.py`, retargeted rather than removed.
- Smoke-tested against Gemma-3-1B-it (N=6) before the full run: 100% format
  reliability, 33% escalation-direction mismatch rate — consistent with this
  session's own ad-hoc diagnostic findings, not a new number invented for
  this fix.

**Full run, all 7 currently-enabled `models.toml` entries (2026-09-26 19:56 UTC,
`eval-results/compare-flow-b-COMP-J2D9D71YNJ-20260926T195623Z.json`, M4,
quality-only decision grade): a real, differentiated answer, not the near-
uniform collapse this document saw when the LLM was asked to classify
severity directly.**

| Model | format_parse_rate (gate 1) | escalation_mismatch_rate (gate 2, n=90) | Verdict |
|---|---|---|---|
| **Qwen3-8B** | 100% | **0.0%** | PASS — clean |
| **Phi-3.5-mini-instruct** | 100% | **0.0%** | PASS — clean |
| **Gemma-3-4B-it** | 100% | **0.0%** | PASS — clean |
| Llama-3.2-1B-Instruct | 100% | 37.8% | PASS — weak |
| Llama-3.2-3B-Instruct | 100% | 43.3% | PASS — weak |
| Qwen2.5-3B-Instruct | 100% | 50.0% | PASS — right at the bar |
| Gemma-3-1B-it | 100% | 51.1% | **reject** — just over the 50% bar |

All 7 clear gate 1 (structural format reliability) at a clean 100% — the
current schema (`baseline_severity`/`escalation`/`recommended_action`/
`risk_synthesis`) parses reliably across the whole spectrum tested. Gate 2
splits the field into three real bands: three models (Qwen3-8B,
Phi-3.5-mini-instruct, Gemma-3-4B-it) hit an exact 0% escalation-direction
mismatch — not just clearing a lenient 50% bar but a qualitatively clean
result — while the two smallest models tested (Llama-3.2-1B, Gemma-3-1B-it)
sit at the weak end, and Gemma-3-1B-it — the model every ad-hoc diagnostic
this session focused on — is the only one of the 7 that formally fails.

This is the first time in this entire document that the escalation/severity
task produced a genuinely clean pass for *any* model, let alone three. It's
consistent with, and sharpens, the pattern already established across every
earlier round here: the bounded escalation decision is reliable at
roughly-3B-and-up scale, and unreliable below it — Qwen2.5-3B-Instruct
landing exactly on the 50% line (not comfortably under it) is itself a data
point that "3B" isn't a clean cutoff, just a rough one.

---

## Running total (update as rounds land)

| # | Intervention | Models it helped | Models unmoved | Verdict |
|---|---|---|---|---|
| 1 | Grammar constraints | LFM2.5-350M, Granite-4.0-H-350M (structural) | — | Confirmed, near-universal for structure |
| 2 | Velocity deviation-from-plan | LFM2.5-350M, Qwen2.5-0.5B-Instruct | 13 of 15 models (0.6B-9B) | Confirmed, narrow — capacity-gated |
| 3 | Rule engine wording | **Llama-3.1-8B-Instruct only** (100%/40%/95% across tiers, genuine) | Phi-3.5-mini, Qwen3-8B, LFM2.5-350M (collapsed to constant "low"); Gemma-3-1B-it, Qwen2.5-0.5B-Instruct (unmoved/regressed) | Overcorrected — 1 real win, 3 new degenerate collapses, needs a less aggressive rewrite |
| 5 | Architectural pivot: severity + recommended_action to cheap math, LLM narrowed to bounded escalation | Severity, recommended_action: universal (both fully deterministic, zero model dependency, contradiction eliminated by construction). Real harness, full 7-model run: **Qwen3-8B, Phi-3.5-mini-instruct, Gemma-3-4B-it** at a clean 0% escalation-direction mismatch (gate 2, n=90) | Gemma-3-1B-it: 51.1% mismatch, the only one of 7 to fail gate 2; Llama-3.2-1B (37.8%) and Llama-3.2-3B (43.3%) pass but weakly | Severity + recommended_action: solved. Escalation quality: reliable at ~3B-and-up (three clean PASSes), unreliable below it — first genuinely clean pass for this task anywhere in this document |
| 4 | Brake intensity (v2, 3 separated bands) | **Gemma-3-1B-it** (net 47%→57%, no regressions — first win for this model in 10 rounds) | LFM2.5-350M (net regression, medium collapsed to "low"); Qwen2.5-0.5B-Instruct (net wash) | Mixed, model-specific — not universal, but the first real signal that reaches Gemma at all |
| 6 | Fixed the stale Flow B eval harness (event_label/dispatch_action/eta_slip_min-severity checks replaced with the current card shape + escalation-direction scenarios), then ran it for real | See row 5 — this is the harness that produced row 5's numbers | — | Confirmed the harness fix works: full 7-model run completed cleanly, 24.5 min, no errors |
