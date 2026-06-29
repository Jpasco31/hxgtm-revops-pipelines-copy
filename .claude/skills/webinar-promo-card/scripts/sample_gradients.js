#!/usr/bin/env node
// Converts each PNG in ../assets/ into a sub-2KB SVG gradient by
// downsampling the PNG to a tiny canvas (preserves colors via area
// averaging) and embedding it inside an SVG with a Gaussian blur filter.
//
// Usage: node sample_gradients.js [--downsample 32] [--blur 10]

const fs = require("fs");
const path = require("path");
const puppeteer = require("puppeteer");

const ASSETS_DIR = path.resolve(__dirname, "..", "assets");
const DOWNSAMPLE_W = Number(process.env.DOWNSAMPLE_W || 32);
const DOWNSAMPLE_H = Number(process.env.DOWNSAMPLE_H || 20);
const BLUR_STD_DEV = Number(process.env.BLUR_STD_DEV || 8);

// Map "Burgundy 01.png" -> "gradient-burgundy-01.svg" (and so on).
function targetName(srcBasename) {
  const stem = srcBasename.replace(/\.png$/i, "");
  const m = stem.match(/^(.+?)\s+(\d+)$/);
  if (!m) return `gradient-${stem.toLowerCase().replace(/\s+/g, "-")}.svg`;
  const themeRaw = m[1].toLowerCase().trim();
  const themeMap = {
    "burgundy": "burgundy",
    "dark blue": "ink",
    "deep forest": "forest",
  };
  const theme = themeMap[themeRaw] || themeRaw.replace(/\s+/g, "-");
  return `gradient-${theme}-${m[2]}.svg`;
}

async function downsampleToDataURL(page, srcPath, w, h) {
  const buf = fs.readFileSync(srcPath);
  const b64 = buf.toString("base64");
  return page.evaluate(
    async ({ b64, w, h }) => {
      const img = new Image();
      img.src = "data:image/png;base64," + b64;
      await img.decode();
      const c = document.createElement("canvas");
      c.width = w; c.height = h;
      const ctx = c.getContext("2d");
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = "high";
      ctx.drawImage(img, 0, 0, w, h);
      return c.toDataURL("image/png");
    },
    { b64, w, h }
  );
}

function buildSvg(dataUrl, viewBoxW, viewBoxH) {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${viewBoxW} ${viewBoxH}" preserveAspectRatio="xMidYMid slice">
  <filter id="b" x="-10%" y="-10%" width="120%" height="120%">
    <feGaussianBlur stdDeviation="${BLUR_STD_DEV}"/>
  </filter>
  <image href="${dataUrl}" x="0" y="0" width="${viewBoxW}" height="${viewBoxH}" preserveAspectRatio="none" filter="url(#b)"/>
</svg>
`;
}

(async () => {
  const pngs = fs
    .readdirSync(ASSETS_DIR)
    .filter((f) => f.toLowerCase().endsWith(".png"))
    .sort();
  if (pngs.length === 0) {
    console.error("No PNGs in", ASSETS_DIR);
    process.exit(1);
  }
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  for (const png of pngs) {
    const src = path.join(ASSETS_DIR, png);
    const dataUrl = await downsampleToDataURL(page, src, DOWNSAMPLE_W, DOWNSAMPLE_H);
    const svg = buildSvg(dataUrl, 1200, 627);
    const out = path.join(ASSETS_DIR, targetName(png));
    fs.writeFileSync(out, svg);
    const bytes = fs.statSync(out).size;
    console.log(`${png} -> ${path.basename(out)}  (${bytes} bytes)`);
  }
  await browser.close();
})();
