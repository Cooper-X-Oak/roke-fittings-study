import * as THREE from "three";
import { GLTFLoader } from "../experiment/assets/vendor/three/loaders/GLTFLoader.js";
import { DRACOLoader } from "../experiment/assets/vendor/three/loaders/DRACOLoader.js";
import { RoomEnvironment } from "../experiment/assets/vendor/three/environments/RoomEnvironment.js";

const canvas = document.querySelector("#canvas");
const story = document.querySelector("#story");
const poster = document.querySelector("#poster");
const loading = document.querySelector("#loading");
const playButton = document.querySelector("#play");
const timelineFill = document.querySelector("#timeline-fill");
const shotNumber = document.querySelector("#shot-number");
const shotName = document.querySelector("#shot-name");
const eyebrow = document.querySelector("#eyebrow");
const title = document.querySelector("#title");
const body = document.querySelector("#body");
const debug = document.querySelector("#debug");

const params = new URLSearchParams(location.search);
const debugEnabled = params.has("debug");
debug.hidden = !debugEnabled;

const renderer = new THREE.WebGLRenderer({
  canvas,
  antialias: true,
  alpha: false,
  powerPreference: "high-performance"
});
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.06;
renderer.setClearColor(0x0c1117, 1);
renderer.shadowMap.enabled = false;

const dprCap = Math.min(devicePixelRatio, 1.75);
renderer.setPixelRatio(dprCap);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0c1117);
scene.fog = new THREE.FogExp2(0x0c1117, 0.018);

const camera = new THREE.PerspectiveCamera(34, 1, 0.015, 80);
scene.add(camera);

const environment = new RoomEnvironment();
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(environment, 0.05).texture;
environment.dispose();
pmrem.dispose();

const hemi = new THREE.HemisphereLight(0xb9c5cc, 0x12171c, 0.5);
scene.add(hemi);

const keyLight = new THREE.DirectionalLight(0xfff3e8, 2.0);
keyLight.position.set(4, 7, 6);
scene.add(keyLight);

const rimLight = new THREE.DirectionalLight(0xa9bfd0, 2.25);
rimLight.position.set(-5, 3, -6);
scene.add(rimLight);

const accentLight = new THREE.PointLight(0xc46a3c, 4, 9, 2);
accentLight.position.set(1.5, -1, 2.4);
scene.add(accentLight);

const floor = new THREE.Mesh(
  new THREE.CircleGeometry(8, 80),
  new THREE.MeshStandardMaterial({
    color: 0x18212a,
    roughness: 0.88,
    metalness: 0.08
  })
);
floor.rotation.x = -Math.PI / 2;
floor.position.y = -1.9;
scene.add(floor);

const SHOT_COPY = {
  "product-authority": {
    title: "秩序<br>先于动作",
    body: "先看清整机，再理解内部。"
  },
  "axial-command": {
    title: "一条轴线<br>传递动作",
    body: "执行器、推杆与阀芯，始终保持在同一观察方向。"
  },
  "cascade-revealed": {
    title: "核心结构<br>逐级显现",
    body: "外壳退为参照，串级阀芯与三级阀笼仍处在完整空间中。"
  },
  "systems-in-order": {
    title: "六个系统<br>各在其位",
    body: "有限分离说明职责，不打散产品秩序。"
  },
  "product-resolved": {
    title: "理解之后<br>仍是整体",
    body: "DN80 CL2500 气动串级式装配体。"
  }
};

const GROUP_NAMES = [
  "VALVE_BODY_BONNET",
  "PNEUMATIC_ACTUATOR",
  "STEM_CASCADE_PLUG",
  "CASCADE_TRIM",
  "SEALS_SUPPORT",
  "PRODUCTION_DETAILS"
];

const EXPLODE_OFFSETS = {
  VALVE_BODY_BONNET: [0, 0, 0],
  PNEUMATIC_ACTUATOR: [0, 0.78, 0],
  STEM_CASCADE_PLUG: [0, 0.34, 0],
  CASCADE_TRIM: [0, -0.5, 0],
  SEALS_SUPPORT: [0.52, -0.1, 0.24],
  PRODUCTION_DETAILS: [-0.5, 0.08, -0.2]
};

const GROUP_COLORS = {
  VALVE_BODY_BONNET: 0x626a74,
  PNEUMATIC_ACTUATOR: 0x7a828b,
  STEM_CASCADE_PLUG: 0xc46a3c,
  CASCADE_TRIM: 0xb18a4a,
  SEALS_SUPPORT: 0x66888c,
  PRODUCTION_DETAILS: 0x8b9096
};

