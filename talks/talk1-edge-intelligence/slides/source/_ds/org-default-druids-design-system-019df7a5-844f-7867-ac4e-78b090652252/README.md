# DRUIDS Design System

A guidelines-first design system for **Datadog**. This is not a component library — it's a small set of rules and tokens that, when followed, make any HTML mockup read as Datadog, even when components are recreated from scratch.

## Start here

Open **`guidelines/index.html`** in your browser. It's a multi-page site with sidebar navigation:

- **Overview** — the five non-negotiables
- **Screenshot test** — proof that the rules produce a Datadog-shaped screen
- **Foundations** — Color · Typography · Spacing & density · Border, radius & shadow
- **Patterns** — Tables · Status & state · Iconography · Empty / loading / error
- **Recipes** — Logs row, Monitor card, Host detail panel (copy-paste ready)
- **Anti-patterns** — generic-AI defaults that break the look

## Files

| File | What it is |
|---|---|
| `tokens.css` | All design tokens (colors, type, spacing, radii, shadows) — the single source of truth |
| `site.css` | Site chrome + helper classes (`.dd-btn`, `.dd-pill`, `.dd-table`, `.dd-tag`, `.dd-input`) used in recipes |
| `colors_and_type.css` | Lighter shim around `tokens.css` for projects that only need colors + type |
| `fonts/` | Noto Sans webfonts (300/400/600/700, italics) |
| `assets/` | Datadog wordmark, mark, knockout |
| `guidelines/` | The doc site |

## How to use this in a new project

```html
<link rel="stylesheet" href="path/to/tokens.css">
<style>
  body { font-family: var(--font-family-base); font-size: var(--font-size-md); color: var(--ui-text); }
</style>
```

Then read **Color → Typography → Spacing** before writing any markup. Most "doesn't look like Datadog" failures come from a mis-set body size (it's 13px), oversized controls (28px default), or wrong radii (4px on controls, 8px on cards).

## The five non-negotiables

1. **Body text is 13px.** Not 14, not 16.
2. **Default control height is 28px.** Buttons, inputs, selects.
3. **Border radius is 4px.** Cards step up to 8px. Nothing is "pill-shaped".
4. **Status uses pills and dots, not emoji.** 🟢 / 🚨 are wrong.
5. **One font: Noto Sans.** Roboto Mono for code only.

## Source of truth

Component implementations live in **DataDog/web-ui** at `packages/druids/ui`. This system reproduces the *rules*; for canonical component code, defer to that package.
