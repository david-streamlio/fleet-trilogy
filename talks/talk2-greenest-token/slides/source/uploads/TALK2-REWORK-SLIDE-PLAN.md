# Talk 2 slide plan: "The Greenest Token" (draft 4, 2026-10-06)

**Source:** `docs/TALK2-REWORK-OUTLINE.md` (draft 4). Written by hand to the `tech-slide-planner` format and checks; the skill itself wasn't run on this draft.
- **Study numbers:** traced to the paper (`talks/talk2-greenest-token/paper/main.tex`).
- **Verbatim prompts and outputs:** traced to the result files named in each slide's "Backing:" line.
- **External figures:** traced to the outline's Sources table.
- **Replaces:** the 28-slide plan of 2026-10-05 (in git at `990b1b4`).

**Profile:** `DATADOG_MARKETING_DECK` (not DRUIDS).

**Talk:** 40 minutes, 2026-10-08, for data practitioners. 33 slides:
- a title and a closing plate;
- three section plates;
- 28 content slides, two of them reused from Talk 1.

**Voice:** first person, per the user.

**Arc:**
- Section 1 is a hero's journey: the dragon, the question, the thesis.
- Section 2 gives the seven techniques as "The greenest token is…".
- Section 3 is an explorer's journey through the Edge Triage Pipeline.
- Section 4 is what to do, what to watch, and what I got wrong.

**Placeholder convention:**
- **`[PLACEHOLDER: …]`:** something to supply before the talk. The slide shows a designed "pending" chip.
- **`[IMAGE: …]`:** an AI-generated image still to be made. The slide shows an "image pending" panel with the description as its caption.
- **`[NEEDS: …]`:** the skill's marker for something the input doesn't supply.

**Recurring treatment:**
- **Section 2 slides (7-13):** each has the eyebrow "THE GREENEST TOKEN IS…" and a title that completes the sentence.
- **Section 3 fix slides (21-29):** each carries its Section 2 line as an eyebrow, so the audience can match each fix to its technique.

**Charts** (slide editions under `talks/talk2-greenest-token/slides/charts/`, from `make_figures.py --slides`):
- `slide_fig1_speed.png` (slide 17);
- `slide_changed_prompt.png` (slide 27, inset);
- `slide_fig3_thinking.png` (slide 29).

---

## Phase: Section 1, the dragon (5.5 min, 5 slides)

### Slide 1 — The Greenest Token
- **Core Message:** the title is the answer: the greenest token never reaches a data center's GPU.
- **Visual Manifest:** Type `Typography_Only`. Spec: title, subtitle and speaker line.
- **Suggested Layout:** `Title` (plate).
- **On-Screen Text:** "The Greenest Token" / "is the one that never hits a GPU" / "David Kjerrumgaard · Datadog"
- **Speaker Notes:**
  - Introduce yourself. This is part 2 of the series: Talk 1 asked whether a small LLM can run on the edge; this one asks what AI costs the planet, and what one developer can do about it.
  - The title is the answer, and the rest of the talk is how.
  - By "GPU" I mean the data center's. On your own device, the accelerator turns out to be the efficient choice; I'll come back to that at the end.
  - Forward: start with the bill.
- **Time:** Section 1, ~0.25 min.