let cameraPath;
let product;
let modelScale = 1;
let groups = new Map();
let currentProgress = 0;
let targetProgress = 0;
let scheduled = false;
let playing = false;
let playbackStartedAt = 0;
let currentShotId = "";
let usableFrameAt = 0;
let loadStartedAt = performance.now();
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
const mixVector = (a, b, t) => a.map((value, index) => mix(value, b[index], t));

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
  const shot = cameraPath.shots.find(
    (candidate) => frame >= candidate.startFrame && frame < candidate.endFrame + 1
  ) ?? cameraPath.shots.at(-1);
  return {
    frame,
    shot,
    camera: {
      position: mixVector(left.position, right.position, t),
      target: mixVector(left.target, right.target, t),
      roll: mix(left.roll, right.roll, t),
      fov: mix(left.fov, right.fov, t)
    },
    product: {
      explode: mix(left.explode, right.explode, t),
      bodyOpacity: mix(left.bodyOpacity, right.bodyOpacity, t),
      stemStroke: mix(left.stemStroke, right.stemStroke, t),
      cascadeStage: mix(left.cascadeStage, right.cascadeStage, t)
    },
    light: {
      key: mix(left.keyLight, right.keyLight, t),
      rim: mix(left.rimLight, right.rimLight, t)
    },
    occlusion: mix(left.occlusion, right.occlusion, t)
  };
}

