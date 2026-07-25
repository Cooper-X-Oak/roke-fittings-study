import { expect, test } from "@playwright/test";
import {
  applyNetworkProfile,
  captureCanvasSignature,
  getPerformanceSnapshot,
  getRafFiredCount,
  installPerformanceProbe,
  loadPerformanceBudget,
  meanAbsoluteDifference,
  resourceBytes,
  scrollToProgress,
  waitForWebglState,
} from "./helpers/performance.mjs";

let budget;

test.beforeAll(async () => {
  budget = await loadPerformanceBudget();
});

async function observeFailures(page) {
  const pageErrors = [];
  const requestFailures = [];
  const consoleErrors = [];

  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("requestfailed", (request) => {
    requestFailures.push({
      url: request.url(),
      error: request.failure()?.errorText || "unknown",
    });
  });
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });

  return { pageErrors, requestFailures, consoleErrors };
}

test("poster-first loading, milestones, Web Vitals, and resource budgets are blocking", async ({
  context,
  page,
}) => {
  await installPerformanceProbe(page);
  const failures = await observeFailures(page);
  const session = await applyNetworkProfile(context, page, budget.network);

  await page.goto(budget.route, { waitUntil: "domcontentloaded" });

  const poster = page.locator("[data-3d-poster]");
  await expect(poster).toBeVisible({ timeout: budget.timings.posterVisibleMs });
  await waitForWebglState(page, ["ready"]);
  await page.waitForTimeout(100);

  const snapshot = await getPerformanceSnapshot(page);
  const marks = snapshot.marks;

  for (const markName of budget.requiredMarks) {
    expect.soft(marks[markName], `Missing performance mark: ${markName}`).toBeGreaterThanOrEqual(0);
  }

  const markTimes = budget.requiredMarks.map((name) => marks[name]);
  for (let index = 1; index < markTimes.length; index += 1) {
    expect.soft(
      markTimes[index],
      `${budget.requiredMarks[index]} must not precede ${budget.requiredMarks[index - 1]}`,
    ).toBeGreaterThanOrEqual(markTimes[index - 1]);
  }

  expect.soft(marks["roke:poster-visible"]).toBeLessThanOrEqual(budget.timings.posterVisibleMs);
  expect.soft(marks["roke:model-request-start"]).toBeLessThanOrEqual(
    budget.timings.modelRequestStartMs,
  );
  expect.soft(marks["roke:first-3d-frame"]).toBeLessThanOrEqual(
    budget.timings.first3dFrameMs,
  );
  expect.soft(marks["roke:interactive-ready"]).toBeLessThanOrEqual(
    budget.timings.interactiveReadyMs,
  );

  expect.soft(snapshot.metrics.lcp, "LCP must be observable").toBeGreaterThan(0);
  expect.soft(snapshot.metrics.lcp).toBeLessThanOrEqual(budget.timings.lcpMs);
  expect.soft(snapshot.metrics.cls).toBeLessThanOrEqual(budget.stability.cls);

  const readyTime = marks["roke:interactive-ready"];
  const origin = new URL(page.url()).origin;
  const initialResources = snapshot.resources.filter((resource) => {
    const url = new URL(resource.name);
    return url.origin === origin && resource.startTime <= readyTime;
  });

  const initialTransferBytes = initialResources.reduce(
    (total, resource) => total + resourceBytes(resource),
    0,
  );
  const modelResources = initialResources.filter((resource) =>
    new URL(resource.name).pathname.endsWith(".glb"),
  );
  const javascriptResources = initialResources.filter((resource) =>
    new URL(resource.name).pathname.endsWith(".js"),
  );
  const wasmResources = initialResources.filter((resource) =>
    new URL(resource.name).pathname.endsWith(".wasm"),
  );

  const posterURL = await poster.evaluate((element) => element.currentSrc || element.src || "");
  const posterResource = initialResources.find((resource) => resource.name === posterURL);

  expect.soft(initialResources.length).toBeLessThanOrEqual(
    budget.assets.maxInitialRequestCount,
  );
  expect.soft(initialTransferBytes).toBeLessThanOrEqual(
    budget.assets.maxInitialTransferBytes,
  );
  expect.soft(modelResources).toHaveLength(1);
  expect.soft(resourceBytes(modelResources[0] || {})).toBeLessThanOrEqual(
    budget.assets.maxModelBytes,
  );
  expect.soft(posterResource, "Poster must be a real early network resource").toBeTruthy();
  expect.soft(resourceBytes(posterResource || {})).toBeLessThanOrEqual(
    budget.assets.maxPosterBytes,
  );
  expect.soft(
    javascriptResources.reduce((total, resource) => total + resourceBytes(resource), 0),
  ).toBeLessThanOrEqual(budget.assets.maxCriticalJavaScriptBytes);
  expect.soft(
    wasmResources.reduce((total, resource) => total + resourceBytes(resource), 0),
  ).toBeLessThanOrEqual(budget.assets.maxDecoderWasmBytes);

  const externalRequests = snapshot.resources.filter(
    (resource) => new URL(resource.name).origin !== origin,
  );
  expect.soft(externalRequests).toEqual([]);
  expect.soft(failures.pageErrors).toEqual([]);
  expect.soft(failures.requestFailures).toEqual([]);
  expect.soft(failures.consoleErrors).toEqual([]);

  const longTaskDurations = snapshot.metrics.longTasks.map((task) => task.duration);
  if (longTaskDurations.length > 0) {
    expect.soft(Math.max(...longTaskDurations)).toBeLessThanOrEqual(
      budget.stability.maxSingleLongTaskMs,
    );
    expect.soft(longTaskDurations.reduce((total, duration) => total + duration, 0)).toBeLessThanOrEqual(
      budget.stability.maxTotalLongTaskMs,
    );
  }

  await session.detach();
});

