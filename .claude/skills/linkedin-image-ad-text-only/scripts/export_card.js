#!/usr/bin/env node
/*
 * linkedin-image-ad-text-only - Puppeteer PNG exporter
 *
 * Renders a 1080x1080 text-only LinkedIn ad HTML and screenshots ONLY
 * the .card element. Saves both 1x and 2x PNG files.
 *
 * Usage:
 *   node export_card.js <html-path> <output-dir>
 */

const path = require('path');
const fs = require('fs');

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

  fs.mkdirSync(outDir, { recursive: true });

  const slug = path.basename(htmlPath, '.html');
  const fileUrl = 'file://' + htmlPath;

  let puppeteer;
  try {
    puppeteer = require('puppeteer');
  } catch (e) {
    console.error('puppeteer is not installed. From this script directory run:');
    console.error('  cd ".claude/skills/linkedin-image-ad-text-only/scripts"');
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

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
