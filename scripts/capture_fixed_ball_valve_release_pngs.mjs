#!/usr/bin/env node

import { createHash } from "node:crypto";
import { mkdir, readFile, readdir, stat, writeFile } from "node:fs/promises";
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
const frameDirectory = resolve(args["frame-dir"] ?? ".scratch/goal9-release-png-240");
const outputPath = resolve(args.out ?? "docs/assets/ztovalve/hero/release-render-manifest.json");

if (!url || !modulePath) {
  throw new Error("--url and --playwright-module are required");
}

await mkdir(frameDirectory, { recursive: true });
const existing = await readdir(frameDirectory);
if (existing.some((name) => /^\d{4}\.png$/u.test(name))) {
  throw new Error(`Frame directory already contains PNG frames: ${frameDirectory}`);
}
await mkdir(dirname(outputPath), { recursive: true });

const playwright = await import(pathToFileURL(modulePath).href);
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
  await page.waitForFunction(() => window.__FIXED_BALL_ANIMATIC__, null, {
    timeout: 45000,
  });
  const ready = await page.evaluate(() => window.__FIXED_BALL_ANIMATIC__.waitForReady());
  const frames = [];
  const combined = createHash("sha256");
  for (let frame = 0; frame < ready.frameCount; frame += 1) {
    const capture = await page.evaluate(
      (index) => window.__FIXED_BALL_ANIMATIC__.captureFrame(index),
      frame,
    );
    const filename = `${String(frame + 1).padStart(4, "0")}.png`;
    const absolutePath = resolve(frameDirectory, filename);
    const dataUrl = capture.pngDataUrl;
    await writeFile(
      absolutePath,
      Buffer.from(dataUrl.slice(dataUrl.indexOf(",") + 1), "base64"),
    );
    const digest = await sha256(absolutePath);
    const bytes = (await stat(absolutePath)).size;
    combined.update(`${frame}:${digest}:${bytes}\n`);
    frames.push({
      frame,
      filename,
      shotId: capture.shotId,
      bytes,
      sha256: digest,
    });
    if (frame % 30 === 0 || frame === ready.frameCount - 1) {
      process.stdout.write(`captured ${frame + 1}/${ready.frameCount}\n`);
    }
  }

  const manifest = {
    schemaVersion: 1,
    generatedAt: new Date().toISOString(),
    sourceUrl: url,
    sourcePreview: "docs/assets/ztovalve/hero/animatic-preview.html",
    sourcePrevis: "docs/assets/ztovalve/hero/camera-previs-240.json",
    pngFrameDirectory: frameDirectory.replace(/\\/g, "/"),
    renderProfile: {
      width: ready.renderWidth,
      height: ready.renderHeight,
      dpr: 1,
      fps: ready.fps,
      frameCount: ready.frameCount,
      kind: "transparent product-only release source frames",
    },
    ready,
    browser: {
      userAgent: await page.evaluate(() => navigator.userAgent),
      renderer: await page.evaluate(() => {
        const canvas = document.querySelector("#animatic-canvas");
        const gl = canvas.getContext("webgl2") || canvas.getContext("webgl");
        const extension = gl?.getExtension("WEBGL_debug_renderer_info");
        return extension ? gl.getParameter(extension.UNMASKED_RENDERER_WEBGL) : "unavailable";
      }),
    },
    consoleErrors,
    pageErrors,
    failedRequests,
    combinedPngFrameSha256: combined.digest("hex"),
    totalPngBytes: frames.reduce((sum, frame) => sum + frame.bytes, 0),
    renderDurationMs: Math.round(performance.now() - startedAt),
    frames,
  };
  await writeFile(outputPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
  await context.close();
  process.stdout.write(`Captured ${frames.length} transparent release frames to ${frameDirectory}\n`);
} finally {
  await browser.close();
}
