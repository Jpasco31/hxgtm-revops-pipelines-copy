# linkedin-single-image-ad - reference

The terse pipeline lives in [`SKILL.md`](SKILL.md). This file holds the longer specs, the variant picker, the gradient recipes, the type spec table, the layout details per variant, copy rules, output paths, and the QA checklist.

The output is a LinkedIn single image ad (1080x1080, 1:1) used for product, demo, and "schedule a demo" campaigns. The skill name describes the use case (LinkedIn single image ad); the output file naming uses `linkedin-ad_` to distinguish from `webinar-promo-card`'s `linkedin-card_` prefix.

## Canvas

- **Format:** LinkedIn 1:1 single image ad.
- **Pixel size:** 1080 x 1080.
- **Border radius on the card:** 4px.
- **Padding:** 60px on all sides.
- **File targets:** PNG at 1x (1080x1080) and 2x (2160x2160). PNG only - JPG compression eats the gradient.

## Variant picker

Ask for these choices before selecting a scaffold:

- **Text alignment:** `center` or `left`.
- **Background:** `cream`, `wine`, `ink`, or `forest`.
- **Button needed:** `yes` or `no`.
- **Button background:** `white` or `dark` when a button is needed. Default to white on gradient backgrounds and dark on cream backgrounds.

Derive the template from alignment and background. `center` + `cream` uses `light-center`; `center` + any gradient uses `gradient-center`; `left` + any gradient uses `gradient-left`; `left` + `cream` uses `white-left`.

| Variant | Background | Headline | CTA | Hero panel | Use it for |
|---|---|---|---|---|---|
| `light-center` | Cream `#F5F5F5` | Centered, dark `#16212E`, 76px | Optional | Full-bleed bottom (1080x600) | Product / dashboard explainer ads where the screenshot does the heavy lifting and the headline is short. |
| `gradient-center` | Wine / Ink / Forest gradient (default Forest) | Centered, white, 76px | Optional | Full-bleed bottom (1080x600) | Same shape as `light-center` but with brand gradient authority. Use when the campaign needs more emotional weight or matches a category-led narrative. |
| `gradient-left` | Wine / Ink / Forest gradient (default Wine) | Left-aligned, white, 120px (2 short lines) | Optional, white by default | Frosted-glass code panel anchored bottom-right with intentional bleed (886x630) | Direct-response demo driver. Big bold "try it" moment with a literal CTA. Wine is the flagship default. |
| `white-left` | Cream `#F5F5F5` | Left-aligned, two lines: line 1 dark `#16212E`, line 2 muted `#848D9A`, 100px | Optional, dark by default | Anchored bottom-right with right + bottom padding (720x520) | Outcome-led claim plus product proof. Two-line headline lets you split a setup line and a payoff line. |

## Gradient picker (gradient variants only)

| Gradient | Base color | Use it for |
|---|---|---|
| **Wine** *(default for `gradient-left`)* | `#3F0A20` (`--wine`) | Flagship, executive, high-authority demo drivers. The default unless the brief says otherwise. |
| **Ink** | `#1C2733` (`--ink`) | Technical, product, engineering-led campaigns. |
| **Forest** *(default for `gradient-center`)* | `#01514F` (`--forest`) | Community, partnership, ecosystem, customer-led campaigns. |

White type only on all three. Coral (`--coral`) is forbidden on gradient - hard brand rule.

### Gradient recipes (CSS)

Each recipe is a stack: a soft cool highlight upper-left, a diagonal mid-lift, a deepening lower-right vignette, and a base linear gradient. Drop these into the `.bg-base` block in the chosen template.

#### Wine
```css
background:
  radial-gradient(ellipse 55% 70% at 12% 20%, rgba(190, 150, 200, 0.30) 0%, rgba(190, 150, 200, 0) 65%),
  radial-gradient(ellipse 80% 60% at 50% 45%, rgba(140, 60, 80, 0.22) 0%, rgba(140, 60, 80, 0) 70%),
  radial-gradient(ellipse 70% 90% at 95% 90%, #1a0610 0%, rgba(26, 6, 16, 0) 70%),
  linear-gradient(125deg, #5a1a32 0%, #470f24 40%, #340a1c 70%, #200612 100%);
```

#### Ink
```css
background:
  radial-gradient(ellipse 55% 70% at 12% 20%, rgba(110, 140, 190, 0.32) 0%, rgba(110, 140, 190, 0) 65%),
  radial-gradient(ellipse 80% 60% at 50% 45%, rgba(80, 110, 165, 0.22) 0%, rgba(80, 110, 165, 0) 70%),
  radial-gradient(ellipse 70% 90% at 95% 90%, #0a1424 0%, rgba(10, 20, 36, 0) 70%),
  linear-gradient(125deg, #2a3d5c 0%, #1c2c47 40%, #142239 70%, #0d1828 100%);
```

