#!/usr/bin/env node
import { spawn } from "node:child_process";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "..");
const outcomeRoot = path.join(repoRoot, "outcome");
const toolsPackage = path.join(repoRoot, ".scratch", "__pycache__", "goal9-tools", "package.json");
const requireFromTools = createRequire(toolsPackage);
const { chromium } = requireFromTools("playwright-core");

const outDir = path.join(outcomeRoot, "validation-results", "hero-roke-green");
const port = Number(process.env.ZT_HERO_VERIFY_PORT || 4181);
const baseUrl = `http://127.0.0.1:${port}/ztovalue/`;
fs.mkdirSync(outDir, { recursive: true });

function fail(message, details = {}) {
  const error = new Error(message);
  error.details = details;
  throw error;
}

function browserExecutable() {
  return [
    process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE,
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  ].filter(Boolean).find((candidate) => fs.existsSync(candidate));
}

function waitForHttp(url, timeoutMs = 20000) {
  const started = Date.now();
  return new Promise((resolve, reject) => {
    const attempt = () => {
      const request = http.get(url, (response) => {
        response.resume();
        if (response.statusCode && response.statusCode >= 200 && response.statusCode < 500) {
          resolve();
        } else {
          retry();
        }
      });
      request.on("error", retry);
      request.setTimeout(1200, () => {
        request.destroy();
        retry();
      });
    };
    const retry = () => {
      if (Date.now() - started > timeoutMs) {
        reject(new Error(`Timed out waiting for ${url}`));
        return;
      }
      setTimeout(attempt, 250);
    };
    attempt();
  });
}

async function canvasProbe(page) {
  return page.evaluate(() => {
    const canvas = document.querySelector("#image-sequence");
    if (!canvas) return { exists: false };
    const context = canvas.getContext("2d", { willReadFrequently: true });
    const width = canvas.width;
    const height = canvas.height;
    const points = [
      [0, 0],
      [width - 1, 0],
      [0, height - 1],
      [width - 1, height - 1],
      [Math.floor(width / 2), Math.floor(height / 2)],
      [Math.floor(width * 0.34), Math.floor(height * 0.48)],
      [Math.floor(width * 0.66), Math.floor(height * 0.48)],
    ];
    const pixels = points.map(([x, y]) => Array.from(context.getImageData(x, y, 1, 1).data));
    let signature = 2166136261;
    for (const pixel of pixels) {
      for (const channel of pixel) {
        signature ^= channel;
        signature = Math.imul(signature, 16777619) >>> 0;
      }
    }
    return {
      exists: true,
      width,
      height,
      ready: canvas.closest(".hero-frames")?.classList.contains("is-sequence-ready") ?? false,
      cornerRgb: pixels.slice(0, 4).map((pixel) => pixel.slice(0, 3)),
      signature: signature.toString(16).padStart(8, "0"),
    };
  });
}

async function wordmarkProbe(page) {
  return page.evaluate(() => {
    const wrapper = document.querySelector(".hero-title-svg-wrapper");
    const svg = document.querySelector(".hero-title-svg");
    if (!wrapper || !svg) return { exists: false };
    const rect = wrapper.getBoundingClientRect();
    const style = getComputedStyle(svg);
    return {
      exists: true,
      visible: rect.width > 0 && rect.height > 0 && Number(style.opacity) > 0.2,
      opacity: Number(style.opacity),
      text: svg.textContent.trim(),
      rect: {
        width: Math.round(rect.width),
        height: Math.round(rect.height),
        top: Math.round(rect.top),
        bottom: Math.round(rect.bottom),
      },
    };
  });
}

function assertGreenCorners(probe, label) {
  const target = [0x47, 0x71, 0x4D];
  const maxDelta = Math.max(...probe.cornerRgb.flatMap((pixel) => pixel.map((value, index) => Math.abs(value - target[index]))));
  if (maxDelta > 8) fail(`${label} canvas corners are not green`, { probe, maxDelta });
}

