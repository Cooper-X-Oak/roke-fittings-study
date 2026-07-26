import * as THREE from "three";
import { GLTFLoader } from "../experiment/assets/vendor/three/loaders/GLTFLoader.js";
import { DRACOLoader } from "../experiment/assets/vendor/three/loaders/DRACOLoader.js";
import { RoomEnvironment } from "../experiment/assets/vendor/three/environments/RoomEnvironment.js";

const canvas = document.querySelector("#canvas");
const story = document.querySelector("#story");
const poster = document.querySelector("#poster");
const loading = document.querySelector("#loading");
const forwardButton = document.querySelector("#play-forward");
const reverseButton = document.querySelector("#play-reverse");
const timelineFill = document.querySelector("#timeline-fill");
const shotNumber = document.querySelector("#shot-number");
const shotName = document.querySelector("#shot-name");
const eyebrow = document.querySelector("#eyebrow");
const title = document.querySelector("#title");
const body = document.querySelector("#body");
const directionLabel = document.querySelector("#direction");
const geometryStatus = document.querySelector("#geometry-status");
const debug = document.querySelector("#debug");

const params = new URLSearchParams(location.search);
const debugEnabled = params.has("debug");
debug.hidden = !debugEnabled;

const renderer = new THREE.WebGLRenderer({
  canvas,
  antialias: true,
  alpha: false,
  powerPreference: "high-performance",
});
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1;
renderer.setClearColor(0x11161b, 1);
renderer.shadowMap.enabled = false;
renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x11161b);
scene.fog = new THREE.FogExp2(0x11161b, 0.012);

const camera = new THREE.PerspectiveCamera(31, 1, 0.015, 80);
scene.add(camera);

const environment = new RoomEnvironment();
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(environment, 0.05).texture;
environment.dispose();
pmrem.dispose();

const hemi = new THREE.HemisphereLight(0xd8dde0, 0x171b1f, 0.58);
scene.add(hemi);

const keyLight = new THREE.DirectionalLight(0xf4f0e8, 1.8);
keyLight.position.set(5, 7, 6);
scene.add(keyLight);

const rimLight = new THREE.DirectionalLight(0xa8b5be, 2.2);
rimLight.position.set(-5, 4, -6);
scene.add(rimLight);

const coreLight = new THREE.PointLight(0xd19a68, 3.2, 8, 2);
coreLight.position.set(1.2, -0.8, 2.2);
scene.add(coreLight);

const floor = new THREE.Mesh(
  new THREE.CircleGeometry(8, 80),
  new THREE.MeshStandardMaterial({
    color: 0x242a2f,
    roughness: 0.94,
    metalness: 0.02,
  }),
);
floor.rotation.x = -Math.PI / 2;
floor.position.y = -1.88;
scene.add(floor);

const SHOT_COPY = {
  "core-suspended": {
    title: "精密，先从<br>核心被看见。",
    body: "四个真实几何岛沿中央轴展开；编号只代表镜头中的空间顺序。",
  },
  "precision-nested": {
    title: "一层<br>接住一层。",
    body: "三级阀笼候选与阀座候选分阶段归位，不用发光冒充分离。",
  },
  "body-encloses": {
    title: "核心，被<br>结构承载。",
    body: "阀体先以灰模透明度建立内部位置，再连续闭合。",
  },
  "assembly-complete": {
    title: "直到每一层，<br>成为同一台设备。",
    body: "主体与气动执行器沿同一机械轴完成整机轮廓。",
  },
  "product-presence": {
    title: "精密，最终<br>成为整体。",
    body: "DN80 CL2500 气动串级式调节阀灰模预演。",
  },
};

const GROUP_NAMES = [
  "VALVE_BODY_BONNET",
  "PNEUMATIC_ACTUATOR",
  "STEM_CASCADE_PLUG",
  "CASCADE_TRIM",
  "SEALS_SUPPORT",
  "PRODUCTION_DETAILS",
];

const GROUP_COLORS = {
  VALVE_BODY_BONNET: 0x697077,
  PNEUMATIC_ACTUATOR: 0x858b90,
  STEM_CASCADE_PLUG: 0xb8a08b,
  CASCADE_TRIM: 0xb09a82,
  SEALS_SUPPORT: 0x777e83,
  PRODUCTION_DETAILS: 0x5f656a,
};

