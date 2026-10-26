# Talk 2 outline: "The Greenest Token" (draft 4, 2026-10-06)

**Status:** draft 4 replaces draft 3 (2026-10-04; in git at `990b1b4`), which was framed as "I assumed… it didn't". The talk is on 2026-10-08: 40 minutes, for data practitioners.
- **Slide plan:** `docs/TALK2-REWORK-SLIDE-PLAN.md` (33 slides in the `tech-slide-planner` format, profile `DATADOG_MARKETING_DECK`; written by hand, not by running the skill).
- **Claude design build prompts:** `docs/TALK2-REWORK-DESIGN-PROMPTS.md`.
- **Slide charts:** `talks/talk2-greenest-token/slides/charts/` (`make_figures.py --slides`).
- **Sources of truth:**
  - the paper (`talks/talk2-greenest-token/paper/main.tex`) for every study number;
  - the result files named per slide for verbatim prompts and outputs;
  - the reports under "Sources" for the opening's external figures.

**Direction (user, 2026-10-06):**
- **The arc.** The talk opens with "what can one developer do?", so it follows a hero's journey:
  1. data centers are the dragon, and developers adopting AI are feeding it;
  2. the question: how do we stop feeding it and still use AI?;
  3. the thesis.
- **The techniques.** The title is the answer. The talk shows the techniques that make it possible, each framed as "The greenest token is…".
- **The use case.** It comes next, as an explorer's journey: how each technique turned up inside the Edge Triage Pipeline, with code and message formats.
  - It reuses Talk 1's slides 6 ("Stream Everything to the Cloud? Too Slow.") and 9 ("Put the Judgment on the Truck") from the current Claude Design deck.
- **The close.** A general "what you can do" guide, the signals slide framed as an observability problem, and five misconceptions condensed from the ten assumptions.
- **Timing:** don't over-optimize. The user averages under 2 minutes a slide.

## Decisions (2026-10-06)

