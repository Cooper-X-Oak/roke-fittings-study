import * as THREE from "three";
import { GLTFLoader } from "./assets/vendor/three/loaders/GLTFLoader.js";
import { DRACOLoader } from "./assets/vendor/three/loaders/DRACOLoader.js";
import { KTX2Loader } from "./assets/vendor/three/loaders/KTX2Loader.js";
import { RoomEnvironment } from "./assets/vendor/three/environments/RoomEnvironment.js";
import { createStoryController } from "./story-engine.mjs";
import {
  progressFromDocument,
  stageAtProgress,
} from "./story-math.mjs";

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
const occlusionElement = document.querySelector("#camera-occlusion");
const firstShotPoster = document.querySelector("#first-shot-poster");
const chapters = [...document.querySelectorAll("[data-stage]")];

const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
const desktopLayout = window.matchMedia("(min-width: 900px)");
const query = new URLSearchParams(window.location.search);

let renderer;
let scene;
let camera;
let controller;
let manifest;
let cameraPath;
let modelResourceURL;
let motionLocked = false;
let firstUsableFrameMs = null;
let lastRendererSnapshot = null;
let manifestReadyMs = null;
let modelDecodedMs = null;
let shaderCompiledMs = null;
let posterDecodedMs = null;

firstShotPoster?.decode().then(() => {
  posterDecodedMs = Number(performance.now().toFixed(3));
  performance.mark("car-story-poster-decoded");
}).catch(() => {
  // A failed poster decode must not prevent the existing WebGL/fallback routes.
});

function percentile(values, percentage) {
  if (!values.length) {
    return null;
  }
  const sorted = [...values].sort((left, right) => left - right);
  const index = Math.min(
    sorted.length - 1,
    Math.max(0, Math.ceil((percentage / 100) * sorted.length) - 1),
  );
  return Number(sorted[index].toFixed(3));
}

function plainRendererInfo(info) {
  return {
    memory: {
      geometries: info.memory.geometries,
      textures: info.memory.textures,
    },
    render: {
      calls: info.render.calls,
      triangles: info.render.triangles,
      points: info.render.points,
      lines: info.render.lines,
    },
    programs: info.programs?.length ?? null,
  };
}

function getWebGLDetails() {
  if (!renderer) {
    return null;
  }
  const context = renderer.getContext();
  const debug = context.getExtension("WEBGL_debug_renderer_info");
  return {
    vendor: debug
      ? context.getParameter(debug.UNMASKED_VENDOR_WEBGL)
      : "unavailable",
    renderer: debug
      ? context.getParameter(debug.UNMASKED_RENDERER_WEBGL)
      : "unavailable",
    version: context.getParameter(context.VERSION),
  };
}

function getModelResourceTiming() {
  if (!modelResourceURL) {
    return null;
  }
  const entry = performance
    .getEntriesByName(modelResourceURL, "resource")
    .at(-1);
  if (!entry) {
    return null;
  }
  return {
    name: entry.name,
    durationMs: Number(entry.duration.toFixed(3)),
    transferSize: entry.transferSize,
    encodedBodySize: entry.encodedBodySize,
    decodedBodySize: entry.decodedBodySize,
    responseEndMs: Number(entry.responseEnd.toFixed(3)),
  };
}

function getMemorySnapshot() {
  if (!performance.memory) {
    return {
      available: false,
      reason: "performance.memory is not exposed by this browser",
    };
  }
  return {
    available: true,
    usedJSHeapSize: performance.memory.usedJSHeapSize,
    totalJSHeapSize: performance.memory.totalJSHeapSize,
    jsHeapSizeLimit: performance.memory.jsHeapSizeLimit,
  };
}

const supportedPerformanceEntries =
  PerformanceObserver.supportedEntryTypes ?? [];
const measurement = {
  active: false,
  label: null,
  context: {},
  startedAt: null,
  initialRenderCount: 0,
  frameIntervals: [],
  renderDurations: [],
  longAnimationFrames: [],
  longTasks: [],
};

let readyResolver;
const readyPromise = new Promise((resolve) => {
  readyResolver = resolve;
});

function startRun(label = "scroll-story", context = {}) {
  measurement.active = true;
  measurement.label = label;
  measurement.context = { ...context };
  measurement.startedAt = performance.now();
  measurement.initialRenderCount = controller?.getState().renderCount ?? 0;
  measurement.frameIntervals.length = 0;
  measurement.renderDurations.length = 0;
  measurement.longAnimationFrames.length = 0;
  measurement.longTasks.length = 0;
  return {
    label,
    startedAt: measurement.startedAt,
    renderCount: measurement.initialRenderCount,
  };
}

