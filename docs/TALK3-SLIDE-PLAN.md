# Talk 3 — "Pulsar Speaks English" — Slide Plan

No deck built yet — this is the plan the deck gets built from, generated from
`docs/TALK3-OUTLINE.md` on 2026-10-03 with the `tech-slide-planner` skill.
Every fact below cites the repo file that backs it, same discipline as
`docs/TALK1-SLIDE-PLAN.md` and `docs/TALK2-SLIDE-PLAN.md`. When building
the deck, paste this plan with `docs/TALK2-DECK-BUILD-PROMPT.md`'s general
rules (sections 1–5).

**Style profile: `DATADOG_MARKETING_DECK`** — the same native slide types
Talks 1 and 2 use. Talk 3 has five code slides, and this profile's
`Metric` ("Code + KPI") type is built for code with a number beside it;
the sequence slides use its `Timeline` type. Plate types (`Title`,
`Section`, `Quote`, `Product`, `Statement`, `Closing`) are never placed back
to back and carry only text.

40-minute slot at ~2 min/slide: **24 narrative slides** (3–26), the same
count and pace as Talks 1 and 2, plus untimed Waitroom, Title and Thank You.

## Structure
0. **Cold open** (slide 3): the voice, with no context.
1. **Act 1 — Where the Words Come From** (4–7): Talk 1 recap, the three
   trucks, the whole system.
2. **Act 2 — The Pulsar Function** (8–12): the Functions model, the
   aggregation trick, the real code, the honest shortcut.
3. **Act 3 — Code Decides, the LLM Narrates** (13–18): the rule, the
   prompt, the model pick, two blooper slides.
4. **Act 4 — Giving It a Voice** (19–22): Piper at arm's length,
   pronunciation fixes, speed.
5. **Act 5 — See It Run** (23–24): the recorded demo; the optional Pi slide.
6. **Close** (25–26): the recipe, generalized; the trilogy closer.

## Changes from the outline
- Act 2 order swapped: the code slide (11) now comes before "Honest about
  the shortcut" (12), so the audience sees what the code does before hearing
  what it skips.
- Section dividers added for Acts 1–4 (~15 s each). Acts 5 and the Close
  have no divider: Act 5 opens on the demo itself, and a divider before the
  close would put two plates next to the Thank You slide.
- The outline's 20 slides become 24 because the dividers count as slides;
  total time is unchanged at 40 minutes.

## Open items
- **Take 4 transcript.** Slides 3 and 23 quote the spoken warning; the exact
  wording Gemma produced in take 4 isn't recorded in the repo as text.
  [NEEDS: transcript of `deploy/recordings/.talk3-audio-20261002-174855/001-I-95N.wav`]
- **Take 4 sign-off.** The only take (42.6 s). Not yet reviewed.
- **"Before" audio clips** for slide 21 (raw Piper, normalization off).
- **Slide 24 (Pi)** stays only if the Pi run happens; otherwise cut it and
  give its 1.5 min to slide 23.
- **Subtitle** for the title slide.
- **Demo M4 latency.** Slide 22 deliberately compares nothing across
  hardware; if you want "the LLM is the slow hop" as a number, it needs a
  same-host M4 Gemma timing. [NEEDS: M4 Tier 2 Gemma latency]
- **Repo URL** for slide 26, same open item as Talk 2.

---

### Slide 1 — Welcome! We'll begin shortly.
**Label:** Waitroom

**On-screen text:**
```
Pulsar Speaks English
Grab a coffee and settle in.
```

**Speaker notes:** Untimed lobby slide, same convention as Talks 1 and 2.

### Slide 2 — Pulsar Speaks English
**Label:** Title
**Suggested Layout:** Title (plate)
**Visual Manifest:** Type: `Typography_Only` · Spec: title, subtitle, name.

