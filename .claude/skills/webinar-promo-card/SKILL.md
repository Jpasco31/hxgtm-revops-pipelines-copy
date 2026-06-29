---
name: webinar-promo-card
description: Generate a self-contained, on-brand LinkedIn webinar card (1200x627, 1-4 speakers) for hyperexponential. Use when the user asks to design, produce, build, or export a LinkedIn card, webinar promo card, virtual-event card, panel announcement image, or speaker promo. Outputs a single HTML file with all CSS, fonts, and SVGs inlined plus a PNG via Puppeteer.
user-invocable: true
requires: [design-system]
metadata:
  version: 1.5.0
---

# webinar-promo-card skill

Produces a single LinkedIn-feed webinar card at **1200x627** (LinkedIn 1.91:1) and exports it to PNG. Scope is webinar / virtual-event / panel cards with **1, 2, 3, or 4 named speakers**.

Read [`README.md`](README.md) before composing — it contains the gradient picker, copy rules, headshot-cleanup prompt, layout specs per speaker count, and the QA checklist. The terse pipeline below is the orchestration, not the source of truth for layout values.

## When to use

User says any of: "make a LinkedIn card for the webinar," "design a webinar promo," "speaker card," "panel card," "build the card for [event name]," "export the LinkedIn promo," "regenerate the speaker card."

## Forbidden refusals (read first)

This skill runs end-to-end in **every** environment that has Node.js — local CLI, Cursor, and cloud routines. **Never** respond with any of the following or close variants:

- "this requires a local or Cursor environment"
- "you'll need to run this locally"
- "node_modules is missing, so I can't export"
- "the SessionStart hook didn't fire"
- "I cannot install dependencies in this environment"
- "the routine environment is not configured for Puppeteer / Chromium"
- "the nano-banana MCP isn't connected"
- "GEMINI_API_KEY is missing"
- any variant that redirects the user to a different environment instead of executing step 9

If a hard dependency (Puppeteer, `@google/genai`, `GEMINI_API_KEY`) is genuinely unmet, surface the verbatim shell or API error and stop. The error is the answer — do not narrate around it.

If `require('puppeteer')` fails, run step 9a's install fallback **before** declaring the step blocked. Only after that fallback **also** fails is it acceptable to surface a verbatim shell error — and even then, do not narrate a refusal. The error is the answer.

## Runtime compatibility

This skill runs in **all** Claude Code surfaces — local CLI, Cursor, and cloud routines. Do **not** block on environment checks. Concretely:

- **Node.js / Puppeteer**: locally, run `npm install` in `scripts/` once, or just let step 9a do it. In cloud routines, dependencies are expected to be installed via the routine's environment Setup Script (see [`ROUTINE_INTEGRATION.md`](ROUTINE_INTEGRATION.md)) or via `export_card.js`'s built-in `require('puppeteer')` → `npm install` fallback. Step 9a (the mandatory `node -e "require('puppeteer')" || npm install` one-liner) is the universal safety net — it works in every environment regardless of how Puppeteer got there.
- **Campaign folder**: the repo's `campaigns/` directory is on disk in every surface (cloned by routines, present locally). Create the campaign subfolder if missing.
- **Gemini API key**: the `GEMINI_API_KEY` env var must be set on the routine / locally. The skill hard-fails verbatim if it is missing or the API rejects the call. There is no raw-photo fallback.

If a hard requirement genuinely cannot be met (e.g. the user provided no headline at all), ask the user — do not refuse the run pre-emptively.

Cloud routines have Node.js. If Puppeteer isn't already present, the deps check at the top of step 9 installs it (`npm install` is idempotent and self-contained inside the skill's `scripts/` folder). If `node export_card.js` then fails, surface the verbatim Bash error and stop — do **not** redirect the user to a different environment. Routine-environment configuration (Setup Script, Chromium OS libs) is documented in [`ROUTINE_INTEGRATION.md`](ROUTINE_INTEGRATION.md) and is owned by the routine team, not the skill.

