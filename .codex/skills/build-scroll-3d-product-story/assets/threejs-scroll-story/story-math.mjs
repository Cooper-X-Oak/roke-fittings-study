export function clamp01(value) {
  return Math.min(1, Math.max(0, Number.isFinite(value) ? value : 0));
}

export function smoothstep01(value) {
  const normalized = clamp01(value);
  return normalized * normalized * (3 - 2 * normalized);
}

export function assemblyAmount(window, progress) {
  const [start, end] = window;
  if (progress <= start) {
    return 1;
  }
  if (progress >= end) {
    return 0;
  }
  return 1 - smoothstep01((progress - start) / (end - start));
}

export function sampleGroupPosition(basePosition, group, progress) {
  const amount = assemblyAmount(group.assembleWindow, clamp01(progress));
  return basePosition.map(
    (value, axis) => value + group.explodedOffset[axis] * amount,
  );
}

function surroundingKeyframes(keyframes, progress) {
  const normalized = clamp01(progress);
  if (normalized <= keyframes[0].at) {
    return [keyframes[0], keyframes[0], 0];
  }
  const last = keyframes.at(-1);
  if (normalized >= last.at) {
    return [last, last, 0];
  }
  for (let index = 1; index < keyframes.length; index += 1) {
    const right = keyframes[index];
    if (normalized <= right.at) {
      const left = keyframes[index - 1];
      return [
        left,
        right,
        smoothstep01((normalized - left.at) / (right.at - left.at)),
      ];
    }
  }
  return [last, last, 0];
}

export function sampleVectorKeyframes(keyframes, field, progress) {
  const [left, right, amount] = surroundingKeyframes(keyframes, progress);
  return left[field].map(
    (value, axis) => value + (right[field][axis] - value) * amount,
  );
}

export function stageAtProgress(stages, progress) {
  const normalized = clamp01(progress);
  return (
    stages.find(
      (stage, index) =>
        normalized >= stage.range[0] &&
        (normalized < stage.range[1] || index === stages.length - 1),
    ) ?? stages.at(-1)
  );
}
