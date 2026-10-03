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
every round tested, its pre-fix *aggregate* Edge Triage Pipeline severity mismatch rate was
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
full `make compare-edge-triage-models` harness already avoids this (one model
fully finishes before the next loads); hand-rolled diagnostic scripts don't
get that discipline for free and must be run one at a time.

### 4. Brake-intensity (deceleration magnitude)

**Change under test:** `brake_events` exists on `TelemetryEvent` today as a
bare count, and isn't even surfaced in the Edge Triage Pipeline payload at all currently.
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

**Known gap — addressed (2026-09-26).** The pre-existing Edge Triage Pipeline eval harness
(`eval_lib.py`'s severity-calibration machinery, `test_edge_triage.py`,
`test_compare_edge_triage_models.py`, and every number in this document above
section 5) was built to test the *old* question — can the LLM classify
severity from eta_slip_min-driven tiers. Confirmed unrunnable, not just
stale: `edge_triage_format_reliability` checked for `event_label`/`dispatch_action`,
fields that no longer exist on the card at all — running it unchanged would
have reported 0% format reliability for every model, a harness bug
masquerading as a universal model failure.

Redesigned rather than patched:

- `edge_triage_format_reliability` now checks the current card shape
  (`baseline_severity`/`severity` legal values, `escalation` one of
  raise/hold/lower, `recommended_action` matches its deterministic template —
  a runtime check that the "always agrees by construction" claim actually
  holds, not just in unit tests — `risk_synthesis` non-empty, `eta_impact`/
  `truck_id` hardcoded-correct).
