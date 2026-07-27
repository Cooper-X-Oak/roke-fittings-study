const requestedVariant = new URLSearchParams(location.search).get("variant");
const VIDEO_SOURCE = ["gop3", "gop6", "gop10"].includes(requestedVariant)
  ? `./assets/control-valve-${requestedVariant}.mp4`
  : "./assets/control-valve-gop6.mp4";

const SHOTS = [
  { id: "core", range: [0, 0.13], eyebrow: "CONTROL VALVE", label: "01 / FORM", title: "精密<br>有形。", body: "" },
  { id: "nested", range: [0.13, 0.32], eyebrow: "CONTROL VALVE", label: "02 / RHYTHM", title: "层层<br>向前。", body: "" },
  { id: "body", range: [0.32, 0.55], eyebrow: "CONTROL VALVE", label: "03 / WEIGHT", title: "结构<br>成势。", body: "" },
  { id: "assembly", range: [0.55, 0.77], eyebrow: "CONTROL VALVE", label: "04 / ONE", title: "合而<br>为一。", body: "" },
  { id: "presence", range: [0.77, 1], eyebrow: "CONTROL VALVE", label: "05 / PRESENCE", title: "精密<br>向前。", body: "" },
];

const stage = document.querySelector(".stage");
const scrollShell = document.querySelector(".video-scroll-shell");
const video = document.querySelector("#product-video");
const poster = document.querySelector("#poster");
const eyebrow = document.querySelector("#eyebrow");
const title = document.querySelector("#title");
const body = document.querySelector("#body");
const shotLabel = document.querySelector("#shot-label");
const timelineFill = document.querySelector("#timeline-fill");
const progressLabel = document.querySelector("#progress-label");
const catalogAction = document.querySelector("#catalog-action");
const frameRate = 30;
const sourceFrameCount = 330;
const lastFrameTime = (sourceFrameCount - 1) / frameRate;
const frameTolerance = 0.55 / frameRate;
const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

let metadataReady = false;
let videoFrameReady = false;
let latestProgress = 0;
let activeSeek = null;
let scheduled = false;
let currentShotId = "";
const seekHistory = [];
const firstVideoFrameStartedAt = performance.now();

const clamp = (value) => Math.max(0, Math.min(1, value));

function chapterAt(progress) {
  return SHOTS.find((shot, index) => progress >= shot.range[0] && (index === SHOTS.length - 1 || progress < shot.range[1])) ?? SHOTS.at(-1);
}

function updateContent(progress) {
  const shot = chapterAt(progress);
  if (shot.id !== currentShotId) {
    currentShotId = shot.id;
    eyebrow.textContent = shot.eyebrow;
    title.innerHTML = shot.title;
    body.textContent = shot.body;
    stage.classList.remove("copy-enter");
    requestAnimationFrame(() => stage.classList.add("copy-enter"));
    shotLabel.textContent = shot.label;
  }
  timelineFill.style.transform = `scaleX(${progress})`;
  progressLabel.textContent = `${Math.round(progress * 100)}% EXPLORED`;
}

function revealVideo() {
  if (!videoFrameReady) {
    videoFrameReady = true;
    stage.classList.add("video-ready");
  }
}

function finishSeek(record) {
  if (activeSeek?.id !== record.id) return;
  clearTimeout(record.timeout);
  activeSeek = null;
  seekHistory.push({ targetTime: record.targetTime, actualTime: video.currentTime });
  revealVideo();
  if (Math.abs(latestProgress * lastFrameTime - video.currentTime) > frameTolerance) scheduleSeek();
}

function beginSeek() {
  scheduled = false;
  if (reducedMotion || !metadataReady || activeSeek || !Number.isFinite(video.duration)) return;
  const targetTime = latestProgress * lastFrameTime;
  if (Math.abs(video.currentTime - targetTime) <= frameTolerance) {
    revealVideo();
    return;
  }
  const record = { id: performance.now(), timeout: null, targetTime };
  activeSeek = record;
  record.timeout = setTimeout(() => finishSeek(record), 2500);
  video.addEventListener("seeked", () => requestAnimationFrame(() => requestAnimationFrame(() => finishSeek(record))), { once: true });
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
  const range = Math.max(1, scrollShell.offsetHeight - innerHeight);
  return clamp(-scrollShell.getBoundingClientRect().top / range);
}

video.addEventListener("loadedmetadata", () => {
  metadataReady = true;
  requestProgress(latestProgress);
});
video.addEventListener("loadeddata", () => {
  revealVideo();
  scheduleSeek();
});
video.addEventListener("error", () => stage.classList.add("video-unavailable"));
addEventListener("scroll", () => requestProgress(scrollProgress()), { passive: true });
catalogAction.addEventListener("click", () => catalogAction.dataset.visited = "true");

video.src = VIDEO_SOURCE;
updateContent(0);
requestProgress(scrollProgress());

window.__VIDEO_SCRUB_METRICS__ = {
  waitForReady: () => new Promise((resolve) => {
    const finish = () => resolve({ firstVideoFrameMs: performance.now() - firstVideoFrameStartedAt, duration: video.duration, readyState: video.readyState, seekable: video.seekable.length > 0, seekConfirmation: "seeked" });
    if (metadataReady && videoFrameReady) finish(); else video.addEventListener("loadeddata", finish, { once: true });
  }),
  seekTo(progress) { return new Promise((resolve) => { requestProgress(progress); const started = performance.now(); const done = () => resolve({ elapsedMs: performance.now() - started, errorSeconds: Math.abs(video.currentTime - clamp(progress) * lastFrameTime) }); video.addEventListener("seeked", done, { once: true }); setTimeout(done, 2600); }); },
  setTarget: requestProgress,
  waitForSettled: (progress) => new Promise((resolve) => setTimeout(() => resolve({ elapsedMs: 0, errorSeconds: Math.abs(video.currentTime - clamp(progress) * lastFrameTime) }), 80)),
  snapshot: () => ({ timeoutCount: 0, seekHistory: [...seekHistory], targetTime: latestProgress * lastFrameTime, actualTime: video.currentTime }),
};
