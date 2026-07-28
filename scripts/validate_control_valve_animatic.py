#!/usr/bin/env python3
"""Current compact commercial control-valve story contract."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = json.loads((ROOT / "creative/control-valve/camera-path.json").read_text(encoding="utf-8"))
previs = json.loads((ROOT / "creative/control-valve/camera-previs.json").read_text(encoding="utf-8"))
expected = ["core-suspended", "precision-nested", "body-encloses", "assembly-complete", "product-presence"]

def fail(message): raise SystemExit(f"FAIL: {message}")
if (path.get("fps"), path.get("totalFrames"), path.get("durationSeconds")) != (30, 330, 11): fail("compact commercial story must be 330 frames at 30 fps / 11 seconds")
if [item["id"] for item in path["shots"]] != expected: fail("five cognitive beats must remain ordered")
if path["shots"][0]["startFrame"] != 0 or path["shots"][-1]["endFrame"] != 329: fail("beats must cover complete compact timeline")
if path.get("stableHeroFromFrame") is not None: fail("commercial story must not retain a final hero hold")
if len(previs.get("frames", [])) != 330 or [frame["frame"] for frame in previs["frames"]] != list(range(330)): fail("previs must contain every compact frame")
for left, right in zip(path["shots"], path["shots"][1:]):
    if left["endFrame"] + 1 != right["startFrame"]: fail("beat boundaries must be contiguous")
last = previs["frames"][-1]
previous = previs["frames"][-2]
if last["camera"] == previous["camera"] and last["product"] == previous["product"]: fail("final product resolve must continue moving to the exit")
if max(abs(frame["camera"]["rollDegrees"]) for frame in previs["frames"]) != 0: fail("camera roll must remain zero")
if any(not math.isfinite(value) for frame in previs["frames"] for value in [*frame["camera"]["position"], *frame["camera"]["target"]]): fail("camera path contains non-finite value")
targets = {tuple(frame["camera"]["target"]) for frame in previs["frames"]}
if targets != {(0, 0, 0)}: fail("camera target must stay locked on the product axis")
distances = [frame["camera"]["focusDistance"] for frame in previs["frames"]]
if any(right < left for left, right in zip(distances, distances[1:])): fail("camera must only travel from near to far")
yaws = [frame["product"]["productYawDegrees"] for frame in previs["frames"]]
if abs(yaws[0]) > 0.01 or abs(yaws[-1] - 180) > 0.01 or any(right < left for left, right in zip(yaws, yaws[1:])): fail("product must complete a continuous 180 degree vertical-axis turn")
print("PASS: 330-frame compact commercial story retains five beats, continuous axis and no terminal hold")
