# Talk outline — "Pulsar Speaks English": giving a streaming pipeline a voice
# with Pulsar Functions, a small LLM, and Piper

*(Working title — see "Not yet decided" below.)*

**The thesis line (cold open and closer):**

> "That was a Pulsar Function talking."

This is a showcase talk, not a postmortem or a pivot story: the spine is
*"hey, that's cool — and here's how little it took."* Three ordinary pieces,
each doing one job, chained on Pulsar topics: a **Pulsar Function** that
aggregates the fleet's edge cards, **plain code** that decides, a **small
quantized LLM** that only words the decision, and **Piper** that speaks it.
The "narrate, don't decide" rule and the small-model blooper reel are
supporting segments that explain *why* it's trustworthy — they are not the
plot.

Open cold on the voice with zero context, say the thesis line, then spend
the talk taking it apart. Say the line again at the close, now meaning
"…and you've seen every line of code that made it talk."

Standalone, but rewards Talks 1 and 2: one-slide Talk 1 recap (where the
cards come from), and one optional callback to Talk 2's model pick and Pi
numbers. 40-minute slot at ~2 min/slide → ~20 narrative slides plus
Waitroom/Title/Thank You, same shape as Talks 1 and 2.

Every beat below cites the artifact that already backs it — drawn from what's
in the repo, not invented for the outline.

## Cold open — the voice first (~2 min, 1 slide)

- Black slide, play the audio from the demo take: the I-95N corridor warning
  in the `norman` voice. No title, no setup.
- Then: *"That was a Pulsar Function talking. By the end of this talk you'll
  have seen every piece that made it say that — and it's less than you think."*
- Backing: `deploy/recordings/talk3-demo-20261002-174855.mp4` (audio track),
  `deploy/recordings/.talk3-audio-20261002-174855/001-I-95N.wav`.

## Act 1 — Where the words come from (~6 min, 3 slides)

**Slide: Previously, at the edge (Talk 1 recap, one slide).**
- Trucks run the Edge Triage Pipeline on a Pi-class device: cheap math gates
  the noise, a small LLM writes an enrichment card, and only `high` severity
  crosses the cellular link (`uplink_min_severity`).
- If you missed Talk 1: "each truck sends a short, structured note when
  something's actually wrong." That's all Talk 3 needs.
- Backing: `docs/TALK1-SLIDE-PLAN.md` slides 19–21; `deploy/README.md`
  "Edge Triage Pipeline" section.

**Slide: One truck is an anecdote, three trucks are an incident.**
- The Tier 2 question: is this one truck's bad day, or the whole corridor?
  And should we reroute?
- Show the three demo cards side by side: truck-47 (high, 9 min),
  truck-12 (high, 7 min), truck-31 (medium, 6 min), all I-95N.
- Backing: `deploy/talk3-demo-cards.jsonl`.

**Slide: The whole system on one slide.**
- `enrichment-cards` → `GlobalSynthesisFunction` → `incidents` → speaker →
  speaker/WAV. Two topics, one Function, one consumer.
- Plant the payoff: every box is something you can run on a laptop today.
- Backing: `deploy/README.md` topology diagram.

## Act 2 — The Pulsar Function (~8 min, 4 slides)

**Slide: What a Pulsar Function is (for this room).**
- `process(self, input, context) -> output`. One message in, zero or one out.
  Deployed with `pulsar-admin functions localrun` today, managed mode later.
- Config through `--user-config` (model path, `-no-cnv`, corridor threshold) —
  no rebuild to swap models.
- Backing: `function.py` module docstring, `deploy/run_tier2_localrun.sh`.

**Slide: The tension — Functions are per-message, Tier 2 needs a crowd.**
- You can't decide "corridor-wide" from one card. The trick: Function
  instances are long-lived, so keep a per-corridor accumulator on `self`;
  return `None` (publish nothing) until the corridor hits the threshold.
- Backing: `GlobalSynthesisFunction.process()` in `function.py`.

**Slide: Honest about the shortcut.**
- No event-time windows, no watermarks, accumulator lost on restart, no
  wall-clock flush. Fine for a stage demo; name what production would need
  (Pulsar Functions state, or windowed functions).
- Contrast: `pulsar_adapter.py` has the time-based flush.
- Backing: `function.py` docstring, `pulsar_adapter.py`.

**Slide: The whole Function fits on a slide.**
- Show `process()` in full (~12 lines). The point: the Pulsar part is the
  smallest part of this system.

## Act 3 — Code decides, the LLM narrates (~10 min, 5 slides)

**Slide: The rule.**
- Same rule as Talk 1's edge: cheap code decides, the LLM only puts it into
  words. Here: `decide_scope()` is set-counting over `truck_id`;
  `decide_reroute()` is "corridor-wide AND at least one high." Both are
  explainable, testable, and free.
- Backing: `synthesizer.py`; `docs/CANON.md`.

**Slide: The prompt hands the model a finished verdict.**
- Show the prompt: "already decided" on every fact, "always name the
  corridor," a *placeholder* JSON shape — never a realistic example sentence.
- Why the placeholder: small models copy realistic examples word for word.
- Backing: `prompting.py` `SYNTHESIS_WARNING_PROMPT`.

**Slide: Why Gemma-3-4B-it (Talk 2 callback, optional).**
- Same funnel as Talk 2, run on this task: Gemma-3-4B-it 0%/0% grounding/
  speakability violations, 43.7s Pi p50. The Edge Triage Pipeline's winner,
  Phi-3.5-mini, is the *slowest* here (186.0s) because it pads "2-3
  sentences." The model choice depends on the task.
