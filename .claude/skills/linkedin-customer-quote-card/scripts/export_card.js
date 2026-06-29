#!/usr/bin/env node
/*
 * linkedin-customer-quote-card - Puppeteer PNG exporter
 *
 * Renders a customer quote card HTML at 1080x1080 and screenshots ONLY the
 * .card element. Generates 3 variants (blue, burgundy, green).
 * Saves both 1x and 2x retina PNGs for each.
 *
 * Usage (for one HTML):
 *   node export_card.js <html-path> <output-dir>
 *
 * The SKILL.md pipeline calls this 3 times, once per pattern variant.
 *
 * Requires: puppeteer. First-time install:
 *   cd "Projects/Rev Ops Pipelines/.claude/.claude/skills/linkedin-customer-quote-card/scripts"
 *   npm init -y && npm install puppeteer
 */

const path = require('path');
const fs = require('fs');

// The skill bakes each variant's tile color into the headshot itself, so a
// theme-<variant> card MUST reference the matching ...-<variant>.png avatar.
// Catches the easy-to-miss case of (e.g.) a blue card wired to the burgundy
// headshot. Returns { ok: true } or { ok: false, message } — never throws.
function checkVariantConsistency(html) {
  const themeMatch = html.match(/class="card theme-(blue|burgundy|green)"/);
  if (!themeMatch) {
    return { ok: true }; // no recognizable theme class; nothing to enforce
  }
  const theme = themeMatch[1];

  const avatarMatch = html.match(/class="avatar"\s+src="([^"]*)"/);
  if (!avatarMatch) {
    return { ok: true }; // no avatar img; nothing to enforce
  }
  const src = avatarMatch[1];
  const base = src.split('/').pop() || src;
  const variantTok = base.match(/-(blue|burgundy|green)\.png$/i);
  if (!variantTok) {
    // Avatar filename doesn't follow the -<variant>.png convention — warn, don't block.
    console.warn(
      `[export_card] warning: card theme is "${theme}" but avatar src "${src}" has no ` +
      `recognizable -<variant>.png suffix; cannot verify variant match.`,
    );
    return { ok: true };
  }
  const avatarVariant = variantTok[1].toLowerCase();
  if (avatarVariant !== theme) {
    return {
      ok: false,
      message:
        `Variant mismatch: card theme is "${theme}" but the avatar "${src}" is the ` +
        `"${avatarVariant}" variant. A ${theme} card must use the ` +
        `…-avatar-clean-${theme}.png headshot (its backdrop is baked to the ${theme} tile ` +
        `color). Re-check Step 4 avatar wiring in SKILL.md and re-compose this variant.`,
    };
  }
  return { ok: true };
}

async function run() {
  const CARD_WIDTH = 1080;
  const CARD_HEIGHT = 1080;
  const [, , htmlPathArg, outDirArg] = process.argv;

  if (!htmlPathArg || !outDirArg) {
    console.error('Usage: node export_card.js <html-path> <output-dir>');
    process.exit(2);
  }

  const htmlPath = path.resolve(htmlPathArg);
  const outDir = path.resolve(outDirArg);

  if (!fs.existsSync(htmlPath)) {
    console.error(`HTML file not found: ${htmlPath}`);
    process.exit(2);
  }

  const htmlSource = fs.readFileSync(htmlPath, 'utf-8');
  const variantCheck = checkVariantConsistency(htmlSource);
  if (!variantCheck.ok) {
    console.error(variantCheck.message);
    process.exit(2);
  }

  fs.mkdirSync(outDir, { recursive: true });

  const slug = path.basename(htmlPath, '.html');
  const fileUrl = 'file://' + htmlPath;

  let puppeteer;
  try {
    puppeteer = require('puppeteer');
  } catch (e) {
    console.error('puppeteer is not installed. From this script directory run:');
    console.error('  cd "Projects/Rev Ops Pipelines/.claude/.claude/skills/linkedin-customer-quote-card/scripts"');
    console.error('  npm init -y && npm install puppeteer');
    process.exit(2);
  }

  const browser = await puppeteer.launch({
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  try {
    for (const scale of [1, 2]) {
      const page = await browser.newPage();
      await page.setViewport({
        width: CARD_WIDTH,
        height: CARD_HEIGHT,
        deviceScaleFactor: scale,
      });

      await page.goto(fileUrl, { waitUntil: 'networkidle0' });

      try {
        await page.evaluate(() => document.fonts.ready);
      } catch (_) {}

      const card = await page.$('.card');
      if (!card) {
        throw new Error('Could not find .card element in the HTML.');
      }

      const box = await card.boundingBox();
      if (!box || Math.round(box.width) !== CARD_WIDTH || Math.round(box.height) !== CARD_HEIGHT) {
        const actual = box ? `${Math.round(box.width)}x${Math.round(box.height)}` : 'unknown';
        throw new Error(`Expected .card to be ${CARD_WIDTH}x${CARD_HEIGHT}, got ${actual}.`);
      }

      const suffix = scale === 1 ? '' : '@2x';
      const outPath = path.join(outDir, `${slug}${suffix}.png`);

      await card.screenshot({ path: outPath, omitBackground: false });
      console.log(`wrote ${outPath}`);

      await page.close();
    }
  } finally {
    await browser.close();
  }
}

if (require.main === module) {
  run().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}

module.exports = { checkVariantConsistency };
