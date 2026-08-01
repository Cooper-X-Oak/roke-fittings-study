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
const frameDirectory = resolve(
  args["frame-dir"] ?? "docs/assets/ztovalve/hero/goal12-rokelike-animatic/frames-24",
);
const manifestPath = resolve(
  args.out ?? "docs/assets/ztovalve/hero/goal12-rokelike-animatic/animatic-manifest.json",
);

if (!url || !modulePath) {
  throw new Error("--url and --playwright-module are required");
}

await mkdir(frameDirectory, { recursive: true });
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
    viewport: { width: 960, height: 540 },
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
  await page.waitForFunction(() => window.__GOAL12_ANIMATIC__, null, {
    timeout: 45000,
  });
  const ready = await page.evaluate(() => window.__GOAL12_ANIMATIC__.waitForReady());
  const frames = [];
  const combined = createHash("sha256");

  for (let frame = 0; frame < ready.frameCount; frame += 1) {
    const state = await page.evaluate((index) => window.__GOAL12_ANIMATIC__.setFrame(index), frame);
    await page.waitForTimeout(80);
    const filename = `${String(frame + 1).padStart(4, "0")}.jpg`;
    const absolutePath = resolve(frameDirectory, filename);
    await page.locator("#stage").screenshot({
      path: absolutePath,
      type: "jpeg",
      quality: 88,
    });
    const bytes = (await stat(absolutePath)).size;
    const digest = await sha256(absolutePath);
    combined.update(`${frame}:${digest}:${bytes}\n`);
    frames.push({
      frame,
      filename,
      path: `docs/assets/ztovalve/hero/goal12-rokelike-animatic/frames-24/${filename}`,
      beat: state.name,
      split: Number(state.split.toFixed(4)),
      seat: Number(state.seat.toFixed(4)),
      axis: Number(state.axis.toFixed(4)),
      productYaw: Number(state.productYaw.toFixed(4)),
      bytes,
      sha256: digest,
    });
  }

  const manifest = {
    schemaVersion: 1,
    generatedAt: new Date().toISOString(),
    sourceUrl: url,
    preview: "docs/assets/ztovalve/hero/goal12-rokelike-animatic/preview.html",
    sourceStillDirection: "docs/assets/ztovalve/hero/goal11-rokelike-stills/",
    renderProfile: {
      width: ready.width,
      height: ready.height,
      dpr: 1,
      fps: ready.fps,
      frameCount: ready.frameCount,
      durationSeconds: ready.durationSeconds,
      kind: "24-frame low-resolution ROKE-like rhythm animatic",
      frameSequenceRendered: false,
      fullReleaseFrameCount: 0,
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
      "Goal 12 renders exactly 24 low-resolution review frames.",
      "No 240-frame release sequence is rendered or connected to the homepage.",
      "The animatic validates only rhythm, camera stability, and restrained axial motion.",
      "Final hold covers frames 21-24, satisfying the stable review endpoint requirement.",
      "Product and material claims remain unapproved until the client provides evidence.",
    ],
    consoleErrors,
    pageErrors,
    failedRequests,
    combinedFrameSha256: combined.digest("hex"),
    totalFrameBytes: frames.reduce((sum, frame) => sum + frame.bytes, 0),
    renderDurationMs: Math.round(performance.now() - startedAt),
    frames,
  };

  await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
  await context.close();
  process.stdout.write(`Captured ${frames.length} Goal 12 frames to ${frameDirectory}\n`);
} finally {
  await browser.close();
}
