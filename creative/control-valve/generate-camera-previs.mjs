#!/usr/bin/env node

import { readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const sourcePath = resolve(here, "camera-path.json");
const outputPath = resolve(here, "camera-previs.json");
const runtimePath = resolve(here, "../../docs/control-valve/camera-path.json");
const source = JSON.parse(await readFile(sourcePath, "utf8"));

const smooth = (value) => value * value * (3 - 2 * value);
const mix = (a, b, t) => a + (b - a) * t;
const mixVector = (a, b, t) => a.map((value, index) => mix(value, b[index], t));
const round = (value) => Number(value.toFixed(5));
const roundVector = (values) => values.map(round);

function shotAt(frame) {
  return source.shots.find(
    (shot) => frame >= shot.startFrame && frame <= shot.endFrame,
  );
}

function sample(frame) {
  let left = source.keyframes[0];
  let right = source.keyframes.at(-1);
  for (let index = 1; index < source.keyframes.length; index += 1) {
    if (frame <= source.keyframes[index].frame) {
      left = source.keyframes[index - 1];
      right = source.keyframes[index];
      break;
    }
  }
  const span = Math.max(1, right.frame - left.frame);
  const t = smooth((frame - left.frame) / span);
  const shot = shotAt(frame);
  return {
    frame,
    timeSeconds: round(frame / source.fps),
    progress: round(frame / (source.totalFrames - 1)),
    shotId: shot.id,
    camera: {
      position: roundVector(mixVector(left.position, right.position, t)),
      target: roundVector(mixVector(left.target, right.target, t)),
      rollDegrees: round(mix(left.roll, right.roll, t)),
      fovDegrees: round(mix(left.fov, right.fov, t)),
      focusDistance: round(mix(left.focusDistance, right.focusDistance, t))
    },
    product: {
      explode: round(mix(left.explode, right.explode, t)),
      bodyOpacity: round(mix(left.bodyOpacity, right.bodyOpacity, t)),
      stemStroke: round(mix(left.stemStroke, right.stemStroke, t)),
      cascadeStage: round(mix(left.cascadeStage, right.cascadeStage, t))
    },
    light: {
      key: round(mix(left.keyLight, right.keyLight, t)),
      rim: round(mix(left.rimLight, right.rimLight, t))
    },
    transition: {
      occlusion: round(mix(left.occlusion, right.occlusion, t))
    }
  };
}

const frames = Array.from(
  { length: source.totalFrames },
  (_, frame) => sample(frame),
);
const artifact = {
  schemaVersion: 1,
  title: source.title,
  fps: source.fps,
  totalFrames: source.totalFrames,
  durationSeconds: source.totalFrames / source.fps,
  maxAbsRollDegrees: source.maxAbsRollDegrees,
  stableHeroHold: [source.stableHeroFromFrame, source.totalFrames - 1],
  hiddenCut: {
    fromFrame: null,
    toFrame: null,
    motivation:
      "None. The camera remains outside the product and all five shots connect through visible continuous motion."
  },
  continuityPath: [
    "complete product authority",
    "slow external axial observation",
    "shell transparency reveals the cascade in context",
    "modest six-system separation with a fixed horizon",
    "controlled return",
    "stable three-quarter hero"
  ],
  shots: source.shots,
  frames
};

await writeFile(
  outputPath,
  `${JSON.stringify(artifact, null, 2)}\n`,
  "utf8",
);
await writeFile(
  runtimePath,
  `${JSON.stringify(source, null, 2)}\n`,
  "utf8",
);
process.stdout.write(
  `Generated ${frames.length} deterministic camera states at ${outputPath} and synchronized ${runtimePath}\n`,
);
