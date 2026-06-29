# hyperexponential — Brand Design System

> An internal design system for **hyperexponential (hx)**, the pricing and underwriting platform for commercial P&C insurance. Source-of-truth for logos, color, type, voice, components, and slide layouts.

## Source of truth

This system was distilled from two canonical sources:

1. **`Brand Design System v0.1 (2026)`** Figma file — logo, colour, typography, iconography, brand-book.
2. **`hx_template-2026.potx`** PowerPoint template — official theme XML, slide masters, layouts.

Where they disagreed, **the .potx wins** — it ships the executable values that PowerPoint and downstream PMM teams actually use. All colour tokens here are the exact RGBs from the template's `theme1.xml`.

For voice, glossary, and PMM-approved language, **`PRODUCT_MARKETING_CONTEXT.md` is canon**. This README mirrors it; if the two ever drift, that file wins.

---

## What is hyperexponential?

**hx is the pricing and underwriting platform for commercial P&C insurance.**

hx connects submission intake, triage, pricing decisions, and portfolio feedback loops in a governed, integrated system. It helps insurers turn messy submission inputs into usable data, encode pricing and underwriting logic in a controlled way, support faster and more consistent decisions, and monitor outcomes with portfolio-level visibility.

**Product type.** SaaS, composable, API-first platform.

**Product category.** Pricing and underwriting platform (preferred). Also acceptable: underwriting decision platform. Do **not** use *pricing platform*, *rating engine*, or *underwriting workbench* as category descriptors — they are too narrow.

> ⚠️ **"hx Renew" is deprecated. Never use it.** The product is **hx**, the company is **hyperexponential** (always lowercase), the legal entity is Hyperexponential Ltd.

### Proof points

- $60B+ in GWP supported annually
- 100% customer retention
- Up to 50% reduction in quote-to-bind time

### Glossary (use these terms exactly)

| Term | Meaning |
|---|---|
| hyperexponential / hx | Always lowercase. Legal entity: Hyperexponential Ltd. |
| Submission Triage | Intake and triage workflows |
| Pricing & Rating | "hx's Pricing & Rating solution" |
| Decision Engine | Governed environment for pricing and decision logic |
| Portfolio Intelligence | Portfolio visibility and analysis |
| Data Ingestion Agent / Actuarial Agent / Underwriter Agent | AI agents. Do not prefix with "hx". |
| GWP | Gross Written Premium |
| E&S | Excess & Surplus lines |
| MGA | Managing General Agent |
| PAS | Policy Administration System |

---

## Brand voice

**Tone.** Active, bold, inspiring. Active voice, short sentences, no more than two commas per sentence.

**Style.** Clarity over cleverness. Plain language over marketing fog. Concrete verbs and nouns. Earn claims with evidence.

**Hard rules.**
- American English spelling (color, organization, modeling).
- **Bold (not italics)** for emphasis.
- Oxford comma.
- Double quotation marks.
- Sentence case for titles, buttons, navigation, table headers.
- **No em dashes.** Use periods or commas.
- **No emoji**, ever.
- No hype adjectives, no AI buzzwords, no meta commentary.

### Words to use

underwriting challenges, underwriting decisions, decision-making challenges; book profitability, risk selection, submission handling, portfolio performance; pricing and underwriting platform; **respond faster**, **win more of the right risks**, **write a more profitable book**; governed, auditable, transparent; composable, modular, phased rollout.

### Words to avoid

pricing challenges, rating challenges, pricing bottlenecks (as sole framing); next-gen, cutting-edge, revolutionary, best-in-class; striking, remarkable, significant, compelling, powerful; underwriting workbench, rating engine, pricing platform (as category descriptors); **hx Renew**.

### Headline patterns

Short, active, benefit-led. Sentence case. Use PMM-approved value language verbatim where possible:

- *"Win more of the right risks"*
- *"Respond faster, win more"*
- *"Write a more profitable book"*
- *"One platform, end to end"*
- *"Governed, auditable, transparent"*

