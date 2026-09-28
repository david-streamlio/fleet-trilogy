# Note: LFM2.5-350M and Granite-4.0-H-350M produced zero parseable output —
# a third capability-cliff finding, distinct in shape from BitNet and 0.5B

Factual record from the full-spectrum `make compare-models` run
(`eval-results/compare-COMP-J2D9D71YNJ-20260925T165011Z.json`, all 9
`models.toml` entries, M4, 2026-09-25). This is talk material about an honest
finding, not a bug to fix quietly — same treatment as
`docs/BITNET-POSTMORTEM.md` and `docs/TALK2-0.5B-CAPABILITY-CLIFF.md`.

## The numbers

| model | format_parse_rate | severity_calibration |
|---|---|---|
| LFM2.5-350M (Q8_0) | **0.0 (0/30)** | no data — nothing parsed to check |
| Granite-4.0-H-350M (Q8_0) | **0.0 (0/30)** | no data — nothing parsed to check |
| Qwen3-0.6B (Q8_0) | 1.0 (30/30), for comparison | 61.5% mismatch |

Every single trial, for both models, failed identically: `extract_json_object`
raised `"LLM completion did not contain a JSON object"`.

## What the raw completions actually show

Pulled `sample_failures[].raw_output` for both models. All samples for both
models show the same thing: **the model's output is the prompt, echoed back
almost verbatim** (single-quoted list syntax normalized to double-quoted, but
otherwise unchanged) — including the literal placeholder shape
(`{"event": "<event_name>", "severity": "<low|medium|high>", ...}`) at the end
of the prompt. There is no attempt at an answer anywhere in the completion:
no filled-in JSON, no prose, no partial structure. It's the input, returned.

## Why this is a distinct failure mode, not a repeat of 0.5B's

`docs/TALK2-0.5B-CAPABILITY-CLIFF.md` documented degenerate *repetition* —
the model tries to answer and loops (echoing its own placeholder fills,
scrambling fields) until it hits the token cap. This is different: the model
never diverges from the input at all. It's not looping on its own attempted
output — it's returning the prompt itself as if `-no-cnv` completion mode
were behaving as an identity function for these two specific model families.

**This is not an artifact of `-no-cnv`/raw-completion mode in general.**
Qwen3-0.6B — same `llama-completion` binary, same `-no-cnv` flag, same raw
(non-chat-templated) prompt construction, comparable parameter count — parses
100% of its 30 trials. So whatever is happening is specific to the
LFM2.5-350M-RLCD and Granite-4.0-H-350M weights/architectures under this
exact invocation, not a property of skipping a chat template in general.

## Open question (not yet root-caused)

Two live hypotheses, neither confirmed:

- These two families may expect a chat template wrapper (role tags, special
  tokens) that Qwen3-0.6B's tokenizer/base training makes it more robust to
  omitting; without it, they may fall back to naive next-token continuation
  of their own context, which — for a prompt this repetitive/self-referential
  (the prompt itself contains a JSON shape near its end) — degenerates to
  copying it forward.
- `granite-4.0-h` and `LFM2.5-350M-RLCD` may need architecture-specific
  `llama.cpp` support/newer build flags not fully validated on this build for
  correct sampling — untested here.

Distinguishing these needs an experiment not yet run: repeat this exact
prompt through each model's proper chat template (via `-cnv`/chat mode
instead of raw completion) and see if either produces a real answer. That
would tell you whether this is a prompting-convention gap (fixable) or a
deeper generation problem for these weights on this hardware (a real wall,
like BitNet's).

## Why this matters for the talk

This is a third, differently-shaped wall in the same family as BitNet
(garbage tokens on ARM) and Qwen2.5-0.5B (degenerate repetition): "small
enough" doesn't fail one consistent way — it fails in whatever way that
specific model's training and this exact invocation happen to break down.
The honest framing for the talk: the extreme-low-end of the spectrum isn't
one clean "here's the wall" line on a chart — it's three genuinely different
failure shapes, discovered by the same layered methodology, at three
different points. That's a stronger argument for "you need the evaluation
framework" than a single clean cliff would have been: a single check
(format reliability) catches all three, even though the underlying causes are
completely different and none of them were predictable in advance.

Per the same principle as the 0.5B note: this stays in the chart as a
genuine finding, not a result to omit or footnote away.
