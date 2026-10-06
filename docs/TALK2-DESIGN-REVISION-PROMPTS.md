# Talk 2: Claude design prompts for the revision (2026-10-06)

Paste-ready prompts that revise the deck already built from the 28-slide plan
(`docs/TALK2-REWORK-SLIDE-PLAN.md` at `ba1a7d0`: slide 19 is a chart slide, slide 25's
table has 7 rows). If your deck predates that, send Prompt 6 from
`docs/TALK2-REWORK-DESIGN-PROMPTS.md` first.

**What the revision does:**
- **Concrete examples.** Every do/don't is backed by a real prompt, a real output and the
  number it cost, tagged ACCURACY, SPEED or POWER.
- **A new "greenest token" slide** showing where the savings came from.
- **A bounded-judgment vs whole-job section**, with the two prompts side by side.
- **Corrections from the 2026-10-06 audit** (test log, incident 27). Qwen3.5-9B's "36 of 36
  never finished thinking" was mostly a harness bug: the thinking grammar `[^<]*` closed the
  thought at the model's first "<". The "repeats agreed 80-90%" figure is really 73-92%.
  And the sub-1B models didn't echo the prompt.

Every quoted prompt and output below was checked against the result files named in its
"Source" line. Don't let the design tool tidy them.

**Upload first:** `talks/talk2-greenest-token/slides/charts/slide_fig3_thinking.png`, the
regenerated chart without the invalid point, replacing the old one.

**Order:** R0, R1, R2, R3, R4, R5, then R6 (renumber, recap tags, QA).

**Time:** this adds 6 slides (28 → 34). To stay at 40 min, speak the new example slides
fast (~1 min each), and trim ~5 min elsewhere. Candidates:
- slide 5 ("Three questions, one study") and slide 8 (the speed chart) to ~1 min each;
- slides 17-18 (faster hardware; accuracy across hardware) to ~1 min each;
- slide 21's recap read, not explained (its items now have their own examples).

---

## R0: revision brief (send first)

```
We're revising the existing deck, not rebuilding it. Keep the DATADOG_MARKETING_DECK design, the slide styles you already used, and every rule from my first message: text verbatim, no invented numbers or claims, no planning tags on slides, presenter notes on every slide. Rules for this revision:

1. Verbatim examples. When I give a model prompt or output in a fenced block, show it as a code panel (Roboto Mono, small, JSON syntax-highlighted) exactly as written. You may shorten it only where I put "…". Never paraphrase or tidy a model's output, including its mistakes and odd quoting.
2. Highlight, don't rewrite. To point at what matters (a wrong field, the place a cache ends), put a colored highlight or outline on the existing text, plus the short callout label I give you.
3. Tag each example with its measure: a small chip, ACCURACY (blue #0060FF), SPEED (cyan #00CAFF) or POWER (orange #FF5E00), in Roboto Mono caps.
4. New slides get the presenter notes I give under "Notes:". Keep their numbers exactly.
5. Insert new slides where I say. Don't renumber until the last prompt asks you to.

Reply with a one-line confirmation, then wait.
```

## R1: corrections (data errors; apply exactly)

```
Apply these corrections. They fix errors in the data.

Slide 11 ("I assumed thinking would make it more accurate…"):
- Replace the chart with the uploaded slide_fig3_thinking.png (one invalid point removed).
- Replace the on-screen line "Qwen3.5-9B: 36 of 36 calls never finished thinking" with:
  "Qwen3.5-9B on the simple task: 11 of 18 calls never finished thinking"
- In the presenter notes, replace the sentence starting "Qwen3.5-9B on the hard task hit a 2,048-token budget…" with:
  "On the simple task, Qwen3.5-9B never finished thinking on 11 of 18 calls at a 2,048-token budget. Its hard-task result with thinking on isn't on the chart: my harness's grammar cut the thinking off at the first '<' the model wrote, and those calls never produced an answer. That was a bug in my harness, not the model."

Slide 14: replace "Repeats agreed 80-90% of the time" with "Repeats agreed 73-92% of the time". Keep the rest of the line.

Slide 20, presenter notes: replace "below ~1B parameters, expect echoing and loops, not answers" with:
"below ~1B parameters, expect empty answers or loops: the 350M models stopped without writing anything, and the 0.5B model repeated the template until it ran out of tokens."

Slide 25, table: in the "completion rate" row, replace "36/36 calls truncated" with "11/18 calls never finished thinking".

Change nothing else. List what you changed.
```

