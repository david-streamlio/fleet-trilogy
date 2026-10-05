# Talk outline — "When Your Pulsar Function Speaks English: Inline LLM Inference for Real-Time Stream Enrichment"

**Accepted abstract (verbatim — the talk keeps every promise in it):**

> "Here's a trick: if you embed a tiny LLM inside a stream processing function
> and only fire it on the interesting events, you get AI-enriched streams on a
> single CPU core. I'll demo it live, show the resource profile, and share the
> prompt patterns that actually work at stream speed."

**The thesis line (cold open and closer):**

> "That was a Pulsar Function talking."

True as said: a small LLM *inside* the Function wrote the sentence, on one CPU
core. Piper, downstream, only reads it out, and the talk says so (Act 5).

The spine: *"hey, that's cool — and here's how little it took."* Cheap math
gates the events, a **Pulsar Function** aggregates them, **plain code**
decides, a **small quantized LLM loaded inside the Function** words the
decision on one CPU core, and **Piper** speaks it. The resource profile and the
honest admissions (first attempt 29 s, Pi not yet run, ~1 in 4 warnings with a
factual slip) are part of the plot, not footnotes: the abstract promised them.

Standalone, but rewards Talks 1 and 2. 40-minute slot: 25 narrative slides at
38 minutes plus 2 minutes of slack for the live demo; untimed Waitroom, Title
and Thank You. Full slide-by-slide plan: `docs/TALK3-SLIDE-PLAN.md`.

Every beat cites the artifact that backs it. The one-core numbers all come
from `eval-results/talk3-single-core-m4max-20261004/` (M4 Max, Gemma-3-4B-it
Q4_K_M, median of 10 calls).

## Cold open — the voice first (~2 min, 1 slide)

- Play the I-95N warning from a take recorded with the current defaults
  (in-process, one CPU thread). No title, no setup.
- *"That was a Pulsar Function talking. A small LLM inside it wrote that
  sentence, on one CPU core, no GPU."*
- Backing: the new take (to record; take 4 ran on the GPU through the old
  subprocess path).

## Act 1 — Where the words come from (~5 min, 4 slides incl. divider)

**Only the interesting events.** Talk 1's cheap math gates the readings: in a
simulated run, 720 readings → 201–241 pass (28–33%; the simulator is
incident-heavy, so a real road would be quieter — unmeasured). Only `high`
cards leave the truck. Tier 2 calls its LLM once per incident (3 cards → 1
call). Backing: `gating_counts.txt`; `docs/TALK1-SLIDE-PLAN.md` 19–21.

**One truck is an anecdote, three trucks are an incident.** truck-47 (high,
9 min), truck-12 (high, 7 min), truck-31 (medium, 6 min), all I-95N. Backing:
`deploy/talk3-demo-cards.jsonl`.

**The whole system on one slide.** `enrichment-cards` → `GlobalSynthesisFunction`
[code decides · LLM inside words it] → `incidents` → speaker → Piper.

## Act 2 — The Pulsar Function (~8 min, 6 slides incl. divider)

- **One message in, zero or one out**; config through `--user-config`
  (`llm_backend`, `threads`, `corridor_threshold`).
- **The accumulator trick**: a per-corridor tally on `self`; two of every
  three messages never touch the LLM.
- **`process()` in full** (12 lines).
- **The model lives inside the Function** (new): `InProcessLlmBackend`
  (llama-cpp-python) loads once and stays on `self`; each call skips the load
  and reuses the prompt's fixed instructions (98 of 361 tokens). One core,
  same build: 15.5 s reloaded → 12.0 s kept. Backing: `function.py`,
  `client.py`, `docs/CANON.md`, round 2 of the measurement.
- **Honest about the shortcut**: no windows, no watermarks, lost on restart —
  and each instance holds its own 5.3 GB model.

## Act 3 — Code decides, the LLM narrates (~8 min, 6 slides incl. divider)

