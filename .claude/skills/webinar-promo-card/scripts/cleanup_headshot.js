#!/usr/bin/env node
/*
 * webinar-promo-card — Gemini Image headshot cleanup
 *
 * Calls Google's Gemini Image API ("Nano Banana") directly via @google/genai
 * to neutralize a headshot's background, square-crop, and normalize exposure
 * without altering the subject's likeness. Used by step 6 of the
 * webinar-promo-card skill.
 *
 * Usage:
 *   node cleanup_headshot.js \
 *     --input <abs path to source headshot> \
 *     --output <abs path to write cleaned PNG> \
 *     --prompt-file <abs path to prompt md> \
 *     [--model pro|flash] \
 *     [--aspect-ratio 1:1] \
 *     [--gradient <#hex>]
 *
 * Defaults:
 *   --model pro          → gemini-3-pro-image-preview
 *   anything else        → gemini-2.5-flash-image-preview
 *   --aspect-ratio 1:1
 *   --gradient (omitted) → neutral dark backdrop reusable across all variants
 *
 * When --gradient is provided, the {{BACKDROP_INSTRUCTION}} placeholder in the
 * prompt is replaced with a solid-color instruction (uniform fill, no gradient,
 * no vignette) keyed to that hex. Re-run cleanup per gradient if you use this.
 *
 * Requires the GEMINI_API_KEY env var. Exits non-zero with the verbatim API
 * error on any failure. No retries, no fallback.
 */

const fs = require("fs");
const path = require("path");

const MIME_BY_EXT = {
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".gif": "image/gif",
};

function inferMimeType(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  const mime = MIME_BY_EXT[ext];
  if (!mime) {
    throw new Error(
      `Unsupported image extension "${ext}" for input ${filePath}. Supported: ${Object.keys(MIME_BY_EXT).join(", ")}`,
    );
  }
  return mime;
}

function parseArgs(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith("--")) continue;
    const key = a.slice(2);
    const next = argv[i + 1];
    if (next === undefined || next.startsWith("--")) {
      args[key] = true;
    } else {
      args[key] = next;
      i++;
    }
  }
  return args;
}

function backdropInstruction(gradient) {
  if (!gradient) {
    throw new Error(
      '--gradient is required (e.g. --gradient "#3F0A20"). The cleaned headshot backdrop must match a card gradient.',
    );
  }
  const hex = gradient.trim();
  if (!/^#[0-9a-fA-F]{6}$/.test(hex)) {
    throw new Error(
      `--gradient must be a 6-digit hex like "#3F0A20" (got "${gradient}")`,
    );
  }
  return `a flat solid ${hex.toUpperCase()} backdrop, uniform color edge-to-edge, with no gradient, no vignette, no shading, no texture variation, and no falloff`;
}

async function cleanupHeadshot({
  input,
  output,
  promptFile,
  model = "pro",
  aspectRatio = "1:1",
  gradient,
}) {
  if (!input) throw new Error("--input is required");
  if (!output) throw new Error("--output is required");
  if (!promptFile) throw new Error("--prompt-file is required");

  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    throw new Error(
      "GEMINI_API_KEY env var is not set. The webinar-promo-card skill cannot run headshot cleanup without it. Set GEMINI_API_KEY locally or as a secret on the routine.",
    );
  }

  const { GoogleGenAI } = require("@google/genai");

  const modelId =
    model === "pro" ? "gemini-3-pro-image-preview" : "gemini-2.5-flash-image-preview";

  const rawPrompt = fs.readFileSync(promptFile, "utf-8");
  const promptText = rawPrompt.replace(
    /\{\{BACKDROP_INSTRUCTION\}\}/g,
    backdropInstruction(gradient),
  );
  const imageBytes = fs.readFileSync(input);
  const mimeType = inferMimeType(input);

  const ai = new GoogleGenAI({ apiKey });

  const response = await ai.models.generateContent({
    model: modelId,
    contents: [
      {
        role: "user",
        parts: [
          { text: promptText },
          {
            inlineData: {
              mimeType,
              data: imageBytes.toString("base64"),
            },
          },
        ],
      },
    ],
    config: {
      imageConfig: {
        aspectRatio,
      },
    },
  });

  const parts = (response && response.candidates && response.candidates[0]
    && response.candidates[0].content && response.candidates[0].content.parts) || [];
  const imagePart = parts.find((p) => p.inlineData && p.inlineData.data);
  if (!imagePart) {
    throw new Error(
      "Gemini response contained no image data. Raw response: " +
        JSON.stringify(response),
    );
  }

  const outBytes = Buffer.from(imagePart.inlineData.data, "base64");
  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.writeFileSync(output, outBytes);

  return output;
}

async function main() {
  const args = parseArgs(process.argv);
  const result = await cleanupHeadshot({
    input: args.input,
    output: args.output,
    promptFile: args["prompt-file"],
    model: args.model || "pro",
    aspectRatio: args["aspect-ratio"] || "1:1",
    gradient: args.gradient,
  });
  console.log(`wrote ${result}`);
}

if (require.main === module) {
  main().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}

module.exports = { cleanupHeadshot };