## R2: one bounded judgment vs the whole job (2 new slides after slide 12)

Source: prompts from `DEFAULT_PROMPT_TEMPLATE`
(`talks/talk1-edge-intelligence/src/talk1_edge_intelligence/triage_function.py`) and
`FULL_PROMPT_TEMPLATE` (`tests/model/round3_eval.py`). Outputs from round 3 on the M4 Max:
`eval-results/compare-round3-COMP-J2D9D71YNJ-20261004T154259Z.json` (narrow, call 1) and
`…154409Z.json` (full, call 7). Same model, Gemma-3-4B; same benign case; same physics
(0.30 g, no ABS, so the baseline is medium).

```
Insert two new slides after slide 12 ("I assumed a capable model could do the whole job in one call…"). Eyebrow on both: "ASSUMPTION 3, UP CLOSE" (not a new assumption number). Accent: the same as slide 12. Chip: ACCURACY.

NEW SLIDE A. Title: "One bounded judgment vs the whole job"
Layout: two columns, each a short definition above a code panel.
Left header: "One bounded judgment (production)". Definition: "Code computes the facts first. The model answers one question: raise, hold or lower?"
Left code panel:
"""
A deterministic vehicle-physics system has already computed a baseline severity … Your only job is to decide whether the three operational-context fields below, taken together, are strong enough evidence to move away from it.

BASELINE SEVERITY (already computed from vehicle physics): medium

Operational context:
Weather: Clear skies, dry pavement
Cargo: Dry goods / General freight
Dispatch status: On schedule

How to weigh each field: …
Decision:
- raise: … - lower: … - hold: …
"""
Under it, small: "Model writes: risk_synthesis, escalation. Code adds: final severity, action, truck ID, ETA."
Right header: "The whole job (round 3's test)". Definition: "The model gets the raw physics and the rules, and must do all three steps in one call."
Right code panel:
"""
Assess this slowdown event in three steps.

STEP 1 - BASELINE SEVERITY from vehicle physics, using exactly these rules:
- high if ABS engaged is yes, or the peak deceleration is above 0.45 g.
- Otherwise, if the peak deceleration is 0.22 g or below: medium if the traffic pattern is severe stop-and-go compaction, else low.
- Otherwise (above 0.22 g, up to 0.45 g): high if the traffic pattern is severe stop-and-go compaction, else medium.

Vehicle physics:
Peak deceleration: 0.3 g
ABS engaged: no
Traffic pattern: elevated velocity variance (frequent speed cycling)

STEP 2 - ESCALATION. … (the same context and rules as on the left)

STEP 3 - FINAL SEVERITY AND ACTION:
- severity: the baseline moved one level up for raise …
- recommended_action: exactly "Escalate for driver/dispatcher review." for raise, …
"""
Under it, small: "Model writes all six fields."
Highlight "BASELINE SEVERITY (already computed from vehicle physics): medium" on the left, and "STEP 1" and "STEP 3" on the right, in the same color, with the callout "work moved from code into the model".
Notes: "Same model, same operational context, same escalation rules. The only difference is scope. On the left, five lines of code have already worked out the baseline from the physics, and the model weighs weather, cargo and dispatch. On the right, the model has to apply the thresholds itself, then the escalation, then derive the final severity and the action."

NEW SLIDE B. Title: "Same model, same case: what came back"
Layout: two code panels side by side, a verdict badge under each, one result line across the bottom.
Left header: "One bounded judgment". Code panel:
"""
{
  "risk_synthesis": "Cargo: The cargo is dry goods / general freight, which is not a risk multiplier. Weather: The weather is clear skies, dry pavement, which is not a risk multiplier. Dispatch status: The dispatch status is on schedule, which is not a risk multiplier. Therefore, the baseline severity of medium remains appropriate.",
  "escalation": "hold",
  "truck_id": "truck-47"
}
"""
Badge (green): "Correct: hold".
Right header: "The whole job". Code panel:
"""
{
  "baseline_severity": "medium",
  "risk_synthesis": "Traffic pattern: elevated velocity variance (frequent speed cycling) and peak deceleration: 0.3 g",
  "escalation": "raise",
  "severity": "medium",
  "recommended_action": "Escalate for driver/dispatcher review.",
  "truck_id": "truck-47"
}
"""
Highlight "escalation": "raise" with the callout "raised on the physics alone; the context is benign". Highlight "severity": "medium" with the callout "a raise should make it high: it contradicts itself".
Badge (orange): "Wrong: should hold".
Bottom line, large: "Small models: 94-100% correct on one judgment, 11-22% on the whole job"
Notes: "Gemma-3-4B, the same benign case. Given one question, it weighed each field and held. Given the whole job, it reasoned about the physics instead of the context, raised, and then wrote a severity that contradicts its own raise. Across the small models, accuracy fell from 94-100% to 11-22%. Every part of the job got worse, even the escalation it had just done well."
```

