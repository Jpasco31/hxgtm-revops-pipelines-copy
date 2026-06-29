#!/usr/bin/env node
/*
 * design-system — verify font-weight → face resolution in the card bundle.
 *
 * Proves (not eyeballs) that every weight a card template requests resolves to
 * the intended Acid Grotesk / JetBrains Mono face once Chromium renders the
 * inlined `fonts-inline-card.css` bundle. It builds a tiny self-contained HTML
 * that requests each weight, loads it in headless Chromium (the same engine the
 * export pipeline uses), then asks the DevTools Protocol which platform font
 * actually painted each element via `CSS.getPlatformFontsForNode`.
 *
 * Backs the design-system font-weight fix: Book must resolve at 350 (not snap
 * to 300 Light), Regular at 400, Medium at 500.
 *
 * Usage:   node verify_fonts_inline.js
 * Exit 0 = every weight resolved to its expected face. Exit 1 = a mismatch.
 *
 * Reuses the puppeteer install from a sibling card skill — no deps of its own.
 */

const path = require("path");
const fs = require("fs");
const os = require("os");

const HERE = __dirname;
const CARD_CSS = path.resolve(HERE, "..", "tokens", "fonts-inline-card.css");

function loadPuppeteer() {
  const candidates = [
    path.resolve(HERE, "..", "..", "webinar-promo-card", "scripts", "node_modules", "puppeteer"),
    path.resolve(HERE, "..", "..", "linkedin-customer-quote-card", "scripts", "node_modules", "puppeteer"),
  ];
  for (const c of candidates) {
    if (fs.existsSync(c)) return require(c);
  }
  return require("puppeteer");
}

const puppeteer = loadPuppeteer();

// Each probe requests a weight/family; `expect` is the platform font name
// Chromium should report it painted with. By default we substring-match; the
// Regular (Roman) cut carries no style suffix — it reports the bare family
// name — so it asserts an exact match to avoid colliding with "… Book" etc.
const PROBES = [
  { id: "ag300", family: "'FFF Acid Grotesk'", weight: 300, expect: "Light",            label: "Acid Grotesk 300 → Light" },
  { id: "ag350", family: "'FFF Acid Grotesk'", weight: 350, expect: "Book",             label: "Acid Grotesk 350 → Book" },
  { id: "ag400", family: "'FFF Acid Grotesk'", weight: 400, expect: "FFF Acid Grotesk", exact: true, label: "Acid Grotesk 400 → Regular" },
  { id: "ag500", family: "'FFF Acid Grotesk'", weight: 500, expect: "Medium",           label: "Acid Grotesk 500 → Medium" },
  { id: "jm400", family: "'JetBrains Mono'",   weight: 400, expect: "JetBrains",         label: "JetBrains Mono 400 → Regular" },
];

function buildHtml(cardCss) {
  const blocks = PROBES.map(
    (p) =>
      `<p id="${p.id}" style="font-family:${p.family};font-weight:${p.weight};font-size:48px;margin:0;">${p.label} — Hxgj 0123</p>`,
  ).join("\n");
  return `<!doctype html><html><head><meta charset="utf-8"><style>
${cardCss}
body{background:#111;color:#fff;padding:40px;}
</style></head><body>
${blocks}
</body></html>`;
}

async function run() {
  if (!fs.existsSync(CARD_CSS)) {
    console.error(`Bundle not found: ${CARD_CSS} — run regenerate_fonts_inline.js first.`);
    process.exit(2);
  }

  const tmpHtml = path.join(os.tmpdir(), `verify-fonts-${process.pid}.html`);
  fs.writeFileSync(tmpHtml, buildHtml(fs.readFileSync(CARD_CSS, "utf8")));

  const browser = await puppeteer.launch({
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  const results = [];
  try {
    const page = await browser.newPage();
    await page.goto("file://" + tmpHtml, { waitUntil: "networkidle0" });
    try {
      await page.evaluate(() => document.fonts.ready);
    } catch (_) {
      /* harmless in some headless contexts */
    }

    const client = await page.target().createCDPSession();
    await client.send("DOM.enable");
    await client.send("CSS.enable");
    const { root } = await client.send("DOM.getDocument", { depth: -1 });

    for (const probe of PROBES) {
      const { nodeId } = await client.send("DOM.querySelector", {
        nodeId: root.nodeId,
        selector: `#${probe.id}`,
      });
      const { fonts } = await client.send("CSS.getPlatformFontsForNode", { nodeId });
      const painted = (fonts || []).slice().sort((a, b) => (b.glyphCount || 0) - (a.glyphCount || 0));
      const familyName = painted[0] ? painted[0].familyName : "(none)";
      const ok = probe.exact ? familyName === probe.expect : familyName.includes(probe.expect);
      results.push({ probe, familyName, ok });
    }
  } finally {
    await browser.close();
    fs.rmSync(tmpHtml, { force: true });
  }

  let failed = 0;
  console.log("\nfont-weight → face resolution (via CSS.getPlatformFontsForNode):\n");
  for (const r of results) {
    if (!r.ok) failed++;
    console.log(
      `  [${r.ok ? "PASS" : "FAIL"}] ${r.probe.label.padEnd(34)} painted: ${r.familyName}` +
        (r.ok ? "" : `  (expected to contain "${r.probe.expect}")`),
    );
  }
  console.log("");
  if (failed > 0) {
    console.error(`${failed} weight(s) did not resolve to the expected face.`);
    process.exit(1);
  }
  console.log("All weights resolved to their intended faces.");
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
