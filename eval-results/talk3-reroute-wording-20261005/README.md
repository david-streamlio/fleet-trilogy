# Talk 3: a recommended reroute stated as already happening (2026-10-05)

Demo takes 6 and 7 both said "Traffic is (being) rerouted" where the code's decision only
recommends a reroute (`reroute_recommended: true`, detail "Reroute traffic around I-95N —
…"). This measures how often, and the prompt change that fixes it.

## Setup
- `measure_reroute_wording.py`: Gemma-3-4B-it Q4_K_M in-process (GlobalSynthesisFunction's
  backend), the demo's generation settings (temperature 0.7, 256 tokens), seed 7, a fresh
  backend per prompt. Scenarios: the demo's three cards (20 warnings) and
  `tests/model/tier2_eval_lib.py`'s three (10 each).
- Per warning: "stated as done" (regex in the script: "is/being/has been rerouted",
  "we're rerouting", …; "a reroute is recommended" / "consider rerouting" don't match),
  the Function's fact check (a failure means a regeneration), and the eval's structured,
  speakability and grounding checks.
- Prompts: `published` (`PUBLISHED_SYNTHESIS_WARNING_PROMPT`, every Tier 2 measurement
  before today) and `current` (`SYNTHESIS_WARNING_PROMPT`: plus one instruction, "A reroute
  is only ever a recommendation, never already happening: say that drivers should consider
  it or that it is recommended -- never that traffic is being, or has been, rerouted.").

## Results

| Run | Prompt | Reroute stated as done (30 with a reroute) | No-reroute warnings suggesting one (of 20) | Fact check failed (of 50) | Unstructured |
|---|---|---|---|---|---|
| 1, CPU | published | 8 | 0 | 7 | 0 |
| 1, CPU | rule in every prompt | 0 | **3** ("consider alternative routes") | 5 | 0 |
| 2, CPU | **rule only when a reroute is recommended** | **0** | **0** | 9 | 1 |
| 3, GPU | published | 9 | 0 | 7 | 0 |
| 3, GPU | **rule only when a reroute is recommended** | **0** | **0** | 2 | 0 |

- The first version of the rule, in every prompt, primed "consider" into scenarios with no
  reroute: 3 of 20 suggested alternative routes, contradicting the decision. So the rule is
  added only when a reroute is recommended; without one, the prompt is byte-identical to
  the published one (pinned by `test_prompting.py`).
- Fact-check failures are miscounted high-severity trucks either way; the Function
  regenerates those. 9 vs 7 on the CPU is within noise at n=50; 2 vs 7 on the GPU.
- The one unstructured CPU warning closed its JSON string with a curly quote (”), so the
  parser fell back to the raw text, code fences included. Rare (1 of 200 here), and the
  published prompt can do the same.
- Generation on the GPU: ~0.5 s per warning.

Files: `warnings-*.jsonl` (every warning), `summary-*.json`, `run*.log`. Run 1's "current"
rows are the rule-in-every-prompt version.

## The take that followed
Take 8 (`deploy/recordings/talk3-demo-20261005-174611.mp4`, 36.8 s, GPU,
`LLM_GPU_LAYERS=99`, gitignored): "Drivers approaching I-95N, we're seeing a slowdown
affecting multiple trucks. It is recommended that you consider rerouting around I-95N as
three trucks are experiencing significant delays, with an estimated impact of up to 9
minutes." Fact check passed first time; the warning came ~1 s after the model loaded.
