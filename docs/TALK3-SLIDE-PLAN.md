# Talk 3 — "When Your Pulsar Function Speaks English" — Slide Plan

No deck built yet — this is the plan the deck gets built from, generated from
`docs/TALK3-OUTLINE.md` on 2026-10-03 with the `tech-slide-planner` skill and
reworked on 2026-10-04 against the accepted title and abstract (below).
Every fact below cites the repo file that backs it, same discipline as
`docs/TALK1-SLIDE-PLAN.md` and `docs/TALK2-SLIDE-PLAN.md`. When building
the deck, paste this plan with `docs/TALK2-DECK-BUILD-PROMPT.md`'s general
rules (sections 1–5).

**Accepted title:** "When Your Pulsar Function Speaks English: Inline LLM
Inference for Real-Time Stream Enrichment"

**Accepted abstract (verbatim):** "Here's a trick: if you embed a tiny LLM
inside a stream processing function and only fire it on the interesting
events, you get AI-enriched streams on a single CPU core. I'll demo it live,
show the resource profile, and share the prompt patterns that actually work at
stream speed."

**Where each promise is kept:**

| Promise | Slides |
|---|---|
| A tiny LLM embedded inside a stream processing function ("inline") | 7, 11, 12 |
| Only fire it on the interesting events | 5, 10 |
| On a single CPU core | 21, 22, 25 |
| Demo it live | 25 |
| Show the resource profile | 21, 22 |
| Prompt patterns that work at stream speed | 16, 19 (and checking the output) |

"Speaks English" is kept by the LLM writing English inside the Function; the
voice (slides 23–24) is a bonus the abstract doesn't promise. Gemma-3-4B-it is
"small" more than "tiny" — say "small" on stage.

**Style profile: `DATADOG_MARKETING_DECK`** — the same native slide types
Talks 1 and 2 use. This profile's `Metric` ("Code + KPI") type is built for
code with a number beside it; the sequence slides use its `Timeline` type.
Plate types (`Title`, `Section`, `Quote`, `Product`, `Statement`, `Closing`)
are never placed back to back and carry only text.

40-minute slot: **25 narrative slides** (3–27) planned at 38 minutes, leaving 2
minutes of slack for the live demo, plus untimed Waitroom, Title and Thank You.

## Structure
0. **Cold open** (slide 3): the voice, with no context.
1. **Act 1 — Where the Words Come From** (4–7): only the interesting events,
   the three trucks, the whole system.
2. **Act 2 — The Pulsar Function** (8–13): the Functions model, the
   aggregation trick, the real code, the model living inside it, the honest
   shortcut.
3. **Act 3 — Code Decides, the LLM Narrates** (14–19): the rule, the prompt
   patterns, the model pick, two blooper slides.
4. **Act 4 — On One CPU Core** (20–22): the resource profile; what one core
   buys you.
5. **Act 5 — Giving It a Voice** (23–24): Piper at arm's length, pronunciation
   fixes.
6. **Act 6 — See It Live** (25): the live demo, one CPU core.
7. **Close** (26–27): the recipe, generalized; the trilogy closer.