**On-screen text:**
```
Pulsar Speaks English
[NEEDS: subtitle]
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
  line fades in. Audio: the I-95N warning from take 4
  (`deploy/recordings/.talk3-audio-20261002-174855/001-I-95N.wav`).

**On-screen text:**
```
"That was a Pulsar Function talking."
```

**Speaker notes:** Play the clip before saying anything. Let it finish.
Then: "That was a Pulsar Function talking. By the end of this talk you'll
have seen every piece that made it say that, and it's less than you think."
Don't explain how yet; the next slide steps back to where the facts in
that sentence came from.

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

### Slide 5 — Previously, at the Edge
**Label:** Talk 1 Recap
**Suggested Layout:** Content
**Core Message:** Each truck already sends a short, structured note, but only
when something is actually wrong.
**Visual Manifest:**
- Type: `Mermaid_Architecture`
- Spec: left-to-right, inside a "Truck (Pi-class)" boundary:
  `truck-telemetry` → `TelemetryCoprocessorFunction` (cheap math) →
  `LlmTriageFunction` (small LLM writes the card) → gate `severity = high?`
  → yes: `enrichment-cards` (crosses cellular, exits the boundary) / no:
  local-only topic (stays on the truck). Highlight the `enrichment-cards`
  edge — it's where this talk starts.

**On-screen text:**
```
The Edge Triage Pipeline (Talk 1)
Only high-severity cards cross the cellular link
```

**Speaker notes:** One-slide recap for anyone who missed Talk 1. On every
truck, the Edge Triage Pipeline does the triage: cheap math filters the
noise, a small LLM writes an enrichment card, and only cards that end up
`high` severity go over cellular (`uplink_min_severity`, default `high`).
If you missed Talk 1, the one thing to keep is: each truck sends a short,
structured note when something's actually wrong. That arrow leaving the
truck is where Talk 3 picks up. Backing: `docs/TALK1-SLIDE-PLAN.md` slides
19–21; `deploy/README.md` "Edge Triage Pipeline" section.

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
to go around? Notice truck-31 is medium — that detail matters later, in the
blooper reel. Be straightforward: this is a replayed scenario, not three
cards from Talk 1's live run (the demo slide explains why). Next: what
happens to these three cards, end to end.

**Time:** Act 1, ~2 min.

### Slide 7 — The Whole System on One Slide
**Label:** Two Topics, One Function, One Speaker
**Suggested Layout:** Content
**Core Message:** Two topics, one Function, one consumer — all of it runs on
a laptop.
**Visual Manifest:**
- Type: `Mermaid_Architecture`
- Spec: `enrichment-cards` topic → `GlobalSynthesisFunction` (Pulsar
  Function, `localrun`) → [inside it: plain code decides →
  llama.cpp subprocess with Gemma-3-4B-it words it] → `incidents` topic →
  speaker consumer → Piper subprocess → speaker icon.

**On-screen text:**
```
enrichment-cards → Function → incidents → voice
```

**Speaker notes:** Here's every box. Cards land on `enrichment-cards`. One
Pulsar Function, `GlobalSynthesisFunction`, reads them, makes the
decisions in plain code, and has a small model word the result. That lands
on `incidents` as an `IncidentSynthesis`. A plain consumer reads `incidents`
and hands the sentence to Piper, which speaks it. Every box here runs on a
laptop. The next three acts take it one box at a time, starting with the
Function. Backing: `deploy/README.md` topology diagram.

**Time:** Act 1, ~1.75 min.

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
  elided). KPI side: `1 in → 0 or 1 out`.

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
  --user-config "${USER_CONFIG}"
```

**Speaker notes:** For anyone new to Pulsar Functions: a class with
`process(self, input, context)`. One message in; return a value and it's
published, return `None` and nothing is. Deployed here with
`pulsar-admin functions localrun`; managed mode later is the same class.
Model path, the `-no-cnv` flag, and the corridor threshold all come
through `--user-config`, so swapping models is a config change. That
"one in, zero or one out" shape is fine for Talk 1's per-truck work. Tier
2 has a problem with it, which is the next slide. Backing: `function.py`;
`deploy/run_tier2_localrun.sh`.

**Time:** Act 2, ~2 min.

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
`IncidentSynthesis`. Next: the actual code, which is shorter than this
explanation. Backing: `function.py` module docstring;
`deploy/talk3-windows/tier2.sh` (`CORRIDOR_THRESHOLD=3`).

**Time:** Act 2, ~2 min.

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

    synthesis = synthesize(cards, backend)
    self._accumulator[card.corridor] = []
    return to_json(synthesis) if synthesis is not None else None
