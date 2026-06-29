# linkedin-customer-quote-card reference

The terse pipeline lives in [`SKILL.md`](SKILL.md). This file is the source of truth for canvas size, theme palettes, quote/avatar composition, output paths, and QA checklist. The Gemini Image cleanup prompt template lives in [`references/nano-banana-headshot-cleanup-prompt.md`](references/nano-banana-headshot-cleanup-prompt.md).

## Canvas

- **Reference source:** Figma file `8sGAsifGavCoNlX3J8v8U1`, node `1480:22766`.
- **Per-variant size:** 1080 x 1080.
- **Variants:** `Type=Blue`, `Type=Burgundy`, `Type=Green`.
- **File targets:** For each variant, PNG at 1x (1080x1080) and 2x (2160x2160). Total of 6 files. **The `@2x` (2160x2160) is the primary deliverable** — share that one; the 1x is a preview.

## Visual spec

- The frame contains 3 stacked variants; each variant uses the same layout, a pre-rendered background PNG, and a matching theme color system for accent + avatar tile.
- The top-right brand mark is the dark-mode pair of `hx-logomark.svg` (white "hx" mark only — no wordmark), inlined into the HTML.
- Layout is fixed:
  - Top row: quote block (left, **top-aligned** so its first line sits on the **same line as the logomark**) + hx logomark (right, pinned **top-right** to outer padding, ~63×57px).
  - Bottom row: 280x280 avatar tile (left) + name / optional title / company text (right).
  - Outer padding: 80px; column gap between top region and bottom row: 80px.
  - Top-row gap (quote ↔ logomark): 120px (`justify-content: space-between` pins the lockup to the right edge).
  - Top row flex-grows to fill the space above the bottom row; the quote is top-aligned so open space falls below it.
  - Bottom-row gap: 32px.

### Background assets

The dotted-pattern background is **not generated programmatically**. Each variant uses a pre-rendered 1080x1080 PNG from [`assets/`](assets/), base64-inlined into the HTML so the export stays self-contained.

| Variant   | Background PNG          |
|-----------|-------------------------|
| `blue`    | `Customer-Quote.png`    |
| `burgundy`| `Customer-Quote-1.png`  |
| `green`   | `Customer-Quote-2.png`  |

### Theme colors

The solid color is the fallback under the PNG (and is used directly for the avatar tile and the accent text spans).

- **Blue:** `bg #1D2733`, `accent #A6C4EE`, `avatar bg #0F1924` (a darker near-black blue than the card bg, framing the headshot through depth, mirroring the burgundy/green darker-tile pattern).
- **Burgundy:** `bg #400A20`, `accent #EEA6C4`, `avatar bg #330817` (a deeper wine than the card bg, mirroring green's darker-tile framing pattern; kept above the `#260814` threshold that triggered Gemini's teal fallback). Accent is a soft rose in the same hue family as the burgundy bg, replacing the older coral `#EE6C5B`.
- **Green:** `bg #013F3C`, `accent #59BBB7`, `avatar bg #002625` (a darker teal than the card bg, framing the headshot).

### Typography

- Quote: default 48px, weight **350 (Book)**, line-height 1.1, white text with accent span for the emphasized clause. (Figma specs this Book weight as `350`; the inlined subset now declares Book at 350, so `font-weight: 350` resolves to Book exactly — no more rounding to Light or pinning to 400.)
- Quote is top-aligned (first line on the same line as the top-right logomark); open space below it (toward the avatar block) is intended.
- Name / title / company: 36px, weight 350 (Book), line-height 1.2. Name + title are white; company is the accent color.
- Font stack: `"FFF Acid Grotesk", "Arial", sans-serif`.
- **Fonts are inlined** via `{{FONT_FACE_BLOCK}}` (full contents of [`../design-system/tokens/fonts-inline-card.css`](../design-system/tokens/fonts-inline-card.css)) so the HTML is self-contained. If this block is missing the card silently renders in Arial — always confirm Acid Grotesk in the exported PNG.