## R3: make the assumption slides concrete (slides 10, 11, 13-17)

Sources:
- slide 10: `docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md`, "Pi 4 power measurement";
- slide 11: `…round3…T165312Z.json` / `…T171623Z.json`, calls 9 and 4;
- slide 13: `…T161750Z.json` (raw) / `…T172043Z.json` (chat-off), call 4;
- slide 15: `eval-results/phone-proxies/iphone-flagship/C-artifacts/` (Q-confirm, `…151407Z`
  to `…154001Z`), `talks/talk2-greenest-token/TODO-Q4_0-ACCURACY-CHECK.md`,
  `eval-results/edge-triage-backend-accuracy-m4max-20261005/`;
- slide 16: `eval-results/phone-proxies/m4max-macbook/20261004T190116Z-ablation-ABORTED/ABORTED.txt`,
  `eval-results/phone-proxies/android-flagship/L7-workload-20261004T002907Z/OOM-KERNEL-LOG.txt`,
  test log, `-ctx8192-check`;
- slide 17: test log, "Caffeinated rerun" and gated-reverse.

```
Add a concrete example to each of these slides. Keep each slide's title, eyebrow and "Do this:" footer. On slides 13-17, the example replaces the before/after columns. On slides 10 and 11, add it as a compact strip under or beside the chart.

SLIDE 10 (energy), strip, chip POWER:
"Pi 4 board: 7.3 W while answering (3.4 W idle), 31.7 s per call → 154 J above idle"
"M4 Max chip: 30.8 W, 0.36 s per call → ~15 J"
Callout: "4× the power, a tenth of the energy: compare joules per job, not watts"

SLIDE 11 (thinking), strip, chips ACCURACY + SPEED: two mini-cards, the same question asked with thinking off and on.
Card 1 header: "Qwen3-14B, one case: thinking fixed it". Lines: "Off: 4.81 s, 125 tokens, baseline wrong (medium)". "On: 18.55 s, 449 tokens (349 thinking), right (high)".
Card 2 header: "Another case: thinking broke it". Lines: "Off: 5.04 s, right (hold)". "On: 15.71 s, 580 tokens, wrong (lower)".
Line under the cards: "Across all 36 cases: 72% off vs 78% on, inside each other's error bars, at 4× the time"

SLIDE 13 (chat format), replace the columns, chip ACCURACY. Two code panels, same model (Qwen3.5-9B), same prompt, same benign case.
Left header: "Raw prompt". Show the prompt as one line: "You are a fleet dispatch operational-risk assessor. Assess this slowdown event in three steps. …". Under it, the output:
"""
"baseline_severity": "low",
"risk_synthesis": "Peak deceleration of 0.15 g is below the 0.22 g threshold. Traffic pattern is severe stop-and-go compaction, which triggers medium severity. However, … No fields warrant escalation.",
"escalation": "hold",
"severity": "low",
"recommended_action": "Log and continue; no immediate action needed."
"""
Highlight "which triggers medium severity" and "baseline_severity": "low" with the callout "says medium, writes low".
Right header: "The same prompt in its chat template, thinking off". Show the prompt as:
"""
<|im_start|>user
You are a fleet dispatch operational-risk assessor. … <|im_end|>
<|im_start|>assistant
<think>

</think>
"""
Highlight the template markers with the callout "12 tokens of wrapper". Under it, the output:
"""
"baseline_severity": "medium",
"risk_synthesis": "No escalation fields present; weather is clear/dry (no traction loss), cargo is general freight (no spill/shift risk), and dispatch status is on schedule (no pressure-induced risk).",
"escalation": "hold",
"severity": "medium",
"recommended_action": "Continue monitoring; no status change."
"""
Badges: left orange "Wrong (4 of 5 fields)", right green "Correct".
Bottom line: "Across the hard task: 22% → 72% correct (on the M1: 19% → 61%)"

SLIDE 14 (repeats), replace the columns, chip ACCURACY. A small visual: 3 test cases, each drawn as 6 identical dots in a row (18 dots in all). Label: "18 of 18 correct = 3 cases × 6 repeats". Beside it: "Repeats agreed 73-92% of the time, so it's closer to 3 data points than 18". Then large: "The honest 95% range: 44-100%, not 82-100%".

SLIDE 15 (quantization), replace the columns, chips ACCURACY + POWER. A small table of what Gemma-3-4B answered on the benign case (expected: hold), 45 calls per run:
| File | Run 1 | Run 2 |
| Q4_K_M | hold 45 | hold 45 |
| Q4_0 | lower 39, hold 6 | lower 43, hold 2 |
Under it: "Q4_0: 82 of 270 escalations wrong (30%), for 28% less energy per call (46.9 → 33.6 J on the M1)"
Second line, smaller: "Runtime counts too: the same Phi-3.5 file through llama-cpp-python instead of llama-server answered 'lower' on 15 of 15 benign calls with the reordered prompt"

SLIDE 16 (default context size), replace the columns, chips POWER + SPEED. Three stacked facts:
1. "No context size set: llama-server reserved Phi-3.5's full 128,256-token context. 51.2 GB resident on the 64 GB laptop, swapping"
2. A code panel with the kernel log line from the 16 GB machine:
"""
Out of memory: Killed process 24985 (llama-server) total-vm:20145988kB, anon-rss:15396352kB
"""
3. "At 8,192 tokens: ~6 GB, the same latency (0.36-0.37 s) and energy (14.4-15.3 J per call). The task needs under 1,000."

SLIDE 17 (faster hardware), replace the columns, chips SPEED + POWER. A table, "Laptop, cool vs throttled (median per call)":
| Model | Cool | Throttled |
| Qwen3-8B | 1.37 s, 40.1 J | 1.96 s, 27.8 J |
| Gemma-3-4B | 1.14 s, 36.2 J | 2.01 s, 22.0 J |
| Llama-3.1-8B | 0.78 s, 25.4 J | 1.14 s, 18.6 J |
Line: "Cool: 24-77% faster, but 30-60% more energy per call"
```

