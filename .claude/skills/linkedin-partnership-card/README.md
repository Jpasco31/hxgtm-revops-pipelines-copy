# linkedin-partnership-card reference

The terse pipeline lives in [`SKILL.md`](SKILL.md). This file is the source of truth for the card geometry, background treatment, partner-logo preparation prompt, output paths, and QA checklist.

## Canvas

- **Format:** LinkedIn partnership announcement card.
- **Pixel size:** 1200 x 675.
- **Aspect ratio:** 16:9.
- **Border radius on the card:** 0px.
- **File targets:** PNG at 1x (1200x675) and 2x (2400x1350). PNG only.

## Visual Spec

The card is a flat dark-navy field with a uniform dot grid, and a centered white logo lockup joined by a "+" mark. No glow, no vignette, no gradients.

| Element | Spec |
|---|---|
| Card background | Embedded [`assets/Partnership-announcement.png`](assets/Partnership-announcement.png) (flat navy + uniform dot grid). Fallback color `#14202e`. |
| Logo row | Centered horizontally and vertically on the canvas |
| Left logo | hyperexponential wordmark, white, embedded in `templates/card.html` from `../design-system/assets/logo/hx-wordmark.svg` |
| Divider | White "+" mark, 34.96×33.32px, 1.67px stroke, solid white, centered between the logos. Reads as "hyperexponential + partner". |
| Right logo | Prepared partner logo, white transparent PNG |

## Layout

- `.card` is exactly `1200px` wide and `675px` tall.
- The logo lockup is a centered flex row (hx wordmark, "+" divider, partner logo) with a fixed `50.12px` gap between each element, vertically and horizontally centered on the canvas.
- The logo panels are content-width (`flex: 0 0 auto`), so the "+" divider is optically centered *between* the two logos by the equal `50.12px` gaps rather than pinned to the canvas midline. The divider's canvas x-position therefore shifts with the partner logo's width.
- The hyperexponential wordmark renders at `45.48px` tall, auto width (≈485px from its `viewBox`).
- The partner logo is constrained by CSS variables `--partner-max-w` (default `480px`) and `--partner-max-h` (default `45px`) with `object-fit: contain`. The 45px cap matches the hx wordmark height so the two logos read as equal-rank partners by default.
- Do not add text or decorative marks inside the logo row.

### Optical sizing target

Match the partner wordmark's *cap-height* to `hyperexponential` (~40px in the export), not the partner image's bounding-box height. Logo compositions vary wildly in their cap-height-to-bbox ratio — a tightly-cropped wordmark has bbox ≈ cap-height, but a wordmark+logomark composite (Allianz, S&P, Munich Re) has bbox much taller than its wordmark. A single bbox-height cap can't accommodate both, so the ladder below is composition-aware.

Pick a starting `--partner-max-h` from the ladder, render once, eyeball the cap-heights against `hyperexponential`, and step up by 8px until they match within ~2px. If the partner reads taller than hx, step back down.

| Partner logo type                                              | Starting `--partner-max-h` | Typical landing |
|----------------------------------------------------------------|----------------------------|-----------------|
| Wordmark only, cap-height ≥ 70% of bbox height                 | `45px` (default)           | 45–56px         |
| Wordmark only, cap-height 50–70% of bbox height (e.g. Allianz wordmark alone) | `56px`            | 56–64px         |
| Wordmark + logomark, balanced (wordmark ≥ 60% of bbox)         | `64px`                     | 64–72px         |
| Wordmark + logomark, mark-dominant (wordmark < 60% of bbox)    | `88px`                     | 80–96px         |
| Logomark only or icon-dominant                                 | `72px`                     | 64–80px         |

Upper sanity bound: **120px**. Beyond that the partner reads as the primary brand and the lockup inverts. Don't widen `--partner-max-w` — `object-fit: contain` handles aspect.

Apply via inline style on the `<img class="partner-logo">` tag:

```
<img class="partner-logo"
     style="--partner-max-h: 88px;"
     src="assets/[partner-slug]-logo-white-transparent.png"
     alt="[Partner name] logo">
```

The 88px example matches a wordmark + logomark, mark-dominant partner like Allianz. For a tight-cropped wordmark, leave the inline style off and the defaults (`--partner-max-w: 480px`, `--partner-max-h: 45px`) take over.

When reverting to defaults after a sizing experiment, keep the CSS variable declarations on `.partner-logo` and reset them to `--partner-max-w: 480px;` and `--partner-max-h: 45px;`. Don't remove the declarations entirely — without the variables, `max-width: var(--partner-max-w)` and `max-height: var(--partner-max-h)` become invalid and the partner logo can render at native size.

## Partner Logo Cleanup Prompt

The verbatim prompt the skill uses to convert any partner logo to flat white on transparent lives in [`references/nano-banana-logo-cleanup-prompt.md`](references/nano-banana-logo-cleanup-prompt.md). `scripts/cleanup_logo.js` loads it from disk and passes it straight to Gemini Image — do not paraphrase or improvise.

For reference, the prompt is:

