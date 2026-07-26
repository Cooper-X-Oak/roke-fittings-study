const VIDEO_VARIANTS = {
  gop3: {
    label: "GOP 3",
    src: "./assets/control-valve-gop3.mp4",
  },
  gop6: {
    label: "GOP 6",
    src: "./assets/control-valve-gop6.mp4",
  },
  gop10: {
    label: "GOP 10",
    src: "./assets/control-valve-gop10.mp4",
  },
};

const SHOTS = [
  {
    id: "core-suspended",
    range: [0, 0.14],
    eyebrow: "01 / THE CORE",
    label: "01 THE CORE",
    title: "精密，先从<br>核心被看见。",
    body: "从完整轴线推入核心；视频只承载产品与灯光。",
  },
  {
    id: "precision-nested",
    range: [0.14, 0.38],
    eyebrow: "02 / IN ORDER",
    label: "02 IN ORDER",
    title: "一层<br>接住一层。",
    body: "四个真实几何岛依次归位，HTML 文案独立切换。",
  },
  {
    id: "body-encloses",
    range: [0.38, 0.62],
    eyebrow: "03 / CONTAINED",
    label: "03 CONTAINED",
    title: "核心，被<br>结构承载。",
    body: "滚动时间与阀体闭合保持同一确定性剪辑。",
  },
  {
    id: "assembly-complete",
    range: [0.62, 0.78],
    eyebrow: "04 / AS ONE",
    label: "04 AS ONE",
    title: "直到每一层，<br>成为同一台设备。",
    body: "执行器下降落座，视频不需要实时重算三维几何。",
  },
  {
    id: "product-presence",
    range: [0.78, 1],
    eyebrow: "05 / COMPLETE",
    label: "05 COMPLETE",
    title: "精密，最终<br>成为整体。",
    body: "DN80 CL2500 气动串级式调节阀预渲染滚动实验。",
  },
];

const stage = document.querySelector(".stage");
const video = document.querySelector("#product-video");
const poster = document.querySelector("#poster");
const buttons = [...document.querySelectorAll("[data-variant]")];
const eyebrow = document.querySelector("#eyebrow");
const title = document.querySelector("#title");
const body = document.querySelector("#body");
const shotLabel = document.querySelector("#shot-label");
const timelineFill = document.querySelector("#timeline-fill");
const metricVariant = document.querySelector("#metric-variant");
const metricTarget = document.querySelector("#metric-target");
const metricActual = document.querySelector("#metric-actual");
const metricError = document.querySelector("#metric-error");
const metricState = document.querySelector("#metric-state");
const params = new URLSearchParams(location.search);
const frameRate = 30;
const lastFrameTime = (540 - 1) / frameRate;
const frameTolerance = 0.55 / frameRate;
const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

let activeVariant =
  VIDEO_VARIANTS[params.get("variant")] ? params.get("variant") : "gop6";
let metadataReady = false;
let videoFrameReady = false;
let latestProgress = 0;
let activeSeek = null;
let scheduled = false;
let seekSequence = 0;
let timeoutCount = 0;
let firstVideoFrameMs = null;
let currentShotId = "";
const navigationStartedAt = performance.now();
const seekHistory = [];

const clamp = (value) => Math.max(0, Math.min(1, value));

function chapterAt(progress) {
  return (
    SHOTS.find(
      (shot, index) =>
        progress >= shot.range[0] &&
        (index === SHOTS.length - 1 || progress < shot.range[1]),
    ) ?? SHOTS.at(-1)
  );
}

function updateContent(progress) {
  const shot = chapterAt(progress);
  if (shot.id !== currentShotId) {
    currentShotId = shot.id;
    eyebrow.textContent = shot.eyebrow;
    title.innerHTML = shot.title;
    body.textContent = shot.body;
    shotLabel.textContent = shot.label;
  }
  timelineFill.style.transform = `scaleX(${progress})`;
}

function displayedFrame(callback) {
  if ("requestVideoFrameCallback" in video) {
    video.requestVideoFrameCallback((_now, metadata) => {
      callback(metadata.mediaTime);
    });
  } else {
    requestAnimationFrame(() => callback(video.currentTime));
  }
}

function confirmPausedSeekFrame(callback) {
  requestAnimationFrame(() => {
    requestAnimationFrame(() => callback(video.currentTime));
  });
}

function revealVideo(actualTime) {
  if (!videoFrameReady) {
    videoFrameReady = true;
    firstVideoFrameMs = performance.now() - navigationStartedAt;
    stage.classList.add("video-ready");
  }
  metricActual.textContent = `${actualTime.toFixed(3)} s`;
}

function finishSeek(record, actualTime, timedOut = false) {
  if (activeSeek?.id !== record.id) return;
  clearTimeout(record.timeout);
  record.displayedAt = performance.now();
  record.actualTime = actualTime;
  record.errorSeconds = Math.abs(actualTime - record.targetTime);
  record.latencyMs = record.displayedAt - record.assignedAt;
  record.timedOut = timedOut;
  seekHistory.push(record);
  if (timedOut) timeoutCount += 1;
  activeSeek = null;
  revealVideo(actualTime);
  metricError.textContent = `${(record.errorSeconds * 1000).toFixed(1)} ms`;
  metricState.textContent = timedOut ? "timeout" : "displayed";
  if (Math.abs(latestProgress * lastFrameTime - actualTime) > frameTolerance) {
    scheduleSeek();
  }
}

