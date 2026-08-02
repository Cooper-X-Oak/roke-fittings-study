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
  args["out-dir"] ?? "docs/assets/ztovalve/hero/goal19-threejs-material-lookdev/stills",
);
const manifestPath = resolve(
  args.out ?? "docs/assets/ztovalve/hero/goal19-threejs-material-lookdev/render-manifest.json",
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
  args: [
    "--enable-gpu",
    "--enable-webgl",
    "--ignore-gpu-blocklist",
    "--disable-dev-shm-usage",
  ],
});

const startedAt = performance.now();
try {
  const context = await browser.newContext({
    viewport: { width: 3840, height: 2160 },
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

  await page.goto(url, { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForFunction(() => window.__GOAL19_THREEJS_MATERIAL_LOOKDEV__, null, {
    timeout: 60000,
  });
  const ready = await page.evaluate(() => window.__GOAL19_THREEJS_MATERIAL_LOOKDEV__.waitForReady());
  const states = await page.evaluate(() => window.__GOAL19_THREEJS_MATERIAL_LOOKDEV__.states);
  const stills = [];
  const combined = createHash("sha256");

  for (let index = 0; index < states.length; index += 1) {
    const state = await page.evaluate((stillIndex) => window.__GOAL19_THREEJS_MATERIAL_LOOKDEV__.setStill(stillIndex), index);
    await page.waitForTimeout(260);
    const absolutePath = resolve(outputDirectory, state.filename);
    await page.locator("#stage").screenshot({
      path: absolutePath,
      type: "png",
      animations: "disabled",
    });
    const bytes = (await stat(absolutePath)).size;
    const digest = await sha256(absolutePath);
    combined.update(`${state.id}:${digest}:${bytes}\n`);
    stills.push({
      id: state.id,
      stateId: state.stateId,
      animationState: state.animationState,
      name: state.name,
      purpose: state.purpose,
      filename: state.filename,
      path: `docs/assets/ztovalve/hero/goal19-threejs-material-lookdev/stills/${state.filename}`,
      width: ready.width,
      height: ready.height,
      bytes,
      sha256: digest,
    });
    process.stdout.write(`captured ${state.id} ${state.filename}\n`);
  }

  const manifest = {
    schemaVersion: 1,
    generatedAt: new Date().toISOString(),
    sourceUrl: url,
    preview: "docs/assets/ztovalve/hero/goal19-threejs-material-lookdev/preview.html",
    stateSource: "docs/assets/ztovalve/hero/goal19-threejs-material-lookdev/preview.html",
    renderProfile: {
      width: ready.width,
      height: ready.height,
      dpr: 1,
      stillCount: ready.stillCount,
      animationStateCount: ready.animationStateCount,
      kind: "4K Three.js material lookdev stills with supplier-informed stainless material families",
      frameSequenceRendered: false,
      fullReleaseFrameCount: 0,
      homepageConnected: false,
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
      "Goal 19 renders exactly five 4K Three.js material lookdev stills.",
      "Goal 19 adapts the Goal 16 assembled, exploded, ball-open, and ball-closed reusable animation states.",
      "No 240-frame release sequence is rendered.",
      "The homepage is not replaced or connected to these stills.",
      "Supplier terms guide visual material families only: investment cast bead-blasted stainless shell, mirror polished stainless ball, machined stainless, graphite/dark seals, and PTFE/light soft-seat treatment.",
      "Only the true ball core receives ballTurn; valve seats and seal groups remain fixed.",
      "No pressure, flow-rate, zero-leakage, fire-safe, anti-static, DBB/DIB, certified material grade, or medium claim is made.",
    ],
    consoleErrors,
    pageErrors,
    failedRequests,
    combinedStillSha256: combined.digest("hex"),
    totalStillBytes: stills.reduce((sum, still) => sum + still.bytes, 0),
    renderDurationMs: Math.round(performance.now() - startedAt),
    stills,
  };

  await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
  await context.close();
  process.stdout.write(`Captured ${stills.length} Goal 19 Three.js material lookdev stills to ${outputDirectory}\n`);
} finally {
  await browser.close();
}