const TRIM_SEPARATION_WORLD = [-1.35, -0.45, 0.45, 1.35];
const BODY_OPEN_OFFSET_WORLD = 0.92;
const ACTUATOR_OPEN_OFFSET_WORLD = -1.75;
const ACTUATOR_SEAT_OFFSET_WORLD = 0.16;
const SUPPORT_OPEN_OFFSET_WORLD = -0.9;
const DETAILS_OPEN_OFFSET_WORLD = 0.64;
const STEM_OPEN_OFFSET_WORLD = 0.72;
const POSITION_WELD_PRECISION = 10000;

let cameraPath;
let product;
let productRig;
let modelScale = 1;
let groups = new Map();
let trimIslands = [];
let trimDiagnostics = [];
let currentProgress = 0;
let targetProgress = 0;
let scheduled = false;
let playing = false;
let playbackDirection = 1;
let playbackStartedAt = 0;
let currentShotId = "";
let usableFrameAt = 0;
const loadStartedAt = performance.now();
let renderCount = 0;
let lastRenderAt = 0;
const frameTimes = [];
let readyResolve;
let readyReject;
const readyPromise = new Promise((resolve, reject) => {
  readyResolve = resolve;
  readyReject = reject;
});

const smooth = (value) => value * value * (3 - 2 * value);
const mix = (a, b, t) => a + (b - a) * t;
const mixVector = (a, b, t) =>
  a.map((value, index) => mix(value, b[index], t));

function samplePath(progress) {
  const frame = progress * (cameraPath.totalFrames - 1);
  let left = cameraPath.keyframes[0];
  let right = cameraPath.keyframes.at(-1);
  for (let index = 1; index < cameraPath.keyframes.length; index += 1) {
    if (frame <= cameraPath.keyframes[index].frame) {
      left = cameraPath.keyframes[index - 1];
      right = cameraPath.keyframes[index];
      break;
    }
  }
  const span = Math.max(1, right.frame - left.frame);
  const t = smooth((frame - left.frame) / span);
  const frameIndex = Math.min(
    cameraPath.totalFrames - 1,
    Math.floor(frame),
  );
  const shot =
    cameraPath.shots.find(
      (candidate) =>
        frameIndex >= candidate.startFrame &&
        frameIndex <= candidate.endFrame,
    ) ?? cameraPath.shots.at(-1);
  return {
    frame,
    shot,
    camera: {
      position: mixVector(left.position, right.position, t),
      target: mixVector(left.target, right.target, t),
      roll: mix(left.roll, right.roll, t),
      fov: mix(left.fov, right.fov, t),
      focusDistance: mix(
        new THREE.Vector3(...left.position).distanceTo(
          new THREE.Vector3(...left.target),
        ),
        new THREE.Vector3(...right.position).distanceTo(
          new THREE.Vector3(...right.target),
        ),
        t,
      ),
    },
    product: {
      trimAssembly: mixVector(left.trimAssembly, right.trimAssembly, t),
      stemAssembly: mix(left.stemAssembly, right.stemAssembly, t),
      bodyClosure: mix(left.bodyClosure, right.bodyClosure, t),
      bodyOpacity: mix(left.bodyOpacity, right.bodyOpacity, t),
      actuatorAssembly: mix(
        left.actuatorAssembly,
        right.actuatorAssembly,
        t,
      ),
      detailAssembly: mix(
        left.detailAssembly,
        right.detailAssembly,
        t,
      ),
      productYawDegrees: mix(
        left.productYawDegrees,
        right.productYawDegrees,
        t,
      ),
      coreEmphasis: mix(left.coreEmphasis, right.coreEmphasis, t),
    },
    light: {
      key: mix(left.keyLight, right.keyLight, t),
      rim: mix(left.rimLight, right.rimLight, t),
      core: mix(left.coreLight, right.coreLight, t),
    },
    occlusion: mix(left.occlusion, right.occlusion, t),
  };
}

function configureMaterials(root) {
  root.traverse((node) => {
    if (!node.isMesh) return;
    const sourceMaterials = Array.isArray(node.material)
      ? node.material
      : [node.material];
    const cloned = sourceMaterials.map((source) => {
      const material = source.clone();
      material.metalness = 0.22;
      material.roughness = 0.7;
      material.envMapIntensity = 0.7;
      material.side = THREE.DoubleSide;
      material.userData.baseOpacity = 1;
      return material;
    });
    node.material = Array.isArray(node.material) ? cloned : cloned[0];
  });
}

