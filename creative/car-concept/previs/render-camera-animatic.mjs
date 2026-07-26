#!/usr/bin/env node

import { createReadStream } from "node:fs";
import { mkdir, mkdtemp, rm, stat } from "node:fs/promises";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import { extname, join, normalize, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { pathToFileURL } from "node:url";

const root = resolve(new URL("../../../", import.meta.url).pathname.slice(1));
const output = process.argv[2];
const playwrightPath = process.argv[3];
const browserExecutable = process.argv[4];
const storyboardsOnly = process.argv.includes("--storyboards-only");
if (!output || !playwrightPath) {
  throw new Error("Usage: node render-camera-animatic.mjs <output.mp4> <playwright-index.mjs> [browser.exe]");
}

const artifact = JSON.parse(
  await (await import("node:fs/promises")).readFile(
    join(root, "creative/car-concept/camera-previs.json"),
    "utf8",
  ),
);
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

await new Promise((done) => server.listen(0, "127.0.0.1", done));
const address = server.address();
const port = typeof address === "object" && address ? address.port : 0;
const temp = await mkdtemp(join(tmpdir(), "car-camera-previs-"));
const storyboardDir = join(root, "creative/car-concept/storyboards");
const storyFrames = [52, 150, 220, 338, 430];
const { chromium } = await import(pathToFileURL(playwrightPath).href);
const browser = await chromium.launch({
  headless: true,
  executablePath: browserExecutable || undefined,
  args: ["--enable-gpu", "--enable-webgl", "--ignore-gpu-blocklist"],
});

try {
  await mkdir(storyboardDir, { recursive: true });
  const page = await browser.newPage({
    viewport: { width: 1280, height: 720 },
    deviceScaleFactor: 1,
  });
  page.on("console", (message) => {
    if (message.type() === "error") process.stderr.write(`browser console: ${message.text()}\n`);
  });
  await page.goto(
    `http://127.0.0.1:${port}/creative/car-concept/previs/index.html?frame=0`,
    { waitUntil: "networkidle" },
  );
  await page.waitForFunction(() => window.__PREVIS_READY__ === true, null, { timeout: 30000 });

  if (!storyboardsOnly) {
    for (let frame = 0; frame < artifact.totalFrames; frame += 1) {
      await page.evaluate((value) => window.__setPrevisFrame(value), frame);
      await page.screenshot({
        path: join(temp, `frame-${String(frame).padStart(4, "0")}.jpg`),
        type: "jpeg",
        quality: 92,
      });
      if (frame % 60 === 0) process.stdout.write(`Captured frame ${frame}/${artifact.totalFrames - 1}\n`);
    }
  }

  await page.setViewportSize({ width: 1920, height: 1080 });
  for (let index = 0; index < storyFrames.length; index += 1) {
    await page.evaluate((value) => window.__setPrevisFrame(value), storyFrames[index]);
    await page.screenshot({
      path: join(storyboardDir, `shot-${String(index + 1).padStart(2, "0")}.png`),
      type: "png",
    });
  }
} finally {
  await browser.close();
  await new Promise((done) => server.close(done));
}

const ffmpeg = storyboardsOnly
  ? { status: 0 }
  : spawnSync(
      "ffmpeg",
      [
        "-y",
        "-framerate",
        String(artifact.fps),
        "-i",
        join(temp, "frame-%04d.jpg"),
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "19",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        resolve(output),
      ],
      { stdio: "inherit" },
    );
await rm(temp, { recursive: true, force: true });
if (ffmpeg.status !== 0) {
  throw new Error(`ffmpeg failed with exit code ${ffmpeg.status}`);
}
process.stdout.write(
  storyboardsOnly
    ? `Rendered five camera-path storyboards\n`
    : `Rendered camera-path animatic to ${resolve(output)}\n`,
);
