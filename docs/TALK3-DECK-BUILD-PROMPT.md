# Talk 3 — Claude Design Build Prompt

Paste the block below into Claude design to generate the first draft of the
Talk 3 deck. Attach with it:

1. `docs/TALK3-SLIDE-PLAN.md` — the locked content spec (required).
2. `docs/TALK3-OUTLINE.md` — narrative context only (recommended).
3. `talks/talk1-edge-intelligence/slides/source/Talk 1 Edge Intelligence.dc.html`
   — the visual system to match (recommended; its `_ds/` and `assets/`
   folders sit beside it).

The general rules (1–5) carry over from `docs/TALK2-DECK-BUILD-PROMPT.md`,
which exists because Talk 2's first pass put planning-doc artifacts on
rendered slides. The Talk 3 section reflects the plan as of 2026-10-05
(28 slides, Pi run folded into slide 22).

---

## The prompt

```
You are building presentation slides from TALK3-SLIDE-PLAN.md for "When Your
Pulsar Function Speaks English: Inline LLM Inference for Real-Time Stream
Enrichment" (Talk 3 of the fleet-trilogy conference series, 40-minute slot).
Follow the plan exactly. Do not improve, embellish, or summarize it. Treat it
as a locked content spec, not a starting point for your own rewrite.
TALK3-OUTLINE.md is attached for narrative context only. Where the two
disagree, the slide plan wins.

## Non-negotiable rules

1. Never render planning-doc TODO syntax as slide content. The plan marks
   unresolved items with `[NEEDS: ...]` tags. These are instructions to YOU,
   not text for the audience. If the sentence still works without the tag,
   drop the tag. If it marks something that can't be left out, render a
   presentable non-placeholder version (see the Talk 3 section below) and
   flag it in your summary. "NEEDS:", "[Insert", "TODO", and bracketed
   placeholders must never appear as visible text on a slide.

2. Internal file references belong in speaker notes only. The plan cites repo
   files constantly ("Backing: eval-results/...", `function.py`,
   `deploy/talk3-windows/tier2.sh`). Never put a file path, `.md` filename,
   or "Backing:" citation in on-screen text. Copy each slide's speaker notes
   into the slide's speaker notes, including the Backing lines.

3. Do not add any claim, number, title, subtitle, or tagline that isn't in
   the plan. Every number on screen must appear in that slide's "On-screen
   text" or "Visual Manifest" exactly as written (12.0 s, 0.7 s, 3.99,
   5.3 GB, 6 min 17 s, 1 min 54 s, 201–241, 720, 15.5 s → 12.0 s, and so
   on). Don't round, convert, or recompute. Add no energy, power, wattage,
   cost, or "green" claims of any kind. Say "small model", never "tiny".
   Use "Edge Triage Pipeline", never "Flow B".

4. Match the plan's slide count and structure exactly: 28 slides, numbered
   as in the plan. Section-divider plates are slides 4, 8, 14, and 20. Acts
   5, 6, and the Close have no divider, so don't add one. Plate slides
   (Title, Section, Closing) are 2, 4, 8, 14, 20, and 28, and they carry
   text only. Slide 3 (cold open) and slide 27 (trilogy closer) are content
   slides on purpose, because a plate follows or precedes them. Don't
   promote them to plates. Add no slides (no agenda, no "about me", no extra
   Q&A slide) without flagging it.

5. Lock the visual design to Talk 1's existing system (attached
   "Talk 1 Edge Intelligence.dc.html"): style profile DATADOG_MARKETING_DECK,
   DRUIDS tokens (Noto Sans, 4px/8px radii, `--ui-status-*` colors), white
   content-slide backgrounds, Lucide icon badges for status coding
   (danger/warning/success), and the purple-to-blue faceted gradient ONLY
   on Waitroom, Title, Section, and Closing slides. Use the plan's
   "Suggested Layout" for each slide: `Metric` ("Code + KPI") for slides 11
   and 12, `Timeline` for the sequence slides, `Comparison` and `Stats`
   where named. Don't introduce a new theme.

## Talk 3 specifics

- Code is verbatim. Slides 11, 12, 15, 16 and the other Code_Block slides
  show the code exactly as in the plan: same lines, comments, spacing, and
  names. Don't reformat, shorten, or "fix" it. Slide 11's KPI is "12 lines"
  and must match the code shown. Use monospace with Python syntax
  highlighting.
- Diagrams are native. Draw `Mermaid_Architecture` and `Mermaid_Sequence`
  manifests as clean diagrams in the deck's style, with labels and edge
  counts taken from the Spec. Never show Mermaid source text. On slide 5,
  highlight the `enrichment-cards` edge as specified. On slide 23, draw the
  dashed "this repo" boundary around the consumer only.
- Slide 21 is a table, not a chart. Four rows as given, with the
  "1 CPU thread" row highlighted. Piper is the footer line.
- Slide 22 is three stat tiles with the small footer "first attempt on the
  laptop: 29 s".
- Media files aren't attached; they live only on the speaker's laptop.
  Where the plan calls for audio or video, place an empty, clearly framed
  media slot that I'll fill later. Give it a small neutral caption (e.g.
  "Audio: I-95N warning", "Audio: raw", "Audio: normalized",
  "Video: recorded demo") and no bracket or NEEDS text:
    - Slide 3: one centered audio slot. The line "That was a Pulsar
      Function talking." appears as a build step after it.
    - Slide 24: two audio slots per column (Raw / Normalized), one for the
      I-95N row and one for the ETA row.
    - Slide 25: the plan asks for a visual type that doesn't exist yet.
      Build a content slide with the on-screen line and one large video
      slot as the fallback frame. Don't draw terminal or htop mockups.
      The live screen share replaces this slide on stage.
- Slide 27's footer link is github.com/david-streamlio/fleet-trilogy (as
  plain text, no "https://").
- Slide 2's subtitle IS in the plan ("Inline LLM Inference for Real-Time
  Stream Enrichment"), so keep it. Slide 1 (Waitroom) and 28 (Thank you)
  carry only the text the plan gives.

## After generating

Do a text-only pass over every slide's on-screen content (not the speaker
notes) and confirm none of these appear: "NEEDS:", "[Insert", "TODO", any
file path or `.md` filename, any bracketed placeholder, "Flow B", "tiny".
Confirm the deck has 28 slides with plates exactly at 2, 4, 8, 14, 20, 28.
Then report every slide where you made a judgment call instead of a literal
transcription, plus the list of empty media slots.
```
