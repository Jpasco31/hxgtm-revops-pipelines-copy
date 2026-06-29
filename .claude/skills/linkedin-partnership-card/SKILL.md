---
name: linkedin-partnership-card
description: Generate a logo-only LinkedIn partnership announcement card for hyperexponential at 1200x675. Use when the user asks to create, build, design, render, or export a LinkedIn partnership card, partner announcement image, alliance announcement card, or co-marketing logo card. Always places the hyperexponential wordmark on the left and the supplied partner logo on the right, converting the partner logo to a white transparent asset with the Gemini Image API before export.
user-invocable: true
requires: [design-system]
metadata:
  version: 1.0.0
---

# linkedin-partnership-card skill

Produces a single logo-only LinkedIn partnership announcement card at **1200x675** and exports it to PNG. The layout is fixed: hyperexponential on the left, partner logo on the right, centered white "+" mark between them, dark blue SVG-inspired background.

Read [`README.md`](README.md) before composing. It contains the visual spec, the exact Gemini Image logo prompt, output naming, and QA checklist.

## When to use

User says any of: "make a LinkedIn partnership card," "create a partner announcement image," "build the partnership logo card," "export the co-marketing card," "make this logo white on the hx partnership card."

## Pipeline

### 1. Collect inputs

Ask for whatever is missing. Required fields:

- **Partner name** for alt text and filenames.
- **Partner logo path** as an absolute path to the source logo image.
- **Campaign folder** as an absolute path, typically under `Projects/Rev Ops Pipelines/campaigns/`. The skill writes outputs into `[campaign-folder]/working/` and `[campaign-folder]/export/`.

Optional:

- **Filename date** in `YYYYMMDD` format. If omitted, use today's date.

### 2. Read brand context

This skill declares `requires: [design-system]`. Read the sibling design-system skill before composing:

1. [`../design-system/SKILL.md`](../design-system/SKILL.md)
2. [`../design-system/README.md`](../design-system/README.md)

Use the hyperexponential wordmark from [`../design-system/assets/logo/hx-wordmark.svg`](../design-system/assets/logo/hx-wordmark.svg). Do not substitute the logomark.

### 3. Prepare the partner logo

Invoke `scripts/cleanup_logo.js` via Bash. The script calls Google's Gemini Image API directly via `@google/genai` — no MCP server is involved, so this runs identically in the local CLI and in sandbox/cloud environments. The `GEMINI_API_KEY` env var must be set; if it is not, the script exits non-zero with a verbatim error.

The verbatim prompt lives in [`references/nano-banana-logo-cleanup-prompt.md`](references/nano-banana-logo-cleanup-prompt.md) — the script loads it from disk.

Create `[campaign-folder]/working/assets/` before calling, then run:

```
node ".claude/skills/linkedin-partnership-card/scripts/cleanup_logo.js" \
  --input "<absolute path to the supplied partner logo>" \
  --output "<campaign-folder>/working/assets/<partner-slug>-logo-white-transparent.png" \
  --prompt-file ".claude/skills/linkedin-partnership-card/references/nano-banana-logo-cleanup-prompt.md" \
  --model pro \
  --aspect-ratio "16:9"
```

`[partner-slug]` = lowercase kebab-case of the partner name.

Rules baked into the prompt:

- Keep the partner's original logo shape and proportions.
- Convert visible logo artwork to solid white.
- Remove the background so the output is transparent.
- Do not add shadows, outlines, borders, taglines, icons, or extra text.

Error posture: if `cleanup_logo.js` exits non-zero, surface the verbatim stderr and stop. Do not fall back to the raw logo, do not retry silently, do not continue the pipeline. The card requires a white transparent partner logo.

After the call, run the alpha check and fix described in [`README.md`](README.md). Gemini Image frequently bakes a checkerboard as pixel data instead of creating real transparency (`hasAlpha: no`). Always run `sips -g hasAlpha` on the output and, if needed, fix it with `scripts/fix_logo_transparency.py` before moving to step 4. The fix script also tight-crops the canvas to the artwork bbox, which is what lets the tier ladder in step 7 work for wordmark+logomark composites.

### 4. Compose the card

Start from [`templates/card.html`](templates/card.html) and fill the placeholders:

- `{{PARTNER_LOGO_SRC}}` with the **relative path** `assets/[partner-slug]-logo-white-transparent.png`. Do not use an absolute path or `file://` URL — the HTML is always written to `[campaign-folder]/working/` and the asset is always at `[campaign-folder]/working/assets/`, so the relative reference resolves cleanly for Puppeteer.
- `{{PARTNER_LOGO_ALT}}` with `[Partner name] logo`.
- `{{BACKGROUND_DATA_URI}}` with a `data:image/png;base64,<...>` URI built from [`assets/Partnership-announcement.png`](assets/Partnership-announcement.png). On macOS:

  ```
  printf 'data:image/png;base64,'; base64 -i ".claude/skills/linkedin-partnership-card/assets/Partnership-announcement.png"
  ```

  Inline the full string (no line breaks) so the working HTML stays self-contained and survives being copied around.

