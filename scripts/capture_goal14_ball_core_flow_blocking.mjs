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
  args["frame-dir"] ?? "docs/assets/ztovalve/hero/goal14-ball-core-flow-blocking/frames-96",
);
const manifestPath = resolve(
  args.out ?? "docs/assets/ztovalve/hero/goal14-ball-core-flow-blocking/blocking-manifest.json",
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
  await page.waitForFunction(() => window.__GOAL14_BLOCKING__, null, {
    timeout: 45000,
  });
  const ready = await page.evaluate(() => window.__GOAL14_BLOCKING__.waitForReady());
  const frames = [];
  const combined = createHash("sha256");

  for (let frame = 0; frame < ready.frameCount; frame += 1) {
    const state = await page.evaluate((index) => window.__GOAL14_BLOCKING__.setFrame(index), frame);
    await page.waitForTimeout(70);
    const filename = `${String(frame + 1).padStart(4, "0")}.jpg`;
    const absolutePath = resolve(frameDirectory, filename);
    await page.locator("#stage").screenshot({
      path: absolutePath,
      type: "jpeg",
      quality: 86,
    });
    const bytes = (await stat(absolutePath)).size;
    const digest = await sha256(absolutePath);
    combined.update(`${frame}:${digest}:${bytes}\n`);
    frames.push({
      frame,
      filename,
      path: `docs/assets/ztovalve/hero/goal14-ball-core-flow-blocking/frames-96/${filename}`,
      beat: state.name,
      shellSplit: Number(state.shellSplit.toFixed(4)),
      seatSpread: Number(state.seatSpread.toFixed(4)),
      stemLift: Number(state.stemLift.toFixed(4)),
      lowerDrop: Number(state.lowerDrop.toFixed(4)),
      fastenerSpread: Number(state.fastenerSpread.toFixed(4)),
      ballTurn: Number(state.ballTurn.toFixed(4)),
      flowOpacity: Number(state.flowOpacity.toFixed(4)),
      flowProgress: Number(state.flowProgress.toFixed(4)),
      productYaw: Number(state.productYaw.toFixed(4)),
      bytes,
      sha256: digest,
    });
  }

  const manifest = {
    schemaVersion: 1,
    generatedAt: new Date().toISOString(),
    sourceUrl: url,
    preview: "docs/assets/ztovalve/hero/goal14-ball-core-flow-blocking/preview.html",
    sourceGoal13: "docs/assets/ztovalve/hero/goal13-ordered-assembly-blocking/",
    renderProfile: {
      width: ready.width,
      height: ready.height,
      dpr: 1,
      fps: ready.fps,
      frameCount: ready.frameCount,
      durationSeconds: ready.durationSeconds,
      kind: "96-frame low-resolution ball-core anchored multi-direction anatomy and flow-path blocking",
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
      "Goal 14 renders exactly 96 low-resolution blocking frames.",
      "No 240-frame release sequence is rendered or connected to the homepage.",
      "The blocking validates single-ball-core anchoring, multi-direction anatomy, 90-degree quarter-turn, and restrained flow-path lines.",
      "Only the true ball core receives the functional quarter-turn; valve seats, seat seals, shell, support parts, and fasteners do not follow that rotation.",
      "Flow lines express path only and make no pressure, flow-rate, zero-leakage, material, DBB/DIB, or medium claim.",
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
  process.stdout.write(`Captured ${frames.length} Goal 14 blocking frames to ${frameDirectory}\n`);
} finally {
  await browser.close();
}
