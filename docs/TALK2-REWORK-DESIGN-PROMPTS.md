# Talk 2: Claude design build prompts (draft 4 deck, 2026-10-06)

Paste-ready prompts that build the deck from the draft 4 slide plan: the hero's-journey arc with seven "The greenest token is…" techniques and the explorer's journey. The talk is on 2026-10-08.

This replaces the 2026-10-04 prompts for the 28-slide plan (in git at `990b1b4`) and supersedes `docs/TALK2-DESIGN-REVISION-PROMPTS.md`. Build a **new** deck rather than revising the old one: two thirds of the slides changed.

**Upload to the Claude design project first:**
1. `docs/TALK2-REWORK-SLIDE-PLAN.md`: the locked content spec (33 slides).
2. Three chart images from `talks/talk2-greenest-token/slides/charts/` (SVGs sit beside them):
   - `slide_fig1_speed.png` (slide 17);
   - `slide_changed_prompt.png` (slide 27, small inset);
   - `slide_fig3_thinking.png` (slide 29).
3. Talk 1's slides 6 and 9, if the tool can't copy them from the "Talk 1: Edge Intelligence" project: screenshots or the project URL.
4. The `DATADOG_MARKETING_DECK` design-system export, if you have it. Without it, Prompt 0's tokens are enough.

**Order:** Prompt 0, then 1, 2 and 3 (one batch each), then 4 (QA). Prompt 5 is for later, when the image, the dashboard and the paper link exist.

**Why these rules exist:**
- **Planning tags have reached the slides before.** That was the first Talk 2 build (`docs/TALK2-DECK-BUILD-PROMPT.md`).
- **The design tool defaults to DRUIDS,** a product-UI system that's wrong for a deck.
- **This deck shows real model prompts and outputs, mistakes included.** The tool must not tidy them.

---

## Prompt 0: deck setup and rules (send once, first)

```
You are building the slides for "The Greenest Token" (Talk 2 of a three-talk conference series), a 40-minute talk on 2026-10-08 for data practitioners. The attached TALK2-REWORK-SLIDE-PLAN.md is a locked content spec: build exactly what it says, in order. Don't improve, embellish or summarize it. I'll send the slides in three batches after this message; for now, set up the deck and confirm these rules.

1. Structure. Exactly 33 slides, numbered and titled as in the plan. Each slide uses the native slide type named in its "Suggested Layout" field. Don't add, merge, drop or reorder slides. Plate slides (Title, Section, Statement, Closing) are full-bleed with title-level text only.

2. Content. Use each slide's "On-Screen Text" verbatim. Put its "Speaker Notes" verbatim in the slide's presenter notes. Never add a claim, number, title, tagline or statistic that isn't in the plan, and never change a number.

3. Verbatim code panels. When the plan gives a model prompt, a model output, JSON or code in a fenced block, show it as a code panel (Roboto Mono, small, syntax-highlighted) exactly as written. You may shorten it only where the plan already has "…". Never paraphrase, reformat or fix a model's output, including its mistakes, single quotes, cut-off endings and odd wording. That's the point of those slides.

4. Highlights, not rewrites. Where the plan asks for a highlight and callout, put a colored highlight or outline on the existing text plus the short callout label the plan gives. Don't change the text under it.

5. Pending items:
   - [PLACEHOLDER: label] renders as a designed "pending" chip: a rounded pill with an amber (#FF9B00) 1.5px outline, a small "PENDING" eyebrow in Roboto Mono caps, then the label in plain text.
   - [IMAGE: description] renders as an image panel with a dashed amber outline, an "IMAGE PENDING" eyebrow and the description as a small caption, sized where the final image will go.
   - Never show raw bracket text.

6. Other planning tags. [NEEDS: …] is an instruction to you, not audience text: never render it. File paths, file names (.md, .png, .json, .tex), commit hashes and "Backing:" lines go in presenter notes only, never on a slide.

7. Design system: DATADOG_MARKETING_DECK, the 2025 Datadog presentation template. Do NOT use DRUIDS or any product-UI design system, even if it's this workspace's default. If I've uploaded the marketing-deck design-system export, use its real components and assets. Otherwise use these tokens:
   - canvas 1280×720;
   - violet #5C00EF / #9C43FE with #8000FF accent; #632CA6 for the logo mark only;
   - accents green #00B765, blue #0060FF, cyan #00CAFF, orange #FF5E00, amber #FF9B00, pink #FF0080, mint #57E8B3, magenta #D32D96;
   - Roboto for text (bold titles), Roboto Mono for numerals, labels and code;
   - type scale: display 88, h1 64, h2 48, h3 34, h4 26, lead 22, body 17, small 15, eyebrow 13, caption 12 (px);
   - light content slides (black text on white);
   - full-bleed violet plates with the point-up hexagon-line pattern, or the low-poly backgrounds, for Title/Section/Statement/Closing;
   - cards with hairline borders and soft low shadows; no heavy drop shadows; no eco/green re-theme.

8. Recurring families:
   - Slides 7-13 ("The greenest token is…") are one family. Use the same eyebrow "THE GREENEST TOKEN IS…" in Roboto Mono caps, the title completing the sentence, the technique line, then one or two big numbers in Roboto Mono, all in the same positions on every slide. Cycle the accent color per slide.
   - Slides 21-29 (the fixes) carry their technique's line as an eyebrow (e.g. "…NEVER SENT TO THE DATA CENTER") in the same style, so the audience can match each fix to its technique.

9. Voice. First person, as written. Sentence case; numbers in Roboto Mono; no emoji; no superlatives.

10. Charts. Slides 17, 27 and 29 use the uploaded chart images. Don't redraw, alter, round or extend them.

11. Names. The system is the "Edge Triage Pipeline" (never "Flow B"). Model names exactly as written (e.g. Qwen2.5-1.5B, Qwen3.5-9B, Phi-3.5-mini, Gemma-3-4B, Llama-3.1-8B).

Reply with a one-paragraph confirmation of the design system you'll use and how a "pending" chip and an "image pending" panel will look, then wait for batch 1.
```

