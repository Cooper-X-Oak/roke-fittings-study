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
const distance = (a, b) =>
  Math.sqrt(a.reduce((sum, value, index) => sum + (value - b[index]) ** 2, 0));

function shotAt(frame) {
  return (
    source.shots.find(
      (shot) => frame >= shot.startFrame && frame <= shot.endFrame,
    ) ?? source.shots.at(-1)
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
  const position = mixVector(left.position, right.position, t);
  const target = mixVector(left.target, right.target, t);
  const shot = shotAt(frame);
  return {
    frame,
    timeSeconds: round(frame / source.fps),
    progress: round(frame / (source.totalFrames - 1)),
    shotId: shot.id,
    camera: {
      position: roundVector(position),
      target: roundVector(target),
      rollDegrees: round(mix(left.roll, right.roll, t)),
      fovDegrees: round(mix(left.fov, right.fov, t)),
      focusDistance: round(distance(position, target)),
    },
    product: {
      trimAssembly: roundVector(
        mixVector(left.trimAssembly, right.trimAssembly, t),
      ),
      stemAssembly: round(mix(left.stemAssembly, right.stemAssembly, t)),
      bodyClosure: round(mix(left.bodyClosure, right.bodyClosure, t)),
      bodyOpacity: round(mix(left.bodyOpacity, right.bodyOpacity, t)),
      actuatorAssembly: round(
        mix(left.actuatorAssembly, right.actuatorAssembly, t),
      ),
      detailAssembly: round(
        mix(left.detailAssembly, right.detailAssembly, t),
      ),
      productYawDegrees: round(
        mix(left.productYawDegrees, right.productYawDegrees, t),
      ),
      coreEmphasis: round(
        mix(left.coreEmphasis, right.coreEmphasis, t),
      ),
    },
    light: {
      key: round(mix(left.keyLight, right.keyLight, t)),
      rim: round(mix(left.rimLight, right.rimLight, t)),
      core: round(mix(left.coreLight, right.coreLight, t)),
    },
    transition: {
      occlusion: round(mix(left.occlusion, right.occlusion, t)),
    },
  };
}

const frames = Array.from(
  { length: source.totalFrames },
  (_, frame) => sample(frame),
);
const artifact = {
  schemaVersion: 2,
  title: source.title,
  fps: source.fps,
  totalFrames: source.totalFrames,
  durationSeconds: source.durationSeconds,
  maxAbsRollDegrees: source.maxAbsRollDegrees,
  mechanicalAxisWorld: source.mechanicalAxisWorld,
  stableHeroHold: [source.stableHeroFromFrame, source.totalFrames - 1],
  hiddenCut: {
    fromFrame: null,
    toFrame: null,
    motivation:
      "None. All five beats share one world, one visible mechanical axis and continuous product-state handoffs.",
  },
  continuityPath: [
    "four actual CASCADE_TRIM geometry islands suspended on the central axis",
    "four islands and grouped stem nest in staged order",
    "body closure and opacity establish the core location before enclosure",
    "actuator group completes the vertical silhouette",
    "one bounded camera arc that rises through actuator seating",
    "continuous off-axis final pass with no terminal hero hold",
  ],
  shots: source.shots,
  frames,
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
  `Generated ${frames.length} deterministic grey-animatic states at ${outputPath} and synchronized ${runtimePath}\n`,
);
