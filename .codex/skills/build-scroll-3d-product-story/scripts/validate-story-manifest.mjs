#!/usr/bin/env node

import { readFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";

import { fail, parseArgs } from "./lib/cli.mjs";

const CAPABILITIES = new Set([
  "structured-named-parts",
  "separated-unnamed-parts",
  "partially-merged",
  "fused-single-mesh",
]);
const MODES = new Set([
  "semantic-assembly",
  "review-required-assembly",
  "hybrid-reveal",
  "whole-product",
  "cinematic-scroll",
]);
const SHOT_COUNT = 5;
const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/u;

function isFiniteVector(value, length) {
  return (
    Array.isArray(value) &&
    value.length === length &&
    value.every(Number.isFinite)
  );
}

function isRange(value) {
  return (
    isFiniteVector(value, 2) &&
    value[0] >= 0 &&
    value[1] <= 1 &&
    value[0] < value[1]
  );
}

export function validateManifest(manifest) {
  const errors = [];
  if (!manifest || typeof manifest !== "object" || Array.isArray(manifest)) {
    return ["manifest must be a JSON object"];
  }
  if (manifest.schemaVersion !== 2) {
    errors.push("schemaVersion must equal 2");
  }
  const creative = manifest.creativeDevelopment;
  for (const field of [
    "planId",
    "selectedRouteId",
    "animaticUri",
    "approvalId",
    "evidenceRef",
  ]) {
    if (typeof creative?.[field] !== "string" || !creative[field]) {
      errors.push(`creativeDevelopment.${field} must be a non-empty string`);
    }
  }
  for (const field of ["planId", "selectedRouteId"]) {
    if (
      typeof creative?.[field] === "string" &&
      !SLUG.test(creative[field])
    ) {
      errors.push(`creativeDevelopment.${field} must be kebab-case`);
    }
  }
  if (
    !manifest.model ||
    typeof manifest.model.uri !== "string" ||
    !manifest.model.uri
  ) {
    errors.push("model.uri must be a non-empty string");
  }
  if (!["glb", "gltf"].includes(manifest.model?.format)) {
    errors.push("model.format must be glb or gltf");
  }
  if (!Number.isInteger(manifest.model?.bytes) || manifest.model.bytes < 0) {
    errors.push("model.bytes must be a non-negative integer");
  }
  if (!CAPABILITIES.has(manifest.model?.capability)) {
    errors.push("model.capability is invalid");
  }
  if (!MODES.has(manifest.story?.mode)) {
    errors.push("story.mode is invalid");
  }

  const stages = manifest.story?.stages;
  if (!Array.isArray(stages) || stages.length !== SHOT_COUNT) {
    errors.push("story.stages must contain exactly five approved shots");
  } else {
    const stageIds = new Set();
    stages.forEach((stage, index) => {
      if (!SLUG.test(stage?.id ?? "")) {
        errors.push(`story.stages[${index}].id must be kebab-case`);
      } else if (stageIds.has(stage.id)) {
        errors.push(`duplicate story stage id: ${stage.id}`);
      }
      stageIds.add(stage?.id);
      if (!isRange(stage?.range)) {
        errors.push(`story.stages[${index}].range is invalid`);
      }
      if (
        index > 0 &&
        isRange(stage?.range) &&
        isRange(stages[index - 1]?.range) &&
        Math.abs(stage.range[0] - stages[index - 1].range[1]) > 1e-9
      ) {
        errors.push("story stage ranges must be continuous");
      }
      for (const field of ["eyebrow", "title", "body"]) {
        if (typeof stage?.content?.[field] !== "string") {
          errors.push(`story.stages[${index}].content.${field} must be a string`);
        }
      }
    });
    if (
      isRange(stages[0]?.range) &&
      isRange(stages.at(-1)?.range) &&
      (stages[0].range[0] !== 0 || stages.at(-1).range[1] !== 1)
    ) {
      errors.push("story stage ranges must cover [0, 1]");
    }
  }

  if (manifest.story?.mode === "cinematic-scroll") {
    if (typeof manifest.story.cameraPathUri !== "string" || !manifest.story.cameraPathUri) {
      errors.push("story.cameraPathUri is required for cinematic-scroll");
    }
    const transform = manifest.story.canonicalModelTransform;
    for (const field of ["position", "rotation", "scale"]) {
      if (!isFiniteVector(transform?.[field], 3)) {
        errors.push(`story.canonicalModelTransform.${field} must be a vec3`);
      }
    }
    if (
      !Array.isArray(manifest.story.opacityGroupIds) ||
      !manifest.story.opacityGroupIds.every((id) => SLUG.test(id))
    ) {
      errors.push("story.opacityGroupIds must contain kebab-case group IDs");
    }
  } else for (const key of ["cameraKeyframes", "modelRotationKeyframes"]) {
    const keyframes = manifest.story?.[key];
    if (!Array.isArray(keyframes) || keyframes.length < 2) {
      errors.push(`story.${key} must contain at least two keyframes`);
      continue;
    }
    let previous = -1;
    keyframes.forEach((keyframe, index) => {
      if (
        !Number.isFinite(keyframe?.at) ||
        keyframe.at < 0 ||
        keyframe.at > 1 ||
        keyframe.at < previous
      ) {
        errors.push(`story.${key}[${index}].at is invalid or unordered`);
      }
      previous = keyframe?.at ?? previous;
      if (key === "cameraKeyframes") {
        if (
          !isFiniteVector(keyframe?.position, 3) ||
          !isFiniteVector(keyframe?.target, 3)
        ) {
          errors.push(`story.${key}[${index}] requires position and target vec3`);
        }
      } else if (!isFiniteVector(keyframe?.rotation, 3)) {
        errors.push(`story.${key}[${index}].rotation must be a vec3`);
      }
    });
  }

  if (!Array.isArray(manifest.groups) || manifest.groups.length < 1) {
    errors.push("groups must contain at least one group");
  } else {
    const ids = new Set();
    const selectedNodeIndices = new Set();
    manifest.groups.forEach((group, index) => {
      if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/u.test(group?.id ?? "")) {
        errors.push(`groups[${index}].id is invalid`);
      } else if (ids.has(group.id)) {
        errors.push(`duplicate group id: ${group.id}`);
      }
      ids.add(group?.id);
      if (typeof group?.label !== "string" || !group.label) {
        errors.push(`groups[${index}].label is required`);
      }
      const nodeNames = group?.selector?.nodeNames;
      const nodeIndices = group?.selector?.nodeIndices;
      const validNames =
        Array.isArray(nodeNames) &&
        nodeNames.length > 0 &&
        nodeNames.every((name) => typeof name === "string" && name);
      const validIndices =
        Array.isArray(nodeIndices) &&
        nodeIndices.length > 0 &&
        nodeIndices.every(
          (nodeIndex) => Number.isInteger(nodeIndex) && nodeIndex >= 0,
        );
      if (!validNames && !validIndices) {
        errors.push(
          `groups[${index}].selector requires nodeNames or nodeIndices`,
        );
      }
      if (validIndices) {
        for (const nodeIndex of nodeIndices) {
          if (selectedNodeIndices.has(nodeIndex)) {
            errors.push(`node index ${nodeIndex} belongs to multiple groups`);
          }
          selectedNodeIndices.add(nodeIndex);
        }
      }
      if (
        !Number.isFinite(group?.confidence) ||
        group.confidence < 0 ||
        group.confidence > 1
      ) {
        errors.push(`groups[${index}].confidence must be in [0, 1]`);
      }
      if (typeof group?.reviewRequired !== "boolean") {
        errors.push(`groups[${index}].reviewRequired must be boolean`);
      }
      if (!isFiniteVector(group?.explodedOffset, 3)) {
        errors.push(`groups[${index}].explodedOffset must be a vec3`);
      }
      if (!isRange(group?.assembleWindow)) {
        errors.push(`groups[${index}].assembleWindow is invalid`);
      }
    });
  }

  if (manifest.fallback?.reducedMotion !== "hero") {
    errors.push("fallback.reducedMotion must be hero");
  }
  if (typeof manifest.review?.required !== "boolean") {
    errors.push("review.required must be boolean");
  }
  if (!Array.isArray(manifest.review?.reasons)) {
    errors.push("review.reasons must be an array");
  }
  if (
    manifest.model?.capability === "fused-single-mesh" &&
    manifest.fallback?.fusedMeshStrategy !== "whole-product"
  ) {
    errors.push("fused models must use the whole-product fallback strategy");
  }
  return errors;
}

async function main() {
  const args = parseArgs(process.argv.slice(2), {
    manifest: "required",
  });
  const manifest = JSON.parse(await readFile(args.manifest, "utf8"));
  const errors = validateManifest(manifest);
  if (errors.length) {
    for (const error of errors) {
      process.stderr.write(`- ${error}\n`);
    }
    throw new Error(`Manifest validation failed with ${errors.length} error(s)`);
  }
  process.stdout.write("PASS: product story manifest is valid\n");
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? "").href) {
  main().catch(fail);
}
