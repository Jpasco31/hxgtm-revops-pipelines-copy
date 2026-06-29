# webinar-promo-card — reference

The terse pipeline lives in [`SKILL.md`](SKILL.md). This file holds the longer specs, the gradient recipes, the headshot cleanup prompt, and the per-variant layout details.

The output is a LinkedIn-format card (1200x627, 1.91:1) used for webinar / virtual-event / panel promotion. The skill name describes the use case (webinar promo); the output file naming preserves "linkedin-card" because that describes the canvas format.

## Canvas

- **Format:** LinkedIn 1.91:1 feed card.
- **Pixel size:** 1200 x 627.
- **Border radius on the card:** 4px.
- **Min size:** 640 x 360 (do not produce smaller).
- **File targets:** PNG at 1x (1200x627) and 2x (2400x1254). PNG only — JPG compression eats the gradient.

## Gradient picker

| Gradient | Base color | PNG asset | Use it for |
|---|---|---|---|
| **Wine** *(default)* | `#3F0A20` (`--wine`) | [`assets/Burgundy 01.png`](assets/Burgundy%2001.png) | Flagship, executive, high-authority webinars. The default unless the brief says otherwise. |
| **Ink** | `#1C2733` (`--ink`) | [`assets/Dark blue 01.png`](assets/Dark%20blue%2001.png) | Technical, product, engineering-led sessions. |
| **Forest** | `#002625` | [`assets/Deep Forest 01.png`](assets/Deep%20Forest%2001.png) | Community, partnership, ecosystem, customer-led sessions. |

Each color ships three texture variants (`01` / `02` / `03`) in `assets/` — the table above shows the `01` default. The brief's `variant` field selects which one; it defaults to `01` when omitted, so all nine PNGs are selectable. Variant changes only the background texture — the base color hex is the same across a color's three variants. White type only on all three colors. Coral (`--coral`) is forbidden on gradient — hard brand rule.

Asset paths and substitution recipe: see [`references/gradient-assets.md`](references/gradient-assets.md).

Grain + vignette layers are always on. CSS: [`references/grain-vignette.css`](references/grain-vignette.css).

## Type spec (all variants)

All sizes are in CSS px at the 1200x627 canvas. Body type uses `FFF Acid Grotesk` (fallback `Arial`). The meta/date line uses `JetBrains Mono` (fallback `ui-monospace, SFMono-Regular, Menlo, monospace`).

| Element | Size | Weight | Family | Line-height | Letter-spacing | Color |
|---|---|---|---|---|---|---|
| Logo lockup (height) | 32px (1-speaker: 30px) | — | SVG outlined paths | — | — | `#FFFFFF` (Neutrals/50) |
| Meta (1 / 2-speaker) | 20px | 300 | JetBrains Mono | 1.1 | 0 | `#C6C7C8` (Neutrals/400) |
| Meta (3-speaker) | 20px | 300 | JetBrains Mono | 1.1 | 0 | `#C6C7C8` (Neutrals/400) |
| Meta (4-speaker) | 20px | 300 | JetBrains Mono | 1.1 | 0 | `#C6C7C8` (Neutrals/400) |
| Headline (1-speaker) | 48px | 350 | FFF Acid Grotesk | 1.1 | — | `#FFFFFF` (Neutrals/50) |
| Headline (2-speaker) | 76px | 350 | FFF Acid Grotesk | 1.1 | — | `#FFFFFF` (Neutrals/50) |
| Headline (3-speaker) | 64px | 350 | FFF Acid Grotesk | 1.1 | — | `#FFFFFF` (Neutrals/50) |
| Headline (4-speaker) | 64px | 350 | FFF Acid Grotesk | 1.1 | — | `#FFFFFF` (Neutrals/50) |
| Subtitle (1-speaker) | 32px | 350 | FFF Acid Grotesk | 1.1 | — | `#C6C7C8` (Neutrals/400) |
| Subtitle (2-speaker) | 36px | 350 | FFF Acid Grotesk | 1.1 | — | `#C6C7C8` (Neutrals/400) |
| Subtitle (3-speaker) | 36px | 350 | FFF Acid Grotesk | 1.1 | — | `#C6C7C8` (Neutrals/400) |
| Subtitle (4-speaker) | 36px | 350 | FFF Acid Grotesk | 1.1 | — | `#C6C7C8` (Neutrals/400) |
| Speaker name (1-speaker) | 20px | 350 | FFF Acid Grotesk | 1.1 | — | `#FFFFFF` |
| Speaker name (2-speaker) | 24px | 350 | FFF Acid Grotesk | 1.2 | — | `#FFFFFF` |
| Speaker name (3-speaker) | 20px | 350 | FFF Acid Grotesk | 1.2 | — | `#FFFFFF` |
| Speaker name (4-speaker) | 20px | 350 | FFF Acid Grotesk | 1.2 | — | `#FFFFFF` |
| Speaker role (1-speaker) | 20px | 350 | FFF Acid Grotesk | 1.1 | — | `#B5B6B8` |
| Speaker role (2-speaker) | 24px | 350 | FFF Acid Grotesk | 1.2 | — | `#B5B6B8` |
| Speaker role (3-speaker) | 20px | 350 | FFF Acid Grotesk | 1.2 | — | `#C6C7C8` |
| Speaker role (4-speaker) | 20px | 350 | FFF Acid Grotesk | 1.2 | — | `#C6C7C8` |

