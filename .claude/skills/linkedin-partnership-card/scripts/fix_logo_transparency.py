#!/usr/bin/env python3
"""
fix_logo_transparency.py

Post-processes a partner logo PNG produced by Gemini Image (Nano Banana)
that has hasAlpha: no (checkerboard baked as pixels). Three passes:

1. Convert bright white artwork to opaque white and dark background
   pixels to fully transparent (luminance threshold).
2. Hard-clamp any sub-200 alpha to zero. The luminance pass leaves
   semi-transparent anti-aliasing pixels scattered across the full
   canvas (alpha = lum for 128 <= lum < ~200), which defeats getbbox()
   — without this pass, the bbox crop becomes a no-op on wordmark-only
   composites with internal padding (e.g. Allianz).
3. Auto-crop to the alpha bounding box so the PNG bounds equal the
   artwork bounds. This lets the template's max-width / max-height
   constraints fill the slot instead of scaling around dead padding.

Usage:
    python3 fix_logo_transparency.py <path-to-png>

The file is edited in place. Run after cleanup_logo.js and before
export. Requires Pillow (pre-installed on this machine).
"""

import sys
from PIL import Image

ALPHA_NOISE_THRESHOLD = 200


def fix(path: str) -> None:
    img = Image.open(path).convert("RGBA")
    pixels = img.load()

    for y in range(img.height):
        for x in range(img.width):
            r, g, b, _ = pixels[x, y]
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            if lum < 128:
                pixels[x, y] = (255, 255, 255, 0)
            else:
                pixels[x, y] = (255, 255, 255, int(lum))

    r, g, b, a = img.split()
    a_clamped = a.point(lambda v: v if v >= ALPHA_NOISE_THRESHOLD else 0)
    img = Image.merge("RGBA", (r, g, b, a_clamped))

    bbox = img.getbbox()
    if bbox is None:
        print(f"warning: image is fully transparent, skipping crop: {path}", file=sys.stderr)
        img.save(path)
        return

    cropped = img.crop(bbox)

    cropped.save(path)
    print(f"fixed: {path}  ({cropped.width}x{cropped.height}, hasAlpha: yes, cropped from {img.width}x{img.height})")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 fix_logo_transparency.py <path-to-png>", file=sys.stderr)
        sys.exit(2)
    fix(sys.argv[1])
