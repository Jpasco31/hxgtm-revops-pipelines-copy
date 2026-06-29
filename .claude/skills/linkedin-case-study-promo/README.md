# linkedin-case-study-promo reference

The orchestration pipeline lives in [`SKILL.md`](SKILL.md). This file is the source of truth for visual specs, typography, copy limits, the customer-logo treatment, output paths, and QA.

## Canvas

- **Format:** LinkedIn 1:1 single image ad, customer-co-branded.
- **Per variant size:** 1080 x 1080.
- **Variants:** `wine`, `ink`, `forest`.
- **File targets:** 1x PNG (1080x1080) and 2x PNG (2160x2160).

## Visual spec

- Co-branded composition (hx wordmark top-left, customer logo top-right, headline below). No screenshot, no avatar, no speaker imagery.
- Fixed structure:
  - Top utility row with hx brand lockup (logomark + "hyperexponential" wordmark, top-left, embedded as inline SVG) and the prepared customer logo (top-right).
  - Gradient background layer (inlined from design-system assets).
  - Large headline block in the lower portion of the card.
- The three variants share identical layout and typography, changing only the base color and gradient.

### Theme colors

- **Wine:** `bg #3F0A20`, gradient: `gradient-wine.png`.
- **Ink:** `bg #1C2733`, gradient: `gradient-ink.png`.
- **Forest:** `bg #01514F`, gradient: `gradient-forest.png`.

Gradient PNGs live at `../design-system/assets/gradients/`. They are base64-encoded and inlined as CSS `background-image` data URIs at compose time.

### Customer logo (top-right)

- Position: top-right of the card, mirroring the hx lockup at top-left. Anchored at `top: 80px; right: 80px;` so both lockups sit on the same horizontal baseline as the existing hx wordmark.
- Asset: prepared white transparent PNG produced by nano banana in step 3 of the pipeline.
- Slot bounds via CSS variables on `.customer-logo`:
  - `--customer-max-w: 200px;`
  - `--customer-max-h: 80px;`
- `object-fit: contain` so the logo never stretches; the longer of the two bounds wins.
- The hx wordmark renders as a ~400x40 lockup (cap-height ~40px). The customer logo should sit at roughly the same optical weight — they should read as equal-rank co-brands in the top row, not parent + child.

### Optical sizing target

- Pure-wordmark customer logos (e.g. just text) should match the hx wordmark cap-height (~40-56px rendered). With a tight crop, the customer PNG usually renders at a height of 50-72px.
- Logomark + wordmark customer logos (e.g. icon next to text) usually look balanced when the **wordmark portion** matches that ~40-56px cap-height. The icon may extend taller. These typically render up to ~80px tall.

If the customer logo still looks visually lighter than the hx wordmark after auto-cropping, override the defaults inline on the card HTML:

```
<img class="customer-logo"
     style="--customer-max-w: 240px; --customer-max-h: 100px;"
     src="assets/[customer-slug]-logo-white-transparent.png"
     alt="[Customer name] logo">
```

Bump in 20px increments and re-export until the lockup feels balanced. Do not lower below the defaults; if the logo looks too heavy, the source crop is usually wrong and step 3 should be re-run.

When reverting to template defaults after a sizing experiment, keep the CSS variable declarations on `.customer-logo` and reset them to `--customer-max-w: 200px;` and `--customer-max-h: 80px;`. Do not remove the declarations entirely — without the variables, `max-width: var(--customer-max-w)` and `max-height: var(--customer-max-h)` become invalid and the logo can render at native size.

## Typography

- Headline: `100px`, weight `350`, line-height `110%`, color `#FFF`. Token: `Digital/Title/L`.
- Font: `"FFF Acid Grotesk"`, font-style `normal`.
- Fonts inlined via `{{FONT_FACE_BLOCK}}` from `../design-system/tokens/fonts-inline-card.css`.

## Customer logo cleanup prompt

Pass this prompt **verbatim** to `nano-banana` `edit_image`. Do not paraphrase or improvise.