### Person

"We" for hx, "you" for the customer. The customer is always the protagonist.

### Numbers

Numbers are content. They get their own type treatment (Arial Light at display sizes, mono at small sizes). Always pair with a unit or a noun (*"$60B+ GWP"*, *"50% reduction in quote-to-bind"*).

### Tone in product UI

Imperative and short. *"Run model"*, *"Compare versions"*, *"Add factor"*. Error states explain what happened, then what to do — never *"Oops!"*.

---

## Index

Root files:
- **`README.md`** — this file
- **`SKILL.md`** — agent-skill manifest
- **`PRODUCT_MARKETING_CONTEXT.md`** — canonical PMM brief (voice, glossary, proof points)
- **`2026-design-system-v2.md`** — long-form token spec extracted from Figma 2026-04-22

Folders:
- **`tokens/`** — `colors_and_type.css` (CSS custom-property tokens) and the base64-inlined font bundles (`fonts-inline.css` for the full family, `fonts-inline-card.css` for the Light/Book/Regular/Medium subset)
- **`assets/`** — `logo/` (wordmark, logomark, lockup), `icons/` (SVG icon library), `decorations/` (lunes, dashed circles, sine wave), `reference-renders/` (brand-team comp PNGs)
- **`fonts/`** — raw .otf files (source for the inlined bundles)
- **`preview/`** — small HTML cards rendered in the Design System tab
- **`scripts/`** — `regenerate_fonts_inline.js` rebuilds `tokens/fonts-inline*.css` whenever the .otf binaries change

---

## Visual foundations

### Color (from `theme1.xml`)

| Token | Hex | Theme role | Use |
|---|---|---|---|
| `--ink` | `#1C2733` | dk1 / lt1-on-dark | Primary dark surface, primary text |
| `--paper` | `#FFFFFF` | lt1 | Light surface |
| `--forest` | `#01514F` | dk2 | Deep accent surface |
| `--cream` | `#FAFAF7` | lt2 | Off-white surface |
| `--teal` | `#59BBB6` | accent1 | Primary accent — most-used |
| `--cerulean` | `#4D6FF8` | accent2 | Secondary accent / link |
| `--ice` | `#A6C3ED` | accent3 | Tertiary accent / surface tint |
| `--coral` | `#EE6C5A` | accent4 | Warm accent / call-out |
| `--wine` | `#3F0A20` | accent5 | Deep accent — sparingly |
| `--lilac` | `#BCA0E7` | accent6 | Soft accent / quote tint |
| `--link` | `#0563C1` | hlink | Links (theme default) |

**Neutrals** (`--neutral-100` through `--neutral-950`) bridge `--paper` and `--ink`.

**Rules.**
- Dominant background is `--ink` `#1C2733` for marketing surfaces; `--paper` for product UI.
- One accent per layout. Never mix three accents at full saturation.
- Wine is reserved for moments of weight (a single quote, a section divider) — never a chart fill.
- Teal is the workhorse accent — use it first.

### Typography

The official template ships with **Arial** as both heading and body face. We mirror that:

- **Heading:** Arial — 300/400/700 across display, H1–H3, eyebrow.
- **Body:** Arial — 16px / 1.5, tracking −0.005em.
- **Mono:** JetBrains Mono — for numerics, code, and the eyebrow when set in mono.

**Optional override.** The licensed **FFF Acid Grotesk** webfont files are present in `fonts/` and pre-inlined as base64 `@font-face` rules in `tokens/fonts-inline.css` (full family) and `tokens/fonts-inline-card.css` (Light/Book/Regular/Medium subset). Paste a bundle's contents into a `<style>` block to render Acid Grotesk without any external font dependency. Acid Grotesk is the brand-book typeface; Arial is the executable substitute that ships with PowerPoint everywhere.

**Scale (px).**

