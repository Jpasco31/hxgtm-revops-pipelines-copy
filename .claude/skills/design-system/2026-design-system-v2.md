# 2026 Design System — v2
**Source:** [Brand Design System – New 2026 (Figma)](https://www.figma.com/design/8sGAsifGavCoNlX3J8v8U1/Brand-Design-System--New-2026-)
**File key:** `8sGAsifGavCoNlX3J8v8U1`
**Last extracted:** April 22, 2026

This is the v2 reference for any skill that produces hx-branded visual assets. Compared to v1 it is organised around **semantic tokens** (Background, Text, Surface, Button) rather than raw colour swatches, adds **exact component specs** pulled from Figma, and includes the **Figma annotation names** so content-type playbooks can map 1:1 to real Figma components.

Template-level specs (which components to use for a webinar card, a stats post, etc.) do not live here — they live in each skill's `content-types/` playbooks.

---

## 0. How to use this file

- **Primitive layer** → sections 1–2 (raw palette + type scale)
- **Semantic layer** → sections 3–5 (what you actually consume in playbooks)
- **Component layer** → section 6 (buttons, surfaces, eyebrows, logos, gradients)
- **Rules layer** → section 7 (colour pairings, hard brand rules)

Playbooks should reference tokens by **semantic name** (e.g. `surface/glass/social`, `button/default/dark`) — not raw hex — so visual refreshes only happen in this file.

---

## 1. Brand Colours (primitives)

### Primary Brand Colours

| Name | Token | HEX | PMS | CMYK |
|------|-------|-----|-----|------|
| Ink | `--primary/ink` | `#1D2733` | 7546 C | 84 / 70 / 48 / 49 |
| Wine | `--primary/wine` | `#400A20` | 7421 C | 47 / 99 / 54 / 59 |
| Forest | `--primary/forest` | `#01514E` | 7721 C | 89 / 48 / 59 / 36 |

> Ink is the default dark background. Wine and Forest are primary accent colours used for content differentiation.

### Primary Gradients

Three gradient variants (raster fills in Figma, so treat them as image assets when reproducing outside Figma).

| Name | Figma annotation | Base colour |
|------|------------------|-------------|
| Ink Gradient | `Background.gradient` | `#1D2733` |
| Wine Gradient | `Background.gradient` | `#400A20` |
| Forest Gradient | `Background.gradient` | `#01514E` |

**Overlay rule (corrected):** apply the gradient fill as background, then overlay a `#D9D9D9` fill at `mix-blend-mode: multiply`, **opacity `50%`** — this is what the Figma file uses (v1 incorrectly said 80%).

### Accent Palette — Blue

| Name | Token | HEX | PMS | CMYK |
|------|-------|-----|-----|------|
| Ink | `--accent/blue/ink` | `#1D2733` | 7546 C | 84 / 70 / 48 / 49 |
| Cerulean | `--accent/blue/cerulean` | `#4E70F8` | 2718 C | 61 / 42 / 2 / 0 |
| Ice | `--accent/blue/ice` | `#A6C4EE` | 2717 C | 33 / 13 / 0 / 0 |
| Pale Yellow | `--accent/blue/pale-yellow` | `#F4FFBE` | Yellow 0131 C | 08 / 0 / 33 / 0 |

### Accent Palette — Red / Warm

| Name | Token | HEX | PMS | CMYK |
|------|-------|-----|-----|------|
| Wine | `--accent/red/wine` | `#400A20` | 7421 C | 47 / 99 / 54 / 59 |
| Coral | `--accent/red/coral` | `#EE6C5B` | 1635 C | 0 / 70 / 58 / 0 |
| Pink | `--accent/red/pink` | `#FFB3C3` | 1767 C | 0 / 42 / 09 / 0 |
| Lilac | `--accent/red/lilac` | `#BCA1E8` | 2645 C | 28 / 36 / 0 / 0 |

> **Coral** (`#EE6C5B`) is the primary social-media accent for headlines and display text on dark solid backgrounds.

### Accent Palette — Green

| Name | Token | HEX | PMS | CMYK |
|------|-------|-----|-----|------|
| Forest | `--accent/green/forest` | `#01514E` | 7721 C | 89 / 48 / 59 / 36 |
| Forest Light | `--accent/green/forest-light` | `#59BBB7` | 563 C | 64 / 0 / 32 / 0 |
| Cyan | `--accent/green/cyan` | `#49DEFF` | 305 C | 57 / 0 / 03 / 0 |
| Tangerine | `--accent/green/tangerine` | `#FFB194` | 162 C | 41 / 0 / 39 / 0 |

### Neutral Scale

| Token | HEX | Use |
|-------|-----|-----|
| `--neutrals/50` | `#FFFFFF` | White — primary text on dark bg |
| `--neutrals/100` | `#F5F5F5` | Near-white backgrounds |
| `--neutrals/200` | `#F0F0F0` | Light surface |
| `--neutrals/300` | `#E0E0E0` | Borders, dividers, muted text on gradient pills |
| `--neutrals/400` | `#C6C7C8` | Disabled states |
| `--neutrals/500` | `#B5B6B8` | Supporting / muted text on dark bg |
| `--neutrals/600` | `#848D9A` | Subdued body copy on light bg |
| `--neutrals/700` | `#28323F` | Dark card backgrounds |
| `--neutrals/800` | `#1D2935` | Deep background |
| `--neutrals/900` | `#16212E` | Primary dark background + default dark button |
| `--neutrals/950` | `#0F1924` | Deepest background |

### Opacity Variants

All brand colours expose these opacity levels for layering, overlays, and text hierarchy.

| Level | Value |
|-------|-------|
| Full | 100% |
| High | 75% |
| Mid | 50% |
| Low | 25% |

---

## 2. Typography

### Typefaces

| Face | Usage | Style |
|------|-------|-------|
| **FFF Acid Grotesk Book** | Display, body, headlines, buttons | Not italic |
| **JetBrains Mono Regular** | Labels, eyebrows, running heads, monospace tags | Uppercase, regular weight |

### Social Media Type Scale

Sizes are in **pt/px** for social contexts. Where two values appear (e.g. `30/24`), the larger is for wide formats, the smaller for square or compact formats.

| Element | Size | Font |
|---------|------|------|
| Stats / Hero Number | 140 | FFF Acid Grotesk |
| Headline (display) | 84 (line-height 1.1) | FFF Acid Grotesk |
| Main message (L1) | 48 | FFF Acid Grotesk |
| Quote text | 48 | FFF Acid Grotesk |
| CTA / Button (wide) | 48 | FFF Acid Grotesk |
| CTA / Button (compact) | 30 | FFF Acid Grotesk |
| Supporting info (L2) | 30 | FFF Acid Grotesk |
| Quote name | 30 | FFF Acid Grotesk |
| Quote job title | 30 | FFF Acid Grotesk |
| Speaker name | 30 / 24 | FFF Acid Grotesk |
| Speaker job title | 30 / 24 | FFF Acid Grotesk |
| Eyebrow | 30 / 24 | JetBrains Mono |
| Tags / event info | 30 | JetBrains Mono |
| Running head | 24 | JetBrains Mono |
| Secondary button | 30 | FFF Acid Grotesk |
| Body / supporting copy | 10–12 | FFF Acid Grotesk |

---

## 3. Semantic Background Tokens

Pulled from the `Background` section of the Figma file. Consume these in templates instead of raw palette values.

| Semantic token | Resolves to | Use |
|----------------|-------------|-----|
| `bg/page/dark` | `--neutrals/900` (`#16212E`) | Default social-post background |
| `bg/page/deep` | `--neutrals/950` (`#0F1924`) | Deepest background, hero modules |
| `bg/page/light` | `--neutrals/50` (`#FFFFFF`) | Light-mode page / light pill backdrop |
| `bg/page/surface-light` | `--neutrals/100` (`#F5F5F5`) | Light secondary surface |
| `bg/card/dark` | `--neutrals/700` (`#28323F`) | Dark card on a dark page |
| `bg/gradient/ink` | Ink gradient + 50% multiply overlay | Hero card, launch post |
| `bg/gradient/wine` | Wine gradient + 50% multiply overlay | Thought-leadership, events |
| `bg/gradient/forest` | Forest gradient + 50% multiply overlay | Partnership / community content |

---

## 4. Semantic Text Tokens

Pulled from the `Text` section of the Figma file.

| Semantic token | Resolves to | Use |
|----------------|-------------|-----|
| `text/on-dark/primary` | `--neutrals/50` (`#FFFFFF`) | Headlines on dark bg |
| `text/on-dark/secondary` | `--neutrals/500` (`#B5B6B8`) | Body copy on dark bg |
| `text/on-dark/muted` | `--neutrals/300` (`#E0E0E0`) | Muted label on dark bg / gradient pill secondary |
| `text/on-dark/accent` | `--accent/red/coral` (`#EE6C5B`) | Display accent on solid dark bg only |
| `text/on-light/primary` | `--neutrals/900` (`#16212E`) | Headlines on light bg |
| `text/on-light/secondary` | `--neutrals/600` (`#848D9A`) | Body copy on light bg |
| `text/on-gradient/primary` | `--neutrals/50` (`#FFFFFF`) | Headlines on any gradient bg |
| `text/on-gradient/secondary` | `--neutrals/50` @ 75% | Body copy on any gradient bg |

> **Never** use Coral on gradient backgrounds — use white.

---

## 5. Semantic Surface Tokens

| Semantic token | Figma annotation | Resolves to | Use |
|----------------|------------------|-------------|-----|
| `surface/glass/social` | `Surface.default.glass.social` | `rgba(255,255,255,0.10)`, radius `20px` | Glass card over gradient/image for social posts |
| `surface/card/dark` | — | `--neutrals/700`, radius `20px` | Solid dark card on dark bg |
| `surface/card/light` | — | `--neutrals/50`, radius `20px` | Solid light card on light bg |

---

## 6. Components

### 6.1 Primary Button

All three variants share the same geometry — they are **separate components**, not interaction states. `Hover` is literally the light pill, `Clicked` is the gradient pill. Pick the variant that fits the surface you are on.

**Geometry (all variants)**

| Property | Value |
|----------|-------|
| Width × height | `302.244 × 64.767 px` (reference size) |
| Border radius | `69.084 px` (fully pill) |
| Padding (horizontal) | `69.084 px` |
| Label font | FFF Acid Grotesk Book, `30.224 px`, not italic |
| Label gap (between tokens) | `8.636 px` |
| Content gap | `17.271 px` |
| Suffix | ` →` appended to final word |

**Two-tone label pattern**

Every primary button label is split into two text runs: the **lead word(s)** in the primary text colour, and the **action + arrow** in the secondary (muted) text colour. Example: `Book a` (primary) + `Demo →` (secondary). Content-type playbooks must follow this pattern.

**Variants**

| Variant | Figma annotation | Background | Primary text | Secondary text | Use on |
|---------|------------------|------------|--------------|----------------|--------|
| `button/default/dark` | `button.default.dark` | `--neutrals/900` (`#16212E`) | `--neutrals/50` (`#FFFFFF`) | `--neutrals/500` (`#B5B6B8`) | Light or white backgrounds |
| `button/default/light` | `button.default.light` | `--neutrals/50` (`#FFFFFF`) | `--neutrals/900` (`#16212E`) | `--neutrals/600` (`#848D9A`) | Dark or Ink backgrounds |
| `button/secondary/gradient` | `button.secondary.gradient` | Brand gradient fill | `--neutrals/50` (`#FFFFFF`) | `--neutrals/300` (`#E0E0E0`) | Gradient backgrounds, secondary CTAs |

**Hard rules**

1. Never put a dark pill on a dark background — switch to the light variant.
2. Never put a light pill on a pure white page — switch to the dark variant.
3. The gradient pill is secondary-only; it should not be the sole CTA on a page.

### 6.2 Eyebrow / Label

```
[● indicator dot]  [UPPERCASE LABEL TEXT]
```

| Property | Value |
|----------|-------|
| Dot | `4 × 4 px` square, `--accent/red/coral` |
| Text | JetBrains Mono Regular, 6–8 px (or 24/30 pt on social), white, uppercase |
| Gap dot → text | `5 px` |

Used for post-type labels such as `LIVE SESSION`, `SESSION SPOTLIGHT`, `REGISTER YOUR INTEREST`.

### 6.3 Section Divider / Running Head

- Font: JetBrains Mono Regular, 24 pt
- Colour: White on dark, `--neutrals/500` on lighter dark surfaces

### 6.4 Logo Lockup

- Component name: `hx Logo Lockup`
- Reference width: `~279 px`
- Pairs with URL text (e.g. `hyperexponential.com/careers`) at 24 pt FFF Acid Grotesk Book

### 6.5 Gradient Background Block

- Component name: `Gradient BG`
- Reference size: `322.631 × 241.973 px` (scales with frame)
- Structure: raster gradient image + `#D9D9D9` overlay at `multiply 50%`
- Do not recreate the gradient procedurally — export from Figma

---

## 7. Usage Rules

### Colour pairings for social posts

| Background | Headline colour | Body colour |
|------------|-----------------|-------------|
| Ink / `--neutrals/900` | Coral `#EE6C5B` | White |
| Ink / `--neutrals/900` | White | `--neutrals/500` |
| White / `--neutrals/50` | Ink `#1D2733` | `--neutrals/600` |
| Ink gradient | White | White @ 75% |
| Wine gradient | White | White @ 75% |
| Forest gradient | White | White @ 75% |

### Accent selection by content type

| Content type | Recommended accent |
|---|---|
| Events / live sessions | Coral |
| Product / technical | Cerulean or Cyan |
| Thought leadership / quotes | Lilac or Ice |
| Data / stats | Pale Yellow or Tangerine |
| Partnership / community | Forest Light |

### Hard brand rules

1. Never use Coral on a gradient background — use white headlines.
2. Never use a dark button on a dark background (use `button/default/light` instead).
3. `--neutrals/600` body copy is for light backgrounds only.
4. On dark backgrounds use `--neutrals/500` for body copy, not `--neutrals/600`.
5. On all three gradients: white type only — never Coral.
6. Gradient overlay is `multiply 50%`, not 80%.
7. Never redraw the primary button — always instance `Primary-Button/Default`, `/Hover`, or `/Clicked` from Figma.

---

## 8. CSS Variables (drop-in)

```css
:root {
  /* Primary brand */
  --primary-ink:    #1D2733;
  --primary-wine:   #400A20;
  --primary-forest: #01514E;

  /* Neutrals */
  --neutrals-50:  #FFFFFF;
  --neutrals-100: #F5F5F5;
  --neutrals-200: #F0F0F0;
  --neutrals-300: #E0E0E0;
  --neutrals-400: #C6C7C8;
  --neutrals-500: #B5B6B8;
  --neutrals-600: #848D9A;
  --neutrals-700: #28323F;
  --neutrals-800: #1D2935;
  --neutrals-900: #16212E;
  --neutrals-950: #0F1924;

  /* Accent — Blue */
  --accent-blue-cerulean:    #4E70F8;
  --accent-blue-ice:         #A6C4EE;
  --accent-blue-pale-yellow: #F4FFBE;

  /* Accent — Red */
  --accent-red-coral: #EE6C5B;
  --accent-red-pink:  #FFB3C3;
  --accent-red-lilac: #BCA1E8;

  /* Accent — Green */
  --accent-green-forest-light: #59BBB7;
  --accent-green-cyan:         #49DEFF;
  --accent-green-tangerine:    #FFB194;

  /* Semantic — Background */
  --bg-page-dark:         var(--neutrals-900);
  --bg-page-deep:         var(--neutrals-950);
  --bg-page-light:        var(--neutrals-50);
  --bg-page-surface-light:var(--neutrals-100);
  --bg-card-dark:         var(--neutrals-700);

  /* Semantic — Text */
  --text-on-dark-primary:      var(--neutrals-50);
  --text-on-dark-secondary:    var(--neutrals-500);
  --text-on-dark-muted:        var(--neutrals-300);
  --text-on-dark-accent:       var(--accent-red-coral);
  --text-on-light-primary:     var(--neutrals-900);
  --text-on-light-secondary:   var(--neutrals-600);
  --text-on-gradient-primary:  var(--neutrals-50);

  /* Semantic — Surface */
  --surface-glass-social: rgba(255, 255, 255, 0.10);
  --surface-card-dark:    var(--neutrals-700);
  --surface-card-light:   var(--neutrals-50);

  /* Radii */
  --radius-card:   20px;
  --radius-pill:   9999px;
}
```

---

## 9. Changelog vs v1

- **Added** semantic token layer (Background / Text / Surface) matching the Figma `Background`, `Text`, `Surface` sections.
- **Added** Figma annotation names (`button.default.dark`, `Surface.default.glass.social`, etc.) so playbooks can map to components.
- **Added** glass surface token `surface/glass/social` at `rgba(255,255,255,0.10)`, radius 20 px.
- **Corrected** gradient overlay: `multiply 50%` (was `80%` in v1).
- **Corrected** primary button spec — the three variants are separate components, not hover/click states; each has its own colour pairing.
- **Documented** the two-tone button label pattern (primary lead + muted action).
- **Clarified** dark vs light pill usage rules by surface.