test("scroll animation changes and reverses while the renderer sleeps after settling", async ({
  page,
}) => {
  await installPerformanceProbe(page);
  const failures = await observeFailures(page);

  await page.goto(budget.route, { waitUntil: "domcontentloaded" });
  await waitForWebglState(page, ["ready"]);

  const canvas = page.locator("#webgl-canvas");
  await expect(canvas).toBeVisible();

  const dimensions = await canvas.evaluate((element) => {
    const rect = element.getBoundingClientRect();
    return {
      width: element.width,
      height: element.height,
      cssWidth: rect.width,
      cssHeight: rect.height,
      pixels: element.width * element.height,
      effectivePixelRatio: Math.max(
        element.width / Math.max(rect.width, 1),
        element.height / Math.max(rect.height, 1),
      ),
    };
  });

  expect.soft(dimensions.pixels).toBeLessThanOrEqual(
    budget.rendering.maxDrawingBufferPixels,
  );
  expect.soft(dimensions.effectivePixelRatio).toBeLessThanOrEqual(
    budget.rendering.maxEffectivePixelRatio,
  );

  const assembled = await captureCanvasSignature(page);
  const scrollResponse = await scrollToProgress(page, 0.72);
  expect.soft(scrollResponse).toBeLessThanOrEqual(budget.timings.scrollResponseMs);
  await page.waitForTimeout(budget.stability.settleMs);
  const exploded = await captureCanvasSignature(page);

  expect.soft(meanAbsoluteDifference(assembled, exploded)).toBeGreaterThanOrEqual(
    budget.rendering.minStateSignatureDifference,
  );

  await scrollToProgress(page, 0);
  await page.waitForTimeout(budget.stability.settleMs);
  const reassembled = await captureCanvasSignature(page);

  expect.soft(meanAbsoluteDifference(assembled, reassembled)).toBeLessThanOrEqual(
    budget.rendering.maxReverseSignatureDifference,
  );

  await page.waitForTimeout(budget.stability.settleMs);
  const rafBefore = await getRafFiredCount(page);
  await page.waitForTimeout(budget.stability.observationMs);
  const rafAfter = await getRafFiredCount(page);

  expect.soft(rafAfter - rafBefore).toBeLessThanOrEqual(
    budget.stability.maxRafCallbacksAfterSettle,
  );
  expect.soft(failures.pageErrors).toEqual([]);
  expect.soft(failures.requestFailures).toEqual([]);
  expect.soft(failures.consoleErrors).toEqual([]);
});

test("critical 3D asset failure preserves poster, fallback, and readable core content", async ({
  page,
}) => {
  await installPerformanceProbe(page);
  const failures = await observeFailures(page);

  await page.route("**/*", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname.endsWith(".glb") || pathname.endsWith(".wasm")) {
      await route.abort("failed");
      return;
    }
    await route.continue();
  });

  await page.goto(budget.route, { waitUntil: "domcontentloaded" });
  await waitForWebglState(page, ["error", "fallback"]);

  await expect(page.locator("[data-3d-poster]")).toBeVisible();
  await expect(page.locator("h1")).toBeVisible();
  await expect(page.locator("#viewer-fallback")).toBeVisible();

  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect.soft(overflow).toBeLessThanOrEqual(1);
  expect.soft(failures.pageErrors).toEqual([]);
  expect.soft(failures.consoleErrors).toEqual([]);
});

test("reduced motion remains visually stable and does not keep a hot render loop", async ({
  page,
}) => {
  await installPerformanceProbe(page);
  await page.emulateMedia({ reducedMotion: "reduce" });

  await page.goto(budget.route, { waitUntil: "domcontentloaded" });
  await waitForWebglState(page, ["ready", "reduced-motion"]);

  await expect(page.locator("#motion-toggle")).toBeHidden();

  const canvas = page.locator("#webgl-canvas");
  const hasRenderableCanvas = await canvas.evaluate(
    (element) => element.width > 0 && element.height > 0 && getComputedStyle(element).visibility !== "hidden",
  );

  let before;
  if (hasRenderableCanvas) before = await captureCanvasSignature(page);

  await scrollToProgress(page, 0.72);
  await page.waitForTimeout(budget.stability.settleMs);

  if (hasRenderableCanvas) {
    const after = await captureCanvasSignature(page);
    expect.soft(meanAbsoluteDifference(before, after)).toBeLessThanOrEqual(
      budget.rendering.maxReverseSignatureDifference,
    );
  } else {
    await expect(page.locator("[data-3d-poster]")).toBeVisible();
  }

  await page.waitForTimeout(budget.stability.settleMs);
  const rafBefore = await getRafFiredCount(page);
  await page.waitForTimeout(budget.stability.observationMs);
  const rafAfter = await getRafFiredCount(page);

  expect.soft(rafAfter - rafBefore).toBeLessThanOrEqual(
    budget.stability.maxRafCallbacksAfterSettle,
  );
});