function findAndCaptureGroups(root) {
  for (const name of GROUP_NAMES) {
    const node = root.getObjectByName(name);
    if (!node) throw new Error(`GLB is missing semantic group ${name}`);
    groups.set(name, {
      node,
      basePosition: node.position.clone(),
    });
    node.traverse((child) => {
      if (!child.isMesh) return;
      const materials = Array.isArray(child.material)
        ? child.material
        : [child.material];
      for (const material of materials) {
        material.color?.setHex(GROUP_COLORS[name]);
      }
    });
  }
}

function findTrimMesh() {
  const root = groups.get("CASCADE_TRIM")?.node;
  let result = null;
  root?.traverse((node) => {
    if (!result && node.isMesh && node.geometry?.getAttribute("position")) {
      result = node;
    }
  });
  if (!result) throw new Error("CASCADE_TRIM has no decodable mesh geometry");
  return result;
}

function connectedTriangleComponents(geometry) {
  const position = geometry.getAttribute("position");
  const index = geometry.index;
  const triangleCount = Math.floor(
    (index ? index.count : position.count) / 3,
  );
  const parents = new Int32Array(triangleCount);
  const ranks = new Uint8Array(triangleCount);
  for (let value = 0; value < triangleCount; value += 1) parents[value] = value;

  const find = (value) => {
    let cursor = value;
    while (parents[cursor] !== cursor) {
      parents[cursor] = parents[parents[cursor]];
      cursor = parents[cursor];
    }
    return cursor;
  };
  const union = (left, right) => {
    let leftRoot = find(left);
    let rightRoot = find(right);
    if (leftRoot === rightRoot) return;
    if (ranks[leftRoot] < ranks[rightRoot]) {
      [leftRoot, rightRoot] = [rightRoot, leftRoot];
    }
    parents[rightRoot] = leftRoot;
    if (ranks[leftRoot] === ranks[rightRoot]) ranks[leftRoot] += 1;
  };
  const vertexIndexAt = (offset) => (index ? index.getX(offset) : offset);
  const weldedOwner = new Map();

  for (let triangle = 0; triangle < triangleCount; triangle += 1) {
    for (let corner = 0; corner < 3; corner += 1) {
      const vertex = vertexIndexAt(triangle * 3 + corner);
      const key = [
        Math.round(position.getX(vertex) * POSITION_WELD_PRECISION),
        Math.round(position.getY(vertex) * POSITION_WELD_PRECISION),
        Math.round(position.getZ(vertex) * POSITION_WELD_PRECISION),
      ].join(",");
      const owner = weldedOwner.get(key);
      if (owner === undefined) weldedOwner.set(key, triangle);
      else union(triangle, owner);
    }
  }

  const components = new Map();
  for (let triangle = 0; triangle < triangleCount; triangle += 1) {
    const root = find(triangle);
    if (!components.has(root)) components.set(root, []);
    const values = components.get(root);
    values.push(
      vertexIndexAt(triangle * 3),
      vertexIndexAt(triangle * 3 + 1),
      vertexIndexAt(triangle * 3 + 2),
    );
  }
  return [...components.values()].filter((values) => values.length >= 30);
}

