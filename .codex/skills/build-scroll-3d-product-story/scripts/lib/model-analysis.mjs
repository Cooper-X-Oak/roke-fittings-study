import { readFile, stat } from "node:fs/promises";
import { extname, resolve } from "node:path";

const GLB_MAGIC = 0x46546c67;
const JSON_CHUNK = 0x4e4f534a;
const TRIANGLES = 4;
const TRIANGLE_STRIP = 5;
const TRIANGLE_FAN = 6;

function parseGlb(buffer) {
  if (buffer.length < 20 || buffer.readUInt32LE(0) !== GLB_MAGIC) {
    throw new Error("Invalid GLB header");
  }
  const version = buffer.readUInt32LE(4);
  const declaredLength = buffer.readUInt32LE(8);
  if (version !== 2) {
    throw new Error(`Unsupported GLB version: ${version}`);
  }
  if (declaredLength > buffer.length) {
    throw new Error(
      `GLB declares ${declaredLength} bytes but only ${buffer.length} are available`,
    );
  }
  let offset = 12;
  while (offset + 8 <= declaredLength) {
    const chunkLength = buffer.readUInt32LE(offset);
    const chunkType = buffer.readUInt32LE(offset + 4);
    const chunkStart = offset + 8;
    const chunkEnd = chunkStart + chunkLength;
    if (chunkEnd > declaredLength) {
      throw new Error("GLB chunk exceeds declared file length");
    }
    if (chunkType === JSON_CHUNK) {
      const jsonText = buffer
        .subarray(chunkStart, chunkEnd)
        .toString("utf8")
        .replace(/[\u0000\u0020]+$/u, "");
      return JSON.parse(jsonText);
    }
    offset = chunkEnd;
  }
  throw new Error("GLB does not contain a JSON chunk");
}

export async function loadModelDocument(modelPath) {
  const absolutePath = resolve(modelPath);
  const extension = extname(absolutePath).toLowerCase();
  const info = await stat(absolutePath);
  if (extension === ".glb") {
    const buffer = await readFile(absolutePath);
    return {
      document: parseGlb(buffer),
      format: "glb",
      bytes: info.size,
      absolutePath,
    };
  }
  if (extension === ".gltf") {
    const text = await readFile(absolutePath, "utf8");
    return {
      document: JSON.parse(text),
      format: "gltf",
      bytes: info.size,
      absolutePath,
    };
  }
  throw new Error(`Expected a .glb or .gltf file, received: ${modelPath}`);
}

function identityMatrix() {
  return [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];
}

function multiplyMatrices(left, right) {
  const output = new Array(16).fill(0);
  for (let column = 0; column < 4; column += 1) {
    for (let row = 0; row < 4; row += 1) {
      for (let index = 0; index < 4; index += 1) {
        output[column * 4 + row] +=
          left[index * 4 + row] * right[column * 4 + index];
      }
    }
  }
  return output;
}

function composeMatrix(node) {
  if (Array.isArray(node.matrix) && node.matrix.length === 16) {
    return [...node.matrix];
  }
  const [x, y, z, w] = node.rotation ?? [0, 0, 0, 1];
  const [sx, sy, sz] = node.scale ?? [1, 1, 1];
  const [tx, ty, tz] = node.translation ?? [0, 0, 0];
  const xx = x * x;
  const yy = y * y;
  const zz = z * z;
  const xy = x * y;
  const xz = x * z;
  const yz = y * z;
  const wx = w * x;
  const wy = w * y;
  const wz = w * z;
  return [
    (1 - 2 * (yy + zz)) * sx,
    2 * (xy + wz) * sx,
    2 * (xz - wy) * sx,
    0,
    2 * (xy - wz) * sy,
    (1 - 2 * (xx + zz)) * sy,
    2 * (yz + wx) * sy,
    0,
    2 * (xz + wy) * sz,
    2 * (yz - wx) * sz,
    (1 - 2 * (xx + yy)) * sz,
    0,
    tx,
    ty,
    tz,
    1,
  ];
}