The 3-speaker headline is 64px: the headline takes the full width (no right column to compete with) and the visual weight needs to sit above three tiles instead of beside two. Weight and color stay aligned with the 1/2-speaker headline.

**Body text renders Book; the meta line is the one remaining approximation.** Every variant specs Acid Grotesk at `350` (headline, subtitle, name, company) and JetBrains Mono at `300` (meta). `fonts-inline-card.css` now declares Acid Grotesk at 300/350/400/500, so `350` resolves to the **Book** face exactly as designed (verified via `CSS.getPlatformFontsForNode` — see `design-system/scripts/verify_fonts_inline.js`). JetBrains Mono still ships only the 400 Regular cut, so the meta `300` still resolves up to 400 — adding `JetBrainsMono-Light.ttf` at 300 is tracked as a separate, design-gated change.

**Antialiased smoothing is required.** Every template's `html, body` sets `-webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale;`. Without it, white Book text on the dark gradient renders thicker in the Puppeteer/Chromium screenshot and reads as "chunky" — heavier than the Book face actually is. Keep both declarations on all variants.

**Meta line is monospace.** The date/time line uses JetBrains Mono to visually pin it to a "code/data" register that reads as distinct from the body copy. 20px on all variants.

**Subtitle wrap.** The subtitle CSS includes `text-wrap: balance` so multi-line subheads split evenly rather than orphaning the last word. Leave it on.

**Title-stack spacing.** On **1-speaker**, the meta / headline / subtitle stack is a flex column with a literal `gap: 20px` (the left column is a flex column distributed via `justify-content: space-between`). On **2-speaker**, the `.text` stack is a flex column with a literal `gap: 12px` (per the Figma export), and the logo sits 120px above the stack via the `.left` column's `gap: 120px`. On **3-speaker** the `.text` stack is a flex column with `gap: 12px`; the logo and that stack are the two children of a `.top-region` that distributes them via `justify-content: space-between`, so the logo → meta gap is whatever vertical slack remains above the title stack and the 150px speaker row (no literal `margin-top`). **4-speaker** shares the 3-speaker `.top-region` `space-between` behavior verbatim.

## Layout per variant