function splitTrimIntoActualIslands() {
  const sourceMesh = findTrimMesh();
  const geometry = sourceMesh.geometry;
  const components = connectedTriangleComponents(geometry);
  const maximumIndex = geometry.getAttribute("position").count - 1;
  const IndexArray = maximumIndex > 65535 ? Uint32Array : Uint16Array;
  const candidates = components.map((indices) => {
    const componentGeometry = new THREE.BufferGeometry();
    for (const [name, attribute] of Object.entries(geometry.attributes)) {
      componentGeometry.setAttribute(name, attribute);
    }
    componentGeometry.setIndex(
      new THREE.BufferAttribute(new IndexArray(indices), 1),
    );
    const position = geometry.getAttribute("position");
    const bounds = new THREE.Box3();
    const point = new THREE.Vector3();
    for (const vertexIndex of new Set(indices)) {
      point.fromBufferAttribute(position, vertexIndex);
      bounds.expandByPoint(point);
    }
    componentGeometry.boundingBox = bounds;
    const center = bounds.getCenter(new THREE.Vector3());
    const sphere = new THREE.Sphere();
    bounds.getBoundingSphere(sphere);
    componentGeometry.boundingSphere = sphere;
    return { indices, geometry: componentGeometry, center };
  });
  candidates.sort((left, right) => left.center.y - right.center.y);
  if (candidates.length !== 4) {
    throw new Error(
      `CASCADE_TRIM exposes ${candidates.length} connected geometry islands; exactly 4 are required`,
    );
  }

  const sourceMaterials = Array.isArray(sourceMesh.material)
    ? sourceMesh.material
    : [sourceMesh.material];
  for (const material of sourceMaterials) material.visible = false;

  trimIslands = candidates.map((candidate, index) => {
    const material = sourceMaterials[0].clone();
    material.visible = true;
    material.color.setHex([0x8c8278, 0xa29485, 0xb1a18f, 0xc0aa91][index]);
    material.metalness = 0.28;
    material.roughness = 0.62;
    material.emissive = new THREE.Color(0x2c1609);
    material.emissiveIntensity = 0;
    const mesh = new THREE.Mesh(candidate.geometry, material);
    mesh.name = `CASCADE_GEOMETRY_ISLAND_${index + 1}`;
    sourceMesh.add(mesh);
    return {
      name: mesh.name,
      node: mesh,
      basePosition: mesh.position.clone(),
      triangleCount: candidate.indices.length / 3,
      localCenter: candidate.center.clone(),
    };
  });
  trimDiagnostics = trimIslands.map((island, index) => ({
    name: island.name,
    axisOrder: index + 1,
    triangleCount: island.triangleCount,
    localCenter: island.localCenter.toArray(),
  }));
}

function orientAndFit(root) {
  root.updateMatrixWorld(true);
  let box = new THREE.Box3().setFromObject(root);
  const size = box.getSize(new THREE.Vector3());
  if (size.x > size.y && size.x > size.z) {
    root.rotation.z = Math.PI / 2;
  } else if (size.z > size.y && size.z > size.x) {
    root.rotation.x = Math.PI / 2;
  }
  root.updateMatrixWorld(true);
  box = new THREE.Box3().setFromObject(root);
  const orientedSize = box.getSize(new THREE.Vector3());
  modelScale = 3.4 / orientedSize.y;
  root.scale.setScalar(modelScale);
  root.updateMatrixWorld(true);
  box = new THREE.Box3().setFromObject(root);
  const center = box.getCenter(new THREE.Vector3());
  root.position.sub(center);
  root.updateMatrixWorld(true);
}

function setGroupOpacity(name, opacity) {
  const entry = groups.get(name);
  if (!entry) return;
  entry.node.traverse((node) => {
    if (!node.isMesh || node.name.startsWith("CASCADE_GEOMETRY_ISLAND_")) {
      return;
    }
    const materials = Array.isArray(node.material)
      ? node.material
      : [node.material];
    for (const material of materials) {
      if (material.visible === false) continue;
      const finalOpacity = Math.min(
        material.userData.baseOpacity ?? 1,
        opacity,
      );
      material.opacity = finalOpacity;
      material.transparent = finalOpacity < 0.995;
      material.depthWrite = finalOpacity > 0.52;
    }
  });
}

function resetGroupPositions() {
  for (const entry of groups.values()) {
    entry.node.position.copy(entry.basePosition);
  }
}