function finishRun(extra = {}) {
  const finishedAt = performance.now();
  const intervals = [...measurement.frameIntervals];
  const durations = [...measurement.renderDurations];
  const over16 = intervals.filter((value) => value > 16.7).length;
  const over33 = intervals.filter((value) => value > 33.3).length;
  const renderCount = controller?.getState().renderCount ?? 0;
  const navigation = performance.getEntriesByType("navigation")[0];

  const result = {
    schemaVersion: "1.0.0",
    label: measurement.label,
    environment: {
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight,
      },
      devicePixelRatio: window.devicePixelRatio,
      userAgent: navigator.userAgent,
      hardwareConcurrency: navigator.hardwareConcurrency ?? null,
      deviceMemoryGiB: navigator.deviceMemory ?? null,
      cacheState: measurement.context.cacheState ?? "not-recorded",
      webgl: getWebGLDetails(),
    },
    loading: {
      posterDecodedMs,
      firstUsableProductFrameMs: firstUsableFrameMs,
      phaseMilestonesMs: {
        manifestReady: manifestReadyMs,
        modelDecoded: modelDecodedMs,
        shaderCompiled: shaderCompiledMs,
        firstUsableProductFrame: firstUsableFrameMs,
      },
      navigation: navigation
        ? {
            domContentLoadedMs: Number(
              navigation.domContentLoadedEventEnd.toFixed(3),
            ),
            loadEventEndMs: Number(navigation.loadEventEnd.toFixed(3)),
          }
        : null,
      modelResource: getModelResourceTiming(),
    },
    runtime: {
      measurementDurationMs: Number(
        (finishedAt - measurement.startedAt).toFixed(3),
      ),
      measuredRendererFrames: intervals.length,
      rendererFramesDuringRun:
        renderCount - measurement.initialRenderCount,
      frameIntervalMs: {
        p50: percentile(intervals, 50),
        p95: percentile(intervals, 95),
        max: intervals.length
          ? Number(Math.max(...intervals).toFixed(3))
          : null,
      },
      frameIntervalOver16_7Ms: {
        count: over16,
        ratio: intervals.length
          ? Number((over16 / intervals.length).toFixed(5))
          : null,
      },
      frameIntervalOver33_3Ms: {
        count: over33,
        ratio: intervals.length
          ? Number((over33 / intervals.length).toFixed(5))
          : null,
      },
      renderCpuDurationMs: {
        p50: percentile(durations, 50),
        p95: percentile(durations, 95),
        max: durations.length
          ? Number(Math.max(...durations).toFixed(3))
          : null,
      },
      idleRendererFramesAfterSettle:
        extra.idleRendererFramesAfterSettle ?? null,
      renderer: lastRendererSnapshot,
    },
    browserSignals: {
      longAnimationFrame: supportedPerformanceEntries.includes(
        "long-animation-frame",
      )
        ? {
            available: true,
            count: measurement.longAnimationFrames.length,
            totalDurationMs: Number(
              measurement.longAnimationFrames
                .reduce((total, entry) => total + entry.duration, 0)
                .toFixed(3),
            ),
            maxDurationMs: measurement.longAnimationFrames.length
              ? Number(
                  Math.max(
                    ...measurement.longAnimationFrames.map(
                      (entry) => entry.duration,
                    ),
                  ).toFixed(3),
                )
              : 0,
          }
        : {
            available: false,
            reason: "long-animation-frame is not supported",
          },
      mainThreadLongTask: supportedPerformanceEntries.includes("longtask")
        ? {
            available: true,
            count: measurement.longTasks.length,
            totalDurationMs: Number(
              measurement.longTasks
                .reduce((total, entry) => total + entry.duration, 0)
                .toFixed(3),
            ),
            maxDurationMs: measurement.longTasks.length
              ? Number(
                  Math.max(
                    ...measurement.longTasks.map((entry) => entry.duration),
                  ).toFixed(3),
                )
              : 0,
          }
        : {
            available: false,
            reason: "longtask is not supported",
          },
      memory: getMemorySnapshot(),
    },
    story: {
      stage: body.dataset.storyStage,
      progress: controller?.getState().currentProgress ?? null,
      groups: controller?.getState().resolvedGroups ?? [],
    },
    ...extra,
  };

  measurement.active = false;
  return result;
}

