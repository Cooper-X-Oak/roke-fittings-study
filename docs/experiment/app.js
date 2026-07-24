import * as THREE from "three";
import { GLTFLoader } from "./assets/vendor/three/loaders/GLTFLoader.js";
import { DRACOLoader } from "./assets/vendor/three/loaders/DRACOLoader.js";
import { KTX2Loader } from "./assets/vendor/three/loaders/KTX2Loader.js";
import { RoomEnvironment } from "./assets/vendor/three/environments/RoomEnvironment.js";

const canvas = document.querySelector("#webgl-canvas");
const body = document.body;
const storyProgress = document.querySelector("#story-progress");
const progressOutput = document.querySelector("#progress-output");
const loadingPercent = document.querySelector("#loading-percent");
const runtimeStatus = document.querySelector("#runtime-status-copy");
const rendererStatus = document.querySelector("#renderer-status");
const partCount = document.querySelector("#part-count");
const fallbackCopy = document.querySelector("#fallback-copy");
const motionToggle = document.querySelector("#motion-toggle");
const chapters = [...document.querySelectorAll("[data-chapter]")];

const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
const desktopLayout = window.matchMedia("(min-width: 900px)");
const query = new URLSearchParams(window.location.search);

let renderer;
let scene;
let camera;
let modelPivot;
let movableParts = [];
let animationFrame = 0;
let targetProgress = 0;
let renderedProgress = 0;
let motionPaused = false;
let lastFrameTime = performance.now();
let fpsWindowStart = lastFrameTime;
let fpsFrames = 0;

function setState(state, message) {
  body.dataset.webglState = state;
  runtimeStatus.textContent = message;
}

function supportsWebGL2() {
  try {
    const probe = document.createElement("canvas");
    const context = probe.getContext("webgl2", {
      failIfMajorPerformanceCaveat: true,
    });
    if (!context) return false;
    context.getExtension("WEBGL_lose_context")?.loseContext();
    return true;
  } catch {
    return false;
  }
}

function clamp01(value) {
  return Math.min(1, Math.max(0, value));
}

function smoothstep(min, max, value) {
  const normalized = clamp01((value - min) / (max - min));
  return normalized * normalized * (3 - 2 * normalized);
}

function damp(current, target, smoothing, deltaSeconds) {
  return THREE.MathUtils.lerp(
    current,
    target,
    1 - Math.exp(-smoothing * deltaSeconds),
  );
}

function pageProgress() {
  const scrollable = document.documentElement.scrollHeight - window.innerHeight;
  return scrollable > 0 ? clamp01(window.scrollY / scrollable) : 0;
}

function motionIsEnabled() {
  return !motionPaused && !reducedMotion.matches && desktopLayout.matches;
}

function updateMotionLabel() {
  const systemPaused = reducedMotion.matches || !desktopLayout.matches;
  motionToggle.hidden = systemPaused || body.dataset.webglState !== "ready";
  motionToggle.setAttribute("aria-pressed", String(motionPaused));
  motionToggle.textContent = motionPaused ? "继续动态" : "暂停动态";

  if (reducedMotion.matches && body.dataset.webglState === "ready") {
    runtimeStatus.textContent = "系统已启用减少动态：保持装配检查视角";
  }
}

function updateStoryUI(progress) {
  const percent = Math.round(progress * 100);
  storyProgress.value = percent;
  storyProgress.textContent = `${percent}%`;
  progressOutput.value = String(percent).padStart(2, "0");
  progressOutput.textContent = String(percent).padStart(2, "0");

  const activeIndex = Math.min(
    chapters.length - 1,
    Math.floor(progress * chapters.length),
  );
  chapters.forEach((chapter, index) => {
    chapter.toggleAttribute("data-active", index === activeIndex);
  });
}

function semanticDirection(name, direction) {
  const normalizedName = name.toLowerCase();

  if (normalizedName.includes("roof")) direction.y += 0.9;
  if (normalizedName.includes("hood")) {
    direction.y += 0.45;
    direction.z += 0.65;
  }
  if (normalizedName.includes("engine")) direction.y += 0.8;
  if (normalizedName.includes("interior")) direction.y += 0.34;
  if (normalizedName.includes("wheel")) direction.x *= 1.75;
  if (normalizedName.includes("door")) direction.x *= 1.45;
  if (normalizedName.includes("rear")) direction.z -= 0.35;
  if (normalizedName.includes("front")) direction.z += 0.35;

  if (direction.lengthSq() < 0.06) {
    const hash = [...name].reduce(
      (total, character) => total + character.charCodeAt(0),
      0,
    );
    direction.set(
      hash % 2 === 0 ? 1 : -1,
      0.42 + ((hash >> 1) % 3) * 0.18,
      hash % 3 === 0 ? 0.7 : -0.7,
    );
  }

  return direction.normalize();
}

