---
name: linkedin-customer-quote-card
description: Generate one or more customer quote cards for hyperexponential using the Figma 2026 reference at node 1480:22766. Use when the user asks to create, build, design, render, or export customer quote/testimonial graphics. For each quote row, outputs 3 variants (Blue, Burgundy, Green), each at 1080x1080, with exact composition from the design system reference. Single-row and multi-row invocations follow the same pipeline.
user-invocable: true
requires: [design-system]
metadata:
  version: 1.3.0
---

# linkedin-customer-quote-card skill

Produces **3 variants per quote row** of the customer quote card at **1080x1080** and exports them to PNG. The layout must match Figma file `8sGAsifGavCoNlX3J8v8U1`, node `1480:22766` (`Type=Blue`, `Type=Burgundy`, `Type=Green`) exactly. The skill accepts either a single quote (back-compat) or a list of N quote rows; the pipeline runs once per row.

Read [`README.md`](README.md) before composing. It contains the visual spec for all 3 patterns, output naming, and QA checklist. The Nano Banana avatar prompt lives inline in Step 3 below.

## When to use

User says any of: "make a customer quote card", "create a testimonial card", "build the quote graphic", "export customer quote variants", "generate blue/burgundy/green quote cards".

## Pipeline

### 1. Collect inputs (required)

The skill takes a **list of quote rows** (N ≥ 1). Each row is independent and runs through Steps 3–6 in turn. The orchestrator supplies the list directly; ad-hoc invocations may supply a single row. The Perkins routine builds the list from `download-from-notion`'s Mode 4 manifest — either the legacy `Customer Quotes` child DB (one row per quote) or, on a converted playbook, the per-step form-inputs database read with `--explode-groups` (one submission row whose `Customer Quote 1..N: …` numbered columns are exploded into the same per-row shape). Either way each row carries `quote_text`, `customer_name`, `customer_title`, `company_name`, and `avatar_local_path`, so this skill consumes them identically.

Required per-row fields:

- **Quote text**
- **Customer name** (appears on the card)
- **Company name** (appears on the card)
- **Customer avatar path** (absolute path to LinkedIn photo or attached image)

Optional per-row fields:

