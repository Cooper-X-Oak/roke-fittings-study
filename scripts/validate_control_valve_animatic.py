#!/usr/bin/env python3

from control_valve_validation import CREATIVE, ROOT, ROUTE, fail, read_json


previs = read_json(CREATIVE / "camera-previs.json")
path = read_json(CREATIVE / "camera-path.json")
evidence = read_json(CREATIVE / "render-evidence.json")
frames = previs.get("frames", [])
shots = path.get("shots", [])

if previs.get("fps") != 30 or previs.get("totalFrames") != 480:
    fail("canonical animatic must remain 16 seconds at 30 fps")
if len(frames) != 480 or [frame.get("frame") for frame in frames] != list(range(480)):
    fail("camera previs must contain one ordered state for every frame")
if len(shots) != 5:
    fail("animatic must contain exactly five authored shots")
if shots[0].get("startFrame") != 0 or shots[-1].get("endFrame") != 479:
    fail("five shots must cover the canonical timeline")
for left, right in zip(shots, shots[1:]):
    if left.get("endFrame") + 1 != right.get("startFrame"):
        fail("shot boundaries contain a gap or overlap")

required_state_paths = (
    ("camera", "position"),
    ("camera", "target"),
    ("camera", "rollDegrees"),
    ("camera", "fovDegrees"),
    ("camera", "focusDistance"),
    ("product", "explode"),
    ("product", "bodyOpacity"),
    ("product", "stemStroke"),
    ("product", "cascadeStage"),
    ("light", "key"),
    ("light", "rim"),
    ("transition", "occlusion"),
)
for frame in frames:
    for section, key in required_state_paths:
        if key not in frame.get(section, {}):
            fail(f"frame {frame.get('frame')} misses {section}.{key}")
if max(abs(frame["camera"]["rollDegrees"]) for frame in frames) > 4:
    fail("camera roll exceeds the released 4 degree limit")
if frames[150]["transition"]["occlusion"] < 0.95 or frames[151]["transition"]["occlusion"] < 0.95:
    fail("the only hidden camera relocation lacks authored occlusion")

hold = frames[408:480]
reference = hold[0]
for frame in hold[1:]:
    for section in ("camera", "product", "light"):
        if frame[section] != reference[section]:
            fail(f"stable hero hold drifts at frame {frame['frame']} in {section}")

required_files = (
    ROUTE / "index.html",
    ROUTE / "styles.css",
    ROUTE / "app.mjs",
    ROUTE / "camera-path.json",
    ROUTE / "assets/first-frame-poster.jpg",
)
for artifact in required_files:
    if not artifact.is_file() or artifact.stat().st_size < 256:
        fail(f"missing or empty runtime artifact: {artifact.name}")
captures = evidence.get("captures", [])
if {item.get("shotId") for item in captures} != {shot["id"] for shot in shots}:
    fail("render evidence must include one capture for every shot")
for capture in captures:
    image = ROOT / capture.get("path", "")
    if not image.is_file() or image.stat().st_size < 1000:
        fail(f"rendered shot evidence is missing: {capture.get('path')}")

print(
    "PASS: five-shot animatic has 480 deterministic states, a motivated "
    "occlusion cut, rendered evidence and a stable final 15% hero hold"
)
