# hero-images - curated catalog

This folder ships pre-cropped hero PNGs for the `linkedin-single-image-ad` skill so the compose step doesn't have to invoke Sharp for curated keys. Each hero key has three pre-cropped outputs - one per variant slot. The cropper script (`../scripts/crop_hero.js`) is still used at runtime for user-supplied images via the `hero_path` brief field.

## Slot dimensions

Locked in [`manifest.json`](manifest.json):

| Slot | Dimensions | Used by |
|---|---|---|
| `center` | 1080 x 600 | `light-center`, `gradient-center` (anchored bottom-flush, full canvas width) |
| `left` | 886 x 630 | `gradient-left` (anchored bottom-right with intentional bleed past the right and bottom edges) |
| `white-left` | 720 x 520 | `white-left` (anchored bottom-right within the canvas padding) |

## Curated keys

Each key ships with all three slot crops. The focal points (in the manifest) are tuned to keep the visually informative region centered after Sharp's `cover` resize.

### `portfolio`

- **Source**: `_source/portfolio.png` (987x632, real product UI screenshot of the hyperexponential portfolio dashboard).
- **What it is**: Hyperexponential portfolio dashboard with three KPI cards across the top (Charged premium 1224, New technical premium 1.8BN, New rate adequacy 96%), a Technical premium distribution histogram (with a hover tooltip showing "Number of policies 250 / New technical premium (M) 250"), and a Rate adequacy scatter chart on the right. Black laptop-frame chrome wraps the top and left edges; the bottom and right intentionally bleed off the canvas.
- **Focal point**: `[0.5, 0.4]` - horizontally centered, vertically just above center. Keeps the KPI row, histogram title, and chart body visible across all three slot crops.
- **Recommended variant pairings**:
  - `light-center`: ideal - full-bleed product mockup against cream is the canonical use of this asset.
  - `gradient-center`: ideal - same full-bleed treatment with brand gradient authority.
  - `gradient-left`: ideal - the bottom-right bleed of the `left` slot pairs naturally with the laptop-chrome treatment of the source.
  - `white-left`: ideal - the contained 720x520 panel reads cleanly with the dashboard's KPI row at the top of the crop.
- **Pre-cropped files**:
  - `portfolio--center.png` (1080x600)
  - `portfolio--left.png` (886x630)
  - `portfolio--white-left.png` (720x520)

## Re-cropping the catalog

The pre-cropped PNGs are produced by `../scripts/crop_hero.js` reading `manifest.json`. To regenerate (e.g. after editing a focal point or replacing a `_source/*.png`):

```
cd ".claude/skills/linkedin-single-image-ad"
node scripts/crop_hero.js hero-images/_source/portfolio.png center     hero-images/portfolio--center.png     --focal=0.5,0.4
node scripts/crop_hero.js hero-images/_source/portfolio.png left       hero-images/portfolio--left.png       --focal=0.5,0.4
node scripts/crop_hero.js hero-images/_source/portfolio.png white-left hero-images/portfolio--white-left.png --focal=0.5,0.4
```

## Adding new hero keys

1. Drop the source PNG into `_source/<new-key>.png` (full resolution, RGBA).
2. Add a new entry to `manifest.json` under `keys` with the source path, a focal point as `[fx, fy]` fractions in `[0, 1]`, and a short `description` of what the asset is.
3. Run `crop_hero.js` three times - one per slot - targeting `hero-images/<new-key>--<slot>.png`. See the "Re-cropping the catalog" block above for the invocation pattern.
4. Document the new key in this README under "Curated keys" with a "what it is" description, source dimensions, the chosen focal point, recommended variant pairings, and the three pre-cropped file names.
