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

function percentile(values, probability) {
  if (!values.length) return null;
  const sorted = [...values].sort((left, right) => left - right);
  const index = Math.min(
    sorted.length - 1,
    Math.ceil(probability * sorted.length) - 1,
  );
  return sorted[index];
}

function summarize(results) {
  const latencies = results.map((result) => result.elapsedMs);
  const errors = results.map((result) => result.errorSeconds * 1000);
  return {
    count: results.length,
    latencyP50Ms: percentile(latencies, 0.5),
    latencyP95Ms: percentile(latencies, 0.95),
    latencyMaxMs: Math.max(...latencies),
    displayedErrorP95Ms: percentile(errors, 0.95),
    displayedErrorMaxMs: Math.max(...errors),
  };
}

const args = parseArgs(process.argv.slice(2));
const baseUrl = args.url;
const modulePath = args["playwright-module"];
const browserExecutable = args["browser-executable"];
const outputPath = resolve(
  args.out ?? "creative/control-valve-video/browser-benchmark.json",
);
const posterEvidencePath = resolve(
  args["poster-evidence"] ??
    "docs/control-valve-video/evidence/poster-before-video.png",
);
const midEvidencePath = resolve(
  args["mid-evidence"] ??
    "docs/control-valve-video/evidence/gop6-mid-scroll.png",
);
const variants = ["gop3", "gop6", "gop10"];
const viewport = { width: 1280, height: 800 };

if (!baseUrl || !modulePath) {
  throw new Error("--url and --playwright-module are required");
}

await mkdir(dirname(outputPath), { recursive: true });
await mkdir(dirname(posterEvidencePath), { recursive: true });
await mkdir(dirname(midEvidencePath), { recursive: true });
const { chromium } = await import(pathToFileURL(modulePath).href);
const browser = await chromium.launch({
  headless: true,
  executablePath: browserExecutable || undefined,
  args: ["--enable-gpu", "--ignore-gpu-blocklist"],
});

