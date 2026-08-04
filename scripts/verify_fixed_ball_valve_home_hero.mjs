#!/usr/bin/env node

import { stat, writeFile } from "node:fs/promises";
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
    const samples = [];
    for (let yIndex = 1; yIndex <= 5; yIndex += 1) {
      for (let xIndex = 1; xIndex <= 7; xIndex += 1) {
        samples.push([
          Math.floor(width * xIndex / 8),
          Math.floor(height * yIndex / 6),
        ]);
      }
    }
    const corners = [
      [0, 0],
      [width - 1, 0],
      [0, height - 1],
      [width - 1, height - 1],
    ];
    const pixels = samples.map(([x, y]) => Array.from(context.getImageData(x, y, 1, 1).data));
    const cornerPixels = corners.map(([x, y]) => Array.from(context.getImageData(x, y, 1, 1).data));
    const alphaPixels = pixels.filter((pixel) => pixel[3] > 0).length;
    const cornerAlphaMax = Math.max(...cornerPixels.map((pixel) => pixel[3]));
    let signature = 2166136261;
    for (const pixel of pixels) {
      for (const channel of pixel) {
        signature ^= channel;
        signature = Math.imul(signature, 16777619) >>> 0;
      }
    }
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
      staticSample: canvas.dataset.staticSample === "true",
      alphaPixels,
      cornerAlphaMax,
      signature: signature.toString(16).padStart(8, "0"),
      mean,
      dataPrefix: canvas.toDataURL("image/png").slice(0, 64),
    };
  });
}

async function heroGeometryProbe(page) {
  return page.evaluate(() => {
    const roundRect = (rect) => ({
      top: Math.round(rect.top),
      right: Math.round(rect.right),
      bottom: Math.round(rect.bottom),
      left: Math.round(rect.left),
      width: Math.round(rect.width),
      height: Math.round(rect.height),
    });
    const heroElements = document.querySelector(".hero-elements");
    const heroFrames = document.querySelector(".hero-frames");
    const canvas = document.querySelector("#image-sequence");
    const heroInfo = document.querySelector(".hero-info");
    const heroInfoStyle = heroInfo ? getComputedStyle(heroInfo) : null;
    const heroFramesStyle = heroFrames ? getComputedStyle(heroFrames) : null;
    const canvasStyle = canvas ? getComputedStyle(canvas) : null;
    return {
      scrollY: Math.round(window.scrollY),
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight,
      },
      heroElements: heroElements ? roundRect(heroElements.getBoundingClientRect()) : null,
      heroFrames: heroFrames ? roundRect(heroFrames.getBoundingClientRect()) : null,
      heroFramesStyle: heroFramesStyle ? {
        position: heroFramesStyle.position,
        bottom: heroFramesStyle.bottom,
        height: heroFramesStyle.height,
      } : null,
      canvas: canvas ? roundRect(canvas.getBoundingClientRect()) : null,
      canvasStyle: canvasStyle ? {
        transform: canvasStyle.transform,
        opacity: canvasStyle.opacity,
      } : null,
      heroInfo: heroInfo ? {
        rect: roundRect(heroInfo.getBoundingClientRect()),
        opacity: Number(heroInfoStyle.opacity),
        transform: heroInfoStyle.transform,
      } : null,
    };
  });
}