### 1 speaker
- Flex **row** of two **equal 520px columns**: left (text stack) + right (headshot tile), **40px** gutter.
- Inner content padding: **uniform 60px on all sides**. Geometry: 60 + 520 + 40 + 520 + 60 = 1200; inner height 627 − 120 = **507px**, which both columns fill via `align-items: stretch`.
- Left column is a flex **column** distributed with `justify-content: space-between` into three zones (top → bottom): logo (top, 30px height) → meta + headline + subtitle (middle, `gap: 20px`) → speaker name + company (bottom).
- Headshot tile fills the right column (520x507). Rounded **8px**, no border, base fill `--gradient-base`. The PNG fills the tile via `object-fit: cover` with `object-position: center top` so the top of the head keeps headroom and isn't cropped.
- Name + company sit at the **bottom-left** of the left column. Name 20px `#FFFFFF`, company 20px `#B5B6B8`, `gap: 6px`.
- **Auto-fit:** the headline shrinks from 48px down to 28px (2px steps) if it would wrap past 2 lines or overflow horizontally. The subtitle shrinks from 32px down to 20px (1px steps) if it would wrap past 2 lines. Runs inline before the screenshot.

### 2 speakers (canonical)
- Flex **row** inside uniform **60px** padding with a **40px** gutter: a left text column (~703px, `flex: 1 1 auto`) and a right speaker column (**337px**, `flex: 0 0 337px`). Geometry: 60 + 703 + 40 + 337 + 60 = 1200.
- Left column is a flex **column** with `align-items: flex-start` and a **120px** gap between the logo (top, 30px height) and the meta/headline/subtitle stack; the stack itself is a flex column with `gap: 12px`. The left column is `align-self: stretch` (fills the 507px inner height); the headline reads large at **76px**.
- Right column has two speaker rows stacked, **40px** gap, vertically centered. Each row is `flex: row; align-items: flex-end; gap: 24px` — a **200x200** tile (rounded **8.5px**, no border, base fill `--gradient-base`, PNG `object-fit: cover`) with a name + company block to its right, **bottom-aligned** to the tile. Name 24px `#FFFFFF`, company 24px `#B5B6B8`, `gap: 6px`. Matches the brand-team reference render in `../design-system/assets/reference-renders/Social Media Webinar Promo - 2 Speakers.png`.
- **Auto-fit:** the headline shrinks from 76px down to 40px (2px steps) if it would wrap past 2 lines or overflow horizontally. The subtitle shrinks from 36px down to 22px (1px steps) if it would wrap past 2 lines. Runs inline before the screenshot.

### 3 speakers (different layout)
- **Single-column** layout inside uniform **60px** padding. Headline goes full-width.
- Top section: a `.top-region` (`flex: 1 1 auto`) that distributes the logo (top-left, 30px height) and the meta/headline/subtitle stack via `justify-content: space-between`, pinning the title stack to the bottom of the upper region. A **40px** gap separates it from the speaker row.
- Bottom section: horizontal row of three tiles, **150x150** rounded **8.5px**, bottom-aligned. The blocks are **fixed-width** (`flex: 0 0 auto`, **20px** gap) and **left-aligned** — each block hugs its 150px tile + label, so the row ends short of the right edge rather than spanning the full width.
- Each tile has its name + company label to the right, **bottom-aligned** to the tile. Name 20px `#FFFFFF`, company 20px `#C6C7C8`, `gap: 6px`.
- **Auto-fit:** the headline shrinks from 64px down to 40px (2px steps) if it would wrap past 2 lines or overflow horizontally. The subtitle shrinks from 36px down to 22px (1px steps) if it would wrap past 2 lines. Runs inline before the screenshot.
- Reference: [`../design-system/assets/reference-renders/Social Media Webinar Promo - 3 Speakers.png`](../design-system/assets/reference-renders/Social%20Media%20Webinar%20Promo%20-%203%20Speakers.png).

