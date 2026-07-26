import * as THREE from "three";
import { DRACOLoader } from "/docs/experiment/assets/vendor/three/loaders/DRACOLoader.js";
import { GLTFLoader } from "/docs/experiment/assets/vendor/three/loaders/GLTFLoader.js";
import { KTX2Loader } from "/docs/experiment/assets/vendor/three/loaders/KTX2Loader.js";

const artifact = await fetch("../camera-previs.json").then((response) => response.json());
const canvas = document.querySelector("#stage");
const renderer = new THREE.WebGLRenderer({
  canvas,
  antialias: true,
  alpha: true,
  powerPreference: "high-performance",
});
renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
renderer.setSize(innerWidth, innerHeight, false);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.02;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(32, innerWidth / innerHeight, 0.025, 80);

const hemisphere = new THREE.HemisphereLight(0x8fa4c2, 0x07080a, 0.72);
scene.add(hemisphere);

const key = new THREE.DirectionalLight(0xffd8cf, 3.2);
key.position.set(4.5, 6, 5.5);
key.castShadow = true;
key.shadow.mapSize.set(2048, 2048);
key.shadow.camera.left = -6;
key.shadow.camera.right = 6;
key.shadow.camera.top = 6;
key.shadow.camera.bottom = -6;
scene.add(key);

const redRim = new THREE.PointLight(0xe51d32, 22, 12, 2);
redRim.position.set(-2.8, 1.8, 3.7);
scene.add(redRim);

const coolRim = new THREE.DirectionalLight(0x8ebfff, 2.4);
coolRim.position.set(-5, 3, -4);
scene.add(coolRim);

const floor = new THREE.Mesh(
  new THREE.PlaneGeometry(30, 30),
  new THREE.MeshStandardMaterial({ color: 0x07080a, roughness: 0.72, metalness: 0.12 }),
);
floor.rotation.x = -Math.PI / 2;
floor.position.y = -0.17;
floor.receiveShadow = true;
scene.add(floor);

const dracoLoader = new DRACOLoader();
dracoLoader.setDecoderPath("/docs/experiment/assets/vendor/three/libs/draco/");
dracoLoader.setDecoderConfig({ type: "wasm" });

const ktx2Loader = new KTX2Loader();
ktx2Loader.setTranscoderPath("/docs/experiment/assets/vendor/three/libs/basis/");
ktx2Loader.detectSupport(renderer);

const loader = new GLTFLoader();
loader.setDRACOLoader(dracoLoader);
loader.setKTX2Loader(ktx2Loader);
const gltf = await loader.loadAsync("/docs/experiment/assets/models/car-concept-web.glb");
const model = gltf.scene;
model.rotation.set(0.01, -0.07, 0);
scene.add(model);

const basePositions = new Map();
const baseMaterials = new Map();
model.traverse((object) => {
  basePositions.set(object.uuid, object.position.clone());
  if (object.isMesh) {
    object.castShadow = true;
    object.receiveShadow = true;
    const materials = Array.isArray(object.material) ? object.material : [object.material];
    const clones = materials.map((material) => material.clone());
    baseMaterials.set(object.uuid, clones);
    object.material = Array.isArray(object.material) ? clones : clones[0];
  }
});

function explodeOffset(name, amount) {
  if (/WheelFrontL/u.test(name)) return [1.1, 0.08, 0.72].map((value) => value * amount);
  if (/WheelFrontR/u.test(name)) return [-1.1, 0.08, 0.72].map((value) => value * amount);
  if (/WheelRearL/u.test(name)) return [1.0, 0.05, -0.7].map((value) => value * amount);
  if (/WheelRearR/u.test(name)) return [-1.0, 0.05, -0.7].map((value) => value * amount);
  if (/BodyDoorL/u.test(name)) return [0.92, 0.24, 0].map((value) => value * amount);
  if (/BodyDoorR/u.test(name)) return [-0.92, 0.24, 0].map((value) => value * amount);
  if (/BodyHood/u.test(name)) return [0, 0.78, 0.5].map((value) => value * amount);
  if (/BodyWindshield/u.test(name)) return [0, 0.72, 0.06].map((value) => value * amount);
  if (/^Interior/u.test(name)) return [0, 0.22, -0.08].map((value) => value * amount);
  if (/Axles/u.test(name)) return [0, -0.12, 0].map((value) => value * amount);
  return [0, 0, 0];
}

function applyExplode(amount) {
  for (const child of model.getObjectByName("BodyUnderside")?.children ?? []) {
    const base = basePositions.get(child.uuid);
    const offset = explodeOffset(child.name, amount);
    child.position.set(base.x + offset[0], base.y + offset[1], base.z + offset[2]);
  }
}

function applyBodyOpacity(opacity) {
  model.traverse((object) => {
    if (!object.isMesh) return;
    const name = object.name || object.parent?.name || "";
    const isBody = /^Body(?!Underside)/u.test(name);
    const materials = baseMaterials.get(object.uuid);
    for (const material of materials) {
      material.transparent = isBody && opacity < 0.999;
      material.opacity = isBody ? opacity : 1;
      material.depthWrite = !isBody || opacity > 0.45;
    }
  });
}

const title = document.querySelector("#shot-title");
const copy = document.querySelector("#shot-copy");
const counter = document.querySelector("#frame-counter");
const telemetry = document.querySelector("#telemetry");
const progressBar = document.querySelector("#progress-value");
const occlusion = document.querySelector("#occlusion");

function updateFrame(frameNumber) {
  const frame = artifact.frames[Math.max(0, Math.min(artifact.totalFrames - 1, frameNumber))];
  const shot = artifact.shots.find((entry) => entry.id === frame.shotId);
  camera.position.set(...frame.camera.position);
  camera.fov = frame.camera.fovDegrees;
  camera.updateProjectionMatrix();
  camera.lookAt(...frame.camera.target);
  camera.rotateZ(THREE.MathUtils.degToRad(frame.camera.rollDegrees));
  applyExplode(frame.product.explode);
  applyBodyOpacity(frame.product.bodyOpacity);
  key.intensity = 2.4 * frame.light.key;
  redRim.intensity = 13 * frame.light.rim;
  coolRim.intensity = 1.8 * frame.light.rim;
  hemisphere.intensity = 0.5 + frame.light.key * 0.25;
  occlusion.style.opacity = String(frame.transition.occlusion);
  title.textContent = `${String(artifact.shots.indexOf(shot) + 1).padStart(2, "0")} / ${shot.title}`;
  copy.textContent = shot.copy;
  counter.textContent = `F${String(frame.frame).padStart(3, "0")}  ${frame.timeSeconds.toFixed(2)}s`;
  telemetry.textContent = `FOV ${frame.camera.fovDegrees.toFixed(1)}°   ROLL ${frame.camera.rollDegrees.toFixed(1)}°   FOCUS ${frame.camera.focusDistance.toFixed(2)}m`;
  progressBar.style.width = `${frame.progress * 100}%`;
  renderer.render(scene, camera);
  window.__PREVIS_FRAME__ = frame.frame;
}

window.__setPrevisFrame = updateFrame;
await renderer.compileAsync(scene, camera);
const initialFrame = Number(new URLSearchParams(location.search).get("frame") ?? 0);
updateFrame(initialFrame);
window.__PREVIS_READY__ = true;

addEventListener("resize", () => {
  renderer.setSize(innerWidth, innerHeight, false);
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.render(scene, camera);
});
