# Talk 2 — Claude Design Build Prompt

Paste the block below into Claude design together with `docs/TALK2-SLIDE-PLAN.md`
(or a link/upload of it) when generating or regenerating the deck. It exists
because the first generation pass shipped literal planning-doc artifacts onto
rendered slides — `NEEDS: measurement` tags, `[Insert Repo URL Pointer]`,
internal `.md` filenames — plus a few invented claims and a dropped section
divider. Sections 1–5 below are general and reusable for Talk 1/Talk 3
regenerations too; section 6 is specific to this plan version
(2026-09-30 trim pass).

---

## The prompt

```
You are building presentation slides from docs/TALK2-SLIDE-PLAN.md for "The
Greenest Token" (Talk 2 of the fleet-trilogy conference series). Follow the
plan exactly — do not improve, embellish, or summarize it. Treat it as a
locked content spec, not a starting point for your own creative rewrite.

## Non-negotiable rules

1. Never render planning-doc TODO syntax as slide content. The plan marks
   unresolved items with `[NEEDS: source]`, `[NEEDS: measurement]`, or
   placeholder brackets like `[Insert Repo URL Pointer]`. These are
   instructions to YOU, not text for the audience. For any such tag:
   - If the surrounding sentence still makes sense without it, drop the tag
     and keep the honest hedge language already in the sentence (e.g. "its
     own estimate" stays, the tag does not).
   - If the tag marks something that can't be omitted (e.g. a missing repo
     URL on the closing slide), do NOT render the bracket placeholder. Stop
     and ask for the real value, or substitute a presentable non-placeholder
     phrase (e.g. "available on request") and flag that substitution back.
   - Never let "NEEDS: ..." or "[Insert ...]" appear as literal visible text
     on a rendered slide, under any circumstance.

2. Internal doc/file references stay in speaker notes only. The plan cites
   its own source docs constantly ("Backing: docs/...", "See
   TALK2-GPU-BENCHMARK-PLAN.md"). These exist for fact-checking, not for the
   audience. Never put a filename, a `.md` reference, or a "Backing:"
   citation in on-screen slide text. If a slide's "On-screen text" block in
   the plan contains one, move it to that slide's speaker notes and rewrite
   the on-screen line in plain audience-facing language.

3. Do not add any claim, number, title, or tagline that isn't already in the
   plan. The plan's title slide has no subtitle — don't invent one. Never
   introduce energy/power/wattage-efficiency claims of any kind: this
   project has explicitly not measured power consumption anywhere (see the
   plan's Slide 6/23 notes and its Open Items), so "efficient" framing
   beyond what the plan itself states is a factual overclaim, not a
   stylistic choice.

4. Match the plan's slide count and structure exactly. The plan's
   "## Structure" section lists 5 acts (Act 0 through Act 4), each with its
   own section-divider slide, totaling 26 slides. Build exactly that many
   section dividers, in that order, with none dropped, merged, or silently
   skipped. Don't add slides beyond what the plan specifies (including a
   closing/thank-you slide) without flagging the addition in your output
   summary.

5. Lock the visual design to Talk 1's existing, already-built system — DRUIDS
   tokens (Noto Sans, 4px/8px radii, `--ui-status-*` color tokens) plus
   `DATADOG_MARKETING_DECK` native slide types, matching
   `talks/talk1-edge-intelligence/slides/source/Talk 1 Edge Intelligence.dc.html`:
   white content-slide backgrounds, Lucide icon-badge status coding
   (danger/warning/success), purple-to-blue faceted gradient reserved ONLY
   for Title/Section/Closing/Waitroom slides. Don't introduce a different
   visual theme — including any eco/green-tinted palette — even though this
   talk's content is sustainability-framed. The framing lives in the words,
   not the color system.

## Known content issues to fix during this build

- "Accuracy delta" table (plan's Slide 21, "Hardware Changes Speed, Not
  Accuracy"): the sign convention is backwards. A model whose mismatch rate
  improved on Pi 4 vs. M4 currently shows a NEGATIVE "accuracy delta," which
  reads as a regression. Recompute each delta as (M4 mismatch % − Pi
  mismatch %) so positive always means "got more accurate," and relabel the
  column if that helps clarity.
- M4 gate result slide (plan's Slide 19, "Layer 5"): don't blend "<=6.7%
  escalation mismatch" and "the 50% bar" into one claim — they're two
  different thresholds. Give them two clearly separated lines.
- Cut any "85-96% less energy" stat if it shows up from a prior draft — it
  is not in the current plan and isn't sourced anywhere in this project.
  Act 1's slide should state the theoretical appeal of 1-bit LLMs in words
  only, with no fabricated percentage.
- Closing slide repo link: don't ship `[Insert Repo URL Pointer]` as visible
  text. Ask for the real URL before finalizing, or use a non-placeholder
  phrase in the interim.

## After generating

Do a final text-only pass over every slide's on-screen content (not speaker
notes) and verify none of these appear anywhere: "NEEDS:", "[Insert", "TODO",
any `.md` filename, any bracket `[...]` placeholder. Report back any slide
where you had to make a judgment call rather than a literal transcription
from the plan.
```
