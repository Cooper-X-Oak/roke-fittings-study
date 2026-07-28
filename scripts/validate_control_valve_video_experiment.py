#!/usr/bin/env python3

import hashlib
import json
import math
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CREATIVE = ROOT / "creative" / "control-valve-video"
ROUTE = ROOT / "docs" / "control-valve-video"


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def read_json(path: Path) -> dict:
    if not path.is_file():
        fail(f"required evidence is missing: {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


render = read_json(CREATIVE / "render-manifest.json")
profile = render.get("renderProfile", {})
frames = render.get("frames", [])
if profile != {
    "width": 1280,
    "height": 800,
    "dpr": 1,
    "fps": 30,
    "frameCount": 540,
    "durationSeconds": 18,
    "uiFree": True,
    "captureSurface": "WebGL canvas only",
    "captureMethod": "HTMLCanvasElement.toDataURL",
}:
    fail("render profile is not the approved 540-frame UI-free canvas export")
if len(frames) != 540 or [item.get("frame") for item in frames] != list(range(540)):
    fail("render manifest does not prove every ordered source frame")
if len({item.get("filename") for item in frames}) != 540:
    fail("frame filenames are not unique")
if len({item.get("sha256") for item in frames}) < 400:
    fail("rendered animation lacks sufficient distinct visual states")
if any(
    len(item.get("sha256", "")) != 64 or item.get("bytes", 0) < 10_000
    for item in frames
):
    fail("a rendered frame lacks valid size or SHA-256 evidence")
if (
    render.get("consoleErrors")
    or render.get("pageErrors")
    or render.get("failedRequests")
):
    fail("UI-free frame render contains browser failures")
source_previs = ROOT / render.get("sourceCameraPrevis", "")
if (
    not source_previs.is_file()
    or sha256(source_previs) != render.get("sourceCameraPrevisSha256")
):
    fail("render manifest is not bound to the current canonical camera previs")

poster = ROOT / render.get("posterPath", "")
if not poster.is_file() or poster.stat().st_size < 100_000:
    fail("first-frame poster is missing or too small")
if sha256(poster) != frames[0].get("sha256"):
    fail("first-frame poster is not byte-identical to frame zero")

encode = read_json(CREATIVE / "encode-manifest.json")
policy = encode.get("matchedEncodePolicy", {})
expected_policy = {
    "container": "MP4",
    "codec": "H.264/libx264",
    "width": 1280,
    "height": 800,
    "frameRate": 30,
    "frameCount": 540,
    "durationSeconds": 18,
    "preset": "medium",
    "crf": 21,
    "profile": "high",
    "level": "4.1",
    "pixelFormat": "yuv420p",
    "bFrames": 0,
    "sceneCutDetection": False,
    "fastStart": True,
    "audio": False,
}
if policy != expected_policy:
    fail("GOP comparison changed more than the keyframe interval")
if encode.get("sourceCombinedFrameSha256") != render.get("combinedFrameSha256"):
    fail("encoded variants are not bound to the rendered frame set")

expected_variants = {
    "gop3": (3, 180),
    "gop6": (6, 90),
    "gop10": (10, 54),
}
variants = encode.get("variants", [])
if [item.get("id") for item in variants] != list(expected_variants):
    fail("encode manifest must contain GOP 3, 6 and 10 in order")
for item in variants:
    expected_gop, expected_keyframes = expected_variants[item["id"]]
    asset = ROOT / item.get("path", "")
    if not asset.is_file():
        fail(f"video asset is missing: {item.get('path')}")
    if item.get("gop") != expected_gop or item.get("keyframeCount") != expected_keyframes:
        fail(f"{item['id']} has the wrong keyframe structure")
    if asset.stat().st_size != item.get("bytes") or sha256(asset) != item.get("sha256"):
        fail(f"{item['id']} size or SHA-256 evidence does not match")
    if asset.stat().st_size >= 100 * 1024 * 1024:
        fail(f"{item['id']} exceeds the repository asset ceiling")
    if (
        item.get("codec") != "h264"
        or item.get("codecType") != "video"
        or item.get("width") != 1280
        or item.get("height") != 800
        or item.get("frameRate") != "30/1"
        or item.get("durationSeconds") != 18
        or item.get("frameCount") != 540
        or item.get("audioStreamCount") != 0
    ):
        fail(f"{item['id']} does not match the approved media profile")

benchmark = read_json(CREATIVE / "browser-benchmark.json")
poster_state = benchmark.get("posterBeforeVideo", {})
if (
    poster_state.get("posterVisible") is not True
    or poster_state.get("posterNaturalWidth") != 1280
    or poster_state.get("posterNaturalHeight") != 800
    or poster_state.get("videoReadyState") != 0
    or poster_state.get("videoOpacity") != "0"
):
    fail("poster-before-video evidence does not prove an immediate static first frame")
for evidence_path in (
    poster_state.get("evidencePath", ""),
    benchmark.get("midScrollEvidencePath", ""),
):
    evidence = ROOT / evidence_path
    if not evidence.is_file() or evidence.stat().st_size < 100_000:
        fail(f"browser screenshot evidence is missing: {evidence_path}")

bench_variants = benchmark.get("variants", [])
if [item.get("variant") for item in bench_variants] != list(expected_variants):
    fail("browser benchmark does not contain all matched GOP variants")
for item in bench_variants:
    if item.get("cacheMode") != "cold isolated browser context":
        fail(f"{item['variant']} did not use an isolated cold context")
    if item.get("viewport") != {"width": 1280, "height": 800, "dpr": 1}:
        fail(f"{item['variant']} changed the comparison viewport")
    media = item.get("media", {})
    seekable = media.get("seekable", [])
    if (
        not math.isclose(media.get("duration", 0), 18, abs_tol=0.01)
        or media.get("seekConfirmation") != "seeked + two animation frames"
        or len(seekable) != 1
        or seekable[0].get("start") != 0
        or not math.isclose(seekable[0].get("end", 0), 18, abs_tol=0.01)
    ):
        fail(f"{item['variant']} is not fully seekable under the measured server")
    if item.get("controller", {}).get("timeoutCount") != 0:
        fail(f"{item['variant']} contains a seek timeout")
    if item.get("consoleErrors") or item.get("pageErrors") or item.get("failedRequests"):
        fail(f"{item['variant']} contains browser failures")
    if not 0 <= item.get("firstVideoFrameMs", -1) < 1000:
        fail(f"{item['variant']} first video frame is unbounded")
    for direction in ("forward", "reverse"):
        result = item.get(direction, {})
        if result.get("count") != 11:
            fail(f"{item['variant']} lacks eleven {direction} targets")
        if result.get("latencyP95Ms", math.inf) >= 250:
            fail(f"{item['variant']} {direction} P95 seek exceeds 250 ms")
        if result.get("displayedErrorMaxMs", math.inf) >= 18.4:
            fail(f"{item['variant']} {direction} exceeds one-frame time error")
    rapid = item.get("rapid", {})
    if (
        rapid.get("submittedTargetCount") != 7
        or not 0 < rapid.get("committedSeekDelta", 0) < 7
        or rapid.get("elapsedMs", math.inf) >= 500
        or rapid.get("errorSeconds", math.inf) >= 0.0184
    ):
        fail(f"{item['variant']} does not prove bounded seek coalescing")

route_html = (ROUTE / "index.html").read_text(encoding="utf-8")
route_js = (ROUTE / "app.mjs").read_text(encoding="utf-8")
if "<video" not in route_html or 'id="poster"' not in route_html:
    fail("experiment route lacks layered poster and video surfaces")
for token in ("video.currentTime = targetTime", "confirmPausedSeekFrame", "SHOTS"):
    if token not in route_js:
        fail(f"experiment route lacks required behavior: {token}")

allowed_paths = {
    "ACCEPTANCE.md",
    "AGENTS.md",
    "creative/control-valve/advertising-reference-board.md",
    "creative/control-valve/camera-path.json",
    "creative/control-valve/camera-previs.json",
    "creative/control-valve/creative-development.json",
    "creative/control-valve/creative-routes.md",
    "creative/control-valve/five-shot-script.md",
    "creative/control-valve/generate-camera-previs.mjs",
    "creative/control-valve/render-evidence.json",
    "creative/control-valve-video/browser-benchmark.json",
    "creative/control-valve-video/encode-manifest.json",
    "creative/control-valve-video/experiment-report.md",
    "creative/control-valve-video/render-manifest.json",
    "docs/control-valve-video/app.mjs",
    "docs/control-valve-video/assets/control-valve-gop10.mp4",
    "docs/control-valve-video/assets/control-valve-gop3.mp4",
    "docs/control-valve-video/assets/control-valve-gop6.mp4",
    "docs/control-valve-video/assets/first-frame.png",
    "docs/control-valve-video/evidence/gop6-mid-scroll.png",
    "docs/control-valve-video/evidence/poster-before-video.png",
    "docs/control-valve-video/index.html",
    "docs/control-valve-video/styles.css",
    "docs/control-valve/app.mjs",
    "docs/control-valve/assets/first-frame-poster.jpg",
    "docs/control-valve/camera-path.json",
    "docs/control-valve/evidence/control-valve-grey-animatic.webm",
    "docs/control-valve/evidence/shot-01-core-suspended.png",
    "docs/control-valve/evidence/shot-01-product-authority.png",
    "docs/control-valve/evidence/shot-02-axial-command.png",
    "docs/control-valve/evidence/shot-02-precision-nested.png",
    "docs/control-valve/evidence/shot-03-body-encloses.png",
    "docs/control-valve/evidence/shot-03-cascade-revealed.png",
    "docs/control-valve/evidence/shot-04-assembly-complete.png",
    "docs/control-valve/evidence/shot-04-systems-in-order.png",
    "docs/control-valve/evidence/shot-05-product-presence.png",
    "docs/control-valve/evidence/shot-05-product-resolved.png",
    "docs/control-valve/evidence/validation-closure-complete.png",
    "docs/control-valve/evidence/validation-closure-mid.png",
    "docs/control-valve/evidence/validation-closure-start.png",
    "docs/control-valve/evidence/validation-trim-mid-assembly.png",
    "docs/control-valve/evidence/validation-trim-separated.png",
    "docs/control-valve/index.html",
    "docs/control-valve/styles.css",
    "governance/project-rules.json",
    "governance/project-validation.json",
    "scripts/benchmark_control_valve_video_scrub.mjs",
    "scripts/capture_control_valve_animatic.mjs",
    "scripts/encode_control_valve_video_variants.mjs",
    "scripts/render_control_valve_video_frames.mjs",
    "scripts/serve_pages_with_ranges.mjs",
    "scripts/validate_control_valve_animatic.py",
    "scripts/validate_control_valve_shot_script.py",
    "scripts/validate_control_valve_video_experiment.py",
}
changed = set()
for command in (
    ["git", "diff", "--name-only", "origin/main...HEAD"],
    ["git", "diff", "--name-only"],
    ["git", "diff", "--name-only", "--cached"],
    ["git", "ls-files", "--others", "--exclude-standard"],
):
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    changed.update(
        line.strip().replace("\\", "/")
        for line in result.stdout.splitlines()
        if line.strip()
    )
unexpected = sorted(changed - allowed_paths)
if unexpected:
    fail(f"video experiment changed forbidden paths: {', '.join(unexpected)}")

print(
    "PASS: matched GOP 3/6/10 assets, byte-identical static poster, "
    "fully seekable media, bounded coalescing and error-free bidirectional "
    "browser seeking are proven"
)