## Changes since the 2026-10-03 plan
- **Re-aimed at the accepted abstract.** New: slide 12 (the model lives inside
  the Function), Act 4 (resource profile, one CPU core). Reworked: slide 5
  (gating, with numbers), 16 (prompt patterns for stream speed), 19 (what
  narrate-only does and doesn't buy), 25 (live, not recorded).
- **The model now runs inside the Function.** `GlobalSynthesisFunction` with
  `llm_backend=inprocess` holds Gemma in llama-cpp-python on `self`, loaded
  once (`InProcessLlmBackend`, `docs/CANON.md`). Previously a fresh llama.cpp
  process per call.
- **"No GPU" is now true.** The old take ran llama.cpp with no device flags,
  which on a Mac means the Metal GPU. The demo now runs CPU only, one thread
  (`deploy/talk3-windows/tier2.sh`).
- **Act 4 (voice) shrank from 4 slides to 2** (now Act 5): the divider and
  "The Voice Is the Fast Part" went; Piper's speed moved into the resource
  profile (slide 21). The optional Pi slide folded into slide 22.
- **Title** is the accepted one; the subtitle open item is gone.

## Open items
- **New demo take: recorded, needs sign-off.** Take 4
  (`deploy/recordings/talk3-demo-20261002-174855.mp4`) ran on the GPU through
  the old subprocess path. Take 5 (`talk3-demo-20261004-182716.mp4`, 54.6 s,
  recorded on the M4 Max with the current defaults: in-process, one CPU thread)
  replaces it; transcript in `talk3-demo-20261004-182716.txt` beside it and in
  `talks/talk3-pulsar-speaks-english/TODO-DEMO-RECORDING.md`. Recordings are
  gitignored, so the file is only on the M4 Max. [NEEDS: your review of take 5,
  or a re-take on the external-display machine]
- **Pi run.** Slide 22's Pi-class number is a prediction from benchmarks. A
  real run on a Pi, in-process on one thread, turns it into "I tried it" —
  whatever it shows. [NEEDS: Pi run, `LLM_TIMEOUT_SECONDS=600`]
- **"Before" audio clips** for slide 24 (raw Piper, normalization off).
- **Fact check in the take.** If the new take's log shows a retry or the
  plain-code fallback, slide 25's narration should say so.
- **Gating ratio on real data.** Slide 5's 28–33% comes from a simulator built
  to be incident-heavy; Talk 1 calls its bandwidth claim "inferred, not
  measured." A real ratio needs a live Edge Triage run's counts.
- **Repo URL** for slide 27, same open item as Talk 2.

---

### Slide 1 — Welcome! We'll begin shortly.
**Label:** Waitroom

**On-screen text:**
```
When Your Pulsar Function Speaks English
Grab a coffee and settle in.
```

**Speaker notes:** Untimed lobby slide, same convention as Talks 1 and 2.

### Slide 2 — When Your Pulsar Function Speaks English
**Label:** Title
**Suggested Layout:** Title (plate)
**Visual Manifest:** Type: `Typography_Only` · Spec: title, subtitle, name.

**On-screen text:**
```
When Your Pulsar Function Speaks English
Inline LLM Inference for Real-Time Stream Enrichment
David Kjerrumgaard
Apache Pulsar Committer
```

**Speaker notes:** Untimed. Say nothing about the talk yet — advance
straight into the cold open.

### Slide 3 — Listen First
**Label:** Cold Open
**Suggested Layout:** Content — a sparse, near-empty content slide (not a
plate, since it follows the Title plate) with an embedded audio player.
**Core Message:** A streaming pipeline just spoke a traffic warning out loud.
**Visual Manifest:**
- Type: `Typography_Only`
- Spec: white slide, a single audio control centered; after playback, one
  line fades in. Audio: the I-95N warning from take 5 (one CPU core),
  `deploy/recordings/.talk3-audio-20261004-182716/001-I-95N.wav` (18.6 s):
  "Drivers approaching I-95 North, be advised that there's a slowdown affecting
  multiple trucks within the corridor. We're recommending you reroute traffic
  around I-95 North due to a correlated slowdown, particularly with trucks 47,
  12, and 31, who are experiencing significant delays."

**On-screen text:**
```
"That was a Pulsar Function talking."
```

**Speaker notes:** Play the clip before saying anything. Let it finish.
Then: "That was a Pulsar Function talking. A small LLM inside it wrote that
sentence, on one CPU core, no GPU. By the end of this talk you'll have seen
every piece that made it say that, and it's less than you think." Don't
explain how yet; the next slide steps back to where the facts in that
sentence came from.

**Time:** Cold open, ~2 min.

## Act 1 — Where the Words Come From

### Slide 4 — Where the Words Come From
**Label:** Section: Where the Words Come From
**Suggested Layout:** Section (plate)
**Visual Manifest:** Type: `Typography_Only`

**On-screen text:**
```
Where the Words Come From
```

**Speaker notes:** Divider. "Before the voice, the facts."

**Time:** Act 1, ~0.25 min.

### Slide 5 — Only the Interesting Events
**Label:** Gates Before the LLM
**Suggested Layout:** Content
**Core Message:** Cheap math decides which events are worth an LLM call; that
is what makes one CPU core enough.
**Visual Manifest:**
- Type: `Mermaid_Architecture`
- Spec: left to right, a funnel with a count on each edge. Inside a "Truck
  (Pi-class)" boundary: `truck-telemetry` (720 readings) →
  `TelemetryCoprocessorFunction` (cheap math: slowdown check + ETA-slip gate)
  → (201–241 pass) → `LlmTriageFunction` (small LLM writes the card) → gate
  `severity = high?` → yes: `enrichment-cards` (exits the boundary) / no:
  local-only topic. Then, outside: `enrichment-cards` → Tier 2 Function →
  "1 LLM call per 3 cards". Highlight the `enrichment-cards` edge.

**On-screen text:**
```
720 readings → ~1 in 3 pass cheap math → only "high" leaves the truck
Tier 2: 1 LLM call per incident, not per event
```

**Speaker notes:** This is the trick in the abstract: only fire the LLM on
the interesting events. On every truck, Talk 1's Edge Triage Pipeline puts
cheap math first: a slowdown check and an ETA-slip gate. In a simulated run
— 12 trucks, 60 ticks, 720 readings — 201 to 241 pass, about one in three.
And that simulator is built to be full of incidents, so a real road would be
quieter; we haven't measured a real one. Only those reach a small LLM, and
only cards that come out `high` cross the cellular link. Tier 2 then calls
its LLM once per incident — three cards, one call. Hold on to that: in Act 4
you'll see one core writes about five warnings a minute. Calling the model
rarely is what makes that enough. Backing:
`eval-results/talk3-single-core-m4max-20261004/gating_counts.txt`;
`docs/TALK1-SLIDE-PLAN.md` slides 19–21; `deploy/README.md` "Edge Triage
Pipeline".

**Time:** Act 1, ~2 min.

### Slide 6 — One Truck Is an Anecdote
**Label:** Three Cards, One Corridor
**Suggested Layout:** Metric
**Core Message:** One card is a truck's bad day; three on the same corridor
is an incident.
**Visual Manifest:**
- Type: `Code_Block`
- Spec: code side: the three cards from `deploy/talk3-demo-cards.jsonl`,
  trimmed to the fields shown below. KPI side: `3 trucks · I-95N`, delta
  line `2 high · 1 medium`.

**On-screen text:**
```json
{"truck_id": "truck-47", "corridor": "I-95N", "severity": "high",   "eta_impact": 9.0}
{"truck_id": "truck-12", "corridor": "I-95N", "severity": "high",   "eta_impact": 7.0}
{"truck_id": "truck-31", "corridor": "I-95N", "severity": "medium", "eta_impact": 6.0}
```

**Speaker notes:** This is what arrives in the cloud: three cards, three
trucks, all on I-95N. Tier 2's question is the one a dispatcher would ask:
is this one truck's problem, or the whole corridor? And do we tell drivers
to go around? Notice truck-31 is medium, and the truck called truck-12 —
both matter later, in the blooper reel. Be straightforward: this is a
replayed scenario, not three cards from Talk 1's live run (the demo slide
explains why). Next: what happens to these three cards, end to end.

