#!/usr/bin/env node
/*
 * linkedin-partnership-card — Gemini Image partner-logo cleanup
 *
 * Calls Google's Gemini Image API ("Nano Banana") directly via @google/genai
 * to convert a partner logo to flat white artwork on a transparent background,
 * ready to place on the dark-navy dot-field partnership card. Used by step 3
 * of the linkedin-partnership-card skill.
 *
 * Usage:
 *   node cleanup_logo.js \
 *     --input <abs path to source logo> \
 *     --output <abs path to write cleaned PNG> \
 *     --prompt-file <abs path to prompt md> \
 *     [--model pro|flash] \
 *     [--aspect-ratio 16:9]
 *
 * Defaults:
 *   --model pro          → gemini-3-pro-image-preview
 *   anything else        → gemini-2.5-flash-image-preview
 *   --aspect-ratio 16:9
 *
 * Requires the GEMINI_API_KEY env var. Exits non-zero with the verbatim API
 * error on any failure. No retries, no fallback. Gemini typically bakes a
 * checkerboard pattern as pixel data instead of producing real transparency,
 * so the skill follows this script with `sips -g hasAlpha` and, when needed,
 * `scripts/fix_logo_transparency.py`.
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

async function cleanupLogo({
  input,
  output,
  promptFile,
  model = "pro",
  aspectRatio = "16:9",
}) {
  if (!input) throw new Error("--input is required");
  if (!output) throw new Error("--output is required");
  if (!promptFile) throw new Error("--prompt-file is required");

  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    throw new Error(
      "GEMINI_API_KEY env var is not set. The linkedin-partnership-card skill cannot run logo cleanup without it. Set GEMINI_API_KEY locally or as a secret on the routine.",
    );
  }

  const { GoogleGenAI } = require("@google/genai");

  const modelId =
    model === "pro" ? "gemini-3-pro-image-preview" : "gemini-2.5-flash-image-preview";

  const promptText = fs.readFileSync(promptFile, "utf-8");
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
  const result = await cleanupLogo({
    input: args.input,
    output: args.output,
    promptFile: args["prompt-file"],
    model: args.model || "pro",
    aspectRatio: args["aspect-ratio"] || "16:9",
  });
  console.log(`wrote ${result}`);
}

if (require.main === module) {
  main().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}

module.exports = { cleanupLogo };