> Preserve the original logo shape, proportions, spacing, and visual identity exactly. Convert all visible logo artwork to solid white (#FFFFFF). Remove the background completely and output a transparent PNG. Do not add shadows, gradients, outlines, borders, glow, texture, captions, taglines, extra text, or any new graphic elements. Keep edges clean and sharp. The final image should be a flat white logo on a transparent background, ready to place on a dark blue partnership announcement card.

### Calling the script

```
node ".claude/skills/linkedin-partnership-card/scripts/cleanup_logo.js" \
  --input "<abs path to the user's partner logo>" \
  --output "<campaign-folder>/working/assets/<partner-slug>-logo-white-transparent.png" \
  --prompt-file ".claude/skills/linkedin-partnership-card/references/nano-banana-logo-cleanup-prompt.md" \
  --model pro \
  --aspect-ratio "16:9"
```

| Flag | Purpose | Default |
|------|---------|---------|
| `--input` | Absolute path to the supplied partner logo | required |
| `--output` | Absolute path to write the cleaned PNG | required |
| `--prompt-file` | Absolute path to the verbatim prompt md | required |
| `--model` | `pro` → `gemini-3-pro-image-preview`, anything else → `gemini-2.5-flash-image-preview` | `pro` |
| `--aspect-ratio` | Output canvas aspect ratio | `16:9` |

`GEMINI_API_KEY` must be set in the environment. If it is not, the script exits non-zero with a verbatim error. There is no MCP dependency and no fallback — the same path runs in the local CLI and in sandbox/cloud environments.

`[partner-slug]` = lowercase kebab-case of the partner name.

If the script exits non-zero, stop and tell the user the partner logo could not be prepared. Do not use the raw logo unless the user explicitly approves, because the card requires a white transparent partner logo.

### Alpha check and fix

After `cleanup_logo.js` returns, verify the output has a real alpha channel:

```
sips -g hasAlpha "[output_path]"
```

If the result is `hasAlpha: no`, Gemini Image baked a checkerboard pattern as actual pixels instead of creating transparency. Fix it before continuing:

```
python3 ".claude/skills/linkedin-partnership-card/scripts/fix_logo_transparency.py" \
  "[output_path]"
```

This edits the file in place. Three passes: (1) luminance-binarize white-vs-dark, (2) hard-clamp any sub-200 alpha to zero — this kills antialiasing noise that would otherwise defeat the bbox crop, (3) tight-crop the canvas to the artwork bbox so the template's max-width / max-height variables fill the slot instead of scaling around dead padding. It is safe to run even if the logo is already correct (re-saves as RGBA with a real alpha channel).

The tight crop is what lets the tier ladder in step 7 work for wordmark+logomark composites. Without it, a 1376×768 canvas with most of the artwork concentrated in a 1325×327 strip would render with the wordmark filling only a fraction of the available `--partner-max-h`.

## Output Paths

For a campaign at `[campaign-folder]`:

```
[campaign-folder]/
├── working/
│   ├── assets/
│   │   └── partner-logo-white-transparent.png
│   └── linkedin-partnership-card_20260501_partner-name.html
└── export/
    ├── linkedin-partnership-card_20260501_partner-name.png
    └── linkedin-partnership-card_20260501_partner-name@2x.png
```

Use a partner-specific logo filename when multiple partnership cards share one campaign folder:

```
[campaign-folder]/working/assets/acme-logo-white-transparent.png
```

## Node dependencies

The skill uses `@google/genai` (for `cleanup_logo.js`) and `puppeteer` (for `export_card.js`). `node_modules/` is not shipped with the skill. First-time install pulls both:

```
cd ".claude/skills/linkedin-partnership-card/scripts"
npm install
```

After that the install persists locally. Re-run only if `package.json` changes.

## QA Checklist

- [ ] Source partner logo was supplied by the user as an absolute path.
- [ ] Partner logo was processed with `scripts/cleanup_logo.js` (Gemini Image API, `gemini-3-pro-image-preview`) using the verbatim prompt at `references/nano-banana-logo-cleanup-prompt.md`.
- [ ] `sips -g hasAlpha` on the prepared logo returns `hasAlpha: yes`. If not, run `scripts/fix_logo_transparency.py` before continuing.
- [ ] `fix_logo_transparency.py` reported a tight crop (output canvas size noticeably smaller than the input), confirming the alpha-clamp + bbox crop ran — important for wordmark+logomark composites.
- [ ] Prepared partner logo is white artwork on a transparent background.
- [ ] Generated HTML uses `templates/card.html`.
- [ ] No headline, body copy, CTA, badge, or caption was added.
- [ ] hyperexponential wordmark appears on the left.
- [ ] Partner logo appears on the right.
- [ ] Partner wordmark cap-height visually matches `hyperexponential` within ~2px (use the tier ladder under "Optical sizing target" if it doesn't).
- [ ] Inner-edge gap from hx wordmark to "+" is visually equal to gap from "+" to partner logo.
- [ ] "+" mark is centered between the logos and white.
- [ ] Background is the flat-navy dot-field PNG embedded inline; no glow or vignette is visible.
- [ ] PNG export ran and both 1x and 2x files exist in `export/`.
- [ ] The 1x PNG is exactly 1200x675.
- [ ] The 2x PNG is exactly 2400x1350.
