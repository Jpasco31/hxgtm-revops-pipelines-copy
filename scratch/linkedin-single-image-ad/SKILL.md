---
name: linkedin-single-image-ad
description: Generate a self-contained, on-brand LinkedIn single image ad (1080x1080 square) for hyperexponential. Use when the user asks to design, produce, build, or export a LinkedIn ad, single image ad, square LinkedIn promo, demo ad card, product ad card, or schedule-a-demo card. Outputs a single HTML file with all CSS, fonts, and SVGs inlined plus PNGs at 1x and 2x via Puppeteer. Four layout variants: light-center, gradient-center, gradient-left, white-left.
user-invocable: true
requires: [design-system]
metadata:
  version: 1.0.0
---

# linkedin-single-image-ad skill

Produces a single LinkedIn-feed square ad at **1080x1080** (LinkedIn 1:1 single image ad slot) and exports it to PNG. Scope is product / demo-driver ad creative with **4 fixed layout variants**.

Read [`README.md`](README.md) before composing - it contains the variant picker, gradient picker, type spec table, layout details, hero-image catalog reference, copy rules, and the QA checklist. The terse pipeline below is the orchestration, not the source of truth for layout values.

## When to use

User says any of: "make a LinkedIn ad," "design a single image ad," "build a square LinkedIn promo," "demo ad card," "product ad," "schedule-a-demo card," "1080x1080 LinkedIn ad," "regenerate the ad."

For event / webinar / panel cards (1200x627 with named speakers), use `webinar-promo-card` instead - that is a separate skill with a different canvas and a different scope.

## Pipeline (9 steps)

### 1. Collect the brief
Ask for whatever isn't provided. Required fields:

- **Headline** (sentence case, ideally <= 8 words). For `white-left`, two short lines read best (line 2 renders muted gray).
- **Text alignment**: ask whether the user wants `center` or `left` aligned text.
- **Background**: ask whether the user wants `cream`, `wine`, `ink`, or `forest`.
- **Button**: ask whether a button is needed. If yes, collect `CTA label` and `CTA href` if not provided.
- **Button background**: ask for `white` or `dark` when a button is needed. Default to `white` on gradient backgrounds and `dark` on cream backgrounds.
- **Hero image source**: one of
  - a **curated key**: `portfolio` (see `hero-images/README.md`)
  - an absolute **`hero_path`** to a user-supplied source PNG / JPG
  - `none` to render without a hero image
- **Campaign folder**: absolute path to a folder under the project's `campaigns/` directory (peer to `skills/`). The skill will write outputs into `[campaign-folder]/working/` and `[campaign-folder]/export/`. Create the campaign folder if it doesn't exist.

Optional:

- **Subtitle** (one-line descriptor; `light-center` and `gradient-center` only)
- **Variant override**: `light-center` | `gradient-center` | `gradient-left` | `white-left` if the user already knows the exact scaffold they want.

If the user requests a vertical (1080x1350) or story (1080x1920) ad, stop and flag - this skill is square only.

### 2. Read brand context
This skill declares `requires: [design-system]`. Always read the sibling `design-system` skill in this order before writing any copy:

1. [`../design-system/SKILL.md`](../design-system/SKILL.md)
2. [`../design-system/README.md`](../design-system/README.md)
3. [`../design-system/PRODUCT_MARKETING_CONTEXT.md`](../design-system/PRODUCT_MARKETING_CONTEXT.md)

Apply the hard rules: sentence case, no em dashes, no emoji, no hype adjectives, lowercase "hyperexponential", never "hx Renew", American English, double quotation marks, Oxford comma. Coral is forbidden on any gradient background.

### 3. Read layout reference
The canonical layouts live in [`templates/`](templates/) - those four files ARE the layout source of truth (canvas size, padding, type sizes, hero-slot positioning, gradient stack, grain layer, vignette, inline lockup SVG). The hero-image catalog and slot/focal spec live in [`hero-images/README.md`](hero-images/README.md) and [`hero-images/manifest.json`](hero-images/manifest.json).

### 4. Pick the variant scaffold
Derive the scaffold from the user's text alignment and background choice:

- `center` + `cream` -> `card-light-center.html`
- `center` + `wine` / `ink` / `forest` -> `card-gradient-center.html`
- `left` + `wine` / `ink` / `forest` -> `card-gradient-left.html`
- `left` + `cream` -> `card-white-left.html`

See [`README.md`](README.md) ("Variant picker") for the use-case mapping.

### 5. Pick the gradient (gradient variants only)
From [`README.md`](README.md):

- **Wine** (default for `gradient-left`): flagship, executive, high-authority
- **Ink**: technical, product, engineering-led
- **Forest** (default for `gradient-center`): community, partnership, ecosystem, customer-led

White type only on all three. Coral is forbidden on gradient.

### 6. Resolve the hero image (variant-aware crop)
The hero slot dimensions are different per variant (see `manifest.json`). The skill resolves the hero image differently depending on the source:

- **Curated key** (`portfolio`): copy the matching pre-cropped PNG from `hero-images/` into the campaign's `working/hero/` folder.
  ```
  cp "hero-images/<key>--<variant-slot>.png" "[campaign-folder]/working/hero/<key>--<variant-slot>.png"
  ```
  `<variant-slot>` mapping: `light-center`,`gradient-center` -> `center`; `gradient-left` -> `left`; `white-left` -> `white-left`.
