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
      rafPending: 0,
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
    const nativeCancelAnimationFrame = window.cancelAnimationFrame.bind(window);
    const pendingAnimationFrames = new Set();

    window.requestAnimationFrame = (callback) => {
      probe.rafScheduled += 1;
      let requestId = 0;
      requestId = nativeRequestAnimationFrame((timestamp) => {
        if (pendingAnimationFrames.delete(requestId)) {
          probe.rafPending = pendingAnimationFrames.size;
        }
        probe.rafFired += 1;
        callback(timestamp);
      });
      pendingAnimationFrames.add(requestId);
      probe.rafPending = pendingAnimationFrames.size;
      return requestId;
    };

    window.cancelAnimationFrame = (requestId) => {
      if (pendingAnimationFrames.delete(requestId)) {
        probe.rafPending = pendingAnimationFrames.size;
      }
      nativeCancelAnimationFrame(requestId);
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

export async function getRafSnapshot(page) {
  return page.evaluate(() => {
    const probe = window.__ROKE_E2E_PERFORMANCE__;
    return {
      fired: probe.rafFired,
      pending: probe.rafPending,
      scheduled: probe.rafScheduled,
    };
  });
}

export async function scrollToProgress(page, progress) {
  return page.evaluate(async (targetProgress) => {
    const output = document.querySelector("#progress-output");
    const target = Math.round(targetProgress * 100);
    const scrollable = document.documentElement.scrollHeight - window.innerHeight;
    const start = performance.now();

    return new Promise((resolve) => {
      let settled = false;

      const finish = (reached) => {
        if (settled) return;
        settled = true;
        window.clearTimeout(timeout);
        observer.disconnect();
        resolve({
          reached,
          latencyMs: performance.now() - start,
          actual: Number.parseInt(output?.value || output?.textContent || "-1", 10),
          target,
        });
      };

      const finishIfReady = () => {
        const current = Number.parseInt(output?.value || output?.textContent || "-1", 10);
        if (Math.abs(current - target) <= 1) finish(true);
      };

      const observer = new MutationObserver(finishIfReady);
      if (output) {
        observer.observe(output, {
          attributes: true,
          characterData: true,
          childList: true,
          subtree: true,
        });
      }

      const timeout = window.setTimeout(() => finish(false), 3000);
      window.scrollTo(0, scrollable * targetProgress);
      finishIfReady();
    });
  }, progress);
}

export async function getRuntimeSnapshot(page) {
  return page.evaluate(() => {
    const runtime = window.__ROKE_3D_RUNTIME__;
    if (!runtime || typeof runtime.snapshot !== "function") return null;
    return structuredClone(runtime.snapshot());
  });
}

export function maxAbsoluteDifference(left, right) {
  if (!Array.isArray(left) || !Array.isArray(right) || left.length !== right.length) {
    return Number.POSITIVE_INFINITY;
  }

  let maximum = 0;
  for (let index = 0; index < left.length; index += 1) {
    maximum = Math.max(maximum, Math.abs(left[index] - right[index]));
  }
  return maximum;
}

export function resourceBytes(resource) {
  return resource.transferSize || resource.encodedBodySize || 0;
}
