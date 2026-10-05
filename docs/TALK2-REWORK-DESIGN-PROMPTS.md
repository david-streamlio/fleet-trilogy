# Talk 2: Claude design prompts (rework deck, 2026-10-04)

Paste-ready prompts that turn the slide plan into the deck. The talk is on 2026-10-08.

**What to upload to the Claude design project first:**
1. `docs/TALK2-REWORK-SLIDE-PLAN.md`: the locked content spec (27 slides).
2. The six chart images from `talks/talk2-greenest-token/slides/charts/`:
   - `slide_dice.png` (slide 7)
   - `slide_fig1_speed.png` (slide 8)
   - `slide_fig2_energy.png` (slide 10)
   - `slide_fig3_thinking.png` (slide 11)
   - `slide_fig5_task_scope.png` (slide 12)
   - `slide_fig4_energy_per_day.png` (slide 23)

   SVG versions sit beside them if the tool prefers vector.
3. If you have it, the `DATADOG_MARKETING_DECK` design-system export: the "LH - Datadog Design System" dev kit or the "Datadog Design System Slides" HTML export, the same 2025 template. Without it, Prompt 0's tokens are enough to start.

**Order:** Prompt 0, then 1, 2 and 3 (one batch each), then 4 (QA). Prompt 5 is for later, when the pending data arrives.

**Why these rules exist:**
- **Planning tags reached the slides last time.** The previous Talk 2 build put planning-doc tags and file names on slides (`docs/TALK2-DECK-BUILD-PROMPT.md`). This time pending data must be *visible*, but as a designed chip, never as raw bracket syntax.
- **The design tool defaults to DRUIDS.** It tends to apply the org's default design system, which is DRUIDS, a product-UI system. That's wrong for a deck.

---

## Prompt 0: deck setup and rules (send once, first)

```
You are building the slides for "The Greenest Token" (Talk 2 of a three-talk conference series), a 40-minute talk on 2026-10-08 for data practitioners. The attached TALK2-REWORK-SLIDE-PLAN.md is a locked content spec: build exactly what it says, in order. Don't improve, embellish or summarize it. I'll send the slides in three batches after this message; for now, set up the deck and confirm these rules.

1. Structure. Exactly 27 slides, numbered and titled as in the plan. Each slide uses the native slide type named in its "Suggested Layout" field. Don't add, merge, drop or reorder slides. Plate slides (Title, Section, Quote, Closing) are full-bleed with title-level text only.

2. Content. Use each slide's "On-Screen Text" verbatim. Put its "Speaker Notes" verbatim in the slide's presenter notes. Never add a claim, number, title, tagline or statistic that isn't in the plan, and never change a number. Where the plan gives a chart's data in "Visual Manifest → Spec", that data is authoritative.

3. Placeholders. The plan marks data still being collected as [PLACEHOLDER: label]. Render every one as the same designed "data pending" chip: a rounded pill with an amber (#FF9B00) 1.5px outline, a small "DATA PENDING" eyebrow in Roboto Mono caps, then the label in plain text. The chip must be easy to spot and replace later. Never show the raw bracket text.

4. Other planning tags. [SOURCE: …] and [NEEDS: …] are instructions to you, not audience text. Never render them. Keep the surrounding words and numbers as written (on slide 22, render the footnote's citation, "*Google (2025), median Gemini text prompt including data-center overhead", without the bracket). File paths, file names (.md, .png, .tex) and "Backing:" lines go in presenter notes only, never on a slide.

5. Design system: DATADOG_MARKETING_DECK, the 2025 Datadog presentation template. Do NOT use DRUIDS or any product-UI design system, even if it's this workspace's default. If I've uploaded the marketing-deck design-system export, use its real components and assets. Otherwise use these tokens:
   - canvas 1280×720;
   - violet #5C00EF / #9C43FE with #8000FF accent; #632CA6 for the logo mark only;
   - accents green #00B765, blue #0060FF, cyan #00CAFF, orange #FF5E00, amber #FF9B00, pink #FF0080, mint #57E8B3, magenta #D32D96;
   - Roboto for text (bold titles), Roboto Mono for numerals, labels and code;
   - type scale: display 88, h1 64, h2 48, h3 34, h4 26, lead 22, body 17, small 15, eyebrow 13, caption 12 (px);
   - light content slides (black text on white);
   - full-bleed violet plates with the point-up hexagon-line pattern, or the low-poly backgrounds, for Title/Section/Quote/Closing;
   - cards with hairline borders and soft low shadows; no heavy drop shadows; no eco/green re-theme.

6. Voice. First person ("I assumed…"), as written in the plan. That's the speaker's choice and overrides any template rule preferring "you/we". Sentence case; numbers in Roboto Mono; no emoji; no superlatives.

7. Charts. Slides 7, 8, 10, 11, 12 and 23 use the uploaded chart images. Place each large in the content region with the slide's text beside or below it. Don't redraw a chart unless you can reproduce it exactly from the plan's Spec data in Roboto and the deck palette; never alter, round or extend its values.

8. Names. The system is the "Edge Triage Pipeline" (never "Flow B"). Model names exactly as written (e.g. Qwen3.5-9B, Phi-3.5-mini, Gemma-3-4B).

Reply with a one-paragraph confirmation of the design system you'll use and how a "data pending" chip will look, then wait for batch 1.
```