if (supportedPerformanceEntries.includes("long-animation-frame")) {
  const observer = new PerformanceObserver((list) => {
    if (!measurement.active) {
      return;
    }
    for (const entry of list.getEntries()) {
      measurement.longAnimationFrames.push({
        startTime: entry.startTime,
        duration: entry.duration,
        blockingDuration: entry.blockingDuration ?? null,
      });
    }
  });
  observer.observe({ type: "long-animation-frame", buffered: false });
}

if (supportedPerformanceEntries.includes("longtask")) {
  const observer = new PerformanceObserver((list) => {
    if (!measurement.active) {
      return;
    }
    for (const entry of list.getEntries()) {
      measurement.longTasks.push({
        startTime: entry.startTime,
        duration: entry.duration,
      });
    }
  });
  observer.observe({ type: "longtask", buffered: false });
}

function wait(milliseconds) {
  return new Promise((resolve) => {
    setTimeout(resolve, milliseconds);
  });
}

async function waitForSettled(timeoutMs = 5000) {
  const startedAt = performance.now();
  while (performance.now() - startedAt < timeoutMs) {
    const state = controller?.getState();
    if (
      state &&
      !state.scheduled &&
      Math.abs(state.currentProgress - state.targetProgress) < 0.0004
    ) {
      return state;
    }
    await wait(25);
  }
  throw new Error("Timed out while waiting for the product story to settle.");
}

async function runScrollBenchmark({
  durationMs = 4200,
  idleMs = 1200,
  label = "desktop-scroll-story",
  cacheState = "not-recorded",
} = {}) {
  await readyPromise;
  if (!controller || body.dataset.webglState !== "ready") {
    throw new Error("The realtime product story is not ready.");
  }

  const scrollTravel = Math.max(
    1,
    document.documentElement.scrollHeight - window.innerHeight,
  );
  const originalScrollBehavior =
    document.documentElement.style.scrollBehavior;
  document.documentElement.style.scrollBehavior = "auto";
  window.scrollTo({ top: 0, behavior: "instant" });
  controller.setProgress(0, { immediate: true });
  updateStoryUI(0);
  await wait(120);
  startRun(label, { cacheState });

  const startedAt = performance.now();
  await new Promise((resolve) => {
    function advance(now) {
      const linear = Math.min(1, (now - startedAt) / durationMs);
      const eased =
        linear < 0.5
          ? 2 * linear * linear
          : 1 - Math.pow(-2 * linear + 2, 2) / 2;
      window.scrollTo({
        top: scrollTravel * eased,
        behavior: "instant",
      });
      if (linear < 1) {
        requestAnimationFrame(advance);
      } else {
        resolve();
      }
    }
    requestAnimationFrame(advance);
  });

  await waitForSettled();
  const settledRenderCount = controller.getState().renderCount;
  await wait(idleMs);
  const idleRendererFramesAfterSettle =
    controller.getState().renderCount - settledRenderCount;
  document.documentElement.style.scrollBehavior = originalScrollBehavior;

  return finishRun({
    benchmark: {
      requestedScrollDurationMs: durationMs,
      idleObservationMs: idleMs,
    },
    idleRendererFramesAfterSettle,
  });
}

window.__CAR_STORY_METRICS__ = {
  schemaVersion: "1.0.0",
  waitForReady: () => readyPromise,
  startRun,
  finishRun,
  waitForSettled,
  runScrollBenchmark,
  setProgressForTest: (progress) => {
    if (!controller) {
      throw new Error("The realtime product story is not ready.");
    }
    controller.setProgress(progress, { immediate: true });
    updateStoryUI(progress);
    return controller.getTransformSnapshot();
  },
  transformSnapshot: () => controller?.getTransformSnapshot() ?? null,
  snapshot: () => ({
    pageState: body.dataset.webglState,
    stage: body.dataset.storyStage,
    firstUsableProductFrameMs: firstUsableFrameMs,
    controller: controller?.getState() ?? null,
    renderer: lastRendererSnapshot,
  }),
};

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
    if (!context) {
      return false;
    }
    context.getExtension("WEBGL_lose_context")?.loseContext();
    return true;
  } catch {
    return false;
  }
}

function pageProgress() {
  return progressFromDocument(
    window.scrollY,
    document.documentElement.scrollHeight,
    window.innerHeight,
  );
}

function motionIsEnabled() {
  return !motionLocked && !reducedMotion.matches && desktopLayout.matches;
}

