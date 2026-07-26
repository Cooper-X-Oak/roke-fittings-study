import {
  clamp01,
  stageAtProgress,
} from "./story-math.mjs";

function mix(left, right, amount) {
  return left + (right - left) * amount;
}

function mixVector(left, right, amount) {
  return left.map((value, index) => mix(value, right[index], amount));
}

function sampleCameraPath(cameraPath, progress) {
  const frame = clamp01(progress) * (cameraPath.totalFrames - 1);
  const keyframes = cameraPath.keyframes;
  let rightIndex = keyframes.findIndex((keyframe) => keyframe.frame >= frame);
  if (rightIndex <= 0) {
    return { ...keyframes[0], frame };
  }
  if (rightIndex < 0) {
    return { ...keyframes.at(-1), frame };
  }
  const left = keyframes[rightIndex - 1];
  const right = keyframes[rightIndex];
  const span = Math.max(1, right.frame - left.frame);
  const amount = (frame - left.frame) / span;
  return {
    frame,
    position: mixVector(left.position, right.position, amount),
    target: mixVector(left.target, right.target, amount),
    roll: mix(left.roll, right.roll, amount),
    fov: mix(left.fov, right.fov, amount),
    focusDistance: mix(left.focusDistance, right.focusDistance, amount),
    explode: mix(left.explode, right.explode, amount),
    bodyOpacity: mix(left.bodyOpacity, right.bodyOpacity, amount),
    keyLight: mix(left.keyLight, right.keyLight, amount),
    rimLight: mix(left.rimLight, right.rimLight, amount),
    occlusion: mix(left.occlusion, right.occlusion, amount),
  };
}

function resolveNodeAssociations(root, associations) {
  const nodesByIndex = new Map();
  const nodesByName = new Map();

  root.traverse((object) => {
    const mapping = associations?.get(object);
    if (mapping?.nodes !== undefined) {
      nodesByIndex.set(mapping.nodes, object);
    }
    if (object.name) {
      const named = nodesByName.get(object.name) ?? [];
      named.push(object);
      nodesByName.set(object.name, named);
    }
  });

  return { nodesByIndex, nodesByName };
}

function resolveGroups(root, associations, manifest) {
  const { nodesByIndex, nodesByName } = resolveNodeAssociations(root, associations);
  const opacityGroups = new Set(manifest.story.opacityGroupIds ?? []);

  return manifest.groups.map((group) => {
    const selected = new Set();
    for (const nodeIndex of group.selector.nodeIndices ?? []) {
      const object = nodesByIndex.get(nodeIndex);
      if (object) {
        selected.add(object);
      }
    }
    for (const nodeName of group.selector.nodeNames ?? []) {
      for (const object of nodesByName.get(nodeName) ?? []) {
        selected.add(object);
      }
    }

    const objects = [...selected];
    if (!objects.length) {
      throw new Error(`Manifest group "${group.id}" did not resolve to a model node.`);
    }

    const opacityControlled = opacityGroups.has(group.id);
    const resolvedObjects = objects.map((object) => ({
      object,
      basePosition: object.position.clone(),
    }));

    return {
      ...group,
      opacityControlled,
      objects: resolvedObjects,
    };
  });
}

function applyProgress({
  progress,
  manifest,
  groups,
  camera,
  cameraPath,
  lights,
  occlusionElement,
}) {
  const pathState = sampleCameraPath(cameraPath, progress);
  const narrativeExplode = pathState.explode * 0.2;
  for (const group of groups) {
    for (const { object, basePosition } of group.objects) {
      object.position.set(
        basePosition.x + group.explodedOffset[0] * narrativeExplode,
        basePosition.y + group.explodedOffset[1] * narrativeExplode,
        basePosition.z + group.explodedOffset[2] * narrativeExplode,
      );
      if (group.opacityControlled) {
        object.visible = pathState.bodyOpacity >= 0.16;
      }
    }
  }

  camera.position.set(...pathState.position);
  camera.fov = pathState.fov;
  camera.updateProjectionMatrix();
  camera.lookAt(...pathState.target);
  camera.rotateZ((pathState.roll * Math.PI) / 180);
  lights.key.intensity = 2.4 * pathState.keyLight;
  lights.rim.intensity = 1.8 * pathState.rimLight;
  if (lights.accent) {
    lights.accent.intensity = 13 * pathState.rimLight;
  }
  if (occlusionElement) {
    occlusionElement.style.opacity = String(pathState.occlusion);
  }

  return {
    stage: stageAtProgress(manifest.story.stages, progress),
    pathState,
  };
}

