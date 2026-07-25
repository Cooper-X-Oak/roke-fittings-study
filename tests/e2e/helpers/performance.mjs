import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const helperDirectory = path.dirname(fileURLToPath(import.meta.url));
const repositoryRoot = path.resolve(helperDirectory, "../../..");

export async function loadPerformanceBudget() {
  const budgetPath = path.join(repositoryRoot, "tests/performance-budget.json");
  return JSON.parse(await fs.readFile(budgetPath, "utf8"));
}

export async function installPerformanceProbe(page) {
  await page.addInitScript(() => {
    const probe = {
      rafScheduled: 0,
      rafFired: 0,
      lcp: 0,
      cls: 0,
      longTasks: [],
    };

    Object.defineProperty(window, "__ROKE_E2E_PERFORMANCE__", {
      configurable: false,
      enumerable: false,
      writable: false,
      value: probe,
    });

    const nativeRequestAnimationFrame = window.requestAnimationFrame.bind(window);
    window.requestAnimationFrame = (callback) => {
      probe.rafScheduled += 1;
      return nativeRequestAnimationFrame((timestamp) => {
        probe.rafFired += 1;
        callback(timestamp);
      });
    };

    try {
      new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          probe.lcp = Math.max(
            probe.lcp,
            entry.renderTime || entry.loadTime || entry.startTime || 0,
          );
        }
      }).observe({ type: "largest-contentful-paint", buffered: true });
    } catch {
      // The assertion reports an unavailable LCP value as a test failure.
    }

    try {
      new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (!entry.hadRecentInput) probe.cls += entry.value;
        }
      }).observe({ type: "layout-shift", buffered: true });
    } catch {
      // The assertion reports an unavailable CLS value as a test failure.
    }

    try {
      new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          probe.longTasks.push({
            startTime: entry.startTime,
            duration: entry.duration,
          });
        }
      }).observe({ type: "longtask", buffered: true });
    } catch {
      // Long-task reporting is evidence-only when the browser omits the API.
    }
  });
}

export async function applyNetworkProfile(context, page, network) {
  const session = await context.newCDPSession(page);
  await session.send("Network.enable");
  await session.send("Network.emulateNetworkConditions", {
    offline: false,
    latency: network.latencyMs,
    downloadThroughput: (network.downloadKbps * 1024) / 8,
    uploadThroughput: (network.uploadKbps * 1024) / 8,
    connectionType: "cellular4g",
  });
  return session;
}

export async function waitForWebglState(page, acceptedStates, timeout = 20_000) {
  await page.waitForFunction(
    (states) => states.includes(document.body.dataset.webglState),
    acceptedStates,
    { timeout },
  );
}

export async function getPerformanceSnapshot(page) {
  return page.evaluate(() => {
    const marks = Object.fromEntries(
      performance.getEntriesByType("mark").map((entry) => [entry.name, entry.startTime]),
    );

    const resources = performance.getEntriesByType("resource").map((entry) => ({
      name: entry.name,
      initiatorType: entry.initiatorType,
      startTime: entry.startTime,
      responseEnd: entry.responseEnd,
      transferSize: entry.transferSize,
      encodedBodySize: entry.encodedBodySize,
      decodedBodySize: entry.decodedBodySize,
    }));

    return {
      now: performance.now(),
      marks,
      resources,
      metrics: structuredClone(window.__ROKE_E2E_PERFORMANCE__),
      domContentLoaded: performance.getEntriesByType("navigation")[0]?.domContentLoadedEventEnd || 0,
    };
  });
}

export async function getRafFiredCount(page) {
  return page.evaluate(() => window.__ROKE_E2E_PERFORMANCE__.rafFired);
}

export async function scrollToProgress(page, progress) {
  return page.evaluate(async (targetProgress) => {
    const output = document.querySelector("#progress-output");
    const target = Math.round(targetProgress * 100);
    const scrollable = document.documentElement.scrollHeight - window.innerHeight;
    const start = performance.now();

    return new Promise((resolve, reject) => {
      const timeout = window.setTimeout(() => {
        observer.disconnect();
        reject(new Error(`Progress output did not reach ${target}`));
      }, 3000);

      const finishIfReady = () => {
        const current = Number.parseInt(output?.value || output?.textContent || "-1", 10);
        if (Math.abs(current - target) > 1) return;
        window.clearTimeout(timeout);
        observer.disconnect();
        resolve(performance.now() - start);
      };

      const observer = new MutationObserver(finishIfReady);
      observer.observe(output, {
        attributes: true,
        characterData: true,
        childList: true,
        subtree: true,
      });

      window.scrollTo(0, scrollable * targetProgress);
      finishIfReady();
    });
  }, progress);
}

export async function captureCanvasSignature(page) {
  const canvas = page.locator("#webgl-canvas");
  const bounds = await canvas.boundingBox();
  if (!bounds || bounds.width <= 0 || bounds.height <= 0) {
    throw new Error("WebGL canvas has no visible screenshot bounds");
  }

  // Element screenshots wait for the target to become visually stable. That is
  // the wrong measurement primitive for detecting a hot RAF loop, because the
  // defect under test keeps the canvas changing forever. Clip the page directly
  // so a continuously rendered canvas remains measurable instead of timing out.
  const screenshot = await page.screenshot({
    type: "png",
    clip: bounds,
    animations: "allow",
  });
  const base64 = screenshot.toString("base64");

  return page.evaluate(async (encoded) => {
    const binary = atob(encoded);
    const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
    const bitmap = await createImageBitmap(new Blob([bytes], { type: "image/png" }));
    const sample = new OffscreenCanvas(32, 32);
    const context = sample.getContext("2d", { willReadFrequently: true });
    context.drawImage(bitmap, 0, 0, sample.width, sample.height);
    bitmap.close();
    return Array.from(context.getImageData(0, 0, sample.width, sample.height).data);
  }, base64);
}

export function meanAbsoluteDifference(left, right) {
  if (left.length !== right.length) return Number.POSITIVE_INFINITY;
  let total = 0;
  for (let index = 0; index < left.length; index += 1) {
    total += Math.abs(left[index] - right[index]);
  }
  return total / left.length;
}

export function resourceBytes(resource) {
  return resource.transferSize || resource.encodedBodySize || 0;
}