try {
  const posterContext = await browser.newContext({
    viewport,
    deviceScaleFactor: 1,
    reducedMotion: "no-preference",
  });
  const posterPage = await posterContext.newPage();
  await posterPage.route("**/*.mp4", async (route) => {
    await new Promise((resolvePromise) => setTimeout(resolvePromise, 1200));
    await route.continue();
  });
  await posterPage.goto(`${baseUrl}?variant=gop6`, {
    waitUntil: "domcontentloaded",
  });
  await posterPage.waitForTimeout(160);
  const posterBeforeVideo = await posterPage.evaluate(() => {
    const image = document.querySelector("#poster");
    const video = document.querySelector("#product-video");
    return {
      posterVisible:
        getComputedStyle(image).opacity !== "0" &&
        image.naturalWidth > 0 &&
        image.getBoundingClientRect().width > 0,
      posterNaturalWidth: image.naturalWidth,
      posterNaturalHeight: image.naturalHeight,
      videoReadyState: video.readyState,
      videoOpacity: getComputedStyle(video).opacity,
    };
  });
  await posterPage.screenshot({ path: posterEvidencePath });
  await posterContext.close();

  const results = [];
  let browserIdentity = null;
  for (const variant of variants) {
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
    const startedAt = performance.now();
    await page.goto(`${baseUrl}?variant=${variant}&benchmark=1`, {
      waitUntil: "domcontentloaded",
    });
    const ready = await page.evaluate(() =>
      window.__VIDEO_SCRUB_METRICS__.waitForReady(),
    );
    const coldReadyMs = performance.now() - startedAt;
    browserIdentity ??= await page.evaluate(() => ({
      userAgent: navigator.userAgent,
      hardwareConcurrency: navigator.hardwareConcurrency,
      deviceMemory: navigator.deviceMemory ?? null,
    }));

    const runSequence = async (sequence) => {
      const sequenceResults = [];
      for (const progress of sequence) {
        sequenceResults.push(
          await page.evaluate(
            (value) => window.__VIDEO_SCRUB_METRICS__.seekTo(value),
            progress,
          ),
        );
      }
      return sequenceResults;
    };

    const forward = await runSequence([
      0,
      0.1,
      0.2,
      0.3,
      0.4,
      0.5,
      0.6,
      0.7,
      0.8,
      0.9,
      1,
    ]);
    const reverse = await runSequence([
      1,
      0.9,
      0.8,
      0.7,
      0.6,
      0.5,
      0.4,
      0.3,
      0.2,
      0.1,
      0,
    ]);

    const rapidTargets = [0.05, 0.88, 0.16, 0.77, 0.28, 0.64, 0.37];
    const beforeRapid = await page.evaluate(() =>
      window.__VIDEO_SCRUB_METRICS__.snapshot(),
    );
    for (const progress of rapidTargets) {
      await page.evaluate(
        (value) => window.__VIDEO_SCRUB_METRICS__.setTarget(value),
        progress,
      );
    }
    const rapid = await page.evaluate(
      (value) => window.__VIDEO_SCRUB_METRICS__.waitForSettled(value),
      rapidTargets.at(-1),
    );
    const afterRapid = await page.evaluate(() =>
      window.__VIDEO_SCRUB_METRICS__.snapshot(),
    );
    const repeated = await runSequence([0.37, 0.37, 0.37, 0.37, 0.37]);
    if (variant === "gop6") {
      await page.evaluate(() =>
        window.__VIDEO_SCRUB_METRICS__.seekTo(0.5),
      );
      await page.screenshot({ path: midEvidencePath });
    }
    const finalSnapshot = await page.evaluate(() =>
      window.__VIDEO_SCRUB_METRICS__.snapshot(),
    );
    const resources = await page.evaluate(() =>
      performance
        .getEntriesByType("resource")
        .filter((entry) => entry.name.includes(".mp4"))
        .map((entry) => ({
          name: entry.name,
          durationMs: entry.duration,
          transferSize: entry.transferSize,
          encodedBodySize: entry.encodedBodySize,
          decodedBodySize: entry.decodedBodySize,
        })),
    );
    results.push({
      variant,
      cacheMode: "cold isolated browser context",
      viewport: { ...viewport, dpr: 1 },
      coldReadyMs,
      firstVideoFrameMs: ready.firstVideoFrameMs,
      media: {
        duration: ready.duration,
        readyState: ready.readyState,
        seekable: ready.seekable,
        seekConfirmation: ready.seekConfirmation,
      },
      forward: summarize(forward),
      reverse: summarize(reverse),
      rapid: {
        submittedTargetCount: rapidTargets.length,
        committedSeekDelta:
          afterRapid.seekHistory.length - beforeRapid.seekHistory.length,
        finalTarget: rapidTargets.at(-1),
        ...rapid,
      },
      repeated: summarize(repeated),
      controller: {
        timeoutCount: finalSnapshot.timeoutCount,
        committedSeekCount: finalSnapshot.seekHistory.length,
        finalTargetTime: finalSnapshot.targetTime,
        finalActualTime: finalSnapshot.actualTime,
      },
      resources,
      consoleErrors,
      pageErrors,
      failedRequests,
    });
    await context.close();
  }

  const artifact = {
    schemaVersion: 1,
    collectedAt: new Date().toISOString(),
    sourceUrl: baseUrl,
    comparisonBoundary:
      "Same local origin, browser executable, 1280x800 viewport, DPR 1 and isolated cold browser context per GOP variant.",
    browser: browserIdentity,
    posterBeforeVideo: {
      ...posterBeforeVideo,
      evidencePath:
        "docs/control-valve-video/evidence/poster-before-video.png",
    },
    midScrollEvidencePath:
      "docs/control-valve-video/evidence/gop6-mid-scroll.png",
    variants: results,
  };
  await writeFile(outputPath, `${JSON.stringify(artifact, null, 2)}\n`, "utf8");
  process.stdout.write(`${JSON.stringify(artifact, null, 2)}\n`);
} finally {
  await browser.close();
}
