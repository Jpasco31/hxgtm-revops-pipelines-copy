# Gradient asset paths

The canonical gradients are PNG renders in this skill's [`../assets/`](../assets/) folder. Used by [SKILL.md](../SKILL.md) Step 7 to fill the `{{GRADIENT_IMG_PATH}}` placeholder.

## Asset paths

Each color ships **three texture variants** (`01`, `02`, `03`). The base color is the same across all three variants of a color — only the gradient texture differs.

| Gradient | Variant | Base color | PNG asset |
|---|---|---|---|
| **Wine** | `01` *(default)* | `#3F0A20` | [`../assets/Burgundy 01.png`](../assets/Burgundy%2001.png) |
| **Wine** | `02` | `#3F0A20` | [`../assets/Burgundy 02.png`](../assets/Burgundy%2002.png) |
| **Wine** | `03` | `#3F0A20` | [`../assets/Burgundy 03.png`](../assets/Burgundy%2003.png) |
| **Ink** | `01` *(default)* | `#1C2733` | [`../assets/Dark blue 01.png`](../assets/Dark%20blue%2001.png) |
| **Ink** | `02` | `#1C2733` | [`../assets/Dark blue 02.png`](../assets/Dark%20blue%2002.png) |
| **Ink** | `03` | `#1C2733` | [`../assets/Dark blue 03.png`](../assets/Dark%20blue%2003.png) |
| **Forest** | `01` *(default)* | `#002625` | [`../assets/Deep Forest 01.png`](../assets/Deep%20Forest%2001.png) |
| **Forest** | `02` | `#002625` | [`../assets/Deep Forest 02.png`](../assets/Deep%20Forest%2002.png) |
| **Forest** | `03` | `#002625` | [`../assets/Deep Forest 03.png`](../assets/Deep%20Forest%2003.png) |

The brief's `variant` field selects `01` / `02` / `03` within the chosen color. It defaults to `01` when omitted, so existing briefs render unchanged. All nine PNGs are selectable.

## Recipe

Resolve the PNG from `(color, variant)`: pick the row matching the chosen color and variant, take its absolute path, and substitute it into the template's `{{GRADIENT_IMG_PATH}}` placeholder. The base color (`{{GRADIENT_BASE}}` and the headshot-cleanup `--gradient <hex>`) is **variant-independent** — it follows the color only. The template renders the PNG via:

```html
<div class="bg-base"><img class="gradient-img" src="{{GRADIENT_IMG_PATH}}" aria-hidden="true"></div>
```

`object-fit: cover` on `.gradient-img` ensures the PNG fills the 1200x627 canvas regardless of its native size.

## Why a file reference, not base64-inlined

These PNGs are 2.6–2.9 MB each — base64-inlining them would push the intermediate HTML past 10 MB. Puppeteer reads local files cleanly during PNG export, so the gradient is rasterized into the final PNG even though the HTML carries one external reference. The exported PNG remains a single self-contained deliverable.