function prepareExplodedView(asset, center, modelSize) {
  const assemblyRoot = asset.getObjectByName("BodyUnderside");
  if (!assemblyRoot || assemblyRoot.children.length === 0) return [];

  asset.updateMatrixWorld(true);
  const modelCenterWorld = center.clone();
  asset.localToWorld(modelCenterWorld);
  const largestDimension = Math.max(modelSize.x, modelSize.y, modelSize.z);

  return assemblyRoot.children.map((part, index) => {
    const bounds = new THREE.Box3().setFromObject(part);
    const partCenterWorld = bounds.getCenter(new THREE.Vector3());
    const partSize = bounds.getSize(new THREE.Vector3());
    const direction = semanticDirection(
      part.name || `part-${index}`,
      partCenterWorld.clone().sub(modelCenterWorld),
    );

    const relativeSize = clamp01(partSize.length() / largestDimension);
    const distance =
      largestDimension * (0.09 + relativeSize * 0.18) *
      (part.name.toLowerCase().includes("wheel") ? 1.2 : 1);
    const worldOffset = direction.multiplyScalar(distance);

    const parent = part.parent;
    const localOrigin = parent.worldToLocal(partCenterWorld.clone());
    const localDestination = parent.worldToLocal(
      partCenterWorld.clone().add(worldOffset),
    );

    return {
      object: part,
      basePosition: part.position.clone(),
      offset: localDestination.sub(localOrigin),
    };
  });
}

function addLighting() {
  const pmrem = new THREE.PMREMGenerator(renderer);
  const room = new RoomEnvironment();
  scene.environment = pmrem.fromScene(room, 0.04).texture;
  room.dispose();
  pmrem.dispose();

  const key = new THREE.DirectionalLight(0xffffff, 3.2);
  key.position.set(6, 9, 5);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  key.shadow.camera.left = -7;
  key.shadow.camera.right = 7;
  key.shadow.camera.top = 7;
  key.shadow.camera.bottom = -7;
  key.shadow.camera.near = 0.1;
  key.shadow.camera.far = 30;
  key.shadow.bias = -0.00035;
  scene.add(key);

  const rim = new THREE.DirectionalLight(0xc7d6e6, 1.35);
  rim.position.set(-6, 4, -4);
  scene.add(rim);

  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(30, 30),
    new THREE.ShadowMaterial({
      color: 0x1f2326,
      opacity: 0.16,
    }),
  );
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = -0.81;
  ground.receiveShadow = true;
  scene.add(ground);
}

function frameModel(asset) {
  const bounds = new THREE.Box3().setFromObject(asset);
  const center = bounds.getCenter(new THREE.Vector3());
  const size = bounds.getSize(new THREE.Vector3());

  asset.position.sub(center);
  asset.updateMatrixWorld(true);

  modelPivot = new THREE.Group();
  modelPivot.scale.setScalar(1.08);
  modelPivot.position.set(1.25, -0.12, 0);
  modelPivot.rotation.y = -0.62;
  modelPivot.add(asset);
  scene.add(modelPivot);

  asset.traverse((object) => {
    if (!object.isMesh) return;
    object.castShadow = true;
    object.receiveShadow = true;
  });

  movableParts = prepareExplodedView(asset, new THREE.Vector3(), size);
  partCount.textContent = `${movableParts.length} 组`;
}

function updateModel(progress) {
  if (!modelPivot) return;

  const rotation = smoothstep(0.02, 0.48, progress);
  const explode = smoothstep(0.34, 0.8, progress);
  const settle = smoothstep(0.78, 1, progress);
  const enter = smoothstep(0.015, 0.22, progress);
  const inspectionScale = THREE.MathUtils.lerp(1.08, 1.18, enter);
  const finalScale = THREE.MathUtils.lerp(inspectionScale, 0.92, explode);

  modelPivot.rotation.y =
    -0.62 + rotation * Math.PI * 1.18 + settle * Math.PI * 0.12;
  modelPivot.rotation.x = 0.025 + Math.sin(progress * Math.PI) * 0.035;
  modelPivot.scale.setScalar(finalScale);
  modelPivot.position.x = THREE.MathUtils.lerp(1.25, 0, enter);
  modelPivot.position.y =
    THREE.MathUtils.lerp(-0.12, 0.06, enter) +
    Math.sin(progress * Math.PI) * 0.06;

  movableParts.forEach(({ object, basePosition, offset }) => {
    object.position.copy(basePosition).addScaledVector(offset, explode);
  });

  const cameraShift = smoothstep(0.18, 0.9, progress);
  camera.position.set(
    THREE.MathUtils.lerp(6.4, 6.2, cameraShift),
    THREE.MathUtils.lerp(3.15, 3.9, cameraShift),
    THREE.MathUtils.lerp(7.8, 10.5, cameraShift),
  );
  camera.lookAt(0, 0.08, 0);
}

