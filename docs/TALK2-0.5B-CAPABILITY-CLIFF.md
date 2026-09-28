# Note: the 0.5B model hit a real capability cliff, not a formatting nit

Factual record from the Pi 4 decision-grade `make compare-models` run
(`eval-results/compare-edge-node00-20260925T030826Z.json`, 30 calls/model,
`--model-timeout-seconds=180`), comparing Qwen2.5-1.5B-Instruct and
Qwen2.5-0.5B-Instruct, both Q4_K_M. This is talk material about an honest
finding, not a bug to fix quietly.

## The numbers

| axis | 1.5B | 0.5B |
|---|---|---|
| format_parse_rate | 0.733 (22/30) | **0.033 (1/30)** |
| grounding_violation_rate | 0.000 | 0.200 |
| latency_p50 (s) | 111.5 | 70.7 |
| tokens/sec | 1.71 | 4.04 |

0.5B is faster, as expected. But it is not "small model, good enough" — it is
"small model, mostly broken" on this task, at this prompt.

## What the raw completions actually show

Pulled the `sample_failures[].raw_output` for both models out of the artifact.

**1.5B's 5 failures** are near-miss formatting, not comprehension failures: the
model gets `truck_id`/`corridor`/`eta_impact` right, but wraps the JSON in prose
("Here is the JSON object:") or a ` ```json ` fence, or emits Python-style
single-quoted lists (`['sustained_low_speed', ...]`) instead of valid JSON
arrays. All fixable by hardening `extract_json_object` (strip fences/prose,
tolerate single-quoted lists) — a parser robustness gap, not a model failure.

**0.5B's 29 failures** are a different thing entirely: **degenerate
repetition**. Instead of answering, the model falls into a loop — either
echoing the prompt's own placeholder template verbatim
(`"event": "<event_name>", ..., "eta_impact": <copy the ETA slip value above>`)
over and over until it hits the 256-token cap, or repeating the filled-in JSON
shape dozens of times with fields scrambled (e.g. putting the truck ID into the
`"event"` field, cycling through random severities each repetition). This is
not "close but malformatted" — it's an instruction-following collapse under
one-shot (`-no-cnv`) decoding on this prompt's length/complexity. No amount of
parser hardening recovers a real answer that was never generated.

## Why this matters for the talk

This is the same shape of finding as `docs/BITNET-POSTMORTEM.md`: there is a
real capability floor, and going small enough eventually hits it. The honest
framing is a curve with a knee in it — 1.5B and up hold up fine on this task
(modulo a fixable JSON-formatting robustness gap); 0.5B falls off a cliff on
*this specific structured-output task*, not gradually. Don't smooth this into
"small models are always fine" — the 0.5B row is a genuine wall, and per
`docs/TALK2-MODEL-SPECTRUM-ACCURACY-PLAN.md`'s own instruction ("if accuracy
degrades more sharply than expected at the low end, that's a finding for the
talk, not a result to omit"), it stays in the chart as-is.

## Follow-up: 1.5B's parser gap is fixed

Re-ran `extract_json_object` (`shared/llm-inference/src/llm_inference/structured.py`)
against all 5 of 1.5B's actual `sample_failures` from the artifact: fences/prose
were already handled by the existing extractor; the one remaining real cause was
the single-quoted-list syntax (`['sustained_low_speed', ...]`) the model copies
verbatim from the prompt's own `Signals detected by cheap math: [...]` line —
otherwise-valid JSON that plain `json.loads` rejects outright.

Fixed with `_normalize_single_quoted_lists`, a regex that rewrites only
`[...]`-shaped single-quoted list literals to valid JSON arrays before the
existing fenced-block/raw-decode parsing runs — scoped tightly enough that prose
apostrophes (e.g. "truck's") are untouched (`test_normalization_does_not_touch_prose_apostrophes`).
Verified against the real captured completions: 4 of the 5 failures now parse
correctly (the 5th has no JSON object anywhere in it at all and correctly still
raises — nothing to recover there). Regression test:
`test_extracts_fenced_answer_with_single_quoted_signals_list` in
`shared/llm-inference/tests/test_structured_extraction.py`, using the byte-for-byte
captured completion. `make test`: 73/73 passing.

This does not touch 0.5B's numbers at all — its 29 failures are the degenerate-
repetition collapse described above, which has no JSON object to recover
regardless of parser leniency.

## Open follow-up (not yet done)

- Whether a shorter/simpler prompt changes 0.5B's behavior is an open question
  the model-spectrum plan's wider sweep (Q2_K/Q3_K_M variants, 3B/7B) can help
  answer — not addressed by this note.
- Re-running the Pi decision-grade sweep with the fixed extractor would give an
  updated, higher `format_parse_rate` for 1.5B in the artifact/chart data itself
  (currently 0.733, measured against the old extractor) — not yet done.