function applyState(state) {
  const position = new THREE.Vector3(...state.camera.position);
  const target = new THREE.Vector3(...state.camera.target);
  camera.position.copy(position);
  camera.fov = state.camera.fov;
  camera.up.set(0, 1, 0);
  camera.lookAt(target);
  camera.rotateZ(THREE.MathUtils.degToRad(state.camera.roll));
  camera.updateProjectionMatrix();

  resetGroupPositions();

  const bodyEntry = groups.get("VALVE_BODY_BONNET");
  bodyEntry.node.position.z =
    bodyEntry.basePosition.z +
    (BODY_OPEN_OFFSET_WORLD * (1 - state.product.bodyClosure)) / modelScale;

  const actuator = groups.get("PNEUMATIC_ACTUATOR");
  actuator.node.position.z =
    actuator.basePosition.z +
    (ACTUATOR_OPEN_OFFSET_WORLD * (1 - state.product.actuatorAssembly) +
      ACTUATOR_SEAT_OFFSET_WORLD * state.product.actuatorAssembly) /
      modelScale;

  const support = groups.get("SEALS_SUPPORT");
  support.node.position.z =
    support.basePosition.z +
    (SUPPORT_OPEN_OFFSET_WORLD * (1 - state.product.detailAssembly)) /
      modelScale;

  const details = groups.get("PRODUCTION_DETAILS");
  details.node.position.z =
    details.basePosition.z +
    (DETAILS_OPEN_OFFSET_WORLD * (1 - state.product.detailAssembly)) /
      modelScale;

  const stem = groups.get("STEM_CASCADE_PLUG");
  stem.node.position.z =
    stem.basePosition.z +
    (STEM_OPEN_OFFSET_WORLD * (1 - state.product.stemAssembly)) / modelScale;

  trimIslands.forEach((island, index) => {
    island.node.position.copy(island.basePosition);
    island.node.position.y +=
      (TRIM_SEPARATION_WORLD[index] *
        (1 - state.product.trimAssembly[index])) /
      modelScale;
    island.node.material.emissiveIntensity =
      state.product.coreEmphasis *
      (0.24 + 0.16 * (1 - state.product.trimAssembly[index]));
  });

  productRig.rotation.y = THREE.MathUtils.degToRad(
    state.product.productYawDegrees,
  );
  setGroupOpacity("VALVE_BODY_BONNET", state.product.bodyOpacity);
  setGroupOpacity("PNEUMATIC_ACTUATOR", 0.35 + 0.65 * state.product.actuatorAssembly);
  setGroupOpacity("SEALS_SUPPORT", 0.28 + 0.72 * state.product.detailAssembly);
  setGroupOpacity("PRODUCTION_DETAILS", 0.2 + 0.8 * state.product.detailAssembly);

  keyLight.intensity = state.light.key * 1.9;
  rimLight.intensity = state.light.rim * 2;
  coreLight.intensity = state.light.core * 3.4;
  timelineFill.style.transform = `scaleX(${currentProgress})`;
  updateCopy(state.shot);
}

function updateCopy(shot) {
  if (shot.id === currentShotId) return;
  currentShotId = shot.id;
  const index = cameraPath.shots.findIndex(
    (candidate) => candidate.id === shot.id,
  );
  const number = String(index + 1).padStart(2, "0");
  const copy = SHOT_COPY[shot.id];
  shotNumber.textContent = number;
  shotName.textContent = shot.title;
  eyebrow.textContent = `${number} / ${shot.title}`;
  title.innerHTML = copy.title;
  body.textContent = copy.body;
}

function render(timestamp = performance.now()) {
  scheduled = false;
  if (!product || !cameraPath) return;

  if (lastRenderAt) frameTimes.push(timestamp - lastRenderAt);
  lastRenderAt = timestamp;
  if (frameTimes.length > 1200) frameTimes.shift();

  if (playing) {
    const elapsed = (timestamp - playbackStartedAt) / 1000;
    const phase = Math.min(1, elapsed / cameraPath.durationSeconds);
    currentProgress = playbackDirection > 0 ? phase : 1 - phase;
    targetProgress = currentProgress;
    if (phase >= 1) {
      playing = false;
      directionLabel.textContent =
        playbackDirection > 0 ? "FORWARD COMPLETE" : "REVERSE COMPLETE";
    }
  } else {
    currentProgress += (targetProgress - currentProgress) * 0.16;
    if (Math.abs(targetProgress - currentProgress) < 0.00008) {
      currentProgress = targetProgress;
    }
  }

  const state = samplePath(currentProgress);
  applyState(state);
  renderer.render(scene, camera);
  renderCount += 1;

  if (!usableFrameAt) {
    usableFrameAt = performance.now();
    poster.classList.add("is-hidden");
    loading.textContent = `灰模已就绪 · ${trimIslands.length} 个实际内件几何岛`;
    setTimeout(() => {
      loading.style.display = "none";
    }, 1600);
  }

  if (debugEnabled) {
    const sorted = [...frameTimes].sort((a, b) => a - b);
    const percentile = (p) =>
      sorted[Math.floor((sorted.length - 1) * p)] ?? 0;
    debug.value = [
      `shot ${state.shot.id}`,
      `frame ${state.frame.toFixed(1)} / ${cameraPath.totalFrames - 1}`,
      `progress ${currentProgress.toFixed(4)}`,
      `direction ${playbackDirection > 0 ? "forward" : "reverse"}`,
      `trim islands ${trimIslands.length}`,
      `body opacity ${state.product.bodyOpacity.toFixed(3)}`,
      `renders ${renderCount}`,
      `p50 ${percentile(0.5).toFixed(2)} ms`,
      `p95 ${percentile(0.95).toFixed(2)} ms`,
    ].join("\n");
  }

  if (playing || Math.abs(targetProgress - currentProgress) > 0.00008) {
    schedule();
  }
}

