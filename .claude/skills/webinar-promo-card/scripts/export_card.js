#!/usr/bin/env node
/*
 * webinar-promo-card — Puppeteer PNG exporter
 *
 * Renders a webinar-promo card HTML at 1200x627 (LinkedIn 1.91:1) and
 * screenshots ONLY the .card element (so any host-page padding / dev chrome
 * is excluded). Saves both 1x and 2x retina PNGs.
 *
 * Usage:
 *   node export_card.js <html-path> <output-dir>
 *
 * Example:
 *   node export_card.js \
 *     "/path/to/campaigns/state-of-ai-2026/working/linkedin-card_20260326_state-of-ai.html" \
 *     "/path/to/campaigns/state-of-ai-2026/export"
 *
 * Outputs:
 *   <output-dir>/<slug>.png       (1200x627)
 *   <output-dir>/<slug>@2x.png    (2400x1254)
 *
 * Where <slug> is the html basename without the .html extension.
 *
 * Requires: puppeteer. Auto-installs on first use if missing (see below).
 */

const path = require("path");
const fs = require("fs");
const { execSync } = require("child_process");

function loadPuppeteer() {
  try {
    return require("puppeteer");
  } catch (firstErr) {
    const partial = fs.existsSync(path.join(__dirname, "node_modules", "puppeteer"));
    console.error(
      partial
        ? `puppeteer partial install detected → reinstalling in ${__dirname}`
        : `puppeteer missing → installing in ${__dirname}`,
    );
    if (partial) {
      fs.rmSync(path.join(__dirname, "node_modules", "puppeteer"), {
        recursive: true,
        force: true,
      });
    }
    execSync("npm install", { cwd: __dirname, stdio: "inherit" });
    try {
      return require("puppeteer");
    } catch (secondErr) {
      console.error("puppeteer still unavailable after reinstall — aborting.");
      console.error(secondErr);
      throw firstErr;
    }
  }
}

const puppeteer = loadPuppeteer();

async function run() {
  const [, , htmlPathArg, outDirArg] = process.argv;

  if (!htmlPathArg || !outDirArg) {
    console.error("Usage: node export_card.js <html-path> <output-dir>");
    process.exit(2);
  }

  const htmlPath = path.resolve(htmlPathArg);
  const outDir = path.resolve(outDirArg);

  if (!fs.existsSync(htmlPath)) {
    console.error(`HTML file not found: ${htmlPath}`);
    process.exit(2);
  }

  fs.mkdirSync(outDir, { recursive: true });

  const slug = path.basename(htmlPath, ".html");
  const fileUrl = "file://" + htmlPath;

  const browser = await puppeteer.launch({
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  try {
    for (const scale of [1, 2]) {
      const page = await browser.newPage();
      await page.setViewport({
        width: 1200,
        height: 627,
        deviceScaleFactor: scale,
      });

      await page.goto(fileUrl, { waitUntil: "networkidle0" });

      try {
        await page.evaluate(() => document.fonts.ready);
      } catch (_) {
        // some headless contexts return undefined; harmless
      }

      const card = await page.$(".card");
      if (!card) {
        throw new Error("Could not find .card element in the HTML.");
      }

      const suffix = scale === 1 ? "" : "@2x";
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