The template already embeds the approved hyperexponential wordmark from `../design-system/assets/logo/hx-wordmark.svg` and contains the fixed card geometry, background slot, divider, and logo slots. Do not add copy fields, headlines, CTA text, badges, or captions.

### 5. Write outputs

HTML -> `[campaign-folder]/working/linkedin-partnership-card_[YYYYMMDD]_[PARTNER-SLUG].html`

`[PARTNER-SLUG]` = lowercase kebab-case of the partner name, alphanumeric plus hyphens.

### 6. Export PNG

Run the exporter:

```
node ".claude/skills/linkedin-partnership-card/scripts/export_card.js" \
  "<absolute path to the html written in step 5>" \
  "<campaign-folder>/export"
```

Saves `[slug].png` at 1200x675 and `[slug]@2x.png` at 2400x1350. The script screenshots only the `.card` element.

If puppeteer is not installed yet, run:

```
cd ".claude/skills/linkedin-partnership-card/scripts"
npm install
```

### 7. Verify

Open the 1x PNG and check:

- The 1x PNG is exactly 1200x675.
- The 2x PNG is exactly 2400x1350.
- hyperexponential is on the left and partner is on the right.
- Partner wordmark cap-height visually matches `hyperexponential` within ~2px (see Optical balance check below for the tier ladder).
- Both logos are white.
- The partner logo background is transparent before placement.
- The "+" mark is centered between the two logos, with equal inner-edge gaps to each logo (it sits at the midpoint of the lockup, not necessarily the canvas midline).
- Background matches the flat-navy dot-field PNG; no radial glow, no vignette, no gradients.
- No copy, CTA, extra marks, or borders were added.

**Optical balance check.** Match the partner wordmark's *cap-height* to `hyperexponential` (~40px in the export), not the partner image's bounding-box height. Different logo compositions have very different cap-height-to-bbox ratios — a wordmark-only logo has bbox ≈ cap-height, but a wordmark+logomark composite has bbox much taller than its wordmark, so a single image-height cap can't work for both.

Pick a starting `--partner-max-h` from the ladder, render once, eyeball the cap-heights against `hyperexponential`, then step up by 8px until they match within ~2px. If the partner reads taller than hx, step back down.

| Partner logo type                                              | Starting `--partner-max-h` | Typical landing |
|----------------------------------------------------------------|----------------------------|-----------------|
| Wordmark only, cap-height ≥ 70% of bbox height                 | `45px` (default)           | 45–56px         |
| Wordmark only, cap-height 50–70% of bbox height (e.g. Allianz wordmark alone) | `56px`            | 56–64px         |
| Wordmark + logomark, balanced (wordmark ≥ 60% of bbox)         | `64px`                     | 64–72px         |
| Wordmark + logomark, mark-dominant (wordmark < 60% of bbox)    | `88px`                     | 80–96px         |
| Logomark only or icon-dominant                                 | `72px`                     | 64–80px         |

Upper sanity bound: **120px**. Beyond that the partner reads as the primary brand and the lockup inverts. Don't widen `--partner-max-w` — `object-fit: contain` handles aspect.

Apply via inline style on the `<img class="partner-logo">` tag, e.g. `style="--partner-max-h: 88px;"` for a wordmark+logomark, mark-dominant partner.

## Hard rules

- Canvas is always 1200x675.
- hyperexponential wordmark is always left.
- Partner logo is always right.
- Both logos are white and render at 45px tall by default.
- Partner logo must be prepared as a transparent PNG via `scripts/cleanup_logo.js` (Gemini Image API), followed by `scripts/fix_logo_transparency.py` to clamp alpha noise and tight-crop to the artwork bbox.
- Background is the approved flat-navy dot-field PNG ([`assets/Partnership-announcement.png`](assets/Partnership-announcement.png)), embedded inline as a base64 data URI. No radial glow, no vignette, no gradients.
- The centered "+" mark stays white.
- Output HTML must be self-contained except for the local prepared partner-logo image reference.
- Do not modify the existing `webinar-promo-card` skill.

## Out of scope

- Webinar, event, speaker, customer quote, paid ad, and product announcement cards.
- Alternate aspect ratios.
- Cards with headline, body copy, CTA, badges, or partner descriptions.
- Figma write-back or Figma file generation.
