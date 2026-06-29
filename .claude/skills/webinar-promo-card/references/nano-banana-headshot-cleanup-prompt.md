# Nano-banana headshot cleanup — prompt and settings

Verbatim prompt for `nano-banana edit_image`. **Do not paraphrase, do not improvise** — the prompt is tuned to preserve likeness and prevent restyling. Used by [SKILL.md](../SKILL.md) Step 6.

## Prompt

```
Square 1:1 professional headshot crop. Center the subject's face on the upper third of the frame. Keep the subject's natural likeness, skin tone, hair, glasses, and clothing exactly as in the source. Do not restyle facial features, do not retouch beyond gentle exposure normalization, do not change makeup or hair. Replace the background with {{BACKDROP_INSTRUCTION}}. No text, no logos, no decorations, no studio props, no borders. Photographic, sharp focus on the eyes, neutral natural color.
```

## Backdrop instruction substitution

The `{{BACKDROP_INSTRUCTION}}` placeholder is filled in by [`scripts/cleanup_headshot.js`](../scripts/cleanup_headshot.js) at runtime:

- **`--gradient <hex>` (required)** → `a flat solid <hex> backdrop, uniform color edge-to-edge, with no gradient, no vignette, no shading, no texture variation, and no falloff`. The backdrop matches the card's base color so the headshot tile reads as part of the card. The script errors out if the flag is omitted — every cleanup run is tied to one gradient. Re-run cleanup per gradient when producing multiple gradient variants.

## Settings

- `aspect_ratio`: `"1:1"`
- `model`: `"pro"`
- `path`: absolute path to user's headshot
- `output_path`: `[campaign-folder]/working/headshots/[speaker-slug]_504.png`

## Definitions

- `[speaker-slug]` = lowercase kebab-case of the speaker's full name (e.g. "richard-gunn").
