#!/usr/bin/env node
/*
 * linkedin-partnership-card - Puppeteer PNG exporter
 *
 * Renders a partnership card HTML at 1200x675 and screenshots ONLY the
 * .card element. Saves both 1x and 2x retina PNGs.
 *
 * Usage:
 *   node export_card.js <html-path> <output-dir>
 *
 * Example:
 *   node export_card.js \
 *     "/path/to/campaigns/acme-partnership/working/linkedin-partnership-card_20260501_acme.html" \
 *     "/path/to/campaigns/acme-partnership/export"
 *
 * Outputs:
 *   <output-dir>/<slug>.png       (1200x675)
 *   <output-dir>/<slug>@2x.png    (2400x1350)
 *
 * Where <slug> is the html basename without the .html extension.
 *
 * Requires: puppeteer. First-time install:
 *   cd ".claude/skills/linkedin-partnership-card/scripts"
 *   npm install
 */

const path = require('path');
const fs = require('fs');

async function run() {
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

  fs.mkdirSync(outDir, { recursive: true });

  const slug = path.basename(htmlPath, '.html');
  const fileUrl = 'file://' + htmlPath;

  let puppeteer;
  try {
    puppeteer = require('puppeteer');
  } catch (e) {
    console.error('puppeteer is not installed. From this script directory run:');
    console.error('  cd ".claude/skills/linkedin-partnership-card/scripts"');
    console.error('  npm install');
    process.exit(2);
  }

  const browser = await puppeteer.launch({
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  try {
    for (const scale of [1, 2]) {
      const page = await browser.newPage();
      await page.setViewport({
        width: 1200,
        height: 675,
        deviceScaleFactor: scale,
      });

      await page.goto(fileUrl, { waitUntil: 'networkidle0' });

      try {
        await page.evaluate(() => document.fonts.ready);
      } catch (_) {
        // Some headless contexts return undefined; harmless.
      }

      const card = await page.$('.card');
      if (!card) {
        throw new Error('Could not find .card element in the HTML.');
      }

      const box = await card.boundingBox();
      if (!box || Math.round(box.width) !== 1200 || Math.round(box.height) !== 675) {
        const actual = box ? `${Math.round(box.width)}x${Math.round(box.height)}` : 'unknown';
        throw new Error(`Expected .card to be 1200x675, got ${actual}.`);
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

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