function transformPoint(matrix, point) {
  const [x, y, z] = point;
  return [
    matrix[0] * x + matrix[4] * y + matrix[8] * z + matrix[12],
    matrix[1] * x + matrix[5] * y + matrix[9] * z + matrix[13],
    matrix[2] * x + matrix[6] * y + matrix[10] * z + matrix[14],
  ];
}

function emptyBounds() {
  return {
    min: [Number.POSITIVE_INFINITY, Number.POSITIVE_INFINITY, Number.POSITIVE_INFINITY],
    max: [Number.NEGATIVE_INFINITY, Number.NEGATIVE_INFINITY, Number.NEGATIVE_INFINITY],
  };
}

function includePoint(bounds, point) {
  for (let axis = 0; axis < 3; axis += 1) {
    bounds.min[axis] = Math.min(bounds.min[axis], point[axis]);
    bounds.max[axis] = Math.max(bounds.max[axis], point[axis]);
  }
}

function hasBounds(bounds) {
  return bounds.min.every(Number.isFinite) && bounds.max.every(Number.isFinite);
}

function mergeBounds(target, source) {
  if (!source || !hasBounds(source)) {
    return;
  }
  includePoint(target, source.min);
  includePoint(target, source.max);
}

function meshLocalBounds(document, mesh) {
  const bounds = emptyBounds();
  for (const primitive of mesh?.primitives ?? []) {
    const accessorIndex = primitive.attributes?.POSITION;
    const accessor = document.accessors?.[accessorIndex];
    if (
      Array.isArray(accessor?.min) &&
      accessor.min.length >= 3 &&
      Array.isArray(accessor?.max) &&
      accessor.max.length >= 3
    ) {
      includePoint(bounds, accessor.min.slice(0, 3));
      includePoint(bounds, accessor.max.slice(0, 3));
    }
  }
  return hasBounds(bounds) ? bounds : null;
}

function transformBounds(bounds, matrix) {
  if (!bounds) {
    return null;
  }
  const output = emptyBounds();
  for (const x of [bounds.min[0], bounds.max[0]]) {
    for (const y of [bounds.min[1], bounds.max[1]]) {
      for (const z of [bounds.min[2], bounds.max[2]]) {
        includePoint(output, transformPoint(matrix, [x, y, z]));
      }
    }
  }
  return output;
}

function roundNumber(value) {
  return Number.isFinite(value) ? Number(value.toFixed(6)) : null;
}

function roundVector(vector) {
  return vector.map(roundNumber);
}

function describeBounds(bounds) {
  if (!bounds || !hasBounds(bounds)) {
    return null;
  }
  const center = bounds.min.map(
    (value, axis) => (value + bounds.max[axis]) / 2,
  );
  const extent = bounds.min.map(
    (value, axis) => bounds.max[axis] - value,
  );
  return {
    min: roundVector(bounds.min),
    max: roundVector(bounds.max),
    center: roundVector(center),
    extent: roundVector(extent),
    diagonal: roundNumber(Math.hypot(...extent)),
  };
}

function primitiveTriangles(document, primitive) {
  const accessorIndex = primitive.indices ?? primitive.attributes?.POSITION;
  const count = document.accessors?.[accessorIndex]?.count ?? 0;
  const mode = primitive.mode ?? TRIANGLES;
  if (mode === TRIANGLES) {
    return Math.floor(count / 3);
  }
  if (mode === TRIANGLE_STRIP || mode === TRIANGLE_FAN) {
    return Math.max(0, count - 2);
  }
  return 0;
}

function meaningfulName(name) {
  if (typeof name !== "string") {
    return false;
  }
  const normalized = name.trim().toLowerCase();
  if (normalized.length < 3 || !/[a-z\u00c0-\u024f\u0400-\u04ff]/u.test(normalized)) {
    return false;
  }
  return !/^(node|mesh|object|primitive|part)([ _.-]*\d+)?$/u.test(normalized);
}

