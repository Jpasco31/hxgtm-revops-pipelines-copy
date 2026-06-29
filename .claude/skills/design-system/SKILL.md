---
name: design-system
description: "Reference for the hyperexponential brand system — color tokens, typography, logos, gradients, decorations, and voice rules. Use when generating any branded marketing artifact (decks, one-pagers, web sections, social cards) and as a dependency for the webinar-promo-card skill. Never use deprecated 'hx Renew' terminology."
---

## Context Loading

This skill is fully self-contained — all brand truth lives in the local skill files. Read them in this order to absorb the full brand system:
1. `README.md` — color, type, layout, voice
2. `PRODUCT_MARKETING_CONTEXT.md` — PMM-approved glossary, voice rules, proof points
3. `2026-design-system-v2.md` — token spec extracted from Figma

# design-system skill (hyperexponential)

Read `README.md` in this folder first — it contains brand context, content fundamentals (voice, casing, punctuation), visual foundations (colour, type, motion, layout), an iconography reference, and the slide-layout list.

Then explore:

- `tokens/colors_and_type.css` — drop-in CSS custom-property tokens. Always link or paste this into any HTML artifact.
- `tokens/fonts-inline.css` — base64-inlined `@font-face` rules for all 14 weights/styles (~2.7 MB). Paste into a `<style>` block for fully self-contained HTML.
- `tokens/fonts-inline-card.css` — subset (Light / Book / Regular / Medium upright + JetBrains Mono Regular, ~1.1 MB). Use for screenshot-target HTML. Book is declared at weight `350`, Regular at `400`, matching Figma's numeric weight axis.
- `assets/logo/` — the hx wordmark, logomark, and lockups (light + dark).
- `assets/decorations/` — the brand's geometric decoration kit (dashed circle, lune, double-lune, sine wave). One decoration per layout, single colour, never animated.
- `assets/icons/` — Carbon-derived line icons. Use these or matching IBM Carbon icons.
- `assets/reference-renders/` — brand-team comp renders (e.g. Social Media Webinar Promo PNGs) used as visual targets by downstream card skills.
- `preview/` — small specimen cards (one per token / component family) used to preview the system.
- `PRODUCT_MARKETING_CONTEXT.md` — PMM-approved voice rules, glossary, words to use/avoid, proof points.
- `2026-design-system-v2.md` — the long-form token spec extracted from Figma 2026-04-22.
- `scripts/regenerate_fonts_inline.js` — regenerates the two `tokens/fonts-inline*.css` bundles from the .otf files in `fonts/`. Run only when the font binaries change.

If you create visual artifacts (slides, mocks, throwaway prototypes), inline the tokens and a `fonts-inline*.css` bundle into a single self-contained HTML file. No sibling `fonts/` directory or stylesheet copies needed.

If you are working on production code, you can read this skill to absorb the rules and apply them to real components.

If the user invokes this skill without further guidance, ask them what they want to build, ask a few clarifying questions about audience and surface, then act as an expert hx-brand designer. Output HTML artifacts by default; output production code only if asked.

Hard rules:
- **No emoji**, ever.
- **Sentence case** for all UI copy (headlines, buttons, nav, table headers).
- **No em dashes.** Use periods or commas. Active voice, short sentences, no more than two commas per sentence.
- **American English** spelling (color, organization, modeling).
- **Bold (not italics)** for emphasis. Oxford commas. Double quotation marks.
- **No hype adjectives**: avoid next-gen, cutting-edge, revolutionary, best-in-class, striking, remarkable, significant, compelling, powerful.
- **Never use "hx Renew"** (deprecated product name). The product is **hx**; the company is **hyperexponential** (always lowercase).
- **Don't use these as the product category**: pricing platform, rating engine, underwriting workbench, underwriting intelligence platform. The category is **pricing and underwriting platform**.
- **One accent color per layout**, never mix three. Teal is the workhorse; wine is reserved for moments of weight.
- **One decoration per layout.** Single colour. Never animated.
- **Pill buttons** only.
- **Arial is the executable typeface** (it's what the official .potx ships). The licensed FFF Acid Grotesk webfont files are present in `fonts/` and are pre-inlined into `tokens/fonts-inline.css` and `tokens/fonts-inline-card.css` — paste a bundle's contents into a `<style>` block for self-contained Acid Grotesk rendering. Arial is the safe substitute when neither bundle is loaded.
- **Never invent a logo or icon**. Use the files in `assets/` or substitute with IBM Carbon at the same stroke weight.
- **Color values are non-negotiable** — they come from the official `theme1.xml` in `hx_template-2026.potx`. Don't tweak them for "harmony"; they are the source of truth.
