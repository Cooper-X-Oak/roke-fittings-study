import {
  clamp01,
  sampleGroupPosition,
  sampleVectorKeyframes,
  stageAtProgress,
} from "./story-math.mjs";

function buildNodeIndex(root, associations) {
  const byName = new Map();
  const byIndex = new Map();
  root.traverse((object) => {
    if (object.name) {
      const matches = byName.get(object.name) ?? [];
      matches.push(object);
      byName.set(object.name, matches);
    }
    const association = associations?.get(object);
    if (Number.isInteger(association?.nodes)) {
      byIndex.set(association.nodes, object);
    }
  });
  return { byName, byIndex };
}

function resolveGroupObjects(group, nodeIndex) {
  const matches = new Set();
  for (const nodeIndexValue of group.selector.nodeIndices ?? []) {
    const object = nodeIndex.byIndex.get(nodeIndexValue);
    if (object) {
      matches.add(object);
    }
  }
  for (const nodeName of group.selector.nodeNames ?? []) {
    const named = nodeIndex.byName.get(nodeName) ?? [];
    if (named.length !== 1) {
      throw new Error(
        `Expected one scene node named "${nodeName}", received ${named.length}`,
      );
    }
    matches.add(named[0]);
  }
  if (!matches.size) {
    throw new Error(`Group "${group.id}" did not resolve to any scene objects`);
  }
  return [...matches];
}

function captureGroups(root, associations, groups) {
  const nodeIndex = buildNodeIndex(root, associations);
  return groups.map((group) => ({
    group,
    objects: resolveGroupObjects(group, nodeIndex).map((object) => ({
      object,
      basePosition: object.position.toArray(),
    })),
  }));
}

export function createStoryController({
  root,
  associations,
  camera,
  renderer,
  scene,
  manifest,
  onStageChange = () => {},
  easing = 0.16,
  epsilon = 0.0001,
}) {
  const controlledGroups = captureGroups(
    root,
    associations,
    manifest.groups,
  );
  const baseRotation = root.rotation.toArray().slice(0, 3);
  let targetProgress = 0;
  let currentProgress = 0;
  let scheduledFrame = 0;
  let lastStageId = null;
  let disposed = false;

  function apply(progress) {
    for (const { group, objects } of controlledGroups) {
      for (const { object, basePosition } of objects) {
        object.position.fromArray(
          sampleGroupPosition(basePosition, group, progress),
        );
      }
    }
    const rotation = sampleVectorKeyframes(
      manifest.story.modelRotationKeyframes,
      "rotation",
      progress,
    );
    root.rotation.set(
      baseRotation[0] + rotation[0],
      baseRotation[1] + rotation[1],
      baseRotation[2] + rotation[2],
    );
    camera.position.fromArray(
      sampleVectorKeyframes(
        manifest.story.cameraKeyframes,
        "position",
        progress,
      ),
    );
    const target = sampleVectorKeyframes(
      manifest.story.cameraKeyframes,
      "target",
      progress,
    );
    camera.lookAt(...target);
    const stage = stageAtProgress(manifest.story.stages, progress);
    if (stage.id !== lastStageId) {
      lastStageId = stage.id;
      onStageChange(stage);
    }
    renderer.render(scene, camera);
  }

  function schedule() {
    if (!scheduledFrame && !disposed) {
      scheduledFrame = requestAnimationFrame(tick);
    }
  }

  function tick() {
    scheduledFrame = 0;
    const delta = targetProgress - currentProgress;
    if (Math.abs(delta) <= epsilon) {
      currentProgress = targetProgress;
    } else {
      currentProgress += delta * easing;
    }
    apply(currentProgress);
    if (Math.abs(targetProgress - currentProgress) > epsilon) {
      schedule();
    }
  }

  return {
    setProgress(progress, { immediate = false } = {}) {
      targetProgress = clamp01(progress);
      if (immediate) {
        currentProgress = targetProgress;
      }
      schedule();
    },
    renderNow() {
      apply(currentProgress);
    },
    getProgress() {
      return currentProgress;
    },
    dispose() {
      disposed = true;
      if (scheduledFrame) {
        cancelAnimationFrame(scheduledFrame);
        scheduledFrame = 0;
      }
    },
  };
}