function updateMotionLabel() {
  const systemLocked = reducedMotion.matches || !desktopLayout.matches;
  motionToggle.hidden =
    systemLocked || body.dataset.webglState !== "ready";
  motionToggle.setAttribute("aria-pressed", String(motionLocked));
  motionToggle.textContent = motionLocked
    ? "恢复滚动视图"
    : "固定最终视图";

  if (reducedMotion.matches && body.dataset.webglState === "ready") {
    runtimeStatus.textContent = "已响应减少动态偏好：显示最终装配视图";
  }
}

function updateStoryUI(progress) {
  const percent = Math.round(progress * 100);
  storyProgress.value = percent;
  storyProgress.textContent = `${percent}%`;
  progressOutput.value = String(percent).padStart(2, "0");
  progressOutput.textContent = String(percent).padStart(2, "0");

  if (!manifest) {
    return;
  }
  const stage = stageAtProgress(manifest.story.stages, progress);
  chapters.forEach((chapter) => {
    chapter.toggleAttribute(
      "data-active",
      chapter.dataset.stage === stage.id,
    );
  });
}

function addEnvironment() {
  const pmrem = new THREE.PMREMGenerator(renderer);
  const room = new RoomEnvironment();
  const environment = pmrem.fromScene(room, 0.04);
  scene.environment = environment.texture;
  room.dispose();
  pmrem.dispose();

  const key = new THREE.DirectionalLight(0xffd8cf, 2.4);
  key.position.set(6, 9, 5);
  scene.add(key);

  const rim = new THREE.DirectionalLight(0x8ebfff, 1.8);
  rim.position.set(-6, 4, -4);
  scene.add(rim);

  const accent = new THREE.PointLight(0xe51d32, 13, 12, 2);
  accent.position.set(-2.8, 1.8, 3.7);
  scene.add(accent);

  return { key, rim, accent };
}

function frameAsset(asset) {
  const bounds = new THREE.Box3().setFromObject(asset);
  const size = bounds.getSize(new THREE.Vector3());

  const presentationRoot = new THREE.Group();
  const transform = manifest.story.canonicalModelTransform;
  presentationRoot.position.set(...transform.position);
  presentationRoot.rotation.set(...transform.rotation);
  presentationRoot.scale.set(...transform.scale);
  presentationRoot.add(asset);
  scene.add(presentationRoot);

  let meshCount = 0;
  asset.traverse((object) => {
    if (!object.isMesh) {
      return;
    }
    meshCount += 1;
    object.castShadow = false;
    object.receiveShadow = false;
  });

  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(30, 30),
    new THREE.ShadowMaterial({
      color: 0x1f2326,
      opacity: 0.14,
    }),
  );
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = -0.17;
  ground.receiveShadow = true;
  scene.add(ground);

  partCount.textContent = `${manifest.groups.length} GROUPS`;
  return { presentationRoot, meshCount };
}

function onResize() {
  if (!renderer || !camera) {
    return;
  }
  const width = window.innerWidth;
  const height = window.innerHeight;
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.25) * 0.85);
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  controller?.invalidate("resize");
  updateMotionLabel();
}

function applyScrollState({ immediate = false } = {}) {
  const progress = pageProgress();
  updateStoryUI(progress);
  if (!controller) {
    return;
  }
  const storyProgressValue = motionIsEnabled() ? progress : 1;
  controller.setProgress(storyProgressValue, { immediate });
}

function fail(message, detail) {
  controller?.dispose();
  fallbackCopy.textContent = detail;
  rendererStatus.textContent = "FALLBACK";
  setState("error", message);
  updateMotionLabel();
  readyResolver({ state: "error", message });
}

