#!/usr/bin/env python3

import json
import math
import subprocess
from math import dist
from pathlib import Path

from control_valve_validation import CREATIVE, ROOT, ROUTE, fail, read_json


previs = read_json(CREATIVE / "camera-previs.json")
path = read_json(CREATIVE / "camera-path.json")
plan = read_json(CREATIVE / "creative-development.json")
evidence = read_json(CREATIVE / "render-evidence.json")
frames = previs.get("frames", [])
shots = path.get("shots", [])
expected_ids = [
    "core-suspended",
    "precision-nested",
    "body-encloses",
    "assembly-complete",
    "product-presence",
]

if previs.get("fps") != 30 or previs.get("totalFrames") != 540:
    fail("canonical grey animatic must be exactly 18 seconds at 30 fps")
if previs.get("durationSeconds") != 18:
    fail("camera previs duration must remain 18 seconds")
if len(frames) != 540 or [frame.get("frame") for frame in frames] != list(
    range(540)
):
    fail("camera previs must contain one ordered state for every frame")
if [shot.get("id") for shot in shots] != expected_ids:
    fail("animatic must contain the five approved story-beat IDs in order")
if shots[0].get("startFrame") != 0 or shots[-1].get("endFrame") != 539:
    fail("five beats must cover the canonical timeline")
for left, right in zip(shots, shots[1:]):
    if left.get("endFrame") + 1 != right.get("startFrame"):
        fail("story-beat boundaries contain a gap or overlap")

required_state_paths = (
    ("camera", "position"),
    ("camera", "target"),
    ("camera", "rollDegrees"),
    ("camera", "fovDegrees"),
    ("camera", "focusDistance"),
    ("product", "trimAssembly"),
    ("product", "stemAssembly"),
    ("product", "bodyClosure"),
    ("product", "bodyOpacity"),
    ("product", "actuatorAssembly"),
    ("product", "detailAssembly"),
    ("product", "productYawDegrees"),
    ("product", "coreEmphasis"),
    ("light", "key"),
    ("light", "rim"),
    ("light", "core"),
    ("transition", "occlusion"),
)
for frame in frames:
    for section, key in required_state_paths:
        if key not in frame.get(section, {}):
            fail(f"frame {frame.get('frame')} misses {section}.{key}")
    scalars = [
        frame["camera"]["rollDegrees"],
        frame["camera"]["fovDegrees"],
        frame["camera"]["focusDistance"],
        frame["product"]["stemAssembly"],
        frame["product"]["bodyClosure"],
        frame["product"]["bodyOpacity"],
        frame["product"]["actuatorAssembly"],
        frame["product"]["detailAssembly"],
        frame["product"]["productYawDegrees"],
        frame["product"]["coreEmphasis"],
        frame["light"]["key"],
        frame["light"]["rim"],
        frame["light"]["core"],
        frame["transition"]["occlusion"],
        *frame["camera"]["position"],
        *frame["camera"]["target"],
        *frame["product"]["trimAssembly"],
    ]
    if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in scalars):
        fail(f"frame {frame['frame']} contains a non-finite state")
    if len(frame["product"]["trimAssembly"]) != 4:
        fail(f"frame {frame['frame']} must control exactly four trim islands")

if max(abs(frame["camera"]["rollDegrees"]) for frame in frames) > 1e-9:
    fail("every canonical frame must keep a zero-degree camera roll")
if max(frame["transition"]["occlusion"] for frame in frames) > 1e-9:
    fail("blackout and hidden-cut occlusion are prohibited")
if previs.get("mechanicalAxisWorld") != [0, 1, 0]:
    fail("camera previs must declare one vertical world-space mechanical axis")

camera_steps = [
    dist(left["camera"]["position"], right["camera"]["position"])
    for left, right in zip(frames, frames[1:])
]
if max(camera_steps) > 0.12:
    fail("camera contains a teleport or comfort-breaking per-frame step")
