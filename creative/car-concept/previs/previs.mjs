import * as THREE from "three";
import { DRACOLoader } from "/docs/experiment/assets/vendor/three/loaders/DRACOLoader.js";
import { GLTFLoader } from "/docs/experiment/assets/vendor/three/loaders/GLTFLoader.js";
import { KTX2Loader } from "/docs/experiment/assets/vendor/three/loaders/KTX2Loader.js";

const SHOTS = {
  1: {
    camera: [3.15, 0.78, 3.1],
    target: [0.83, 0.38, 1.16],
    fov: 20,
    visibility: "front-wheel",
    explode: 0,
    rotation: [0.02, -0.08, -0.035],
  },
  2: {
    camera: [2.46, 1.54, 2.34],
    target: [0.02, 0.57, 0.08],
    fov: 27,
    visibility: "cabin",
    explode: 0,
    rotation: [0.01, -0.18, 0],
  },
  3: {
    camera: [5.45, 2.65, 6.28],
    target: [0, 0.5, 0.18],
    fov: 30,
    visibility: "all",
    explode: 1,
    rotation: [0.02, -0.18, 0],
  },
  4: {
    camera: [5.2, 2.22, 5.8],
    target: [0, 0.48, 0.18],
    fov: 28,
    visibility: "all",
    explode: 0.34,
    rotation: [0.015, -0.12, 0],
  },
  5: {
    camera: [4.72, 1.82, 5.2],
    target: [0, 0.46, 0.14],
    fov: 27,
    visibility: "all",
    explode: 0,
    rotation: [0.01, -0.07, 0],
  },
};

const shotNumber = Math.min(
  5,
  Math.max(1, Number(new URLSearchParams(location.search).get("shot") ?? 1)),
);
const shot = SHOTS[shotNumber];
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
renderer.toneMappingExposure = shotNumber === 5 ? 1.06 : 0.98;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(
  shot.fov,
  innerWidth / innerHeight,
  0.03,
  80,
);
camera.position.set(...shot.camera);
camera.lookAt(...shot.target);

scene.add(new THREE.HemisphereLight(0x8fa4c2, 0x090a0c, shotNumber === 5 ? 1.4 : 0.65));

const key = new THREE.DirectionalLight(
  shotNumber >= 4 ? 0xffd7cc : 0xb9d7ff,
  shotNumber === 5 ? 3.5 : 3.1,
);
key.position.set(4.5, 6, 5.5);
key.castShadow = true;
key.shadow.mapSize.set(2048, 2048);
key.shadow.camera.left = -6;
key.shadow.camera.right = 6;
key.shadow.camera.top = 6;
key.shadow.camera.bottom = -6;
scene.add(key);

const redRim = new THREE.PointLight(
  0xe51d32,
  shotNumber === 1 ? 28 : shotNumber >= 4 ? 14 : 10,
  11,
  2,
);
redRim.position.set(-2.5, 1.8, 3.6);
scene.add(redRim);

const coolRim = new THREE.DirectionalLight(0x8ebfff, shotNumber === 3 ? 3.6 : 2.2);
coolRim.position.set(-5, 3, -4);
scene.add(coolRim);

const floor = new THREE.Mesh(
  new THREE.PlaneGeometry(30, 30),
  new THREE.MeshStandardMaterial({
    color: 0x07080a,
    roughness: 0.72,
    metalness: 0.12,
  }),
);
floor.rotation.x = -Math.PI / 2;
floor.position.y = -0.17;
floor.receiveShadow = true;
floor.visible = shotNumber >= 3;
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
const gltf = await loader.loadAsync(
  "/docs/experiment/assets/models/car-concept-web.glb",
);
const model = gltf.scene;
model.rotation.set(...shot.rotation);
scene.add(model);

const basePositions = new Map();
model.traverse((object) => {
  basePositions.set(object.uuid, object.position.clone());
  if (object.isMesh) {
    object.castShadow = true;
    object.receiveShadow = true;
  }
});

function matchesSelfOrAncestor(object, pattern) {
  let current = object;
  while (current && current !== model) {
    if (pattern.test(current.name ?? "")) {
      return true;
    }
    current = current.parent;
  }
  return false;
}

function showOnlyPattern(pattern) {
  model.traverse((object) => {
    if (object.isMesh) {
      object.visible = true;
      if (!matchesSelfOrAncestor(object, pattern)) {
        const materials = Array.isArray(object.material)
          ? object.material
          : [object.material];
        object.material = materials.map((material) => {
          const hidden = material.clone();
          hidden.visible = false;
          return hidden;
        });
        if (object.material.length === 1) {
          object.material = object.material[0];
        }
      }
    }
  });
}

if (shot.visibility === "front-wheel") {
  showOnlyPattern(/^WheelFrontL/u);
} else if (shot.visibility === "cabin") {
  showOnlyPattern(/^(Interior|BodyWindshield)/u);
}

function explodeOffset(name, amount) {
  if (!amount) {
    return [0, 0, 0];
  }
  if (/WheelFrontL/u.test(name)) return [1.1, 0.08, 0.72].map((v) => v * amount);
  if (/WheelFrontR/u.test(name)) return [-1.1, 0.08, 0.72].map((v) => v * amount);
  if (/WheelRearL/u.test(name)) return [1.0, 0.05, -0.7].map((v) => v * amount);
  if (/WheelRearR/u.test(name)) return [-1.0, 0.05, -0.7].map((v) => v * amount);
  if (/BodyDoorL/u.test(name)) return [0.92, 0.24, 0].map((v) => v * amount);
  if (/BodyDoorR/u.test(name)) return [-0.92, 0.24, 0].map((v) => v * amount);
  if (/BodyHood/u.test(name)) return [0, 0.78, 0.5].map((v) => v * amount);
  if (/BodyWindshield/u.test(name)) return [0, 0.72, 0.06].map((v) => v * amount);
  if (/^Interior/u.test(name)) return [0, 0.22, -0.08].map((v) => v * amount);
  if (/Axles/u.test(name)) return [0, -0.12, 0].map((v) => v * amount);
  return [0, 0, 0];
}

if (shot.explode) {
  for (const child of model.getObjectByName("BodyUnderside")?.children ?? []) {
    const base = basePositions.get(child.uuid);
    const offset = explodeOffset(child.name, shot.explode);
    child.position.set(
      base.x + offset[0],
      base.y + offset[1],
      base.z + offset[2],
    );
  }
}

if (shotNumber === 3) {
  model.traverse((object) => {
    if (!object.isMesh) return;
    const name = object.name || object.parent?.name || "";
    if (/^Body(?!Underside)/u.test(name)) {
      const materials = Array.isArray(object.material)
        ? object.material
        : [object.material];
      object.material = materials.map((material) => {
        const clone = material.clone();
        clone.transparent = true;
        clone.opacity = Math.min(clone.opacity ?? 1, 0.78);
        return clone;
      });
      if (object.material.length === 1) {
        object.material = object.material[0];
      }
    }
  });
}

await renderer.compileAsync(scene, camera);
renderer.render(scene, camera);
window.__PREVIS_READY__ = true;