- **Customer title** (e.g. "Chief Underwriting Officer") — rendered as its own line between the name and company. Omitted entirely if not provided.
- **Order** (integer; controls render order. Defaults to the row's index in the input list. Lower runs first.)

Top-level (shared across all rows in one invocation):

- **Campaign folder** (absolute path under `Projects/Rev Ops Pipelines/campaigns/`). Skill writes to `[campaign-folder]/working/` and `[campaign-folder]/export/`.
- **Filename date** in `YYYYMMDD` format (defaults to today).
- **Pattern preference** (`blue`, `burgundy`, `green`; default is all 3 per row).
- **Avatar vertical crop hint** (default `18%` top focal point).

**Back-compat:** if the caller supplies a single set of inputs (`Quote text` / `Customer name` / `Company name` / `Customer avatar path`) instead of a list, treat it as a 1-row list with `Order = 1`.

**Iteration semantics.** Steps 3–6 run **once per row**. Per row, Step 3 produces 3 cleaned avatars (one per variant), Step 4 produces 3 HTMLs, and Step 6 exports 6 PNGs (3 × 1x + 3 × @2x). With N rows you produce 3N HTMLs and 6N PNGs in one campaign folder.

### 2. Read brand context

This skill declares `requires: [design-system]`. Read the sibling design-system skill before composing:

1. [`../design-system/SKILL.md`](../design-system/SKILL.md)
2. [`../design-system/README.md`](../design-system/README.md)

Apply brand colors, typography (`fonts-inline-card.css`), and voice rules.

### 3. Prepare the customer avatar (Gemini Image API)

**For each quote row in the input list**, invoke `scripts/cleanup_headshot.js` via Bash **once per variant** (3 calls per row; 3N total). The script calls Google's Gemini Image API directly via `@google/genai` — no MCP server is involved, so this runs identically in the local CLI and in sandbox/cloud environments. The `GEMINI_API_KEY` env var must be set; if it is not, the script exits non-zero with a verbatim error.

The verbatim prompt with the `{{BACKDROP_INSTRUCTION}}` placeholder lives in [`references/nano-banana-headshot-cleanup-prompt.md`](references/nano-banana-headshot-cleanup-prompt.md) — the script loads it from disk and substitutes the placeholder based on the `--gradient` flag.

`mkdir -p [campaign-folder]/working/assets/` before calling (once for the run; the directory is shared across rows).

Per-row, per-variant filename convention: `[customer-slug]_q[ORDER]-avatar-clean-[variant].png`, where `[customer-slug]` is the kebab-case `Customer name` for the row and `[ORDER]` is zero-padded to 2 digits (`q01`, `q02`, …). For a single-row back-compat invocation the `_q01` segment is still emitted so file naming is consistent across run sizes.

Then for each row × variant, run (using **absolute paths** for `--input`, `--output`, and `--prompt-file`):

```
node ".claude/skills/linkedin-customer-quote-card/scripts/cleanup_headshot.js" \
  --input "<absolute path to this row's customer avatar>" \
  --output "[campaign-folder]/working/assets/[customer-slug]_q[ORDER]-avatar-clean-blue.png" \
  --prompt-file ".claude/skills/linkedin-customer-quote-card/references/nano-banana-headshot-cleanup-prompt.md" \
  --model pro \
  --aspect-ratio 1:1 \
  --gradient "#0F1924"
```

Repeat for `burgundy` (`--gradient "#330817"`, `…_q[ORDER]-avatar-clean-burgundy.png`) and `green` (`--gradient "#002625"`, `…_q[ORDER]-avatar-clean-green.png`).

Each `--gradient` hex is the variant's avatar tile color, so the baked backdrop matches the tile exactly with no visible seam inside the tile.

Rules:

- Cleanup is **photo-only**: square crop, neutralize background to the per-variant tile color, normalize exposure. Never alter the subject's likeness, skin tone, hair, glasses, or clothing.
- If `cleanup_headshot.js` exits non-zero for any variant on any row, surface the verbatim stderr and stop the entire run. Do not fall back to the raw photo, do not skip the variant, do not continue the pipeline, do not retry silently. Do not advance to the next row.
- If `require('@google/genai')` fails, run `cd ".claude/skills/linkedin-customer-quote-card/scripts" && npm install` once, then retry.

### 4. Generate 3 HTML variants per row

**For each quote row**, start from [`templates/card.html`](templates/card.html) and produce 3 HTMLs (one per `patternType`). With N rows this step writes 3N HTML files.

**Asset → variant mapping** (PNGs live in [`assets/`](assets/)):

| Variant   | Background PNG          |
|-----------|-------------------------|
| `blue`    | `Customer-Quote.png`    |
| `burgundy`| `Customer-Quote-1.png`  |
| `green`   | `Customer-Quote-2.png`  |

For each variant, read the mapped PNG as bytes and base64-encode it. Inject the resulting `data:image/png;base64,...` string into the `{{BG_IMAGE_DATA_URI}}` placeholder so the HTML is self-contained (no external file references at export time).

Then for this row × this variant:
- **`{{FONT_FACE_BLOCK}}`** — paste the **full contents** of [`../design-system/tokens/fonts-inline-card.css`](../design-system/tokens/fonts-inline-card.css). This inlines all `@font-face` rules (FFF Acid Grotesk, weights 300/350/400/500) so the output HTML is fully self-contained. **Required** — if this placeholder is left unfilled the card silently falls back to Arial. Note: the quote and name/company text use **weight 350 (Book)**, matching the Figma spec. The inlined subset now declares Book at 350, so `350` resolves to the Book face exactly (verified via `design-system/scripts/verify_fonts_inline.js`) — the old `400` workaround is no longer needed.
- Inject the cleaned avatar for **this row × this variant** (`{{AVATAR_SRC}}` → `[customer-slug]_q[ORDER]-avatar-clean-blue.png` / `-burgundy.png` / `-green.png` from step 3). Each variant uses its own per-variant PNG so the baked backdrop matches the tile color.
- Fill quote markup (`{{QUOTE_HTML}}`), customer name, and company name **from this row** — never from another row in the same run.
- `{{QUOTE_HTML}}` must include `<span class="accent">...</span>` around the emphasized ending clause.
- Ensure the final closing quotation mark matches the color of the final sentence (if the ending clause is accented, the closing quote is accented too).
- **`{{CUSTOMER_TITLE}}`** — when a customer title is supplied, render the name line with a trailing comma (e.g. `Sarah Chen,`) and put the title on its own line via `{{CUSTOMER_TITLE}}` (e.g. `Chief Underwriting Officer`). When no title is supplied, **delete the entire `<p class="title">{{CUSTOMER_TITLE}}</p>` line** — never emit an empty title element.
- Apply one of `theme-blue`, `theme-burgundy`, `theme-green` using `{{PATTERN_TYPE}}`.
- Keep layout fixed to Figma: hx logomark pinned **top-right**, the quote **top-aligned** so its first line sits on the **same line as the logomark**, bottom avatar block + name / title / company.
- Quote typography: default quote size **48px**, weight 400 (Book), line-height 1.1. The quote↔logomark gap is **120px**; the logomark is **63px** wide (~57px tall).

The template uses theme classes to switch the solid background color (used as a fallback under the PNG) and the accent / avatar-tile colors; do not alter structure or element sizing. The top-right brand mark is the inlined dark-mode pair of `hx-logomark.svg` (white mark only — no wordmark) — do not substitute it.

### 5. Write outputs

For each row × variant:
- HTML → `[campaign-folder]/working/customer-quote_[YYYYMMDD]_[CUSTOMER-SLUG]_q[ORDER]-[patternN].html`

Where `[ORDER]` is the zero-padded 2-digit order and `[patternN]` is `blue`, `burgundy`, or `green`. With N rows this produces 3N HTML files.

### 6. Export PNGs

Run the exporter for each HTML file:
```
node "Projects/Rev Ops Pipelines/.claude/skills/linkedin-customer-quote-card/scripts/export_card.js" \
  "<absolute path to html>" \
  "<campaign-folder>/export"
```

This produces 6N files total (N rows × 3 patterns × {1x + @2x}). Exported PNGs follow the same `customer-quote_[YYYYMMDD]_[CUSTOMER-SLUG]_q[ORDER]-[patternN]` stem (plus `@2x` suffix on the 2× export). The script screenshots only the `.card` element at exact 1080x1080.

The exporter also enforces variant consistency — it exits non-zero if a card's `theme-<variant>` class doesn't match the avatar's `-<variant>.png` suffix (e.g. a blue card referencing the burgundy headshot), so a mis-wired `{{AVATAR_SRC}}` fails fast instead of shipping silently.

**The `@2x` PNG (2160×2160) is the primary deliverable** — share/post that one for a crisp result. The 1x (1080×1080) is a secondary/preview asset. (LinkedIn downscales gracefully; the @2x avoids the soft, low-res look.)

If puppeteer not installed:
```
cd "Projects/Rev Ops Pipelines/.claude/skills/linkedin-customer-quote-card/scripts"
npm install
```

### 7. Verify

Open the **@2x PNGs** (the deliverable) and check, for every row × variant in the run:
- Each `@2x` is exactly 2160x2160 (1x is 1080x1080); both must be sharp, not soft.
- **Fonts loaded:** text renders in FFF Acid Grotesk, **not Arial** (geometric `a`/`t`/`G`; quote + name + title are Acid Grotesk Book). If it looks like Arial, `{{FONT_FACE_BLOCK}}` was not filled — fix Step 4 and re-export.
- Quote text, customer name, and company name match **the same row** in the input list — verify by spot-checking each `q[ORDER]` triplet against the corresponding row.
- Composition matches Figma `1480:22766` (quote block, logomark location, avatar tile size/position, name baseline).
- **Name / title / company block:** name line ends with a comma when a title is present, the title sits on its own line and is not split awkwardly (no stranded last word), company is in the accent color. When no title was supplied, only name + company appear (no blank line).
- **Logomark** sits at the **top-right** of the card (~63×57px), **aligned with the first quote line** (the quote is top-aligned).
- Avatar has a clean, **flat** dark backdrop matching the variant's tile color (`#0F1924` blue / `#330817` burgundy / `#002625` green) and correct focal crop (head/eyes not clipped). **Reject any render that still shows the source studio backdrop** (gradient/vignette/lighter grey) — that means `cleanup_headshot.js` was skipped or ineffective; re-run Step 3.
- No stripping artifacts, halos, or backdrop bleed around hair/shoulders; no visible seam between the baked headshot backdrop and the surrounding tile.
- Background PNG matches the selected variant; accent text and avatar tile match the selected theme.
- Top-right shows the `hx-logomark` (dark-mode pair) — mark only, fully white, not clipped or microscopic.
- Typography and spacing follow design-system rules.
- All 3 variants are generated.

**Hard rules**
- Always output **all 3 pattern variants per row** unless user explicitly requests fewer.
- For a multi-row run, process rows strictly in `Order` (then input-list index as tiebreak). Do not interleave rows; finish a row's 3 variants before starting the next row. This keeps the `TASK_RESULT` artifact list ordered for the orchestrator.
- Canvas is always 1080x1080.
- Use exact quote block sizing and avatar treatment from the Figma reference.
- The quote is top-aligned (first line on the same line as the top-right logomark) by design — open space **below** the quote, between it and the avatar block, is intended, not a sparse-composition defect. Only reduce `--quote-size` below 48px if a long quote would otherwise clip.
- Avatar must be processed via `scripts/cleanup_headshot.js` (Gemini Image API) once per variant with `--gradient` set to that variant's tile hex. No transparency, no MCP dependency.
- Use only the approved themes (`blue`, `burgundy`, `green`) and the matching background PNG from [`assets/`](assets/). Do not regenerate or substitute the background pattern.
- Top-right mark is the inlined dark-mode pair of `hx-logomark.svg` (white) — do not swap for the lockup or another logo asset.
- Do not add company logos, CTA copy, or extra badges. (A customer job-title line is supported — see Step 1 / Step 4.)
- Do not modify existing skills (partnership-card, webinar-promo-card, etc.).
- Self-contained HTML (inline CSS, fonts where possible, embedded patterns).

## Out of scope
- Figma generation or write-back.
- Alternate aspect ratios or formats.
- Cards without a customer quote + avatar + company.
- Modifying the reference partnership or webinar skills.

See [`README.md`](README.md) for full visual specs, color palettes extracted from the SVG, and reference layout details. The headshot cleanup prompt template is in [`references/nano-banana-headshot-cleanup-prompt.md`](references/nano-banana-headshot-cleanup-prompt.md).