target_steps = [
    dist(left["camera"]["target"], right["camera"]["target"])
    for left, right in zip(frames, frames[1:])
]
if max(target_steps) > 0.04:
    fail("camera target jumps away from the continuous mechanical axis")

camera_path_length = sum(camera_steps)
yaw_values = [
    frame["product"]["productYawDegrees"]
    for frame in frames
]
product_yaw_range = max(yaw_values) - min(yaw_values)
if camera_path_length < 10:
    fail("camera path remains too restrained for the kinetic Animatic")
if product_yaw_range < 20:
    fail("product observation angle does not change materially")

coordinated_flags = []
for left, right, camera_step in zip(frames, frames[1:], camera_steps):
    product_delta = (
        dist(
            left["product"]["trimAssembly"],
            right["product"]["trimAssembly"],
        )
        + abs(left["product"]["stemAssembly"] - right["product"]["stemAssembly"])
        + abs(left["product"]["bodyClosure"] - right["product"]["bodyClosure"])
        + abs(
            left["product"]["actuatorAssembly"]
            - right["product"]["actuatorAssembly"]
        )
        + abs(left["product"]["detailAssembly"] - right["product"]["detailAssembly"])
        + abs(
            left["product"]["productYawDegrees"]
            - right["product"]["productYawDegrees"]
        )
    )
    coordinated_flags.append(camera_step > 0.001 and product_delta > 0.001)
coordinated_intervals = sum(
    active and (index == 0 or not coordinated_flags[index - 1])
    for index, active in enumerate(coordinated_flags)
)
if coordinated_intervals < 4:
    fail("camera and product motion lack four authored handoff intervals")

for shot in shots:
    hold_length = 12 if shot["id"] != "product-presence" else 81
    hold = frames[shot["endFrame"] - hold_length + 1 : shot["endFrame"] + 1]
    reference = hold[0]
    for frame in hold[1:]:
        for section in ("camera", "product", "light"):
            if frame[section] != reference[section]:
                fail(
                    f"beat {shot['id']} lacks its authored comprehension hold "
                    f"in {section}"
                )

stable_start, stable_end = previs.get("stableHeroHold", [None, None])
if [stable_start, stable_end] != [459, 539]:
    fail("final fifteen-percent hero hold must be frames 459 through 539")
hero_hold = frames[stable_start : stable_end + 1]
reference = hero_hold[0]
for frame in hero_hold[1:]:
    for section in ("camera", "product", "light"):
        if frame[section] != reference[section]:
            fail(f"stable hero hold drifts at frame {frame['frame']} in {section}")

staged_trim_states = {
    76: [0, 0, 0, 0],
    104: [1, 0, 0, 0],
    132: [1, 1, 0, 0],
    160: [1, 1, 1, 0],
    184: [1, 1, 1, 1],
}
for frame_index, expected in staged_trim_states.items():
    if frames[frame_index]["product"]["trimAssembly"] != expected:
        fail(f"frame {frame_index} does not prove staged four-island assembly")

geometry = evidence.get("geometry", {})
if geometry.get("trimConnectedComponentCount") != 4:
    fail("rendered GLB evidence must expose exactly four trim geometry islands")
if geometry.get("independentlyTransformable") is not True:
    fail("lighting-only trim stages do not count as independent separation")
diagnostics = geometry.get("trimDiagnostics", [])
if len(diagnostics) != 4 or any(
    item.get("triangleCount", 0) <= 0 for item in diagnostics
):
    fail("every extracted trim geometry island must contain real triangles")
if "individual STEP cage/seat identity is not asserted" not in geometry.get(
    "labelBoundary", ""
):
    fail("geometry evidence must preserve the trim-island label truth boundary")

separation = evidence.get("separation", {})
if separation.get("distinctAxisPositions") != 4:
    fail("separated trim evidence must show four distinct axis positions")
if separation.get("maximumRadialAxisError", 1) > 0.002:
    fail("trim separation leaves the declared central mechanical axis")
if separation.get("allProjectedOnScreen") is not True:
    fail("the separated trim layers are not all visible in the authored frame")