async function heroWordmarkProbe(page) {
  return page.evaluate(() => {
    const wordmark = document.querySelector(".section-hero .hero-title-wordmark");
    if (!wordmark) return { exists: false, visible: false, text: "" };
    const style = getComputedStyle(wordmark);
    const rect = wordmark.getBoundingClientRect();
    return {
      exists: true,
      visible: style.display !== "none" && style.visibility !== "hidden" && Number(style.opacity) > 0 && rect.width > 0 && rect.height > 0,
      text: wordmark.textContent.trim(),
      width: Math.round(rect.width),
      height: Math.round(rect.height),
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

const moduleStats = await stat(modulePath);
const playwrightModulePath = moduleStats.isDirectory() ? resolve(modulePath, "index.js") : modulePath;
const playwright = await import(pathToFileURL(playwrightModulePath).href);
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
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(250);
  const wordmarkProbe = await heroWordmarkProbe(page);
  const firstProbe = await canvasProbe(page);
  const firstGeometry = await heroGeometryProbe(page);
  await page.screenshot({ path: resolve(dirname(out), "homepage-desktop-first-view.png"), fullPage: false });
  const scrollTargets = await page.evaluate(() => {
    const section = document.querySelector(".section-hero");
    const scrollSpan = Math.max(0, (section?.getBoundingClientRect().height ?? window.innerHeight * 2) - window.innerHeight);
    return {
      mid: Math.round(scrollSpan * 0.55),
      expanded: Math.round(scrollSpan * 0.98),
      info: Math.round(scrollSpan + window.innerHeight * 0.15),
    };
  });
  await page.evaluate((scrollY) => window.scrollTo(0, scrollY), scrollTargets.mid);
  await page.waitForTimeout(700);
  const midProbe = await canvasProbe(page);
  const midGeometry = await heroGeometryProbe(page);
  await page.screenshot({ path: resolve(dirname(out), "homepage-desktop-mid-expand.png"), fullPage: false });
  await page.evaluate((scrollY) => window.scrollTo(0, scrollY), scrollTargets.expanded);
  await page.waitForTimeout(800);
  const expandedProbe = await canvasProbe(page);
  const expandedGeometry = await heroGeometryProbe(page);
  await page.screenshot({ path: resolve(dirname(out), "homepage-desktop-expanded.png"), fullPage: false });
  await page.evaluate((scrollY) => window.scrollTo(0, scrollY), scrollTargets.info);
  await page.waitForTimeout(700);
  const infoGeometry = await heroGeometryProbe(page);
  await page.screenshot({ path: resolve(dirname(out), "homepage-desktop-info-visible.png"), fullPage: false });
  const catalogLink = await page.locator(".section-hero a[href='catalog/index.html']").first().evaluate((link) => ({
    text: link.textContent.trim(),
    href: link.href,
  }));
  if (wordmarkProbe.visible || wordmarkProbe.text === "ZTOVALVE") {
    fail("Desktop hero wordmark is still visible or present as hero text", { wordmarkProbe });
  }
  if (!firstProbe.exists || !firstProbe.classReady || firstProbe.alphaPixels === 0) {
    fail("Desktop hero canvas did not draw a visible first frame", { firstProbe });
  }
  if (firstProbe.staticSample) {
    fail("Desktop hero sequence is still marked as a static sample", { firstProbe });
  }
  if (firstProbe.cornerAlphaMax !== 0 || expandedProbe.cornerAlphaMax !== 0) {
    fail("Desktop hero canvas corners are not transparent", { firstProbe, expandedProbe });
  }
  if (!expandedProbe.exists || expandedProbe.alphaPixels === 0) {
    fail("Desktop hero canvas went blank after scroll", { expandedProbe });
  }
  if (firstProbe.signature === midProbe.signature && firstProbe.signature === expandedProbe.signature) {
    fail("Desktop hero canvas did not visibly change after scroll", { firstProbe, midProbe, expandedProbe });
  }
  if (!firstGeometry.heroElements || !firstGeometry.heroFrames || firstGeometry.heroElements.height < 1 || firstGeometry.heroFrames.height < 1) {
    fail("Desktop hero geometry could not be measured", { firstGeometry });
  }
  if (firstGeometry.heroFrames.height > firstGeometry.heroElements.height * 0.35) {
    fail("Desktop hero frames no longer start from a compact ROKE-style height", { firstGeometry });
  }
  if (!expandedGeometry.heroElements || !expandedGeometry.heroFrames || expandedGeometry.heroFrames.height < expandedGeometry.heroElements.height * 0.9) {
    fail("Desktop hero frames did not expand close to the full hero height", { firstGeometry, midGeometry, expandedGeometry });
  }
  if (firstGeometry.heroFramesStyle?.position !== "absolute") {
    fail("Desktop hero frames are not bottom-anchored with absolute positioning", { firstGeometry });
  }
  if (!infoGeometry.heroInfo || infoGeometry.heroInfo.opacity < 0.85) {
    fail("Desktop hero info layer did not fade in after the product expansion", { firstGeometry, expandedGeometry, infoGeometry });
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
      wordmarkProbe,
      firstProbe,
      midProbe,
      expandedProbe,
      geometry: {
        scrollTargets,
        first: firstGeometry,
        mid: midGeometry,
        expanded: expandedGeometry,
        info: infoGeometry,
      },
      catalogLink,
      screenshots: [
        "docs/assets/ztovalve/hero/homepage-desktop-first-view.png",
        "docs/assets/ztovalve/hero/homepage-desktop-mid-expand.png",
        "docs/assets/ztovalve/hero/homepage-desktop-expanded.png",
        "docs/assets/ztovalve/hero/homepage-desktop-info-visible.png",
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