```

**Speaker notes:** That's the whole Pulsar Function. Build the model
backend once from user-config, parse the card, add it to its corridor,
return `None` until the threshold, then hand off to `synthesize()` and
reset. Everything interesting — the decision, the wording — lives in
`synthesize()`, which has no Pulsar import at all and is unit-tested
without a broker. Before we go there, an honest note about what this
shortcut skips. Backing: `function.py`.

**Time:** Act 2, ~2 min.

### Slide 12 — Honest About the Shortcut
**Label:** Demo vs. Production
**Suggested Layout:** Comparison
**Core Message:** An in-memory tally is fine on stage; production needs
windows and saved state.
**Visual Manifest:**
- Type: `Bar_Comparison`
- Spec: non-numeric two-column contrast. Left ("This demo"): in-memory dict
  on `self`; flushes only on card count; lost on restart. Right ("In
  production"): event-time windows; a time-based flush; state that
  survives a restart.

**On-screen text:**
```
This demo                      In production
in-memory, on self             saved state
flush on card count            flush on time, too
lost on restart                survives restart
```

**Speaker notes:** Say plainly what this skips: no event-time windows, no
watermarks, no wall-clock flush, and the tally is gone if the instance
restarts. A corridor stuck at two cards waits forever. The repo's other
runtime shape, `pulsar_adapter.py`, does have a time-based flush. Fine for
a demo; name it before someone in Q&A does. Now that the plumbing is
covered, the more interesting question: who decides what the warning says?
Backing: `function.py` docstring; `pulsar_adapter.py`.

**Time:** Act 2, ~1.75 min.

## Act 3 — Code Decides, the LLM Narrates

### Slide 13 — Code Decides, the LLM Narrates
**Label:** Section: Code Decides, the LLM Narrates
**Suggested Layout:** Section (plate)
**Visual Manifest:** Type: `Typography_Only`

**On-screen text:**
```
Code Decides, the LLM Narrates
```

**Speaker notes:** Divider.

**Time:** Act 3, ~0.25 min.

### Slide 14 — The Decision Is Plain Python
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

**Time:** Act 3, ~2 min.

### Slide 15 — The Prompt Hands Over a Finished Verdict
**Label:** The Prompt
**Suggested Layout:** Content — overriding the `Metric` default: this slide
has no honest KPI to pair with the code, and a made-up one would break the
accuracy rule.
**Core Message:** Every fact arrives "already decided," and the example
answer is a placeholder, never a sentence to copy.
**Visual Manifest:**
- Type: `Code_Block`
- Spec: the excerpt below from `SYNTHESIS_WARNING_PROMPT` in
  `prompting.py`, with "(already decided)" and the placeholder shape
  highlighted.

**On-screen text:**
```
Always name the corridor explicitly in your warning ...
Scope (already decided): {scope}
Reroute recommended (already decided): {reroute_recommended}
Reroute detail (already decided): {reroute_detail}
...
Shape (a placeholder, not a real answer): {"spoken_warning": "<your warning text here>"}
```

**Speaker notes:** The prompt states every decision as settled: "already
decided," three times. It asks for 2–3 calm, spoken-style sentences and
one JSON key. Two lines were earned the hard way. The placeholder: small
models shown a realistic example sentence copy it no matter the input, so
the example contains nothing worth copying. And "always name the corridor"
— that line has its own story in a minute. First, which model gets this
prompt. Backing: `prompting.py` module docstring.

**Time:** Act 3, ~2 min.

### Slide 16 — Why Gemma-3-4B-it
**Label:** Talk 2 Callback: The Model Pick
**Suggested Layout:** Comparison
**Core Message:** The model that won Talk 1's task is the slowest one here,
so this task got its own pick.
**Visual Manifest:**
- Type: `Bar_Comparison`
- Spec: two columns, Pi 4 decision-grade Tier 2 numbers. Left "Gemma-3-4B-it
  (picked)": 0.0% / 0.0% grounding/speakability violations, p50 43.7 s,
  p95 119.3 s. Right "Phi-3.5-mini-instruct (Edge Triage Pipeline winner)":
  0.0% / 0.0%, p50 186.0 s, p95 251.6 s.

**On-screen text:**
```
Gemma-3-4B-it          Phi-3.5-mini-instruct
p50 43.7 s (Pi 4)      p50 186.0 s (Pi 4)
0% / 0% violations     0% / 0% violations
```

**Speaker notes:** If you saw Talk 2: same evaluation funnel, run on this
task. Both models are perfectly accurate here. The difference is speed:
Phi-3.5-mini, which won the Edge Triage Pipeline, pads a "2–3 sentence"
answer and takes about four times as long. Gemma stays short. Same Pi,
same quantization — the ranking flips with the task. If you didn't see
Talk 2: we measured it, and the repo has the numbers. That covers the
model that behaves; next, the ones that didn't. Backing:
`docs/TALK2-OUTLINE.md` "Final model recommendation."

**Time:** Act 3, ~2 min.

### Slide 17 — What Small Models Say When You Let Them
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
the "always name the corridor" from two slides ago. Thinking out loud:
Qwen3-8B reasons in prose and ran out of its 110-token budget before
reaching the JSON. But the best bloopers weren't the models at all.
Backing: `docs/TALK2-350M-PROMPT-ECHO.md`;
`docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md` rows 17, 22.

**Time:** Act 3, ~2 min.

### Slide 18 — The Bloopers That Weren't the Model
**Label:** Blooper Reel: Us
**Suggested Layout:** Comparison
**Core Message:** If the model only narrates, check the facts you hand it.
**Visual Manifest:**
- Type: `Bar_Comparison`
- Spec: before/after of `reroute_detail` from impact-track row 27. Left
  "Before (our bug)": code said `"3 trucks reporting a correlated
  high-severity slowdown"` → Gemma said "three trucks are experiencing
  high-severity delays." Right "After": `"3 trucks reporting a correlated
  slowdown, 2 at high severity."` Footer line: the eval harness scored
  "I-95 North" and "No reroute is recommended" as violations (row 14).