if separation.get("axisSpan", 0) < 3:
    fail("trim separation span remains too small for a legible commercial beat")

motion = evidence.get("motionAmplitude", {})
if motion.get("cameraPathLength", 0) < 10:
    fail("browser evidence does not prove the enhanced camera path")
if motion.get("maximumCameraStep", 1) > 0.12:
    fail("enhanced camera path exceeds the comfort step bound")
if motion.get("maximumTargetStep", 1) > 0.04:
    fail("enhanced camera target exceeds the continuous-axis bound")
if motion.get("productYawRange", 0) < 20:
    fail("browser evidence does not prove a multi-angle product presentation")
if motion.get("coordinatedIntervalCount", 0) < 4:
    fail("browser evidence lacks coordinated camera/product action intervals")
if motion.get("actuatorTravel", 0) < 1.5:
    fail("actuator descent and seating travel remains visually insignificant")

closure_samples = evidence.get("closureSamples", [])
if [sample.get("id") for sample in closure_samples] != [
    "closure-start",
    "closure-mid",
    "closure-complete",
]:
    fail("closure evidence must include start, middle and completed samples")
opacities = [sample.get("bodyOpacity") for sample in closure_samples]
closures = [sample.get("bodyClosure") for sample in closure_samples]
if opacities != sorted(opacities) or closures != sorted(closures):
    fail("body closure and opacity must progress monotonically")
if opacities[0] >= 0.35 or opacities[1] >= 0.75 or opacities[-1] < 0.95:
    fail("body closure lacks a readable-core interval before final enclosure")
for sample in closure_samples[:2]:
    if sample.get("occlusion") != 0:
        fail("body closure uses a blackout or full-frame occlusion")
    if not all(sample.get("trimProjectedOnScreen", [])):
        fail("the complete trim core leaves the screen before enclosure is established")

forward = evidence.get("forwardPlayback", {})
reverse = evidence.get("reversePlayback", {})
if forward.get("completed") is not True:
    fail("canonical forward playback did not complete")
if reverse.get("completed") is not True:
    fail("canonical reverse playback did not complete")
if forward.get("observedShotIds") != expected_ids:
    fail("forward playback did not observe the approved five beats in order")
if reverse.get("observedShotIds") != list(reversed(expected_ids)):
    fail("reverse playback did not observe the exact reverse beat order")
if any(
    sample.get("occlusion") != 0
    for sample in forward.get("samples", []) + reverse.get("samples", [])
):
    fail("canonical playback contains non-zero full-frame occlusion")

round_trip = evidence.get("roundTrip", {})
for key in (
    "progress022CameraMaxDelta",
    "progress022ProductMaxDelta",
    "progress022TrimTransformMaxDelta",
    "progress067CameraMaxDelta",
    "progress067ProductMaxDelta",
):
    if round_trip.get(key) != 0:
        fail(f"forward-back-forward sampling drifts in {key}")

captures = evidence.get("captures", [])
if [capture.get("shotId") for capture in captures] != expected_ids:
    fail("render evidence must include one current capture for every approved beat")
if any(capture.get("runtimeShotId") != capture.get("shotId") for capture in captures):
    fail("a captured keyframe does not match its authored beat")
for collection in (captures, evidence.get("validationFrames", [])):
    for capture in collection:
        image = ROOT / capture.get("path", "")
        if not image.is_file() or image.stat().st_size < 1000:
            fail(f"rendered evidence is missing: {capture.get('path')}")

video = evidence.get("video", {})
video_path = ROOT / video.get("path", "")
if (
    video.get("canonicalDurationSeconds") != 18
    or not video_path.is_file()
    or video_path.stat().st_size < 100_000
):
    fail("fixed-duration grey Animatic video is missing or too small")

if evidence.get("consoleErrors") or evidence.get("pageErrors") or evidence.get(
    "failedRequests"
):
    fail("browser evidence contains console, page or request failures")

