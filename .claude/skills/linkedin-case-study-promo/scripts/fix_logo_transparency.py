#!/usr/bin/env python3
"""
fix_logo_transparency.py

Post-processes a partner logo PNG produced by nano-banana that has
hasAlpha: no (checkerboard baked as pixels). Two passes:

1. Convert bright white artwork to opaque white and dark background
   pixels to fully transparent (luminance threshold).
2. Auto-crop to the alpha bounding box so the PNG bounds equal the
   artwork bounds. This lets the template's max-width / max-height
   constraints fill the slot instead of scaling around dead padding.

Usage:
    python3 fix_logo_transparency.py <path-to-png>

The file is edited in place. Run after edit_image and before export.
Requires Pillow (pre-installed on this machine).
"""

import sys
from PIL import Image


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

    bbox = img.getbbox()
    if bbox is None:
        print(f"warning: image is fully transparent, skipping crop: {path}", file=sys.stderr)
        img.save(path)
        return

    pad = 4
    left, top, right, bottom = bbox
    left = max(0, left - pad)
    top = max(0, top - pad)
    right = min(img.width, right + pad)
    bottom = min(img.height, bottom + pad)
    cropped = img.crop((left, top, right, bottom))

    cropped.save(path)
    print(f"fixed: {path}  ({cropped.width}x{cropped.height}, hasAlpha: yes, cropped from {img.width}x{img.height})")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 fix_logo_transparency.py <path-to-png>", file=sys.stderr)
        sys.exit(2)
    fix(sys.argv[1])
