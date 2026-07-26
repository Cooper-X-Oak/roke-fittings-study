#!/usr/bin/env node

import { createReadStream } from "node:fs";
import { mkdir, stat } from "node:fs/promises";
import { createServer } from "node:http";
import { extname, join, normalize, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const root = resolve(new URL("../../..", import.meta.url).pathname.slice(1));
const output = join(root, "creative", "car-concept", "storyboards");
const playwrightPath = process.argv[2];
const browserExecutable = process.argv[3];
if (!playwrightPath) {
  throw new Error("Pass the absolute path to Playwright index.mjs");
}

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".glb": "model/gltf-binary",
  ".wasm": "application/wasm",
  ".ktx2": "image/ktx2",
};

const server = createServer(async (request, response) => {
  const url = new URL(request.url ?? "/", "http://127.0.0.1");
  const requested = decodeURIComponent(url.pathname).replace(/^\/+/u, "");
  const path = normalize(join(root, requested || "index.html"));
  if (!path.toLowerCase().startsWith(root.toLowerCase())) {
    response.writeHead(403).end("Forbidden");
    return;
  }
  try {
    const info = await stat(path);
    const file = info.isDirectory() ? join(path, "index.html") : path;
    response.writeHead(200, {
      "Content-Type": MIME[extname(file).toLowerCase()] ?? "application/octet-stream",
      "Cache-Control": "no-store",
    });
    createReadStream(file).pipe(response);
  } catch {
    response.writeHead(404).end("Not found");
  }
});

await new Promise((resolveListen) => {
  server.listen(0, "127.0.0.1", resolveListen);
});
const address = server.address();
const port = typeof address === "object" && address ? address.port : 0;

const { chromium } = await import(pathToFileURL(playwrightPath).href);
const browser = await chromium.launch({
  headless: true,
  executablePath: browserExecutable || undefined,
  args: ["--enable-gpu", "--enable-webgl", "--ignore-gpu-blocklist"],
});

try {
  await mkdir(output, { recursive: true });
  const page = await browser.newPage({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
  });
  page.on("console", (message) => {
    if (message.type() === "error") {
      process.stderr.write(`browser console: ${message.text()}\n`);
    }
  });
  for (let shot = 1; shot <= 5; shot += 1) {
    await page.goto(
      `http://127.0.0.1:${port}/creative/car-concept/previs/index.html?shot=${shot}`,
      { waitUntil: "networkidle" },
    );
    await page.waitForFunction(() => window.__PREVIS_READY__ === true, null, {
      timeout: 30000,
    });
    await page.screenshot({
      path: join(output, `shot-${String(shot).padStart(2, "0")}.png`),
    });
  }
} finally {
  await browser.close();
  await new Promise((resolveClose) => server.close(resolveClose));
}

process.stdout.write(`Captured five storyboard frames in ${output}\n`);