async function initialize() {
  if (query.has("fallback") || query.has("disable-webgl")) {
    setState("fallback", "已启用可验证的静态回退状态");
    rendererStatus.textContent = "FORCED FALLBACK";
    fallbackCopy.textContent =
      "这是通过查询参数启用的可验证回退状态。产品结构、压缩数据和许可证信息仍保持可读。";
    readyResolver({ state: "fallback" });
    return;
  }

  if (!supportsWebGL2()) {
    setState("fallback", "当前浏览器或 GPU 不支持 WebGL 2");
    rendererStatus.textContent = "UNSUPPORTED";
    readyResolver({ state: "fallback" });
    return;
  }

  try {
    const manifestResponse = await fetch("./product-story.json");
    if (!manifestResponse.ok) {
      throw new Error(
        `Product story manifest returned ${manifestResponse.status}.`,
      );
    }
    manifest = await manifestResponse.json();
    const cameraPathResponse = await fetch(manifest.story.cameraPathUri);
    if (!cameraPathResponse.ok) {
      throw new Error(`Camera path returned ${cameraPathResponse.status}.`);
    }
    cameraPath = await cameraPathResponse.json();
    manifestReadyMs = Number(performance.now().toFixed(3));
    updateStoryUI(pageProgress());

    renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: false,
      alpha: false,
      powerPreference: "high-performance",
    });
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.08;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFShadowMap;

    scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf1f1ef);
    camera = new THREE.PerspectiveCamera(38, 1, 0.025, 100);
    const initialCamera = cameraPath.keyframes[0];
    camera.position.set(...initialCamera.position);
    camera.lookAt(...initialCamera.target);

    const lights = addEnvironment();
    onResize();

    const dracoLoader = new DRACOLoader();
    dracoLoader.setDecoderPath(
      new URL("./assets/vendor/three/libs/draco/", import.meta.url).href,
    );
    dracoLoader.setDecoderConfig({ type: "wasm" });

    const ktx2Loader = new KTX2Loader();
    ktx2Loader.setTranscoderPath(
      new URL("./assets/vendor/three/libs/basis/", import.meta.url).href,
    );
    ktx2Loader.detectSupport(renderer);

    const loader = new GLTFLoader();
    loader.setDRACOLoader(dracoLoader);
    loader.setKTX2Loader(ktx2Loader);

    modelResourceURL = new URL(
      query.has("fail-model") ? "./missing-model.glb" : manifest.model.uri,
      import.meta.url,
    ).href;

    const gltf = await loader.loadAsync(modelResourceURL, (event) => {
      if (!event.total) {
        return;
      }
      const percent = Math.min(
        99,
        Math.round((event.loaded / event.total) * 100),
      );
      loadingPercent.textContent = `${String(percent).padStart(2, "0")}%`;
      runtimeStatus.textContent = `正在加载压缩样机 ${percent}%`;
    });
    modelDecodedMs = Number(performance.now().toFixed(3));

    const { presentationRoot, meshCount } = frameAsset(gltf.scene);
    await renderer.compileAsync(scene, camera);
    shaderCompiledMs = Number(performance.now().toFixed(3));

    controller = createStoryController({
      root: presentationRoot,
      associations: gltf.parser.associations,
      camera,
      renderer,
      scene,
      manifest,
      cameraPath,
      lights,
      occlusionElement,
      onStageChange(stage) {
        body.dataset.storyStage = stage.id;
      },
      onRender(event) {
        lastRendererSnapshot = plainRendererInfo(event.rendererInfo);
        if (firstUsableFrameMs === null) {
          firstUsableFrameMs = Number(performance.now().toFixed(3));
          performance.mark("car-story-first-usable-frame");
          body.dataset.productFrame = "ready";
        }
        if (measurement.active) {
          if (event.interval !== null) {
            measurement.frameIntervals.push(event.interval);
          }
          measurement.renderDurations.push(event.renderDuration);
        }
      },
    });

    applyScrollState({ immediate: true });
    loadingPercent.textContent = "100%";
    setState(
      "ready",
      `数字样机已就绪；${meshCount} 个网格由滚动按需驱动`,
    );
    rendererStatus.textContent = "WEBGL2 · DEMAND";
    updateMotionLabel();

    window.addEventListener(
      "scroll",
      () => applyScrollState(),
      { passive: true },
    );
    window.addEventListener("resize", onResize, { passive: true });
    reducedMotion.addEventListener("change", () => {
      updateMotionLabel();
      applyScrollState({ immediate: true });
    });
    desktopLayout.addEventListener("change", () => {
      updateMotionLabel();
      applyScrollState({ immediate: true });
    });
    motionToggle.addEventListener("click", () => {
      motionLocked = !motionLocked;
      updateMotionLabel();
      applyScrollState({ immediate: true });
      runtimeStatus.textContent = motionLocked
        ? "已固定最终装配视图"
        : "数字样机已恢复滚动驱动";
    });

    canvas.addEventListener(
      "webglcontextlost",
      (event) => {
        event.preventDefault();
        fail(
          "WebGL 上下文已丢失",
          "GPU 渲染上下文已中断。请重新载入页面；产品结构与资产来源仍可阅读。",
        );
      },
      false,
    );

    dracoLoader.dispose();
    ktx2Loader.dispose();
    readyResolver({ state: "ready" });
  } catch (error) {
    console.error(error);
    fail(
      "压缩样机加载失败",
      "产品语义清单、GLB 或本地解码器未能完成加载。请重新载入页面；产品说明、压缩数据和模型来源仍保持可读。",
    );
  }
}

initialize();
