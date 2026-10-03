# Talk 2 model-spectrum accuracy plan: a wider chart, not just two points

**Status: both stages complete — M4 gate and Pi 4 decision-grade run.** This
doc's original gate-2-confirmed run (below, 9 models, `severity_mismatch_rate`)
has since been superseded twice: first by widening the candidate pool to 14
models, then by the architectural pivot that moved `severity`/
`recommended_action` to deterministic cheap math and narrowed the LLM's job
to a bounded escalation decision (`severity_mismatch_rate` was replaced by
`escalation-direction mismatch` as the gate metric — see commit
`5630c2d`, which moved severity + recommended_action to deterministic cheap math).
Full detail and the run-by-run history live in
`docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md`'s running-total table (rows
8-18); this status block gives the final numbers only.

The full M4 gate (all 14 candidates, post-pivot metric) produced a 5-model
clean tier: **Qwen3-8B, Phi-3.5-mini-instruct, Gemma-3-4B-it** (0.0%
mismatch), **Llama-3.1-8B-Instruct** (5.6%), **GLM-4-9B-0414** (6.7%) — the
other 9 candidates (including everything ≤0.6B) failed to clear the gate.
All five went on to the Pi 4 decision-grade run (`docs/PI4-RUNBOOK.md`),
which is now **complete** — no larger candidate list is still owed a Pi run:

| model | Pi mismatch | notes |
|---|---|---|
| Phi-3.5-mini-instruct | 0.0% | matches M4 exactly; p50/p95 31.7s/38.8s, RAM 92% on the 2026-10-02 re-run — the first run's 35.7s/157.8s (RAM 93%) started on a throttled, fanless Pi (impact-track row 26); both kept |
| Llama-3.1-8B-Instruct | 0.0% | n=45, gate-2 confirmed; p50/p95 74.7s/232.3s, RAM 91% |
| Qwen3-8B | 0.0% (43/43) | first Pi attempt collapsed to 66.7% format_parse_rate — traced to real thermal throttling (83.7°C, ARM clock cut to 600MHz), not a model or bug; recovered cleanly after a fan fix |
| Gemma-3-4B-it | 2.2% | ~identical to M4's 0%; p50/p95 77.1s/101.4s, RAM 96% |
| GLM-4-9B-0414 | **14.6%** (n=41) | the one outlier — concentrated entirely in the "benign" scenario (6/13 false-escalations), vs. 6.7% on M4 |

Four of five hold 0-2.2% mismatch on real target hardware; GLM-4-9B-0414 is
the one model whose M4 accuracy didn't fully transfer. This is a **separate
axis** from `docs/TALK2-GPU-BENCHMARK-PLAN.md` — see "How this relates to
the other GPU plan" below for exactly how they compose.

### Original gate-2-confirmed result (2026-09-25, superseded above)

The gate-2-confirmed `make compare-models` run (2026-09-25, 18:57 UTC,
`eval-results/compare-COMP-J2D9D71YNJ-20260925T185711Z.json`) eliminated 8 of
9 `models.toml` entries; **Qwen3-8B (Q4_K_M)** was the sole `production_candidates`
PASS (`severity_mismatch_rate` 20.5%, n=88, gate-2 confirmed). Full elimination
table and reasons: `docs/TALK2-OUTLINE.md`'s "Update — gate-2-confirmed
result" section. This was the state before the candidate pool widened to 14
and the escalation-direction pivot replaced the gate metric — kept here for
history, not as current status.

## Why (revised — the talk's own thesis has moved)

The original thesis was "small models are good enough while minimizing
power/hardware footprint," told as two illustrative points
(`SMALL_MODEL_CPU`/`FULL_PRECISION_GPU` in
`talks/talk2-greenest-token/src/talk2_greenest_token/efficiency.py`). What
actually happened while building this talk has become the more honest and
more interesting story: **"what I learned trying to run LLMs on a Pi."**

- Tried true 1-bit (BitNet b1.58-2B-4T) — produced garbage on ARM. Dead end,
  recorded in `docs/BITNET-POSTMORTEM.md`.
- Tried the Qwen2.5 family (0.5B/1.5B, Q4_K_M) — found a real capability cliff
  at 0.5B (`format_parse_rate` 0.033/30, degenerate repetition, not a
  formatting nit) and a fixable JSON-extraction gap at 1.5B — both recorded in
  `docs/TALK2-0.5B-CAPABILITY-CLIFF.md`.
