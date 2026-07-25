#!/usr/bin/env node

import { basename } from "node:path";
import { pathToFileURL } from "node:url";

import { fail, parseArgs, printOrWrite } from "./lib/cli.mjs";
import { inspectModel } from "./lib/model-analysis.mjs";

const TAXONOMY = [
  {
    id: "primary-structure",
    label: "Primary structure",
    priority: 0,
    tokens: ["base", "frame", "housing", "bracket", "skeleton", "support", "structure"],
  },
  {
    id: "functional-core",
    label: "Functional core",
    priority: 1,
    tokens: ["core", "motor", "battery", "pump", "valve", "compressor", "power", "circuit", "board"],
  },
  {
    id: "internal-system",
    label: "Internal system",
    priority: 2,
    tokens: ["inner", "internal", "interior", "insert", "module", "mechanism"],
  },
  {
    id: "connection-system",
    label: "Connection system",
    priority: 3,
    tokens: ["fitting", "ferrule", "connector", "coupling", "tube", "pipe", "nut", "bolt", "screw"],
  },
  {
    id: "outer-shell",
    label: "Outer shell",
    priority: 4,
    tokens: ["shell", "body", "panel", "cover", "casing", "enclosure", "skin"],
  },
  {
    id: "access-system",
    label: "Access system",
    priority: 5,
    tokens: ["door", "hatch", "lid", "handle", "hinge", "cap"],
  },
  {
    id: "mobility-system",
    label: "Mobility system",
    priority: 6,
    tokens: ["wheel", "tire", "tyre", "axle", "rotor", "hub", "track"],
  },
  {
    id: "optical-interface",
    label: "Optical or display interface",
    priority: 7,
    tokens: ["glass", "window", "lens", "light", "lamp", "screen", "display"],
  },
];

function words(value) {
  return String(value ?? "")
    .replace(/([a-z])([A-Z])/gu, "$1 $2")
    .toLowerCase()
    .split(/[^a-z0-9\u00c0-\u024f\u0400-\u04ff]+/u)
    .filter(Boolean);
}