### 4 speakers
- **Same single-column layout as 3-speaker** (full-width headline, `.top-region` distributed via `justify-content: space-between`, 40px gap above the speaker row), with **four** 150x150 tiles instead of three.
- Bottom section: horizontal row of four tiles, **150x150** rounded **8.5px**, bottom-aligned. Each block is fixed-width (`flex: 0 0 256px` = 150px tile + 12px gap + 94px label) with a **20px** gap. Four blocks span 4×256 + 3×20 = **1084px**, so the row runs the full content width (≈edge-to-edge in the 1080 inner column) rather than ending short like the 3-speaker row.
- Each tile has its name + company label to the right, **bottom-aligned** to the tile. Name 20px `#FFFFFF`, company 20px `#C6C7C8`, `gap: 6px`.
- **Auto-fit:** identical to 3-speaker — headline 64px → 40px (2px steps), subtitle 36px → 22px (1px steps). Runs inline before the screenshot.
- Figma source: "Type=4 Speakers" (`Frame 2147229172` speaker row, width 1084).

## Headshot cleanup

Prompt and settings: [`references/nano-banana-headshot-cleanup-prompt.md`](references/nano-banana-headshot-cleanup-prompt.md). Nano-banana is **required** for every run; see SKILL.md Step 6.

Every cleanup run is tied to one gradient — the backdrop is solid-filled with the gradient's base color (wine `#3F0A20`, ink `#1C2733`, forest `#002625`) so the headshot tile reads as part of the card. `--gradient <hex>` is required; the script errors out without it. Do **not** ask Gemini for a "transparent" or "alpha channel" background — `gemini-3-pro-image-preview` cannot emit real alpha for a photo and instead bakes a checkerboard pattern into opaque pixels. The cleaned PNG is written to `working/headshots/[speaker-slug]_[gradient]_504.png`. An all-variants run (step 10) produces one headshot per speaker per gradient — `speakers × 3` Gemini API calls.

## Copy rules

- **Headline.** Sentence case. <= 8 words ideally. Active voice. Avoid hype adjectives (next-gen, cutting-edge, revolutionary, best-in-class, striking, remarkable, significant, compelling, powerful). Avoid AI buzzwords. Earn claims.
- **Meta line.** `Month DD, YYYY, Hpm TZ / Hpm TZ` (e.g. `March 26, 2026, 11am EST / 4pm GMT`). Two timezones is the norm for cross-Atlantic webinars; one is fine for region-specific.
- **Speaker name.** Use the speaker's preferred professional name as written. Do not abbreviate.
- **Speaker role.** `Title, Company`. Spell out company names; never use ticker symbols.
- **No quotes around the headline.** It's a card, not a pull-quote.
- **No CTA button.** This template doesn't have one. The card sits in a LinkedIn post and the CTA lives in the post copy.
- **No hx product names in the headline** unless the brief explicitly says so. Talk about the topic, not the product.

## Output paths