function schedule() {
  if (scheduled) return;
  scheduled = true;
  requestAnimationFrame(render);
}

function startPlayback(direction) {
  playbackDirection = direction;
  playing = true;
  playbackStartedAt = performance.now();
  currentProgress = direction > 0 ? 0 : 1;
  targetProgress = currentProgress;
  directionLabel.textContent = direction > 0 ? "FORWARD" : "REVERSE";
  schedule();
}

function scrollProgress() {
  const rect = story.getBoundingClientRect();
  const travel = story.offsetHeight - innerHeight;
  return THREE.MathUtils.clamp(-rect.top / Math.max(1, travel), 0, 1);
}

function onScroll() {
  if (playing) return;
  targetProgress = scrollProgress();
  directionLabel.textContent = "SCROLL SCRUB";
  schedule();
}

function resize() {
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  renderer.setSize(width, height, false);
  camera.aspect = width / Math.max(1, height);
  camera.updateProjectionMatrix();
  schedule();
}

function islandSnapshot(island) {
  island.node.updateWorldMatrix(true, false);
  const worldCenter = island.localCenter
    .clone()
    .applyMatrix4(island.node.matrixWorld);
  const projected = worldCenter.clone().project(camera);
  return {
    name: island.name,
    triangleCount: island.triangleCount,
    position: island.node.position.toArray(),
    worldCenter: worldCenter.toArray(),
    ndc: projected.toArray(),
    projectedOnScreen:
      Math.abs(projected.x) <= 1 &&
      Math.abs(projected.y) <= 1 &&
      projected.z >= -1 &&
      projected.z <= 1,
  };
}

function stateSnapshot() {
  const sampled = samplePath(currentProgress);
  scene.updateMatrixWorld(true);
  return {
    progress: currentProgress,
    frame: sampled.frame,
    shotId: sampled.shot.id,
    cameraPosition: camera.position.toArray(),
    cameraTarget: sampled.camera.target,
    cameraFov: camera.fov,
    focusDistance: sampled.camera.focusDistance,
    mechanicalAxisWorld: cameraPath.mechanicalAxisWorld,
    productState: structuredClone(sampled.product),
    occlusion: sampled.occlusion,
    renderCount,
    usableFrameMs: usableFrameAt ? usableFrameAt - loadStartedAt : null,
    trimConnectedComponentCount: trimIslands.length,
    trimDiagnostics,
    trimIslands: trimIslands.map(islandSnapshot),
    groups: [...groups].map(([name, entry]) => ({
      name,
      position: entry.node.position.toArray(),
      worldPosition: entry.node.getWorldPosition(new THREE.Vector3()).toArray(),
    })),
  };
}

