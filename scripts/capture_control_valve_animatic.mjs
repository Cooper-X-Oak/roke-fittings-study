#!/usr/bin/env node

import { mkdir, writeFile } from "node:fs/promises";
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

const args = parseArgs(process.argv.slice(2));
const url = args.url;
const modulePath = args["playwright-module"];
const browserExecutable = args["browser-executable"];
const outputPath = resolve(
  args.out ?? "creative/control-valve/render-evidence.json",
);
const routeRoot = resolve("docs/control-valve");
const evidenceDirectory = resolve(routeRoot, "evidence");
const posterPath = resolve(routeRoot, "assets/first-frame-poster.jpg");

if (!url || !modulePath) {
  throw new Error("--url and --playwright-module are required");
}

await mkdir(evidenceDirectory, { recursive: true });
await mkdir(dirname(posterPath), { recursive: true });
const { chromium } = await import(pathToFileURL(modulePath).href);
const browser = await chromium.launch({
  headless: true,
  executablePath: browserExecutable || undefined,
  args: [
    "--enable-gpu",
    "--enable-webgl",
    "--ignore-gpu-blocklist",
  ],
});

const shotFrames = [
  ["monument", 0.08, "shot-01-monument.png"],
  ["command-descends", 0.27, "shot-02-command-descends.png"],
  ["inside-the-cascade", 0.47, "shot-03-inside-the-cascade.png"],
  ["six-systems", 0.73, "shot-04-six-systems.png"],
  ["authority-restored", 1, "shot-05-authority-restored.png"],
];