## R4: two new example slides (before the do/don't slides) and the prompt-layout slide

Sources:
- classifier: `eval-results/compare-COMP-J2D9D71YNJ-20260925T185711Z.json` (Llama-3.1-8B,
  thresholds stated in the prompt) and `compare-edge-triage-COMP-J2D9D71YNJ-20260926T153435Z.json`
  (15 models, before the pivot);
- the rule: `severity_classifier.py`;
- grammar: `eval-results/compare-edge-node00-20260925T030826Z.json` (free text, Pi 4) and
  `compare-edge-triage-COMP-J2D9D71YNJ-20260926T131727Z.json` (with the grammar);
- layout: `EVENT_LAST_PROMPT_TEMPLATE` vs `DEFAULT_PROMPT_TEMPLATE`, Phi-3.5's tokenizer, and
  `eval-results/edge-triage-event-last-pi4-20261005/`.

```
Insert three new slides. Same family style as the assumption slides, but eyebrow "EXAMPLE".

NEW SLIDE C, after slide 19. Title: "What 'fixed instructions first' looks like". Chips: SPEED + POWER.
Two tall prompt diagrams side by side, each drawn as stacked blocks labeled with what the block contains.
Left header: "As built: event fields near the top".
  Blocks, top to bottom: "Intro" · "Baseline + weather, cargo, dispatch (changes every event)" · "How to weigh each field (rules)" · "Decision rules" · "Truck ID, corridor" · "Closing instruction".
  Draw a dashed line labeled "cache ends here" just inside the second block, at the text "Weather:". Shade every block below the line orange: "re-read on every new event: 392 of 506 tokens".
Right header: "Event last: rules first".
  Blocks: "Intro" · "How to weigh each field (rules)" · "Decision rules" · "Baseline + weather, cargo, dispatch (changes every event)" · "Truck ID, corridor" · "Closing instruction".
  Draw the dashed "cache ends here" line inside the fourth block. Shade only the blocks below it: "re-read: 140 of 506 tokens".
Bottom line: "On the Pi 4, per new event: 160 s and 772 J → 82 s and 416 J. Same words, same accuracy on llama-server."
Notes: "The prompt cache reuses everything up to the first token that differs from the last call. In my prompt, that was the weather line, near the top, so every new event re-read the whole rules block. Moving the event fields below the rules lets the rules stay cached. The text is the same apart from one word ('above' became 'below'). Re-check accuracy when you reorder: on llama-cpp-python, the reordered prompt changed one borderline answer."

NEW SLIDE D, after slide 19 and new slide C (so before "Do this, not that: small LLMs"). Title: "Classification in code, judgment in the model". Chip: ACCURACY.
Left header: "Asking the model to classify". Line: "Prompt stated: 'low' means ETA slip under 5.0 minutes. Input: 3.0 minutes." Code panel (Llama-3.1-8B):
"""
{"event": "fleet_dispatch_enrichment", "severity": "high", "signals": ["sustained_low_speed", "stop_go_index", "eta_slip"], "eta_impact": 3.0, "corridor": "I-95N", "truck_id": "truck-47"}
"""
Highlight "severity": "high" with the callout "expected low". Under it: "Severity wrong on 51% of calls (Llama-3.1-8B); across 15 models, 33-73%".
Right header: "The same decision in code". Code panel:
"""
if abs_engaged: return "high"
if g > HIGH_G_FLOOR: return "high"
if g <= LOW_G_CEILING:
    return "medium" if stop_go_index > HIGH_VOLATILITY_STOP_GO_INDEX else "low"
return "high" if stop_go_index > HIGH_VOLATILITY_STOP_GO_INDEX else "medium"
"""
Under it: "Exact every time, in microseconds. The model now only weighs weather, cargo and dispatch."
Notes: "A threshold is exact in code and approximate in a model. Even with the threshold written into the prompt, models put a 3-minute slip in the high bucket. Before I moved severity into code, 15 models got it wrong on 33-73% of calls. Now code computes it, and the model makes the one judgment code can't: whether rain, chemical cargo and schedule pressure together justify raising it."

NEW SLIDE E, after new slide D. Title: "Constrain the output with a grammar, and test the grammar". Chip: ACCURACY.
Left header: "Free text, with 'no prose' in the prompt". Two small code panels.
Qwen2.5-1.5B (22 of 30 parsed):
"""
Here is the JSON object:

{
  "event": "ETA slip",
  "severity": "high",
  "signals": ['sustained_low_speed', 'stop_go_index', 'eta_slip'],
  …
}
"""
Highlight "Here is the JSON object:" (callout "prose") and the single-quoted list (callout "not JSON").
Qwen2.5-0.5B (1 of 30 parsed):
"""
{"event": "<event_name>", "severity": "<low|medium|high>", … } {"event": "<event_name>", "severity": "<low|medium|high>", … } {"event": "<event_name>", …
"""
Callout: "repeats the template until it runs out of tokens".
Middle header: "With a grammar". Code panel (the triage card's grammar):
"""
root ::= "{\n"
  "  \"risk_synthesis\": \"" [^"]* "\",\n"
  "  \"escalation\": " ("\"raise\"" | "\"hold\"" | "\"lower\"") ",\n"
  "  \"truck_id\": " "\"truck-47\"" "\n"
  "}"
"""
Under it: "Qwen2.5-0.5B: 30 of 30. Qwen2.5-1.5B: 30 of 30. The truck ID can't be wrong: it's written into the grammar."
Right header: "Grammars fail silently too". Two short items:
"A stop sequence of '}' cut the closing brace off every answer: 0% valid"
"A thinking grammar that banned '<' ended the model's thinking at its first '<': 32 of 36 calls never answered"
Notes: "A grammar makes the shape impossible to get wrong, and it's the cheapest accuracy win in the study. But it's code, so test it: two of my bugs came from grammars. One cut the closing brace off every card. The other ended a model's thinking the moment it wrote a less-than sign, which is where the '36 of 36 never answered' I first reported came from."
```

