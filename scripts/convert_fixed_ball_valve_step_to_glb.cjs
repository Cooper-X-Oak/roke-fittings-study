#!/usr/bin/env node

const { createHash } = require("node:crypto");
const { readFileSync, statSync, writeFileSync, mkdirSync } = require("node:fs");
const { dirname, resolve } = require("node:path");
const { createRequire } = require("node:module");

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

function sha256(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

function flattenNumbers(value) {
  if (ArrayBuffer.isView(value)) return Array.from(value);
  if (!Array.isArray(value)) return [];
  const result = [];
  const visit = (item) => {
    if (Array.isArray(item) || ArrayBuffer.isView(item)) {
      for (const child of item) visit(child);
    } else {
      result.push(Number(item));
    }
  };
  visit(value);
  return result;
}

function typedIndexArray(indices) {
  const max = indices.reduce((current, value) => Math.max(current, value), 0);
  return max > 65535 ? new Uint32Array(indices) : new Uint16Array(indices);
}

function safeName(value, fallback) {
  const text = typeof value === "string" ? value.trim() : "";
  return text || fallback;
}

function sanitizeMaterialKey(color) {
  return color.map((value) => Math.round(value * 1000)).join("-");
}

function walkOcctTree(node, meshes, makeNode, parentPath = []) {
  const name = safeName(node?.name, parentPath.length ? "Component" : "Fixed Ball Valve");
  const currentPath = [...parentPath, name];
  const gltfNode = makeNode(name, currentPath.join(" / "), node?.meshes ?? []);
  for (const child of node?.children ?? []) {
    gltfNode.addChild(walkOcctTree(child, meshes, makeNode, currentPath));
  }
  return gltfNode;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const toolsDir = resolve(args["tools-dir"] ?? ".scratch/goal9-tools");
  const stepPath = resolve(args.step);
  const outPath = resolve(args.out);
  const reportPath = resolve(args.report ?? "asset/derived/fixed-ball-valve/glb-conversion-report.json");
  const linearDeflection = Number(args["linear-deflection"] ?? 0.0009);
  const angularDeflection = Number(args["angular-deflection"] ?? 0.35);
  const scale = Number(args.scale ?? 0.001);
  const requireFromTools = createRequire(resolve(toolsDir, "package.json"));
  const occtImport = requireFromTools("occt-import-js");
  const gltfTransform = requireFromTools("@gltf-transform/core");
  const {
    Accessor,
    Document,
    NodeIO,
    Primitive,
  } = gltfTransform;

  const occt = await occtImport();
  const sourceBytes = readFileSync(stepPath);
  const result = occt.ReadStepFile(sourceBytes, {
    linearUnit: "millimeter",
    linearDeflectionType: "bounding_box_ratio",
    linearDeflection,
    angularDeflection,
  });
  if (!result?.success) {
    throw new Error(`OpenCascade STEP import failed: ${result?.error ?? "unknown error"}`);
  }

  const document = new Document();
  const buffer = document.createBuffer("fixed-ball-valve-buffer");
  const scene = document.createScene("fixed-ball-valve-scene");
  const materialCache = new Map();
  const meshes = result.meshes ?? [];
  const meshBearingNodes = [];
  const createdMeshes = [];
  const bounds = {
    min: [Number.POSITIVE_INFINITY, Number.POSITIVE_INFINITY, Number.POSITIVE_INFINITY],
    max: [Number.NEGATIVE_INFINITY, Number.NEGATIVE_INFINITY, Number.NEGATIVE_INFINITY],
  };

  function materialFor(color) {
    const normalized = Array.isArray(color) && color.length >= 3 ? color.slice(0, 3) : [0.66, 0.66, 0.64];
    const key = sanitizeMaterialKey(normalized);
    if (!materialCache.has(key)) {
      const name = `mat-${key}`;
      const material = document
        .createMaterial(name)
        .setBaseColorFactor([normalized[0], normalized[1], normalized[2], 1])
        .setMetallicFactor(0.72)
        .setRoughnessFactor(0.32);
      materialCache.set(key, material);
    }
    return materialCache.get(key);
  }

  function createPrimitiveFromOcctMesh(mesh, meshIndex) {
    const positions = flattenNumbers(mesh?.attributes?.position?.array).map((value) => value * scale);
    const normals = flattenNumbers(mesh?.attributes?.normal?.array);
    const indices = flattenNumbers(mesh?.index?.array).map((value) => Math.trunc(value));
    if (positions.length < 9 || indices.length < 3) {
      return null;
    }
    for (let index = 0; index < positions.length; index += 3) {
      for (let axis = 0; axis < 3; axis += 1) {
        const value = positions[index + axis];
        bounds.min[axis] = Math.min(bounds.min[axis], value);
        bounds.max[axis] = Math.max(bounds.max[axis], value);
      }
    }
    const primitive = document
      .createPrimitive(`primitive-${meshIndex}`)
      .setMode(Primitive.Mode.TRIANGLES)
      .setAttribute(
        "POSITION",
        document
          .createAccessor(`position-${meshIndex}`)
          .setType(Accessor.Type.VEC3)
          .setArray(new Float32Array(positions))
          .setBuffer(buffer),
      )
      .setIndices(
        document
          .createAccessor(`indices-${meshIndex}`)
          .setType(Accessor.Type.SCALAR)
          .setArray(typedIndexArray(indices))
          .setBuffer(buffer),
      )
      .setMaterial(materialFor(mesh?.color));
    if (normals.length === positions.length) {
      primitive.setAttribute(
        "NORMAL",
        document
          .createAccessor(`normal-${meshIndex}`)
          .setType(Accessor.Type.VEC3)
          .setArray(new Float32Array(normals))
          .setBuffer(buffer),
      );
    }
    return primitive;
  }

  const primitiveCache = new Map();
  function makeNode(name, path, meshIndices) {
    const node = document.createNode(name);
    if (meshIndices.length) {
      const gltfMesh = document.createMesh(name);
      for (const meshIndex of meshIndices) {
        if (!primitiveCache.has(meshIndex)) {
          primitiveCache.set(meshIndex, createPrimitiveFromOcctMesh(meshes[meshIndex], meshIndex));
        }
        const primitive = primitiveCache.get(meshIndex);
        if (primitive) gltfMesh.addPrimitive(primitive);
      }
      if (gltfMesh.listPrimitives().length) {
        node.setMesh(gltfMesh);
        meshBearingNodes.push({ name, path, meshIndices });
        createdMeshes.push(gltfMesh);
      } else {
        gltfMesh.dispose();
      }
    }
    return node;
  }

  const rootNode = walkOcctTree(result.root, meshes, makeNode);
  scene.addChild(rootNode);
  document.getRoot().setDefaultScene(scene);

  mkdirSync(dirname(outPath), { recursive: true });
  const io = new NodeIO();
  await io.write(outPath, document);

  const finiteBounds = bounds.min.every(Number.isFinite) && bounds.max.every(Number.isFinite);
  const report = {
    schemaVersion: 1,
    generatedAt: new Date().toISOString(),
    source: {
      path: stepPath.replace(/\\/g, "/"),
      bytes: statSync(stepPath).size,
      sha256: sha256(stepPath),
      unit: "millimeter",
    },
    conversion: {
      engine: "occt-import-js / OpenCascade WASM",
      outputScale: scale,
      outputUnit: "meter",
      linearDeflectionType: "bounding_box_ratio",
      linearDeflection,
      angularDeflection,
      meshCountFromOcct: meshes.length,
      meshBearingNodeCount: meshBearingNodes.length,
      materialCount: materialCache.size,
    },
    output: {
      path: outPath.replace(/\\/g, "/"),
      bytes: statSync(outPath).size,
      sha256: sha256(outPath),
      format: "glTF 2.0 binary GLB",
    },
    boundsMeters: finiteBounds
      ? {
          min: bounds.min.map((value) => Number(value.toFixed(6))),
          max: bounds.max.map((value) => Number(value.toFixed(6))),
          size: bounds.max.map((value, index) => Number((value - bounds.min[index]).toFixed(6))),
        }
      : null,
    partTree: {
      rootName: safeName(result.root?.name, "Fixed Ball Valve"),
      meshBearingNodes,
    },
    issues: [
      "GLB node hierarchy is converted from STEP import metadata and remains subject to engineering review.",
      "Materials use source colors with a commercial metallic treatment; exact alloy/coating claims require client evidence.",
      "Output geometry is scaled from millimeters to meters for web camera fitting.",
    ],
  };
  mkdirSync(dirname(reportPath), { recursive: true });
  writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  process.stdout.write(`${JSON.stringify(report.output, null, 2)}\n`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