try {
  // Bootstrap the actual model once to create the image that is shown before
  // WebGL is usable on later loads. This first page is intentionally separate
  // from official console/network evidence.
  const bootstrap = await browser.newPage({
    viewport: { width: 1600, height: 1000 },
    deviceScaleFactor: 1,
  });
  bootstrap.on("console", () => {});
  await bootstrap.goto(url, { waitUntil: "networkidle" });
  await bootstrap.evaluate(() =>
    window.__CONTROL_VALVE_METRICS__.waitForReady(),
  );
  await bootstrap.evaluate(() =>
    window.__CONTROL_VALVE_METRICS__.setProgressForTest(0.08),
  );
  await bootstrap.waitForTimeout(180);
  await bootstrap.locator("#canvas").screenshot({
    path: posterPath,
    type: "jpeg",
    quality: 86,
  });
  await bootstrap.close();

  const context = await browser.newContext({
    viewport: { width: 1600, height: 1000 },
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

  // Ensure the poster has a measurable period in which it is the usable
  // product frame before model bytes and Draco decoding complete.
  await page.route("**/control-valve-shot-ready.glb", async (route) => {
    await new Promise((resolveDelay) => setTimeout(resolveDelay, 650));
    await route.continue();
  });
  await page.goto(url, { waitUntil: "domcontentloaded" });
  const posterLoadingState = await page.locator("#poster").evaluate(async (node) => {
    await node.decode();
    const style = getComputedStyle(node);
    return {
      complete: node.complete,
      naturalWidth: node.naturalWidth,
      naturalHeight: node.naturalHeight,
      opacity: Number(style.opacity),
      visible: style.display !== "none" && style.visibility !== "hidden",
      capturedAtMs: Number(performance.now().toFixed(2)),
    };
  });

  await page.waitForLoadState("networkidle");
  const ready = await page.evaluate(() =>
    window.__CONTROL_VALVE_METRICS__.waitForReady(),
  );
  await page.waitForTimeout(200);
  const posterAfterReady = await page.locator("#poster").evaluate((node) => ({
    opacity: Number(getComputedStyle(node).opacity),
    hiddenClass: node.classList.contains("is-hidden"),
  }));

  const captures = [];
  for (const [shotId, progress, filename] of shotFrames) {
    const snapshot = await page.evaluate(
      (value) => window.__CONTROL_VALVE_METRICS__.setProgressForTest(value),
      progress,
    );
    await page.waitForTimeout(160);
    const absolutePath = resolve(evidenceDirectory, filename);
    await page.screenshot({ path: absolutePath });
    captures.push({
      shotId,
      progress,
      path: `docs/control-valve/evidence/${filename}`,
      runtimeShotId: snapshot.shotId,
    });
  }

  const benchmark = await page.evaluate(async () => {
    const durations = [];
    let previous;
    // This headless pass is a short runtime diagnostic, not a substitute for
    // hardware-GPU profiling. Structural cost is asserted separately from the
    // GLB (six primitives / six draw-call candidates).
    const total = 24;
    for (let index = 0; index < total; index += 1) {
      await new Promise((resolveFrame) => {
        requestAnimationFrame((timestamp) => {
          if (previous !== undefined) durations.push(timestamp - previous);
          previous = timestamp;
          window.__CONTROL_VALVE_METRICS__.setProgressForTest(
            index / (total - 1),
          );
          resolveFrame();
        });
      });
    }
    const sorted = [...durations].sort((a, b) => a - b);
    const percentile = (value) =>
      sorted[Math.floor((sorted.length - 1) * value)] ?? 0;
    const beforeIdle =
      window.__CONTROL_VALVE_METRICS__.snapshot().renderCount;
    await new Promise((resolveDelay) => setTimeout(resolveDelay, 900));
    const afterIdle =
      window.__CONTROL_VALVE_METRICS__.snapshot().renderCount;
    const modelResource = performance
      .getEntriesByType("resource")
      .find((entry) => entry.name.endsWith("control-valve-shot-ready.glb"));
    const canvas = document.querySelector("#canvas");
    const gl = canvas?.getContext("webgl2") ?? canvas?.getContext("webgl");
    const rendererInfo = (() => {
      if (!gl) return null;
      const extension = gl.getExtension("WEBGL_debug_renderer_info");
      return {
        vendor: extension
          ? gl.getParameter(extension.UNMASKED_VENDOR_WEBGL)
          : gl.getParameter(gl.VENDOR),
        renderer: extension
          ? gl.getParameter(extension.UNMASKED_RENDERER_WEBGL)
          : gl.getParameter(gl.RENDERER),
        version: gl.getParameter(gl.VERSION),
      };
    })();
    return {
      sampleCount: durations.length,
      p50FrameMs: Number(percentile(0.5).toFixed(3)),
      p95FrameMs: Number(percentile(0.95).toFixed(3)),
      framesOver16_7Ms: durations.filter((value) => value > 16.7).length,
      framesOver33_3Ms: durations.filter((value) => value > 33.3).length,
      idleRendererFrames: afterIdle - beforeIdle,
      usableFrameMs:
        window.__CONTROL_VALVE_METRICS__.snapshot().usableFrameMs,
      modelResource: modelResource
        ? {
            durationMs: Number(modelResource.duration.toFixed(3)),
            transferSize: modelResource.transferSize,
            encodedBodySize: modelResource.encodedBodySize,
            decodedBodySize: modelResource.decodedBodySize,
          }
        : null,
      rendererInfo,
      jsHeapBytes: performance.memory?.usedJSHeapSize ?? null,
    };
  });

  const bodyHasContent = await page.evaluate(
    () => document.body.innerText.trim().length > 0,
  );
  const interactiveLabels = await page
    .locator("button, a")
    .evaluateAll((nodes) => nodes.map((node) => node.textContent.trim()));

  const result = {
    schemaVersion: 1,
    collectedAt: new Date().toISOString(),
    sourceUrl: url,
    browserMode: "headless Chromium; renderer recorded in benchmark.rendererInfo",
    performanceInterpretation:
      "Short headless diagnostic only. It does not certify discrete-GPU frame rate; the portable performance proof is the six-primitive Draco GLB and demand-rendering behavior.",
    viewport: { width: 1600, height: 1000, dpr: 1 },
    ready,
    posterLoadingState,
    posterAfterReady,
    bodyHasContent,
    interactiveLabels,
    consoleErrors,
    pageErrors,
    failedRequests,
    captures,
    benchmark,
  };
  await writeFile(outputPath, `${JSON.stringify(result, null, 2)}\n`, "utf8");
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
  await context.close();
} finally {
  await browser.close();
}
