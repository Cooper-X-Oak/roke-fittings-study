#!/usr/bin/env node

import assert from "node:assert/strict";

import {
  assemblyAmount,
  sampleGroupPosition,
  sampleVectorKeyframes,
  stageAtProgress,
} from "../assets/threejs-scroll-story/story-math.mjs";

const base = [1, 2, 3];
const group = {
  explodedOffset: [4, -2, 1],
  assembleWindow: [0.3, 0.7],
};

const startA = sampleGroupPosition(base, group, 0);
const assembled = sampleGroupPosition(base, group, 1);
const startB = sampleGroupPosition(base, group, 0);

assert.deepEqual(startA, [5, 0, 4]);
assert.deepEqual(assembled, base);
assert.deepEqual(startB, startA);
assert.deepEqual(base, [1, 2, 3], "sampling must not mutate base transforms");
assert.equal(assemblyAmount(group.assembleWindow, 0.3), 1);
assert.equal(assemblyAmount(group.assembleWindow, 0.7), 0);

const keys = [
  { at: 0, position: [0, 0, 0] },
  { at: 1, position: [10, 20, 30] },
];
assert.deepEqual(sampleVectorKeyframes(keys, "position", 0), [0, 0, 0]);
assert.deepEqual(sampleVectorKeyframes(keys, "position", 1), [10, 20, 30]);
assert.deepEqual(
  sampleVectorKeyframes(keys, "position", 0.5),
  sampleVectorKeyframes(keys, "position", 0.5),
);

const stages = [
  { id: "first", range: [0, 0.5] },
  { id: "second", range: [0.5, 1] },
];
assert.equal(stageAtProgress(stages, 0).id, "first");
assert.equal(stageAtProgress(stages, 0.5).id, "second");
assert.equal(stageAtProgress(stages, 1).id, "second");

process.stdout.write(
  "PASS: story transforms are deterministic, reversible, and base-relative\n",
);
