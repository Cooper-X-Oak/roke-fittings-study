const VIDEO_SOURCE = "./assets/control-valve-gop6.mp4";

const SHOTS = [
  { id: "core", range: [0, 0.14], eyebrow: "01 / THE CORE", label: "01 THE CORE", title: "精密，先从<br>核心被看见。", body: "沿滚动查看内部结构如何沿同一条轴线展开、归位与闭合。" },
  { id: "nested", range: [0.14, 0.38], eyebrow: "02 / IN ORDER", label: "02 IN ORDER", title: "一层<br>接住一层。", body: "四个几何岛依次归位；编号仅描述镜头中的空间顺序。" },
  { id: "body", range: [0.38, 0.62], eyebrow: "03 / CONTAINED", label: "03 CONTAINED", title: "核心，被<br>结构承载。", body: "阀体闭合建立位置关系，让核心仍可被看见。" },
  { id: "assembly", range: [0.62, 0.78], eyebrow: "04 / AS ONE", label: "04 AS ONE", title: "直到每一层，<br>成为同一台设备。", body: "执行器落座，镜头回到完整的产品姿态。" },
  { id: "presence", range: [0.78, 1], eyebrow: "05 / COMPLETE", label: "05 COMPLETE", title: "精密，最终<br>成为整体。", body: "滚动至终点，停留在完整产品的静止画面。" },
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
const lastFrameTime = (540 - 1) / frameRate;
const frameTolerance = 0.55 / frameRate;
const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

let metadataReady = false;
let videoFrameReady = false;
let latestProgress = 0;
let activeSeek = null;
let scheduled = false;
let currentShotId = "";

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
  const record = { id: performance.now(), timeout: null };
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