function beginSeek() {
  scheduled = false;
  if (
    reducedMotion ||
    !metadataReady ||
    activeSeek ||
    !Number.isFinite(video.duration)
  ) {
    return;
  }
  const targetTime = latestProgress * lastFrameTime;
  metricTarget.textContent = `${targetTime.toFixed(3)} s`;
  if (Math.abs(video.currentTime - targetTime) <= frameTolerance) {
    const actualTime = video.currentTime;
    revealVideo(actualTime);
    metricError.textContent =
      `${(Math.abs(actualTime - targetTime) * 1000).toFixed(1)} ms`;
    metricState.textContent = "displayed";
    return;
  }
  const record = {
    id: ++seekSequence,
    variant: activeVariant,
    progress: latestProgress,
    targetTime,
    assignedAt: performance.now(),
  };
  activeSeek = record;
  metricState.textContent = "seeking";
  record.timeout = setTimeout(() => {
    finishSeek(record, video.currentTime, true);
  }, 2500);
  const onSeeked = () => {
    confirmPausedSeekFrame((actualTime) =>
      finishSeek(record, actualTime, false),
    );
  };
  video.addEventListener("seeked", onSeeked, { once: true });
  video.currentTime = targetTime;
}

function scheduleSeek() {
  if (!scheduled) {
    scheduled = true;
    requestAnimationFrame(beginSeek);
  }
}

function requestProgress(progress) {
  latestProgress = clamp(progress);
  updateContent(latestProgress);
  scheduleSeek();
}

function scrollProgress() {
  const range = Math.max(1, document.documentElement.scrollHeight - innerHeight);
  return clamp(scrollY / range);
}

function setVariant(id) {
  if (!VIDEO_VARIANTS[id]) throw new Error(`Unknown variant: ${id}`);
  activeVariant = id;
  metadataReady = false;
  videoFrameReady = false;
  activeSeek = null;
  stage.classList.remove("video-ready");
  metricVariant.textContent = VIDEO_VARIANTS[id].label;
  metricState.textContent = "loading";
  metricActual.textContent = "poster";
  metricError.textContent = "—";
  buttons.forEach((button) => {
    button.setAttribute(
      "aria-pressed",
      String(button.dataset.variant === id),
    );
  });
  video.src = VIDEO_VARIANTS[id].src;
  video.load();
}

function waitForReady(timeoutMs = 10000) {
  const startedAt = performance.now();
  return new Promise((resolve, reject) => {
    const poll = () => {
      if (metadataReady && videoFrameReady) {
        resolve(snapshot());
        return;
      }
      if (performance.now() - startedAt > timeoutMs) {
        reject(new Error("Video readiness timed out"));
        return;
      }
      setTimeout(poll, 16);
    };
    poll();
  });
}

function waitForSettled(progress, timeoutMs = 5000) {
  const targetProgress = clamp(progress);
  const targetTime = targetProgress * lastFrameTime;
  const startedAt = performance.now();
  requestProgress(targetProgress);
  return new Promise((resolve, reject) => {
    const poll = () => {
      if (
        !activeSeek &&
        Math.abs(video.currentTime - targetTime) <= frameTolerance
      ) {
        const actualTime = video.currentTime;
        resolve({
          targetProgress,
          targetTime,
          actualTime,
          errorSeconds: Math.abs(actualTime - targetTime),
          elapsedMs: performance.now() - startedAt,
        });
        return;
      }
      if (performance.now() - startedAt > timeoutMs) {
        reject(new Error(`Seek to ${targetProgress} timed out`));
        return;
      }
      setTimeout(poll, 8);
    };
    poll();
  });
}

function snapshot() {
  return {
    activeVariant,
    metadataReady,
    videoFrameReady,
    posterVisible:
      getComputedStyle(poster).opacity !== "0" &&
      poster.getBoundingClientRect().width > 0 &&
      poster.naturalWidth > 0,
    latestProgress,
    targetTime: latestProgress * lastFrameTime,
    actualTime: video.currentTime,
    currentShotId,
    activeSeek: activeSeek
      ? {
          id: activeSeek.id,
          targetTime: activeSeek.targetTime,
        }
      : null,
    firstVideoFrameMs,
    seekConfirmation: "seeked + two animation frames",
    timeoutCount,
    seekHistory: structuredClone(seekHistory),
    seekable: Array.from(
      { length: video.seekable.length },
      (_value, index) => ({
        start: video.seekable.start(index),
        end: video.seekable.end(index),
      }),
    ),
    duration: video.duration,
    readyState: video.readyState,
  };
}

video.addEventListener("loadedmetadata", () => {
  metadataReady = true;
  requestProgress(latestProgress);
});

video.addEventListener("loadeddata", () => {
  revealVideo(video.currentTime);
  scheduleSeek();
});

video.addEventListener("error", () => {
  metricState.textContent = `error ${video.error?.code ?? ""}`.trim();
});

buttons.forEach((button) => {
  button.addEventListener("click", () => {
    const nextUrl = new URL(location.href);
    nextUrl.searchParams.set("variant", button.dataset.variant);
    history.replaceState({}, "", nextUrl);
    setVariant(button.dataset.variant);
  });
});

addEventListener(
  "scroll",
  () => {
    requestProgress(scrollProgress());
  },
  { passive: true },
);

window.__VIDEO_SCRUB_METRICS__ = {
  waitForReady,
  seekTo: waitForSettled,
  setTarget(progress) {
    requestProgress(progress);
    return snapshot();
  },
  waitForSettled,
  snapshot,
};

updateContent(0);
setVariant(activeVariant);