- The old severity-calibration check (severity vs. `eta_slip_min` tiers,
  removed in `ffe912c`) is gone — severity no longer varies by model at all, so it couldn't
  discriminate between models even in principle. Replaced by
  `check_escalation_direction`: the same three operational-context scenarios
  (escalate-worthy / benign / de-escalate-worthy) this session's ad-hoc
  `diagnose_operational_risk.py` script already validated, formalized into
  the real harness via a new `run_edge_triage_trials(..., contextual_trigger_overrides,
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
`eval-results/compare-edge-triage-COMP-J2D9D71YNJ-20260926T195623Z.json`, M4,
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

## Infrastructure fix: the M4 harness was reloading the model on every trial

Widening the Edge Triage Pipeline run to all 14 candidate models (M4 gate) surfaced a
problem that had nothing to do with model quality: it was running far slower
than the model spectrum alone predicted. Root-caused, not guessed at:

- `SubprocessLlmBackend.generate()` shells out to `llama-completion` (a
  one-shot CLI binary) fresh on **every single call** — `lsof` on a live
  process confirmed the Metal shader library gets re-mapped from disk on
  every subprocess launch. For a workload calling `generate()` ~120 times per
  model, that means reloading the full model weights and reinitializing the
  GPU backend 120 times per model.
- The file-based prompt cache (`--prompt-cache-ro /tmp/telemetry_base.cache`)
  had silently never worked at all: `-ro` never writes the cache file, and
  nothing in this pipeline ever ran a non-`-ro` pass to create it. `ls`
  confirmed the file didn't exist.
- `DEFAULT_THREADS=4` on a 16-core M4 (12 performance + 4 efficiency,
  confirmed via `sysctl`) left two-thirds of the performance cores idle.

Fix: added `LlmServerBackend` to `shared/llm-inference` — starts
`llama-server` (built fresh; the existing build had `LLAMA_BUILD_SERVER=OFF`)
once and keeps it running across every call, using its raw `/completion`
endpoint (not the OpenAI-compatible chat endpoint, which would silently
chat-template the prompt — verified live that `/completion` sends it
untouched, matching `-no-cnv`'s existing behavior byte-for-byte). This also
fixes the prompt cache for free: llama-server's internal slot cache reuses a
shared prompt prefix across HTTP requests automatically — verified live, a
second call sharing an 86/90-token prefix with the first dropped
prompt-processing time from 44ms to 3.6ms with zero extra code. Threads
raised to 12. `triage_function.py` switched from `SubprocessLlmBackend` to
`LlmServerBackend`; the eval harness now closes each model's server before
the manifest loop moves to the next one (skipping this would leave two
servers competing for the GPU at once — the exact contention this project
already hit and corrupted two earlier diagnostic runs).

**One real regression this surfaced and fixed along the way**: llama-server's
`stop` field excludes the matched text from the returned content (unlike
whatever `--reverse-prompt` did under the old CLI path) — passing
`stop=("}",)` alongside the grammar silently truncated the required closing
brace off every completion, a 0%-format-reliability failure, not a subtle
one. Fixed by dropping `stop` entirely: the grammar's root rule already ends
with a required `"}"` literal, and grammar-constrained decoding terminates
on its own once that's satisfied — no separate stop sequence was ever
necessary.

**Measured, validated speedup**: an 8-model run (including two 8B models,
Llama-3.1-8B-Instruct and Qwen3-8B) completed in 232.79s. The earlier
7-model run under the old architecture took 1471s (24.5 min) for a similar
model set — roughly a 6x speedup, with identical result shape (same models
landing at 0% escalation mismatch as before) confirming the backend swap
didn't change what's being measured, only how fast.

## Full M4 gate result: all 14 candidates (2026-09-26 21:52 UTC)

`eval-results/compare-edge-triage-COMP-J2D9D71YNJ-20260926T215201Z.json` — the
complete M4 sweep, all 14 non-thermally-excluded `models.toml` entries
(everything except Gemma-3-1B-it, already rejected in the fixed-harness run
above, and Qwen3.8-27B, excluded for confirmed Pi 4 thermal issues at its
weight class). 1492.70s wall time (~24.9 min) for all 14, on the fixed
`LlmServerBackend` architecture — for comparison, the *old* architecture took
24.5 min for 7 models; this run covered exactly double the model count in
about the same wall time.

| Model | format_parse_rate | escalation_mismatch_rate (n) | Verdict |
|---|---|---|---|
| **Qwen3-8B** | 1.000 | **0.0%** (90) | Clean PASS |
| **Phi-3.5-mini-instruct** | 1.000 | **0.0%** (90) | Clean PASS |
| **Gemma-3-4B-it** | 1.000 | **0.0%** (90) | Clean PASS |
| Llama-3.1-8B-Instruct | 1.000 | 5.6% (90) | Strong PASS |
| GLM-4-9B-0414 | 1.000 | 6.7% (90) | Strong PASS |
| Qwen2.5-0.5B-Instruct | 1.000 | 33.3% (90) | Weak PASS |
| Qwen2.5-1.5B-Instruct | 0.967 | 36.6% (82) | Weak PASS |
| Llama-3.2-1B-Instruct | 1.000 | 38.9% (90) | Weak PASS |
| Ling-3.0-tiny (7.9B-A1.3B) | 1.000 | 42.2% (90) | Weak PASS |
| Llama-3.2-3B-Instruct | 1.000 | 42.2% (90) | Weak PASS |
| Qwen2.5-3B-Instruct | 1.000 | 46.7% (90) | Weak PASS, right at the line |
| LFM2.5-350M | 1.000 | 64.4% (90) | **REJECT** |
| Qwen3-0.6B | 1.000 | 66.7% (90) | **REJECT** |
| Granite-4.0-H-350M | 1.000 | 66.7% (90) | **REJECT** |

**Headline findings for the talk:**

1. **Format reliability is a solved problem across the whole spectrum now** —
   13 of 14 models hit exactly 1.000, the one exception (Qwen2.5-1.5B,
   0.967) barely dented. This is a genuinely different picture from the old
   free-text Flow A results (`docs/TALK2-OUTLINE.md`'s gate-1 table, where
   five of nine models never even reached gate 2) — grammar-constrained
   decoding under the current schema is structurally reliable everywhere
   tested, model size and family stopped mattering for this axis entirely.
2. **A real, five-model top tier exists at ≤6.7% mismatch**: Qwen3-8B,
   Phi-3.5-mini-instruct, and Gemma-3-4B-it at an exact 0%, plus
   Llama-3.1-8B-Instruct (5.6%) and GLM-4-9B-0414 (6.7%). This is the richest
   "clean" candidate pool anywhere in this document — every earlier round
   found at most one or two genuine wins.
3. **11 of 14 clear the 50% bar; only the three smallest fail it** —
   Qwen3-0.6B, LFM2.5-350M, and Granite-4.0-H-350M (all ≤0.6B-class) are the
   only rejects, at 64-67% mismatch. The cutoff isn't clean by size alone
   though: Qwen2.5-0.5B-Instruct (also sub-1B) passes at 33.3%, better than
   several 1-3B models — size correlates with success on this task but
   doesn't determine it model-by-model.
4. **The RAM column in this artifact is not usable for comparison** — it's a
   cumulative session-wide high-water mark (documented in the harness's own
   `resident_ram_mb_note`), not per-model footprint. Actual RAM/latency
   comparison has to come from the Pi 4 decision-grade run, not this M4
   quality gate — exactly the two-stage funnel this whole project has been
   built around.

**What this changes about the stage-model pick**: before this session,
exactly one model (Qwen3-8B, Flow A) had ever cleared a gate-2-equivalent bar
in this entire project. There are now five real M4-cleared candidates for
the Edge Triage Pipeline specifically, spanning very different resource footprints (Phi-3.5-mini
~2.4GB weights vs. GLM-4-9B ~6.2GB) — the actual pick depends entirely on
which of these fit the Pi 4's real constraints, decided next.

## Pi 4 decision-grade run: two real findings before a single model passed

Kicked off the M4-cleared top tier (Qwen3-8B, Phi-3.5-mini-instruct,
Gemma-3-4B-it, Llama-3.1-8B-Instruct, GLM-4-9B-0414) sequentially on the real
Pi 4 target (8GB RAM, 4 cores, `edge-node00`), one model at a time. The first
model in the queue (Qwen3-8B) surfaced two real problems before producing a
usable result — one about the model, one about the eval code.

**1. Qwen3-8B failed gate 1 on the Pi — and thermal throttling is very
likely why.** 5 of 15 format-check trials hit the 300s timeout
("llama-server did not respond within 300.0s"), landing `format_parse_rate`
at 0.667 — below the 80% gate-1 bar, so gate 2 never ran. Checked the Pi's
actual thermal state mid-run (on the *next* queued model, Phi-3.5-mini,
since Qwen3-8B had already moved on): `vcgencmd measure_temp` read **83.7°C**,
`vcgencmd get_throttled` returned `0xe0006` — decoded, bits for "ARM
frequency capped" and "currently throttled" were both set **live, at read
time**, not just "has occurred since boot." `vcgencmd measure_clock arm`
confirmed it: **600MHz**, against the Pi 4's stock 1.5GHz — a 60% clock
reduction. This reframes something the project already believed: `models.toml`
attributes confirmed Pi 4 thermal issues specifically to Qwen3.8-27B's weight
class, as if smaller models were thermally fine. This reading says the Pi may
throttle under *any* sustained real-inference load on its current cooling
setup, not just the heaviest model — which means every Pi latency number
gathered anywhere in this project without also checking throttle state is a
number of unknown provenance: it might describe the Pi 4's real capability,
or a throttled fraction of it. Worth checking `get_throttled` on every future
Pi run, not just when something already looks slow.

**2. A real bug in the comparison harness, hit by this exact failure mode.**
`_build_recommendation` (in all three comparison harnesses —
`test_compare_models.py`, `test_compare_edge_triage_models.py`, and the new
`test_compare_tier2_models.py`) checked `if not axis["values"]:` to decide
whether an axis had any data. That's wrong when a single-model run's only
model fails to reach gate 2: `axis["values"]` is `{"model-id": None}` — a
non-empty dict, so the check passes through — and the code then does
`results[axis["best"]]` where `best` is `None` (since `_build_comparison`
only sets `best` when at least one *non-None* value exists), crashing with
`KeyError: None`. This is a real, pre-existing latent bug (not something this
session's changes introduced), just never triggered before because every
earlier run had at least one model clear gate 2. It crashed *before* the
JSON artifact gets written, so Qwen3-8B's Pi run produced no usable artifact
at all — the format_parse_rate/latency numbers above are recovered from the
pytest failure traceback's captured local variables, not a clean report.
Fixed (`if axis["best"] is None:` instead) and synced to the Pi before the
next queued model (Phi-3.5-mini) could hit the same crash.

**A live intervention, mid-session**: after the throttling reading above, a
fan was added directly to the Pi while Phi-3.5-mini's run was still actively
in progress (same sustained load, no pause — `llama-server`'s CPU time was
still climbing between readings, ruling out "it just went idle" as the
explanation).

| | Before fan | After fan |
|---|---|---|
| Temp | 83.7°C | 76.4°C |
| `get_throttled` live bits | Set (freq-capped + throttled, at read time) | Clear |
| ARM clock | 600MHz | 1800MHz (full boost) |

Two readings isn't a controlled study — temperature fluctuates on its own,
and this doesn't isolate the fan from other factors yet — but the clock
recovering from a 60%-reduced 600MHz to a full 1800MHz boost, on the
identical sustained workload, is a strong signal in the expected direction.
Worth tracking a real before/after series (several more readings on both
sides, same workload) rather than resting on two points, but this already
suggests the earlier throttling finding is a genuinely fixable cooling
problem, not an inherent Pi 4 ceiling.

**First complete Pi 4 decision-grade result: Phi-3.5-mini-instruct (2026-09-26
23:25 UTC, `eval-results/compare-edge-triage-edge-node00-20260926T232520Z.json`,
53min run, post-fan/post-bugfix).** This clears the actual first gate for
this talk track: does ANY LLM produce accurate results on the Pi 4, at all,
period. It does — 0.0% escalation mismatch, gate-2 confirmed, on the real
target hardware, identical to its M4 result.

| Axis | Value |
|---|---|
| format_parse_rate | 86.7% (clears gate 1) |
| escalation_mismatch_rate | **0.0%** (n=45, gate-2 confirmed — identical to its M4 result) |
| latency p50 | 35.7s |
| latency p95 | 157.8s |
| tokens/sec (approx) | 0.467 |
| resident RAM | 7.1GB of the Pi's 7.6GB total (93%) |

Latency/RAM are recorded for the talk's data set, not evaluated here —
resource-fit and optimization are a later pass, separate from this session's
actual bar (accuracy on the real target, period).

**Second Pi 4 decision-grade result: Gemma-3-4B-it (2026-09-27 00:47 UTC,
`eval-results/compare-edge-triage-edge-node00-20260927T004712Z.json`, 82min
run) — a second model clears the same bar.**

| Axis | Phi-3.5-mini-instruct | Gemma-3-4B-it |
|---|---|---|
| format_parse_rate | 86.7% | **100%** |
| escalation_mismatch_rate | 0.0% (n=45) | 2.2% (n=45) — both effectively clean |
| latency p50 | 35.7s | 77.1s |
| latency p95 | 157.8s | 101.4s |
| tokens/sec (approx) | 0.467 | 0.867 |
| resident RAM | 7.11GB (93%) | 7.26GB (96%) |

Two models now have real, accurate, gate-2-confirmed output running on the
actual Pi 4 target — the first-gate objective for this talk track, met
twice. Latency/RAM numbers are captured above for the talk's data set;
performance optimization is explicitly out of scope for this pass.

**Third Pi 4 decision-grade result: Llama-3.1-8B-Instruct (2026-09-27 02:18
UTC, `eval-results/compare-edge-triage-edge-node00-20260927T021819Z.json`, 91min
run) — a third model clears the same bar.**

| Axis | Value |
|---|---|
| format_parse_rate | 86.7% |
| escalation_mismatch_rate | **0.0%** (n=45, gate-2 confirmed) |
| latency p50 | 74.7s |
| latency p95 | 232.3s |
| tokens/sec (approx) | 0.499 |
| resident RAM | 6.92GB (91%) |

Three models now have real, accurate, gate-2-confirmed output on the actual
Pi 4 target: Phi-3.5-mini-instruct, Gemma-3-4B-it, Llama-3.1-8B-Instruct.
Latency/RAM captured for the data set, not evaluated here.

**Also decided mid-run**: Qwen3-8B's Pi failure (gate-1 timeout, likely
thermal per the finding above) gets a clean re-run, queued to fire
automatically after the remaining models (GLM-4-9B-0414, currently running)
finish — now that the fan is in and thermal is stable, it deserves a fair
result before being counted as a real rejection
rather than a measurement artifact.

**Decision-tree data point: for this stack, hardware changes speed, not
accuracy.** Same software (llama.cpp, GGUF Q4_K_M), same model, two
different machines (M4 Max MacBook vs. Pi 4) — three models now have both
readings:

| Model | M4 → Pi p50 latency ratio | M4 → Pi p95 latency ratio | Accuracy delta (Pi − M4) |
|---|---|---|---|
| Phi-3.5-mini-instruct | 47.5x slower | 199.0x slower | +0.0pp |
| Gemma-3-4B-it | 37.6x slower | 42.7x slower | +2.2pp |
| Llama-3.1-8B-Instruct | 59.9x slower | 109.5x slower | −5.6pp |

Latency dropped by 38-200x depending on model/percentile; accuracy moved by
at most 5.6 percentage points, in *both* directions, on `n=45-90` samples
small enough that this is plausibly sampling noise around a stable true
rate rather than a real hardware-driven effect. For the "when to use an LLM
on the edge" decision tree: moving the same model/quantization from a
Mac Studio-class M4 Max to a Pi 4 is a speed and resource-footprint decision,
not an accuracy one — at least for this stack, on the models tested so far.
Whether a *different* quantization scheme (e.g. MLX) would change the
accuracy side independently of hardware is a real, separate question, not
pursued further this round.

**Fourth Pi 4 decision-grade result: GLM-4-9B-0414 (2026-09-27 04:18 UTC,
`eval-results/compare-edge-triage-edge-node00-20260927T041805Z.json`, 120min
run).**

| Axis | Value |
|---|---|
| format_parse_rate | 86.7% |
| escalation_mismatch_rate | 14.6% (6/41) — concentrated entirely in the "benign" scenario (6/13 false-escalations: expected "hold", got "lower"/"raise") |
| latency p50 | 94.3s |
| latency p95 | 300.1s (pinned at the timeout ceiling) |
| resident RAM | 6.81GB |

Roughly double its M4 reading (6.7% mismatch there) on a modest sample
(n=41) — plausibly noise, but this is the first of the top-5 to show a real
gap between M4 and Pi quality rather than a near-identical number, so it's
flagged rather than assumed to be sampling variance.

**Fifth Pi 4 decision-grade result: Qwen3-8B — post-fan re-run closes out
the thermal question (2026-09-27 06:43 UTC,
`eval-results/compare-edge-triage-edge-node00-20260927T064341Z.json`, 145min
run).** This is the model that failed gate 1 on its first Pi attempt (rows 9/10
above) with the Pi running hot and throttled. Re-queued to run last, after
the fan fix had time to prove itself on every other model in the queue.
Result: format_parse_rate recovered from 66.7% to **86.7%**, and
escalation_mismatch_rate came back at a clean **0.0% (43/43)** — a full
pass, on the real target hardware. The original failure was thermal, not
the model, confirmed by a real re-run rather than inferred from the
temperature reading alone.

**Top-5 Pi 4 decision-grade summary — every M4-cleared Edge Triage Pipeline candidate now
has a real Pi 4 number:**

| Model | Format | Escalation mismatch | p50 | p95 | RAM after |
|---|---|---|---|---|---|
| Phi-3.5-mini-instruct | 86.7% | 0.0% | 35.7s | 157.8s | 7.11GB |
| Gemma-3-4B-it | 100.0% | 2.2% | 77.1s | 101.4s | 7.26GB |
| Llama-3.1-8B-Instruct | 86.7% | 0.0% | 74.7s | 232.3s | 6.92GB |
| GLM-4-9B-0414 | 86.7% | 14.6% | 94.3s | 300.1s | 6.81GB |
| Qwen3-8B (post-fan re-run) | 86.7% | 0.0% | 127.0s | 300.0s | 7.02GB |

RAM readings past the first model in a queued run are a floor, not a true
peak (`ru_maxrss` is cumulative for the whole process session — see the
harness's own `resident_ram_mb_note`). (Phi-3.5-mini's row is from a run that started on a
throttled, fanless Pi — kept as recorded; re-run and diagnosis in row 26 and "Cooling re-run"
below. The other four rows ran after the first fan was fitted.) Four of five hold 0-2.2% mismatch on
the real target hardware; GLM-4-9B is the one outlier at 14.6%. This is the
complete Tier 1 (Edge Triage Pipeline) Pi dataset for this project so far — the M4 gate
found a clean cliff at exactly these five models (0-6.7% mismatch there vs.
33%+ for every other candidate), so there is no larger list still waiting
on a Pi run.

---

## Tier 2 (talk3) corridor-omission prompt fix, validated at scale (n=30)

**The fix**: one line added to `SYNTHESIS_WARNING_PROMPT`
(`talks/talk3-pulsar-speaks-english/src/talk3_pulsar_speaks_english/prompting.py`):
"Always name the corridor explicitly in your warning ... — never omit it,
even when the situation seems minor." Deliberately framed as a narrow,
mechanical "always include this literal fact" instruction — contrast with
the Edge Triage Pipeline's escalation-task prompt tuning (row 3), which repeatedly asked
models to weigh multiple risk factors, not just state one fact, and kept
overcorrecting as a result.

**Full 15-model re-test, n=30 per model,
`eval-results/compare-tier2-COMP-J2D9D71YNJ-20260927T050845Z.json`, 826s run
— grounding-violation rate, pre-fix vs. post-fix:**

| Model | Pre-fix | Post-fix | Change |
|---|---|---|---|
| Llama-3.1-8B-Instruct | 20.0% | **0.0%** | improved |
| Qwen3-8B | 10.0% | 10.0% | unchanged |
| GLM-4-9B-0414 | 0.0% | 0.0% | unchanged |
| Gemma-3-1B-it | 70.0% | **10.0%** | improved — newly passes |
| Phi-3.5-mini-instruct | 0.0% | 10.0% | regressed |
| Gemma-3-4B-it | 0.0% | 0.0% | unchanged |
| Qwen2.5-1.5B-Instruct | 10.0% | **50.0%** | regressed sharply — newly rejects |
| Qwen2.5-3B-Instruct | 100.0% | 30.0% | improved substantially, still rejects |
| Llama-3.2-3B-Instruct | 70.0% | 30.0% | improved, still rejects on other axes |
| Qwen2.5-0.5B-Instruct | 70.0% | 70.0% | unchanged |
| Qwen3-0.6B | 70.0% | 70.0% | unchanged |
| Ling-3.0-tiny | 80.0% | 100.0% | regressed (already a clear reject on every axis) |
| Llama-3.2-1B-Instruct | 100.0% | 100.0% | unchanged |
| LFM2.5-350M | n/a (0% nonempty) | n/a (0% nonempty) | unchanged |
| Granite-4.0-H-350M | n/a (0% nonempty) | n/a (0% nonempty) | unchanged |

**Two regressions, both diagnosed by reading the actual flagged sample
text, not just trusting the percentage:**

1. **Phi-3.5-mini-instruct (0%→10%)**: hallucinates a specific *wrong*
   corridor ("I-10W" instead of the real "I-95N") in roughly 1 in 10 trials,
   rather than omitting it — arguably worse than omission (actively
   misleading vs. merely incomplete), though small enough the model still
   passes overall.
2. **Qwen2.5-1.5B-Instruct (10%→50%), a new finding**: not corridor
   omission — the model starts echoing prompt-template fragments verbatim
   instead of writing a warning (`"Reroute detail (already decided): none"`,
   `"Enrichment cards:"`, `"Affected trucks: 2"`), and in one trial parrots
   the new instruction sentence itself back as if it were the answer. This
   flips the model from PASS to REJECT. It's the same prompt-echo collapse
   pattern seen three times already in the Edge Triage Pipeline's escalation-task prompt
   tuning (row 3 and others) — except the trigger here was a purely
   mechanical "state this one literal fact" instruction, not a nuanced
   multi-factor judgment call, on a smaller model (1.5B) than any prior
   instance. Confirms the collapse pattern isn't specific to reasoning-heavy
   prompts — sharpening *any* instruction can tip a small enough model over.

**One genuine new pass**: Gemma-3-1B-it (70%→10%), verified against real
sample text — its two remaining violations are honest partial omissions
("The corridor is experiencing a slowdown..." never naming it), not echo
artifacts. Notably, this model *failed* the Edge Triage Pipeline's escalation gate (51.1%
mismatch — see its `models.toml` elimination note) but *passes* Tier 2's
simpler paraphrase task. The clearest evidence yet in this project that
task-appropriate model sizing is real: the same model is unusable for one
task and production-viable for another.

**Final validated Tier 2 (talk3) PASS list, n=30, post-fix**:
Llama-3.1-8B-Instruct (0%), Qwen3-8B (10%), GLM-4-9B-0414 (0%),
Gemma-3-1B-it (10%), Phi-3.5-mini-instruct (10%), Gemma-3-4B-it (0%) — six
models, now queued for their own Pi 4 decision-grade run. **Superseded
below**: the Pi run's own token-budget fix later exposed Qwen3-8B's PASS
here as an artifact of an overly generous max_tokens default (see "Pi 4
decision-grade run: Tier 2" and row 22) — corrected list is 5 models, not 6.

---

## Edge Triage Pipeline escalation failures split into two distinct archetypes, not one spectrum

Reading the full 15-model M4 Edge Triage Pipeline per-scenario breakdown (not just the
aggregate mismatch rate) side by side shows two genuinely different failure
shapes, not just "worse vs. better":

| Model | Mismatch | escalate-worthy | benign | de-escalate-worthy |
|---|---|---|---|---|
| Qwen3-8B / Phi-3.5-mini / Gemma-3-4B | 0.0% | 100% | 100% | 100% |
| Llama-3.1-8B-Instruct | 5.6% | 93.3% | 90.0% | 100% |
| GLM-4-9B-0414 | 6.7% | 100% | 80.0% | 100% |
| Qwen2.5-0.5B-Instruct | 33.3% | **0.0%** | 100% | 100% |
| Qwen2.5-1.5B-Instruct | 36.6% | 28.6% | 77.8% | 85.2% |
| Llama-3.2-1B-Instruct | 38.9% | **0.0%** | 83.3% | 100% |
| Ling-3.0-tiny | 42.2% | 16.7% | 56.7% | 100% |
| Llama-3.2-3B-Instruct | 42.2% | 73.3% | **0.0%** | 100% |
| Qwen2.5-3B-Instruct | 46.7% | 3.3% | 56.7% | 100% |
| Gemma-3-1B-it | 51.1% | 100% | **10.0%** | 36.7% |
| LFM2.5-350M | 64.4% | 100% | **0.0%** | 6.7% |
| Qwen3-0.6B | 66.7% | 100% | **0.0%** | **0.0%** |
| Granite-4.0-H-350M | 66.7% | 3.3% | **0.0%** | 96.7% |

**"Never raises" (Qwen2.5-0.5B, Llama-3.2-1B, Qwen2.5-3B, Granite-4.0-H, weakly
Ling-3.0-tiny)**: near-0% specifically on escalate-worthy, fine or good on the
calmer scenarios. **"Can't calm down" (Gemma-3-1B-it, LFM2.5-350M,
Qwen3-0.6B)**: perfect on escalate-worthy, collapse on benign and/or
de-escalate-worthy — they over-trigger. Llama-3.2-3B-Instruct is a third,
narrower shape (decent escalate-worthy, 0% benign specifically). This
distinction directly shaped which model got which intervention below.

## Two prompt-side accuracy interventions, round 2 — one archetype each, both real negative-or-mixed results

**RAG (query-dependent retrieval), targeting the "can't calm down" archetype
— Gemma-3-1B-it** (full raw result:
`eval-results/rag-edge-triage-gemma-3-1b-it-COMP-J2D9D71YNJ-20260927T201646Z.json`).
Built a held-out pool of 24 synthetic escalation
precedents (`tests/model/escalation_precedents.py`), embedded with
`sentence-transformers` (`all-MiniLM-L6-v2`, in-memory cosine similarity —
no vector DB, unnecessary at this corpus size), retrieved top-2 per query,
injected as a "similar past cases" block before the existing rule-based
prompt's `Decision:` section. Single variable isolated: same model, same 3
canonical scenarios, RAG on vs. off, n=90 each.

| | Baseline | RAG |
|---|---|---|
| Overall mismatch | 58.9% | 57.8% |
| Latency p50/p95 | 0.54s / 0.66s | 0.51s / 0.63s |

No detectable accuracy effect (1.1pp on n=90 is noise) and no detectable
latency effect on M4 (fast enough that the ~20% longer prompt doesn't
register). The one unambiguous, real cost: the embedder itself —
**4.91s one-time load, 531.9MB RSS** on a warm cache — paid for zero measured
benefit. Converges with row 3's earlier finding that Gemma-3-1B-it is
unmoved by rule-tightening too: two different intervention types, same
non-result, on the same model — real evidence it's capacity-gated for this
task, not technique-gated. (Latency conclusion is M4-specific; the Pi's much
lower CPU throughput could still show a real prefill tax from the longer
prompt that M4's headroom hides — not tested on the Pi.)

**Static (non-retrieved) few-shot, targeting the "never raises" archetype —
Qwen2.5-3B-Instruct and Qwen2.5-1.5B-Instruct** (full raw result:
`eval-results/static-fewshot-qwen2.5-COMP-J2D9D71YNJ-20260927T203806Z.json`).
Two fixed, moderate (not
cartoonishly extreme) worked examples baked into every prompt regardless of
scenario — isolates "do worked examples help at all" from RAG's retrieval
overhead. n=90 per condition per model, all three per-scenario rates
checked, not just the aggregate (row 3's own lesson: an aggregate
improvement can hide a benign/de-escalate collapse).

| Model | Scenario | Baseline | Few-shot |
|---|---|---|---|
| Qwen2.5-3B-Instruct | escalate-worthy | 3.3% | **100.0%** |
| Qwen2.5-3B-Instruct | benign | 46.7% | **3.3%** |
| Qwen2.5-3B-Instruct | de-escalate-worthy | 100.0% | **6.7%** |
| Qwen2.5-3B-Instruct | **overall mismatch** | 50.0% | **63.3% (worse)** |
| Qwen2.5-1.5B-Instruct | escalate-worthy | 20.7% | 86.2% |
| Qwen2.5-1.5B-Instruct | benign | 69.2% | 65.5% |
| Qwen2.5-1.5B-Instruct | de-escalate-worthy | 77.8% | 66.7% |
| Qwen2.5-1.5B-Instruct | **overall mismatch** | 45.1% | **27.3% (better)** |

Qwen2.5-3B-Instruct is a clean, textbook overcorrection: the two
"raise"-labeled examples didn't teach risk-trigger recognition, they pushed
the decision boundary toward raise across every scenario, moving it from the
"never raises" archetype into the "can't calm down" one — the aggregate
mismatch rate got *worse* despite the targeted scenario "fixing," which is
exactly why the per-scenario breakdown matters more than the headline number.
Qwen2.5-1.5B-Instruct shows a genuine net improvement, but a real portion of
it comes from trading away de-escalate-worthy accuracy (77.8%→66.7%), not
from getting more discriminating — the same mechanism at a smaller dose, not
a clean win.

**The generalized finding**: overcorrection isn't specific to explicit
rule-tightening (row 3) or to models that already over-trigger (Group 2). A
different intervention (biased worked examples) on a different failure
archetype (Group 1, "never raises") produced the same shape of failure. Any
prompt-side push toward one decision direction risks the same trade-off,
almost regardless of technique — a stronger, more general version of row 3's
original finding.

---

## Running total (update as rounds land)

| # | Intervention | Models it helped | Models unmoved | Verdict |
|---|---|---|---|---|
| 1 | Grammar constraints | LFM2.5-350M, Granite-4.0-H-350M (structural) | — | Confirmed, near-universal for structure |
| 2 | Velocity deviation-from-plan | LFM2.5-350M, Qwen2.5-0.5B-Instruct | 13 of 15 models (0.6B-9B) | Confirmed, narrow — capacity-gated |
| 3 | Rule engine wording | **Llama-3.1-8B-Instruct only** (100%/40%/95% across tiers, genuine) | Phi-3.5-mini, Qwen3-8B, LFM2.5-350M (collapsed to constant "low"); Gemma-3-1B-it, Qwen2.5-0.5B-Instruct (unmoved/regressed) | Overcorrected — 1 real win, 3 new degenerate collapses, needs a less aggressive rewrite |
| 5 | Architectural pivot: severity + recommended_action to cheap math, LLM narrowed to bounded escalation | Severity, recommended_action: universal (both fully deterministic, zero model dependency, contradiction eliminated by construction). Real harness, full 7-model run: **Qwen3-8B, Phi-3.5-mini-instruct, Gemma-3-4B-it** at a clean 0% escalation-direction mismatch (gate 2, n=90) | Gemma-3-1B-it: 51.1% mismatch, the only one of 7 to fail gate 2; Llama-3.2-1B (37.8%) and Llama-3.2-3B (43.3%) pass but weakly | Severity + recommended_action: solved. Escalation quality: reliable at ~3B-and-up (three clean PASSes), unreliable below it — first genuinely clean pass for this task anywhere in this document |
| 4 | Brake intensity (v2, 3 separated bands) | **Gemma-3-1B-it** (net 47%→57%, no regressions — first win for this model in 10 rounds) | LFM2.5-350M (net regression, medium collapsed to "low"); Qwen2.5-0.5B-Instruct (net wash) | Mixed, model-specific — not universal, but the first real signal that reaches Gemma at all |
| 6 | Fixed the stale Edge Triage Pipeline eval harness (event_label/dispatch_action/eta_slip_min-severity checks replaced with the current card shape + escalation-direction scenarios), then ran it for real | See row 5 — this is the harness that produced row 5's numbers | — | Confirmed the harness fix works: full 7-model run completed cleanly, 24.5 min, no errors |
| 7 | Infrastructure: SubprocessLlmBackend → LlmServerBackend (persistent server, 12 threads, working prompt cache) | All models — pure speedup, not an accuracy change | — | ~6x faster (232.79s for 8 models incl. two 8B, vs. 1471s for a similar 7-model set), identical result shape confirmed |
| 8 | Full M4 gate, all 14 candidates | **Qwen3-8B, Phi-3.5-mini-instruct, Gemma-3-4B-it** (0.0%); Llama-3.1-8B-Instruct (5.6%), GLM-4-9B-0414 (6.7%) — 5-model clean tier | Qwen3-0.6B, LFM2.5-350M, Granite-4.0-H-350M (64-67%, all ≤0.6B) | 11/14 pass the 50% bar; format reliability solved everywhere (13/14 at exactly 1.000); richest candidate pool in this whole project — next step is the Pi 4 decision-grade run |
| 9 | Pi 4 decision-grade run, Qwen3-8B (first of the top-5 queue) | — | Qwen3-8B: failed gate 1 on the Pi (0.667 format_parse_rate, 5/15 timeouts at 300s) | Not a model-quality finding — thermal throttling (see row 10) is the far more likely cause than the model itself |
| 10 | Pi 4 thermal throttling, discovered live mid-run | — | Confirmed: 83.7°C, `get_throttled` live bits set, ARM clock reduced to 600MHz (40% of stock) during sustained inference | Reframes `models.toml`'s "only Qwen3.8-27B has thermal issues" note — may be a property of sustained load on this Pi's cooling generally, not one model's weight class. A fan added mid-session (same sustained workload) brought it to 76.4°C, live throttle bits clear, clock back to full 1800MHz boost — encouraging but only 2 data points so far |
| 11 | Pi 4 decision-grade run, Phi-3.5-mini-instruct | **First gate cleared: accurate LLM output on the real Pi 4** (0.0% mismatch, identical to M4) | — | Latency (35.7s p50/157.8s p95) and RAM (93%) captured for the talk's data set; optimization out of scope for this pass. *(Kept as recorded — this run started on a throttled, fanless Pi; its 2026-10-02 re-run measured 31.7s/38.8s, 100% format. See row 26.)* |
| 12 | Pi 4 decision-grade run, Gemma-3-4B-it | Second model clears the same bar (2.2% mismatch, ~identical to M4's 0%) | — | Latency (77.1s p50/101.4s p95) and RAM (96%) captured; optimization out of scope for this pass |
| 13 | Pi 4 decision-grade run, Llama-3.1-8B-Instruct | Third model clears the same bar (0.0% mismatch, n=45, gate-2 confirmed) | — | Latency (74.7s p50/232.3s p95) and RAM (91%) captured; optimization out of scope for this pass |
| 14 | Tier 2 (talk3) harness bug: negation-blind grounding checks | Fixed both, verified against real output before trusting the numbers | — | Gemma-3-4B-it's "I-95 North" (natural paraphrase of "I-95N") and Qwen3-8B's "No reroute is recommended" (correct hold, contains the keyword "reroute") were both scored as violations by naive exact-string/keyword checks — same lesson as this whole project's "verify against real ground truth" discipline, applied to the eval harness's own code this time |
| 15 | Decision-tree data point: M4→Pi hardware swap, same stack | Accuracy stable across all 3 models tested (delta ≤5.6pp, plausibly noise) | — | Latency dropped 38-200x for the same models/quantization; hardware changes speed, not accuracy, for this stack — a real input to "when to use an LLM on the edge" |
| 16 | Full Tier 2 (talk3) comparison, all 15 candidates, post-grounding-fix | **GLM-4-9B-0414, Phi-3.5-mini-instruct, Gemma-3-4B-it** (0.0% grounding violation); Qwen3-8B, Qwen2.5-1.5B (10%); Llama-3.1-8B (20%) — 6-model pass tier, independent of the Edge Triage Pipeline's model selection per explicit instruction | LFM2.5-350M, Granite-4.0-H-350M (0% nonempty — same prompt-echo failure as earlier Flow A and Edge Triage Pipeline findings); Qwen2.5-0.5B, Qwen3-0.6B, Ling-3.0-tiny, Gemma-3-1B-it, Llama-3.2-1B/3B (all fail on real grounding, not the fixed bug); **Qwen2.5-3B-Instruct still 100% grounding-violation post-fix** | The grounding fix (row 14) is validated by scale: Gemma-3-4B-it went from 100%→0.0% violation between the 6-model pre-fix run and this 15-model post-fix run, confirming it was a harness bug. Tier 2's own pass list only partially overlaps the Edge Triage Pipeline's (Qwen2.5-1.5B-Instruct passes Tier 2 despite never reaching the Edge Triage Pipeline's gate 2) — confirms the two tasks genuinely test different skills, as intended |
| 17 | Qwen2.5-3B-Instruct's grounding failure, diagnosed | Confirmed real, not a harness artifact — read the actual flagged text | — | Systematically omits the corridor entirely in lower-stakes scenarios: 100% violation on single-truck, 50% on corridor-wide-no-reroute, **0% on corridor-wide-with-reroute**. Consistent pattern, not noise — the model trades completeness for brevity specifically when it judges the situation less severe, dropping "I-95N" from otherwise well-formed, speakable warnings. A real deployment concern if the spoken warning is meant to stand alone rather than supplement an already-corridor-scoped channel |
| 18 | Pi 4 decision-grade run, GLM-4-9B-0414 + Qwen3-8B post-fan re-run — completes the top-5 Edge Triage Pipeline Pi queue | All five M4-cleared candidates now have real Pi numbers; Qwen3-8B recovered from a 66.7% format_parse_rate (thermal, row 9/10) to 86.7% with a clean 0.0% mismatch (43/43) once the fan fix had time to prove out | GLM-4-9B: 14.6% mismatch on the Pi (vs. 6.7% on M4), concentrated entirely in the "benign" scenario (6/13 false-escalations) | Four of five hold 0-2.2% mismatch on real target hardware; GLM-4-9B is the one outlier, on a modest n=41 sample. Qwen3-8B's clean re-run confirms the thermal diagnosis was correct, not just plausible. This is the complete Tier 1 (Edge Triage Pipeline) Pi dataset — the M4 gate's clean cliff at exactly these 5 models means there's no larger list still owed a Pi run |
| 19 | Tier 2 (talk3) corridor-omission prompt fix ("always name the corridor" instruction), validated n=30 across all 15 candidates | Llama-3.1-8B-Instruct (20%→0%), Gemma-3-1B-it (70%→10%, newly passes), Qwen2.5-3B-Instruct (100%→30%, still rejects), Llama-3.2-3B-Instruct (70%→30%) | Phi-3.5-mini-instruct (0%→10%: new wrong-corridor hallucination, "I-10W" instead of "I-95N"); **Qwen2.5-1.5B-Instruct (10%→50%, newly rejects)**: not omission — a prompt-echo collapse, the model outputs copied template fragments ("Reroute detail (already decided): none", "Enrichment cards:") instead of a paraphrase | Net effect on the 6-model pass list is a lateral swap (Gemma-3-1B-it in, Qwen2.5-1.5B-Instruct out), not a net gain or loss. Confirms the prompt-echo overcorrection pattern (row 3) isn't specific to reasoning-heavy prompts — it also hit a purely mechanical "state this one fact" instruction, on a smaller model (1.5B) than any prior instance. Also the clearest task-appropriate-sizing evidence in this project: Gemma-3-1B-it fails the Edge Triage Pipeline's escalation gate (51.1% mismatch) but passes Tier 2's simpler paraphrase task outright |
| 20 | RAG (query-dependent precedent retrieval), targeting the "can't calm down" archetype — Gemma-3-1B-it | — | No detectable accuracy effect (58.9%→57.8% mismatch, n=90, within noise) or M4 latency effect (0.54s→0.51s p50) | Real, unambiguous cost with zero measured benefit: embedder load 4.91s + 531.9MB RSS. Converges with row 3: two different intervention types (rule-tightening, retrieval) both unmoved this model — real evidence it's capacity-gated for this task, not technique-gated. Latency conclusion is M4-only; not tested on the Pi, where lower CPU throughput could still show a real prefill tax |
| 21 | Static (non-retrieved) few-shot, targeting the "never raises" archetype — Qwen2.5-3B-Instruct and Qwen2.5-1.5B-Instruct | Qwen2.5-1.5B-Instruct: net improvement, 45.1%→27.3% mismatch (escalate-worthy 20.7%→86.2%) | **Qwen2.5-3B-Instruct got worse overall (50.0%→63.3% mismatch)**: escalate-worthy fixed (3.3%→100%) but benign (46.7%→3.3%) and de-escalate-worthy (100%→6.7%) collapsed — moved from "never raises" into "can't calm down." Qwen2.5-1.5B's improvement partly bought by trading away de-escalate-worthy (77.8%→66.7%) | Generalizes row 3's overcorrection finding beyond rule-tightening and beyond over-triggering models: biased worked examples produced the same failure shape on a different archetype. Checking all three per-scenario rates (not just the aggregate) is what caught this — the aggregate alone would have looked like a win for Qwen2.5-3B on the one scenario it targeted |
| 22 | Pi 4 decision-grade run, Tier 2 (talk3), all 6 M4-passing models | Gemma-3-1B-it, Phi-3.5-mini-instruct, Gemma-3-4B-it, GLM-4-9B-0414, and (after the max_tokens fix below) Llama-3.1-8B-Instruct all transfer cleanly from M4 to Pi | **Qwen3-8B**: initially collapsed to 10.0% nonempty on the Pi (256-token default, no stop sequence, ~555-560s needed at its measured throughput vs. the 300s budget). Fixed the timeout-wiring bug and the token budget (capped at 110, sized off `MAX_SPEAKABLE_WORDS`) — nonempty recovered to 100%, but structured_rate/speakability then revealed a genuine, hardware-independent problem: Qwen3-8B reasons out loud in raw-completion mode, and 110 tokens sometimes runs out before it reaches the JSON. Confirmed by re-running on M4 under the identical config (structured 90%→73.3%, speak_viol 10%→26.7%) — same direction on both hosts, so this is a real model/config interaction, not a Pi artifact | Two real bugs found and fixed en route: `--model-timeout-seconds` never wired into `run_tier2_trials` (hardcoded 180s default, invisible on M4, corrupted Phi-3.5-mini's first Pi attempt); then no grammar/stop-sequence on a task that only needs a short answer. Fixing the second bug's overly generous token budget is what *exposed* Qwen3-8B's real weakness — the original PASS was an artifact of budget slack, not evidence of quality. **Qwen3-8B removed from the Tier 2 PASS list** (now 5 models, not 6) |
| 23 | Cross-task latency comparison, Edge Triage Pipeline vs. Tier 2, the four models that pass both | Diagnosed the Pi latency swap between the two tasks (below) down to per-model output length, not throughput or hardware | — | Real, model-specific verbosity/task interaction: Phi-3.5-mini-instruct and Llama-3.1-8B-Instruct write far more text on Tier 2 than the Edge Triage Pipeline (and vice versa for Gemma-3-4B-it and GLM-4-9B-0414) — same pattern visible on M4, so not a Pi artifact |
| 24 | Real Pi 4 power measurement (inline USB-C meter, KWS-2303C), the two final picks on their own tasks (2026-10-02) | **Measured, not modelled:** idle 3.405 W / 3.401 W (two 10-min baselines, 0.1% apart); Phi-3.5-mini on the Edge Triage Pipeline (n=15 eval runs, 60 calls) **≈154 J/call** above idle; Gemma-3-4B-it on Tier 2 (n=30) **≈208 J/call** above idle | — | Pi draws ~7.3 W running inference vs. ~3.4 W idle — about half of every call's wall-socket energy is just keeping the board on. Mac M4 Max contrast (`powermetrics`, chip only, harness overhead included — an upper bound): ≈15 J and ≈23 J/call, ~10x less per call despite ~4x the power, because it's ~88x faster. Different classes of machine, not a fair benchmark. Detail: "Pi 4 power measurement" below |
| 25 | Cooling re-run: all five Edge Triage Pipeline candidates with a new external fan, same flags (2026-10-02/03) | Gemma-3-4B-it, Llama-3.1-8B, GLM-4-9B, Qwen3-8B latencies match their published (first-fan) runs within ~1-10%; quality within noise (Llama 0→2 of 45, GLM 6→3 of 41); all five still gate-2 PASS | — | Old fan vs. new fan changes almost nothing — both prevent the 600MHz hard throttle. The fan doesn't stop the 8-9B models touching the 80°C soft limit (5-9% of 30s trace samples, clock trimmed to ≥1580MHz). GLM's 7.3% now sits near its M4 6.7%, so its earlier Pi gap (14.6%) may not be a Pi effect — two runs can't say. Detail: "Cooling re-run" below |
| 26 | Phi-3.5-mini's published Pi run (row 11) diagnosed as throttle-affected | Re-run (2026-10-02, cooled Pi, external fan): **31.7s p50 / 38.8s p95, 100% format**, 0.0% mismatch (n=45) | — | Not a model change: the row 11 run started one second after a Qwen3-8B run had throttled the Pi to 600MHz (row 10), before any fan; the fan went in mid-run. Only its tail moved (p50 −11%, p95 157.8→38.8s) and its two format failures were empty outputs, consistent with 300s timeouts. Both runs kept; the re-run is the fair cross-model comparison (the other four never ran fanless) |
| 27 | Tier 2 `reroute_detail` overstated severity — a plain-code grounding bug the LLM narrated (2026-10-02) | Fixed in `synthesizer.decide_reroute` | — | Said "N trucks reporting a correlated high-severity slowdown" whenever ANY card was high; with 3 trucks (2 high, 1 medium) Gemma then said "three trucks are experiencing high-severity delays" aloud. Now "3 trucks reporting a correlated slowdown, 2 at high severity." Same lesson as row 14, from the other side: verify the facts code hands the model, not just the model |

---

## Pi 4 decision-grade run: Tier 2 (talk3), all 6 M4-passing models

Ran the validated 6-model Tier 2 PASS list on the real Pi 4 target, one
model at a time, n=30 (`pi_tier2_queue.sh` then `pi_tier2_queue_resume.sh` —
see the timeout bugfix below).

| Model | M4 nonempty/speak/ground | Pi nonempty/speak/ground | Pi p50/p95 | Pi tok/s | Pi RAM |
|---|---|---|---|---|---|
| Gemma-3-1B-it | 100%/3.3%/10.0% | 100%/3.3%/10.0% | 60.1s/82.4s | 1.865 | 1533MB |
| Phi-3.5-mini-instruct | 100%/0.0%/10.0% | 100%/0.0%/0.0% | 186.0s/251.6s | 0.450 | 7171MB |
| Gemma-3-4B-it | 100%/0.0%/0.0% | 100%/0.0%/0.0% | 43.7s/119.3s | 0.690 | 7049MB |
| GLM-4-9B-0414 | 100%/0.0%/0.0% | 100%/0.0%/0.0% | 57.6s/179.5s | 0.304 | 6808MB |
| **Qwen3-8B** | 100%/10.0%/10.0% | **10.0%**/0.0%/0.0% | 300.1s/300.1s | 0.461 | 6994MB |
| **Llama-3.1-8B-Instruct** | 100%/3.3%/0.0% | **6.7%**/0.0%/0.0% | 300.1s/300.1s | 0.455 | 6815MB |

(This table is the pre-fix snapshot, kept for the narrative below. Corrected
final numbers for the bottom two rows, after the max_tokens fix: see
"Fixed" further down — Llama-3.1-8B-Instruct→100%/100%/0.0%/0.0% on Pi,
clean; Qwen3-8B→100%/63.3%/36.7%/10.0% on Pi and a matching regression on
M4 under the identical config, now REJECTED from the PASS list.)

4 of 6 (Gemma-3-1B-it, Phi-3.5-mini, Gemma-3-4B-it, GLM-4-9B) transfer
cleanly from M4 to Pi — Gemma-3-1B-it's numbers are essentially identical on
both hosts.

**A real timeout-wiring bug, found and fixed mid-run**:
`test_compare_tier2_models.py::_run_one_model` read
`--model-timeout-seconds` from the CLI only to log it into the report's
`seed_config` — it never actually passed it to `run_tier2_trials`, which
silently used `tier2_eval_lib.py`'s hardcoded `DEFAULT_EVAL_TIMEOUT_SECONDS
= 180.0` regardless. Invisible on M4 (real latencies never approached 180s
there) but it corrupted Phi-3.5-mini-instruct's first Pi attempt (27/30
trials hit "did not respond within 180.0s", nonempty_rate=10.0%). Fixed
(wired the CLI option through), killed the corrupted run, and re-ran
everything after Gemma-3-1B-it (whose result stayed valid — its real
latencies never got near 180s either).

**A second real gap, found after the fix, not a bug in the fix**:
Qwen3-8B and Llama-3.1-8B-Instruct still collapsed to 10.0%/6.7% nonempty
on the Pi even with the timeout correctly set to 300s. Every error reads
exactly `"llama-server did not respond within 300.0s"` — real, not an
artifact. Root cause: unlike the Edge Triage Pipeline, **Tier 2's harness has no grammar and
no stop sequence** (`run_tier2_trials` builds a bare
`LlmGenerationConfig(timeout_seconds=...)`), so generation only ends when
the model naturally emits a stop token or hits the 256-token default cap.
At these two models' measured Pi throughput (~0.455-0.461 tok/s), reaching
256 tokens takes ~555-560s — almost double the 300s budget. GLM-4-9B is
*slower* per-token (0.304 tok/s) but finishes fine, meaning it reliably
stops itself well short of 256 tokens for this prompt; these two apparently
don't. This is a harness gap on a task that only ever needs a short answer,
not evidence the models can't do the task — both show 100% nonempty on M4.

**Fixed**: adding an actual `stop` sequence was considered and rejected —
llama-server excludes matched stop text from the returned content (the same
lesson `triage_function.py`'s grammar/stop interaction bug already taught
this project), and Tier 2 has no grammar to fall back on, so a stop match
would strip the JSON's closing brace and break parsing for every model, not
just these two. Capped `max_tokens=110` instead (`tier2_eval_lib.py`),
sized off `MAX_SPEAKABLE_WORDS`' own documented "generous ceiling" (70
words ≈ 100-101 tokens) plus JSON overhead. Re-ran both models on the Pi
under the fix, n=30 each:

| Model | Pi nonempty | Pi structured | Pi speak_viol | Pi ground_viol | Pi p50/p95 |
|---|---|---|---|---|---|
| Llama-3.1-8B-Instruct | **100.0%** | 100.0% | 0.0% | 0.0% | 147.9s/238.8s |
| Qwen3-8B | **100.0%** | 63.3% | 36.7% | 10.0% | 151.2s/244.6s |

---

## Cross-task latency comparison: Edge Triage Pipeline vs. Tier 2, same models, same hardware

The four models that clear both Pi 4 gates (Phi-3.5-mini-instruct,
Gemma-3-4B-it, Llama-3.1-8B-Instruct, GLM-4-9B-0414) show an unexpected
pattern when their Edge Triage Pipeline and Tier 2 Pi latencies are put side by side:
Phi-3.5-mini-instruct and Llama-3.1-8B-Instruct get markedly *slower* on
Tier 2 than the Edge Triage Pipeline, while Gemma-3-4B-it and GLM-4-9B-0414 get *faster*:

| Model | Edge Triage Pipeline Pi p50/p95 | Edge Triage Pipeline tok/s | Tier 2 Pi p50/p95 | Tier 2 tok/s |
|---|---|---|---|---|
| Phi-3.5-mini-instruct | 35.7s / 157.8s | 0.467 | 186.0s / 251.6s | 0.450 |
| Llama-3.1-8B-Instruct | 74.7s / 232.3s | 0.499 | 147.9s / 238.8s | ~0.455 |
| Gemma-3-4B-it | 77.1s / 101.4s | 0.867 | 43.7s / 119.3s | 0.690 |
| GLM-4-9B-0414 | 94.3s / 300.1s | not reported | 57.6s / 179.5s | 0.304 |

tok/s is roughly comparable per model across the two tasks, which rules out
a throughput explanation — the swap has to come from how much each model
*writes* per task, not how fast it writes. Since the Pi's raw completions
for these two tasks aren't committed to this repo (Pi-generated artifacts
live on the Pi, per this session's own convention), output length was
reconstructed from each model's own M4 run instead — same model, same
prompt, same sampling settings, so length is a model/task property, not a
hardware one, even though wall-clock isn't. Every M4 comparison artifact
already records `tokens_per_sec_approx` ("whitespace word count / latency"),
so inverting `tokens_per_sec_approx × p50_latency` recovers an approximate
word count per trial:

| Model | Edge Triage Pipeline words (M4, p50) | Tier 2 words (M4, p50, uncapped/pre-fix) | Tier 2 words (M4, p50, capped @110 tok) |
|---|---|---|---|
| Phi-3.5-mini-instruct | 18.6 | **114.9** | 47.6 |
| Llama-3.1-8B-Instruct | 37.6 | **154.5** | 70.0 |
| Gemma-3-4B-it | **71.9** | 32.5 | 33.0 |
| GLM-4-9B-0414 | **36.2** | 22.3 | — (never needed the cap) |

(Edge Triage Pipeline: `eval-results/compare-edge-triage-COMP-J2D9D71YNJ-20260926T215201Z.json`.
Tier 2 uncapped: `eval-results/compare-tier2-COMP-J2D9D71YNJ-20260927T050845Z.json`.
Tier 2 capped: `eval-results/compare-tier2-COMP-J2D9D71YNJ-20260928T151529Z.json`.)

The word counts flip in exactly the direction the Pi latencies did. Phi-3.5-mini
and Llama-3.1-8B are terse on the Edge Triage Pipeline (~19-38 words) but want to write
115-155 words on Tier 2 with nothing stopping them — that's why their
pre-fix Pi runs hit the 300s timeout ceiling (see the max_tokens fix above),
and why even after the 110-token cap they still use most of the budget
(47.6/70.0 words, 4-5x their Edge Triage Pipeline output). Gemma-3-4B-it and GLM-4-9B-0414
run the opposite way: verbose on the Edge Triage Pipeline's `risk_synthesis` field (32-72
words justifying the escalation decision) but naturally terse on Tier 2's
"2-3 sentence" paraphrase (~22-33 words), comfortably under any cap.

**Why the two tasks pull different models in different directions:**
The Edge Triage Pipeline's prompt (`triage_function.DEFAULT_PROMPT_TEMPLATE`) explicitly asks
the model to justify itself — "First write risk_synthesis: name the
SPECIFIC field(s) that drove your decision and why" — an open-ended
reasoning field whose *length* the GBNF grammar never constrains, only its
structure (`build_grammar`'s `[^"]*` term accepts any length). Gemma-3-4B-it
treats that as license to explain at length; Phi-3.5-mini and Llama-3.1-8B
answer it tersely. Tier 2's prompt
(`talk3_pulsar_speaks_english.prompting.SYNTHESIS_WARNING_PROMPT`) explicitly
bounds scope instead — "2-3 sentences," "your only job is to phrase the
warning" — and has no reasoning task and no grammar at all. GLM-4-9B and
Gemma-3-4B-it comply; Phi-3.5-mini and Llama-3.1-8B don't, padding well past
2-3 sentences (the same family of failure as Qwen3-8B's documented
reasoning-out-loud problem above, just verbose restating rather than
visible chain-of-thought). Neither harness uses a `stop` sequence for the
same documented reason (see the max_tokens fix above), so in both cases only
`max_tokens` or the model's own EOS choice ends generation — and which one
fires first is a model x task property this project doesn't otherwise
control for.

**Takeaway for the talk:** a model's per-task verbosity is not predictable
from its behavior on a different task, even a structurally similar one on
the same hardware — Gemma-3-4B-it and Phi-3.5-mini-instruct essentially trade
places between the two tasks. Any resource-budget story that treats "this
model's speed" as a single number, rather than a per-prompt property, would
be wrong for at least half of this project's own top-tier models.

The timeout collapse is gone for both — comfortably under the 300s budget
now. Llama-3.1-8B-Instruct is a clean win, matching its M4 quality exactly.

**Qwen3-8B surfaced a third, genuinely different finding — and it isn't a
Pi problem.** Its structured_rate dropped and speakability violations rose
even though nonempty is 100%. Reading the actual flagged text: Qwen3-8B
reasons out loud before answering ("Alright, let's see. The user wants a
proactive traffic warning...") — unsurprising in raw-completion mode with
no chat template to separate thinking from the final answer, but it means
a 110-token cap sized for the *answer* sometimes runs out before the model
ever reaches the JSON. Before trusting this as a Pi-specific artifact, this
project's own single-variable-isolation discipline required checking
whether it reproduces on M4 under the identical (new) config — it does:

| Model | Host | max_tokens | structured | speak_viol | ground_viol |
|---|---|---|---|---|---|
| Qwen3-8B | M4 | 256 (old) | 90.0% | 10.0% | 10.0% (PASS) |
| Qwen3-8B | M4 | 110 (new) | 73.3% | 26.7% | 0.0% (**REJECT**) |
| Qwen3-8B | Pi | 110 (new) | 63.3% | 36.7% | 10.0% (**REJECT**) |

(`eval-results/compare-tier2-COMP-J2D9D71YNJ-20260928T151529Z.json` for the
M4 110-token re-baseline.) Same direction, same magnitude, on both hosts —
this is a real model/config interaction, not hardware. The original PASS
for Qwen3-8B was itself an artifact of a token budget generous enough to
let it finish thinking out loud before running out of room; a budget sized
for what the Pi can actually afford exposes that it doesn't handle this
task as cleanly as the original number suggested. **Qwen3-8B is removed
from the Tier 2 PASS list** — the corrected list is Llama-3.1-8B-Instruct,
GLM-4-9B-0414, Gemma-3-1B-it, Phi-3.5-mini-instruct, Gemma-3-4B-it (5
models, not 6).


---

## Pi 4 power measurement: real energy per call (2026-10-02)

Row 24 in detail — the measurement `docs/TALK2-POWER-MEASUREMENT-PLAN.md`
planned, now done. A YEREADW/KOWSI **KWS-2303C** USB-C meter sits inline between
the wall supply and the Pi's USB-C power-in port (its **male end toward the
power source** — the manual's orientation). It's display-only: each window was
read by hand from one phone photo (accumulated mWh and elapsed time, read
together), with the counters zeroed by a 3-second button hold at the start.
Energy counts in whole mWh, time in whole seconds. Every window ran through
`/mnt/data/fleet-trilogy/pi_power_trial.sh` on the Pi, which logs Pi-side
timestamps and a 30s temperature/clock/throttle trace; all readings are in
`/mnt/data/fleet-trilogy/pi_power_trial.log`.

Energy above idle = `mWh × 3.6 − P_idle × meter_seconds`. The seconds between
the reset and the run's start, and between its end and the photo, are idle
time counted on both sides of that subtraction, so reading lag cancels.

| Window | Meter | Pi elapsed | Energy above idle | Per call |
|---|---|---|---|---|
| Idle baseline 1 (fan on, 39°C) | 680 mWh / 719 s → **3.405 W** | 600.0 s | — | — |
| **Phi-3.5-mini, Edge Triage Pipeline**, n=15 (60 calls) | 5212 mWh / 2803 s | 2362.8 s | 9,219 J | **≈154 J** (0.043 Wh) |
| Idle baseline 2 | 563 mWh / 596 s → **3.401 W** | 600.0 s | — | — |
| Gemma-3-4B-it, Tier 2, n=30 — first run (fan re-aimed 11 min in; 3/55 soft-limit samples) | 3360 mWh / 1662 s | 1625.1 s | 6,444 J | ≈215 J |
| **Gemma-3-4B-it, Tier 2, n=30 — clean re-run** (0/53 throttled) | 3266 mWh / 1619 s | 1570.7 s | 6,251 J | **≈208 J** (0.058 Wh) |

Artifacts (on the Pi, `eval-results/`): Phi `compare-edge-triage-edge-node00-20261002T222637Z.json`;
Gemma `compare-tier2-edge-node00-20261002T231503Z.json` (first) and
`…20261002T234456Z.json` (clean). Quality held throughout: Phi 100% format /
0.0% mismatch (n=45); Gemma 100% structured, 0% speakability and grounding
violations.

Cross-checks that held on every window: mWh ÷ mAh = 5.09–5.26 V average (the
supply's real range); meter seconds minus Pi seconds = 37–52 s of photo/reset
lag; the two idle baselines agree to 0.1%; the throttled first Gemma run lands
within 3% of the clean one. A 4-core CPU-only load (`yes` × 4) peaked at
6.17 W, but inference averaged 7.3–7.4 W — the extra watt is memory traffic,
which a pure-ALU load doesn't exercise. Excluded: a 3-call trial run used only
to validate the reading process (throttled for half of it; 280 J/call isn't a
result).

**Mac M4 Max contrast** (`sudo powermetrics --samplers cpu_power,gpu_power -i 1000`,
same two model/task pairs, same `--model-eval-runs`, 3 reps each):

| | Calls/rep | Avg chip power | Energy above idle / rep | Per call | Rep spread |
|---|---|---|---|---|---|
| Phi-3.5-mini, Edge Triage Pipeline | 60 | 30.8 W | 918.5 J | **≈15.3 J** | ±0.4% |
| Gemma-3-4B-it, Tier 2 | 30 | 39.4 W | 680.4 J | **≈22.7 J** | ±1.7% |

Mac idle chip power was 0.30 W, so idle subtraction changes these by ~1%.
Artifacts: `eval-results/compare-edge-triage-COMP-J2D9D71YNJ-20261002T213056Z.json`,
`…213226Z`, `…213355Z` and `compare-tier2-COMP-J2D9D71YNJ-20261002T213713Z.json`,
`…213830Z`, `…213948Z`. Two caveats, both favouring the Mac: `powermetrics`
measures the chip only (CPU+GPU+ANE — not DRAM, SSD, display or PSU losses),
while the Pi meter measures the whole board at the wall; and each Mac rep
includes harness startup and model load (~30% of a 30 s Phi rep, ~13% of a
Gemma rep), so these per-call figures are upper bounds.

**Reading these numbers — batch totals vs. per-call averages.** "Same
workload" means the identical batch on both machines: the same GGUF file, the
same harness (`test_compare_edge_triage_models.py` / `test_compare_tier2_models.py`),
the same prompts and scenarios, and the same `--model-eval-runs` — **60 model
calls** for Phi's Edge Triage batch, **30** for Gemma's Tier 2 batch — each batch
including its own startup, model load and teardown. What differs is the machine
and its llama.cpp build: CPU-only on the Pi; on the Mac, Metal on the **GPU**
(powermetrics during the runs: GPU 18-28 W, CPU 12-15 W, Neural Engine 0 W) —
the GPU comparison point the talk plans for, not a CPU-to-CPU match. Thread
count and timeout settings also differ per machine; they don't change the call
count. Time and energy below are cumulative over the whole batch (Pi: one
batch; Mac: mean of 3 batches, which agreed within 2%); the per-call columns are
those totals divided by the call count, setup amortized in — no individual call
was metered on its own.

| | Pi: whole batch | Mac: whole batch (mean of 3) | Pi: per call | Mac: per call |
|---|---|---|---|---|
| **Phi-3.5-mini, Edge Triage Pipeline (60 calls)** | | | | |
| Time | 39.4 min | 30.2 s | ~39 s | ~0.5 s |
| Average power | 7.31 W | 30.7 W | — | — |
| Energy above idle | 9,219 J | 918 J | **154 J** | **15.3 J** |
| Total energy | 17,264 J (4.8 Wh) | 928 J (0.26 Wh) | 288 J | 15.5 J |
| **Gemma-3-4B-it, Tier 2 (30 calls)** | | | | |
| Time | 26.2 min | 17.4 s | ~52 s | ~0.6 s |
| Average power | 7.38 W | 39.3 W | — | — |
| Energy above idle | 6,251 J | 680 J | **208 J** | **22.7 J** |
| Total energy | 11,593 J (3.2 Wh) | 686 J (0.19 Wh) | 386 J | 22.9 J |

Pi ÷ Mac: 10.0x / 9.2x above idle (the fairer ratio), 18.6x / 16.9x total — the
total ratio overstates the gap, since it counts the Pi board's 3.4 W idle but
only the Mac chip's 0.3 W (a MacBook's wall-socket idle, unmeasured here, is
several watts). Per-call time includes amortized setup; pure inference medians
are 31.7 s / 43.6 s on the Pi vs. 0.36 s / 0.51 s on the Mac. The Pi's "total"
runs exclude the post-run seconds before the meter photo (idle, subtracted at
the measured idle power).

**What it shows:** the Pi draws ~4x less power but takes ~88x longer per call
(31.7 s vs. 0.36 s median), so it spends **~10x more energy per call** on both
tasks — even doubling the Mac's chip figure for wall losses leaves the Pi ~5x
behind. And on the Pi, idle is half of every call's wall energy (≈288 J total
vs. ≈154 J above idle, Phi), which matters for an edge box that's always on
anyway. Framing per `docs/TALK2-POWER-MEASUREMENT-PLAN.md`: different classes
of machine, not a fair benchmark.

Two things this doesn't settle: per-token energy (Pi calls are dominated by
prompt processing, so per-call is the meaningful unit until exact completion
lengths are pulled), and `efficiency.py`'s `SMALL_MODEL_CPU.power_watts`, still
the illustrative constant — whether to anchor it on one task's number or
represent both is the open design question the plan already names. Also noted:
the Mac's per-call latency today (0.36 s Phi, 0.51 s Gemma p50) is about twice as
fast as the published M4 figures (0.75 s, 0.63 s); not yet diagnosed.