**On-screen text:**
```
Before: "3 trucks reporting a correlated high-severity slowdown"
After:  "3 trucks reporting a correlated slowdown, 2 at high severity"
```

**Speaker notes:** Remember truck-31 was medium? Our own reroute code said
"high-severity" for all three trucks whenever any one was high. Gemma
read that out faithfully: "three trucks are experiencing high-severity
delays." The model did its job; it narrated our bug. Fixed in
`decide_reroute`. And earlier, the eval harness itself flagged Gemma's
"I-95 North" and a correct "No reroute is recommended" as failures, from
naive string matching. The line: if the model only narrates, check the
facts you hand it. That's the wording sorted; now turning it into sound.
Backing: `docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md` rows 14, 27;
`synthesizer.py`.

**Time:** Act 3, ~1.75 min.

## Act 4 — Giving It a Voice

### Slide 19 — Giving It a Voice
**Label:** Section: Giving It a Voice
**Suggested Layout:** Section (plate)
**Visual Manifest:** Type: `Typography_Only`

**On-screen text:**
```
Giving It a Voice
```

**Speaker notes:** Divider.

**Time:** Act 4, ~0.25 min.

### Slide 20 — Piper, at Arm's Length
**Label:** TTS as a Separate Process
**Suggested Layout:** Content
**Core Message:** Piper is GPL, so it runs as a separate process, never
imported — the same way we call llama.cpp.
**Visual Manifest:**
- Type: `Mermaid_Architecture`
- Spec: two parallel rows with matching shape. Row 1: `llm_inference` →
  subprocess → `llama.cpp` + GGUF. Row 2: `PiperSpeaker` → subprocess →
  `piper` (own venv, GPL-3.0) + voice `.onnx` → WAV → `afplay` / `aplay`.
  A dashed boundary labelled "this repo" around only the left-hand boxes.

**On-screen text:**
```
Piper (GPL-3.0) — own venv, subprocess only
Voice: norman (public domain)
```

**Speaker notes:** Piper — `piper-tts`, the OHF-Voice/piper1-gpl project —
is GPL-3.0; the MIT original was archived in October 2025. So it's never
a dependency: it lives in its own venv and we call it as a separate
process, the same way `llm_inference` calls llama.cpp. Voices have their
own licenses too: this demo uses `norman`, public-domain LibriVox
recordings; avoid `ryan` and the `hfc` voices (non-commercial) and
`lessac`. One more surprise: Piper doesn't know what "I-95N" means.
Backing: `speech.py` docstring; package README "Speaking the warning."

**Time:** Act 4, ~2 min.

### Slide 21 — TTS Doesn't Know What I-95N Means
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
plain code doing exactly one job, same pattern as the decision code. Last
question for this act: is the voice going to be the slow part? Backing:
`normalize_for_speech()` in `speech.py`.

**Time:** Act 4, ~2 min.

### Slide 22 — The Voice Is the Fast Part
**Label:** ~70x Real Time
**Suggested Layout:** Stats — overriding the `Time_Series_Line_Chart`
mapping: there's no series to chart, just three numbers.
**Core Message:** Piper speaks 11 seconds of audio in 0.16 seconds; the
LLM is the slow hop.
**Visual Manifest:**
- Type: `Typography_Only`
- Spec: three stat tiles, M4: `0.16 s` (synthesis time), `11 s` (audio
  length), `~70x` (faster than real time).

**On-screen text:**
```
0.16 s   to synthesize
11 s     of audio
~70x     real time (M4)
```

**Speaker notes:** On the M4, Piper writes 11 seconds of speech in 0.16
seconds — about 70 times faster than real time. Whatever wait you notice
in the demo is the LLM, not the voice. Don't compare this to Talk 2's Pi
latency on screen; different hardware. Now, all of it running together.
Backing: package README.