function onResize() {
  if (!renderer || !camera) return;
  const width = window.innerWidth;
  const height = window.innerHeight;
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.8));
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  updateMotionLabel();
}

function animate(now) {
  const delta = Math.min((now - lastFrameTime) / 1000, 0.1);
  lastFrameTime = now;

  targetProgress = pageProgress();
  const modelTarget = motionIsEnabled() ? targetProgress : 0.115;
  renderedProgress = damp(renderedProgress, modelTarget, 8.5, delta);

  updateStoryUI(targetProgress);
  updateModel(renderedProgress);
  renderer.render(scene, camera);

  animationFrame = requestAnimationFrame(animate);
}

function fail(message, detail) {
  cancelAnimationFrame(animationFrame);
  fallbackCopy.textContent = detail;
  rendererStatus.textContent = "FALLBACK";
  setState("error", message);
  updateMotionLabel();
}

async function initialize() {
  if (query.has("fallback")) {
    setState("fallback", "已启用可验证的 WebGL 回退状态");
    rendererStatus.textContent = "FORCED FALLBACK";
    fallbackCopy.textContent =
      "这是通过 ?fallback=1 启用的可验证回退状态。实验说明、压缩数据和许可证信息仍保持可读。";
    return;
  }

  if (!supportsWebGL2()) {
    setState("fallback", "当前浏览器或 GPU 不支持 WebGL 2");
    rendererStatus.textContent = "UNSUPPORTED";
    return;
  }

  try {
    renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: false,
      powerPreference: "high-performance",
    });
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.08;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf1f1ef);
    camera = new THREE.PerspectiveCamera(28, 1, 0.1, 100);
    camera.position.set(6.4, 3.15, 7.8);
    camera.lookAt(0, 0.08, 0);

    addLighting();
    onResize();

    const dracoLoader = new DRACOLoader();
    dracoLoader.setDecoderPath(
      new URL(
        "./assets/vendor/three/libs/draco/",
        import.meta.url,
      ).href,
    );
    dracoLoader.setDecoderConfig({ type: "wasm" });

    const ktx2Loader = new KTX2Loader();
    ktx2Loader.setTranscoderPath(
      new URL(
        "./assets/vendor/three/libs/basis/",
        import.meta.url,
      ).href,
    );
    ktx2Loader.detectSupport(renderer);

    const loader = new GLTFLoader();
    loader.setDRACOLoader(dracoLoader);
    loader.setKTX2Loader(ktx2Loader);

    const modelURL = new URL(
      "./assets/models/car-concept-web.glb",
      import.meta.url,
    ).href;

    const gltf = await loader.loadAsync(modelURL, (event) => {
      if (!event.total) return;
      const percent = Math.min(99, Math.round((event.loaded / event.total) * 100));
      loadingPercent.textContent = `${String(percent).padStart(2, "0")}%`;
      runtimeStatus.textContent = `正在加载压缩样机 ${percent}%`;
    });

    frameModel(gltf.scene);
    await renderer.compileAsync(scene, camera);

    loadingPercent.textContent = "100%";
    setState("ready", "实时样机已就绪；滚动控制旋转与拆解");
    rendererStatus.textContent = "WEBGL2 · ACTIVE";
    motionToggle.hidden = false;
    updateMotionLabel();

    window.addEventListener("resize", onResize, { passive: true });
    reducedMotion.addEventListener("change", updateMotionLabel);
    desktopLayout.addEventListener("change", updateMotionLabel);
    motionToggle.addEventListener("click", () => {
      motionPaused = !motionPaused;
      updateMotionLabel();
      runtimeStatus.textContent = motionPaused
        ? "滚动动态已暂停；样机保持装配检查视角"
        : "实时样机已就绪；滚动控制旋转与拆解";
    });

    canvas.addEventListener(
      "webglcontextlost",
      (event) => {
        event.preventDefault();
        fail(
          "WebGL 上下文已丢失",
          "GPU 渲染上下文已中断。请重新载入页面以恢复三维实验；说明与模型来源仍可阅读。",
        );
      },
      false,
    );

    lastFrameTime = performance.now();
    fpsWindowStart = lastFrameTime;
    animationFrame = requestAnimationFrame(animate);
  } catch (error) {
    console.error(error);
    fail(
      "压缩样机加载失败",
      "本地 GLB 或解码器未能完成加载。请重新载入页面；实验说明、压缩数据和模型来源仍保持可读。",
    );
  }
}

initialize();