function buildParents(nodes) {
  const parents = new Array(nodes.length).fill(null);
  nodes.forEach((node, parentIndex) => {
    for (const childIndex of node.children ?? []) {
      if (parents[childIndex] === null) {
        parents[childIndex] = parentIndex;
      }
    }
  });
  return parents;
}

function buildWorldMatrices(nodes, parents) {
  const cache = new Array(nodes.length);
  function resolveWorld(index, active = new Set()) {
    if (cache[index]) {
      return cache[index];
    }
    if (active.has(index)) {
      throw new Error(`Node hierarchy contains a cycle at node ${index}`);
    }
    active.add(index);
    const local = composeMatrix(nodes[index] ?? {});
    const parentIndex = parents[index];
    cache[index] =
      parentIndex === null
        ? local
        : multiplyMatrices(resolveWorld(parentIndex, active), local);
    active.delete(index);
    return cache[index];
  }
  return nodes.map((_, index) => resolveWorld(index));
}

function nodePath(nodes, parents, index) {
  const parts = [];
  let cursor = index;
  const visited = new Set();
  while (cursor !== null && !visited.has(cursor)) {
    visited.add(cursor);
    const node = nodes[cursor] ?? {};
    parts.push(node.name?.trim() || `#${cursor}`);
    cursor = parents[cursor];
  }
  return parts.reverse().join("/");
}

function classify(meshNodeCount, semanticRatio) {
  if (meshNodeCount <= 1) {
    return {
      capability: "fused-single-mesh",
      truePartAnimation: false,
      semanticGrouping: false,
      reason:
        "The model exposes no more than one independently transformable mesh-bearing node.",
    };
  }
  if (meshNodeCount <= 3) {
    return {
      capability: "partially-merged",
      truePartAnimation: true,
      semanticGrouping: false,
      reason:
        "Only two or three independently transformable mesh-bearing nodes are available.",
    };
  }
  if (semanticRatio >= 0.5) {
    return {
      capability: "structured-named-parts",
      truePartAnimation: true,
      semanticGrouping: true,
      reason:
        "The model exposes multiple independent parts and most have meaningful node names.",
    };
  }
  return {
    capability: "separated-unnamed-parts",
    truePartAnimation: true,
    semanticGrouping: false,
    reason:
      "The model exposes multiple independent parts, but names are too weak for trusted semantic grouping.",
  };
}