| # | Question | Decision |
|---|---|---|
| 1 | Title | "The Greenest Token" (as programmed), subtitle "is the one that never hits a GPU" (Talk 1's cliffhanger wording). "GPU" means a data center's GPU: the study found a CPU used more energy per decision than a GPU, so slide 32 says so out loud |
| 2 | Opening statistics | From primary reports only (see Sources); five cards on slide 2, three on slide 3 |
| 3 | Thesis | A demand argument, not a study result: fewer tokens sent to cloud AI → less demand → a slower data-center build-out. Analogy: leaving the car at home one day a week |
| 4 | Techniques | The user's five, plus two the study supports: "read only once" (prompt order and the cache) and "the model never thinks" (thinking off) |
| 5 | The naive first approach | The real first attempt (Sept 12, "Flow A"): the model wrote the whole card as free-text JSON. Raw telemetry is "the road not taken": the cheap-math gate was there from day one |
| 6 | Talk 1's slides 6 and 9 | Reused, with the badges reworded so they don't contradict this talk's measurements (user approved): "Sub-second" → "decided on the truck, no round trip"; "Up to 95% noise / 90% bandwidth savings" → "9.2 MB a day of raw telemetry → ~4 KB per incident"; "Network risk" kept |
| 7 | Device slide | Yes (user): Fig. 1, an M1 generates at iPhone 17 Pro speed |
| 8 | Signals slide | Kept, framed as an observability problem (user) |
| 9 | Misconceptions | Five (user approved): small device, repeats, quantization, defaults, chat format |
| 10 | The abstract | No quote slide this time. Its 1-bit claim is answered in slide 32's notes |
| 11 | Design system | `DATADOG_MARKETING_DECK` (not DRUIDS) |
| 12 | Voice | First person |

## Where the record differs from the first framing

The user's sketch of the journey (2026-10-06) differed from the repo's history in these places. The plan follows the record.

1. **The naive raw-telemetry approach never ran.**
   - `docs/CANON.md` (line ~80): neither tier asks the LLM to "notice" an anomaly in raw numbers.
   - No commit contains a prompt like "determine if the truck's ETA will be impacted".
   - The real first attempt asked a small model to write the whole enrichment card, classifying severity and describing the ETA impact as free-text JSON (`eval-results/compare-COMP-J2D9D71YNJ-20260912T202854Z.json`). That failed on every measure.
2. **The gate and the co-processor were the starting design (Talk 1), not fixes.**
   - The gate, a grammar, the "static rules first" intent, temperature 0.2 and the 60 s timeout all date from the first Edge Triage Pipeline commit (`aa96b9e`, 2026-09-25).
   - The fixes found along the way were:
     - the grammar (versus Flow A's free text);
     - placeholders instead of a filled-in example;
     - severity moved into code with a raise/hold/lower task (`18b836f`, `754ab57`);
     - llama-server instead of a process per call;
     - token caps sized to the answer;
     - later, the prompt order.
3. **The co-processor doesn't compute rolling averages or summarize a stream.**
   - The truck's telemetry already carries a 6-reading rolling window (`shared/fleet-simulator/src/fleet_simulator/scenario.py`, `_compute_signals`).
   - The co-processor works one event at a time: it gates it and adds the traffic-pattern label, the deviation from the route plan, the trip context and the baseline severity. Its docstring rejects a rolling window: "TelemetryEvent is a single snapshot".
   - "A model can't reason over a sequence of events" was a design rule, never a tested failure.
4. **Prompt echo was never "turned off".**
   - llama.cpp's command-line tool printed the prompt into every stored output, so the 350M models' "echo" was really an empty answer.
   - The printed prompt went away when the pipeline moved to llama-server. `--no-display-prompt` appears nowhere in the history.
   - What did happen: small models parroted the output template. The 0.5B repeated it until the token cap; the grammar and the narrower task cured that.
5. **Timeouts didn't stop runaway reasoning; token caps did.**
   - The 60 s timeout dates from day one (`triage_function.py`, `DEFAULT_TIMEOUT_SECONDS`).
   - Runaway generation was bounded by caps: 300 tokens for the card, and 1,024 for capped thinking.
   - **Side finding, unverified in the live demo:** the 60 s default is shorter than a changed-prompt call on the Pi 4 (82-160 s). `deploy/run_edge_triage_llm_localrun.sh` doesn't set `timeout_seconds`, so check what Talk 1's Pi demo does on an incident's first call.
6. **Thinking was never on in production.** Production sends raw completion plus a grammar. "Thinking off" is a measured lesson from round 3, not a pipeline fix.
7. **"Traditional ML" for classification:** the classifier is five lines of threshold code (`severity_classifier.py`). Slides say "code (or a classic ML model)".
8. **The grammar doesn't buy speed.**
   - Its measured win is valid structure.
   - Tokens barely changed with the narrower task: Gemma-3-4B wrote 96.5 tokens for one judgment vs 106.5 for the whole job (round 3, `…154259Z` vs `…154409Z`).
9. **Numbers corrected from the superseded revision prompts (`docs/TALK2-DESIGN-REVISION-PROMPTS.md`):**
   - **Prompt cache:** about 400 → 148 of 514 tokens re-read per new event, as measured (paper Table IV, §IV-B; `eval-results/edge-triage-event-last-pi4-20261005/`). "392 → 140 of 506" was a static tokenizer count.
   - **Severity with the thresholds written into the prompt:** 20-63% wrong (`…20260925T185711Z`; Llama-3.1-8B 45 of 89). The 33-73% figure is the 15-model grammar run with qualitative rules (`…20260926T153435Z`).
   - **Grammar before/after:** use the same-machine pair (`…20260925T165011Z` → `…153435Z`): 28/30 → 30/30 (Qwen2.5-1.5B), 16/30 → 30/30 (0.5B), 0/30 → 30/30 (LFM2.5-350M), 0/30 → 25/30 (Granite-4.0-H-350M). The prompt and temperature changed too.
   - **"~23 calls per truck-day"** assumes one incident a day (17-28 calls per incident).
   - **"0 calls in 2.3 truck-days"** comes from synthetic normal driving.
   - **The 128k-context out-of-memory crash** was on a 16 GiB cloud stand-in, not the Pi.

## Arc: 33 slides, ~37 minutes

| Section | Slides | Minutes | Arc |
|---|---|---|---|
| 1. The dragon | 1-5 | 5.5 | Hero's journey: the ordinary world (data centers' footprint), the call (we're feeding it), the question, the thesis |
| 2. The greenest token is… | 6-13 | 5.5 | The seven techniques, one light slide each: the line, the technique, the size of the saving. No code |
| 3. How I found them | 14-29 | 21.5 | Explorer's journey: the cloud path (Talk 1, slide 6), the edge path (Talk 1, slide 9), the device class, the first attempt and how it failed, then eight fixes with code, prompts and outputs |
| 4. What you can do | 30-33 | 4.5 | The general guide, observability, five misconceptions, thank you |

## Evidence map: each technique, where it's shown, and its proof

| "The greenest token is the one…" | Section 2 | Section 3 | Evidence (source) |
|---|---|---|---|
| never sent to the data center | 7 | 21 | 17,280 events per truck-day → ~23 calls per incident; 0 calls in 2.3 simulated truck-days; 9.2 MB a day → ~4 KB per incident (paper; impact track row 28). The Pi answers ~2,700 calls a day at 31.7 s (arithmetic) |
| whose inputs are already calculated | 8 | 22 | The truck computes the rolling average, stop-and-go index and ETA slip. The co-processor adds the baseline and context. Given two raw numbers, small models didn't work out the difference (impact track, "Velocity deviation-from-plan") |
| that doesn't stand in for a better tool | 9 | 23 | With the thresholds in the prompt, severity was wrong on 20-63% of calls (`…185711Z`); with a grammar, still 33-73% (`…153435Z`); code is exact |
| asked a simple, directed question | 10 | 24-25 | Small models 94-100% on one judgment vs 11-22% on the whole job (paper Table VI; round 3) |
| told what shape to take | 11 | 26 | Same machine: 28/30 → 30/30 and 16/30 → 30/30 with a grammar; a filled-in example was copied on 28 of 30 calls (`6ff72a3` comment) |
| read only once | 12 | 27 | ~400 → ~148 of 514 tokens; Pi 4: 772 J and 160 s → 416 J and 82 s per new event (paper Table IV, §IV-B) |
| the model never thinks | 13 | 29 | No measurable accuracy gain at 4-11× the time and 4-7× the energy (paper Fig. 3; round 3) |
| (bound every call) | — | 28 | 150 tokens cut off 8 of 10 cards, 300 fixed it (`754ab57`); a 1,024 thinking cap finished every call; a throttling Pi hit the 300 s timeout on 5 of 15 calls (impact track) |

## Sources (external figures)

Every figure below was read in its primary document (research 2026-10-06), and two were re-checked against the live pages. Page numbers are printed page numbers.

| Key | Source | Used for |
|---|---|---|
| IEA-2026 | IEA, *Key Questions on Energy and AI* (WEO Special Report), April 2026, CC BY 4.0. https://iea.blob.core.windows.net/assets/3179f7f8-01f6-4dd6-bffa-c9f7b73f1dc9/KeyQuestionsonEnergyandAI.pdf | Slide 2: 485 TWh in 2025 → 950 TWh in 2030, ~3% (p. 10); 1.5% in 2025 and 20-30% where clusters are (p. 34); ~350 Mt CO2 by 2035 (p. 13); capex over USD 400 billion in 2025, +75% for 2026 (pp. 9, 18). Slide 3: AI-focused data centres +50% in 2025 (p. 9), ~465 TWh by 2030 (p. 26); agentic tasks "hundreds or thousands of times more energy per query" (p. 9) |
| IEA-2025 | IEA, *Energy and AI*, April 2025. https://iea.blob.core.windows.net/assets/de9dea13-b07d-42c5-a398-d1b3ae17d866/EnergyandAI.pdf | Slide 2: 180 Mt CO2 today (p. 18). Notes: data centres are about a tenth of global demand growth to 2030 (p. 14) |
| LBNL-2025 | Smith, Hubbard, Newkirk, Ganeshalingam, Holecek, Sartor, Mills, Shehabi, *United States Data Center Energy Usage Report: 2025 Update*, LBNL, June 2026, LBNL-2001758, https://doi.org/10.71468/P1RP4F | Slide 2: 192 TWh, 4.7% of US electricity in 2024; 649 TWh, 11.8% in 2030, Reference Case (p. 8); range 9.5-15.3% (p. 9) |
| LBNL-2024 | Shehabi et al., *2024 United States Data Center Energy Usage Report*, LBNL, December 2024, LBNL-2001637 | Slide 2: 66 billion liters on site in 2023 (p. 55); nearly 800 billion liters indirect, through electricity (p. 57). Water isn't revised in the 2025 update |
| Google-2025 | Elsworth et al., "Measuring the environmental impact of delivering AI at Google Scale", arXiv:2508.15734, 21 Aug 2025 | Slide 3: median Gemini Apps text prompt 0.24 Wh (inference and serving only, May 2025) |
| Oviedo-2026 | Oviedo et al. (Microsoft), "Energy use of AI inference, efficiency pathways, and test-time scaling", *Joule* 10(8):102430, 2026, DOI 10.1016/j.joule.2026.102430 | Slide 3: median 0.31 Wh per query; test-time scaling 15× longer → 13× the energy, 3.91 Wh |
| SO-2026 | Stack Overflow 2026 Developer Survey, blog post 6 Oct 2026, https://stackoverflow.blog/2026/10/06/the-results-of-the-2026-developer-survey-are-here | Slide 3: "73% of respondents who indicate using AI coding assistants/agents use them daily"; "a third of daily users using any AI tools use AI four or more hours per day". Self-selected sample; use the blog's wording |

Alternates, if a card needs swapping:
- **Google water:** Google's data centers consumed 10,523 million gallons of water in 2025 (Google *2026 Environmental Report*, p. 96).
- **US electricity:** EPRI projects 9-17% of US electricity by 2030 (*Powering Intelligence 2026*).
- **Prompts:** ChatGPT gets 2.5 billion prompts a day (OpenAI via Axios/TechCrunch, Jul 2025).
- **Per-query energy:** Epoch AI estimates ~0.3 Wh for a typical GPT-4o query (Feb 2025).

What a skeptic will raise, for Q&A:
- These are modeled estimates, not metered totals.
- Data centers are about a tenth of global electricity-demand growth to 2030 (IEA-2025 p. 14), but up to 20-30% of demand where they cluster (IEA-2026 p. 34).
- Google's 0.24 Wh excludes training.
- Indirect water uses the local grid mix and ignores power purchase agreements.