## Cooling re-run: five Edge Triage Pipeline models, three cooling conditions (2026-10-02/03)

Rows 25-26 in detail. The Pi has now run under three cooling setups, and the
published top-5 table mixes the first two:

| Condition | When | Models measured |
|---|---|---|
| **No fan** | 2026-09-26, start of the top-5 queue | Qwen3-8B's first attempt only (600MHz hard throttle, 83.7°C, gate-1 FAIL with 5/15 timeouts — rows 9-10), and the first part of Phi-3.5-mini's run |
| **First fan** (fitted mid-way through Phi's run) | 2026-09-26/27 | The published top-5 set: Phi (mixed), Gemma-3-4B-it, Llama-3.1-8B, GLM-4-9B, Qwen3-8B re-run |
| **External fan** | 2026-10-02/03 | All five: Phi from the power run (row 24), the other four in an unattended queue (`/mnt/data/fleet-trilogy/pi_cooling_rerun_queue.sh`, same flags as the published runs, each model started below 50°C) |

No model has a complete no-fan Edge Triage run except Qwen3-8B's failure.

| Model | First fan (published): format / mismatch / p50 / p95 | External fan: format / mismatch / p50 / p95 | Trace: median / peak / ≥80°C / soft-limit samples |
|---|---|---|---|
| Phi-3.5-mini-instruct | 86.7% / 0.0% / 35.7s / 157.8s *(started fanless)* | **100% / 0.0% / 31.7s / 38.8s** | 72.0 / 81.8°C / 11% / 3 of 79 |
| Gemma-3-4B-it | 100% / 2.2% / 77.1s / 101.4s | 100% / 2.2% / 78.8s / 102.7s | 71.1 / 82.3°C / 3% / 0 of 168 |
| Llama-3.1-8B-Instruct | 86.7% / 0.0% / 74.7s / 232.3s | 86.7% / 4.4% / 72.5s / 230.3s | 70.6 / 82.7°C / 14% / 9 of 176 |
| GLM-4-9B-0414 | 86.7% / 14.6% / 94.3s / 300.1s | 86.7% / 7.3% / 103.6s / 300.1s | 69.6 / 83.2°C / 19% / 23 of 258 |
| Qwen3-8B | 86.7% / 0.0% / 127.0s / 300.0s | 86.7% / 0.0% / 128.8s / 300.1s | 69.6 / 82.7°C / 13% / 16 of 293 |

External-fan artifacts (on the Pi, `eval-results/`): Phi
`compare-edge-triage-edge-node00-20261002T222637Z.json`; Gemma `…20261003T011051Z`,
Llama `…20261003T023919Z`, GLM `…20261003T044858Z`, Qwen3-8B `…20261003T071555Z`.
Traces: `trace_edge_triage_<model>_fan2.log` and the power run's
`trace_edge-triage-phi35-n15-20261002T214714Z.log`.

**Old fan vs. new fan: almost no difference.** The four models whose published
runs started with a fan reproduce their latency within ~1-10% and stay gate-2
PASS. Both fans prevent the 600MHz hard throttle that broke Qwen3-8B's first
run; neither keeps the 8-9B models fully under the Pi's 80°C soft limit, which
trims the clock to no lower than 1580MHz for brief stretches (clustered in each
run's first ~10 minutes and a couple of later bursts). No undervoltage on any
run. The quality shifts (Llama 0→2 of 45, GLM 6→3 of 41) are small enough to be
run-to-run noise; GLM's 7.3% now sits next to its M4 6.7%, so the earlier
"GLM regresses on the Pi" reading (14.6%) is no longer clearly a Pi effect.

**Phi is the exception, and it's the start condition, not the model** (row
26). Timeline from `pi_queue.log` and the run logs:

| Time (UTC) | Event |
|---|---|
| 2026-09-26 21:37 → 22:32:29 | Qwen3-8B, fanless, throttling at 600MHz / 83.7°C; FAILs gate 1 |
| 22:32:30 | Phi-3.5-mini starts — one second later, same heat-soaked fanless Pi |
| during Phi's run | first fan fitted (83.7°C / 600MHz → 76.4°C / 1800MHz) |
| 23:25:21 onward | Gemma, Llama, GLM, Qwen3-8B re-run — all with the fan |

Only Phi's tail moved (p50 −11%; p95 157.8 → 38.8 s): most calls ran at full
clock in both runs, and a minority ran 3-4x slower in the first — what part of a
run at a third of the clock looks like. Its two format failures were empty
outputs (`process() returned None`, no raw completion), consistent with 300s
timeouts — the same failure that sank the Qwen3-8B run just before it. A cool
start alone can't explain this: with a fan the Pi reaches its steady ~70-72°C
within ~2 minutes regardless of where it started. Both Phi runs are kept; the
external-fan run is the fair cross-model comparison, and it also removes the
outline's earlier caveat that Gemma-3-4B-it had the better tail (101.4s vs.
157.8s) — on equal thermal footing Phi wins the tail too (38.8s).

**For the "cooling is part of the energy budget" beat:** the evidence is fan vs.
no fan (rows 9-10, and Phi's throttled tail), not old fan vs. new fan. A
controlled no-fan run of the other models doesn't exist yet.
