export const clamp01 = (value) => Math.min(1, Math.max(0, value));

export function smoothstep(edge0, edge1, value) {
  if (edge0 === edge1) {
    return value >= edge1 ? 1 : 0;
  }
  const amount = clamp01((value - edge0) / (edge1 - edge0));
  return amount * amount * (3 - 2 * amount);
}

export function assemblyAmount(progress, window) {
  return smoothstep(window[0], window[1], progress);
}

export function sampleVectorKeyframes(keyframes, progress, field) {
  if (!keyframes.length) {
    return [0, 0, 0];
  }
  if (progress <= keyframes[0].at) {
    return [...keyframes[0][field]];
  }
  const last = keyframes[keyframes.length - 1];
  if (progress >= last.at) {
    return [...last[field]];
  }

  for (let index = 0; index < keyframes.length - 1; index += 1) {
    const current = keyframes[index];
    const next = keyframes[index + 1];
    if (progress >= current.at && progress <= next.at) {
      const amount = smoothstep(current.at, next.at, progress);
      return current[field].map(
        (value, axis) => value + (next[field][axis] - value) * amount,
      );
    }
  }

  return [...last[field]];
}

export function stageAtProgress(stages, progress) {
  return (
    stages.find(
      (stage, index) =>
        progress >= stage.range[0] &&
        (progress < stage.range[1] || index === stages.length - 1),
    ) ?? stages[stages.length - 1]
  );
}

export function progressFromDocument(scrollY, scrollHeight, viewportHeight) {
  const travel = Math.max(1, scrollHeight - viewportHeight);
  return clamp01(scrollY / travel);
}