### Slide 2 — Data centers run up an environmental bill
- **Core Message:** data centers' electricity, water, carbon and build-out are large and growing fast.
- **Visual Manifest:** Type `Typography_Only`, overridden to a stats layout with an image. Spec: an image panel, [IMAGE: a hyperscale data center at dusk, its cooling plant venting steam, drawn as a dragon's lair, the dragon asleep around the building; muted violet palette, no text in the image], beside or behind five stat cards. Each card has a big number, a one-line label and a small source line.
- **Suggested Layout:** `Stats`. Override: five cards plus an image panel; the slide's content is headline numbers, not a chart.
- **On-Screen Text (cards):**
  1. "485 TWh" / "electricity used by data centers in 2025, ~1.5% of the world's; ~950 TWh (~3%) by 2030" / "IEA, Key Questions on Energy and AI (2026)"
  2. "4.7% → 11.8%" / "of US electricity: 192 TWh in 2024, projected for 2030" / "LBNL, US Data Center Energy Usage Report: 2025 Update"
  3. "66 B liters" / "of water consumed on site by US data centers in 2023, plus ~800 B liters at the power plants that serve them" / "LBNL (2024)"
  4. "180 → 350 Mt" / "of CO₂ a year from data-center electricity, today → 2035" / "IEA (2025, 2026)"
  5. "$400 B+" / "of hyperscaler capital spending in 2025, with ~75% more announced for 2026" / "IEA (2026)"
- **Speaker Notes:**
  - Walk the cards: electricity heading for 3% of the world's, a US share that could more than double by 2030, water both on site and at the power plants, carbon set to double, and capital spending that keeps rising.
  - Be straight about what these are: modeled estimates, not meter readings. Data centers are about a tenth of global electricity-demand growth to 2030, but where they cluster they can be 20-30% of the local demand.
  - Backing: outline Sources (IEA-2026 pp. 9-10, 13, 18, 34; LBNL-2025 p. 8; LBNL-2024 pp. 55, 57; IEA-2025 p. 18).
  - Forward: what's driving the growth.
- **Time:** Section 1, ~1.5 min.

### Slide 3 — AI is the growth engine, and we're feeding it
- **Core Message:** AI is what's growing data-center demand, and developers adopting AI are part of that demand.
- **Visual Manifest:** Type `Typography_Only`, overridden to three stat cards. Spec: three cards, each a big number, a label and a source line.
- **Suggested Layout:** `Three-up`.
- **On-Screen Text (cards):**
  1. "+50%" / "electricity used by AI-focused data centers in 2025; set to triple to ~465 TWh by 2030" / "IEA (2026)"
  2. "0.24 Wh" / "for a median AI text prompt. Reasoning that runs 15× longer: 13× the energy. Agentic tasks: hundreds to thousands of times more" / "Google (2025); Oviedo et al., Joule (2026); IEA (2026)"
  3. "73%" / "of developers who use AI coding assistants or agents use them every day; a third of daily users, 4+ hours a day" / "Stack Overflow Developer Survey (2026)"
- **Speaker Notes:**
  - The fastest-growing part of the footprint is AI. One prompt is small, but we don't send one: assistants all day, agents that loop and reason, every call on someone's GPU.
  - That's us. Developers adopting AI are feeding the dragon. This isn't a guilt trip: AI is useful and it isn't going away.
  - Backing: outline Sources (IEA-2026 pp. 9, 26; Google-2025; Oviedo-2026; SO-2026).
  - Forward: so the real question is how.
- **Time:** Section 1, ~1.5 min.

### Slide 4 — How do we stop feeding the dragon, and still use AI?
- **Core Message:** the talk's question.
- **Visual Manifest:** Type `Typography_Only`. Spec: the question alone.
- **Suggested Layout:** `Statement` (plate).
- **On-Screen Text:** "How do we stop feeding the dragon, and still use AI?"
- **Speaker Notes:** let it sit. Not "stop using AI": use it without sending every token to a data center. Forward: my answer, as a thesis.
- **Time:** Section 1, ~0.5 min.

### Slide 5 — Every token we don't send is demand nobody has to build for
- **Core Message:** the less we rely on cloud AI, the less demand there is for the data centers that host it, and the slower the build-out; it's negligible per developer but powerful in aggregate.
- **Visual Manifest:** Type `Mermaid_Architecture`, drawn natively. Spec: a left-to-right chain of four nodes, "Fewer tokens sent to cloud AI" → "Less demand" → "A slower data-center build-out" → "Less environmental impact", with the analogy below it.
- **Suggested Layout:** `Content`.
- **On-Screen Text:**
  - The chain (as above).
  - "Like leaving the car at home one day a week: nothing on its own, a lot when everyone does it."
- **Speaker Notes:**
  - This is the thesis, and it's a demand argument, not something I measured: data centers get built because we use them.
  - What I did measure is the part a developer controls: how to send fewer tokens, and what the ones you do send cost.
  - Next: seven techniques, then the project where I found each one, the hard way.
- **Time:** Section 1, ~1.75 min.

## Phase: Section 2, the greenest token is… (5.5 min, 8 slides)

### Slide 6 — The greenest token is…
- **Core Message:** seven techniques, one sentence each.
- **Visual Manifest:** Type `Typography_Only`. Spec: section title and subtitle.
- **Suggested Layout:** `Section` (plate).
- **On-Screen Text:** "The greenest token is…" / "Seven ways to stop feeding the dragon"
- **Speaker Notes:** each finishes the sentence. The first two cut the most, because they stop tokens existing at all. Forward: the biggest one.
- **Time:** Section 2, ~0.25 min.

### Slide 7 — …the one never sent to the data center
- **Core Message:** filter at the edge, so only high-value events ever reach a model and only the results that matter leave the device.
- **Visual Manifest:** Type `Typography_Only`, overridden to two big stats. Spec: two stat blocks plus a technique line and a small proof line.
- **Suggested Layout:** `Stats`.
- **On-Screen Text:**
  - Eyebrow: "THE GREENEST TOKEN IS…"
  - Technique: "A cheap-math gate on the truck; only high-severity results cross the cellular link"
  - Stat: "17,280 → ~23" / "events a truck sends per day → LLM calls per incident"
  - Stat: "9.2 MB → ~4 KB" / "raw telemetry per truck-day → what's uplinked per incident"
  - Small line: "0 LLM calls in 2.3 simulated truck-days of normal driving"
- **Speaker Notes:**
  - The biggest lever by far: energy is calls × joules per call, and this changes the calls by three to four orders of magnitude.
  - Caveats: "per incident" is 17-28 calls; the zero comes from simulated normal driving.
  - Backing: paper Fig. 4 (§IV-F); `docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md` row 28.
  - Forward: the events that do reach the model should arrive finished.
- **Time:** Section 2, ~0.75 min.

### Slide 8 — …the one whose inputs are already calculated
- **Core Message:** compute features where the data lives; the model gets facts, not a stream.
- **Visual Manifest:** Type `Mermaid_Architecture`, drawn natively. Spec: three small boxes left to right: "Truck: rolling average speed, stop-and-go index, ETA slip" → "Co-processor: baseline severity, trip context" → "Model: one finished event".
- **Suggested Layout:** `Content`.
- **On-Screen Text:**
  - Eyebrow: "THE GREENEST TOKEN IS…"
  - Technique: "The truck does the arithmetic; the co-processor adds what it knows; the model reads one finished event"
  - Line: "Given two raw numbers, small models didn't work out the difference themselves"
- **Speaker Notes:**
  - Arithmetic is exact and nearly free in code; in a model it's tokens and guesses.
  - No model in this pipeline ever sees a stream: the co-processor handles one event at a time, and the truck's telemetry already carries a short rolling window.
  - Backing: impact track, "Velocity deviation-from-plan" (handing two raw numbers "did nothing").
  - Forward: and some decisions shouldn't be the model's at all.
- **Time:** Section 2, ~0.75 min.

### Slide 9 — …the one that doesn't stand in for a better tool
- **Core Message:** classification and thresholds belong in code (or a classic ML model), not in an LLM.
- **Visual Manifest:** Type `Typography_Only`, overridden to a stat. Spec: one big stat, a technique line and a contrast line.
- **Suggested Layout:** `Stats`.
- **On-Screen Text:**
  - Eyebrow: "THE GREENEST TOKEN IS…"
  - Technique: "Severity from five lines of threshold code, not from the model"
  - Stat: "20–63%" / "of severity calls wrong, even with the thresholds written into the prompt"
  - Line: "Code: exact, every time"
- **Speaker Notes:**
  - A threshold is exact in code and approximate in a model. If a rule can be written down, don't spend tokens asking a model to apply it.
  - Backing: `eval-results/compare-COMP-J2D9D71YNJ-20260925T185711Z.json` (thresholds stated; 7 models with parseable answers).
  - Forward: what's left for the model is one judgment.
- **Time:** Section 2, ~0.75 min.

### Slide 10 — …the one asked a simple, directed question
- **Core Message:** give the model one bounded judgment, not the whole job.
- **Visual Manifest:** Type `Bar_Comparison`, overridden to two stats side by side. Spec: "94–100%" vs "11–22%".
- **Suggested Layout:** `Stats`.
- **On-Screen Text:**
  - Eyebrow: "THE GREENEST TOKEN IS…"
  - Technique: "The model answers one question: raise, hold or lower the baseline?"
  - Stats: "94–100%" / "small models correct on one judgment" · "11–22%" / "the same models on the whole job"
- **Speaker Notes:** same models, same cases; only the scope changed. Backing: paper Table VI (§IV-D; round 3, M4 Max, raw mode). Forward: then make sure the answer comes back in the right shape.
- **Time:** Section 2, ~0.75 min.

### Slide 11 — …the one told what shape to take
- **Core Message:** constrain the output with a grammar, use placeholders instead of example values, and size the token cap to the answer.
- **Visual Manifest:** Type `Typography_Only`, overridden to two stats. Spec: two stat blocks and a technique line.
- **Suggested Layout:** `Stats`.
- **On-Screen Text:**
  - Eyebrow: "THE GREENEST TOKEN IS…"
  - Technique: "A grammar, placeholders instead of example values, a token cap that fits the answer"
  - Stat: "30 of 30" / "answers valid with a grammar (16 of 30 without, for a 0.5B model)"
  - Stat: "28 of 30" / "calls that copied the example's number when my template showed one"
- **Speaker Notes:** a grammar makes malformed output impossible. It fixes structure, not judgment. Backing: `…20260925T165011Z` → `…20260926T153435Z` (same machine); `git show 6ff72a3:shared/llm-inference/src/llm_inference/structured.py` (lines 19-27). Forward: then stop paying to re-read what hasn't changed.
- **Time:** Section 2, ~0.75 min.

### Slide 12 — …the one read only once
- **Core Message:** put the fixed instructions first and the per-request data last, so the prompt cache does the re-reading.
- **Visual Manifest:** Type `Bar_Comparison`, overridden to two stats. Spec: two before → after stats.
- **Suggested Layout:** `Stats`.
- **On-Screen Text:**
  - Eyebrow: "THE GREENEST TOKEN IS…"
  - Technique: "Fixed instructions first, per-request data last"
  - Stat: "~400 → ~148" / "prompt tokens re-read per new event, of 514"
  - Stat: "772 J → 416 J" / "per new event on a Raspberry Pi 4"
- **Speaker Notes:** a cache reuses a prompt only up to the first token that changed. Backing: paper Table IV (§IV-B, "When the prompt changes"); `eval-results/edge-triage-event-last-pi4-20261005/`. Forward: and don't pay for thinking you don't need.
- **Time:** Section 2, ~0.75 min.

### Slide 13 — …the one the model never thinks
- **Core Message:** turn thinking off for short, bounded tasks; cap it if you need it.
- **Visual Manifest:** Type `Typography_Only`, overridden to two stats. Spec: two stat blocks.
- **Suggested Layout:** `Stats`.
- **On-Screen Text:**
  - Eyebrow: "THE GREENEST TOKEN IS…"
  - Technique: "Thinking off for short, bounded tasks; a cap if you need it"
  - Stat: "4–11×" / "the time with thinking on, for no measurable accuracy gain"
  - Stat: "4–7×" / "the energy per call on an iPhone-class M1"
- **Speaker Notes:** Backing: paper Fig. 3 and Table VI (§IV-D; round 3, three machines). Forward: those are the seven. Now, how I found them, starting where Talk 1 left off.
- **Time:** Section 2, ~0.75 min.

## Phase: Section 3, how I found them (21.5 min, 16 slides)

### Slide 14 — How I found them
- **Core Message:** every technique came from something that went wrong.
- **Visual Manifest:** Type `Typography_Only`. Spec: section title and subtitle.
- **Suggested Layout:** `Section` (plate).
- **On-Screen Text:** "How I found them" / "One truck, one small model, a lot of wrong turns"
- **Speaker Notes:** this is the use case from Talk 1, the Edge Triage Pipeline, seen from the inside. Forward: the cloud way first.
- **Time:** Section 3, ~0.25 min.

### Slide 15 — Stream Everything to the Cloud? Too Slow.
- **Core Message:** the cloud-centric pipeline streams every raw reading to a cloud core that's already overloaded: the dragon from slide 3.
- **Visual Manifest:** Type `Mermaid_Architecture`. Spec: **reused from Talk 1's current deck, slide 6, as built**:
  - **Left:** "Dumb Edge", three truck icons, "raw, unfiltered".
  - **Middle:** "High-Latency Cellular Pipeline" ribbons labeled "RPM", "GPS", "Brake wear".
  - **Right:** a "Cloud Core" box marked "Overloaded", holding "Ingestion Queues: Overloaded", "Stream Processing: Lagging" and "Data Lakes".
  - **Bottom:** a row of three badges.
  - **Changed for this talk (user approved 2026-10-06):**
    - the Data Lakes tag "Up to 95% Noise Data" → "every raw reading";
    - the Data efficiency badge's BEFORE → "every reading: 9.2 MB per truck-day";
    - the Decision latency and Network risk badges unchanged.
- **Suggested Layout:** `Content` (as in Talk 1).
- **On-Screen Text:** Talk 1's slide 6, with the changes above.
- **Speaker Notes:**
  - This is the dragon's diet: every reading from every truck streamed over cellular to a cloud core that queues, lags and stores mostly noise.
  - One truck sends an event every 5 seconds: 17,280 a day, 9.2 MB.
  - Forward: Talk 1's answer.
- **Time:** Section 3, ~1.25 min.

### Slide 16 — Put the Judgment on the Truck
- **Core Message:** move the judgment onto a commodity edge node running a small LLM, and send only filtered anomalies.
- **Visual Manifest:** Type `Mermaid_Architecture`. Spec: **reused from Talk 1's current deck, slide 9, as built**:
  - **Top:** "Commodity Edge Node (Raspberry Pi 4 Class Hardware / 4GB-8GB RAM)" and "Small LLM · Edge Diagnostics Model".
  - **Left:** "Smart Edge" trucks.
  - **Right:** flow lines to "Lean Cloud Core · Operations Control Center".
  - **Bottom:** three badges.
  - **Changed for this talk (user approved 2026-10-06):**
    - "Sub-second Local Action" → "Local action, no round trip";
    - "Filtered Anomalies Only (Up to 90% Bandwidth Savings)" → "Filtered anomalies only (~4 KB per incident instead of 9.2 MB a day)";
    - Decision latency AFTER → "decided on the truck, no round trip";
    - Data efficiency BEFORE → "every reading: 9.2 MB per truck-day", AFTER → "~4 KB per incident";
    - Network risk unchanged.
- **Suggested Layout:** `Content` (as in Talk 1).
- **On-Screen Text:** Talk 1's slide 9, with the changes above.
- **Speaker Notes:**
  - Talk 1 showed this runs: a small LLM on a Pi-class box decides on the truck, and only what matters crosses the link.
  - This talk is about what it took to make that work, and what each decision costs.
  - Forward: is a Pi even the right edge node?
- **Time:** Section 3, ~1.25 min.

### Slide 17 — The edge node could be the phone in the driver's pocket
- **Core Message:** phone-class hardware already generates fast enough for small models.
- **Visual Manifest:** Type `Device_Spectrum`. Spec: the paper's Fig. 1, generation speed (tg128, tokens/s) for Qwen3.5-2B, Gemma-4-E2B, Gemma-3-4B, Phi-3.5-mini and Llama-3.1-8B on four platforms: the mainstream Android stand-in (c7g), the flagship Android stand-in (c9g), the M1 GPU and the M4 GPU. It includes the published iPhone 17 Pro points (39.1 and 38.8 tokens/s). File: `slides/charts/slide_fig1_speed.png`.
- **Suggested Layout:** `Content`.
- **On-Screen Text:**
  - "M1 ≈ iPhone 17 Pro (within 9%)"
  - "17 models, 0.34–9.4B parameters, 4-bit, one llama.cpp build"
  - "Baseline: a Raspberry Pi 4, metered at the wall"
- **Speaker Notes:**
  - Phones are the real target. These are stand-ins, not phones; real phones are next.
  - The M1 lands on the iPhone 17 Pro's published numbers. What fits in memory: up to 4B parameters in 4 GiB, 8-9B in 6 GiB.
  - I started on a Pi 4, the slowest box in the study: if it works there, it works anywhere.
  - Forward: my first attempt.
- **Time:** Section 3, ~1.0 min.

### Slide 18 — My first attempt: let the small model write the whole card
- **Core Message:** I asked a small LLM to do the whole job in one call: classify severity and describe the ETA impact, as JSON.
- **Visual Manifest:** Type `Code_Block`. Spec: the real prompt (2026-09-12), verbatim, shortened only at "…", beside a KPI.
- **Suggested Layout:** `Metric` (Code + KPI).
- **On-Screen Text:**
  - Code block:
    ```
    You are generating a structured enrichment card for fleet dispatch. Cheap math has already detected the signals below — do not re-derive detection, just classify severity and describe the ETA impact.

    Respond with ONLY a single JSON object with exactly these keys: "event", "severity", "signals", "eta_impact", "corridor", "truck_id". No prose, no markdown fences.

    Truck: truck-47
    Corridor: I-95N
    Signals detected by cheap math: ['sustained_low_speed', 'stop_go_index', 'eta_slip']
    Rolling average speed: 35.0 mph
    ETA slip: 6.0 minutes
    …
    Shape (placeholders only, not real values): {"event": "<event_name>", "severity": "<low|medium|high>", "signals": ['sustained_low_speed', 'stop_go_index', 'eta_slip'], …}
    ```
  - KPI: "6 fields, 1 call" / "the model classifies, measures and writes everything"
- **Speaker Notes:**
  - The naive idea: small LLMs are smart now, so hand one the event and ask for the finished card.
  - I never fed it raw telemetry: the cheap-math gate was rule one from Talk 1's design. But I asked it to do everything else.
  - Notice my own template: the signals list is in single quotes. That comes back on the next slides.
  - Backing: `eval-results/compare-COMP-J2D9D71YNJ-20260912T202854Z.json` (prompt as the model saw it).
  - Forward: how it went.
- **Time:** Section 3, ~1.5 min.

### Slide 19 — It failed on every measure
- **Core Message:** too slow, unparseable, wrong, and it copied my example.
- **Visual Manifest:** Type `Typography_Only`, overridden to four stats. Spec: four stat blocks, each tagged with its measure.
- **Suggested Layout:** `Stats`.
- **On-Screen Text:**
  - "111.5 s" / "per call on the Pi 4 (Qwen2.5-1.5B), with a new event every 5 s" (SPEED)
  - "22 of 30" / "answers parsed as JSON (1 of 30 for the 0.5B model)" (ACCURACY)
  - "37–81%" / "of severity calls wrong, across models" (ACCURACY)
  - "28 of 30" / "calls that copied my example's 4.0 instead of the real 18.0" (ACCURACY)
- **Speaker Notes:**
  - On the Pi it took almost two minutes per answer, and the slowest calls hit the 180-second timeout. More than 20 new events arrive while it answers one.
  - Severity: 7 models on the laptop, wrong 37-81% of the time.
  - The copying was the first version of the prompt, which showed a filled-in example card. The model copied its 4.0 into nearly every answer.
  - Backing: `eval-results/compare-edge-node00-20260925T030826Z.json` (Pi 4: p50 111.5 s, p95 180.3 s; parsed 22/30 and 1/30); `…20260925T165011Z.json` (severity); `6ff72a3` comment (copying).
  - Forward: what it actually wrote.
- **Time:** Section 3, ~1.5 min.

### Slide 20 — What it actually wrote
- **Core Message:** told "no prose", the models wrote prose, copied my broken template, and looped.
- **Visual Manifest:** Type `Code_Block`. Spec: three verbatim panels, each with a header naming the model and machine, and highlighted callouts.
- **Suggested Layout:** `Content`.
- **On-Screen Text:**
  - Panel 1, header "Asked for JSON only (Qwen2.5-1.5B, laptop)":
    ```
    To classify the severity and describe the ETA impact, we need to analyze the detected signals and the rolling average speed. Here's the process:
    …
    The truck is slipping ahead by 6 minutes, which is a significant delay for the entire convoy behind it.
    …
    ```json
    {
      "event": "Traffic Congestion and Slip Ahead",
      "severity": "high",
      …
      "truck_id": "truck-
    ```
    Callouts: "prose" on the first line; "slipping ahead?" on "slipping ahead"; "cut off mid-answer" on the last line.
  - Panel 2, header "Copied my template's quotes (Qwen2.5-1.5B, Pi 4)":
    ```
    Here is the JSON object:

    {
      "event": "ETA slip",
      "severity": "high",
      "signals": ['sustained_low_speed', 'stop_go_index', 'eta_slip'],
      "eta_impact": 6.0,
      "corridor": "I-95N",
      "truck_id": "truck-47"
    }
    ```
    Callouts: "prose again" on the first line; "single quotes: not JSON, copied from my prompt" on the signals line.
  - Panel 3, header "Repeated the template (Qwen2.5-0.5B, Pi 4)":
    ```
    {"event": "<event_name>", "severity": "<low|medium|high>", … } {"event": "<event_name>", "severity": "<low|medium|high>", … } {"event": "<event_name>", …
    ```
    Callout: "until it ran out of tokens".
- **Speaker Notes:**
  - Three different failures.
  - The second one is on me: my template showed a Python-style list, and the model did what I showed, not what I said.
  - Early on I thought small models were echoing my prompt back. They weren't: the command-line tool printed the prompt into the output, and the smallest models had written nothing at all. The real parroting is panel 3, the template on repeat.
  - Backing: `…20260912T202854Z.json` (1.5B, sample_failures[2]); `…20260925T030826Z.json` (1.5B and 0.5B, sample_failures[0]).
  - Forward: the fixes, biggest first.
- **Time:** Section 3, ~1.5 min.

### Slide 21 — Fix 1: call the model only when it matters
- **Core Message:** a Pi can't answer every event, so a cheap-math gate decides when the model runs.
- **Visual Manifest:** Type `Typography_Only`, overridden to three stats. Spec: three stat blocks and a gate line.
- **Suggested Layout:** `Stats`.
- **On-Screen Text:**
  - Eyebrow: "…NEVER SENT TO THE DATA CENTER"
  - Stats: "17,280" / "events per truck per day" · "~2,700" / "calls a day a Pi 4 can answer, at 31.7 s each" · "~23" / "LLM calls per incident, after the gate"
  - Line: "The gate: real slowdown signals and an ETA slip of 3–60 minutes"
- **Speaker Notes:**
  - To be fair to myself: this gate was in the design from day one, from Talk 1. These numbers show why it isn't optional.
  - Even gated, an incident's ~23 calls take 12-15 minutes of LLM work on the Pi for a 2-4 minute incident. Calling once per incident would cut that about 20×; I haven't built it yet.
  - Backing: paper Table II (31.7 s per call, repeated prompt); `~2,700` = 86,400 s / 31.7 s; impact track (12-15 minutes; 17-28 calls per incident).
  - Forward: what the gate hands the model.
- **Time:** Section 3, ~1.25 min.

### Slide 22 — Fix 2: give it facts, not a stream
- **Core Message:** by the time the model sees an event, the math is done.
- **Visual Manifest:** Type `Code_Block`. Spec: the triage payload (shape from `coprocessor.build_triage_payload`; values as on Talk 1's slide 19, illustrative), with highlights, beside a KPI.
- **Suggested Layout:** `Metric` (Code + KPI).
- **On-Screen Text:**
  - Eyebrow: "…WHOSE INPUTS ARE ALREADY CALCULATED"
  - Code block:
    ```json
    {
      "truck_id": "truck-47",
      "corridor": "I-95N",
      "signals": ["sustained_low_speed", "stop_go_index", "eta_slip"],
      "metrics": {
        "rolling_avg_speed": 36.1,
        "eta_slip_min": 7.2,
        "traffic_pattern": "elevated velocity variance (frequent speed cycling)",
        "peak_deceleration_g": 0.31,
        "abs_engaged": false
      },
      "baseline_severity": "medium",
      "contextual_triggers": {
        "weather_condition": "Heavy rain, wet asphalt",
        "cargo_type": "Liquids / Chemical Tanker",
        "dispatch_status": "Running 20 minutes behind schedule"
      }
    }
    ```
    Highlights: "rolling_avg_speed" and "eta_slip_min", callout "computed on the truck"; "traffic_pattern", "baseline_severity" and "contextual_triggers", callout "added by the co-processor".
  - KPI: "1 event" / "per call: the model never sees a stream"
- **Speaker Notes:**
  - The truck's telemetry already carries a short rolling window. The co-processor works one event at a time: it gates it, labels the traffic pattern, looks up the trip and sets a baseline severity from the physics.
  - When I handed small models two raw numbers to compare, none of them worked out the difference. So compute the fact first.
  - Values as on Talk 1's slide 19 (illustrative).
  - Forward: and some decisions shouldn't be the model's at all.
- **Time:** Section 3, ~1.25 min.

### Slide 23 — Fix 3: classification belongs in code
- **Core Message:** even with the rule written into the prompt, models misclassified; five lines of code don't.
- **Visual Manifest:** Type `Bar_Comparison`. Spec: two columns: the model's output with the rule stated, and the same decision in code.
- **Suggested Layout:** `Comparison`.
- **On-Screen Text:**
  - Eyebrow: "…DOESN'T STAND IN FOR A BETTER TOOL"
  - Left header: "Asking the model (Llama-3.1-8B)". Line: "The prompt said: 'low' means ETA slip under 5.0 minutes. Input: 3.0 minutes." Code:
    ```json
    {"event": "fleet_dispatch_enrichment", "severity": "high", "signals": ["sustained_low_speed", "stop_go_index", "eta_slip"], "eta_impact": 3.0, "corridor": "I-95N", "truck_id": "truck-47"}
    ```
    Highlight "severity": "high", callout "expected low". Under: "Wrong on 45 of 89 calls. Across models, 20–63% wrong with the thresholds stated"
  - Right header: "The same decision in code". Code:
    ```python
    if abs_engaged:
        return "high"
    if g > HIGH_G_FLOOR:
        return "high"
    if g <= LOW_G_CEILING:
        return "medium" if stop_go_index > HIGH_VOLATILITY_STOP_GO_INDEX else "low"
    return "high" if stop_go_index > HIGH_VOLATILITY_STOP_GO_INDEX else "medium"
    ```
    Under: "Exact, every time. The model now weighs only what code can't: weather, cargo, schedule."
- **Speaker Notes:**
  - The rule changed between the two designs: ETA tiers then, vehicle physics now. The point is where the rule lives.
  - Even after a grammar made every answer parse, severity was still wrong on 33-73% of calls across 15 models.
  - Backing: `…20260925T185711Z.json` (Llama sample_mismatches[0], 45/89); `…20260926T153435Z.json` (33-73%); `severity_classifier.classify_severity`.
  - Forward: so what's left for the model?
- **Time:** Section 3, ~1.5 min.

### Slide 24 — Fix 4: one bounded judgment, not the whole job
- **Core Message:** code computes the facts; the model answers one question: raise, hold or lower.
- **Visual Manifest:** Type `Bar_Comparison`. Spec: two columns, each a short definition above a code panel, with matching highlights.
- **Suggested Layout:** `Comparison`.
- **On-Screen Text:**
  - Eyebrow: "…ASKED A SIMPLE, DIRECTED QUESTION"
  - Left header: "One bounded judgment (production)". Definition: "Code computes the facts first. The model answers one question: raise, hold or lower?" Code panel:
    ```
    A deterministic vehicle-physics system has already computed a baseline severity … Your only job is to decide whether the three operational-context fields below, taken together, are strong enough evidence to move away from it.

    BASELINE SEVERITY (already computed from vehicle physics): medium

    Operational context:
    Weather: Clear skies, dry pavement
    Cargo: Dry goods / General freight
    Dispatch status: On schedule

    How to weigh each field: …
    Decision:
    - raise: … - lower: … - hold: …
    ```
    Under it, small: "Model writes: risk_synthesis, escalation. Code adds: final severity, action, truck ID, ETA."
  - Right header: "The whole job (round 3's test)". Definition: "The model gets the raw physics and the rules, and must do all three steps in one call." Code panel:
    ```
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
    ```
    Under it, small: "Model writes all six fields."
  - Highlights: "BASELINE SEVERITY (already computed from vehicle physics): medium" on the left, and "STEP 1" and "STEP 3" on the right, in the same color, with the callout "work moved from code into the model".
- **Speaker Notes:** same model, same operational context, same escalation rules; only the scope differs. On the left, five lines of code have already worked out the baseline from the physics, and the model weighs weather, cargo and dispatch. On the right, the model has to apply the thresholds itself, then the escalation, then derive the final severity and the action. Backing: `DEFAULT_PROMPT_TEMPLATE` (`talks/talk1-edge-intelligence/src/talk1_edge_intelligence/triage_function.py`); `FULL_PROMPT_TEMPLATE` (`tests/model/round3_eval.py`). Forward: what came back.
- **Time:** Section 3, ~1.75 min.

### Slide 25 — Same model, same case: what came back
- **Core Message:** given one question, the model weighed each field and held; given the whole job, it raised on the physics and contradicted itself.
- **Visual Manifest:** Type `Bar_Comparison`. Spec: two code panels side by side, a verdict badge under each, one result line across the bottom.
- **Suggested Layout:** `Comparison`.
- **On-Screen Text:**
  - Left header: "One bounded judgment". Code panel:
    ```json
    {
      "risk_synthesis": "Cargo: The cargo is dry goods / general freight, which is not a risk multiplier. Weather: The weather is clear skies, dry pavement, which is not a risk multiplier. Dispatch status: The dispatch status is on schedule, which is not a risk multiplier. Therefore, the baseline severity of medium remains appropriate.",
      "escalation": "hold",
      "truck_id": "truck-47"
    }
    ```
    Badge (green): "Correct: hold".
  - Right header: "The whole job". Code panel:
    ```json
    {
      "baseline_severity": "medium",
      "risk_synthesis": "Traffic pattern: elevated velocity variance (frequent speed cycling) and peak deceleration: 0.3 g",
      "escalation": "raise",
      "severity": "medium",
      "recommended_action": "Escalate for driver/dispatcher review.",
      "truck_id": "truck-47"
    }
    ```
    Highlight "escalation": "raise", callout "raised on the physics alone; the context is benign". Highlight "severity": "medium", callout "a raise should make it high: it contradicts itself". Badge (orange): "Wrong: should hold".
  - Bottom line, large: "Small models: 94–100% correct on one judgment, 11–22% on the whole job"
- **Speaker Notes:**
  - Gemma-3-4B, the same benign case. Given one question, it weighed each field and held. Given the whole job, it reasoned about the physics instead of the context, raised, then wrote a severity that contradicts its own raise.
  - Across the small models, accuracy fell from 94-100% to 11-22%. Every part of the job got worse, even the escalation it had just done well.
  - Backing: `eval-results/compare-round3-COMP-J2D9D71YNJ-20261004T154259Z.json` (calls[1]) and `…154409Z.json` (calls[7]); paper Table VI.
  - Forward: then make the shape impossible to get wrong.
- **Time:** Section 3, ~1.75 min.

### Slide 26 — Fix 5: tell it the shape
- **Core Message:** a grammar makes malformed output impossible; it fixes structure, not judgment.
- **Visual Manifest:** Type `Bar_Comparison`. Spec: left, the free-text answer (from slide 20, panel 2); right, the grammar and a grammar-shaped answer; a numbers line across the bottom.
- **Suggested Layout:** `Comparison`.
- **On-Screen Text:**
  - Eyebrow: "…TOLD WHAT SHAPE TO TAKE"
  - Left header: "Free text, 'no prose' in the prompt". Code: slide 20's panel 2, shortened (first line "Here is the JSON object:" and the single-quoted signals line, highlighted).
  - Right header: "With a grammar". Code (the triage card's grammar):
    ```
    root ::= "{\n"
      "  \"risk_synthesis\": \"" [^"]* "\",\n"
      "  \"escalation\": " ("\"raise\"" | "\"hold\"" | "\"lower\"") ",\n"
      "  \"truck_id\": " "\"truck-47\"" "\n"
      "}"
    ```
    Under it: "The truck ID can't be wrong: it's written into the grammar."
  - Bottom line: "Same laptop: 28 → 30 of 30 valid (Qwen2.5-1.5B), 16 → 30 (0.5B), 0 → 30 (a 350M model)"
  - Small line: "Placeholders, not example values: a filled-in example was copied on 28 of 30 calls"
  - Small line: "Structure, not judgment: every answer parsed, and severity was still wrong 33–73% of the time"
- **Speaker Notes:**
  - The grammar is the cheapest accuracy win in the study, but only for the shape. The next change, the narrower task, is what fixed the answers.
  - The before/after is on the same laptop, but the prompt and temperature changed too.
  - The second 350M model reached 25 of 30.
  - Backing: `…20260925T165011Z.json` → `…20260926T153435Z.json`; grammar from `triage_function.py`.
  - Forward: now, speed.
- **Time:** Section 3, ~1.75 min.

### Slide 27 — Fix 6: fixed instructions first
- **Core Message:** a prompt cache reuses only what hasn't changed, so the fixed instructions go first and the per-request data last.
- **Visual Manifest:** Type `Mermaid_Architecture`, drawn natively. Spec: two tall prompt diagrams side by side, each drawn as stacked blocks labeled with what the block contains:
  - **Left header:** "As built: event fields near the top".
    - Blocks, top to bottom: "Intro" · "Baseline + weather, cargo, dispatch (changes per event)" · "How to weigh each field (rules)" · "Decision rules" · "Truck ID, corridor" · "Closing instruction".
    - A dashed line labeled "cache ends at the first line that changes" sits at the top of the second block. Every block below the line is shaded orange: "re-read per new event: ~400 of 514 tokens".
  - **Right header:** "Event last: rules first".
    - Blocks: "Intro" · "How to weigh each field (rules)" · "Decision rules" · "Baseline + weather, cargo, dispatch (changes per event)" · "Truck ID, corridor" · "Closing instruction".
    - The dashed line sits at the top of the fourth block, and only the blocks below it are shaded: "re-read: ~148 of 514 tokens".
  - **Optional small inset:** `slides/charts/slide_changed_prompt.png`.
- **Suggested Layout:** `Content`.
- **On-Screen Text:**
  - Eyebrow: "…READ ONLY ONCE"
  - The two diagrams as above.
  - Bottom line: "On the Pi 4, per new event: 160 s and 772 J → 82 s and 416 J. Same words, same accuracy on llama-server."
- **Speaker Notes:**
  - Found while preparing this talk. My benchmark repeated one event, so the server read 1 of 514 prompt tokens: it measured a repeat, not a call.
  - A new event re-read about 400, because my prompt put the event's fields before the rules. Moving them after, same words otherwise: 148.
  - On a CPU, reading the prompt is the slow part (129 of the 160 seconds). On the laptop GPU the same change saved 26%; on the Pi, 46%.
  - It's opt-in in the code, and re-check accuracy when you reorder: through llama-cpp-python the reordered prompt tipped a borderline case.
  - Backing: paper Table IV (§IV-B, "When the prompt changes"); `eval-results/edge-triage-event-last-pi4-20261005/`.
  - Forward: and put a ceiling on every call.
- **Time:** Section 3, ~1.5 min.

### Slide 28 — Fix 7: bound every call
- **Core Message:** cap the tokens to fit the answer, and set the timeout from measured latency.
- **Visual Manifest:** Type `Typography_Only`, overridden to three cards. Spec: three cards, each a heading and one line.
- **Suggested Layout:** `Three-up`.
- **On-Screen Text:**
  - Card "Token cap": "At 150 tokens, 8 of 10 cards were cut off; 300 fixed it."
  - Card "Thinking cap": "Capped at 1,024 tokens, every call finished. Uncapped, Qwen3.5-9B never finished thinking on 11 of 18."
  - Card "Timeout": "Set it from measured latency. A throttling Pi 4 hit the 300 s timeout on 5 of 15 calls, until it got a fan."
- **Speaker Notes:**
  - A timeout doesn't stop a runaway model; a token cap does. The timeout bounds the wall clock, so set it from what you measured.
  - My own function's 60-second default is shorter than a changed-prompt call on the Pi (82-160 s). Measure before you set it.
  - Backing: commit `754ab57` (150 → 300, 0 of 10 truncated); paper §IV-D (capped thinking; 11 of 18); impact track (5 of 15 at 300 s, fan).
  - Forward: the cap I needed most was on thinking.
- **Time:** Section 3, ~1.0 min.

### Slide 29 — Fix 8: thinking off
- **Core Message:** reasoning added time and energy without measurable accuracy.
- **Visual Manifest:** Type `Time_Series_Line_Chart`, overridden to a chart slide. Spec: the paper's Fig. 3, correctness (%) vs median latency (s, log) for Qwen3-8B, Qwen3-14B, Qwen3.5-9B and Qwen3.8-27B in raw, chat-off and chat-on modes, plus capped thinking (hollow diamonds). Qwen3.5-9B's chat-on point is omitted (harness artifact, test log incident 27). File: `slides/charts/slide_fig3_thinking.png`. Beside it, two mini-cards.
- **Suggested Layout:** `Content`. Override: the affinity map's `Stats` can't show the trade-off curve.
- **On-Screen Text:**
  - Eyebrow: "…THE ONE THE MODEL NEVER THINKS"
  - "No measurable gain, at 4–11× the time and 4–7× the energy per call"
  - Card 1, header "Qwen3-14B, one case: thinking fixed it". Lines: "Off: 4.81 s, 125 tokens, baseline wrong (medium)". "On: 18.55 s, 449 tokens (349 thinking), right (high)".
  - Card 2, header "Another case: thinking broke it". Lines: "Off: 5.04 s, right (hold)". "On: 15.71 s, 580 tokens, wrong (lower)".
  - Line under the cards: "Across all 36 cases: 72% off vs 78% on, inside each other's error bars"
- **Speaker Notes:**
  - Production never had thinking on. This is what happened when I tried it, on three machines.
  - Qwen3-14B 72% → 78%, Qwen3-8B 44% → 47%, Qwen3.8-27B 67% → 67%: all within each other's ranges. On the iPhone-class M1, Qwen3-14B went from 202 to 817 J per call.
  - A short, bounded judgment doesn't need multi-step reasoning, and some models don't know when to stop.
  - Backing: paper Fig. 3 and §IV-D; round 3 files `…T165312Z` and `…T171623Z` (calls 9 and 4).
  - Forward: those are the fixes. Here's the version for any LLM.
- **Time:** Section 3, ~1.5 min.

## Phase: Section 4, what you can do (4.5 min, 4 slides)

### Slide 30 — What you can do, with any LLM
- **Core Message:** the techniques, as a checklist for any LLM.
- **Visual Manifest:** Type `Typography_Only`. Spec: an eight-item checklist in two columns of four, generous type, a check mark per item.
- **Suggested Layout:** `Content`.
- **On-Screen Text:**
  1. "Filter first: cheap math decides when the model runs"
  2. "Send facts, not streams: compute features where the data lives"
  3. "Keep classification in code (or a classic ML model)"
  4. "Ask one bounded question, not the whole job"
  5. "Constrain the output: a grammar or schema; placeholders, not example values"
  6. "Fixed instructions first, per-request data last"
  7. "Cap tokens and time; thinking off unless it measurably helps"
  8. "Measure joules per job, on many different cases; re-test after any model, quantization or runtime change"
- **Speaker Notes:** the slide to photograph. Every line is one of the fixes, true whether the model is on a phone or in a data center; the first three decide whether a token exists at all. Forward: and to know whether it's working, you have to be able to see it.
- **Time:** Section 4, ~1.5 min.

### Slide 31 — Running LLMs is an observability problem
- **Core Message:** most of these failures were invisible to latency monitoring; observe energy, completion, memory, heat, correctness, call rate and what the cache served.
- **Visual Manifest:** Type `[NEEDS: new visual type not yet in the supported list]`. Spec: a 7-row table (Signal | Failure it caught | Effect) from the paper's Table VII, plus a small dashboard placeholder.
- **Suggested Layout:** `Content`.
- **On-Screen Text:**
  - Lead: "Latency looked fine. These didn't."
  - Table:
    - energy per decision | thinking on | 202 → 817 J per call, accuracy unchanged
    - completion rate | thinking runaway | 11 of 18 calls never finished thinking
    - memory headroom | default context size | ~50 GB reserved, ~6 GB needed
    - thermal state | sustained load | cool: 24–77% faster, 30–60% more energy per call
    - correctness, per case | Q4_0 on Gemma-3-4B | errors 0% → 30%, energy −10–41%
    - invocation rate | no gate vs gate | 17,280 vs ~23 calls per truck-day
    - prompt tokens read per call | a benchmark repeating one input | 1 vs 400 of 514 tokens; Pi 4: 154 → 772 J per call
  - Inset: [PLACEHOLDER: Datadog dashboard screenshot of these signals]
- **Speaker Notes:**
  - An LLM in production is a system to observe, not a function to time. In almost every failure in this talk the latency looked normal; the problem showed up in energy, completion, memory, heat, correctness, call rate or cache reads.
  - Each row is a metric I'd put on a dashboard. Carbon per decision is energy × the grid's carbon intensity where and when it ran.
  - Backing: paper Table VII (§VI).
  - Forward: and what I got wrong along the way.
- **Time:** Section 4, ~1.5 min.

### Slide 32 — What I got wrong
- **Core Message:** five assumptions the data overturned.
- **Visual Manifest:** Type `Typography_Only`. Spec: five rows, each the assumption in quotes, then what happened.
- **Suggested Layout:** `Content`.
- **On-Screen Text:**
  1. "A small device uses less energy." A slow CPU used more per decision: ~154 J on a Pi 4 vs 15–20 J on Apple GPUs.
  2. "More repeats make a result solid." Repeats agreed 73–92% of the time: "18 of 18" means somewhere between 44% and 100%.
  3. "A cheaper quantization is a free win." Q4_0 made Gemma-3-4B wrong on 30% of escalations, for 10–41% less energy.
  4. "The defaults are sensible." A server's default 128k context reserved ~50 GB on a 64 GB laptop, for a task that needs under 1,000 tokens.
  5. "The chat format doesn't matter." The model's own chat template took Qwen3.5-9B from 22% to 72%.
- **Speaker Notes:**
  - The first one is why the title says GPU, not "GPU-free": energy is power × time, so a slow chip pays for every second. The greenest token never reaches a data center's GPU; on your own device, use its accelerator.
  - The abstract promised 1-bit models on CPUs. They didn't run correctly on ARM at all, so the study used ordinary 4-bit models. The abstract's other claim, calling the model only when it's needed, turned out to be the whole story.
  - Backing: paper Fig. 2 (§IV-B, energy); §III-D and §IV-D (repeats agreed in 90-92% of full-task and 73-79% of narrow-task cases); Table V (§IV-C, quantization); §IV-E and test log incidents 14 and 23 (context); Table VI (§IV-D, chat template).
  - Forward: thank you.
- **Time:** Section 4, ~1.5 min.

### Slide 33 — Thank you
- **Core Message:** the paper and what's next.
- **Visual Manifest:** Type `Typography_Only`. Spec: title and one subtitle line.
- **Suggested Layout:** `Closing` (plate).
- **On-Screen Text:** "Thank you" / "Paper: [PLACEHOLDER: link, or 'preprint coming'] · Next: real phones and their NPUs" / "David Kjerrumgaard · Datadog"
- **Speaker Notes:** take questions. Talk 1 and Talk 3 complete the series.
- **Time:** Q&A, outside the 40 minutes.

---

## Checks

**Deck rhythm.** Plates are `Title`, `Section`, `Quote`, `Product`, `Statement` and `Closing`; (P) marks them below:
- **Slides 1-5:** 1 Title (P) · 2 Stats · 3 Three-up · 4 Statement (P) · 5 Content
- **Slides 6-13:** 6 Section (P) · 7 Stats · 8 Content · 9-13 Stats
- **Slides 14-20:** 14 Section (P) · 15-16 Content · 17 Content · 18 Metric · 19 Stats · 20 Content
- **Slides 21-29:** 21 Stats · 22 Metric · 23-26 Comparison · 27 Content · 28 Three-up · 29 Content
- **Slides 30-33:** 30-32 Content · 33 Closing (P)

No two plates are adjacent, and every plate carries `Typography_Only`. Section 2's seven slides share one family look, with the eyebrow, the line and the big number in the same positions.

**Placeholders and pending items:**

| Slide | Item |
|---|---|
| 2 | [IMAGE: the data center as a dragon's lair] |
| 31 | Datadog dashboard screenshot |
| 33 | paper link |

**Confirm before the talk:** the opening's external figures are from primary reports (outline Sources). Re-check any that you change.

**Total: ~37 min across 32 timed slides (target: 40 min).** Section 1 5.5, Section 2 5.5, Section 3 21.5, Section 4 4.5. The closing slide sits in Q&A. The user averages under 2 minutes a slide; the ~3 minutes of slack is deliberate.