- Now broadening beyond Qwen2.5 (see "Model spectrum" below) to see whether
  that cliff/robustness pattern is Qwen-specific or general, and to build a
  broader accuracy/speed/efficiency comparison across model families.

This plan produces the **accuracy side** of that story using real
measurements (not illustrative constants), gated on the M4 before anything
goes to the Pi for speed/efficiency numbers (see "Two-stage funnel" below).

## No longer a same-family-only spectrum — that's now intentional

The earlier version of this plan restricted every addition to the Qwen2.5
family specifically to isolate "does size/quantization alone explain the
accuracy delta" as a clean single-axis chart. That constraint was based on not
knowing what else would run in this environment, not a hard requirement of the
talk. It's now explicitly relaxed: this plan adds three more model families
(see below), and the resulting chart is a **broader accuracy/speed/efficiency
comparison across families**, not a pure single-family spectrum. That's a
different, less rigorous-looking chart than a same-family isolation would give
— call this out explicitly when presenting it (e.g. annotate which points
share a family/quantization scheme), rather than implying the whole chart
isolates one variable when it no longer does.

## Important constraint: no revisiting BitNet

`docs/BITNET-POSTMORTEM.md` already answers "how far down can we go" for true
1-bit models: the BitNet b1.58-2B-4T fork produces garbage output
(`@@@@@@@@...`) on ARM, M4 included, for reasons deep in its hand-written
kernels that we deliberately chose not to debug. **Do not re-attempt BitNet as
part of this spectrum.** The low end of the spectrum here means aggressive
*mainline-llama.cpp-compatible* quantization (Q2_K/Q3_K_M GGUF, still real
4-bit-class or lower quantized weights, not 1-bit), not the abandoned fork.
The "1-bit LLM" framing stays exactly where the postmortem already put it: the
honest story of a wall we hit, not a claim about the shipped models.

## Two-stage funnel: M4 is a gate, not a benchmark