**Subagent note**: if you are running as a subagent and the orchestrator passed you a GitHub-API path for `SKILL.md`, the runtime files (`scripts/`, `templates/`, etc.) are still on the local filesystem at the cloned repo path. Use the local path for any `node` or shell command in step 9.

## Pipeline (11 steps)

### 1. Collect the brief
Ask for whatever isn't provided. Required fields:

- **Event headline** (sentence case, ideally <= 8 words)
- **Date + time + timezone** (e.g. `March 26, 2026, 11am EST / 4pm GMT`)
- **Speakers**: 1-4 entries, each with `name`, `role` (e.g. "President, hyperexponential"), and a **required** `photo_path` (absolute path to a headshot file). `photo_path` is required for every speaker. If any speaker is missing it, raise an explicit error — `photo_path is required for speaker "<name>". This skill cannot run without a headshot for every speaker.` — and halt. Do not proceed, do not silently prompt the user mid-pipeline. (This intentionally overrides Step 1's general "ask for whatever isn't provided" rule for `photo_path` only — the hard-fail contract is deliberate.) **Do not** generate or substitute initials, silhouettes, or "photo pending" placeholders.

  When the brief comes from a Perkins form whose speaker inputs are explicit numbered groups — `Speaker 1: Name` / `Speaker 1: Title` / `Speaker 1: Headshot`, `Speaker 2: …`, etc. — pair each speaker's name and title with their **same-numbered** headshot. Never infer the name↔headshot pairing by position or order; the number in the field name is authoritative.

  If a brief supplies Notion file URLs, a Notion page ID with a Files property, or any Notion-hosted reference instead of local paths, the caller (or the routine orchestrator) must run the [`download-from-notion`](../download-from-notion/SKILL.md) skill first and substitute the returned absolute path as `photo_path`. This skill never downloads inputs itself — the hard-fail above is preserved regardless of where the brief sourced the photos.
- **Campaign folder**: absolute path to a folder under the repo's `campaigns/` directory (at the repo root). The skill will write outputs into `[campaign-folder]/working/` and `[campaign-folder]/export/`. Create the campaign folder if it doesn't exist.

Optional:

- **Subtitle** (one-line descriptor, not a second sentence)
- **Gradient**: `wine` (default), `ink`, or `forest` (see picker in README)
- **Variant**: `01` (default), `02`, or `03` — the texture variant within the chosen color. Defaults to `01` when omitted. See [`references/gradient-assets.md`](references/gradient-assets.md) for the full color × variant table.

If the user provides 5+ speakers, stop and ask them to drop one or split into a multi-card carousel. Do not extrapolate.

### 2. Read brand context
This skill declares `requires: [design-system]`. Always read the sibling `design-system` skill in this order before writing any copy:

1. [`../design-system/SKILL.md`](../design-system/SKILL.md)
2. [`../design-system/README.md`](../design-system/README.md)
3. [`../design-system/PRODUCT_MARKETING_CONTEXT.md`](../design-system/PRODUCT_MARKETING_CONTEXT.md)

Apply the hard rules: sentence case, no em dashes, no emoji, no hype adjectives, lowercase "hyperexponential", never "hx Renew", American English, double quotation marks, Oxford comma. Coral is forbidden on gradient backgrounds.

### 3. Read layout reference
The canonical layouts live in [`templates/`](templates/) — those files ARE the layout source of truth (inline gradient SVG slot, grain layer, vignette, inline lockup SVG, type sizes). The 3- and 4-speaker variants share a **different layout** from 1/2-speaker (full-width headline + horizontal speaker row at the bottom; the 4-speaker row spans the full content width) — see [`README.md`](README.md) for specs and [`../design-system/assets/reference-renders/`](../design-system/assets/reference-renders/) for the brand-team comp renders.

### 4. Pick the variant scaffold
From [`templates/`](templates/):

- 1 speaker -> `card-1-speaker.html` (single full-height tile in the right column with equal 64px margins; name + role pinned bottom-left, aligned to the tile's bottom edge)
- 2 speakers -> `card-2-speakers.html` (two stacked tiles in right column — matches the brand-team reference render in `../design-system/assets/reference-renders/`)
- 3 speakers -> `card-3-speakers.html` (full-width headline, three horizontal tiles at the bottom, row ends short of the right edge)
- 4 speakers -> `card-4-speakers.html` (same single-column layout as 3-speaker, with four horizontal tiles spanning the full content width)

### 5. Pick the gradient
From [`README.md`](README.md):

- **Wine** (default): flagship, executive, high-authority
- **Ink**: technical, product, engineering-led
- **Forest**: community, partnership, ecosystem, customer-led

White type only on all three. Never Coral on gradient.

The **color** picks the gradient family; the brief's **variant** field (`01` default / `02` / `03`) picks the texture PNG within that family. Each color ships three variants in [`assets/`](assets/) and all nine are selectable. Variant defaults to `01` when the brief omits it. Resolve the PNG from `(color, variant)` using the table in [`references/gradient-assets.md`](references/gradient-assets.md). The base color hex is variant-independent — it follows the color only.

The chosen gradient drives the primary card (steps 7–9). Step 10 will offer to produce all three colors (keeping the selected variant number).

### 6. Headshot cleanup (Gemini Image, photo-only)
For each speaker, invoke `scripts/cleanup_headshot.js` via Bash. The script calls Google's Gemini Image API directly via `@google/genai` — no MCP server is involved. The `GEMINI_API_KEY` env var must be set; if it is not, the script exits non-zero with a verbatim error. Surface that error and stop. There is no raw-photo fallback.

Every cleanup run is tied to one gradient. The backdrop is solid-filled with the gradient's base color so the headshot tile reads as part of the card. `--gradient <hex>` is **required** — the script errors out without it.

Gradient → hex map (use the hex matching the gradient chosen in step 5):

- `wine` → `#3F0A20`
- `ink` → `#1C2733`
- `forest` → `#002625`

`mkdir -p [campaign-folder]/working/headshots/` before calling.

For each speaker, run:

```
node ".claude/skills/webinar-promo-card/scripts/cleanup_headshot.js" \
  --input "<absolute path to the speaker's headshot>" \
  --output "[campaign-folder]/working/headshots/[speaker-slug]_[gradient]_504.png" \
  --prompt-file ".claude/skills/webinar-promo-card/references/nano-banana-headshot-cleanup-prompt.md" \
  --model pro \
  --aspect-ratio 1:1 \
  --gradient "<hex>"
```

`[gradient]` in the output filename is the lowercase gradient name (`wine` / `ink` / `forest`). Headshots for different gradients coexist side-by-side in `working/headshots/`.

Settings (all required, mirror the previous MCP contract):

- `--input`: absolute path to the user's headshot
- `--output`: `[campaign-folder]/working/headshots/[speaker-slug]_[gradient]_504.png`
- `--prompt-file`: `.claude/skills/webinar-promo-card/references/nano-banana-headshot-cleanup-prompt.md` — the prompt is loaded verbatim from disk and used as the text part
- `--model pro` (default) → `gemini-3-pro-image-preview`. Any other value falls back to `gemini-2.5-flash-image-preview`.
- `--aspect-ratio 1:1` (default)
- `--gradient <hex>` (required): 6-digit hex matching the chosen gradient's base color (see map above)

Rules:

- Cleanup is **photo-only**: square crop, replace background with the gradient's solid hex, normalize exposure. Never alter the subject's likeness, skin tone, hair, or clothing.
- If `cleanup_headshot.js` exits non-zero, surface the verbatim stderr and stop. Do not fall back to the raw photo, do not skip the speaker, do not continue the pipeline, do not retry silently.
- Every speaker must have a `photo_path` from step 1 (the brief halts at step 1 otherwise). **Do not** call the script to generate a person who does not exist.

### 7. Compose the card
Start from the chosen template in [`templates/`](templates/). **Strip the leading `<!-- … -->` comment from the template before substituting placeholders** — that comment lists every placeholder name (e.g. `{{HEADLINE}}`), so a naive `replace('{{HEADLINE}}', value)` lands on the comment occurrence and leaves the real slot intact. Either drop the leading comment first (`template.replace(/^<!--[\s\S]*?-->\s*/, '')`) or substitute with a global regex per placeholder.

Then fill the placeholders:

- `{{FONT_FACE_BLOCK}}` — paste the **full contents** of [`../design-system/tokens/fonts-inline-card.css`](../design-system/tokens/fonts-inline-card.css). This is ~1.1 MB of base64-encoded `@font-face` rules (FFF Acid Grotesk Light 300 / Book 350 / Regular 400 / Medium 500 upright + JetBrains Mono Regular). Pasting it inline makes fonts self-contained in the HTML — no external font files needed.
- `{{LOGO_SVG}}` — paste the **full contents** of [`../design-system/assets/logo/hx-wordmark.svg`](../design-system/assets/logo/hx-wordmark.svg). This SVG uses outlined paths for the "hyperexponential" wordmark, so it renders correctly regardless of which fonts are loaded. The SVG declares `fill="currentColor"`; the `.logo` container sets `color: #FFFFFF` so the wordmark renders white on every gradient.
- `{{HEADLINE}}` — sentence case, brand-approved language
- `{{SUBTITLE}}` — optional; omit the subtitle block entirely if not provided
- `{{META}}` — date/time/timezone line. Renders in JetBrains Mono Regular.
- `{{GRADIENT_BASE}}` — `#3F0A20` (wine) / `#1C2733` (ink) / `#002625` (forest). Acts as the solid-color fallback under the gradient PNG. Variant-independent: it follows the color, not the variant.
- `{{GRADIENT_IMG_PATH}}` — absolute path to the chosen color+variant PNG in [`assets/`](assets/) (e.g. `Burgundy 02.png` for wine + variant `02`). Resolve `(color, variant)` against the full table in [`references/gradient-assets.md`](references/gradient-assets.md); default variant is `01`. The template references the PNG with `<img src="{{GRADIENT_IMG_PATH}}">` — Puppeteer reads the local file during export and rasterizes it into the final PNG.
- `{{SPEAKER_N_NAME}}`, `{{SPEAKER_N_ROLE}}` — strings
- `{{SPEAKER_N_PHOTO_NODE}}` — `<img src="...">` referencing the cleaned PNG at `headshots/[speaker-slug]_[gradient]_504.png` (the gradient-suffixed file produced in step 6 for the gradient being composed)

Inline the font-face block, CSS, the wordmark SVG, the SVG noise/grain layer, and the vignette. The gradient PNG is the single external reference in the intermediate HTML — Puppeteer rasterizes it into the exported PNG so the final deliverable remains a single self-contained file.

### 8. Write outputs
- HTML -> `[campaign-folder]/working/linkedin-card_[YYYYMMDD]_[TOPIC-SLUG].html`

`[YYYYMMDD]` = the event date in compact form. `[TOPIC-SLUG]` = kebab-case slug of the headline (lowercase, alphanumeric + hyphens, max 60 chars).

**Filename convention when all three gradient variants are produced (step 10):** append the gradient name as a suffix to all output files so the set is distinguishable:

- `linkedin-card_[YYYYMMDD]_[TOPIC-SLUG]_wine.html` / `_wine.png` / `_wine@2x.png`
- `linkedin-card_[YYYYMMDD]_[TOPIC-SLUG]_ink.html` / `_ink.png` / `_ink@2x.png`
- `linkedin-card_[YYYYMMDD]_[TOPIC-SLUG]_forest.html` / `_forest.png` / `_forest@2x.png`

Rename the primary file to include its gradient suffix at the same time, so the full set is consistent. If only one gradient is produced, leave the filename unsuffixed.

The campaign folder no longer needs a sibling `fonts/` directory or a `colors_and_type.css` copy — the HTML is fully self-contained.

### 9. Export PNG

You **must** run the exporter via Bash. Do not describe the command, do not ask the user to run it, do not skip the export. This step is mandatory in every environment — local, Cursor, and cloud routine alike.

**Step 9a — mandatory deps check.** Run this command before the exporter. Do not skip it. A missing `node_modules/` is **not** a blocker — this command creates it. The check is idempotent (it short-circuits when Puppeteer is already installed):

```
node -e "require('puppeteer'); require('@google/genai')" 2>/dev/null || \
  (cd ".claude/skills/webinar-promo-card/scripts" && npm install)
```

If this command fails (non-zero exit), **read the error before reacting**:

- If the error is an npm/network failure (`SELF_SIGNED_CERT_IN_CHAIN`, `ENOTFOUND`, etc.): surface the verbatim error and stop. The routine env may need `NODE_EXTRA_CA_CERTS` set — see `ROUTINE_INTEGRATION.md` Option A.
- If the error is `MODULE_NOT_FOUND` after a successful npm install: the install partially failed. Surface the verbatim error and stop.
- Any other error: surface verbatim and stop.

Do **not** refuse, do **not** narrate, do **not** redirect to a different environment. The verbatim shell output is the only acceptable failure response from this step.

**Step 9b — run the exporter:**

```
node ".claude/skills/webinar-promo-card/scripts/export_card.js" \
  "<absolute path to the html written in step 8>" \
  "<campaign-folder>/export"
```

Saves `[slug].png` (1200x627) and `[slug]@2x.png` (2400x1254, deviceScaleFactor 2). The script clones the `.card` element and screenshots only that node, so any browser chrome / page padding is excluded.

**Failure handling — read the error before reacting:**

- If the error contains `Cannot find module 'puppeteer'` → step 9a was skipped. Run it now (`cd ".claude/skills/webinar-promo-card/scripts" && npm install`), then retry the exporter once. Do **not** refuse with "node_modules is missing" or any environment-availability claim.
- If the error contains `Failed to launch the browser process`, `error while loading shared libraries`, or any Chromium / `lib*.so` reference → the routine sandbox is missing OS-level shared libraries Chromium needs to start. This is a routine-env config issue, not a skill issue. Surface the verbatim error to the user, tell them the routine setup script needs the Chromium runtime libs added (`libnss3`, `libgbm1`, `libasound2`, `libxss1`, etc., installed via `apt-get`), and stop. Do **not** retry. Do **not** redirect them to a local environment.
- Any other error → surface verbatim and stop.

`node_modules/` is gitignored. Never write a run summary that says the user "needs to run this locally" or "needs Node.js / Puppeteer installed" — those statements are wrong inside this skill's contract.

### 10. Offer all three gradient colors
After step 9 completes, always ask:

> "Would you like all three gradient colors (wine, ink, forest)? I'll swap only the gradient background and base color — copy, layout, headshots, and fonts stay identical."

The all-colors run keeps the **same selected variant number** (`01` / `02` / `03`) across all three colors — variant choice is orthogonal to color. Headshots still regenerate per color (the backdrop hex differs), but not per variant.

If yes:

1. For each of the two remaining gradients, re-run steps 5 → 9 using the same brief, the same template, and the same variant number. **Re-run step 6 for every speaker** with the matching `--gradient <hex>` — the cleaned headshots are written to gradient-suffixed paths (`[speaker-slug]_wine_504.png` / `_ink_504.png` / `_forest_504.png`) in `working/headshots/`, so all three sets coexist. An all-variants run is `speakers × 3` Gemini API calls.
2. Apply the gradient-suffixed filename convention from step 8 to all three output files (including the primary card produced in steps 7–9). Rename the primary HTML and its PNGs to include the `_[gradient]` suffix.
3. Deliver a run summary listing all six PNGs (three 1x, three 2x) with their paths.

If no: deliver the primary card as-is with the unsuffixed filename.

### 11. Upload to Notion

After all PNGs are written (step 9 for one gradient, or step 10 for all three), upload them to a Notion page using the [`upload-to-notion`](../upload-to-notion/SKILL.md) skill.

**Resolve the Notion API token** (do **not** ask the user — it is supplied by the runtime):

1. If the orchestrator passed `notion_api_key` in the brief or the routine prompt, use that.
2. Else read `NOTION_API_KEY` from the environment (`echo "$NOTION_API_KEY"` via Bash).
3. If neither is set, skip this step entirely and note in the run summary: "Notion upload skipped — no `NOTION_API_KEY` in env and no token in the brief." **Do not block on the upload.**

**Resolve the Notion target page via the Notion MCP**:

1. The orchestrator/brief provides a Notion page reference — typically a **page name**, sometimes a URL or UUID. Do not rely on env vars for the target page; always resolve through the Notion MCP so the data stays current.
2. Call `mcp__claude_ai_Notion__notion-search` with the page name (or with a search term derived from the brief — e.g. the campaign name, event title, or speaker name) to find the target page. Use `query_type: "internal"` filtered to pages.
3. If a Notion URL was provided instead, extract the 32-char hex segment at the end as the page ID and call `mcp__claude_ai_Notion__notion-fetch` to confirm the page exists and you have access.
4. If multiple matches return, pick the most recently edited and note the choice in the run summary. Never proceed on an ambiguous match silently — if confidence is low, list the top 2-3 matches in the run summary and pick the best fit; flag it for the orchestrator to confirm.
5. If no page is resolvable (no matches, or the integration isn't shared with any matching page), skip this step and note in the run summary which search terms were tried.

**Invoke `upload-to-notion`** once per PNG (use the `@2x` variant by default for higher fidelity). Pass:

- `notion_api_key`: the token resolved above
- `source`: absolute path to the PNG (e.g. `[campaign-folder]/export/linkedin-card_[YYYYMMDD]_[TOPIC-SLUG]@2x.png`, suffixed with `_wine` / `_ink` / `_forest` if all three were produced)
- `target`: `page_block`
- `target_id`: the resolved page ID
- `block_type`: `image`
- `caption`: `LinkedIn promo card — [HEADLINE] ([gradient])`. Omit `([gradient])` if only one variant was produced.

**Report results**: list each uploaded file with the Notion URL and the new block ID returned by `upload-to-notion`. If any single upload fails, surface the error verbatim and continue with the remaining PNGs — do not abort the whole batch. If `upload-to-notion` returns a `## Partial success — block-append failed` block (Steps 1–2 succeeded but block-append exhausted its retry budget on a Notion 5xx / 429), copy that block **verbatim** into the run summary under the affected PNG — do not paraphrase, do not collapse it into a one-line note, do not strip the curl recipe. The block contains the `file_upload.id`, parent page URL, and the manual-retry recipe the user needs to finish the upload.

In cloud routines: `upload-to-notion` requires the Notion API token (from env or orchestrator) and the `mcp__claude_ai_Notion__*` tools (available if the Notion connector is enabled on the routine). If the connector isn't available, skip this step cleanly and tell the user in the run summary.

## Hard rules

- No emoji, ever.
- Sentence case for everything.
- No em dashes. Use periods or commas.
- American English.
- Always lowercase "hyperexponential". Never "hx Renew".
- Headline must fit on 2-3 lines at the variant's spec'd size (48px for 1-speaker, 76px for 2-speaker, 64px for 3- and 4-speaker) in the headline column. Tighten the copy before tightening the type.
- 5+ speakers is not supported. Ask the user to split.
- Coral (`--coral`) is forbidden on any gradient background.
- Output HTML inlines CSS, fonts (base64 `@font-face` rules from `fonts-inline-card.css`, including JetBrains Mono Regular), the wordmark lockup SVG (`hx-wordmark.svg`, outlined paths), and the grain/vignette layers. The gradient background references a local PNG in this skill's `assets/` folder by absolute path — Puppeteer rasterizes it into the exported PNG so the final deliverable remains a single self-contained file. No external network dependencies.
- Gemini Image is used for **photo cleanup only**. Never invent a speaker, never alter likeness, never generate background imagery.
- Every speaker must have a headshot. There is no no-photo fallback. A brief missing a photo for any speaker is a hard error — raise it explicitly and halt.

## Out of scope

- Square (1:1) and vertical (4:5) variants — flag and stop. Do not extrapolate pixel values from the 1.91:1 spec.
- Customer-quote, partnership, product-announcement, paid-ad LinkedIn cards.
- Figma write-back / Figma file generation.
- Multi-card carousels (use a separate skill / playbook).