- Backing: `docs/TALK2-OUTLINE.md` "Final model recommendation."

**Slide: Blooper reel — what small models say when you let them.**
(Lighter, fast-paced; one line each, real output where available.)
- **The echo:** the 350M models hand back the prompt, placeholder and all.
  (`docs/TALK2-350M-PROMPT-ECHO.md`)
- **The silent corridor:** Qwen2.5-3B drops "I-95N" whenever it decides the
  situation is minor — 100% on single-truck, 0% once a reroute is involved.
  Fixed by one blunt prompt line. (impact track row 17)
- **Thinking out loud:** Qwen3-8B reasons in prose and runs out of tokens
  before the JSON. (row 22)

**Slide: …and the bloopers that weren't the model.**
- **The harness was wrong:** "I-95 North" and "No reroute is recommended"
  were scored as violations by naive string checks. (row 14)
- **The code was wrong:** `decide_reroute` said "high-severity" for all three
  trucks when only two were; Gemma faithfully said it aloud. The LLM
  narrated a bug in *our* code. (row 27, fixed in `synthesizer.py`)
- The line: *if the model only narrates, check the facts you hand it.*

## Act 4 — Giving it a voice (~6 min, 3 slides)

**Slide: Piper, at arm's length.**
- Piper (`piper-tts`, OHF-Voice/piper1-gpl) is GPL-3.0, so it's never a
  dependency: its own venv, invoked as a subprocess — the same way
  `llm_inference` calls llama.cpp.
- Voices have their own licenses: the demo uses `norman` (public domain,
  LibriVox); avoid `ryan`/`hfc_*` (NC-SA) and `lessac`.
- Backing: `speech.py` docstring; package README "Speaking the warning."

**Slide: TTS doesn't know what I-95N means.**
- Play both versions: raw "eye ninety-five *en*" vs. normalized "I-95 North";
  "ee-ta" vs. "E T A." The fix is a dozen lines of regex, checked against
  Piper's phonemizer — more plain code.
- Backing: `normalize_for_speech()` in `speech.py`.
- Needs: record the two "before" clips (see "Not yet decided").

**Slide: The voice is the fast part.**
- Piper: ~70x real time on an M4 (0.16s for 11s of audio). The LLM is the slow
  hop, not the voice.
- Backing: package README.

## Act 5 — See it run (~4 min, 2 slides)

**Slide: The demo, end to end.**
- Play the take: cards arrive (3s apart) → "[Decided by code]" panel →
  "[Worded by the LLM]" panel → the voice. Narrate over it, pointing at
  which window is code and which is model.
- Be upfront: the input cards are replayed (only truck-47 has trip
  context that reaches `high` in a live run); everything after the replay is
  live on every take.
- Backing: `deploy/README.md` "Talk 3 demo"; the take above.

**Slide: Could it run on the Pi?** *(optional — only if the Pi run happens)*
- Same Function, same model: Tier 2's Pi p50 is ~44s per warning — slow
  enough to notice, fast enough for a traffic warning.
- Backing: `docs/TALK2-OUTLINE.md` Tier 2 table; a Pi take if recorded.

## Close — what you could build (~4 min, 2 slides)

**Slide: The recipe, generalized.**
- Pulsar Function to aggregate → plain code to decide → small LLM to word →
  TTS to speak. Swap the domain: factory floor alarms, on-call pages read
  aloud, building sensors, in-cab driver alerts.
- Everything here is commodity: no GPU, no cloud LLM API.

**Slide: Trilogy closer.**
- Talk 1: the edge decides what's worth sending. Talk 2: how to prove which
  model deserves the job. Talk 3: the fleet tells you about it, out loud.
- Replay the cold-open clip, then the thesis line, fully loaded: *"That was
  a Pulsar Function talking — and now you've seen every line that made it
  talk."*

## Timing summary

| Section | Slides | Minutes |
|---|---|---|
| Cold open | 1 | 2 |
| Act 1 — Where the words come from | 3 | 6 |
| Act 2 — The Pulsar Function | 4 | 8 |
| Act 3 — Code decides, the LLM narrates | 5 | 10 |
| Act 4 — Giving it a voice | 3 | 6 |
| Act 5 — See it run | 2 (1 if no Pi) | 4 |
| Close | 2 | 4 |
| **Total** | **20** | **40** |

Plus untimed Waitroom, Title and Thank You slides.

## Not yet decided / needs your input

- **Title.** Working: "Pulsar Speaks English." Needs a subtitle in the style
  of Talks 1–2.
- **Demo take sign-off.** Take 4 (42.6s) is the only take; not yet reviewed.
  Also check whether its spoken text should be quoted on the cold-open slide.
- **Pi slide.** Keep only if the optional Pi run happens; otherwise fold the
  ~44s number into the Talk 2 callback slide and give Act 3 the extra time.
- **"Before" audio clips** for the I-95N/ETA slide — need recording with
  normalization off (raw Piper call via `~/tools/piper/.venv/bin/piper`).
- **Blooper reel format** — read-aloud quotes, or actually *speak* the bad
  outputs with Piper (funnier; needs the raw completions pulled from
  `eval-results/`).
- **How much Talk 2 to lean on** — one callback slide as written, or cut it
  to keep the talk fully standalone.
- **"1-bit" language check** (carried over from Talk 2's open items): this
  outline avoids 1-bit framing; keep it that way in the deck.
