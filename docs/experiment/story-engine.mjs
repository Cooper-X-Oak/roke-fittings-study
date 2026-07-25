import {
  assemblyAmount,
  clamp01,
  sampleVectorKeyframes,
  stageAtProgress,
} from "./story-math.mjs";

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

    return {
      ...group,
      objects: objects.map((object) => ({
        object,
        basePosition: object.position.clone(),
      })),
    };
  });
}

function applyProgress({
  progress,
  manifest,
  groups,
  root,
  baseRotation,
  camera,
}) {
  for (const group of groups) {
    const assembled = assemblyAmount(progress, group.assembleWindow);
    const exploded = 1 - assembled;
    for (const { object, basePosition } of group.objects) {
      object.position.set(
        basePosition.x + group.explodedOffset[0] * exploded,
        basePosition.y + group.explodedOffset[1] * exploded,
        basePosition.z + group.explodedOffset[2] * exploded,
      );
    }
  }

  const rotation = sampleVectorKeyframes(
    manifest.story.modelRotationKeyframes,
    progress,
    "rotation",
  );
  root.rotation.set(
    baseRotation.x + rotation[0],
    baseRotation.y + rotation[1],
    baseRotation.z + rotation[2],
  );

  const position = sampleVectorKeyframes(
    manifest.story.cameraKeyframes,
    progress,
    "position",
  );
  const target = sampleVectorKeyframes(
    manifest.story.cameraKeyframes,
    progress,
    "target",
  );
  camera.position.set(...position);
  camera.lookAt(...target);

  return stageAtProgress(manifest.story.stages, progress);
}

export function createStoryController({
  root,
  associations,
  camera,
  renderer,
  scene,
  manifest,
  onStageChange = () => {},
  onRender = () => {},
  onSettled = () => {},
}) {
  const groups = resolveGroups(root, associations, manifest);
  const baseRotation = root.rotation.clone();
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
    const stage = applyProgress({
      progress,
      manifest,
      groups,
      root,
      baseRotation,
      camera,
    });
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
    const damping = 1 - Math.exp(-13 * deltaSeconds);
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