let server;
try {
  server = spawn(process.execPath, ["scripts/serve-preview.mjs", "dist", "/ztovalue", String(port)], {
    cwd: outcomeRoot,
    stdio: ["ignore", "pipe", "pipe"],
  });
  await waitForHttp(baseUrl);

  const executablePath = browserExecutable();
  if (!executablePath) fail("No Chrome or Edge executable found for Playwright homepage verification");
  const browser = await chromium.launch({ headless: true, executablePath });

  const desktop = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1, reducedMotion: "no-preference" });
  const page = await desktop.newPage();
  const consoleErrors = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.waitForFunction(() => document.querySelector(".hero-frames.is-sequence-ready"), null, { timeout: 45000 });
  await page.waitForTimeout(500);
  const firstProbe = await canvasProbe(page);
  const firstWordmark = await wordmarkProbe(page);
  await page.screenshot({ path: path.join(outDir, "desktop-first-view.png"), fullPage: false });

  const scrollTargets = await page.evaluate(() => {
    const section = document.querySelector(".section-hero");
    const scrollSpan = Math.max(0, (section?.getBoundingClientRect().height ?? window.innerHeight * 2) - window.innerHeight);
    return { mid: Math.round(scrollSpan * 0.55), expanded: Math.round(scrollSpan * 0.98) };
  });
  await page.evaluate((scrollY) => window.scrollTo(0, scrollY), scrollTargets.mid);
  await page.waitForTimeout(700);
  const midProbe = await canvasProbe(page);
  await page.screenshot({ path: path.join(outDir, "desktop-mid.png"), fullPage: false });
  await page.evaluate((scrollY) => window.scrollTo(0, scrollY), scrollTargets.expanded);
  await page.waitForTimeout(800);
  const expandedProbe = await canvasProbe(page);
  const fadedWordmark = await wordmarkProbe(page);
  await page.screenshot({ path: path.join(outDir, "desktop-expanded.png"), fullPage: false });

  if (!firstProbe.exists || !firstProbe.ready) fail("Desktop hero canvas did not draw", { firstProbe });
  if (firstProbe.width !== 1920 || firstProbe.height !== 1080) fail("Desktop hero canvas resolution is not 1920x1080", { firstProbe });
  assertGreenCorners(firstProbe, "First");
  assertGreenCorners(expandedProbe, "Expanded");
  if (firstProbe.signature === midProbe.signature && firstProbe.signature === expandedProbe.signature) {
    fail("Desktop hero canvas did not visibly change after scroll", { firstProbe, midProbe, expandedProbe });
  }
  if (!firstWordmark.exists || !firstWordmark.visible || !firstWordmark.text.includes("ZTOVALVE")) {
    fail("ZTOVALVE wordmark is not visible in the first desktop viewport", { firstWordmark });
  }
  if (fadedWordmark.exists && fadedWordmark.opacity > firstWordmark.opacity - 0.25) {
    fail("ZTOVALVE wordmark did not fade enough during hero scroll", { firstWordmark, fadedWordmark });
  }
  await desktop.close();

  const mobile = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, reducedMotion: "no-preference" });
  const mobilePage = await mobile.newPage();
  await mobilePage.goto(baseUrl, { waitUntil: "networkidle" });
  const mobileProbe = await mobilePage.evaluate(() => {
    const image = document.querySelector(".section-hero-mobile-image");
    const desktopHeroVisible = getComputedStyle(document.querySelector(".section-hero")).display !== "none";
    return {
      imageSrc: image?.currentSrc || image?.src || "",
      complete: image?.complete ?? false,
      naturalWidth: image?.naturalWidth ?? 0,
      naturalHeight: image?.naturalHeight ?? 0,
      desktopHeroVisible,
    };
  });
  await mobilePage.screenshot({ path: path.join(outDir, "mobile-fallback.png"), fullPage: false });
  if (mobileProbe.desktopHeroVisible) fail("Desktop sequence hero is visible on mobile viewport", { mobileProbe });
  if (!mobileProbe.complete || mobileProbe.naturalWidth !== 1920 || mobileProbe.naturalHeight !== 1080) {
    fail("Mobile fallback is not the 1920x1080 green fallback", { mobileProbe });
  }
  await mobile.close();
  await browser.close();

  const result = {
    schema: "ztovalve-fixed-ball-valve-roke-green-homepage-validation/v1",
    status: "pass",
    url: baseUrl,
    desktop: { firstProbe, midProbe, expandedProbe, firstWordmark, fadedWordmark },
    mobile: mobileProbe,
    screenshots: path.relative(repoRoot, outDir).replaceAll("\\", "/"),
    consoleErrors,
  };
  fs.writeFileSync(path.join(outDir, "homepage-validation.json"), `${JSON.stringify(result, null, 2)}\n`, "utf8");
  console.log(JSON.stringify(result, null, 2));
} finally {
  if (server && !server.killed) server.kill();
}