- **`hero_path`** (user-supplied): run the Sharp cropper, which reads the slot dimensions from `hero-images/manifest.json` and produces a focal-point-aware crop sized to the slot:
  ```
  node scripts/crop_hero.js <hero_path> <variant-slot> "[campaign-folder]/working/hero/<basename>--<variant-slot>.png" [--focal=fx,fy] [--auto-focal]
  ```
  Default focal point is `0.5,0.5` (center). Pass `--focal=0.20,0.10` etc. for an off-center hot spot, or `--auto-focal` to let Sharp's `attention` strategy pick. Output goes next to the HTML's sibling `working/hero/` folder.
- **`none`**: skip the hero. The template's hero region renders empty (the gradient or cream background fills the area).

Hero imagery is never AI-generated. nano-banana is not used by this skill.

`mkdir -p "[campaign-folder]/working/hero/"` before copying or cropping.

### 7. Compose the card
Start from the chosen template in [`templates/`](templates/), fill the placeholders:

- `{{FONT_FACE_BLOCK}}` - paste the **full contents** of [`../design-system/tokens/fonts-inline-card.css`](../design-system/tokens/fonts-inline-card.css). This is ~600 KB of base64-encoded `@font-face` rules (Light / Book / Medium upright). Pasting it inline makes the output HTML fully self-contained - no external font files needed.
- `{{HEADLINE}}` (light-center, gradient-center, gradient-left) - sentence case, brand-approved language.
- `{{HEADLINE_LINE_1}}` and `{{HEADLINE_LINE_2}}` (white-left only) - two-line headline; line 2 renders in muted gray. Pass `""` for line 2 to render a single line.
- `{{SUBTITLE}}` (light-center, gradient-center) - optional one-line descriptor; pass `""` to omit.
- `{{HERO_IMAGE_NODE}}` - `<img src="hero/<filename>.png" alt="">` referencing the resolved hero image, OR an empty string for no hero.
- `{{GRADIENT_BASE}}` (gradient variants only) - `#3F0A20` (Wine) / `#1C2733` (Ink) / `#01514F` (Forest). Also swap the `.bg-base` gradient stack per the README's gradient recipes (`BG_STACK` comment marks the swap point).
- Button controls - if the user wants no button, remove the whole `.cta` anchor from left-aligned templates and do not add one to center-aligned templates. If the user wants a button, use the collected CTA label and href. Use white button background on gradients by default and dark button background on cream by default, unless the user chooses otherwise.

Inline everything: the font-face block, CSS, the gradient stack, the SVG noise/grain layer, the vignette, and the wordmark lockup SVG (so it picks up `@font-face`). The output HTML has **no external dependencies** other than the sibling `hero/<filename>.png` referenced via `<img>`.

### 8. Write outputs
- HTML -> `[campaign-folder]/working/linkedin-ad_[YYYYMMDD]_[TOPIC-SLUG].html`
- Hero PNG (if any) -> `[campaign-folder]/working/hero/<filename>.png` (sibling of the HTML so the relative `<img src="hero/...">` resolves at export time)

`[YYYYMMDD]` = today's date in compact form (or the campaign's launch date if the user provides one). `[TOPIC-SLUG]` = kebab-case slug of the headline (lowercase, alphanumeric + hyphens, max 60 chars).

The `linkedin-ad_` filename prefix distinguishes outputs from `webinar-promo-card`'s `linkedin-card_` prefix when both skills run against the same campaign folder.

### 9. Export PNG
Run the exporter:

```
node ".claude/skills/linkedin-single-image-ad/scripts/export_card.js" \
  "<absolute path to the html written in step 8>" \
  "<campaign-folder>/export"
```

Saves `[slug].png` (1080x1080) and `[slug]@2x.png` (2160x2160, deviceScaleFactor 2). The script clones the `.card` element and screenshots only that node, so any browser chrome / page padding is excluded.

If puppeteer or sharp isn't installed yet, run `cd ".claude/skills/linkedin-single-image-ad/scripts" && npm install` once. `node_modules/` is gitignored.

## Hard rules

- No emoji, ever.
- Sentence case for everything.
- No em dashes. Use periods or commas.
- American English.
- Always lowercase "hyperexponential". Never "hx Renew".
- Headline must fit at the variant's spec'd size (76 / 76 / 120 / 100 px) without overflowing the visible canvas. Tighten the copy before tightening the type.
- Coral (`--coral`) is forbidden on any gradient background.
- Output HTML must be **fully self-contained**: inline CSS, inline lockup SVG, inline gradient stack, inline base64 `@font-face` rules from `fonts-inline-card.css`. The only external reference allowed is `<img src="hero/<filename>.png">` resolving to the sibling `working/hero/` folder.
- `nano-banana` is not used by this skill. Hero imagery is curated (`hero-images/`) or user-supplied via `hero_path`.

## Out of scope

- Vertical (1080x1350) and story (1080x1920) ad formats - flag and stop. Do not extrapolate pixel values from the 1:1 spec.
- Square-on-square carousel ads.
- Customer-quote ads, partnership ads, event-specific ads (use `webinar-promo-card` for events).
- Figma write-back / Figma file generation.
- AI-generated product UI mockups (curated `hero-images/` library or user-supplied source only).