---

## Prompt 1: slides 1-13 (the dragon; the greenest token is…)

```
Build slides 1-13 from the attached plan, following the rules from my first message.

- Slide 1 (Title plate): title "The Greenest Token", subtitle "is the one that never hits a GPU", speaker line.
- Slide 2 (Stats, with an image): the [IMAGE] panel large (left half, or full-bleed behind a translucent card row), and the five stat cards exactly as in the plan. Each card shows its big number in Roboto Mono, the one-line label, and the source line in caption type. Make the cards readable from the back of a room: number first, label second, source last.
- Slide 3 (Three-up): three stat cards in the same style as slide 2. The title is "AI is the growth engine, and we're feeding it".
- Slide 4 (Statement plate): the question alone.
- Slide 5 (Content): the four-node chain drawn natively, left to right with arrows, then the analogy line below it in lead type.
- Slide 6 (Section plate): "The greenest token is…" / "Seven ways to stop feeding the dragon".
- Slides 7-13: the "greenest token" family (rule 8). Slide 8's three-box flow is drawn natively, in the family style, in place of the big number.

When done, list any slide where you made a judgment call rather than a literal transcription.
```

## Prompt 2: slides 14-29 (how I found them)

```
Build slides 14-29 from the attached plan, following the same rules.

- Slide 14 (Section plate): "How I found them" / "One truck, one small model, a lot of wrong turns".
- Slides 15 and 16 are reused from the "Talk 1: Edge Intelligence" deck (its slides 6 and 9). Copy them if you can, otherwise rebuild them from the uploaded screenshots, keeping their layout and art. Then apply exactly these wording changes, and nothing else:
  - Slide 15 ("Stream Everything to the Cloud? Too Slow."):
    - the Data Lakes tag "Up to 95% Noise Data" becomes "every raw reading";
    - the Data efficiency badge's BEFORE becomes "every reading: 9.2 MB per truck-day".
  - Slide 16 ("Put the Judgment on the Truck"):
    - "Sub-second Local Action" becomes "Local action, no round trip";
    - "Filtered Anomalies Only (Up to 90% Bandwidth Savings)" becomes "Filtered anomalies only (~4 KB per incident instead of 9.2 MB a day)";
    - Decision latency AFTER becomes "decided on the truck, no round trip";
    - Data efficiency BEFORE becomes "every reading: 9.2 MB per truck-day", AFTER becomes "~4 KB per incident".
  - On both slides the Network risk badge stays as it is.
- Slide 17 (Content): slide_fig1_speed.png large, the three lines as a narrow side column; emphasize "M1 ≈ iPhone 17 Pro (within 9%)".
- Slide 18 (Metric / Code + KPI): the prompt as a code panel exactly as written (keep the single-quoted list: it matters two slides later), and the KPI "6 fields, 1 call".
- Slide 19 (Stats): four stat blocks, each with a small measure chip, SPEED (cyan #00CAFF) or ACCURACY (blue #0060FF), as the plan tags them.
- Slide 20 (Content): three code panels side by side or stacked, each with its header, verbatim, with the callouts on the exact text the plan names. Panel 1 ends mid-word ("truck-"): keep it that way.
- Slides 21-29: the fix family (rule 8):
  - 21: three stat blocks.
  - 22: Code + KPI, the payload JSON with two highlight colors and their callouts.
  - 23-26: Comparison, two columns, verbatim panels, highlights and badges as the plan says. On 24 the three highlights share one color, with the callout "work moved from code into the model".
  - 27: two stacked-block prompt diagrams drawn natively, with dashed "cache ends at the first line that changes" lines and orange shading below them; slide_changed_prompt.png only as a small optional inset.
  - 28: Three-up.
  - 29: slide_fig3_thinking.png large, the two mini-cards beside it, the summary line under them.

When done, list any judgment calls.
```

