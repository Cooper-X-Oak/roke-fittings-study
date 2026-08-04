#!/usr/bin/env python3
"""Validate Goal 28 clean PBR stainless + motion fusion preview outputs."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GOAL_DIR = ROOT / "docs" / "assets" / "ztovalve" / "hero" / "goal28-clean-pbr-motion-preview"
MANIFEST = GOAL_DIR / "render-manifest.json"
REQUIRED_CHANNELS = {
    "shellSplit",
    "seatSpread",
    "stemLift",
    "lowerDrop",
    "fastenerSpread",
    "ballTurn",
}
REQUIRED_ZONE_IDS = {
    "G25-SS-CAST-BLASTED-SATIN-01",
    "G25-SS-MACH-FLANGE-RADIAL-01",
    "G25-SS-BRUSH-NO4-LINEAR-01",
    "G25-SS-MACH-BORE-CIRCULAR-01",
    "G25-SS-EDGE-BURNISH-01",
    "G25-SS-MACH-BOLT-BORE-DARK-01",
    "G25-SS-ROOT-DARK-AO-01",
}
REQUIRED_LIGHT_ROLES = {
    "top-left-oblique-key",
    "top-right-oblique-rim",
    "bottom-left-lift",
    "bottom-right-lift",
    "front-fill",
}


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def read_json(path: Path) -> dict:
    require(path.is_file(), f"missing {path.relative_to(ROOT).as_posix()}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path.relative_to(ROOT).as_posix()} must contain a JSON object")
    return value


def project_path(value: str) -> Path:
    require(value and not Path(value).is_absolute(), f"path must be project-relative: {value}")
    path = (ROOT / value).resolve()
    try:
        path.relative_to(ROOT)
    except ValueError:
        fail(f"path escapes project root: {value}")
    return path


def main() -> int:
    manifest = read_json(MANIFEST)
    require(manifest["goalId"] == "goal28-clean-pbr-motion-preview", "unexpected Goal28 id")
    require(manifest["product"] == "ztovalve fixed ball valve", "Goal28 product drifted")

    consumed_sources = json.dumps(manifest["sourceBoundary"], ensure_ascii=False).lower()
    require("control-valve" not in consumed_sources, "Goal28 must not consume control-valve assets")

    for key in (
        "stepMesh",
        "goal20SemanticMap",
        "cameraPrevis",
        "motionControl",
        "goal25dMaterialManifest",
        "goal26RenderManifest",
    ):
        require(project_path(manifest["sourceBoundary"][key]).is_file(), f"missing source {key}")

    profile = manifest["renderProfile"]
    require(profile["sequenceFrameCount"] == 240, "Goal28 must render exactly 240 preview frames")
    require(profile["sourceTotalFrames"] == 240, "Goal28 must consume the 240-frame camera previs")
    require(profile["homepageConnected"] is False, "Goal28 must not connect homepage")
    require(profile["heroAvifReplaced"] is False, "Goal28 must not replace hero AVIF")
    require(profile["published"] is False, "Goal28 must not publish Pages")

    material = manifest["materialFusion"]
    require(material["bodyZoneCount"] == 7, "Goal28 must carry the seven Goal25D material zones")
    require(set(material["zoneMaterialIds"]) == REQUIRED_ZONE_IDS, "Goal28 zone material ids drifted")
    require(material["cleanMainExplicitScratchCurves"] is False, "Goal28 must use clean PBR, not scratch curves")
    require(material["cleanMainExplicitTraceObjectsVisible"] is False, "Goal28 clean main trace visibility drifted")
    require(material["legacyTraceGeometryUsedInGoal28"] is False, "Goal28 must not use legacy trace geometry")
    zone_counts = material["zoneAssignment"]["zoneCounts"]
    require(set(zone_counts) == REQUIRED_ZONE_IDS, "Goal28 body zone assignment is incomplete")
    require(all(count > 0 for count in zone_counts.values()), "Goal28 body zones must all have faces")

    motion = manifest["motionFusion"]
    require(set(motion["controlledChannels"]) == REQUIRED_CHANNELS, "Goal28 motion channel set drifted")
    require(motion["cameraControlVerified"] is True, "Goal28 camera control was not verified")
    require(motion["partMotionControlVerified"] is True, "Goal28 part motion was not verified")
    require(motion["ballTurnControlVerified"] is True, "Goal28 ball turn was not verified")
    require(motion["maxBallAngleDegrees"] > 80, "Goal28 ball turn amplitude is too low")
    require(motion["maxOffset"] > 0.05, "Goal28 exploded motion amplitude is too low")

    lighting = manifest["lighting"]
    require(lighting["removedMirrorReadablePanels"] is True, "Goal28 must remove mirror-readable rectangular panels")
    require(set(item["role"] for item in lighting["rig"]) == REQUIRED_LIGHT_ROLES, "Goal28 lighting roles drifted")
    require(lighting["polishedBallRoughnessRange"][0] >= 0.10, "Goal28 ball roughness is too mirror-like")

    frames = manifest["frames"]
    require(len(frames) == 240, "Goal28 frame records must include 240 frames")
    require([frame["frame"] for frame in frames] == list(range(240)), "Goal28 frame indices must be contiguous 0..239")
    for frame in frames:
        path = project_path(frame["path"])
        require(path.is_file(), f"missing frame {frame['path']}")
        require(path.stat().st_size > 0, f"empty frame {frame['path']}")
        require(set(frame["channels"]) == {"exploded", *REQUIRED_CHANNELS}, f"channel set mismatch at frame {frame['frame']}")

    poster = manifest["previewSurface"]["poster"]
    require(poster is not None and project_path(poster).is_file(), "Goal28 poster is missing")
    index = GOAL_DIR / "index.html"
    status = GOAL_DIR / "motion-material-status.md"
    require(index.is_file(), "Goal28 index.html is missing")
    require(status.is_file(), "Goal28 motion-material-status.md is missing")
    index_text = index.read_text(encoding="utf-8")
    require("frames/frame0000.png" in index_text, "Goal28 index does not reference the frame sequence")
    require("render-manifest.json" in index_text, "Goal28 index does not reference the manifest")

    print("PASS: Goal28 clean PBR stainless material and Goal26 motion fusion preview is complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