**Time:** Act 4, ~1.75 min.

## Act 5 — See It Run

### Slide 23 — See It Run
**Label:** Demo Recording
**Suggested Layout:** Content — full-width embedded video (no affinity-map
entry for video; `Product` is a plate with no content region, so it can't
hold a player).
**Core Message:** Three cards in, a decision by code, a sentence by the
model, a voice out — live on every take.
**Visual Manifest:**
- Type: `[NEEDS: new visual type not yet in the supported list]` —
  embedded video. Spec: `deploy/recordings/talk3-demo-20261002-174855.mp4`
  (42.6 s, 1890×1006, with audio); three windows: cards arriving,
  "[Decided by code]" / "[Worded by the LLM]", the voice.

**On-screen text:**
```
Replayed cards → live Function → live model → live voice
```

**Speaker notes:** Narrate over it, pointing at each window: the three
cards arriving three seconds apart; the "Decided by code" panel —
corridor-wide, three trucks, reroute; then "Worded by the LLM," the
sentence Gemma wrote; then the voice. Be upfront: the cards are replayed,
because in a live Talk 1 run only truck-47 has trip context that reaches
`high`, so Tier 2 would only ever see one truck. Everything after the
replay — the Function, the decision, the model, the voice — is live on
every take. [NEEDS: take 4 transcript to quote the sentence.] Backing:
`deploy/README.md` "Talk 3 demo."

**Time:** Act 5, ~2.5 min.

### Slide 24 — Could It Run on the Pi?
**Label:** Optional: The Pi
**Suggested Layout:** Stats
**Core Message:** The same Function and model run on a Pi 4, at about 44
seconds per warning.
**Visual Manifest:**
- Type: `Typography_Only`
- Spec: two stat tiles from Talk 2's Pi 4 Tier 2 table: `43.7 s` p50,
  `119.3 s` p95, Gemma-3-4B-it. If a Pi take is recorded, add a frame
  from it. [NEEDS: Pi take, if any]

**On-screen text:**
```
43.7 s   p50 per warning (Pi 4)
119.3 s  p95
```

**Speaker notes:** Optional — keep this slide only if the Pi run happens.
Same Function, same model, on a Raspberry Pi 4: a median of about 44
seconds per warning. Slow enough to notice, fast enough for a traffic
warning drivers hear before they reach the corridor. Next: what you
could build with the same four steps. Backing: `docs/TALK2-OUTLINE.md`
Tier 2 table.

**Time:** Act 5, ~1.5 min.

## Close

### Slide 25 — The Recipe
**Label:** Aggregate, Decide, Word, Speak
**Suggested Layout:** Timeline
**Core Message:** Aggregate with a Function, decide in code, word with a
small LLM, speak with TTS — swap the domain and it still works.
**Visual Manifest:**
- Type: `Mermaid_Sequence`
- Spec: four numbered steps: (1) Aggregate — Pulsar Function; (2) Decide
  — plain code; (3) Word — small quantized LLM; (4) Speak — Piper. Under
  the line, example domains: factory-floor alarms, on-call pages read
  aloud, building sensors, in-cab driver alerts.

**On-screen text:**
```
1 Aggregate   2 Decide   3 Word   4 Speak
No GPU. No cloud LLM API.
```

**Speaker notes:** Strip out the trucks and here's what's left: a
Function to aggregate, plain code to decide, a small model to word it, a
TTS engine to speak it. Every piece is commodity — no GPU, no cloud LLM
API. Point it at factory alarms, on-call pages, building sensors. Last
slide: where this sits in the trilogy.

**Time:** Close, ~2 min.

### Slide 26 — The Fleet Tells You, Out Loud
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
the whole talk: "That was a Pulsar Function talking — and now you've seen
every line that made it talk." Point at the repo for the code.

**Time:** Close, ~2 min.

### Slide 27 — Thank you
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

| Section | Slides | Minutes | Outline target |
|---|---|---|---|
| Cold open | 3 | 2.0 | 2 |
| Act 1 | 4–7 | 6.0 | 6 |
| Act 2 | 8–12 | 8.0 | 8 |
| Act 3 | 13–18 | 10.0 | 10 |
| Act 4 | 19–22 | 6.0 | 6 |
| Act 5 | 23–24 | 4.0 | 4 |
| Close | 25–26 | 4.0 | 4 |

**Total: 40 min across 24 slides (target: 40 min)** — plus untimed
Waitroom, Title and Thank You. If slide 24 is cut, slide 23 takes 4.0 min.
