#!/usr/bin/env node

import process from "node:process";
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

function maxTransformDifference(left, right) {
  const leftValues = [
    ...left.rootRotation,
    ...left.cameraPosition,
    ...left.groups.flatMap((group) => group.positions.flat()),
  ];
  const rightValues = [
    ...right.rootRotation,
    ...right.cameraPosition,
    ...right.groups.flatMap((group) => group.positions.flat()),
  ];
  if (leftValues.length !== rightValues.length) {
    return Number.POSITIVE_INFINITY;
  }
  return leftValues.reduce(
    (maximum, value, index) =>
      Math.max(maximum, Math.abs(value - rightValues[index])),
    0,
  );
}

const args = parseArgs(process.argv.slice(2));
const url = args.url;
const playwrightModule = args["playwright-module"] ?? "playwright";
const browserExecutable = args["browser-executable"];
const screenshotPrefix = args["screenshot-prefix"];

if (!url) {
  throw new Error("--url is required");
}

const moduleSpecifier = /^[A-Za-z]:[\\/]/u.test(playwrightModule)
  ? pathToFileURL(playwrightModule).href
  : playwrightModule;
const { chromium } = await import(moduleSpecifier);
const browser = await chromium.launch({
  headless: true,
  executablePath: browserExecutable || undefined,
  args: [
    "--enable-gpu",
    "--enable-webgl",
    "--ignore-gpu-blocklist",
  ],
});

const functional = {
  pageTitle: null,
  stages: [],
  consoleErrors: [],
  pageErrors: [],
  failedRequests: [],
  fallbackState: null,
  loadErrorState: null,
  deterministicTransformMaxDifference: null,
};
const runs = [];

try {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1,
    reducedMotion: "no-preference",
  });
  const page = await context.newPage();
  page.on("console", (message) => {
    if (message.type() === "error") {
      functional.consoleErrors.push(message.text());
    }
  });
  page.on("pageerror", (error) => {
    functional.pageErrors.push(error.message);
  });
  page.on("requestfailed", (request) => {
    functional.failedRequests.push({
      url: request.url(),
      error: request.failure()?.errorText ?? "unknown",
    });
  });

  await page.goto(url, { waitUntil: "networkidle" });
  try {
    await page.waitForFunction(
      () => Boolean(window.__CAR_STORY_METRICS__),
      null,
      { timeout: 5000 },
    );
  } catch (error) {
    throw new Error(
      `Metrics API did not initialize. Console errors: ${JSON.stringify(
        functional.consoleErrors,
      )}. Page errors: ${JSON.stringify(functional.pageErrors)}`,
      { cause: error },
    );
  }
  const ready = await page.evaluate(() =>
    window.__CAR_STORY_METRICS__.waitForReady(),
  );
  if (ready.state !== "ready") {
    throw new Error(`Product story did not reach ready state: ${ready.state}`);
  }

  functional.pageTitle = await page.title();
  functional.stages = await page
    .locator("[data-stage]")
    .evaluateAll((elements) => elements.map((element) => element.dataset.stage));

  const firstFinal = await page.evaluate(() =>
    window.__CAR_STORY_METRICS__.setProgressForTest(1),
  );
  await page.evaluate(() =>
    window.__CAR_STORY_METRICS__.setProgressForTest(0),
  );
  const secondFinal = await page.evaluate(() =>
    window.__CAR_STORY_METRICS__.setProgressForTest(1),
  );
  functional.deterministicTransformMaxDifference = maxTransformDifference(
    firstFinal,
    secondFinal,
  );

  await page.evaluate(() =>
    window.__CAR_STORY_METRICS__.setProgressForTest(0),
  );
  if (screenshotPrefix) {
    await page.screenshot({ path: `${screenshotPrefix}-intro.png` });
  }
  await page.evaluate(() => {
    document.documentElement.style.scrollBehavior = "auto";
    const travel =
      document.documentElement.scrollHeight - window.innerHeight;
    window.scrollTo({ top: travel * 0.55, behavior: "instant" });
  });
  await page.evaluate(() =>
    window.__CAR_STORY_METRICS__.waitForSettled(),
  );
  if (screenshotPrefix) {
    await page.screenshot({ path: `${screenshotPrefix}-assembly.png` });
  }

  runs.push(
    await page.evaluate(() =>
      window.__CAR_STORY_METRICS__.runScrollBenchmark({
        durationMs: 4200,
        idleMs: 1200,
        label: "desktop-cold-scroll",
        cacheState: "cold",
      }),
    ),
  );
  if (screenshotPrefix) {
    await page.screenshot({ path: `${screenshotPrefix}-hero.png` });
  }

  await page.reload({ waitUntil: "networkidle" });
  const warmReady = await page.evaluate(() =>
    window.__CAR_STORY_METRICS__.waitForReady(),
  );
  if (warmReady.state !== "ready") {
    throw new Error(`Warm product story did not reach ready state: ${warmReady.state}`);
  }
  runs.push(
    await page.evaluate(() =>
      window.__CAR_STORY_METRICS__.runScrollBenchmark({
        durationMs: 4200,
        idleMs: 1200,
        label: "desktop-warm-scroll",
        cacheState: "warm",
      }),
    ),
  );

  const fallback = await context.newPage();
  await fallback.goto(`${url}?fallback=1`, { waitUntil: "networkidle" });
  functional.fallbackState = await fallback.locator("body").getAttribute(
    "data-webgl-state",
  );

  const loadError = await context.newPage();
  loadError.on("console", () => {});
  await loadError.goto(`${url}?fail-model=1`, { waitUntil: "networkidle" });
  await loadError.evaluate(() =>
    window.__CAR_STORY_METRICS__.waitForReady(),
  );
  functional.loadErrorState = await loadError.locator("body").getAttribute(
    "data-webgl-state",
  );

  await context.close();
} finally {
  await browser.close();
}

const result = {
  schemaVersion: 1,
  collectedAt: new Date().toISOString(),
  sourceUrl: url,
  browserMode: "headless Chromium with GPU/WebGL enabled",
  functional,
  runs,
};

process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
