#!/usr/bin/env node

import { mkdir, rm, stat, writeFile } from "node:fs/promises";
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
const videoPath = resolve(
  evidenceDirectory,
  "control-valve-grey-animatic.webm",
);
const temporaryVideoDirectory = resolve(
  args["video-temp"] ?? "D:/Temp/control-valve-grey-animatic-video",
);

if (!url || !modulePath) {
  throw new Error("--url and --playwright-module are required");
}

await mkdir(evidenceDirectory, { recursive: true });
await mkdir(dirname(posterPath), { recursive: true });
await rm(temporaryVideoDirectory, { recursive: true, force: true });
await mkdir(temporaryVideoDirectory, { recursive: true });
const { chromium } = await import(pathToFileURL(modulePath).href);
const browser = await chromium.launch({
  headless: true,
  executablePath: browserExecutable || undefined,
  args: ["--enable-gpu", "--enable-webgl", "--ignore-gpu-blocklist"],
});

const shotCaptures = [
  ["core-suspended", 0.08, "shot-01-core-suspended.png"],
  ["precision-nested", 0.28, "shot-02-precision-nested.png"],
  ["body-encloses", 0.48, "shot-03-body-encloses.png"],
  ["assembly-complete", 0.7, "shot-04-assembly-complete.png"],
  ["product-presence", 1, "shot-05-product-presence.png"],
];

const validationCaptures = [
  ["trim-separated", 0, "validation-trim-separated.png"],
  ["trim-mid-assembly", 0.25, "validation-trim-mid-assembly.png"],
  ["closure-start", 0.4, "validation-closure-start.png"],
  ["closure-mid", 0.49, "validation-closure-mid.png"],
  ["closure-complete", 0.59, "validation-closure-complete.png"],
];

function maxAbsDelta(left, right) {
  if (Array.isArray(left) && Array.isArray(right)) {
    return Math.max(
      0,
      ...left.map((value, index) => maxAbsDelta(value, right[index])),
    );
  }
  if (
    left &&
    right &&
    typeof left === "object" &&
    typeof right === "object"
  ) {
    const keys = new Set([...Object.keys(left), ...Object.keys(right)]);
    return Math.max(
      0,
      ...[...keys].map((key) => maxAbsDelta(left[key], right[key])),
    );
  }
  if (
    typeof left === "number" &&
    Number.isFinite(left) &&
    typeof right === "number" &&
    Number.isFinite(right)
  ) {
    return Math.abs(left - right);
  }
  return left === right ? 0 : Number.POSITIVE_INFINITY;
}

async function playAndSample(page, direction) {
  await page.evaluate((value) => {
    window.__CONTROL_VALVE_METRICS__.setProgressForTest(value > 0 ? 0 : 1);
    window.__CONTROL_VALVE_METRICS__.startPlaybackForTest(value);
  }, direction);
  const startedAt = Date.now();
  const samples = [];
  while (Date.now() - startedAt < 20500) {
    await page.waitForTimeout(180);
    const snapshot = await page.evaluate(() =>
      window.__CONTROL_VALVE_METRICS__.snapshot(),
    );
    samples.push({
      elapsedMs: Date.now() - startedAt,
      progress: snapshot.progress,
      frame: snapshot.frame,
      shotId: snapshot.shotId,
      cameraPosition: snapshot.cameraPosition,
      focusDistance: snapshot.focusDistance,
      bodyOpacity: snapshot.productState.bodyOpacity,
      trimAssembly: snapshot.productState.trimAssembly,
      occlusion: snapshot.occlusion,
    });
    if (
      (direction > 0 && snapshot.progress >= 1) ||
      (direction < 0 && snapshot.progress <= 0)
    ) {
      break;
    }
  }
  const observed = [];
  for (const sample of samples) {
    if (observed.at(-1) !== sample.shotId) observed.push(sample.shotId);
  }
  return {
    direction: direction > 0 ? "forward" : "reverse",
    completed:
      direction > 0
        ? samples.at(-1)?.progress === 1
        : samples.at(-1)?.progress === 0,
    elapsedMs: Date.now() - startedAt,
    sampleCount: samples.length,
    observedShotIds: observed,
    samples,
  };
}

