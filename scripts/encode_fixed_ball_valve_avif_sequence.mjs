#!/usr/bin/env node

import { createHash } from "node:crypto";
import { mkdir, readFile, readdir, stat, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { createRequire } from "node:module";

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

async function sha256(path) {
  return createHash("sha256").update(await readFile(path)).digest("hex");
}

const args = parseArgs(process.argv.slice(2));
const toolsDir = resolve(args["tools-dir"] ?? ".scratch/goal9-tools");
const pngDir = resolve(args["png-dir"] ?? ".scratch/goal9-release-png-240");
const avifDir = resolve(args["avif-dir"] ?? "docs/upload/images/zt-hero-fixed-ball-valve");
const outputPath = resolve(args.out ?? "docs/assets/ztovalve/hero/avif-sequence-manifest.json");
const quality = Number(args.quality ?? 54);
const effort = Number(args.effort ?? 4);
const requireFromTools = createRequire(resolve(toolsDir, "package.json"));
const sharp = requireFromTools("sharp");

await mkdir(avifDir, { recursive: true });
const existingAvif = (await readdir(avifDir)).filter((name) => /^\d{4}\.avif$/u.test(name));
if (existingAvif.length > 0) {
  throw new Error(`AVIF output directory already contains numbered frames: ${avifDir}`);
}

const pngFrames = (await readdir(pngDir))
  .filter((name) => /^\d{4}\.png$/u.test(name))
  .sort();
if (pngFrames.length !== 240) {
  throw new Error(`Expected 240 PNG frames, found ${pngFrames.length} in ${pngDir}`);
}

const frames = [];
const combined = createHash("sha256");
const startedAt = performance.now();
for (let index = 0; index < pngFrames.length; index += 1) {
  const pngName = pngFrames[index];
  const avifName = pngName.replace(/\.png$/u, ".avif");
  const pngPath = resolve(pngDir, pngName);
  const avifPath = resolve(avifDir, avifName);
  const image = sharp(pngPath, { limitInputPixels: false });
  const metadata = await image.metadata();
  await image
    .avif({
      quality,
      effort,
      chromaSubsampling: "4:2:0",
    })
    .toFile(avifPath);
  const bytes = (await stat(avifPath)).size;
  const digest = await sha256(avifPath);
  combined.update(`${index}:${digest}:${bytes}\n`);
  frames.push({
    frame: index,
    filename: avifName,
    path: `docs/upload/images/zt-hero-fixed-ball-valve/${avifName}`,
    sourcePng: pngPath.replace(/\\/g, "/"),
    width: metadata.width,
    height: metadata.height,
    hasAlpha: metadata.hasAlpha === true,
    bytes,
    sha256: digest,
  });
  if (index % 30 === 0 || index === pngFrames.length - 1) {
    process.stdout.write(`encoded ${index + 1}/${pngFrames.length}\n`);
  }
}

const manifest = {
  schemaVersion: 1,
  generatedAt: new Date().toISOString(),
  encoder: {
    tool: "sharp",
    version: sharp.versions.sharp,
    quality,
    effort,
    chromaSubsampling: "4:2:0",
  },
  sourcePngDirectory: pngDir.replace(/\\/g, "/"),
  avifDirectory: avifDir.replace(/\\/g, "/"),
  frameCount: frames.length,
  dimensions: { width: frames[0].width, height: frames[0].height },
  allSourcesHaveAlpha: frames.every((frame) => frame.hasAlpha),
  totalAvifBytes: frames.reduce((sum, frame) => sum + frame.bytes, 0),
  combinedAvifSha256: combined.digest("hex"),
  encodeDurationMs: Math.round(performance.now() - startedAt),
  frames,
};
await writeFile(outputPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
process.stdout.write(`Encoded ${frames.length} AVIF frames to ${avifDir}\n`);
