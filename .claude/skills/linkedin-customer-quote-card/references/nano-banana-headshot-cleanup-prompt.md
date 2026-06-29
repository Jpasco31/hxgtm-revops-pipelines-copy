# Nano-banana headshot cleanup — prompt and settings

Verbatim prompt for `cleanup_headshot.js` → Gemini Image API. **Do not paraphrase, do not improvise** — the prompt is tuned to preserve likeness and prevent restyling. Used by [SKILL.md](../SKILL.md) Step 3.

## Prompt

```
Square 1:1 professional headshot crop. Center the subject's face on the upper third of the frame. Keep the subject's natural likeness, skin tone, hair, glasses, and clothing exactly as in the source. Do not restyle facial features, do not retouch beyond gentle exposure normalization, do not change makeup or hair. Replace the background with {{BACKDROP_INSTRUCTION}}. No text, no logos, no decorations, no studio props, no borders. Photographic, sharp focus on the eyes, neutral natural color.
```

## Backdrop instruction substitution

The `{{BACKDROP_INSTRUCTION}}` placeholder is filled in by [`scripts/cleanup_headshot.js`](../scripts/cleanup_headshot.js) at runtime:

- **No `--gradient` flag** → `a flat, slightly desaturated dark backdrop matching the card palette`. Produces a neutral dark backdrop reusable across multiple variants.
- **`--gradient <hex>`** → `a flat solid <hex> backdrop, uniform color edge-to-edge, with no gradient, no vignette, no shading, no texture variation, and no falloff`. Produces a single-color backdrop tuned to one specific variant tile color. Re-run cleanup per variant if you use this.

The customer-quote-card skill calls the script **3 times per customer**, once per variant, each with the matching tile hex via `--gradient`. This produces a perfect tile-color match with no visible seam inside the avatar tile.

**Note on tile hexes**: The per-variant tile hexes below — `#0F1924` blue, `#330817` burgundy, `#002625` green — are the validated set. Gemini renders all three cleanly as flat solid backdrops with the verbatim prompt above and produces no teal fallback or visible seam against the card-side tile color.

## Per-variant tile hex

| Variant   | `--gradient` value |
|-----------|--------------------|
| `blue`    | `#0F1924`          |
| `burgundy`| `#330817`          |
| `green`   | `#002625`          |

## Settings

- `--aspect-ratio`: `1:1`
- `--model`: `pro` → `gemini-3-pro-image-preview`
- `--input`: absolute path to the customer's avatar / LinkedIn photo
- `--output`: `[campaign-folder]/working/assets/[customer-slug]-avatar-clean-[variant].png`

## Definitions

- `[customer-slug]` = lowercase kebab-case of the customer's name.
- `[variant]` = one of `blue`, `burgundy`, `green`.
