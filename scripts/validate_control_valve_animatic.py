#!/usr/bin/env python3

from math import dist

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
if max(abs(frame["camera"]["rollDegrees"]) for frame in frames) > 1e-9:
    fail("every canonical frame must keep a zero-degree camera roll")
if max(frame["transition"]["occlusion"] for frame in frames) > 0.01:
    fail("blackout and hidden-cut occlusion are prohibited")

camera_steps = [
    dist(left["camera"]["position"], right["camera"]["position"])
    for left, right in zip(frames, frames[1:])
]
if max(camera_steps) > 0.08:
    fail("camera contains a teleport or a comfort-breaking per-frame step")
if min(
    dist(frame["camera"]["position"], frame["camera"]["target"])
    for frame in frames
) < 6:
    fail("camera enters the close internal geometry comfort exclusion zone")
fovs = [frame["camera"]["fovDegrees"] for frame in frames]
if max(fovs) - min(fovs) > 3:
    fail("field-of-view range exceeds the restrained comfort contract")

for shot in shots:
    hold = frames[shot["endFrame"] - 23 : shot["endFrame"] + 1]
    reference = hold[0]
    for frame in hold[1:]:
        for section in ("camera", "product", "light"):
            if frame[section] != reference[section]:
                fail(
                    f"shot {shot['id']} lacks a 24-frame comprehension hold "
                    f"in {section}"
                )

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

playback = evidence.get("fullPlayback", {})
if playback.get("completed") is not True:
    fail("fixed-duration browser playback did not reach the final frame")
if playback.get("blackoutElementPresent") is not False:
    fail("runtime still contains a blackout overlay")
if playback.get("observedShotIds") != [shot["id"] for shot in shots]:
    fail("fixed-duration playback did not observe the five shots in script order")

styles = (ROUTE / "styles.css").read_text(encoding="utf-8")
app = (ROUTE / "app.mjs").read_text(encoding="utf-8")
if "#c46a3c" not in styles or "#0c1117" not in styles:
    fail("restrained graphite-and-copper visual direction is not implemented")
if "GROUP_COLORS" not in app or "秩序" not in app:
    fail("runtime lacks the released industrial hierarchy and tonal direction")

print(
    "PASS: five-shot animatic has 480 deterministic zero-roll states, no "
    "blackout or teleport, five comprehension holds, restrained industrial "
    "tone, full playback evidence and a stable final 15% hero hold"
)