camera_previs_record = plan.get("cameraPrevis", {})
animatic_record = plan.get("animatic", {})
if (
    camera_previs_record.get("fps") != 30
    or camera_previs_record.get("totalFrames") != 540
    or camera_previs_record.get("frameStateCount") != 540
    or camera_previs_record.get("reviewed") is not True
):
    fail("creative-development camera-previs record is incomplete")
if (
    animatic_record.get("durationSeconds") != 18
    or animatic_record.get("reviewed") is not True
    or animatic_record.get("uri") != video.get("path")
):
    fail("creative-development Animatic record is not bound to rendered video")
if plan.get("confirmation") != {"status": "pending"}:
    fail("automatic creative release must remain pending in this phase")

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
    "docs/control-valve/app.mjs",
    "docs/control-valve/assets/first-frame-poster.jpg",
    "docs/control-valve/camera-path.json",
    "docs/control-valve/evidence/control-valve-grey-animatic.webm",
    # Explicitly retired predecessor evidence. Deletions are part of the
    # atomic phase replacement; stale shots must not remain current evidence.
    "docs/control-valve/evidence/shot-01-product-authority.png",
    "docs/control-valve/evidence/shot-02-axial-command.png",
    "docs/control-valve/evidence/shot-03-cascade-revealed.png",
    "docs/control-valve/evidence/shot-04-systems-in-order.png",
    "docs/control-valve/evidence/shot-05-product-resolved.png",
    "docs/control-valve/evidence/shot-01-core-suspended.png",
    "docs/control-valve/evidence/shot-02-precision-nested.png",
    "docs/control-valve/evidence/shot-03-body-encloses.png",
    "docs/control-valve/evidence/shot-04-assembly-complete.png",
    "docs/control-valve/evidence/shot-05-product-presence.png",
    "docs/control-valve/evidence/validation-trim-separated.png",
    "docs/control-valve/evidence/validation-trim-mid-assembly.png",
    "docs/control-valve/evidence/validation-closure-start.png",
    "docs/control-valve/evidence/validation-closure-mid.png",
    "docs/control-valve/evidence/validation-closure-complete.png",
    "docs/control-valve/index.html",
    "docs/control-valve/styles.css",
    "docs/control-valve-video/app.mjs",
    "docs/control-valve-video/assets/control-valve-gop10.mp4",
    "docs/control-valve-video/assets/control-valve-gop3.mp4",
    "docs/control-valve-video/assets/control-valve-gop6.mp4",
    "docs/control-valve-video/assets/first-frame.png",
    "docs/control-valve-video/evidence/gop6-mid-scroll.png",
    "docs/control-valve-video/evidence/poster-before-video.png",
    "docs/control-valve-video/index.html",
    "docs/control-valve-video/styles.css",
    "governance/project-rules.json",
    "governance/project-validation.json",
    "scripts/capture_control_valve_animatic.mjs",
    "scripts/benchmark_control_valve_video_scrub.mjs",
    "scripts/encode_control_valve_video_variants.mjs",
    "scripts/render_control_valve_video_frames.mjs",
    "scripts/serve_pages_with_ranges.mjs",
    "scripts/validate_control_valve_animatic.py",
    "scripts/validate_control_valve_shot_script.py",
    "scripts/validate_control_valve_video_experiment.py",
    "scripts/validate_control_valve_business_page.py",
}
commands = [
    ["git", "diff", "--name-only", "origin/main...HEAD"],
    ["git", "diff", "--name-only"],
    ["git", "diff", "--name-only", "--cached"],
    ["git", "ls-files", "--others", "--exclude-standard"],
]
changed = set()
for command in commands:
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
    fail(f"grey-animatic phase changed forbidden paths: {', '.join(unexpected)}")

print(
    "PASS: 540 deterministic grey-animatic frames prove four real trim "
    "geometry islands, commercial motion amplitude, five coordinated action "
    "intervals, readable body closure, exact forward/reverse beat order, zero "
    "round-trip drift and a stable final fifteen-percent hero hold"
)