## R5: "The greenest token is the one you never…" (new slide before slide 24)

Sources:
- calls and bytes: impact track row 28 and `tests/model/uplink_budget.py`;
- energy per truck-day: Fig. 4's inputs (calls × J per call);
- tokens generated: the 2026-10-05 runs (median 42);
- thinking: round 3, Qwen3-14B, call 9;
- re-read: Phi-3.5's tokenizer and `eval-results/edge-triage-event-last-pi4-20261005/`;
- accelerator: Table II.

```
Insert a new slide before slide 24 ("Where the energy savings actually came from"). Title: "The greenest token is the one you never…". Eyebrow: "WHERE THE SAVINGS CAME FROM".
Layout: a five-row ledger, drawn natively, one row per kind of token avoided, largest saving first. Each row has: the phrase completing the title (large, left); what did it; before → after (Roboto Mono); a measure chip.
Row 1. "…send to the model" | "Cheap-math gate" | "17,280 events → 23 LLM calls per truck-day (0 in 2.3 truck-days of normal driving)" | POWER
Row 2. "…send over the network" | "Keep raw telemetry home" | "9.2 MB per truck-day → ~4 KB per incident" | POWER
Row 3. "…generate" | "Code writes the card; thinking off" | "The model writes one judgment, ~42 tokens; the same Qwen3-14B call: 449 tokens with thinking, 125 without" | SPEED + POWER
Row 4. "…re-read" | "Fixed instructions first" | "392 → 140 prompt tokens per new event; Pi 4: 772 → 416 J" | SPEED + POWER
Row 5. "…compute on a slow chip" | "Use the accelerator" | "Pi 4 CPU 154 J → M4 Max GPU ~15 J per call" | POWER
Draw rows 1-2 visibly larger or bolder than rows 3-5. Under the ledger: "Energy = calls × joules per call. Rows 1-2 cut the calls and bytes by ~750× and ~2,300×; rows 3-5 cut each call by 2-10×."
Notes: "This is where the savings came from, in the order of their size. The greenest token is the one the model never sees: the gate stopped every event in two simulated truck-days of normal driving, and an incident takes about 23 calls instead of an LLM call every 5 seconds. Next, the bytes you never send. Then come the tokens inside each call: the ones code writes instead of the model, the reasoning you don't ask for, the prompt the cache doesn't re-read, and the hardware that does the work. Those matter, but each is worth 2-10×, not 1,000×."
```

