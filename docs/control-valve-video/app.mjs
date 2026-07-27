const requestedVariant = new URLSearchParams(location.search).get("variant");
const VIDEO_SOURCE = ["gop3", "gop6", "gop10"].includes(requestedVariant)
  ? `./assets/control-valve-${requestedVariant}.mp4`
  : "./assets/control-valve-gop6.mp4";

const SHOTS = [
  { id: "core", range: [0, 0.13], label: "01 / FORM" },
  { id: "nested", range: [0.13, 0.32], label: "02 / RHYTHM" },
  { id: "body", range: [0.32, 0.55], label: "03 / WEIGHT" },
  { id: "assembly", range: [0.55, 0.77], label: "04 / ONE" },
  { id: "presence", range: [0.77, 1], label: "05 / PRESENCE" },
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
    shotLabel.textContent = shot.label;
  }
  timelineFill.style.transform = `scaleX(${progress})`;
  const titleProgress = clamp((progress - 0.16) / 0.64);
  title.style.setProperty("--hero-title-y", `${titleProgress * -116}vh`);
  title.style.opacity = `${1 - titleProgress}`;
  eyebrow.style.opacity = `${Math.max(0, 1 - titleProgress * 1.6)}`;
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
