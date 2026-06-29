#!/usr/bin/env node
/*
 * linkedin-single-image-ad - Sharp-based focal-point hero cropper
 *
 * Crops a source image to one of the variant slot dimensions defined in
 * ../hero-images/manifest.json. Used (a) at scaffolding time to produce the
 * pre-cropped library committed under hero-images/, and (b) at compose time
 * for the user-supplied `hero_path` branch where the source is not in the
 * curated library.
 *
 * Algorithm:
 *   1. Read source dimensions.
 *   2. Compute the slot's aspect ratio from manifest.json.
 *   3. Resize the source so the smaller dimension fully covers the slot
 *      (`sharp.fit.cover` semantics - scale so both width and height are
 *      >= slot size, preserving aspect ratio).
 *   4. Compute the focal-point pixel position in the resized image.
 *   5. Extract a slot-sized region centered on the focal point, clamped to
 *      image bounds.
 *
 * Usage:
 *   node crop_hero.js <input-path> <slot> <output-path> [--focal=fx,fy] [--auto-focal]
 *
 *   <slot>          one of: center | left | white-left
 *   --focal=fx,fy   optional focal point as 0-1 fractions (default 0.5,0.5)
 *   --auto-focal    use Sharp's `attention` strategy (entropy-based smart crop)
 *                   when no --focal is supplied. Falls back to center if both
 *                   --focal and --auto-focal are absent.
 *
 * Examples:
 *   node crop_hero.js ./_source/dashboard.png center ./dashboard--center.png --focal=0.20,0.10
 *   node crop_hero.js /tmp/screenshot.png left /tmp/working/screenshot--left.png --auto-focal
 */

const fs = require('fs');
const path = require('path');

const MANIFEST_PATH = path.resolve(__dirname, '..', 'hero-images', 'manifest.json');

function parseArgs(argv) {
  const positional = [];
  const flags = { focal: null, autoFocal: false };
  for (const a of argv) {
    if (a.startsWith('--focal=')) {
      const raw = a.slice('--focal='.length);
      const parts = raw.split(',').map((s) => parseFloat(s.trim()));
      if (parts.length !== 2 || parts.some((n) => Number.isNaN(n))) {
        throw new Error(`Invalid --focal value: ${raw}. Expected fx,fy (each 0-1).`);
      }
      flags.focal = parts;
    } else if (a === '--auto-focal') {
      flags.autoFocal = true;
    } else {
      positional.push(a);
    }
  }
  return { positional, flags };
}

function clamp(n, lo, hi) {
  return Math.max(lo, Math.min(hi, n));
}

async function run() {
  const { positional, flags } = parseArgs(process.argv.slice(2));
  const [inputPath, slotName, outputPath] = positional;

  if (!inputPath || !slotName || !outputPath) {
    console.error('Usage: node crop_hero.js <input-path> <slot> <output-path> [--focal=fx,fy] [--auto-focal]');
    process.exit(2);
  }

  if (!fs.existsSync(inputPath)) {
    console.error(`Input file not found: ${inputPath}`);
    process.exit(2);
  }

  if (!fs.existsSync(MANIFEST_PATH)) {
    console.error(`Manifest not found: ${MANIFEST_PATH}`);
    process.exit(2);
  }

  const manifest = JSON.parse(fs.readFileSync(MANIFEST_PATH, 'utf8'));
  const slot = manifest.slots && manifest.slots[slotName];
  if (!slot) {
    const valid = Object.keys(manifest.slots || {}).join(', ');
    console.error(`Unknown slot "${slotName}". Valid slots: ${valid}`);
    process.exit(2);
  }

  let sharp;
  try {
    sharp = require('sharp');
  } catch (e) {
    console.error('sharp is not installed. From this script directory run:');
    console.error('  cd ".claude/skills/linkedin-single-image-ad/scripts"');
    console.error('  npm install');
    process.exit(2);
  }

  const slotW = slot.width;
  const slotH = slot.height;

  fs.mkdirSync(path.dirname(path.resolve(outputPath)), { recursive: true });

  if (flags.autoFocal && !flags.focal) {
    await sharp(inputPath)
      .resize(slotW, slotH, { fit: 'cover', position: sharp.strategy.attention })
      .png()
      .toFile(outputPath);
    console.log(`wrote ${outputPath} (${slotW}x${slotH}, auto-focal)`);
    return;
  }

  const focal = flags.focal || [0.5, 0.5];
  const [fx, fy] = focal;
  if (fx < 0 || fx > 1 || fy < 0 || fy > 1) {
    console.error(`--focal components must be in [0,1]. Got fx=${fx}, fy=${fy}.`);
    process.exit(2);
  }

  const meta = await sharp(inputPath).metadata();
  const srcW = meta.width;
  const srcH = meta.height;
  if (!srcW || !srcH) {
    console.error('Could not read source image dimensions.');
    process.exit(2);
  }

  const scale = Math.max(slotW / srcW, slotH / srcH);
  const resizedW = Math.ceil(srcW * scale);
  const resizedH = Math.ceil(srcH * scale);

  const focalPxX = fx * resizedW;
  const focalPxY = fy * resizedH;

  let extractLeft = Math.round(focalPxX - slotW / 2);
  let extractTop = Math.round(focalPxY - slotH / 2);

  extractLeft = clamp(extractLeft, 0, resizedW - slotW);
  extractTop = clamp(extractTop, 0, resizedH - slotH);

  await sharp(inputPath)
    .resize(resizedW, resizedH, { fit: 'fill' })
    .extract({ left: extractLeft, top: extractTop, width: slotW, height: slotH })
    .png()
    .toFile(outputPath);

  console.log(
    `wrote ${outputPath} (${slotW}x${slotH}, focal=${fx},${fy}, source=${srcW}x${srcH}, resized=${resizedW}x${resizedH}, extract=${extractLeft},${extractTop})`
  );
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