| Role | Size | Weight | Tracking |
|---|---|---|---|
| Display | 96 / 64 / 48 | 300 | −0.02em |
| H1 | 42 | 400 | −0.01em |
| H2 | 28 | 400 | −0.01em |
| H3 | 22 | 400 | −0.01em |
| Body | 16 | 400 | −0.005em |
| Caption | 14 | 400 | 0 |
| Eyebrow | 11–14 | 400/500 | +0.04em, ALL CAPS |

### Spacing & grid

- **Slide canvas:** 1920 × 1080 (16:9), 64px outer margin.
- **Token scale (px):** `4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96, 128`.
- **Grid:** 12-column on slides, 8-column on landscape web heroes, 4-column on mobile.

### Decorations

The decoration kit comes from the .potx master pages, all built from circles:

- **`assets/decorations/dashed-circle.svg`** — 2px dashed ring, used as a quiet badge or anchor on cover slides.
- **`assets/decorations/lune.svg`** — single-arc crescent cut from two overlapping circles. Used on quote slides.
- **`assets/decorations/double-lune.svg`** — two stacked lunes, used on section dividers.
- **`assets/decorations/sine-wave.svg`** — low-amplitude sine, full-bleed across the bottom of "thank you" slides.

These are **never animated, never repeated more than once per layout, and always in a single colour** (usually `--teal` or `--ice` on dark, `--ink` on light).

### Borders, radii, shadows

- **Corner radius:** 2px for surface containers, 8px for cards in slide layouts. Buttons are pill-shaped.
- **Borders:** 1px solid `rgba(28,39,51,0.08)` on light, 1px solid `rgba(255,255,255,0.08)` on dark.
- **Shadows:** sparing. `0 4px 16px rgba(0,0,0,0.05)` for cards on light backgrounds; on dark, elevation comes from a 1-step-lighter neutral fill.

### Hover, press, focus

- **Hover:** opacity → 0.85, no color shift. Text-only links underline.
- **Press:** scale → 0.98, 80ms.
- **Focus:** 2px outer ring in `--cerulean` with a 2px offset.

### Motion

- **Easing:** `cubic-bezier(0.32, 0.72, 0, 1)`.
- **Durations:** 120ms (state), 240ms (modal), 600ms (hero-in).
- **No bounce, no parallax.** Motion is functional.

---

## Iconography

IBM Carbon-derived, then reduced. Icons are line-only, 2px stroke, drawn on an 85px symbol grid (scales to 24/32/48px in product). Monochrome, inherit `currentColor`. There is no inline icon font.

**Coverage:** ~20 SVGs in `assets/icons/` covering concept, action, data, object, and people categories. For anything not present, **substitute the matching IBM Carbon icon** at the same stroke weight — design-intent-equivalent.

**Emoji and unicode-as-icon:** never. The arrow `→` set in the body face is the only unicode glyph treated as ornament.

---

## How to use this system

For a fully self-contained HTML artifact (no external deps), paste both bundles into a single `<style>` block:

```html
<style>
  /* Paste contents of tokens/fonts-inline-card.css (or fonts-inline.css for the full family) */
  /* Paste contents of tokens/colors_and_type.css */
</style>
<body class="hx hx-dark">
  <p class="hx-eyebrow">— Brand guidelines</p>
  <h1 class="hx-display">Win more of the right risks</h1>
  <p class="hx-body">The pricing and underwriting platform for commercial P&amp;C insurance.</p>
</body>
```

Or, when the artifact lives next to this skill on disk and external links are fine:

```html
<link rel="stylesheet" href="tokens/fonts-inline-card.css">
<link rel="stylesheet" href="tokens/colors_and_type.css">
```

Or load tokens directly in your own CSS:

```css
.my-card {
  background: var(--surface-1);
  color: var(--fg-1);
  border-radius: var(--radius-card);
  padding: var(--space-6);
  font-family: var(--font-sans);
}
```