#### Forest
```css
background:
  radial-gradient(ellipse 55% 70% at 12% 20%, rgba(120, 200, 180, 0.25) 0%, rgba(120, 200, 180, 0) 65%),
  radial-gradient(ellipse 80% 60% at 50% 45%, rgba(60, 130, 120, 0.22) 0%, rgba(60, 130, 120, 0) 70%),
  radial-gradient(ellipse 70% 90% at 95% 90%, #00211f 0%, rgba(0, 33, 31, 0) 70%),
  linear-gradient(125deg, #0d6260 0%, #075753 40%, #034743 70%, #002927 100%);
```

### Grain + vignette (always on, gradient variants)

Always layer these two on top of the gradient, regardless of which gradient is chosen:

```css
.bg-grain {
  position: absolute; inset: 0;
  opacity: 0.18;
  mix-blend-mode: overlay;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 0.55 0'/></filter><rect width='100%25' height='100%25' filter='url(%23n)'/></svg>");
}
.bg-vignette {
  position: absolute; inset: 0;
  background: radial-gradient(ellipse 90% 90% at 50% 100%, rgba(0, 0, 0, 0.30) 0%, rgba(0, 0, 0, 0) 70%);
}
```

The `gradient-left` template uses a bottom-right vignette instead of a bottom-center one, since the hero panel is anchored to the bottom-right corner. Light variants (`light-center`, `white-left`) skip grain and vignette entirely.

## Type spec (1080x1080 canvas)

All sizes are CSS px. Use `FFF Acid Grotesk` first, fall back to `Arial`. Headline weight 350 maps to Light (300) at render time - see the note at the bottom of this section.

| Element | `light-center` / `gradient-center` | `gradient-left` | `white-left` |
|---|---|---|---|
| Logo lockup height | 45px | 45px | 45px |
| Logo color | `#16212E` (light) / `#FFFFFF` (gradient) | `#FFFFFF` | `#16212E` |
| Headline size | 76px | 120px | 100px |
| Headline weight | 350 (Book) | 350 (Book) | 350 (Book) |
| Headline line-height | 1.1 | 1.1 | 1.1 |
| Headline color | `#16212E` (light) / `#FFFFFF` (gradient) | `#FFFFFF` | line 1 `#16212E`, line 2 `#848D9A` |
| Subtitle size | 28px | n/a | n/a |
| Subtitle color | `#848D9A` (light) / `rgba(255,255,255,0.72)` (gradient) | n/a | n/a |
| CTA pill | Optional, user-selected background | Optional, user-selected background | Optional, user-selected background |
| CTA pill padding | 8px / 32px | 8px / 32px | 8px / 32px |
| CTA pill radius | 44.135px | 44.135px | 44.135px |
| Padding | 60px | 60px | 60px |

**Notes on weight 350.** The Figma headline tokens map to weight 350, which has no matching static OTF face in the loaded family (Light=300, Book=400, Medium=500). Browsers' font-matching algorithm renders 350 in **Light (300)** because for any value between 100–500 it picks the closest face descending first. This is the intended visual; do not "fix" 350 to 300 unless the spec changes.

**Headline wrap.** All headline elements include `text-wrap: balance` so multi-line headlines split evenly rather than orphaning the last word. Leave it on.

## Layout per variant

### `light-center`
- Single-column flex layout, items center-aligned.
- Logo top-center at 60px from top edge.
- Text block (headline + optional subtitle) center-aligned, sitting above the hero region.
- Hero region: `position: absolute; left: 0; bottom: 0; width: 1080px; height: 600px; overflow: hidden;`. The hero image fills via `object-fit: cover; object-position: top center;` so the top of the cropped asset stays visible.

### `gradient-center`
- Same layout as `light-center` (centered logo + headline).
- Layered behind: `.bg-base` (gradient), `.bg-grain` (noise), `.bg-vignette` (bottom-center radial dark).
- Hero region same dimensions and positioning as `light-center`. Hero sits above the vignette so the product mockup reads cleanly against the gradient.

### `gradient-left`
- Single-column flex layout, items left-aligned, 80px gap between logo and text.
- Logo top-left.
- Headline 120px on two short lines (e.g. "Try AI-powered" / "underwriting"). 40px gap between headline and CTA.
- CTA: white pill, dark `#16212E` text, 32px label, "Schedule a demo" + arrow icon.
- Hero panel: positioned at `left: 243px; top: 791px; width: 886px; height: 630px;` - bleeds 49px past the right edge and 341px past the bottom edge (mirrors the Figma "panel slipping off the canvas" treatment). Clipped by the card's `overflow: hidden`.
- Hero panel chrome: 2px `rgba(255,255,255,0.6)` border, 28px border-radius, 14px inner padding, large drop shadow. Inner image clipped to a 17px-radius rounded rectangle.

### `white-left`
- Single-column flex layout, items left-aligned, 60px gap between logo and text.
- Logo top-left.
- Headline 100px on two lines. Line 1 dark `#16212E`, line 2 muted `#848D9A`. 40px gap between headline and CTA.
- CTA: dark `#16212E` pill, white text, 32px label, "Schedule a demo" + arrow icon.
- Hero panel: anchored bottom-right at `right: 60px; bottom: 60px; width: 720px; height: 520px;`. 12px border-radius, soft drop shadow, white background fallback.