try {
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

  await page.goto(url, { waitUntil: "networkidle" });
  const ready = await page.evaluate(() =>
    window.__CONTROL_VALVE_METRICS__.waitForReady(),
  );
  await page.evaluate(() =>
    window.__CONTROL_VALVE_METRICS__.setProgressForTest(0),
  );
  await page.waitForTimeout(180);
  await page.locator("#canvas").screenshot({
    path: posterPath,
    type: "jpeg",
    quality: 88,
  });

  const captures = [];
  for (const [shotId, progress, filename] of shotCaptures) {
    const snapshot = await page.evaluate(
      (value) => window.__CONTROL_VALVE_METRICS__.setProgressForTest(value),
      progress,
    );
    await page.waitForTimeout(120);
    const absolutePath = resolve(evidenceDirectory, filename);
    await page.screenshot({ path: absolutePath });
    captures.push({
      shotId,
      progress,
      path: `docs/control-valve/evidence/${filename}`,
      runtimeShotId: snapshot.shotId,
      frame: snapshot.frame,
    });
  }

  const validationFrames = [];
  for (const [id, progress, filename] of validationCaptures) {
    const snapshot = await page.evaluate(
      (value) => window.__CONTROL_VALVE_METRICS__.setProgressForTest(value),
      progress,
    );
    await page.waitForTimeout(120);
    const absolutePath = resolve(evidenceDirectory, filename);
    await page.screenshot({ path: absolutePath });
    validationFrames.push({
      id,
      progress,
      path: `docs/control-valve/evidence/${filename}`,
      snapshot,
    });
  }

  const roundTripSequence = [0.22, 0.67, 0.22, 0.67, 0.22];
  const roundTripSnapshots = [];
  for (const progress of roundTripSequence) {
    roundTripSnapshots.push(
      await page.evaluate(
        (value) => window.__CONTROL_VALVE_METRICS__.setProgressForTest(value),
        progress,
      ),
    );
  }
  const roundTrip = {
    sequence: roundTripSequence,
    progress022CameraMaxDelta: maxAbsDelta(
      roundTripSnapshots[0].cameraPosition,
      roundTripSnapshots[2].cameraPosition,
    ),
    progress022ProductMaxDelta: maxAbsDelta(
      roundTripSnapshots[0].productState,
      roundTripSnapshots[2].productState,
    ),
    progress022TrimTransformMaxDelta: maxAbsDelta(
      roundTripSnapshots[0].trimIslands.map((item) => item.position),
      roundTripSnapshots[4].trimIslands.map((item) => item.position),
    ),
    progress067CameraMaxDelta: maxAbsDelta(
      roundTripSnapshots[1].cameraPosition,
      roundTripSnapshots[3].cameraPosition,
    ),
    progress067ProductMaxDelta: maxAbsDelta(
      roundTripSnapshots[1].productState,
      roundTripSnapshots[3].productState,
    ),
  };

  const forwardPlayback = await playAndSample(page, 1);
  const reversePlayback = await playAndSample(page, -1);

  const closureSamples = validationFrames
    .filter((item) => item.id.startsWith("closure-"))
    .map((item) => ({
      id: item.id,
      progress: item.progress,
      frame: item.snapshot.frame,
      bodyOpacity: item.snapshot.productState.bodyOpacity,
      bodyClosure: item.snapshot.productState.bodyClosure,
      occlusion: item.snapshot.occlusion,
      trimProjectedOnScreen: item.snapshot.trimIslands.map(
        (island) => island.projectedOnScreen,
      ),
      trimNdc: item.snapshot.trimIslands.map((island) => island.ndc),
    }));

  const separatedSnapshot = validationFrames.find(
    (item) => item.id === "trim-separated",
  ).snapshot;
  const separatedWorldCenters = separatedSnapshot.trimIslands.map(
    (item) => item.worldCenter,
  );
  const maximumRadialAxisError = Math.max(
    ...separatedWorldCenters.map(([x, _y, z]) => Math.hypot(x, z)),
  );
  const axisYValues = separatedWorldCenters.map((center) => center[1]);

  const result = {
    schemaVersion: 2,
    collectedAt: new Date().toISOString(),
    sourceUrl: url,
    viewport: { width: 1600, height: 1000, dpr: 1 },
    ready,
    consoleErrors,
    pageErrors,
    failedRequests,
    geometry: {
      trimConnectedComponentCount: ready.trimConnectedComponentCount,
      trimDiagnostics: ready.trimDiagnostics,
      independentlyTransformable: ready.trimConnectedComponentCount === 4,
      labelBoundary:
        "Geometry islands are numbered only by camera-readable axis order; individual STEP cage/seat identity is not asserted.",
    },
    separation: {
      maximumRadialAxisError,
      axisYValues,
      distinctAxisPositions: new Set(
        axisYValues.map((value) => value.toFixed(6)),
      ).size,
      allProjectedOnScreen: separatedSnapshot.trimIslands.every(
        (item) => item.projectedOnScreen,
      ),
    },
    closureSamples,
    roundTrip,
    forwardPlayback,
    reversePlayback,
    captures,
    validationFrames: validationFrames.map(({ snapshot, ...item }) => ({
      ...item,
      shotId: snapshot.shotId,
      frame: snapshot.frame,
    })),
  };

  await writeFile(outputPath, `${JSON.stringify(result, null, 2)}\n`, "utf8");
  await context.close();

  const videoContext = await browser.newContext({
    viewport: { width: 1600, height: 1000 },
    deviceScaleFactor: 1,
    reducedMotion: "no-preference",
    recordVideo: {
      dir: temporaryVideoDirectory,
      size: { width: 1280, height: 800 },
    },
  });
  const videoPage = await videoContext.newPage();
  await videoPage.goto(url, { waitUntil: "networkidle" });
  await videoPage.evaluate(() =>
    window.__CONTROL_VALVE_METRICS__.waitForReady(),
  );
  const video = videoPage.video();
  await videoPage.locator("#play-forward").click();
  await videoPage.waitForTimeout(18800);
  await videoPage.close();
  await video.saveAs(videoPath);
  await videoContext.close();
  result.video = {
    path: "docs/control-valve/evidence/control-valve-grey-animatic.webm",
    bytes: (await stat(videoPath)).size,
    direction: "forward",
    canonicalDurationSeconds: 18,
  };
  await writeFile(outputPath, `${JSON.stringify(result, null, 2)}\n`, "utf8");
  await rm(temporaryVideoDirectory, { recursive: true, force: true });
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
} finally {
  await browser.close();
}