- **The rule**: `decide_scope()`, `decide_reroute()` — plain code, 0 LLM calls.
- **Prompt patterns for stream speed**: "already decided" facts; a
  placeholder, never an example; fixed instructions first (reused in-process);
  bounded output ("2-3 sentences", ~60 tokens). On one core, reading the prompt
  is ~3/4 of a call.
- **Why Gemma-3-4B-it** (Talk 2 callback): Phi-3.5-mini is 4x slower on this
  task because it writes ~115 words to Gemma's ~33.
- **Blooper reel, the models**: the echo, the silent corridor, thinking out
  loud.
- **Narrating isn't the same as getting it right**: our `reroute_detail` bug
  (row 27, fixed), and Gemma's own slips — about 1 in 4 warnings, hand-checked
  (7/30 and 6/25), e.g. "9 to 12 minutes" (no input says 12; truck-12?), a
  dropped reroute. Talk 2's string checks passed all of them. Now plain code
  checks every number against the facts (`fact_check.py`): fail → retry once →
  plain-code warning. Caught 14 of 62 real warnings; misses claims without a
  number ("impacting all lanes").

## Act 4 — On one CPU core (~5 min, 3 slides incl. divider)

- **The resource profile** (M4 Max, model kept in the Function): GPU 0.7 s;
  4 CPU threads 3.5 s; **1 CPU thread 12.0 s, cores busy 1.00, 5.3 GB**.
  Piper: 11 s of audio in 0.16 s (measured earlier, on an M4).
- **What one core buys you**: ~5 warnings a minute — enough because the gates
  keep the LLM rare. Honest numbers: the first one-core attempt (subprocess per
  call, Homebrew build) took 29 s; a Pi 5-class core is predicted at ~1 min, not
  yet run. Replace the prediction with the real result, slow or failed.

## Act 5 — Giving it a voice (~3 min, 2 slides)

- **Piper, at arm's length**: "the Function wrote it, Piper reads it." A plain
  consumer, GPL-3.0 Piper in its own venv as a subprocess; `norman` voice
  (public domain).
- **TTS doesn't know what I-95N means**: `normalize_for_speech()`.

## Act 6 — See it live (~4 min, 1 slide)

- Live: replay the three cards → "[Decided by code]" → "[Worded by the LLM]"
  → the voice, with a CPU meter showing one core busy (~15 s for the first
  incident). Recorded take as the fallback. Inputs replayed (disclosed); the
  rest live.

## Close (~3 min, 2 slides)

- **The recipe**: gate, aggregate, decide, word, speak. "One CPU core. No
  GPU. No cloud LLM API."
- **Trilogy closer**, then the line fully loaded: *"That was a Pulsar
  Function talking — a small model inside it, on one CPU core — and now you've
  seen every line that made it talk."*

## Timing summary

| Section | Slides | Minutes |
|---|---|---|
| Cold open | 1 | 2.0 |
| Act 1 — Where the words come from | 4 | 5.25 |
| Act 2 — The Pulsar Function | 6 | 8.0 |
| Act 3 — Code decides, the LLM narrates | 6 | 8.0 |
| Act 4 — On one CPU core | 3 | 4.75 |
| Act 5 — Giving it a voice | 2 | 2.75 |
| Act 6 — See it live | 1 | 4.0 |
| Close | 2 | 3.25 |
| **Total** | **25** | **38 + 2 slack** |

## Not yet decided / needs your input

- **New demo take** with the current `tier2.sh` defaults (in-process, one CPU
  thread, no GPU), for the fallback and the cold-open audio.
- **Pi run**: in-process, one thread, `LLM_TIMEOUT_SECONDS=600`, so slide 22
  can say "I tried it" with the real result.
- **Real gating ratio** from a live Edge Triage run, to replace the simulator's
  28–33%.
- **"Before" audio clips** for the I-95N/ETA slide (raw Piper, normalization
  off).
- **"1-bit" language check** (carried over from Talk 2's open items): this
  outline avoids 1-bit framing; keep it that way in the deck.
