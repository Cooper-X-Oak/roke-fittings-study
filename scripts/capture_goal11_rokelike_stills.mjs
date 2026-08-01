#!/usr/bin/env node

import { createHash } from "node:crypto";
import { mkdir, readFile, stat, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { pathToFileURL } from "node:url";

function parseArgs(argv) {
  const result = {};
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index];
    const value = argv[index + 1];
    if (!key?.startsWith("--") || value === undefined) {
      throw new Error(`Invalid argument sequence near ${key ?? "<end>"}`);
    }
    result[key.slice(2)] = value;
  }
  return result;
}

async function sha256(path) {
  return createHash("sha256").update(await readFile(path)).digest("hex");
}

const args = parseArgs(process.argv.slice(2));
const url = args.url;
const modulePath = args["playwright-module"];
const browserExecutable = args["browser-executable"];
const outputDirectory = resolve(
  args["out-dir"] ?? "docs/assets/ztovalve/hero/goal11-rokelike-stills",
);
const manifestPath = resolve(
  args.out ?? "docs/assets/ztovalve/hero/goal11-rokelike-stills/still-manifest.json",
);

if (!url || !modulePath) {
  throw new Error("--url and --playwright-module are required");
}

await mkdir(outputDirectory, { recursive: true });
await mkdir(dirname(manifestPath), { recursive: true });

const playwright = await import(pathToFileURL(resolve(modulePath)).href);
const chromium = playwright.chromium ?? playwright.default?.chromium;
if (!chromium) {
  throw new Error("Could not resolve chromium from playwright-core module");
}

const browser = await chromium.launch({
  headless: true,
  executablePath: browserExecutable || undefined,
  args: ["--enable-gpu", "--enable-webgl", "--ignore-gpu-blocklist"],
});

const startedAt = performance.now();
try {
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
    reducedMotion: "no-preference",
  });
  const page = await context.newPage();
  const consoleErrors = [];
  const pageErrors = [];
  const failedRequests = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("requestfailed", (request) => {
    failedRequests.push({
      url: request.url(),
      failure: request.failure()?.errorText ?? "unknown",
    });
  });

  await page.goto(url, { waitUntil: "networkidle" });
  await page.waitForFunction(() => window.__GOAL11_STILLS__, null, {
    timeout: 45000,
  });
  const ready = await page.evaluate(() => window.__GOAL11_STILLS__.waitForReady());
  const states = await page.evaluate(() => window.__GOAL11_STILLS__.states);
  const stills = [];
  const combined = createHash("sha256");

  for (let index = 0; index < states.length; index += 1) {
    const state = await page.evaluate((stillIndex) => window.__GOAL11_STILLS__.setStill(stillIndex), index);
    await page.waitForTimeout(160);
    const filename = state.filename;
    const path = resolve(outputDirectory, filename);
    await page.locator("#stage").screenshot({
      path,
      type: "jpeg",
      quality: 90,
    });
    const bytes = (await stat(path)).size;
    const digest = await sha256(path);
    combined.update(`${state.id}:${digest}:${bytes}\n`);
    stills.push({
      id: state.id,
      name: state.name,
      noteTitle: state.noteTitle,
      noteBody: state.noteBody,
      filename,
      path: `docs/assets/ztovalve/hero/goal11-rokelike-stills/${filename}`,
      bytes,
      sha256: digest,
    });
    process.stdout.write(`captured ${state.id} ${filename}\n`);
  }

  const manifest = {
    schemaVersion: 1,
    generatedAt: new Date().toISOString(),
    sourceUrl: url,
    preview: "docs/assets/ztovalve/hero/goal11-rokelike-stills/preview.html",
    renderProfile: {
      width: 1920,
      height: 1080,
      dpr: 1,
      kind: "six-keyframe ROKE-like hero still direction draft",
      frameSequenceRendered: false,
    },
    ready,
    browser: {
      userAgent: await page.evaluate(() => navigator.userAgent),
      renderer: await page.evaluate(() => {
        const canvas = document.querySelector("#hero-canvas");
        const gl = canvas.getContext("webgl2") || canvas.getContext("webgl");
        const extension = gl?.getExtension("WEBGL_debug_renderer_info");
        return extension ? gl.getParameter(extension.UNMASKED_RENDERER_WEBGL) : "unavailable";
      }),
    },
    constraints: [
      "No 240-frame render is produced in Goal 11.",
      "The subject remains visually stable in the hero frame.",
      "Motion grammar is limited to restrained horizontal axial assembly, a controlled axis cue, and a small assembled-product turn.",
      "Small hardware must read as detail texture, not as independent flying parts.",
      "This is a direction draft; material and product claims still require client approval before final homepage copy.",
    ],
    consoleErrors,
    pageErrors,
    failedRequests,
    combinedStillSha256: combined.digest("hex"),
    totalBytes: stills.reduce((sum, still) => sum + still.bytes, 0),
    renderDurationMs: Math.round(performance.now() - startedAt),
    stills,
  };
  await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
  await context.close();
  process.stdout.write(`Captured ${stills.length} stills to ${outputDirectory}\n`);
} finally {
  await browser.close();
}
