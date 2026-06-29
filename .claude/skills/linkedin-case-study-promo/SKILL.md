---
name: linkedin-case-study-promo
description: Generate a square LinkedIn case study promo card for hyperexponential at 1080x1080. Use when the user asks to create, build, design, render, or export a case study card, customer case study promo, customer-result LinkedIn ad, or co-branded case-study image. Always places the hyperexponential wordmark in the top-left and a required customer logo in the top-right, prepared as a white transparent PNG via nano banana. Outputs three variants (wine, ink, forest) from fixed templates and exports 1x and 2x PNGs.
user-invocable: true
requires: [design-system]
metadata:
  version: 1.0.0
---

# linkedin-case-study-promo skill

Produces **3 case-study promo variants** at **1080x1080** with a co-branded hx + customer lockup in the top row, and exports PNGs.

Read [`README.md`](README.md) before composing. It contains the visual spec, type rules, customer-logo treatment, the verbatim nano banana prompt, placeholder guidance, output naming, and QA checklist.

## When to use

User says any of: "make a LinkedIn case study card", "build a case study promo", "create a customer-result LinkedIn ad", "export the [customer name] case study card", "build wine/ink/forest case study variants".

## Pipeline

### 1. Collect inputs (required)

Ask for whatever is missing. Required fields:

- **Headline**
- **Customer name** (used for alt text and the filename slug; e.g. `Novo Nordisk` -> `novo-nordisk`)
- **Customer logo path** (absolute path to the source customer logo image)
- **Campaign folder** (absolute path under `Projects/Rev Ops Pipelines/campaigns/`). Skill writes to `[campaign-folder]/working/` and `[campaign-folder]/export/`.

Optional:

- **Filename date** in `YYYYMMDD` format (defaults to today).
- **Variant preference** (`wine`, `ink`, `forest`; default is all 3).
- **Topic slug** (kebab-case; defaults to a slug derived from the headline).

The customer logo is **required**. If the user does not provide one, stop and ask before continuing — case study promos must be co-branded.

### 2. Read brand context

This skill declares `requires: [design-system]`. Read the sibling design-system skill before composing:

1. [`../design-system/SKILL.md`](../design-system/SKILL.md)
2. [`../design-system/README.md`](../design-system/README.md)

Apply brand colors, typography, and writing rules. Do not critique or rewrite the supplied headline — use it exactly as provided.

### 3. Prepare the customer logo

Call the `edit_image` tool from the `user-nano-banana` MCP server after reading that tool's schema at `user-nano-banana/tools/edit_image.json`. Use the exact prompt and settings from [`README.md`](README.md).

Settings:

- `path`: absolute path to the supplied customer logo
- `output_path`: `[campaign-folder]/working/assets/[customer-slug]-logo-white-transparent.png`
- `aspect_ratio`: `"1:1"`
- `model`: `"pro"`
- `prompt`: verbatim from README

Rules:

- Keep the customer's original logo shape and proportions.
- Convert visible logo artwork to solid white.
- Remove the background so the output is transparent.
- Do not add shadows, outlines, borders, taglines, icons, or extra text.

Create `[campaign-folder]/working/assets/` before calling.

After the call, run the alpha check and fix described in [`README.md`](README.md). nano banana frequently bakes a checkerboard as pixel data instead of creating real transparency (`hasAlpha: no`). Always run `sips -g hasAlpha` on the output and, if needed, fix it with `scripts/fix_logo_transparency.py` before moving to step 4.

If the call fails or the logo cannot be prepared, **stop the pipeline** and tell the user. Do not fall back to the raw logo — case study promos require a white transparent customer logo.

### 4. Choose templates

Use the fixed templates in [`templates/`](templates/):

- `card-wine.html`
- `card-ink.html`
- `card-forest.html`

Each template is a locked 1080x1080 composition: hx wordmark top-left, customer logo top-right, headline block in the lower portion, gradient background.

### 5. Compose each variant

For each selected variant, replace placeholders:

- `{{FONT_FACE_BLOCK}}` — paste the **full contents** of [`../design-system/tokens/fonts-inline-card.css`](../design-system/tokens/fonts-inline-card.css). This inlines all `@font-face` rules so the output HTML is fully self-contained.
- `{{GRADIENT_SRC}}` — base64-encode the matching PNG from [`../design-system/assets/gradients/`](../design-system/assets/gradients/) (`gradient-wine.png`, `gradient-ink.png`, or `gradient-forest.png`) and paste the result as a data URI: `data:image/png;base64,[output of: base64 < gradient-wine.png]`. This fills the CSS `background-image` on `.card` so the HTML is self-contained.
- `{{HEADLINE}}`
- `{{CUSTOMER_LOGO_SRC}}` — the **relative path** `assets/[customer-slug]-logo-white-transparent.png`. Do not use an absolute path or `file://` URL — the HTML is always written to `[campaign-folder]/working/` and the asset is always at `[campaign-folder]/working/assets/`, so the relative reference resolves cleanly for Puppeteer.
- `{{CUSTOMER_LOGO_ALT}}` — `[Customer name] logo`.

Rules:

- Keep copy concise so the headline does not overflow.
- Do not add screenshots, avatars, speaker names, or event metadata.
- Do not add additional partner logos — the only co-brand is the customer logo top-right.
- Do not change card geometry, spacing, or base color tokens from templates.

### 6. Write outputs

For each variant:

- HTML -> `[campaign-folder]/working/linkedin-case-study-promo_[YYYYMMDD]_[CUSTOMER-SLUG]-[TOPIC-SLUG]-<variant>.html`

Where `<variant>` is `wine`, `ink`, or `forest`. `[CUSTOMER-SLUG]` is lowercase kebab-case of the customer name. `[TOPIC-SLUG]` is lowercase kebab-case of the topic (or supplied/derived slug).

### 7. Export PNGs

Run exporter for each HTML file:

```
node ".claude/skills/linkedin-case-study-promo/scripts/export_card.js" \
  "<absolute path to html>" \
  "<campaign-folder>/export"
```

This writes 1x and 2x PNG for each selected variant.

If puppeteer not installed:

```
cd ".claude/skills/linkedin-case-study-promo/scripts"
npm install
```

### 8. Verify

Open the exported 1x PNGs and check:

- Each image is exactly 1080x1080.
- Headline is visible and not clipped.
- Palette and decorative field match the selected variant.
- hx wordmark appears top-left and customer logo appears top-right.
- Customer logo is white on a transparent background, not clipped, and optically balanced against the hx wordmark.
- No screenshots, avatars, photos, or extra logos appear.
- All requested variants were exported.

## Hard rules

- Canvas is always 1080x1080.
- Customer logo is **required**. Abort the pipeline if it is missing or if nano banana fails.
- Customer logo is always top-right. hx wordmark is always top-left. Both are white.
- Customer logo must be prepared as a transparent PNG with nano banana before composition.
- Default output is all 3 variants unless user explicitly requests fewer.
- No hero image, no avatars, no speaker chips, no extra partner logos.
- Use only `wine`, `ink`, or `forest` templates.
- Keep output HTML self-contained (inline CSS/SVG/fonts/gradient) except for the local prepared customer-logo image reference.
- Do not modify adjacent skills (`linkedin-image-ad-text-only`, `linkedin-partnership-card`, `design-system`, etc.).

## Out of scope

- 1200x627 webinar cards, customer quote cards, or partnership cards.
- Vertical ad formats (1080x1350 or story).
- Cards with multiple customer logos, partner logos, body copy, CTA, or badges.
- Figma write-back.
