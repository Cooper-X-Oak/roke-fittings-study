const VIDEO_SOURCE = "./assets/blender-hero-preview-gop6.mp4";
const SHOTS = [
  { range: [0, 0.13], label: "01 / CORE" },
  { range: [0.13, 0.32], label: "02 / ORDER" },
  { range: [0.32, 0.55], label: "03 / BODY" },
  { range: [0.55, 0.77], label: "04 / ASSEMBLY" },
  { range: [0.77, 1], label: "05 / PRESENCE" },
];

const stage = document.querySelector(".stage");
const scrollShell = document.querySelector(".scroll-shell");
const video = document.querySelector("#product-video");
const shotLabel = document.querySelector("#shot-label");
const timelineFill = document.querySelector("#timeline-fill");
const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

let metadataReady = false;
let videoReady = false;
let latestProgress = 0;
let activeSeek = null;
let scheduled = false;

const clamp = (value) => Math.max(0, Math.min(1, value));

function chapterAt(progress) {
  return SHOTS.find((shot, index) => progress >= shot.range[0] && (index === SHOTS.length - 1 || progress < shot.range[1])) ?? SHOTS.at(-1);
}

function updateHud(progress) {
  shotLabel.textContent = chapterAt(progress).label;
  timelineFill.style.transform = `scaleX(${progress})`;
}

function revealVideo() {
  if (!videoReady) {
    videoReady = true;
    stage.classList.add("video-ready");
  }
}

function finishSeek(record) {
  if (activeSeek?.id !== record.id) return;
  clearTimeout(record.timeout);
  activeSeek = null;
  revealVideo();
}

function beginSeek() {
  scheduled = false;
  if (reducedMotion || !metadataReady || activeSeek || !Number.isFinite(video.duration)) return;
  const targetTime = latestProgress * video.duration;
  if (Math.abs(video.currentTime - targetTime) <= 0.035) {
    revealVideo();
    return;
  }
  const record = { id: performance.now(), timeout: null };
  activeSeek = record;
  record.timeout = setTimeout(() => finishSeek(record), 1600);
  video.addEventListener("seeked", () => requestAnimationFrame(() => finishSeek(record)), { once: true });
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
  updateHud(latestProgress);
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

video.src = VIDEO_SOURCE;
updateHud(0);
requestProgress(scrollProgress());

window.__BLENDER_HERO_PREVIEW__ = {
  waitForReady: () => new Promise((resolve) => {
    const finish = () => resolve({ duration: video.duration, readyState: video.readyState, videoReady, source: VIDEO_SOURCE });
    if (metadataReady && videoReady) finish();
    else video.addEventListener("loadeddata", finish, { once: true });
  }),
  seekTo(progress) {
    return new Promise((resolve) => {
      requestProgress(progress);
      const started = performance.now();
      const done = () => resolve({ elapsedMs: performance.now() - started, currentTime: video.currentTime, duration: video.duration });
      video.addEventListener("seeked", done, { once: true });
      setTimeout(done, 1700);
    });
  },
  snapshot: () => ({ progress: latestProgress, currentTime: video.currentTime, duration: video.duration, videoReady }),
};