---

## Prompt 1: slides 1-8 (Opening, Section 1, Section 2)

```
Build slides 1-8 from the attached plan, following the rules from my first message.

- Slide 1 (Title plate): title, subtitle and speaker line only.
- Slide 2 (Stats): two stat blocks. Both numbers are pending, so render each as a "data pending" chip in the stat position, with its label (IEA data-center electricity, 2024; projected 2030). Show the line "They aren't going away. What can I do as a developer?" as the slide's lead sentence.
- Slide 3 (Quote plate): the abstract as one large blockquote, attribution "— my accepted abstract for this talk". This quote returns on slide 25, so make it look like a promise, not a footnote.
- Slide 4 (Content): question headline plus the three lines. The second line contains a "data pending" chip (smartphones in use) inline at the start of the sentence.
- Slide 5 (Three-up): three cards, Accuracy / Speed / Power, each with its one-line question; the caption line beneath in small type.
- Slide 6 (Metric / Code + KPI): the JSON telemetry event as a syntax-highlighted code block on the left, exactly as written (11 lines). On the right the KPI "raise · hold · lower" in large Roboto Mono, labeled "the one thing the LLM decides", and the sub-line "532 B every 5 s in → only high-severity cards cross the cellular link".
- Slide 7 (Content): the uploaded slide_dice.png as the main visual, with the three short lines (Accuracy / Speed / Power) beside it.
- Slide 8 (Content): slide_fig1_speed.png large, with the three lines as a narrow side column. Emphasize "M1 ≈ iPhone 17 Pro (within 9%)".

When done, list any slide where you made a judgment call rather than a literal transcription.
```

## Prompt 2: slides 9-18 (Section 3: "I assumed… it didn't")

```
Build slides 9-18 from the attached plan, following the same rules.

Slide 9 is a Section plate ("I assumed… it didn't" / "Nine assumptions, and what the data said").

Slides 10-18 are a series of nine assumptions, so they must look like one family:
- An eyebrow on every slide, "ASSUMPTION 1 OF 9" through "ASSUMPTION 9 OF 9" (Roboto Mono caps).
- The headline is the slide title from the plan: "I assumed … . It didn't." The verdict half may be visually emphasized.
- A "Do this:" line in the same position on every slide (bottom band or footer), styled as a takeaway (e.g. a mint or green left rule with bold "Do this:"). Use the plan's footer/third line text for it.
- Vary the accent color per slide (cycle violet, blue, pink, orange, cyan, green, magenta) so the run of similar layouts stays lively.

The slides:
- Slides 10-12 (Content, chart slides):
  - 10: slide_fig2_energy.png;
  - 11: slide_fig3_thinking.png (it includes the capped-thinking diamonds), with the plan's small line under the chart;
  - 12: slide_fig5_task_scope.png.

  Put the chart large, with the first two on-screen lines beside it and the "Do this:" line in its usual place.
- Slides 13-18 (Comparison): left column = what I assumed (the plan's "Before column"), right column = what happened (the plan's "After column"), highlighted as the winning side, with the "Do this:" line in its usual place. Slide 13 also has two small lines under the right column, both from the plan: "Lookup tables + the chat template lifted 3 of 4 small models by 36-42 points" and "On the M1, worked examples nearly doubled the prompt but cost no more energy: answers got shorter".

When done, list any judgment calls.
```

