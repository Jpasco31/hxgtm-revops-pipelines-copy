---
name: linkedin-image-ad-text-only
description: Generate a text-only LinkedIn single image ad for hyperexponential at 1080x1080. Use when the user asks to create, build, design, render, or export a text-only LinkedIn image ad with no product screenshot, no avatar, and no speaker imagery. Outputs three variants (wine, ink, forest) from fixed templates and exports 1x and 2x PNGs.
user-invocable: true
requires: [design-system]
metadata:
  version: 1.0.0
---

# linkedin-image-ad-text-only skill

Produces **3 text-only variants** at **1080x1080** and exports PNGs.

Read [`README.md`](README.md) before composing. It contains the visual spec, type rules, placeholder guidance, output naming, and QA checklist.

## When to use

User says any of: "make a text-only LinkedIn ad", "create a square LinkedIn image ad with no screenshot", "build wine/ink/forest ad variants", "export text-only LinkedIn promo cards".

## Pipeline

### 1. Collect inputs (required)

Ask for whatever is missing. Required fields:

- **Headline**
- **Campaign folder** (absolute path under `Projects/Rev Ops Pipelines/campaigns/`). Skill writes to `[campaign-folder]/working/` and `[campaign-folder]/export/`.

Optional:

- **Filename date** in `YYYYMMDD` format (defaults to today).
- **Variant preference** (`wine`, `ink`, `forest`; default is all 3).

### 2. Read brand context

This skill declares `requires: [design-system]`. Read the sibling design-system skill before composing:

1. [`../design-system/SKILL.md`](../design-system/SKILL.md)
2. [`../design-system/README.md`](../design-system/README.md)

Apply brand colors, typography, and writing rules. Do not critique or rewrite the supplied headline — use it exactly as provided.

### 3. Choose templates

Use the fixed templates in [`templates/`](templates/):

- `card-wine.html`
- `card-ink.html`
- `card-forest.html`

Each template is a locked 1080x1080 text-only composition aligned to the Figma design reference (`8sGAsifGavCoNlX3J8v8U1`, `node-id=1589:14677` family).

### 4. Compose each variant

For each selected variant, replace placeholders:

- `{{FONT_FACE_BLOCK}}` — paste the **full contents** of [`../design-system/tokens/fonts-inline-card.css`](../design-system/tokens/fonts-inline-card.css). This inlines all `@font-face` rules so the output HTML is fully self-contained.
- `{{GRADIENT_SRC}}` — base64-encode the matching PNG from [`../design-system/assets/gradients/`](../design-system/assets/gradients/) (`gradient-wine.png`, `gradient-ink.png`, or `gradient-forest.png`) and paste the result as a data URI: `data:image/png;base64,[output of: base64 < gradient-wine.png]`. This fills the CSS `background-image` on `.card` so the HTML is self-contained.
- `{{HEADLINE}}`

Rules:

- Keep copy concise so the headline does not overflow.
- Do not add screenshots, avatars, logos from other companies, speaker names, or event metadata.
- Do not change card geometry, spacing, or base color tokens from templates.

### 5. Write outputs

For each variant:

- HTML -> `[campaign-folder]/working/linkedin-image-ad-text-only_[YYYYMMDD]_[TOPIC-SLUG]-<variant>.html`

Where `<variant>` is `wine`, `ink`, or `forest`.

### 6. Export PNGs

Run exporter for each HTML file:

```
node ".claude/skills/linkedin-image-ad-text-only/scripts/export_card.js" \
  "<absolute path to html>" \
  "<campaign-folder>/export"
```

This writes 1x and 2x PNG for each selected variant.

If puppeteer not installed:

```
cd ".claude/skills/linkedin-image-ad-text-only/scripts"
npm install
```

### 7. Verify

Open the exported 1x PNGs and check:

- Each image is exactly 1080x1080.
- Headline is visible and not clipped.
- Palette and decorative field match the selected variant.
- No non-text imagery appears.
- All requested variants were exported.

## Hard rules

- Canvas is always 1080x1080.
- Default output is all 3 variants unless user explicitly requests fewer.
- Text-only composition only (no hero image, no avatars, no speaker chips).
- Use only `wine`, `ink`, or `forest` templates.
- Keep output HTML self-contained (inline CSS/SVG).
- Do not modify adjacent skills.

## Out of scope

- 1200x627 webinar cards, customer quote cards, or partnership cards.
- Vertical ad formats (1080x1350 or story).
- Figma write-back.
