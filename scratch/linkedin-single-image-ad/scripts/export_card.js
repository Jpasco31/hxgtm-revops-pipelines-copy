#!/usr/bin/env node
/*
 * linkedin-single-image-ad - Puppeteer PNG exporter
 *
 * Renders a linkedin-single-image-ad card HTML at 1080x1080 (LinkedIn 1:1) and
 * screenshots ONLY the .card element (so any host-page padding / dev chrome
 * is excluded). Saves both 1x and 2x retina PNGs.
 *
 * Usage:
 *   node export_card.js <html-path> <output-dir>
 *
 * Example:
 *   node export_card.js \
 *     "/path/to/campaigns/foo/working/linkedin-ad_20260618_my-topic.html" \
 *     "/path/to/campaigns/foo/export"
 *
 * Outputs:
 *   <output-dir>/<slug>.png       (1080x1080)
 *   <output-dir>/<slug>@2x.png    (2160x2160)
 *
 * Where <slug> is the html basename without the .html extension.
 *
 * Requires: puppeteer. First-time install:
 *   cd ".claude/skills/linkedin-single-image-ad/scripts"
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
    console.error('  cd ".claude/skills/linkedin-single-image-ad/scripts"');
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
        width: 1080,
        height: 1080,
        deviceScaleFactor: scale,
      });

      await page.goto(fileUrl, { waitUntil: 'networkidle0' });

      try {
        await page.evaluate(() => document.fonts.ready);
      } catch (_) {
        // some headless contexts return undefined; harmless
      }

      const card = await page.$('.card');
      if (!card) {
        throw new Error('Could not find .card element in the HTML.');
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