function slug(value) {
  const normalized = String(value ?? "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/gu, "-")
    .replace(/^-+|-+$/gu, "");
  return normalized || "assembly";
}

function categoryFor(candidate) {
  const candidateWords = new Set(words(`${candidate.name ?? ""} ${candidate.path}`));
  for (const category of TAXONOMY) {
    if (category.tokens.some((token) => candidateWords.has(token))) {
      return { ...category, inferredFrom: "semantic-token", confidence: 0.72 };
    }
  }
  const parent = candidate.path.split("/").slice(-2, -1)[0] ?? "Unclassified";
  return {
    id: `assembly-${slug(parent)}`,
    label: `${parent} assembly`,
    priority: 8,
    inferredFrom: "parent-hierarchy",
    confidence: candidate.semanticName ? 0.52 : 0.32,
  };
}

function normalizedDirection(center, modelCenter, seed) {
  const vector = center.map((value, axis) => value - modelCenter[axis]);
  const length = Math.hypot(...vector);
  if (length > 1e-6) {
    return vector.map((value) => value / length);
  }
  const axis = Math.abs(seed) % 3;
  const direction = [0, 0, 0];
  direction[axis] = seed % 2 === 0 ? 1 : -1;
  return direction;
}

function stableHash(value) {
  let hash = 2166136261;
  for (const character of String(value)) {
    hash ^= character.codePointAt(0);
    hash = Math.imul(hash, 16777619);
  }
  return hash | 0;
}

function round(value) {
  return Number(value.toFixed(5));
}

function createStages() {
  return [
    {
      id: "intro",
      range: [0, 0.12],
      content: {
        eyebrow: "Product system",
        title: "Introduce the product promise",
        body: "Replace this candidate copy with verified product value.",
        cta: null,
      },
    },
    {
      id: "exploded",
      range: [0.12, 0.3],
      content: {
        eyebrow: "Architecture",
        title: "Reveal the meaningful structure",
        body: "Explain why the visible subsystems matter.",
        cta: null,
      },
    },
    {
      id: "assembly",
      range: [0.3, 0.72],
      content: {
        eyebrow: "Assembly",
        title: "Show how the system becomes one",
        body: "Connect assembly order to engineering value.",
        cta: null,
      },
    },
    {
      id: "reveal",
      range: [0.72, 0.9],
      content: {
        eyebrow: "Complete product",
        title: "Resolve the complete silhouette",
        body: "Move from explanation to product desire.",
        cta: null,
      },
    },
    {
      id: "hero",
      range: [0.9, 1],
      content: {
        eyebrow: "Product family",
        title: "Author the final hero promise",
        body: "Settle the product, message, and action.",
        cta: {
          label: "Explore the product",
          href: "#product",
        },
      },
    },
  ];
}

function groupCandidates(inspection) {
  const grouped = new Map();
  for (const candidate of inspection.partCandidates) {
    const category = categoryFor(candidate);
    const existing = grouped.get(category.id) ?? {
      ...category,
      candidates: [],
    };
    existing.candidates.push(candidate);
    existing.confidence = Math.min(existing.confidence, category.confidence);
    grouped.set(category.id, existing);
  }
  return [...grouped.values()].sort(
    (left, right) =>
      left.priority - right.priority || left.id.localeCompare(right.id),
  );
}

function buildGroups(inspection) {
  const capability = inspection.capability.capability;
  const modelCenter = inspection.bounds?.center ?? [0, 0, 0];
  const diagonal = Math.max(inspection.bounds?.diagonal ?? 1, 1e-3);
  const categories = groupCandidates(inspection);
  if (!categories.length) {
    return [
      {
        id: "whole-product",
        label: "Whole product",
        selector: {
          nodeIndices: [0],
        },
        confidence: 0,
        reviewRequired: true,
        explodedOffset: [0, 0, 0],
        assembleWindow: [0.3, 0.72],
      },
    ];
  }
  return categories.map((category, index) => {
    const centers = category.candidates
      .map((candidate) => candidate.bounds?.center)
      .filter(Boolean);
    const center = centers.length
      ? [0, 1, 2].map(
          (axis) =>
            centers.reduce((sum, value) => sum + value[axis], 0) /
            centers.length,
        )
      : modelCenter;
    const direction = normalizedDirection(
      center,
      modelCenter,
      stableHash(category.id),
    );
    const distance =
      capability === "fused-single-mesh"
        ? 0
        : diagonal * Math.min(0.32, 0.18 + index * 0.012);
    const spread =
      categories.length <= 1 ? 0 : (index / (categories.length - 1)) * 0.25;
    const start = 0.31 + spread;
    const end = Math.min(0.72, start + 0.17);
    const uniqueNames = category.candidates
      .filter((candidate) => candidate.name && candidate.nameIsUnique)
      .map((candidate) => candidate.name);
    const selector = {
      nodeIndices: category.candidates.map((candidate) => candidate.nodeIndex),
      ...(uniqueNames.length === category.candidates.length
        ? { nodeNames: uniqueNames }
        : {}),
    };
    return {
      id: category.id,
      label: category.label,
      selector,
      confidence: round(category.confidence),
      reviewRequired: true,
      explodedOffset: direction.map((value) => round(value * distance)),
      assembleWindow: [round(start), round(end)],
    };
  });
}

export async function generateManifest(modelPath, publicUri) {
  const inspection = await inspectModel(modelPath, {
    publicPath: publicUri ?? basename(modelPath),
  });
  const capability = inspection.capability.capability;
  const center = inspection.bounds?.center ?? [0, 0, 0];
  const diagonal = Math.max(inspection.bounds?.diagonal ?? 1, 1);
  const fused = capability === "fused-single-mesh";
  const mode =
    capability === "structured-named-parts"
      ? "semantic-assembly"
      : capability === "separated-unnamed-parts"
        ? "review-required-assembly"
        : capability === "partially-merged"
          ? "hybrid-reveal"
          : "whole-product";
  const reasons = [
    "Confirm all inferred subsystem groups, assembly windows, and exploded offsets with a product owner.",
    "Replace candidate stage copy, final camera, poster, and CTA with project-approved content.",
    ...inspection.warnings,
  ];
  return {
    $schema: "./product-story.schema.json",
    schemaVersion: 1,
    model: {
      uri: publicUri ?? basename(modelPath),
      format: inspection.source.format,
      bytes: inspection.source.bytes,
      capability,
    },
    story: {
      mode,
      stages: createStages(),
      cameraKeyframes: [
        {
          at: 0,
          position: [
            round(center[0]),
            round(center[1] + diagonal * 0.08),
            round(center[2] + diagonal * 1.35),
          ],
          target: center.map(round),
        },
        {
          at: 1,
          position: [
            round(center[0] + diagonal * 0.62),
            round(center[1] + diagonal * 0.24),
            round(center[2] + diagonal * 1.05),
          ],
          target: center.map(round),
        },
      ],
      modelRotationKeyframes: [
        {
          at: 0,
          rotation: [0, -0.35, 0],
        },
        {
          at: 0.72,
          rotation: [0.04, 0.12, 0],
        },
        {
          at: 1,
          rotation: [0, 0.36, 0],
        },
      ],
    },
    groups: buildGroups(inspection),
    fallback: {
      poster: null,
      reducedMotion: "hero",
      fusedMeshStrategy: fused
        ? "whole-product"
        : capability === "partially-merged"
          ? "hybrid-reveal"
          : "not-required",
    },
    review: {
      required: true,
      reasons,
    },
  };
}

async function main() {
  const args = parseArgs(process.argv.slice(2), {
    model: "required",
    "public-uri": "optional",
    out: "optional",
  });
  const manifest = await generateManifest(args.model, args["public-uri"]);
  await printOrWrite(manifest, args.out);
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? "").href) {
  main().catch(fail);
}
