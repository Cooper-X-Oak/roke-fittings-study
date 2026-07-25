import * as THREE from "three";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { KTX2Loader } from "three/addons/loaders/KTX2Loader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";

import { createStoryController } from "./story-engine.mjs";

const storySection = document.querySelector("[data-product-story]");
const canvas = document.querySelector("[data-story-canvas]");
const content = {
  eyebrow: document.querySelector("[data-stage-eyebrow]"),
  title: document.querySelector("[data-stage-title]"),
  body: document.querySelector("[data-stage-body]"),
  cta: document.querySelector("[data-stage-cta]"),
};
const status = document.querySelector("[data-story-status]");

function showStage(stage) {
  content.eyebrow.textContent = stage.content.eyebrow;
  content.title.textContent = stage.content.title;
  content.body.textContent = stage.content.body;
  if (stage.content.cta) {
    content.cta.textContent = stage.content.cta.label;
    content.cta.href = stage.content.cta.href;
    content.cta.hidden = false;
  } else {
    content.cta.hidden = true;
  }
}

function scrollProgress() {
  const bounds = storySection.getBoundingClientRect();
  const distance = Math.max(1, storySection.offsetHeight - innerHeight);
  return Math.min(1, Math.max(0, -bounds.top / distance));
}

async function loadStory() {
  const manifestUrl = storySection.dataset.manifest;
  const response = await fetch(manifestUrl);
  if (!response.ok) {
    throw new Error(`Story manifest failed with HTTP ${response.status}`);
  }
  const manifest = await response.json();
  if (manifest.fallback.poster) {
    storySection.style.setProperty(
      "--product-poster",
      `url("${manifest.fallback.poster}")`,
    );
  }

  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: true,
    alpha: true,
    powerPreference: "high-performance",
  });
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.75));

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(34, 1, 0.01, 10000);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x30343b, 2.1));
  const key = new THREE.DirectionalLight(0xffffff, 2.8);
  key.position.set(3, 5, 4);
  scene.add(key);

  const loader = new GLTFLoader();
  const draco = new DRACOLoader();
  draco.setDecoderPath(storySection.dataset.dracoPath);
  loader.setDRACOLoader(draco);
  const ktx2 = new KTX2Loader();
  ktx2.setTranscoderPath(storySection.dataset.ktx2Path);
  ktx2.detectSupport(renderer);
  loader.setKTX2Loader(ktx2);
  loader.setMeshoptDecoder(MeshoptDecoder);

  const gltf = await loader.loadAsync(manifest.model.uri);
  const root = gltf.scene;
  scene.add(root);

  const controller = createStoryController({
    root,
    associations: gltf.parser.associations,
    camera,
    renderer,
    scene,
    manifest,
    onStageChange: showStage,
  });

  function resize() {
    const width = Math.max(1, canvas.clientWidth);
    const height = Math.max(1, canvas.clientHeight);
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    controller.renderNow();
  }

  const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
  function updateProgress() {
    controller.setProgress(reducedMotion.matches ? 1 : scrollProgress(), {
      immediate: reducedMotion.matches,
    });
  }

  const resizeObserver = new ResizeObserver(resize);
  resizeObserver.observe(canvas);
  addEventListener("scroll", updateProgress, { passive: true });
  reducedMotion.addEventListener("change", updateProgress);
  updateProgress();
  resize();
  status.hidden = true;

  addEventListener(
    "pagehide",
    () => {
      controller.dispose();
      resizeObserver.disconnect();
      draco.dispose();
      ktx2.dispose();
      renderer.dispose();
    },
    { once: true },
  );
}

loadStory().catch((error) => {
  canvas.hidden = true;
  status.textContent = `3D unavailable: ${error.message}`;
  status.dataset.state = "error";
});
