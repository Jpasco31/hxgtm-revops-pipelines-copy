# linkedin-image-ad-text-only reference

The orchestration pipeline lives in [`SKILL.md`](SKILL.md). This file is the source of truth for visual specs, typography, copy limits, output paths, and QA.

## Canvas

- **Format:** LinkedIn 1:1 single image ad.
- **Per variant size:** 1080 x 1080.
- **Variants:** `wine`, `ink`, `forest`.
- **File targets:** 1x PNG (1080x1080) and 2x PNG (2160x2160).

## Visual spec

- Text-only composition (no screenshot, no avatar, no partner logo).
- Fixed structure:
  - Top utility row with hx brand lockup (logomark + "hyperexponential" wordmark, top-left).
  - Gradient background layer (inlined from design-system assets).
  - Large headline block in the lower portion of the card.
- The three variants share identical layout and typography, changing only the base color and gradient.

### Theme colors

- **Wine:** `bg #3F0A20`, gradient: `gradient-wine.png`.
- **Ink:** `bg #1C2733`, gradient: `gradient-ink.png`.
- **Forest:** `bg #01514F`, gradient: `gradient-forest.png`.

Gradient PNGs live at `../design-system/assets/gradients/`. They are base64-encoded and inlined as CSS `background-image` data URIs at compose time.

## Typography

- Headline: `100px`, weight `350`, line-height `110%`, color `#FFF`. Token: `Digital/Title/L`.
- Font: `"FFF Acid Grotesk"`, font-style `normal`.
- Fonts inlined via `{{FONT_FACE_BLOCK}}` from `../design-system/tokens/fonts-inline-card.css`.

## Placeholder rules

Replace these placeholders in each selected template:

- `{{FONT_FACE_BLOCK}}` — full contents of `../design-system/tokens/fonts-inline-card.css`.
- `{{GRADIENT_SRC}}` — base64 data URI of the variant's gradient PNG from `../design-system/assets/gradients/` (`gradient-wine.png`, `gradient-ink.png`, `gradient-forest.png`). Format: `data:image/png;base64,[base64 output]`.
- `{{HEADLINE}}` — sentence case, target <= 10 words.

Copy constraints:

- Sentence case.
- No emoji.
- No em dashes.
- No hype adjectives.
- Keep "hyperexponential" lowercase if used.

## Output naming

- HTML: `linkedin-image-ad-text-only_YYYYMMDD_[topic-slug]-wine.html` (and `-ink`, `-forest`)
- PNG: same slug with `.png` and `@2x.png`.

## Output paths

For campaign folder `[campaign-folder]`:

```
[campaign-folder]/
├── working/
│   ├── linkedin-image-ad-text-only_20260508_topic-wine.html
│   ├── linkedin-image-ad-text-only_20260508_topic-ink.html
│   └── linkedin-image-ad-text-only_20260508_topic-forest.html
└── export/
    ├── linkedin-image-ad-text-only_20260508_topic-wine.png
    ├── linkedin-image-ad-text-only_20260508_topic-wine@2x.png
    ├── linkedin-image-ad-text-only_20260508_topic-ink.png
    ├── linkedin-image-ad-text-only_20260508_topic-ink@2x.png
    ├── linkedin-image-ad-text-only_20260508_topic-forest.png
    └── linkedin-image-ad-text-only_20260508_topic-forest@2x.png
```

## QA checklist

For each exported PNG:

- [ ] Size is exact (`1080x1080` for 1x and `2160x2160` for 2x).
- [ ] Headline text does not overflow or clip.
- [ ] Gradient and base color match the selected variant.
- [ ] hx brand lockup is visible in top-left.
- [ ] Card contains no screenshot/avatar/photo/partner-logo elements.
- [ ] Composition remains aligned to fixed template geometry.

## Reference source

- Figma file: `8sGAsifGavCoNlX3J8v8U1`
- Node family: `1589:14677`, `1589:14836`, `1589:14875`
