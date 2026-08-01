#!/usr/bin/env node

import { writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { mkdir } from "node:fs/promises";
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

function fail(message, details = {}) {
  const error = new Error(message);
  error.details = details;
  throw error;
}

async function canvasProbe(page) {
  return page.evaluate(() => {
    const canvas = document.querySelector("#image-sequence");
    if (!canvas) return { exists: false };
    const context = canvas.getContext("2d", { willReadFrequently: true });
    const width = canvas.width;
    const height = canvas.height;
    const samples = [
      [Math.floor(width * 0.5), Math.floor(height * 0.5)],
      [Math.floor(width * 0.38), Math.floor(height * 0.55)],
      [Math.floor(width * 0.62), Math.floor(height * 0.5)],
      [Math.floor(width * 0.5), Math.floor(height * 0.32)],
    ];
    const pixels = samples.map(([x, y]) => Array.from(context.getImageData(x, y, 1, 1).data));
    const alphaPixels = pixels.filter((pixel) => pixel[3] > 0).length;
    const mean = pixels
      .reduce(
        (sum, pixel) => sum.map((value, index) => value + pixel[index]),
        [0, 0, 0, 0],
      )
      .map((value) => Math.round(value / pixels.length));
    return {
      exists: true,
      width,
      height,
      classReady: canvas.closest(".hero-frames")?.classList.contains("is-sequence-ready") ?? false,
      alphaPixels,
      mean,
      dataPrefix: canvas.toDataURL("image/png").slice(0, 64),
    };
  });
}

const args = parseArgs(process.argv.slice(2));
const url = args.url;
const modulePath = args["playwright-module"];
const browserExecutable = args["browser-executable"];
const out = resolve(args.out ?? "docs/assets/ztovalve/hero/homepage-verification.json");

if (!url || !modulePath) {
  throw new Error("--url and --playwright-module are required");
}

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

try {
  const desktop = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1,
    reducedMotion: "no-preference",
  });
  const page = await desktop.newPage();
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
  await page.waitForFunction(() => document.querySelector(".hero-frames.is-sequence-ready"), null, {
    timeout: 45000,
  });
  const firstProbe = await canvasProbe(page);
  await page.screenshot({ path: resolve(dirname(out), "homepage-desktop-first-view.png"), fullPage: false });
  await page.evaluate(() => window.scrollTo(0, Math.floor(window.innerHeight * 1.25)));
  await page.waitForTimeout(800);
  const scrolledProbe = await canvasProbe(page);
  await page.screenshot({ path: resolve(dirname(out), "homepage-desktop-scrolled.png"), fullPage: false });
  const catalogLink = await page.locator(".section-hero a[href='catalog/index.html']").first().evaluate((link) => ({
    text: link.textContent.trim(),
    href: link.href,
  }));
  if (!firstProbe.exists || !firstProbe.classReady || firstProbe.alphaPixels === 0) {
    fail("Desktop hero canvas did not draw a visible first frame", { firstProbe });
  }
  if (!scrolledProbe.exists || scrolledProbe.alphaPixels === 0) {
    fail("Desktop hero canvas went blank after scroll", { scrolledProbe });
  }
  if (JSON.stringify(firstProbe.mean) === JSON.stringify(scrolledProbe.mean)) {
    fail("Desktop hero canvas did not visibly change after scroll", { firstProbe, scrolledProbe });
  }
  if (!catalogLink.href.endsWith("/catalog/index.html")) {
    fail("Catalog CTA href is unexpected", { catalogLink });
  }
  await desktop.close();

  const mobile = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 2,
    isMobile: true,
    reducedMotion: "no-preference",
  });
  const mobilePage = await mobile.newPage();
  await mobilePage.goto(url, { waitUntil: "networkidle" });
  const mobileProbe = await mobilePage.evaluate(() => {
    const image = document.querySelector(".section-hero-mobile-image");
    const desktopHeroVisible = getComputedStyle(document.querySelector(".section-hero")).display !== "none";
    return {
      desktopHeroVisible,
      imageSrc: image?.currentSrc || image?.src || "",
      complete: image?.complete ?? false,
      naturalWidth: image?.naturalWidth ?? 0,
      naturalHeight: image?.naturalHeight ?? 0,
    };
  });
  await mobilePage.screenshot({ path: resolve(dirname(out), "homepage-mobile-fallback.png"), fullPage: false });
  if (mobileProbe.desktopHeroVisible) {
    fail("Desktop sequence hero is visible on mobile viewport", { mobileProbe });
  }
  if (!mobileProbe.complete || mobileProbe.naturalWidth < 1 || !mobileProbe.imageSrc.includes("fixed-ball-valve-mobile-fallback.png")) {
    fail("Mobile fallback image is not loaded", { mobileProbe });
  }
  await mobile.close();

  const result = {
    schemaVersion: 1,
    verifiedAt: new Date().toISOString(),
    url,
    desktop: {
      firstProbe,
      scrolledProbe,
      catalogLink,
      screenshots: [
        "docs/assets/ztovalve/hero/homepage-desktop-first-view.png",
        "docs/assets/ztovalve/hero/homepage-desktop-scrolled.png",
      ],
    },
    mobile: {
      probe: mobileProbe,
      screenshot: "docs/assets/ztovalve/hero/homepage-mobile-fallback.png",
    },
    consoleErrors,
    pageErrors,
    failedRequests,
  };
  await mkdir(dirname(out), { recursive: true });
  await writeFile(out, `${JSON.stringify(result, null, 2)}\n`, "utf8");
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
} finally {
  await browser.close();
}