## Prompt 3: slides 19-27 (Sections 4 and 5, closing)

```
Build slides 19-27 from the attached plan, following the same rules.

- Slides 19-20 (Comparison): "Do" column vs "Don't" column, three items each. Make these the most photographable slides in the deck: generous type, green check marks on Do, orange crosses on Don't, nothing else on the slide.
- Slide 21 (Section plate): "Does the thesis hold?" with the thesis as subtitle.
- Slide 22 (Three-up): three cards with the plan's card titles and lines. Footnote (small, grey #787878, leading "*"): "*Google (2025), median Gemini text prompt including data-center overhead".
- Slide 23 (Content): slide_fig4_energy_per_day.png large, three lines beside it. Make "Energy = calls × joules per call" the visual anchor of the text column.
- Slide 24 (Content): a clean 6-row, 3-column table (Signal | Failure it caught | Effect) exactly as in the plan; numbers in Roboto Mono. A small "data pending" chip in a corner slot labeled "Datadog dashboard screenshot".
- Slide 25 (Comparison): left = "What I promised" (the abstract's three claims), right = "What I measured" (three findings). Each finding gets a verdict badge: "Untested" (grey), "Smaller in practice" (amber), "Confirmed" (green). Visually echo slide 3's quote styling on the left column, so the callback is obvious.
- Slide 26 (Content): the three lines, then the closing line large and bold across the bottom: "The energy savings came from not calling the model, not from making each call cheaper." This is the line the talk ends on, so give it the most visual weight in the deck.
- Slide 27 (Closing plate): "Thank you", the subtitle line with the paper link as a "data pending" chip, and the speaker line.

When done, list any judgment calls.
```

## Prompt 4: QA pass (after all three batches)

```
Do a final check of the whole deck against the attached plan and report the results as a list:
1. Count: exactly 27 slides, in the plan's order, each with its named native type. No two full-bleed plate slides adjacent.
2. Text-only scan of every slide's visible content (not presenter notes). None of these may appear: "[", "]", "PLACEHOLDER:", "SOURCE", "NEEDS", "TODO", ".md", ".png", ".tex", "Backing:", "Flow B".
3. "Data pending" chips: exactly these, all in the same style:
   - slide 2 (two chips)
   - slide 4
   - slide 24
   - slide 27
4. Numbers: spot-check every number on slides 6, 8, 10-18, 22-25 against the plan; list any mismatch.
5. Voice: first person preserved; sentence case; no emoji.
6. Presenter notes: present on every slide, matching the plan's Speaker Notes.
Fix anything that fails, then summarize what you changed.
```

## Prompt 5: fill in pending data (later, when the runs are in)

Send one message per update, filled in from the results (Claude Code will prepare the exact values):

```
Replace the "data pending" chip on slide <N> with: <final text or number>. Keep the slide's layout; don't change anything else. If the new text is longer than the chip, reflow only that line.
```

| Slide | Pending item | Expected | Source when ready |
|---|---|---|---|
| 2 | IEA data-center electricity (2024; 2030 projection) | before the talk | IEA "Energy and AI" (2025): confirm the figures |
| 4 | smartphones in use worldwide | before the talk | a citable figure (e.g. an industry survey) |
| ~~11~~ | capped thinking: **filled in** 2026-10-05 (the slide plan's line and notes; Fig. 3 regenerated with the capped points) | done | — |
| ~~13~~ | worked-examples energy on the M1: **filled in** 2026-10-05 | done | — |
| 24 | Datadog dashboard screenshot | after the slides | `talks/talk2-greenest-token/TODO-DATADOG-DASHBOARD-DEMO.md` |
| 27 | paper link | when available | — |