**Time:** Act 1, ~1.5 min.

### Slide 7 — The Whole System on One Slide
**Label:** Two Topics, One Function, One Speaker
**Suggested Layout:** Content
**Core Message:** Two topics, one Function with the model inside it, one
consumer — all of it on one laptop, the LLM on one CPU core.
**Visual Manifest:**
- Type: `Mermaid_Architecture`
- Spec: `enrichment-cards` topic → `GlobalSynthesisFunction` (Pulsar
  Function, `localrun`) → [inside its boundary: plain code decides →
  Gemma-3-4B-it in llama-cpp-python, loaded once, 1 CPU thread, words it] →
  `incidents` topic → speaker consumer → Piper subprocess → speaker icon.

**On-screen text:**
```
enrichment-cards → Function [code decides · LLM words] → incidents → voice
```

**Speaker notes:** Here's every box. Cards land on `enrichment-cards`. One
Pulsar Function, `GlobalSynthesisFunction`, reads them, makes the
decisions in plain code, and has a small model word the result — and the
model is inside the Function, not a service it calls. That lands on
`incidents` as an `IncidentSynthesis`. A plain consumer reads `incidents`
and hands the sentence to Piper, which speaks it. The next acts take it one
box at a time, starting with the Function. Backing: `deploy/README.md`
topology diagram; `function.py`.

**Time:** Act 1, ~1.5 min.

## Act 2 — The Pulsar Function

### Slide 8 — The Pulsar Function
**Label:** Section: The Pulsar Function
**Suggested Layout:** Section (plate)
**Visual Manifest:** Type: `Typography_Only`

**On-screen text:**
```
The Pulsar Function
```

**Speaker notes:** Divider.

**Time:** Act 2, ~0.25 min.

### Slide 9 — One Message In, Zero or One Out
**Label:** What a Pulsar Function Is
**Suggested Layout:** Metric
**Core Message:** A Pulsar Function is a class with one method, and
config arrives through `--user-config`, not a rebuild.
**Visual Manifest:**
- Type: `Code_Block`
- Spec: code side: the signature, then the real `localrun` call from
  `deploy/run_tier2_localrun.sh` (`--py`/`--broker-service-url` lines
  elided), then the demo's user-config. KPI side: `1 in → 0 or 1 out`.

**On-screen text:**
```python
class GlobalSynthesisFunction:
    def process(self, input: str, context) -> str | None:
        ...
```
```
pulsar-admin functions localrun \
  --classname talk3_pulsar_speaks_english.function.GlobalSynthesisFunction \
  --inputs persistent://public/default/enrichment-cards \
  --output persistent://public/default/incidents \
  --user-config '{"llm_backend": "inprocess", "threads": "1", "corridor_threshold": "3", ...}'
```

**Speaker notes:** For anyone new to Pulsar Functions: a class with
`process(self, input, context)`. One message in; return a value and it's
published, return `None` and nothing is. Deployed here with
`pulsar-admin functions localrun`; managed mode later is the same class.
Model path, how the model runs, how many threads, and the corridor threshold
all come through `--user-config`, so swapping models — or going from four
cores to one — is a config change. That "one in, zero or one out" shape is
fine for Talk 1's per-truck work. Tier 2 has a problem with it, which is the
next slide. Backing: `function.py`; `deploy/run_tier2_localrun.sh`;
`deploy/talk3-windows/tier2.sh`.

**Time:** Act 2, ~1.5 min.

### Slide 10 — Functions Are Per-Message; Tier 2 Needs a Crowd
**Label:** The Accumulator Trick
**Suggested Layout:** Timeline
**Core Message:** A long-lived Function instance can keep a per-corridor
tally on `self` and stay silent until enough trucks report.
**Visual Manifest:**
- Type: `Mermaid_Sequence`
- Spec: four numbered steps: (1) truck-47 card → accumulator I-95N = 1 →
  return `None`; (2) truck-12 card → 2 → `None`; (3) truck-31 card → 3 =
  threshold → `synthesize()`; (4) clear I-95N, publish to `incidents`.
  Threshold 3 is the demo's `CORRIDOR_THRESHOLD` (code default 2).

**On-screen text:**
```
1 card → hold   2 cards → hold   3 cards → synthesize   → publish
```