The M4 run is **not** meant to produce Pi-comparable speed/efficiency
numbers — it exists to fail models fast. Goal (in the user's words): "find the
failures quickly rather than slowly on the Pi."

1. **Gate, on the M4**: run `make compare-models`'s correctness axes only
   (`format_reliability`, `grounding`, `directional_accuracy`) for every
   candidate model. This is CPU-only, wall-clock-cheap relative to the Pi, and
   `_decision_grade()` already auto-labels it `"quality-only (non-target
   hardware)"` — correct, since M4 timing/RAM numbers aren't Pi-representative.
2. **Promote only the models that pass the gate** to a full Pi run
   (`docs/PI4-RUNBOOK.md`'s existing job) for the decision-grade
   latency/tokens-per-sec/power/RAM numbers that actually matter for "would
   this run on the target hardware."
3. **Gate thresholds (decided):**
   - `format_reliability.rate >= 0.7`
   - `grounding.violation_rate <= 0.05`

   A model clears the gate and proceeds to the Pi only if it meets **both**;
   failing either one cuts the model, and its M4 failure mode becomes the
   finding (same treatment as 0.5B in `docs/TALK2-0.5B-CAPABILITY-CLIFF.md`).
   Consistent with the Qwen2.5 baseline: 1.5B cleared both (`format_parse_rate`
   ~0.73 pre-fix/higher post-`extract_json_object`-fix; `grounding.violation_rate`
   0.000); 0.5B failed both (0.033; 0.200 — though note that 0.200 is 1
   violation out of only 5 grounding-checkable samples, since grounding is only
   evaluated on calls that parsed at all, so it's a thin-N number for any model
   with a low parse rate — treat a low-N grounding result with proportional
   caution when reporting, even though it's still a legitimate gate input).

   `directional_accuracy.f1` (and precision/recall) is **reported for every
   model, pass or fail, but is not a gating criterion.** In the one completed
   run, `f1`/precision/recall were bit-for-bit identical for both Qwen2.5
   models (tp=49, fp=1, fn=33, tn=97) — this axis scores the fleet simulator's
   seeded ground-truth labels against the pipeline's slowdown classification,
   and in this dataset it didn't actually vary with the LLM's own output. It's
   a pipeline-plumbing sanity check more than a per-model discriminator here,
   which is why it stays informational rather than gating.

   `severity_calibration.mismatch_rate` (new — see "Severity calibration" below)
   is likewise **reported, not gating**, same treatment as `f1`: it's a
   genuinely new judgment axis with no track record yet across models, so it
   stays informational until we've seen it vary meaningfully across the
   spectrum.

## Severity calibration: the missing task-specific accuracy axis

Everything the harness measured before this addition checked *form* (is it
parseable JSON, are `truck_id`/`corridor`/`eta_impact` grounded in the input)
and a *pipeline-plumbing* check (`directional_accuracy`, which — see above —
doesn't actually vary with the LLM's own output). Nothing checked whether the
model's actual judgment call, `severity`, was *right*. That's a real gap for a
task whose entire point is "classify severity and describe the ETA impact"
(the prompt's own words, `structured.py`'s `ENRICHMENT_CARD_PROMPT`).

**There is no severity ground truth anywhere else in this repo.** `severity`
is otherwise a free-text `"low"/"medium"/"high"` string the LLM invents;
grep across the whole tree turns up no threshold, formula, or labeled dataset
for it — the only downstream consumer (`talk3_pulsar_speaks_english
/synthesizer.py`) just checks for the literal string `"high"` to decide on a
corridor-wide reroute. So this is a deliberately chosen, deterministic rule,
not a discovered fact — documented here so the talk can say exactly that.

**The rule** (`eval_lib.expected_severity`), tied to the fleet simulator's own
incident ramp rate (`shared/fleet-simulator/src/fleet_simulator/scenario.py`:
`SLOWDOWN_ETA_SLIP_PER_TICK_MINUTES=0.6`, `MIN_INCIDENT_TICKS=24`/
`MAX_INCIDENT_TICKS=48` → a fully-played-out incident accumulates 14.4–28.8min
of slip; detection itself fires as early as `eta_slip_min=2.0`):

| tier | `eta_slip_min` range | rationale |
|---|---|---|
| low | `[2, 5)` | just crossed the detection floor, early in an incident |
| medium | `[5, 15)` | spans the width where most incidents cross (min incident length alone is 14.4min) |
| high | `[15, ∞)` | already past a full minimum-length incident: a genuinely prolonged delay |

**New eval (`tests/model/test_severity_calibration.py`, wired into both the
single-model Tier 3 suite and `make compare-models`):** builds three
representative events — `eta_slip_min` 3.0/10.0/20.0, one per tier — runs each
through the real enrichment prompt, and compares the model's `severity`
against `expected_severity(eta_slip_min)`. Reported as `severity_calibration:
{total, mismatches, mismatch_rate, sample_mismatches}`, same shape as
`grounding`. Gated via `--model-severity-max-mismatch-rate` (default `0.5` —
deliberately lenient; see the gate-threshold note above for why this stays
informational rather than a hard cut for now).

**Early real signal** (smoke test, Qwen2.5-1.5B-Instruct Q4_K_M, n=1 per tier
— too small to trust as a finding, but worth watching for at proper N): the
model said `"high"` for both the `eta_slip_min=3.0` (expected `low`) and
`eta_slip_min=10.0` (expected `medium`) cases, `eta_impact` correctly grounded
each time. If this holds up at the full `--model-eval-runs` count, it's a
distinct finding from the 0.5B capability cliff — not "broken," but
"systematically over-escalates severity" — exactly the kind of thing this
axis exists to catch and the earlier harness had no way to see.

## Scope boundary

This plan produces **accuracy-gate measurements across a spread of model
families/sizes/quantization levels**, all run as CPU inference on the M4. It
does **not**:

- measure latency, power, or RAM as decision-grade numbers for anything run on
  the M4 — the M4 is not the target stage hardware (the Pi 4 is), so those
  axes from an M4 run are illustrative/contextual at best. The existing
  harness already encodes this distinction for you (see below) — don't fight
  it or add a parallel labeling scheme.
- touch `SMALL_MODEL_CPU`/`FULL_PRECISION_GPU`'s existing definitions in
  `efficiency.py` directly — this plan feeds a *new* chart (accuracy across
  families/sizes/quantization, plus whichever models clear the gate get
  Pi speed/tokens-per-sec/efficiency numbers next), not a replacement for the
  two-point cost/latency/power comparison those constants already tell.
- require any new eval harness code. `tests/model/test_compare_models.py`
  already does exactly this job for an arbitrary number of models in
  `models.toml` — see below.

## How this relates to the other GPU plan

`docs/TALK2-GPU-BENCHMARK-PLAN.md` is about **one** real fp16-on-GPU data
point (latency/power/cost, via Metal) to replace `FULL_PRECISION_GPU`'s
illustrative constant. This plan is about **accuracy across many models**,
CPU-only, to build a size/quantization-vs-accuracy chart. They can both run on
the same machine (the M4) but are independent work:

- Run this plan's `make compare-models` sweep first — it's the cheaper,
  lower-risk one (no `powermetrics`/`sudo`, no Metal build required, reuses
  the harness as-is).
- The GPU plan's single fp16-Metal data point can optionally become one more
  point on this same accuracy chart (its `format_parse_rate`/`precision`/
  `recall`/`f1` numbers are directly comparable to this plan's other rows) —
  but its latency/power numbers stay in `efficiency.py`'s separate two-point
  comparison. One run's accuracy numbers can feed both stories; that's a
  bonus, not a requirement to sequence them together.

## 1. The harness already supports this — no new code

`tests/model/test_compare_models.py` (`make compare-models`) already:

- runs the full existing eval set (format reliability, grounding, directional
  accuracy, latency, load time, resident RAM) for **every** model listed in
  `models.toml`, on identical seeded inputs (`AXES`, `_run_one_model`);
- proceeds even when only some manifest models are available on the current
  host, reporting the rest as unavailable rather than skipping the run
  (its module docstring says so explicitly);
- already labels a run's **decision-grade** scope per-host via
  `_decision_grade()`: a Pi 4 (`Linux` + `aarch64`/`armv7l`/`armv6l`) run is
  `"full (Pi 4 target)"`; anything else — including the M4 — is automatically
  labeled `"quality-only (non-target hardware)"`. That label already exists
  precisely to say "trust format/grounding/accuracy numbers from this run;
  don't trust its latency/RAM numbers as Pi-representative." This plan is
  simply: run that same harness on the M4 with a longer `models.toml`, and
  only read the quality axes (`format_parse_rate`, `grounding_violation_rate`,
  `precision`, `recall`, `f1`) out of the result.

So this plan's only real work is **(a) deciding which models to add to the
spectrum** and **(b) actually running it** — not writing new test code.

## 2. Model spectrum to add to `models.toml`

`models.toml` currently has two entries: Qwen2.5-1.5B-Instruct and
Qwen2.5-0.5B-Instruct, both Q4_K_M. Widen the spectrum along two independent
dimensions — don't conflate them in the chart:

**A. Quantization level, same model family/size** (isolates "how much does
quantizing this specific model hurt accuracy"):
- Qwen2.5-0.5B-Instruct: add Q2_K and Q3_K_M alongside the existing Q4_K_M.
- Qwen2.5-1.5B-Instruct: add Q2_K and Q3_K_M alongside the existing Q4_K_M.

**B. Model size, held at a fixed reasonable quantization** (isolates "how much
does model scale help accuracy, at a quantization level we'd actually ship"):
- Qwen2.5-0.5B-Instruct Q4_K_M (existing)
- Qwen2.5-1.5B-Instruct Q4_K_M (existing)
- Qwen2.5-3B-Instruct Q4_K_M (new — mid-point)
- Qwen2.5-7B-Instruct Q4_K_M (new — still CPU-runnable on M4 unified memory,
  upper end of "quantized" before crossing into the GPU plan's fp16 territory)

**C. Cross-family, at a fixed reasonable size/quantization** (new — the
"what I learned broadening beyond Qwen2.5" part of the talk arc):
- Llama-3.1-8B-Instruct, Q4_K_M
- Qwen3-8B, Q4_K_M
- GLM-4-9B-0414, Q4_K_M

Each addition is a new `[[models]]` entry in `models.toml` — same shape as the
existing two, with `-no-cnv` in `extra_args` per the manifest's existing
convention (mainline llama.cpp one-shot mode, not chat/conversation mode; the
mode bug the earlier timeout-fix session's smoke test hit when it bypassed
this convention). New env var names (e.g. `LLM_BINARY_PATH_QWEN05B_Q2K`,
`LLM_MODEL_PATH_QWEN3B`) following the existing `_QWEN15B`/`_QWEN05B` pattern.

Notes specific to the three cross-family additions:

- **All three run via `SubprocessLlmBackend` (CPU `llama.cpp`), not
  `HttpLlmBackend`** — even though Qwen3-8B is already loaded and served live
  by the M4's vllm-mlx stack (the `fast` route). Using the live engine would be
  free and avoid CPU contention, but it measures a different quantization/
  serving stack than the GGUF `llama.cpp` path the other two families use —
  mixing methods inside the same gate would confound "did this model fail" with
  "did this serving stack behave differently." Keep the gate apples-to-apples;
  the live engine stays available as an optional separate bonus data point if
  wanted later, not part of the gate itself.
- **Verify GLM-4-9B-0414 architecture support in whatever `llama.cpp` build
  runs on the M4 before pulling weights.** GLM-4 is a newer architecture than
  Llama/Qwen and support varies by version — a build without it will fail to
  load the model outright, which is a build/toolchain problem to catch before
  wasting a weights download, not an accuracy-gate finding.
- **Expect new prompt-echo/JSON-extraction failure modes per family.** The
  existing `extract_json_object` heuristics (fenced-block preference,
  single-quoted-list normalization) were reverse-engineered specifically from
  Qwen2.5's completion behavior. Llama-3.1/Qwen3/GLM-4 will very likely echo,
  fence, or restate the prompt differently — inspect a handful of each
  family's raw completions (same way `docs/TALK2-0.5B-CAPABILITY-CLIFF.md` was
  built) before trusting any `format_parse_rate` number from them, since a low
  rate could mean "the model is bad at this" or "the extractor doesn't
  recognize this family's echo pattern yet" — those are different findings and
  the chart should say which one it is.

## 3. Steps

1. Confirm access; `uv sync`; `make test` passes in mock mode (sanity check,
   same first step as every other runbook here).
2. Pick and record the gate threshold (see "Two-stage funnel" above) before
   running anything, so it's not chosen after seeing results.
3. Pull the additional GGUF weights (Q2_K/Q3_K_M for the existing two models,
   Q4_K_M for 3B/7B, Q4_K_M for the three cross-family additions) — not
   committed to the repo, same `.gitignore` rule as the existing weights.
   Confirm `llama.cpp` on the M4 actually supports GLM-4's architecture before
   pulling its weights.
4. Coherence check each new model once with a plain prompt before trusting
   any eval number from it — same discipline as every other runbook here;
   catches a bad quantize/download before it pollutes the comparison table.
5. Add the new `[[models]]` entries to `models.toml`.
6. Run `make compare-models` on the M4 (the gate). Expect it to auto-label the
   run `"quality-only (non-target hardware)"` — that's correct and expected,
   not a bug to fix.
7. From the resulting artifact JSON, pull `format_reliability.rate`,
   `grounding.violation_rate`, `directional_accuracy.{precision,recall,f1}`
   per model. For each of the three cross-family additions, read a handful of
   `sample_failures[].raw_output` before trusting the number (see the
   per-family note above) — ignore `latency`/`load_time_seconds`/
   `resident_ram_mb_*` for gate purposes (M4 numbers for those aren't
   Pi-representative).
8. Copy the artifact to `eval-results/`, same convention as the Pi runs
   (dated, host-labeled filename).
9. Apply the recorded gate threshold: models that pass move on to a full Pi
   run (`docs/PI4-RUNBOOK.md`) for decision-grade latency/tokens-per-sec/
   power/RAM numbers; models that fail stop here, with their M4 failure mode
   as the finding (same treatment as 0.5B in
   `docs/TALK2-0.5B-CAPABILITY-CLIFF.md` — a wall to report, not to omit).

## 4. What comes back from this

Two layers of artifact, matching the two-stage funnel:

- An M4 gate artifact JSON (accuracy axes across all candidate models: the
  existing Qwen2.5 spectrum plus Llama-3.1-8B, Qwen3-8B, and GLM-4-9B), used
  to decide who proceeds.
- Pi decision-grade artifact(s) (`docs/PI4-RUNBOOK.md`) for whichever models
  clear the gate — the source of the actual latency/tokens-per-sec/power/RAM
  numbers for the talk's speed/efficiency axes.

From these, a short note on what should go into a new chart-producing
function in `talk2_greenest_token/report.py` covering the three axes the user
named: **accuracy** (format_parse_rate/f1 per model), **speed**
(tokens-per-sec, Pi-measured only), and **efficiency** (latency/RAM/power
relative to model size, Pi-measured only). Since the model set now spans
multiple families rather than one isolated spectrum, annotate which points
share a family/quantization scheme when presenting the chart (per "No longer
a same-family-only spectrum" above) rather than implying a single clean axis.
Human decides the final framing — a chart that quietly cherry-picks the
flattering axis would undercut the same intellectual honesty this project's
other postmortems and "illustrative, not measured" labels have maintained
throughout. If accuracy degrades more sharply than expected at the low end,
or a whole family fails to clear the gate, that's a finding for the talk, not
a result to omit.
