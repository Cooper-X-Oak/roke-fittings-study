#!/usr/bin/env node

import { createHash } from "node:crypto";
import { mkdir, readFile, readdir, rename, rm, stat, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { createRequire } from "node:module";

const FRAME_COUNT = 240;

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

function expectedName(number, extension) {
  return `${String(number).padStart(4, "0")}.${extension}`;
}

async function alphaStats(sharp, imagePath) {
  const { data, info } = await sharp(imagePath, { limitInputPixels: false })
    .ensureAlpha()
    .raw()
    .toBuffer({ resolveWithObject: true });
  const alphaOffset = info.channels - 1;
  const total = info.width * info.height;
  let transparent = 0;
  let opaque = 0;
  let nonTransparent = 0;
  for (let pixel = 0; pixel < total; pixel += 1) {
    const alpha = data[pixel * info.channels + alphaOffset];
    if (alpha === 0) transparent += 1;
    if (alpha === 255) opaque += 1;
    if (alpha > 0) nonTransparent += 1;
  }
  const cornerCoordinates = [
    [0, 0],
    [info.width - 1, 0],
    [0, info.height - 1],
    [info.width - 1, info.height - 1],
  ];
  const cornerAlpha = cornerCoordinates.map(([x, y]) => data[(y * info.width + x) * info.channels + alphaOffset]);
  return {
    width: info.width,
    height: info.height,
    channels: info.channels,
    hasAlpha: info.channels === 4,
    transparentPixels: transparent,
    opaquePixels: opaque,
    nonTransparentPixels: nonTransparent,
    transparentRatio: transparent / total,
    opaqueRatio: opaque / total,
    nonTransparentRatio: nonTransparent / total,
    cornerAlpha,
    cornerAlphaMax: Math.max(...cornerAlpha),
  };
}

function assertTransparentContract(stats, label) {
  if (!stats.hasAlpha) {
    throw new Error(`${label} does not decode with an alpha channel`);
  }
  if (stats.cornerAlphaMax !== 0) {
    throw new Error(`${label} corner alpha must be 0, got ${stats.cornerAlpha.join(",")}`);
  }
  if (stats.transparentPixels === 0 || stats.opaquePixels === stats.width * stats.height) {
    throw new Error(`${label} is fully opaque; refusing to bake a background into the hero sequence`);
  }
  if (stats.nonTransparentPixels < 400) {
    throw new Error(`${label} has too few non-transparent product pixels`);
  }
}

const args = parseArgs(process.argv.slice(2));
const toolsDir = resolve(args["tools-dir"] ?? ".scratch/goal9-tools");
const pngDir = resolve(args["png-dir"] ?? ".scratch/assets/ztovalve/hero/v3-transparent-commercial-240/frames");
const avifDir = resolve(args["avif-dir"] ?? "docs/upload/images/zt-hero-fixed-ball-valve");
const outputPath = resolve(args.out ?? "docs/assets/ztovalve/hero/v3-transparent-commercial-240-encode-manifest.json");
const quality = Number(args.quality ?? 58);
const effort = Number(args.effort ?? 4);
const inputIndexBase = Number(args["input-index-base"] ?? 0);
const overwrite = args.overwrite === "true";
const requireFromTools = createRequire(resolve(toolsDir, "package.json"));
const sharp = requireFromTools("sharp");

if (![0, 1].includes(inputIndexBase)) {
  throw new Error("--input-index-base must be 0 or 1");
}

await mkdir(avifDir, { recursive: true });
const existingAvif = (await readdir(avifDir)).filter((name) => /^\d{4}\.avif$/u.test(name)).sort();
if (existingAvif.length > 0 && !overwrite) {
  throw new Error(`AVIF output directory already contains numbered frames: ${avifDir}`);
}
if (overwrite && existingAvif.length > 0 && existingAvif.length !== FRAME_COUNT) {
  throw new Error(`Refusing overwrite because expected 240 existing AVIF frames, found ${existingAvif.length} in ${avifDir}`);
}

const pngFrames = [];
for (let index = 0; index < FRAME_COUNT; index += 1) {
  pngFrames.push(expectedName(index + inputIndexBase, "png"));
}
const actualPngFrames = (await readdir(pngDir)).filter((name) => /^\d{4}\.png$/u.test(name)).sort();
if (actualPngFrames.length !== FRAME_COUNT || actualPngFrames.some((name, index) => name !== pngFrames[index])) {
  throw new Error(
    `Expected contiguous PNG frames ${pngFrames[0]}..${pngFrames[pngFrames.length - 1]} in ${pngDir}; found ${actualPngFrames.length}`,
  );
}

const frames = [];
const combined = createHash("sha256");
const startedAt = performance.now();
let decodedAvifCornerAlphaMax = 0;
let minSourceTransparentRatio = 1;
let maxSourceTransparentRatio = 0;
let minAvifTransparentRatio = 1;
let maxAvifTransparentRatio = 0;

for (let index = 0; index < pngFrames.length; index += 1) {
  const pngName = pngFrames[index];
  const avifName = expectedName(index + 1, "avif");
  const pngPath = resolve(pngDir, pngName);
  const avifPath = resolve(avifDir, avifName);
  const tempAvifPath = `${avifPath}.${process.pid}.${index}.tmp.avif`;
  const sourceAlpha = await alphaStats(sharp, pngPath);
  assertTransparentContract(sourceAlpha, `source PNG ${pngName}`);

  let avifAlpha;
  try {
    await sharp(pngPath, { limitInputPixels: false })
      .avif({
        quality,
        effort,
        chromaSubsampling: "4:2:0",
      })
      .toFile(tempAvifPath);

    avifAlpha = await alphaStats(sharp, tempAvifPath);
    assertTransparentContract(avifAlpha, `decoded AVIF ${avifName}`);
    await rm(avifPath, { force: true });
    await rename(tempAvifPath, avifPath);
  } catch (error) {
    await rm(tempAvifPath, { force: true }).catch(() => {});
    throw error;
  }
  decodedAvifCornerAlphaMax = Math.max(decodedAvifCornerAlphaMax, avifAlpha.cornerAlphaMax);
  minSourceTransparentRatio = Math.min(minSourceTransparentRatio, sourceAlpha.transparentRatio);
  maxSourceTransparentRatio = Math.max(maxSourceTransparentRatio, sourceAlpha.transparentRatio);
  minAvifTransparentRatio = Math.min(minAvifTransparentRatio, avifAlpha.transparentRatio);
  maxAvifTransparentRatio = Math.max(maxAvifTransparentRatio, avifAlpha.transparentRatio);

  const bytes = (await stat(avifPath)).size;
  const digest = await sha256(avifPath);
  combined.update(`${index}:${digest}:${bytes}\n`);
  frames.push({
    frameIndex: index,
    filename: avifName,
    path: `docs/upload/images/zt-hero-fixed-ball-valve/${avifName}`,
    sourcePng: pngPath.replace(/\\/g, "/"),
    width: sourceAlpha.width,
    height: sourceAlpha.height,
    sourceAlpha: {
      cornerAlpha: sourceAlpha.cornerAlpha,
      transparentRatio: Number(sourceAlpha.transparentRatio.toFixed(6)),
      nonTransparentRatio: Number(sourceAlpha.nonTransparentRatio.toFixed(6)),
    },
    decodedAvifAlpha: {
      cornerAlpha: avifAlpha.cornerAlpha,
      transparentRatio: Number(avifAlpha.transparentRatio.toFixed(6)),
      nonTransparentRatio: Number(avifAlpha.nonTransparentRatio.toFixed(6)),
    },
    bytes,
    sha256: digest,
  });
  if ((index + 1) % 30 === 0 || index === pngFrames.length - 1) {
    process.stdout.write(`encoded and alpha-checked ${index + 1}/${pngFrames.length}\n`);
  }
}

const manifest = {
  schemaVersion: 2,
  generatedAt: new Date().toISOString(),
  encoder: {
    tool: "sharp",
    version: sharp.versions.sharp,
    quality,
    effort,
    chromaSubsampling: "4:2:0",
  },
  sourcePngDirectory: pngDir.replace(/\\/g, "/"),
  sourcePngNaming: `${expectedName(inputIndexBase, "png")}..${expectedName(inputIndexBase + FRAME_COUNT - 1, "png")}`,
  avifDirectory: avifDir.replace(/\\/g, "/"),
  avifNaming: "0001.avif..0240.avif",
  frameCount: frames.length,
  dimensions: { width: frames[0].width, height: frames[0].height },
  transparentDelivery: {
    allSourcesHaveAlpha: true,
    sourcePngAlphaNotFullyOpaque: true,
    allDecodedAvifCornersAlphaZero: decodedAvifCornerAlphaMax === 0,
    decodedAvifCornerAlphaMax,
    sourceTransparentRatioRange: [
      Number(minSourceTransparentRatio.toFixed(6)),
      Number(maxSourceTransparentRatio.toFixed(6)),
    ],
    decodedAvifTransparentRatioRange: [
      Number(minAvifTransparentRatio.toFixed(6)),
      Number(maxAvifTransparentRatio.toFixed(6)),
    ],
  },
  totalAvifBytes: frames.reduce((sum, frame) => sum + frame.bytes, 0),
  combinedAvifSha256: combined.digest("hex"),
  encodeDurationMs: Math.round(performance.now() - startedAt),
  frames,
};
await writeFile(outputPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
process.stdout.write(`Encoded and alpha-checked ${frames.length} AVIF frames to ${avifDir}\n`);