**Speaker notes:** You can't call something corridor-wide from one card.
Functions are per-message, but Function instances are long-lived
processes, not spun up per message. So the class keeps a dictionary on
`self`: corridor → cards so far. Each call appends and returns `None`
until the corridor hits the threshold — three for this demo, one per
truck — then it synthesizes, clears that corridor, and returns one
`IncidentSynthesis`. Notice what that means for the LLM: two of every
three messages never touch it. Next: the actual code, which is shorter
than this explanation. Backing: `function.py` module docstring;
`deploy/talk3-windows/tier2.sh` (`CORRIDOR_THRESHOLD=3`).

**Time:** Act 2, ~1.5 min.

### Slide 11 — The Whole Function Fits on a Slide
**Label:** process(), In Full
**Suggested Layout:** Metric
**Core Message:** The Pulsar part is the smallest part of this system.
**Visual Manifest:**
- Type: `Code_Block`
- Spec: code side: `process()` verbatim from `function.py`. KPI side:
  `12 lines` (the method's own line count, blank lines included).

**On-screen text:**
```python
def process(self, input: str, context) -> str | None:
    backend = self._backend or self._build_backend(context)
    card = from_json(EnrichmentCard, input)
    cards = self._accumulator[card.corridor]
    cards.append(card)

    if len(cards) < self._corridor_threshold:
        return None

    synthesis = synthesize(cards, backend, config=self._config)
    self._accumulator[card.corridor] = []
    return to_json(synthesis) if synthesis is not None else None
```

**Speaker notes:** That's the whole Pulsar Function. Build the model
backend once from user-config, parse the card, add it to its corridor,
return `None` until the threshold, then hand off to `synthesize()` and
reset. Everything interesting — the decision, the wording — lives in
`synthesize()`, which has no Pulsar import at all and is unit-tested
without a broker. That first line is where the model comes in, and it's
the next slide. Backing: `function.py`.

**Time:** Act 2, ~1.5 min.

### Slide 12 — The Model Lives Inside the Function
**Label:** Inline Inference
**Suggested Layout:** Metric
**Core Message:** The model loads once and stays on `self`, next to the
accumulator; every call after the first skips the load and the prompt's
fixed instructions.
**Visual Manifest:**
- Type: `Code_Block`
- Spec: code side: the `inprocess` branch of `_build_backend()` in
  `function.py`, trimmed as below. KPI side: `15.5 s → 12.0 s` per warning,
  delta line `one CPU core · reloaded vs. kept`.

**On-screen text:**
```python
# _build_backend(), first message only
backend = InProcessLlmBackend(        # llama-cpp-python: llama.cpp in-process
    model_path,
    threads=1,                        # one CPU core
    gpu_layers=0,                     # no GPU
)
self._backend = backend               # kept on self, like the accumulator
```

**Speaker notes:** "Inline" in the title means this. The model isn't a
service the Function calls; it's loaded into the Function's own process by
llama-cpp-python, the Python binding for llama.cpp — still C++ underneath,
the way numpy is. It loads on the first message and stays on `self`, the
same way the accumulator does. Two things stop happening per call: loading
the model, about a second, and re-reading the prompt's fixed instructions —
98 of the prompt's 361 tokens are the same every time, and the binding
reuses them from the last call. On one core, that took a warning from 15.5
seconds to 12.0, same build, same model. Honest history: Talk 3 started out
shelling out to the llama.cpp binary for every message, and that's still in
the repo as the other backend. Backing:
`eval-results/talk3-single-core-m4max-20261004/README.md` (round 2,
`fresh_t1` vs. `kept_t1`); `InProcessLlmBackend` in
`shared/llm-inference/src/llm_inference/client.py`; `docs/CANON.md`.

**Time:** Act 2, ~2 min.

### Slide 13 — Honest About the Shortcut
**Label:** Demo vs. Production
**Suggested Layout:** Comparison
**Core Message:** An in-memory tally is fine on stage; production needs
windows and saved state, and every instance carries its own model.
**Visual Manifest:**
- Type: `Bar_Comparison`
- Spec: non-numeric two-column contrast. Left ("This demo"): in-memory dict
  on `self`; flushes only on card count; lost on restart; one instance, one
  model in memory. Right ("In production"): event-time windows; a
  time-based flush; state that survives a restart; memory sized per
  instance.

**On-screen text:**
```
This demo                      In production
in-memory, on self             saved state
flush on card count            flush on time, too
lost on restart                survives restart
1 instance = 1 model (5.3 GB)  size memory per instance
```

**Speaker notes:** Say plainly what this skips: no event-time windows, no
watermarks, no wall-clock flush, and the tally is gone if the instance
restarts. A corridor stuck at two cards waits forever. The repo's other
runtime shape, `pulsar_adapter.py`, does have a time-based flush. And the
cost of "inline": each Function instance holds its own copy of the model,
5.3 GB here, so scaling out with parallelism multiplies memory. Fine for a
demo; name it before someone in Q&A does. Now, the more interesting
question: who decides what the warning says? Backing: `function.py`
docstring; `pulsar_adapter.py`;
`eval-results/talk3-single-core-m4max-20261004/README.md` (peak RSS).

**Time:** Act 2, ~1.25 min.

## Act 3 — Code Decides, the LLM Narrates

### Slide 14 — Code Decides, the LLM Narrates
**Label:** Section: Code Decides, the LLM Narrates
**Suggested Layout:** Section (plate)
**Visual Manifest:** Type: `Typography_Only`

**On-screen text:**
```
Code Decides, the LLM Narrates
```

**Speaker notes:** Divider.

**Time:** Act 3, ~0.25 min.

### Slide 15 — The Decision Is Plain Python
**Label:** The Rule
**Suggested Layout:** Metric
**Core Message:** Scope and reroute are decided by plain code before
the model is ever called.
**Visual Manifest:**
- Type: `Code_Block`
- Spec: code side: the two functions below from `synthesizer.py`, type
  hints and docstrings elided, the reroute-detail wording replaced by
  `...`. KPI side: `0 LLM calls to decide`.

**On-screen text:**
```python
def decide_scope(cards):
    truck_ids = {card.truck_id for card in cards}
    return SCOPE_SINGLE_TRUCK if len(truck_ids) <= 1 else SCOPE_CORRIDOR_WIDE

def decide_reroute(cards, scope):
    if scope != SCOPE_CORRIDOR_WIDE:
        return False, None
    if not any(card.severity.lower() == HIGH_SEVERITY for card in cards):
        return False, None
    ...  # build reroute_detail, return True
```

**Speaker notes:** Same rule as Talk 1's edge: cheap code decides, the LLM
only puts it into words. One distinct truck means single-truck; two or
more means corridor-wide. Reroute only if it's corridor-wide and at least
one truck reported high. Explainable, testable, free, and the model can't
overrule it because it never sees the question. Our three cards: three
trucks, two high, so corridor-wide and reroute. So what do we actually ask
the model? Backing: `synthesizer.py`; `docs/CANON.md`.

**Time:** Act 3, ~1.5 min.

### Slide 16 — Prompt Patterns for Stream Speed
**Label:** The Prompt
**Suggested Layout:** Content — overriding the `Metric` default: four
patterns, not one KPI.
**Core Message:** Hand over a finished verdict, show a placeholder not an
example, keep the fixed part first and the answer short: on one core, every
token costs.
**Visual Manifest:**
- Type: `Code_Block`
- Spec: the excerpt below from `SYNTHESIS_WARNING_PROMPT` in
  `prompting.py`, with four callouts down the right: ① "(already decided)";
  ② the placeholder shape; ③ a bracket over the fixed instructions, "same
  every call → reused"; ④ "2-3 sentences", "~60 tokens out".

**On-screen text:**
```
You are generating a short, calm, spoken-style ... warning (2-3 sentences) ...
Always name the corridor explicitly in your warning ...
Scope (already decided): {scope}
Reroute recommended (already decided): {reroute_recommended}
...
Shape (a placeholder, not a real answer): {"spoken_warning": "<your warning text here>"}
```

**Speaker notes:** Four patterns. One: every decision arrives "already
decided," so the model narrates instead of judging. Two: the example shape
is a placeholder; small models shown a realistic sentence copy it no matter
the input. Three and four are about speed. On one core, reading the prompt
is most of the time — about three quarters of a call in our first
measurement — so the fixed instructions go first, where the in-process
model can reuse them from the last call, and the facts go after. And the
answer is bounded: "2-3 sentences," about 60 tokens. Output length moves
latency more than model choice does — next slide. Backing: `prompting.py`
module docstring; `eval-results/talk3-single-core-m4max-20261004/README.md`
(round 1 phase times, round 2 prefix reuse).

**Time:** Act 3, ~2 min.

### Slide 17 — Why Gemma-3-4B-it
**Label:** Talk 2 Callback: The Model Pick
**Suggested Layout:** Comparison
**Core Message:** The model that won Talk 1's task is the slowest one here,
because it writes four times as much.
**Visual Manifest:**
- Type: `Bar_Comparison`
- Spec: two columns, Pi 4 Tier 2 numbers from Talk 2. Left "Gemma-3-4B-it
  (picked)": p50 43.7 s, ~33 words. Right "Phi-3.5-mini-instruct (Edge
  Triage Pipeline winner)": p50 186.0 s, ~115 words.

**On-screen text:**
```
Gemma-3-4B-it          Phi-3.5-mini-instruct
p50 43.7 s (Pi 4)      p50 186.0 s (Pi 4)
~33 words              ~115 words
```

**Speaker notes:** If you saw Talk 2: same evaluation funnel, run on this
task. Both passed its accuracy checks. The difference is speed, and it
isn't the hardware or the model's raw throughput — Phi-3.5-mini pads a
"2–3 sentence" answer to about 115 words, Gemma writes about 33. Same Pi,
same quantization, and the ranking flips with the task. That's pattern
four from the last slide, measured. Those accuracy checks were string
matches, though; the next two slides are what they missed. Backing:
`docs/TALK2-OUTLINE.md` "Final model recommendation";
`docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md` "Cross-task latency
comparison".

**Time:** Act 3, ~1.25 min.

### Slide 18 — What Small Models Say When You Let Them
**Label:** Blooper Reel: The Models
**Suggested Layout:** Three-up — three short cards, one per blooper (no
affinity-map entry for a card row; Three-up is the closest content type).
**Core Message:** Small models fail in specific, repeatable ways, and each
one changed the prompt or the token budget.
**Visual Manifest:**
- Type: `Typography_Only`
- Spec: three cards, one line each: "The echo" (350M models), "The silent
  corridor" (Qwen2.5-3B), "Thinking out loud" (Qwen3-8B).

**On-screen text:**
```
The echo — hands back the prompt, placeholder and all
The silent corridor — drops "I-95N" when it judges things minor
Thinking out loud — runs out of tokens before the answer
```

**Speaker notes:** Quick and light. The echo: LFM2.5-350M and
Granite-4.0-H-350M returned the prompt itself, placeholder included, every
time. The silent corridor: Qwen2.5-3B left out "I-95N" in 100% of
single-truck warnings and 0% once a reroute was involved — deciding for
itself what was too minor to name. One blunt prompt line fixed it; that's
the "always name the corridor" on the prompt slide. Thinking out loud:
Qwen3-8B reasons in prose and ran out of its 110-token budget before
reaching the JSON. But the bloopers that matter most came from the model we
picked. Backing: `docs/TALK2-350M-PROMPT-ECHO.md`;
`docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md` rows 17, 22.

**Time:** Act 3, ~1.25 min.

### Slide 19 — Narrating Isn't the Same as Getting It Right
**Label:** Check What It Says
**Suggested Layout:** Comparison
**Core Message:** Keeping the LLM out of the decision keeps it from
deciding wrong, not from saying something wrong — so plain code checks
every number it says against the facts, and words the warning itself if
the model gets it wrong twice.
**Visual Manifest:**
- Type: `Bar_Comparison`
- Spec: left "What it said (hand-checked, ~1 in 4)": "9 to 12 minutes" (no
  card says 12 — truck-12?); "one reporting high severity" (two were); a
  recommended reroute left out. Right "What code does now": the three checks
  (minutes ∈ the cards' delays; high-severity count; reroute and corridor
  named) → retry once → plain-code warning. Footer: "Caught 14 of 62 real
  warnings; missed 'impacting all lanes'."

**On-screen text:**
```
What it said — about 1 in 4            What code does now
"9 to 12 minutes"   (truck-12?)        every number checked against the facts
"one ... high severity" (two were)     fail → ask again → fail → plain code says it
reroute left out                       caught 14 of 62; not "all lanes"
```

**Speaker notes:** Two kinds of wrong. Ours first, briefly: our reroute
code once said "high-severity" for all three trucks when any one was high,
and Gemma read it out faithfully — we fixed the code. Then the model's own:
reading every warning by hand, about one in four has a factual slip — 7 of
30 in one run, 6 of 25 in another. The best one: "9 to 12 minutes." No card
says 12. One of the trucks is called truck-12. Twice it dropped the reroute
code had recommended. Talk 2's accuracy check passed all of these, because
it matched strings. So now plain code checks what the model says, the same
way plain code made the decision: every number of minutes has to be one of
the cards' delays, a count of high-severity trucks has to match, the reroute
and the corridor have to be there. Fail, and the Function asks once more —
another 12 seconds on one core. Fail again, and code words the warning
itself: stiffer, never wrong. Against the 62 different warnings from today's
runs, it caught 14, every one a real slip, and it misses what has no number
in it — "impacting all lanes." Now: what all this costs on one core.
Backing: `fact_check.py`; `tests/test_fact_check.py`;
`docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md` rows 14, 27;
`eval-results/talk3-single-core-m4max-20261004/README.md` (both accuracy
sections; "Fact check").

**Time:** Act 3, ~1.75 min.

## Act 4 — On One CPU Core

### Slide 20 — On One CPU Core
**Label:** Section: On One CPU Core
**Suggested Layout:** Section (plate)
**Visual Manifest:** Type: `Typography_Only`

**On-screen text:**
```
On One CPU Core
```

**Speaker notes:** Divider. "The abstract promised a resource profile.
Here it is."

**Time:** Act 4, ~0.25 min.

### Slide 21 — The Resource Profile
**Label:** One Warning, Three Ways
**Suggested Layout:** Stats — a four-row table, the one-core row
highlighted.
**Core Message:** One CPU core writes a warning in 12 seconds using one
core and 5.3 GB; the voice takes a fraction of a second.
**Visual Manifest:**
- Type: `Typography_Only`
- Spec: table, M4 Max, Gemma-3-4B-it Q4_K_M kept in the Function, median of
  10 calls: rows "GPU (Metal)", "4 CPU threads", "**1 CPU thread**"; columns
  seconds per warning, cores busy, memory. Footer row: "Piper: 11 s of
  audio in 0.16 s (M4)".

**On-screen text:**
```
                  per warning   cores busy   memory
GPU (Metal)        0.7 s        0.08         2.9 GB
4 CPU threads      3.5 s        3.99         5.3 GB
1 CPU thread      12.0 s        1.00         5.3 GB
Piper voice: 11 s of audio in 0.16 s
```

**Speaker notes:** Same model, same Function, three ways to run it, on
this laptop. The GPU does it in under a second — and that's not the point
of this talk. On one CPU thread: 12 seconds per warning, and "cores busy"
is CPU time over wall time, exactly 1.00, so one thread really is one core.
Memory is 5.3 GB either way on the CPU. And the voice is not the slow part:
Piper speaks 11 seconds of audio in 0.16 seconds — measured earlier on an
M4, not in this run, so read it as an order of magnitude. Backing:
`eval-results/talk3-single-core-m4max-20261004/README.md` (round 2:
`kept_gpu`, `kept_t4`, `kept_t1`); package README (Piper speed).

**Time:** Act 4, ~2.5 min.

### Slide 22 — What One Core Buys You
**Label:** The Honest Version
**Suggested Layout:** Stats — three stat tiles.
**Core Message:** One core is about five warnings a minute: enough because
the gates in front keep the LLM rare. My first one-core attempt was slower
than this, and a Pi-class core will be slower still.
**Visual Manifest:**
- Type: `Typography_Only`
- Spec: three tiles: `~5 / min` (warnings per core, M4 Max); `29 s` (first
  attempt: subprocess per call, Homebrew build); `~1 min` (Pi 5-class core,
  predicted — not run). [NEEDS: Pi run result to replace the prediction]

**On-screen text:**
```
~5 / min    warnings per CPU core (12 s each)
29 s        my first one-core attempt
~1 min      predicted on a Pi 5-class core (not yet run)
```

**Speaker notes:** Twelve seconds a warning is about five warnings a minute
per core. That's why slide 5 mattered: fire the model on every reading and
one core drowns; fire it once per incident and one core keeps up. Two
honest numbers. My first single-core attempt — a new llama.cpp process per
message, with Homebrew's generic build — took 29 seconds a warning. Moving
the model into the Function and building llama.cpp for this machine got it
to 12. And the edge: benchmarks put a Pi 5-class core about four to five
times slower than this one, so about a minute a warning, close to the
backend's 60-second default timeout. I haven't run that yet; if you're
watching a recording, check the repo. [If the Pi run happens, replace this
with what it showed — slow or failed, say so.] Backing:
`eval-results/talk3-single-core-m4max-20261004/README.md` (headline table;
round 1); `eval-results/phone-proxies/pi5/20261003T184429Z/` and
`iphone-flagship/A-cpu-threads-20261004T064452Z/` llama-bench `-t 1`
(Gemma-3-4B-it: prompt 7.4 vs. 35.3 tok/s, output 3.3 vs. 15.1 tok/s).

**Time:** Act 4, ~2 min.

## Act 5 — Giving It a Voice

### Slide 23 — Piper, at Arm's Length
**Label:** TTS as a Separate Process
**Suggested Layout:** Content
**Core Message:** The Function wrote the words; Piper reads them out — a
separate, GPL-licensed process downstream, never imported.
**Visual Manifest:**
- Type: `Mermaid_Architecture`
- Spec: `incidents` topic → `speaker.py` (plain Pulsar consumer) →
  subprocess → `piper` (own venv, GPL-3.0) + voice `.onnx` → WAV →
  `afplay` / `aplay`. A dashed boundary labelled "this repo" around only the
  consumer.

**On-screen text:**
```
The Function wrote it. Piper reads it.
Piper (GPL-3.0) — own venv, subprocess only · Voice: norman (public domain)
```

**Speaker notes:** To be precise about the cold open: the Function wrote
that sentence; Piper read it out. The speaker is a plain Pulsar consumer,
not a Function, because playing audio is a side effect on whichever machine
has the speakers. Piper — `piper-tts`, the OHF-Voice/piper1-gpl project —
is GPL-3.0; the MIT original was archived in October 2025. So it's never a
dependency: it lives in its own venv and we run it as a separate process.
Voices have their own licenses too: this demo uses `norman`, public-domain
LibriVox recordings; avoid `ryan` and the `hfc` voices (non-commercial) and
`lessac`. One more surprise: Piper doesn't know what "I-95N" means.
Backing: `speaker.py` and `speech.py` docstrings; package README "Speaking
the warning."

**Time:** Act 5, ~1.5 min.

### Slide 24 — TTS Doesn't Know What I-95N Means
**Label:** Normalize Before You Speak
**Suggested Layout:** Comparison
**Core Message:** A few lines of plain code fix what TTS mispronounces.
**Visual Manifest:**
- Type: `Bar_Comparison`
- Spec: two columns, each with an audio control. Left "Raw":
  "I-95N" → "eye ninety-five *en*"; "ETA" → "ee-ta". Right "Normalized":
  "I-95 North"; "E T A". [NEEDS: the two "before" audio clips]

**On-screen text:**
```
I-95N  → "eye ninety-five en"     I-95 North
ETA    → "ee-ta"                  E T A
```

**Speaker notes:** Play the raw clip, then the fixed one. Piper reads the
direction letter as a letter and "ETA" as a word — confirmed against
Piper's own phonemizer, not guessed. The fix is `normalize_for_speech()`:
two regexes and a whitespace collapse, run before every Piper call. More
plain code doing exactly one job, same pattern as the decision code. Now,
all of it, live. Backing: `normalize_for_speech()` in `speech.py`.

**Time:** Act 5, ~1.25 min.

## Act 6 — See It Live

### Slide 25 — See It Live
**Label:** Live Demo
**Suggested Layout:** Content — switch to the terminal windows; the slide
itself is only the fallback's frame.
**Core Message:** Three cards in, a decision by code, a sentence by the
model on one CPU core, a voice out — live.
**Visual Manifest:**
- Type: `[NEEDS: new visual type not yet in the supported list]` — live
  screen share of the three windows (`deploy/talk3-windows/cards.sh`,
  `decision.sh`, `spoken.sh`), plus a CPU meter showing one core busy
  [NEEDS: pick the meter — Activity Monitor's CPU history or `htop`].
  Fallback: take 5, `deploy/recordings/talk3-demo-20261004-182716.mp4`
  (54.6 s, 1314×876, with audio), embedded video.

**On-screen text:**
```
Replayed cards → live Function → live model (1 CPU core) → live voice
```

**Speaker notes:** Run it live: start `replay.sh`. Narrate as it goes: the
three cards arriving three seconds apart; the "Decided by code" panel —
corridor-wide, three trucks, reroute; the CPU meter — one core pinned for
about 15 seconds on this first incident, since the model's cache is empty;
then "Worded by the LLM," and the voice. Be upfront: the cards are
replayed, because in a live Talk 1 run only truck-47 has trip context that
reaches `high`, so Tier 2 would only ever see one truck. Everything after
the replay is live. If anything fails, switch to the recorded take and say
so. Before the session: start the broker and the four windows, and check
`tier2.sh`'s log shows `llm_backend=inprocess` and one thread. Backing:
`deploy/README.md` "Talk 3 demo"; `deploy/talk3-windows/tier2.sh`.

**Time:** Act 6, ~4 min.

## Close

### Slide 26 — The Recipe
**Label:** Gate, Aggregate, Decide, Word, Speak
**Suggested Layout:** Timeline
**Core Message:** Gate with cheap math, aggregate with a Function, decide in
code, word with a small LLM inside the Function, speak with TTS — swap the
domain and it still works.
**Visual Manifest:**
- Type: `Mermaid_Sequence`
- Spec: five numbered steps: (1) Gate — cheap math; (2) Aggregate — Pulsar
  Function; (3) Decide — plain code; (4) Word — small LLM, inside the
  Function, one core; (5) Speak — Piper. Under the line, example domains:
  factory-floor alarms, on-call pages read aloud, building sensors, in-cab
  driver alerts.

**On-screen text:**
```
1 Gate   2 Aggregate   3 Decide   4 Word   5 Speak
One CPU core. No GPU. No cloud LLM API.
```

**Speaker notes:** Strip out the trucks and here's what's left: cheap math
to decide what's interesting, a Function to aggregate, plain code to
decide, a small model inside the Function to word it, a TTS engine to speak
it. One CPU core, no GPU, no cloud LLM API — what you just watched. Point it
at factory alarms, on-call pages, building sensors. Last slide: where this
sits in the trilogy.

**Time:** Close, ~1.75 min.

### Slide 27 — The Fleet Tells You, Out Loud
**Label:** Trilogy Closer
**Suggested Layout:** Three-up — content-bearing, because the Thank You
`Closing` plate follows directly.
**Core Message:** Talk 1 decided what was worth sending, Talk 2 proved which
model deserved the job, Talk 3 said it out loud.
**Visual Manifest:**
- Type: `Typography_Only`
- Spec: three cards: "Talk 1 — the edge decides what's worth sending";
  "Talk 2 — prove which model deserves the job"; "Talk 3 — the fleet
  tells you, out loud." Repo link in the footer. [NEEDS: repo URL]

**On-screen text:**
```
Talk 1: the edge decides what's worth sending
Talk 2: prove which model deserves the job
Talk 3: the fleet tells you, out loud
```

**Speaker notes:** Replay the cold-open clip. Then the line, now carrying
the whole talk: "That was a Pulsar Function talking — a small model inside
it, on one CPU core — and now you've seen every line that made it talk."
Point at the repo for the code and the measurements.

**Time:** Close, ~1.5 min.

### Slide 28 — Thank you
**Label:** Thank You
**Suggested Layout:** Closing (plate)
**Visual Manifest:** Type: `Typography_Only`

**On-screen text:**
```
David Kjerrumgaard
Apache Pulsar Committer
```

**Speaker notes:** Transition to Q&A.

---

## Time-budget check

| Section | Slides | Minutes |
|---|---|---|
| Cold open | 3 | 2.0 |
| Act 1 — Where the Words Come From | 4–7 | 5.25 |
| Act 2 — The Pulsar Function | 8–13 | 8.0 |
| Act 3 — Code Decides, the LLM Narrates | 14–19 | 8.0 |
| Act 4 — On One CPU Core | 20–22 | 4.75 |
| Act 5 — Giving It a Voice | 23–24 | 2.75 |
| Act 6 — See It Live | 25 | 4.0 |
| Close | 26–27 | 3.25 |

**Total: 38 min across 25 slides, plus 2 min of slack for the live demo
(target: 40 min)** — plus untimed Waitroom, Title and Thank You.