## Headshot cleanup (Gemini Image API)

Cleanup runs via [`scripts/cleanup_headshot.js`](scripts/cleanup_headshot.js), which calls Google's Gemini Image API directly through `@google/genai` (no MCP server). Requires `GEMINI_API_KEY`. The verbatim prompt with the `{{BACKDROP_INSTRUCTION}}` placeholder lives in [`references/nano-banana-headshot-cleanup-prompt.md`](references/nano-banana-headshot-cleanup-prompt.md).

The skill calls the script **3 times per customer**, once per variant, passing the variant's avatar tile hex via `--gradient` so each cleaned PNG bakes an exact tile-matching backdrop:

| Variant   | `--gradient` value | Output filename                                |
|-----------|--------------------|------------------------------------------------|
| `blue`    | `#0F1924`          | `[customer-slug]-avatar-clean-blue.png`        |
| `burgundy`| `#330817`          | `[customer-slug]-avatar-clean-burgundy.png`    |
| `green`   | `#002625`          | `[customer-slug]-avatar-clean-green.png`       |

See [`SKILL.md`](SKILL.md) Step 3 for the exact command, settings, and the hard-fail-on-error rule (no raw-photo fallback).

## Avatar crop handling

- Avatar container is fixed at `280x280` with `8.512px` radius.
- Use `object-fit: cover`.
- Default vertical crop target is `18%` from top (`object-position: 50% 18%`).
- If forehead/hairline is clipped, adjust via inline `--avatar-y` on `.card` (example: `--avatar-y: 12%`).

## Output Naming

- HTML: `customer-quote_YYYYMMDD_[customer-slug]_q[ORDER]-[variant].html`
- PNG: `customer-quote_YYYYMMDD_[customer-slug]_q[ORDER]-[variant].png` (+ `@2x`)

Where:
- `[customer-slug]` = lowercase kebab-case of the row's `Customer name`.
- `[ORDER]` = the row's `Order` value, zero-padded to 2 digits (`01`, `02`, …). For a single-row back-compat invocation, `[ORDER]` is `01`.
- `[variant]` = `blue` / `burgundy` / `green`.

A multi-row run writes 3N HTMLs and 6N PNGs (3 variants × {1x, @2x}) to one campaign folder.

## QA Checklist

For all 3 exported PNGs per row (check the `@2x` deliverable):
- Exact 1080x1080 dimensions (2160x2160 for `@2x`); both sharp, not soft.
- **Fonts loaded:** text is FFF Acid Grotesk **Book**, not Arial. If it looks like Arial, `{{FONT_FACE_BLOCK}}` was not filled.
- Quote layout and avatar placement match Figma node `1480:22766`.
- Top-right hx logomark (dark-mode pair from `hx-logomark.svg`) is present, fully white, not clipped or microscopic, pinned to the **top-right** (~63×57px) **aligned with the first quote line** (quote top-aligned).
- **Name / title / company:** name line ends with a comma when a title is present; the title sits on its own line and is not awkwardly split (no stranded last word); company is in the accent color. No empty title line when none was supplied.
- Background PNG corresponds to the selected variant; accent text and avatar tile colors are correct (no palette mixing).
- Avatar backdrop is a **flat** fill matching the variant's tile color with no visible seam inside the tile; no stripping/halo artifacts around hair/shoulders; subject looks natural. Reject any render still showing the source studio backdrop (gradient/vignette/lighter grey).
- Typography follows design-system (sizes/weights/line-heights above).
- Optical balance across elements; no clipping.
- All 3 variants produced per row; all rows present in `Order` sequence.
- Per-row content (quote text, customer name, company name) matches the originating row in the input list — no cross-contamination across rows.

When fidelity is uncertain, re-check against Figma node `1480:22766` via `get_design_context` / `get_screenshot` before final export.

See `SKILL.md` for the full pipeline and hard rules.