function configureMaterials(root) {
  root.traverse((node) => {
    if (!node.isMesh) return;
    node.frustumCulled = true;
    const sourceMaterials = Array.isArray(node.material)
      ? node.material
      : [node.material];
    const cloned = sourceMaterials.map((source) => {
      const material = source.clone();
      material.metalness = Math.max(material.metalness ?? 0, 0.45);
      material.roughness = Math.max(material.roughness ?? 0.5, 0.32);
      material.envMapIntensity = 0.85;
      material.userData.baseOpacity = material.opacity;
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
      basePosition: node.position.clone()
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

function orientAndFit(root) {
  root.updateMatrixWorld(true);
  let box = new THREE.Box3().setFromObject(root);
  const size = box.getSize(new THREE.Vector3());
  if (size.x > size.y && size.x > size.z) {
    root.rotation.z = Math.PI / 2;
  } else if (size.z > size.y && size.z > size.x) {
    root.rotation.x = -Math.PI / 2;
  }
  root.updateMatrixWorld(true);
  box = new THREE.Box3().setFromObject(root);
  const orientedSize = box.getSize(new THREE.Vector3());
  // Leave enough headroom for the complete product silhouette in both hero
  // shots. Macro shots obtain scale from camera travel, not from cropping the
  // assembly at the viewport edges.
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
    if (!node.isMesh) return;
    const materials = Array.isArray(node.material) ? node.material : [node.material];
    for (const material of materials) {
      const finalOpacity = Math.min(material.userData.baseOpacity ?? 1, opacity);
      material.opacity = finalOpacity;
      material.transparent = finalOpacity < 0.995;
      material.depthWrite = finalOpacity > 0.34;
    }
  });
}

function applyState(state) {
  const up = new THREE.Vector3(0, 1, 0);
  const position = new THREE.Vector3(...state.camera.position);
  const target = new THREE.Vector3(...state.camera.target);
  camera.position.copy(position);
  camera.fov = state.camera.fov;
  camera.up.copy(up);
  camera.lookAt(target);
  camera.rotateZ(THREE.MathUtils.degToRad(state.camera.roll));
  camera.updateProjectionMatrix();

  for (const [name, entry] of groups) {
    const offset = EXPLODE_OFFSETS[name];
    entry.node.position.set(
      entry.basePosition.x + (offset[0] * state.product.explode) / modelScale,
      entry.basePosition.y + (offset[1] * state.product.explode) / modelScale,
      entry.basePosition.z + (offset[2] * state.product.explode) / modelScale
    );
  }

  const stem = groups.get("STEM_CASCADE_PLUG");
  if (stem) {
    stem.node.position.y -= state.product.stemStroke / modelScale;
  }
  setGroupOpacity("VALVE_BODY_BONNET", state.product.bodyOpacity);

  const cascadeGlow = Math.min(1, state.product.cascadeStage / 3);
  const trim = groups.get("CASCADE_TRIM");
  trim?.node.traverse((node) => {
    if (!node.isMesh) return;
    const materials = Array.isArray(node.material) ? node.material : [node.material];
    for (const material of materials) {
      material.emissive?.setRGB(0.18 * cascadeGlow, 0.045 * cascadeGlow, 0.008);
      material.emissiveIntensity = 0.45 * cascadeGlow;
    }
  });

  keyLight.intensity = state.light.key * 2.25;
  rimLight.intensity = state.light.rim * 2.1;
  accentLight.intensity = 2.8 + state.product.cascadeStage * 1.3;
  timelineFill.style.transform = `scaleX(${currentProgress})`;
  updateCopy(state.shot);
}

function updateCopy(shot) {
  if (shot.id === currentShotId) return;
  currentShotId = shot.id;
  const index = cameraPath.shots.findIndex((candidate) => candidate.id === shot.id);
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
  if (frameTimes.length > 900) frameTimes.shift();

  if (playing) {
    const elapsed = (timestamp - playbackStartedAt) / 1000;
    targetProgress = Math.min(1, elapsed / 16);
    currentProgress = targetProgress;
    if (targetProgress >= 1) {
      playing = false;
      playButton.lastChild.textContent = " 重新播放 16 秒 Animatic";
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
    loading.textContent = "六组实时资产已就绪";
    setTimeout(() => {
      loading.style.display = "none";
    }, 1200);
  }

  if (debugEnabled) {
    const sorted = [...frameTimes].sort((a, b) => a - b);
    const percentile = (p) => sorted[Math.floor((sorted.length - 1) * p)] ?? 0;
    debug.value = [
      `shot ${state.shot.id}`,
      `frame ${state.frame.toFixed(1)} / 479`,
      `progress ${currentProgress.toFixed(4)}`,
      `renders ${renderCount}`,
      `usable ${(usableFrameAt - loadStartedAt).toFixed(1)} ms`,
      `p50 ${percentile(0.5).toFixed(2)} ms`,
      `p95 ${percentile(0.95).toFixed(2)} ms`,
      `dpr ${dprCap.toFixed(2)}`
    ].join("\n");
  }

  if (
    playing ||
    Math.abs(targetProgress - currentProgress) > 0.00008
  ) {
    schedule();
  }
}

function schedule() {
  if (scheduled) return;
  scheduled = true;
  requestAnimationFrame(render);
}

function scrollProgress() {
  const rect = story.getBoundingClientRect();
  const travel = story.offsetHeight - innerHeight;
  return THREE.MathUtils.clamp(-rect.top / Math.max(1, travel), 0, 1);
}

function onScroll() {
  if (playing) return;
  targetProgress = scrollProgress();
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

function stateSnapshot() {
  const sampled = samplePath(currentProgress);
  return {
    progress: currentProgress,
    shotId: sampled.shot.id,
    cameraPosition: camera.position.toArray(),
    cameraFov: camera.fov,
    explode: sampled.product.explode,
    bodyOpacity: sampled.product.bodyOpacity,
    stemStroke: sampled.product.stemStroke,
    renderCount,
    usableFrameMs: usableFrameAt ? usableFrameAt - loadStartedAt : null,
    groups: [...groups].map(([name, entry]) => ({
      name,
      position: entry.node.position.toArray()
    }))
  };
}

window.__CONTROL_VALVE_METRICS__ = {
  waitForReady: () => readyPromise,
  setProgressForTest(value) {
    targetProgress = THREE.MathUtils.clamp(value, 0, 1);
    currentProgress = targetProgress;
    const state = samplePath(currentProgress);
    applyState(state);
    renderer.render(scene, camera);
    renderCount += 1;
    return stateSnapshot();
  },
  snapshot: stateSnapshot
};

playButton.addEventListener("click", () => {
  playing = true;
  playbackStartedAt = performance.now();
  currentProgress = 0;
  targetProgress = 0;
  playButton.lastChild.textContent = " 正在播放";
  schedule();
});

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
      loader.loadAsync("./assets/control-valve-shot-ready.glb")
    ]);
    if (!pathResponse.ok) throw new Error(`camera path HTTP ${pathResponse.status}`);
    cameraPath = await pathResponse.json();
    product = gltf.scene;
    product.name = "CONTROL_VALVE_PRODUCT";
    configureMaterials(product);
    findAndCaptureGroups(product);
    orientAndFit(product);
    scene.add(product);
    draco.dispose();
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) {
      targetProgress = 1;
      currentProgress = 1;
    } else {
      targetProgress = scrollProgress();
      currentProgress = targetProgress;
    }
    resize();
    readyResolve({ state: "ready", groups: groups.size });
  } catch (error) {
    loading.textContent = `实时模型不可用：${error.message}`;
    loading.classList.add("is-error");
    console.error(error);
    readyReject(error);
  }
}

start();