## R6: renumber, recap tags, QA (send last)

```
1. Renumber all slides in order. The assumption eyebrows stay "ASSUMPTION 1 OF 10" … "10 OF 10"; the new slides keep "ASSUMPTION 3, UP CLOSE", "EXAMPLE" and "WHERE THE SAVINGS CAME FROM".
2. On the two "Do this, not that" slides, add after each item a small grey reference (caption size) to the slide that shows its example, using the new numbers:
   - Small LLMs: One bounded judgment → "One bounded judgment vs the whole job". Thinking off → the thinking slide. The model's own chat template → the chat-format slide. The whole job in one call → "Same model, same case: what came back". A quantization or runtime you haven't re-tested → the quantization slide. The server's default context size → the defaults slide.
   - Every LLM: Language judgment in the model; classification in code → "Classification in code, judgment in the model". Constrain the output with a grammar → "Constrain the output with a grammar, and test the grammar". Fixed instructions first, per-request data last → "What 'fixed instructions first' looks like". Many different test cases → the repeats slide. Make the LLM a classifier → "Classification in code, judgment in the model". Call it on every event → "The greenest token is the one you never…". Benchmark one repeated input → the "cost of a repeat" slide. Compare watts → the energy slide.
3. QA, report as a list:
   a. Slide count: 34 (28 + 6 new). No two full-bleed plates adjacent.
   b. Every code panel matches my text character for character, apart from cuts at "…". Model mistakes are preserved.
   c. Not on any slide: "36 of 36", "80-90%", "echo". No planning tags.
   d. Every example has its measure chip(s); every new slide has presenter notes.
   e. The "data pending" chips are unchanged.
Fix anything that fails, then summarize what you changed.
```