## Hero image catalog

The skill ships with three curated hero keys, pre-cropped for all three slot shapes. See [`hero-images/README.md`](hero-images/README.md) for the full catalog including recommended variant pairings.

| Key | What it is | Recommended variant pairing |
|---|---|---|
| `dashboard` | Underwriting dashboard with data cards (premium, expected loss ratio, etc.) | Best with `light-center` or `gradient-center` (full-bleed). Acceptable in `gradient-left` and `white-left`. |
| `code-panel` | Code editor panel showing a JavaScript schema edit ("Add a node called underwriter name to my data schema") | Designed for `gradient-left`. Acceptable in others if the campaign theme is technical / engineering-led. |
| `file-uploader` | File-uploader product UI with stacked file cards | Designed for `white-left`. Acceptable in others if the campaign theme is workflow / triage. |

User-supplied images go through `scripts/crop_hero.js` instead - see [`SKILL.md`](SKILL.md) step 6.

## Copy rules

- **Headline.** Sentence case. <= 8 words ideally (3–5 words is best at 120px). Active voice. Avoid hype adjectives (next-gen, cutting-edge, revolutionary, best-in-class, striking, remarkable, significant, compelling, powerful). Avoid AI buzzwords. Earn claims.
- **Two-line headlines (`white-left`).** Line 1 sets up the claim (dark), line 2 lands the payoff (muted). Keep both lines short - 3–5 words each. Example: "Smarter triage." / "Quote in minutes."
- **Subtitle.** One short clause. No second sentence. No period at the end.
- **CTA label.** Default `Schedule a demo`. Acceptable swaps: `See it in action`, `Book a walkthrough`, `Get a demo`. Keep it imperative and short - the pill caps at ~3 words at 32px.
- **CTA background.** Ask for white or dark when a button is needed. White CTA uses `background: #FFFFFF`, `border: #FFFFFF`, and text `#16212E`. Dark CTA uses `background: #16212E`, `border: #16212E`, and white text. Keep the button at `display: flex`, `padding: 8px 32px`, `justify-content: center`, `align-items: center`, `gap: 4px`, `border-radius: 44.135px`, and `border: 0.727px solid`.
- **No quotes around the headline.** It's an ad, not a pull-quote.
- **No hx product names in the headline** unless the brief explicitly says so. Talk about the outcome, not the product SKU.

## Output paths

For a campaign at `[campaign-folder]` (typically under `Projects/Rev Ops Pipelines/campaigns/`):

```
[campaign-folder]/
├── working/
│   ├── hero/
│   │   └── <key>--<variant-slot>.png                  # copied from hero-images/ or
│   │                                                   # produced by scripts/crop_hero.js
│   └── linkedin-ad_20260618_smarter-triage.html
└── export/
    ├── linkedin-ad_20260618_smarter-triage.png        # 1080x1080
    └── linkedin-ad_20260618_smarter-triage@2x.png     # 2160x2160
```

The HTML is fully self-contained - base64 fonts inlined, inline CSS, inline lockup SVG. The only sibling dependency is the `hero/` folder containing the resolved hero PNG.

## Puppeteer + Sharp

The exporter uses `puppeteer`. The cropper uses `sharp`. `node_modules/` is **not** shipped with the skill - gitignored to keep the skill portable. First-time install:

```
cd ".claude/skills/linkedin-single-image-ad/scripts"
npm install
```

After that the install persists locally. Re-run only if `package.json` changes.

## QA checklist (before delivering)

- [ ] Variant matches the brief (light-center, gradient-center, gradient-left, or white-left).
- [ ] Headline is sentence case, no em dashes, no hype adjectives, no banned words.
- [ ] For `white-left`, line 1 is dark and line 2 is muted gray. Both lines fit on a single visual line each.
- [ ] For gradient variants, the gradient matches the brief (Wine / Ink / Forest) and the `{{GRADIENT_BASE}}` color and `BG_STACK` recipe both swapped consistently.
- [ ] CTA pill matches the variant (none / white / dark) and the label is imperative + short.
- [ ] Lockup SVG is inlined (not `<img src=...>`) so it picks up `@font-face` and `currentColor`.
- [ ] All CSS is in a single `<style>` block in `<head>`. No external stylesheets.
- [ ] `@font-face` rules use `url(data:font/otf;base64,...)` - no relative font paths.
- [ ] Hero `<img src="hero/...">` resolves to a sibling `working/hero/<filename>.png` that exists on disk before export.
- [ ] Coral does not appear anywhere on the card.
- [ ] PNG export ran. Both 1x (1080x1080) and 2x (2160x2160) exist in `export/`.
- [ ] `file <slug>.png` reports the expected dimensions exactly. No extra body padding bleeding into the screenshot.