## Prompt 3: slides 30-33 (what you can do)

```
Build slides 30-33 from the attached plan, following the same rules.

- Slide 30 (Content): the eight items as a checklist in two columns of four, generous type, a green check per item, nothing else on the slide. This is the slide people will photograph.
- Slide 31 (Content): the lead line "Latency looked fine. These didn't." large, then a clean 7-row, 3-column table (Signal | Failure it caught | Effect) exactly as in the plan; numbers in Roboto Mono. A small "pending" chip in a corner slot, labeled "Datadog dashboard screenshot of these signals".
- Slide 32 (Content): five rows. Each starts with the assumption in quotes (bold), then what happened (regular). Give row 1 slightly more weight.
- Slide 33 (Closing plate): "Thank you", the subtitle line with the paper link as a "pending" chip, and the speaker line.

When done, list any judgment calls.
```

## Prompt 4: QA pass (after all three batches)

```
Do a final check of the whole deck against the attached plan and report the results as a list:
1. Count: exactly 33 slides, in the plan's order, each with its named native type. No two full-bleed plate slides adjacent.
2. Text-only scan of every slide's visible content (not presenter notes). None of these may appear: "PLACEHOLDER:", "IMAGE:", "NEEDS", "TODO", "Backing:", ".md", ".png", ".json", ".tex", "Flow B", a commit hash.
3. Pending items, all in the same styles: an image panel on slide 2; chips on slides 31 and 33.
4. Verbatim check: every code panel on slides 18, 20, 22-26 matches the plan character for character, apart from cuts the plan marks with "…". Model mistakes, single quotes and the cut-off "truck-" are preserved.
5. Talk 1 slides 15 and 16: the wording changes are applied and nothing else changed. Neither slide says "sub-second", "95%" or "90%".
6. Numbers: spot-check every number on slides 2, 3, 7-13, 17, 19, 21, 23, 25-29 and 31-32 against the plan; list any mismatch.
7. Families: slides 7-13 share one layout; slides 21-29 each carry their eyebrow.
8. Presenter notes: present on every slide, matching the plan's Speaker Notes.
Fix anything that fails, then summarize what you changed.
```

## Prompt 5: fill in pending items (later)

Send one message per item:

```
Replace the pending <chip | image panel> on slide <N> with: <final text, or the attached image>. Keep the slide's layout; don't change anything else.
```

| Slide | Pending item | Notes |
|---|---|---|
| 2 | AI-generated image | The plan's [IMAGE] description is the brief: the data center as a dragon's lair, the dragon asleep around the building, muted violet palette, no text in the image |
| 31 | Datadog dashboard screenshot | `talks/talk2-greenest-token/TODO-DATADOG-DASHBOARD-DEMO.md` |
| 33 | paper link | when available |
