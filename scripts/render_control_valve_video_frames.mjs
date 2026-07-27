#!/usr/bin/env node

import { copyFile, mkdir, readFile, readdir, stat, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
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
  const bytes = await readFile(path);
  return createHash("sha256").update(bytes).digest("hex");
}

const args = parseArgs(process.argv.slice(2));
const url = args.url;
const modulePath = args["playwright-module"];
const browserExecutable = args["browser-executable"];
const frameDirectory = resolve(
  args["frame-dir"] ?? "D:/Temp/control-valve-video-frames",
);
const outputPath = resolve(
  args.out ?? "creative/control-valve-video/render-manifest.json",
);
const posterPath = resolve(
  args.poster ?? "docs/control-valve-video/assets/first-frame.png",
);
const viewport = { width: 1280, height: 800 };
const cameraPrevis = JSON.parse(await readFile(resolve("creative/control-valve/camera-previs.json"), "utf8"));
const fps = cameraPrevis.fps;
const frameCount = cameraPrevis.totalFrames;

if (!url || !modulePath) {
  throw new Error("--url and --playwright-module are required");
}

await mkdir(frameDirectory, { recursive: true });
await mkdir(dirname(outputPath), { recursive: true });
await mkdir(dirname(posterPath), { recursive: true });
const existing = await readdir(frameDirectory);
if (existing.some((name) => /^frame\d{4}\.png$/u.test(name))) {
  throw new Error(
    `Frame directory is not empty: ${frameDirectory}. Use a fresh directory.`,
  );
}

const { chromium } = await import(pathToFileURL(modulePath).href);
const browser = await chromium.launch({
  headless: true,
  executablePath: browserExecutable || undefined,
  args: ["--enable-gpu", "--enable-webgl", "--ignore-gpu-blocklist"],
});

const startedAt = performance.now();
try {
  const context = await browser.newContext({
    viewport,
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
  const ready = await page.evaluate(() =>
    window.__CONTROL_VALVE_METRICS__.waitForReady(),
  );
  const frames = [];
  const combined = createHash("sha256");

  for (let frame = 0; frame < frameCount; frame += 1) {
    const progress = frame / (frameCount - 1);
    const capture = await page.evaluate(
      (value) =>
        window.__CONTROL_VALVE_METRICS__.setProgressAndCaptureForTest(value),
      progress,
    );
    const filename = `frame${String(frame).padStart(4, "0")}.png`;
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
      progress,
      shotId: capture.state.shotId,
      sourceFrame: capture.state.frame,
      filename,
      sha256: digest,
      bytes,
    });
    if (frame % 60 === 0 || frame === frameCount - 1) {
      process.stdout.write(`rendered ${frame + 1}/${frameCount}\n`);
    }
  }

  await copyFile(resolve(frameDirectory, "frame0000.png"), posterPath);
  const cameraPrevisPath = resolve(
    "creative/control-valve/camera-previs.json",
  );
  const manifest = {
    schemaVersion: 1,
    generatedAt: new Date().toISOString(),
    sourceUrl: url,
    sourceCameraPrevis: "creative/control-valve/camera-previs.json",
    sourceCameraPrevisSha256: await sha256(cameraPrevisPath),
    outputDirectory: frameDirectory,
    posterPath: "docs/control-valve-video/assets/first-frame.png",
    renderProfile: {
      width: viewport.width,
      height: viewport.height,
      dpr: 1,
      fps,
      frameCount,
      durationSeconds: frameCount / fps,
      uiFree: true,
      captureSurface: "WebGL canvas only",
      captureMethod: "HTMLCanvasElement.toDataURL",
    },
    ready,
    browser: {
      userAgent: await page.evaluate(() => navigator.userAgent),
      renderer: await page.evaluate(() => {
        const canvasElement = document.querySelector("#canvas");
        const gl =
          canvasElement.getContext("webgl2") ||
          canvasElement.getContext("webgl");
        const extension = gl?.getExtension("WEBGL_debug_renderer_info");
        return extension
          ? gl.getParameter(extension.UNMASKED_RENDERER_WEBGL)
          : "unavailable";
      }),
    },
    consoleErrors,
    pageErrors,
    failedRequests,
    combinedFrameSha256: combined.digest("hex"),
    totalPngBytes: frames.reduce((sum, frame) => sum + frame.bytes, 0),
    renderDurationMs: performance.now() - startedAt,
    frames,
  };
  await writeFile(outputPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
  await context.close();
  process.stdout.write(
    `Rendered ${frameCount} UI-free frames and wrote ${outputPath}\n`,
  );
} finally {
  await browser.close();
}
