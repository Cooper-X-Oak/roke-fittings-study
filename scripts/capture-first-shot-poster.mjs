#!/usr/bin/env node

import process from "node:process";
import { writeFile } from "node:fs/promises";
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

const args = parseArgs(process.argv.slice(2));
const url = args.url;
const out = args.out;
const playwrightModule = args["playwright-module"] ?? "playwright";
const browserExecutable = args["browser-executable"];

if (!url || !out) {
  throw new Error("--url and --out are required");
}

const moduleSpecifier = /^[A-Za-z]:[\\/]/u.test(playwrightModule)
  ? pathToFileURL(playwrightModule).href
  : playwrightModule;
const { chromium } = await import(moduleSpecifier);
const browser = await chromium.launch({
  headless: true,
  executablePath: browserExecutable || undefined,
  args: ["--enable-gpu", "--enable-webgl", "--ignore-gpu-blocklist"],
});

try {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1,
  });
  await page.goto(url, { waitUntil: "networkidle" });
  const dataUrl = await page.evaluate(async () => {
    await window.__CAR_STORY_METRICS__.waitForReady();
    window.__CAR_STORY_METRICS__.setProgressForTest(0);
    await window.__CAR_STORY_METRICS__.waitForSettled();
    return document
      .querySelector("#webgl-canvas")
      .toDataURL("image/jpeg", 0.84);
  });
  const encoded = dataUrl.replace(/^data:image\/jpeg;base64,/u, "");
  await writeFile(out, Buffer.from(encoded, "base64"));
  process.stdout.write(`${out}\n`);
} finally {
  await browser.close();
}