For a campaign at `[campaign-folder]` (typically under the repo's `campaigns/` directory):

```
[campaign-folder]/
├── working/
│   ├── headshots/
│   │   ├── richard-gunn_wine_504.png                   # cleaned via nano-banana, wine-tinted backdrop
│   │   ├── richard-gunn_ink_504.png                    # (added on all-variants runs)
│   │   ├── richard-gunn_forest_504.png
│   │   ├── krzysztof-wanatowicz_wine_504.png
│   │   ├── krzysztof-wanatowicz_ink_504.png
│   │   └── krzysztof-wanatowicz_forest_504.png
│   └── linkedin-card_20260326_state-of-ai-in-underwriting_wine.html
└── export/
    ├── linkedin-card_20260326_state-of-ai-in-underwriting_wine.png    # 1200x627
    └── linkedin-card_20260326_state-of-ai-in-underwriting_wine@2x.png # 2400x1254
```

The campaign folder no longer needs sibling `fonts/` or `colors_and_type.css` files. Fonts are inlined as base64 `@font-face` rules during composition (see `{{FONT_FACE_BLOCK}}` in `SKILL.md` step 7). The intermediate HTML has one external reference — the gradient PNG at an absolute path inside this skill's `assets/` folder — which Puppeteer rasterizes into the exported PNG.

## Puppeteer

The exporter uses `puppeteer`. `node_modules/` is gitignored, so it has to be installed once per environment — but the skill handles this automatically:

- **Any environment**: step 9a in `SKILL.md` runs `node -e "require('puppeteer')" || npm install` before the exporter, so Puppeteer is installed on first use automatically. No manual step.
- **Local / Cursor**: optionally run `cd ".claude/skills/webinar-promo-card/scripts" && npm install` once up front. Persists across sessions.

If step 9 fails with `Cannot find module 'puppeteer'` despite the above, the SKILL.md retry path runs `npm install` and tries again — this is a fallback, not the user's job.

**Cloud routine note**: installing the Puppeteer npm package downloads the Chromium **binary**, but Chromium also needs OS-level shared libraries (`libnss3`, `libgbm1`, `libasound2`, `libxss1`, etc.) to launch. Those libs are not installed by `npm install` — they belong in the routine's setup script (`apt-get install`). If `puppeteer.launch()` fails with a `lib*.so` error, that's the missing piece.

## QA checklist (before delivering)

- [ ] Speaker count matches the chosen template (1, 2, 3, or 4).
- [ ] Headline is sentence case, <= 8 words, no em dashes, no hype adjectives, no banned words.
- [ ] Meta line renders in **JetBrains Mono**, not Acid Grotesk. If it falls back to a system mono, the font block wasn't pasted in full.
- [ ] All body text (headline, subtitle, name, role) renders in **Book** — every variant specs Acid Grotesk `350`, which now resolves to the Book face (not the old 300 Light snap). See "Body text renders Book" above.
- [ ] Logo wordmark uses the inlined `hx-wordmark.svg` (outlined paths). The "hyperexponential" word should render identically even if Acid Grotesk fails to load.
- [ ] Gradient background is the chosen color's selected variant PNG from `assets/` (e.g. `Burgundy 0N` / `Dark blue 0N` / `Deep Forest 0N`, where `N` is the chosen variant, default `01`), not the old inline SVG gradient.
- [ ] (1-speaker only) 60px padding all sides; two equal 520px columns with a 40px gutter; headshot tile fills the right column (8px radius, no border); the head keeps clear headroom (not cropped at the top).
- [ ] (1-speaker) Meta → headline and headline → subtitle gaps render at a uniform ≈20px ink-to-ink. (2-speaker and 3-speaker use a flat `gap: 12px` — see "Title-stack spacing" above.)
- [ ] (1-speaker only) The left column distributes via `space-between`: logo at the top, meta + headline + subtitle stack in the middle, name + company at the bottom.
- [ ] Logo → meta line has a clear vertical gap (1-speaker and 3-speaker: the `space-between` distribution leaves clear air below the logo; 120px in 2-speaker).
- [ ] All CSS is in a single `<style>` block in `<head>`. No external stylesheets.
- [ ] `@font-face` rules use `url(data:font/...;base64,...)` — no relative font paths, no sibling `fonts/` folder needed.
- [ ] Every speaker has a cleaned PNG in `headshots/` (504px, square). No raw photos, no gradient-tile fallbacks.
- [ ] Each headshot tile backdrop is a uniform solid gradient-base fill — no checkerboard, no transparency artifacts, no original-photo background.
- [ ] (3-speaker only) The three 150px tiles are **left-aligned** with a 20px gap (fixed-width blocks, not distributed across the full card width); the row ends short of the right edge.
- [ ] (4-speaker only) The four 150px tiles are bottom-aligned with a 20px gap (fixed-width blocks), spanning the full content width (≈edge-to-edge); confirm the 4th tile's label isn't clipped by the card's `overflow: hidden`.
- [ ] Coral does not appear anywhere on the card.
- [ ] PNG export ran. Both 1x and 2x exist in `export/`.
- [ ] The card's visible canvas in the screenshot is exactly 1200x627 (1x) — no extra body padding bleeding into the screenshot.