export function createStoryController({
  root,
  associations,
  camera,
  renderer,
  scene,
  manifest,
  cameraPath,
  lights,
  occlusionElement,
  onStageChange = () => {},
  onRender = () => {},
  onSettled = () => {},
}) {
  const groups = resolveGroups(root, associations, manifest);
  const state = {
    currentProgress: 0,
    targetProgress: 0,
    currentStageId: null,
    frameHandle: 0,
    lastFrameAt: 0,
    renderCount: 0,
    disposed: false,
  };

  function render(progress, now, interval, reason) {
    const { stage, pathState } = applyProgress({
      progress,
      manifest,
      groups,
      camera,
      cameraPath,
      lights,
      occlusionElement,
    });
    state.pathState = pathState;
    if (stage.id !== state.currentStageId) {
      state.currentStageId = stage.id;
      onStageChange(stage, progress);
    }

    const renderStartedAt = performance.now();
    renderer.render(scene, camera);
    const renderDuration = performance.now() - renderStartedAt;
    state.renderCount += 1;
    onRender({
      now,
      interval,
      reason,
      progress,
      renderCount: state.renderCount,
      renderDuration,
      rendererInfo: renderer.info,
    });
  }

  function tick(now) {
    state.frameHandle = 0;
    if (state.disposed) {
      return;
    }

    const interval = state.lastFrameAt ? now - state.lastFrameAt : null;
    const deltaSeconds = state.lastFrameAt
      ? Math.min(0.1, interval / 1000)
      : 1 / 60;
    state.lastFrameAt = now;

    const distance = state.targetProgress - state.currentProgress;
    const damping = 1 - Math.exp(-8 * deltaSeconds);
    state.currentProgress += distance * damping;
    if (Math.abs(distance) < 0.00035) {
      state.currentProgress = state.targetProgress;
    }

    render(state.currentProgress, now, interval, "animation");

    if (state.currentProgress !== state.targetProgress) {
      schedule("progress");
    } else {
      state.lastFrameAt = 0;
      onSettled({
        progress: state.currentProgress,
        renderCount: state.renderCount,
      });
    }
  }

  function schedule() {
    if (!state.frameHandle && !state.disposed) {
      state.frameHandle = requestAnimationFrame(tick);
    }
  }

  function setProgress(progress, { immediate = false } = {}) {
    state.targetProgress = clamp01(progress);
    if (immediate) {
      state.currentProgress = state.targetProgress;
      state.lastFrameAt = 0;
      render(state.currentProgress, performance.now(), null, "immediate");
      onSettled({
        progress: state.currentProgress,
        renderCount: state.renderCount,
      });
      return;
    }
    schedule("set-progress");
  }

  function invalidate(reason = "invalidate") {
    if (state.disposed) {
      return;
    }
    render(
      state.currentProgress,
      performance.now(),
      null,
      reason,
    );
  }

  function getState() {
    return {
      currentProgress: state.currentProgress,
      targetProgress: state.targetProgress,
      currentStageId: state.currentStageId,
      renderCount: state.renderCount,
      scheduled: Boolean(state.frameHandle),
      disposed: state.disposed,
      resolvedGroups: groups.map((group) => ({
        id: group.id,
        objectCount: group.objects.length,
      })),
    };
  }

  function getTransformSnapshot() {
    return {
      progress: state.currentProgress,
      rootRotation: [root.rotation.x, root.rotation.y, root.rotation.z],
      cameraPosition: [camera.position.x, camera.position.y, camera.position.z],
      cameraRollDegrees: state.pathState?.roll ?? 0,
      cameraFovDegrees: camera.fov,
      explode: state.pathState?.explode ?? 0,
      bodyOpacity: state.pathState?.bodyOpacity ?? 1,
      keyLight: lights.key.intensity,
      rimLight: lights.rim.intensity,
      groups: groups.map((group) => ({
        id: group.id,
        positions: group.objects.map(({ object }) => [
          object.position.x,
          object.position.y,
          object.position.z,
        ]),
      })),
    };
  }

  function dispose() {
    state.disposed = true;
    if (state.frameHandle) {
      cancelAnimationFrame(state.frameHandle);
      state.frameHandle = 0;
    }
  }

  return {
    setProgress,
    invalidate,
    getState,
    getTransformSnapshot,
    dispose,
  };
}