export function analyzeDocument(document, metadata = {}) {
  const nodes = document.nodes ?? [];
  const meshes = document.meshes ?? [];
  const materials = document.materials ?? [];
  const parents = buildParents(nodes);
  const worldMatrices = buildWorldMatrices(nodes, parents);
  const nameCounts = new Map();
  for (const node of nodes) {
    if (node.name?.trim()) {
      nameCounts.set(node.name, (nameCounts.get(node.name) ?? 0) + 1);
    }
  }

  let primitiveCount = 0;
  let triangleCount = 0;
  let dracoPrimitiveCount = 0;
  for (const mesh of meshes) {
    for (const primitive of mesh.primitives ?? []) {
      primitiveCount += 1;
      triangleCount += primitiveTriangles(document, primitive);
      if (primitive.extensions?.KHR_draco_mesh_compression) {
        dracoPrimitiveCount += 1;
      }
    }
  }

  const modelBounds = emptyBounds();
  const partCandidates = [];
  for (let nodeIndex = 0; nodeIndex < nodes.length; nodeIndex += 1) {
    const node = nodes[nodeIndex];
    if (!Number.isInteger(node.mesh) || !meshes[node.mesh]) {
      continue;
    }
    const mesh = meshes[node.mesh];
    const localBounds = meshLocalBounds(document, mesh);
    const worldBounds = transformBounds(localBounds, worldMatrices[nodeIndex]);
    mergeBounds(modelBounds, worldBounds);
    const materialNames = [
      ...new Set(
        (mesh.primitives ?? [])
          .map((primitive) => materials[primitive.material]?.name)
          .filter(Boolean),
      ),
    ];
    partCandidates.push({
      nodeIndex,
      name: node.name?.trim() || null,
      nameIsUnique: Boolean(node.name && nameCounts.get(node.name) === 1),
      path: nodePath(nodes, parents, nodeIndex),
      parentNodeIndex: parents[nodeIndex],
      meshIndex: node.mesh,
      semanticName: meaningfulName(node.name),
      primitiveCount: mesh.primitives?.length ?? 0,
      triangleCount: (mesh.primitives ?? []).reduce(
        (sum, primitive) => sum + primitiveTriangles(document, primitive),
        0,
      ),
      materialNames,
      bounds: describeBounds(worldBounds),
    });
  }

  const semanticCount = partCandidates.filter(
    (candidate) => candidate.semanticName,
  ).length;
  const semanticRatio =
    partCandidates.length === 0 ? 0 : semanticCount / partCandidates.length;
  const classification = classify(partCandidates.length, semanticRatio);
  const duplicateNodeNames = [...nameCounts.entries()]
    .filter(([, count]) => count > 1)
    .map(([name, count]) => ({ name, count }));
  const images = document.images ?? [];
  const basisuTextureCount = (document.textures ?? []).filter(
    (texture) => texture.extensions?.KHR_texture_basisu,
  ).length;
  const ktx2ImageCount = images.filter(
    (image) =>
      image.mimeType === "image/ktx2" ||
      (typeof image.uri === "string" && /\.ktx2(?:$|[?#])/iu.test(image.uri)),
  ).length;
  const missingBoundsCount = partCandidates.filter(
    (candidate) => !candidate.bounds,
  ).length;

  return {
    schemaVersion: 1,
    source: {
      path: metadata.publicPath ?? metadata.absolutePath ?? null,
      format: metadata.format ?? null,
      bytes: metadata.bytes ?? null,
      assetVersion: document.asset?.version ?? null,
      generator: document.asset?.generator ?? null,
    },
    counts: {
      scenes: document.scenes?.length ?? 0,
      nodes: nodes.length,
      meshNodes: partCandidates.length,
      meshes: meshes.length,
      primitives: primitiveCount,
      triangles: triangleCount,
      materials: materials.length,
      textures: document.textures?.length ?? 0,
      images: images.length,
      animations: document.animations?.length ?? 0,
      skins: document.skins?.length ?? 0,
      cameras: document.cameras?.length ?? 0,
    },
    compression: {
      extensionsUsed: document.extensionsUsed ?? [],
      extensionsRequired: document.extensionsRequired ?? [],
      dracoPrimitiveCount,
      meshoptBufferViewCount: (document.bufferViews ?? []).filter(
        (view) => view.extensions?.EXT_meshopt_compression,
      ).length,
      basisuTextureCount,
      ktx2ImageCount,
    },
    naming: {
      meaningfulMeshNodeNames: semanticCount,
      meaningfulMeshNodeRatio: roundNumber(semanticRatio),
      duplicateNodeNames,
    },
    bounds: describeBounds(modelBounds),
    capability: classification,
    warnings: [
      ...(missingBoundsCount
        ? [
            `${missingBoundsCount} mesh-bearing nodes have no accessor min/max bounds; spatial candidates may be incomplete.`,
          ]
        : []),
      ...(duplicateNodeNames.length
        ? [
            "Duplicate node names require node-index selectors or manual disambiguation.",
          ]
        : []),
      ...(classification.capability === "fused-single-mesh"
        ? [
            "True semantic exploded assembly requires external mesh segmentation.",
          ]
        : []),
    ],
    partCandidates,
  };
}

export async function inspectModel(modelPath, options = {}) {
  const loaded = await loadModelDocument(modelPath);
  return analyzeDocument(loaded.document, {
    ...loaded,
    publicPath: options.publicPath ?? null,
  });
}