function canonicalMotionSummary() {
  const states = Array.from(
    { length: cameraPath.totalFrames },
    (_, frame) => samplePath(frame / (cameraPath.totalFrames - 1)),
  );
  const vectorDistance = (left, right) =>
    Math.hypot(...left.map((value, index) => value - right[index]));
  const productDelta = (left, right) =>
    vectorDistance(left.trimAssembly, right.trimAssembly) +
    Math.abs(left.stemAssembly - right.stemAssembly) +
    Math.abs(left.bodyClosure - right.bodyClosure) +
    Math.abs(left.actuatorAssembly - right.actuatorAssembly) +
    Math.abs(left.detailAssembly - right.detailAssembly) +
    Math.abs(left.productYawDegrees - right.productYawDegrees);
  let cameraPathLength = 0;
  let maximumCameraStep = 0;
  let maximumTargetStep = 0;
  let coordinatedFrameCount = 0;
  let coordinatedIntervalCount = 0;
  let insideCoordinatedInterval = false;
  for (let index = 1; index < states.length; index += 1) {
    const cameraStep = vectorDistance(
      states[index - 1].camera.position,
      states[index].camera.position,
    );
    const targetStep = vectorDistance(
      states[index - 1].camera.target,
      states[index].camera.target,
    );
    const coordinated =
      cameraStep > 0.001 &&
      productDelta(states[index - 1].product, states[index].product) > 0.001;
    cameraPathLength += cameraStep;
    maximumCameraStep = Math.max(maximumCameraStep, cameraStep);
    maximumTargetStep = Math.max(maximumTargetStep, targetStep);
    if (coordinated) {
      coordinatedFrameCount += 1;
      if (!insideCoordinatedInterval) coordinatedIntervalCount += 1;
    }
    insideCoordinatedInterval = coordinated;
  }
  const yawValues = states.map((state) => state.product.productYawDegrees);
  return {
    cameraPathLength,
    maximumCameraStep,
    maximumTargetStep,
    productYawRange:
      Math.max(...yawValues) - Math.min(...yawValues),
    coordinatedFrameCount,
    coordinatedIntervalCount,
  };
}

window.__CONTROL_VALVE_METRICS__ = {
  waitForReady: () => readyPromise,
  setProgressForTest(value) {
    playing = false;
    targetProgress = THREE.MathUtils.clamp(value, 0, 1);
    currentProgress = targetProgress;
    const state = samplePath(currentProgress);
    applyState(state);
    scene.updateMatrixWorld(true);
    renderer.render(scene, camera);
    renderCount += 1;
    return stateSnapshot();
  },
  setProgressAndCaptureForTest(value) {
    playing = false;
    targetProgress = THREE.MathUtils.clamp(value, 0, 1);
    currentProgress = targetProgress;
    const state = samplePath(currentProgress);
    applyState(state);
    scene.updateMatrixWorld(true);
    renderer.render(scene, camera);
    renderCount += 1;
    return {
      state: stateSnapshot(),
      pngDataUrl: renderer.domElement.toDataURL("image/png"),
    };
  },
  startPlaybackForTest(direction) {
    startPlayback(direction >= 0 ? 1 : -1);
    return stateSnapshot();
  },
  snapshot: stateSnapshot,
  canonicalMotionSummary,
};

forwardButton.addEventListener("click", () => startPlayback(1));
reverseButton.addEventListener("click", () => startPlayback(-1));
addEventListener("scroll", onScroll, { passive: true });
new ResizeObserver(resize).observe(canvas);

async function start() {
  try {
    const draco = new DRACOLoader();
    draco.setDecoderPath("../experiment/assets/vendor/three/libs/draco/");
    const loader = new GLTFLoader();
    loader.setDRACOLoader(draco);
    const [pathResponse, gltf] = await Promise.all([
      fetch("./camera-path.json"),
      loader.loadAsync("./assets/control-valve-shot-ready.glb"),
    ]);
    if (!pathResponse.ok) {
      throw new Error(`camera path HTTP ${pathResponse.status}`);
    }
    cameraPath = await pathResponse.json();
    product = gltf.scene;
    product.name = "CONTROL_VALVE_PRODUCT";
    configureMaterials(product);
    findAndCaptureGroups(product);
    splitTrimIntoActualIslands();
    orientAndFit(product);
    productRig = new THREE.Group();
    productRig.name = "CONTROL_VALVE_PRODUCT_RIG";
    productRig.add(product);
    scene.add(productRig);
    draco.dispose();
    geometryStatus.textContent = `${trimIslands.length} 个实际内件几何岛`;

    if (matchMedia("(prefers-reduced-motion: reduce)").matches) {
      targetProgress = 1;
      currentProgress = 1;
    } else {
      targetProgress = scrollProgress();
      currentProgress = targetProgress;
    }
    resize();
    readyResolve({
      state: "ready",
      groups: groups.size,
      trimConnectedComponentCount: trimIslands.length,
      trimDiagnostics,
    });
  } catch (error) {
    loading.textContent = `灰模不可用：${error.message}`;
    loading.classList.add("is-error");
    console.error(error);
    readyReject(error);
  }
}

start();