> Preserve the original logo shape, proportions, spacing, and visual identity exactly. Convert all visible logo artwork to solid white (#FFFFFF). Remove the background completely and output a transparent PNG. Do not add shadows, gradients, outlines, borders, glow, texture, captions, taglines, extra text, or any new graphic elements. Keep edges clean and sharp. The final image should be a flat white logo on a transparent background, ready to place on a dark gradient case study card.

Before calling the tool, read its descriptor at the enabled MCP tools path for `user-nano-banana/tools/edit_image.json`. The tool requires a `prompt`; use absolute paths for both `path` and `output_path`.

Settings on the call:

- `path`: absolute path to the user's customer logo
- `output_path`: `[campaign-folder]/working/assets/[customer-slug]-logo-white-transparent.png`
- `aspect_ratio`: `"1:1"`
- `model`: `"pro"`

`[customer-slug]` = lowercase kebab-case of the customer name.

If the call fails or returns an error, stop and tell the user the customer logo could not be prepared. Do not use the raw logo — the card requires a white transparent customer logo.

After `edit_image` returns, verify the output has a real alpha channel:

```
sips -g hasAlpha "[output_path]"
```

If the result is `hasAlpha: no`, nano banana baked a checkerboard pattern as actual pixels instead of creating transparency. Fix it before continuing:

```
python3 ".claude/skills/linkedin-case-study-promo/scripts/fix_logo_transparency.py" \
  "[output_path]"
```

This edits the file in place: white artwork becomes opaque white, dark background becomes transparent, then the image is auto-cropped to the alpha bounding box. It is safe to run even if the logo is already correct (it will re-save as RGBA with a real alpha channel).

After fixing, visually confirm the logo is not undersized in the top-right slot due to excess transparent padding. If the logo appears too small, rerun `edit_image` with the same prompt and note that the canvas should be tightly cropped around the logo artwork.

## Placeholder rules

Replace these placeholders in each selected template:

- `{{FONT_FACE_BLOCK}}` — full contents of `../design-system/tokens/fonts-inline-card.css`.
- `{{GRADIENT_SRC}}` — base64 data URI of the variant's gradient PNG from `../design-system/assets/gradients/` (`gradient-wine.png`, `gradient-ink.png`, `gradient-forest.png`). Format: `data:image/png;base64,[base64 output]`.
- `{{HEADLINE}}` — sentence case, target <= 12 words.
- `{{CUSTOMER_LOGO_SRC}}` — relative path `assets/[customer-slug]-logo-white-transparent.png`.
- `{{CUSTOMER_LOGO_ALT}}` — `[Customer name] logo`.

Copy constraints:

- Sentence case.
- No emoji.
- No em dashes.
- No hype adjectives.
- Keep "hyperexponential" lowercase if used.

## Output naming

- HTML: `linkedin-case-study-promo_YYYYMMDD_[customer-slug]-[topic-slug]-wine.html` (and `-ink`, `-forest`)
- PNG: same slug with `.png` and `@2x.png`.

## Output paths

For campaign folder `[campaign-folder]`:

```
[campaign-folder]/
├── working/
│   ├── assets/
│   │   └── [customer-slug]-logo-white-transparent.png
│   ├── linkedin-case-study-promo_20260509_novo-nordisk-gen-ai-wine.html
│   ├── linkedin-case-study-promo_20260509_novo-nordisk-gen-ai-ink.html
│   └── linkedin-case-study-promo_20260509_novo-nordisk-gen-ai-forest.html
└── export/
    ├── linkedin-case-study-promo_20260509_novo-nordisk-gen-ai-wine.png
    ├── linkedin-case-study-promo_20260509_novo-nordisk-gen-ai-wine@2x.png
    ├── linkedin-case-study-promo_20260509_novo-nordisk-gen-ai-ink.png
    ├── linkedin-case-study-promo_20260509_novo-nordisk-gen-ai-ink@2x.png
    ├── linkedin-case-study-promo_20260509_novo-nordisk-gen-ai-forest.png
    └── linkedin-case-study-promo_20260509_novo-nordisk-gen-ai-forest@2x.png
```

## Puppeteer

The exporter uses `puppeteer`. `node_modules/` is not shipped with the skill. First-time install:

```
cd ".claude/skills/linkedin-case-study-promo/scripts"
npm install
```

After that the install persists locally. Re-run only if `package.json` changes.

## QA checklist

For each exported PNG:

- [ ] Source customer logo was supplied by the user as an absolute path.
- [ ] Customer logo was processed with `user-nano-banana` `edit_image` using the exact prompt above.
- [ ] `sips -g hasAlpha` on the prepared logo returns `hasAlpha: yes`. If not, `scripts/fix_logo_transparency.py` was run before composition.
- [ ] Prepared customer logo is white artwork on a transparent background.
- [ ] Size is exact (`1080x1080` for 1x and `2160x2160` for 2x).
- [ ] Headline text does not overflow or clip.
- [ ] Gradient and base color match the selected variant.
- [ ] hx brand lockup is visible in the top-left.
- [ ] Customer logo is visible in the top-right, not clipped, and optically balanced against the hx wordmark.
- [ ] Card contains no screenshot/avatar/photo/extra-logo elements.
- [ ] Composition remains aligned to fixed template geometry.
- [ ] If nano banana failed, the pipeline was aborted and no card was exported with the raw logo.

## Reference source

- Figma file: `8sGAsifGavCoNlX3J8v8U1`
- Node family: `1589:14677`, `1589:14836`, `1589:14875` (text-only ad family used as the geometry base)
- Customer logo treatment is mirrored from the `linkedin-partnership-card` skill.
