#!/usr/bin/env node

import { readdir, stat } from "node:fs/promises";
import { extname, relative, resolve } from "node:path";

import { fail, parseArgs, printOrWrite } from "./lib/cli.mjs";

const FRAME_EXTENSIONS = new Set([".avif", ".webp", ".png", ".jpg", ".jpeg"]);

async function listFiles(directory) {
  const root = resolve(directory);
  const output = [];
  async function visit(current) {
    for (const entry of await readdir(current, { withFileTypes: true })) {
      const path = resolve(current, entry.name);
      if (entry.isDirectory()) {
        await visit(path);
      } else if (entry.isFile()) {
        const info = await stat(path);
        output.push({
          path: relative(root, path).replace(/\\/gu, "/"),
          bytes: info.size,
        });
      }
    }
  }
  await visit(root);
  return output.sort((left, right) => left.path.localeCompare(right.path));
}

function summary(files) {
  const bytes = files.reduce((sum, file) => sum + file.bytes, 0);
  return {
    requests: files.length,
    bytes,
    mebibytes: Number((bytes / 1024 / 1024).toFixed(3)),
  };
}

async function main() {
  const args = parseArgs(process.argv.slice(2), {
    "runtime-dir": "required",
    "frames-dir": "required",
    out: "optional",
  });
  const runtimeFiles = await listFiles(args["runtime-dir"]);
  const frameFiles = (await listFiles(args["frames-dir"])).filter((file) =>
    FRAME_EXTENSIONS.has(extname(file.path).toLowerCase()),
  );
  if (!frameFiles.length) {
    throw new Error("The frame directory does not contain supported image frames");
  }
  const realtime3d = summary(runtimeFiles);
  const frameSequence = summary(frameFiles);
  const result = {
    schemaVersion: 1,
    comparison: {
      realtime3d,
      frameSequence: {
        ...frameSequence,
        frameCount: frameFiles.length,
      },
      delta: {
        bytes: realtime3d.bytes - frameSequence.bytes,
        requests: realtime3d.requests - frameSequence.requests,
        realtimeToFramesByteRatio: Number(
          (realtime3d.bytes / frameSequence.bytes).toFixed(4),
        ),
      },
    },
    releaseAssumptions: {
      fixedWeakNetworkGate: false,
      compareOnSameDeviceBrowserViewportCache: true,
    },
    browserMetricsToCollect: [
      "firstUsableProductFrameMs",
      "frameTimeP50Ms",
      "frameTimeP95Ms",
      "framesOver16_7Ms",
      "framesOver33_3Ms",
      "longAnimationFrames",
      "mainThreadTimeMs",
      "peakMemoryBytes",
      "idleFramesAfterSettled",
    ],
    caveat:
      "File bytes and request counts do not prove runtime frame pacing or visual fidelity.",
  };
  await printOrWrite(result, args.out);
}

main().catch(fail);
