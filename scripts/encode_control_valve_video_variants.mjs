#!/usr/bin/env node

import { mkdir, readFile, stat, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { spawn } from "node:child_process";
import { dirname, resolve } from "node:path";

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

function run(command, args) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, {
      stdio: ["ignore", "pipe", "pipe"],
      windowsHide: true,
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => {
      stdout += chunk;
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk;
    });
    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0) resolvePromise({ stdout, stderr });
      else reject(new Error(`${command} exited ${code}\n${stderr}`));
    });
  });
}

async function sha256(path) {
  const bytes = await readFile(path);
  return createHash("sha256").update(bytes).digest("hex");
}

const args = parseArgs(process.argv.slice(2));
const frameDirectory = resolve(args["frame-dir"]);
const outputDirectory = resolve(
  args["output-dir"] ?? "docs/control-valve-video/assets",
);
const manifestPath = resolve(
  args.out ?? "creative/control-valve-video/encode-manifest.json",
);
const sourceManifestPath = resolve(
  args["render-manifest"] ??
    "creative/control-valve-video/render-manifest.json",
);
const ffmpeg = args.ffmpeg ?? "ffmpeg";
const ffprobe = args.ffprobe ?? "ffprobe";
const variants = [3, 6, 10];
const sourceManifest = JSON.parse(await readFile(sourceManifestPath, "utf8"));
const fps = sourceManifest.renderProfile?.fps;
const frameCount = sourceManifest.renderProfile?.frameCount;

if (!args["frame-dir"]) {
  throw new Error("--frame-dir is required");
}

await mkdir(outputDirectory, { recursive: true });
await mkdir(dirname(manifestPath), { recursive: true });
if (!Number.isInteger(frameCount) || frameCount < 2 || !Number.isFinite(fps)) {
  throw new Error("Render manifest must declare a valid frame count and fps");
}

const results = [];
for (const gop of variants) {
  const filename = `control-valve-gop${gop}.mp4`;
  const outputPath = resolve(outputDirectory, filename);
  const encodeArgs = [
    "-hide_banner",
    "-loglevel",
    "error",
    "-y",
    "-framerate",
    String(fps),
    "-start_number",
    "0",
    "-i",
    resolve(frameDirectory, "frame%04d.png"),
    "-frames:v",
    String(frameCount),
    "-an",
    "-c:v",
    "libx264",
    "-preset",
    "medium",
    "-crf",
    "21",
    "-profile:v",
    "high",
    "-level",
    "4.1",
    "-pix_fmt",
    "yuv420p",
    "-g",
    String(gop),
    "-keyint_min",
    String(gop),
    "-sc_threshold",
    "0",
    "-bf",
    "0",
    "-movflags",
    "+faststart",
    outputPath,
  ];
  process.stdout.write(`encoding GOP ${gop}\n`);
  await run(ffmpeg, encodeArgs);

  const streamProbe = await run(ffprobe, [
    "-v",
    "error",
    "-select_streams",
    "v:0",
    "-count_frames",
    "-show_entries",
    "stream=codec_name,codec_type,width,height,avg_frame_rate,duration,nb_read_frames",
    "-of",
    "json",
    outputPath,
  ]);
  const frameProbe = await run(ffprobe, [
    "-v",
    "error",
    "-select_streams",
    "v:0",
    "-show_frames",
    "-show_entries",
    "frame=key_frame",
    "-of",
    "csv=p=0",
    outputPath,
  ]);
  const audioProbe = await run(ffprobe, [
    "-v",
    "error",
    "-select_streams",
    "a",
    "-show_entries",
    "stream=index",
    "-of",
    "csv=p=0",
    outputPath,
  ]);
  const stream = JSON.parse(streamProbe.stdout).streams?.[0];
  const keyframeCount = frameProbe.stdout
    .split(/\r?\n/u)
    .filter((value) => value.trim().startsWith("1")).length;
  results.push({
    id: `gop${gop}`,
    gop,
    path: `docs/control-valve-video/assets/${filename}`,
    bytes: (await stat(outputPath)).size,
    sha256: await sha256(outputPath),
    codec: stream?.codec_name,
    codecType: stream?.codec_type,
    width: Number(stream?.width),
    height: Number(stream?.height),
    frameRate: stream?.avg_frame_rate,
    durationSeconds: Number(stream?.duration),
    frameCount: Number(stream?.nb_read_frames),
    keyframeCount,
    audioStreamCount: audioProbe.stdout.trim()
      ? audioProbe.stdout.trim().split(/\r?\n/u).length
      : 0,
  });
}

const manifest = {
  schemaVersion: 1,
  generatedAt: new Date().toISOString(),
  sourceRenderManifest:
    "creative/control-valve-video/render-manifest.json",
  sourceCombinedFrameSha256: sourceManifest.combinedFrameSha256,
  independentVariable: "GOP/keyframe interval only",
  matchedEncodePolicy: {
    container: "MP4",
    codec: "H.264/libx264",
    width: 1280,
    height: 800,
    frameRate: 30,
      frameCount,
      durationSeconds: frameCount / fps,
    preset: "medium",
    crf: 21,
    profile: "high",
    level: "4.1",
    pixelFormat: "yuv420p",
    bFrames: 0,
    sceneCutDetection: false,
    fastStart: true,
    audio: false,
  },
  variants: results,
};
await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
process.stdout.write(`${JSON.stringify(manifest, null, 2)}\n`);
