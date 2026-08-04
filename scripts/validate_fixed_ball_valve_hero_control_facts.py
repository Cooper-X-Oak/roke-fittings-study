#!/usr/bin/env python3
"""Validate fixed-ball-valve hero control facts from delivered bridge evidence."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HERO = ROOT / "docs" / "assets" / "ztovalve" / "hero"
GOAL26 = HERO / "goal26-blender-camera-explosion-proof"

EXPECTED_STEP_SHA = "3ddb291607730239f5a067e9d1730acda0931874c5f42c4ac0c358516efa2547"
EXPECTED_BROCHURE_SHA = "5d515a1213d2c943b63754d5eff2029ed326762dd52de4025432398fcd5d5cbf"
EXPECTED_GLB_SHA = "89024869647b3aaf3fe5301694a2753dc87e9dd3d05b41b9c651ef4e9754384b"
EXPECTED_STEP_MESH_SHA = "0326bbf77f186dc9869bd0715d7096f94bad3d502b1b0cab1d93860dcef4888f"
EXPECTED_CHANNELS = {
    "shellSplit",
    "seatSpread",
    "stemLift",
    "lowerDrop",
    "fastenerSpread",
    "ballTurn",
}
EXPECTED_SHOTS = [
    "contracted-presence",
    "axis-made-legible",
    "seat-system-proof",
    "pressure-shell-closes",
    "commercial-hero-hold",
]


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def read_json(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"missing {path.relative_to(ROOT)}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path.relative_to(ROOT)} must be a JSON object")
    return value


def sha256(path: Path) -> str:
    require(path.is_file(), f"missing {path.relative_to(ROOT)}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def delivery_path(production_path: str) -> Path:
    prefix = "docs/assets/ztovalve/hero/"
    require(production_path.startswith(prefix), f"unexpected hero production path: {production_path}")
    return HERO / production_path[len(prefix):]


def validate_source_and_route() -> None:
    audit = read_json(HERO / "model-audit.json")
    step = audit["sourcePreservation"]["step"]
    brochure = audit["sourcePreservation"]["brochure"]
    output = audit["output"]
    conversion = audit["conversion"]
    inspection = audit["glbInspection"]["counts"]

    require(step["sha256"] == EXPECTED_STEP_SHA, "fixed ball valve STEP hash drifted")
    require(brochure["sha256"] == EXPECTED_BROCHURE_SHA, "fixed ball valve brochure hash drifted")
    require(output["sha256"] == EXPECTED_GLB_SHA, "fixed ball valve GLB hash drifted")
    require(conversion["meshBearingNodeCount"] == 138, "STEP-derived mesh-bearing node count drifted")
    require(inspection["meshNodes"] == 138, "GLB mesh node count drifted")
    require(inspection["animations"] == 0 and inspection["cameras"] == 0, "source GLB must remain unanimated and camera-free")

    groups = {group["id"] for group in audit["movableGroups"]}
    require(
        {
            "body-pressure-shell",
            "ball-trunnion-core",
            "stem-packing-drive",
            "seat-seal-system",
            "fasteners-small-hardware",
        }.issubset(groups),
        "semantic movable groups are incomplete",
    )

    require((ROOT / "asset" / "derived" / "fixed-ball-valve" / "source").is_dir(), "derived fixed-ball-valve source folder is missing")
    require(sha256(HERO / "fixed-ball-valve.glb") == EXPECTED_GLB_SHA, "delivered fixed ball valve GLB does not match audit")

    chain = read_json(HERO / "goal18-step-first-input-chain" / "input-chain-manifest.json")
    verdict = chain["verdict"]
    require(verdict["primaryInputForFinalCommercialRender"] == "STEP-first", "commercial render route is not STEP-first")
    require(verdict["currentOperationalFallback"] == "existing audited GLB for lookdev, blocking, and web-preview continuity", "GLB fallback boundary drifted")
    require(verdict["confidence"] == "high", "STEP-first route confidence is no longer high")


def validate_storyboard_and_camera() -> None:
    creative = read_json(HERO / "creative-development.json")
    require(creative["selectedRouteId"] == "axis-to-seal", "selected creative route drifted")
    require([shot["id"] for shot in creative["shots"]] == EXPECTED_SHOTS, "creative shot order drifted")
    require(creative["cameraPrevis"]["totalFrames"] == 24, "review animatic frame count drifted")
    require(creative["animatic"]["durationSeconds"] == 2.0, "24-frame animatic duration drifted")

    camera = read_json(HERO / "camera-previs-240.json")
    require(camera["fps"] == 30, "camera previs fps drifted")
    require(camera["totalFrames"] == 240, "camera previs frame count drifted")
    require(camera["durationSeconds"] == 8.0, "camera previs duration drifted")
    require([item["shotId"] for item in camera["shotBoundaries"]] == EXPECTED_SHOTS, "camera shot boundary order drifted")
    require(camera["maxAbsRollDegrees"] <= 3, "camera roll envelope drifted")
    require(len(camera["frameStates"]) == 240, "camera previs must define every canonical frame")
    require(camera["frameStates"][0]["frame"] == 0, "camera previs first frame drifted")
    require(camera["frameStates"][-1]["frame"] == 239, "camera previs last frame drifted")


def validate_motion_and_blender_proof() -> None:
    control = read_json(GOAL26 / "motion-control.json")
    manifest = read_json(GOAL26 / "render-manifest.json")

    require(control["product"] == "ztovalve fixed ball valve", "motion control product drifted")
    require(control["sourceBoundary"]["notControlValve"] is True, "fixed ball valve proof must stay separate from control-valve assets")
    require(control["sourceBoundary"]["homepageChanged"] is False, "Goal26 must not change homepage")
    require(control["sourceBoundary"]["finalHeroAssetsChanged"] is False, "Goal26 must not replace final hero assets")

    require(control["sources"]["stepMesh"] == "docs/assets/ztovalve/hero/goal20-blender-cycles-step-proof/goal20-step-mesh.glb", "Goal26 step mesh source drifted")
    require(control["sources"]["cameraPrevis"] == "docs/assets/ztovalve/hero/camera-previs-240.json", "Goal26 camera previs source drifted")
    require(set(control["partChannels"]) == EXPECTED_CHANNELS, "motion control channel set drifted")
    require(control["partChannels"]["ballTurn"]["degrees"] == 90, "ball turn is no longer a quarter turn")
    require("progress - 0.18" in control["stateSampler"]["exploded"], "exploded sampler start drifted")
    require("progress - 0.46" in control["stateSampler"]["ballTurn"], "ball-turn sampler start drifted")
    require(control["axisMap"]["threeToBlender"] == {"x": "x", "y": "z", "z": "-y"}, "Three.js-to-Blender axis map drifted")

    require(manifest["product"] == "ztovalve fixed ball valve", "Goal26 render manifest product drifted")
    require(manifest["renderer"] == "Blender Cycles", "Goal26 renderer must remain Blender Cycles")
    require(manifest["sourceBoundary"]["stepMesh"] == control["sources"]["stepMesh"], "manifest/control step mesh mismatch")
    require(manifest["sourceBoundary"]["cameraPrevis"] == control["sources"]["cameraPrevis"], "manifest/control camera mismatch")
    require(manifest["sourceBoundary"]["motionControl"] == "docs/assets/ztovalve/hero/goal26-blender-camera-explosion-proof/motion-control.json", "manifest motion-control source drifted")
    require(manifest["sourceBoundary"]["stepMeshSha256"] == EXPECTED_STEP_MESH_SHA, "STEP-derived Goal20 mesh hash drifted")
    require(sha256(delivery_path(manifest["sourceBoundary"]["stepMesh"])) == EXPECTED_STEP_MESH_SHA, "delivered STEP-derived mesh file hash drifted")
    require(sha256(HERO / "camera-previs-240.json") == manifest["sourceBoundary"]["cameraPrevisSha256"], "camera-previs-240 hash mismatch")
    require(sha256(GOAL26 / "motion-control.json") == manifest["sourceBoundary"]["motionControlSha256"], "Goal26 motion-control hash mismatch")

    profile = manifest["renderProfile"]
    require(profile["homepageConnected"] is False, "Goal26 proof must not be connected to homepage")
    require(profile["frameSequenceRendered"] is False, "Goal26 proof must not render final frame sequence")
    require(profile["heroAvifReplaced"] is False, "Goal26 proof must not replace hero AVIF")
    require(profile["renderedFrameCount"] >= 4, "Goal26 must retain at least four proof frames")

    require(set(manifest["controlledChannels"]) == EXPECTED_CHANNELS, "render manifest channel set drifted")
    evidence = manifest["proofEvidence"]
    require(evidence["cameraControlVerified"] is True, "camera control is not verified")
    require(evidence["partMotionControlVerified"] is True, "part motion control is not verified")
    require(evidence["ballTurnControlVerified"] is True, "ball turn control is not verified")
    require(evidence["maxBallAngleDegrees"] >= 85, "ball turn proof angle is too small")

    still_frames = [still["frame"] for still in manifest["stills"]]
    require(still_frames == [0, 72, 136, 216], "Goal26 smoke proof frames drifted")
    for still in manifest["stills"]:
        require(delivery_path(still["path"]).is_file(), f"missing proof still mapped from {still['path']}")
        require(still["camera"]["source"] == control["sources"]["cameraPrevis"], "proof still camera source mismatch")
        require(set(still["channels"]) == {"exploded", *EXPECTED_CHANNELS}, "proof still channel set drifted")


def validate_hero_composition() -> None:
    page = read_json(HERO / "homepage-verification.json")
    require(page["desktop"]["firstProbe"]["exists"] is True, "desktop hero first view probe is missing")
    require(page["desktop"]["firstProbe"]["classReady"] is True, "desktop hero first view is not ready")
    require(page["desktop"]["scrolledProbe"]["exists"] is True, "desktop scrolled probe is missing")
    require(page["desktop"]["catalogLink"]["text"] == "查看产品", "catalog action text drifted")
    require("/catalog/" in page["desktop"]["catalogLink"]["href"], "catalog action href drifted")
    require(page["mobile"]["probe"]["desktopHeroVisible"] is False, "mobile should use fallback instead of desktop hero")
    require(page["mobile"]["probe"]["complete"] is True, "mobile fallback image is not complete")
    require(page["mobile"]["probe"]["naturalWidth"] == 1920, "mobile fallback width drifted")
    require(page["mobile"]["probe"]["naturalHeight"] == 1080, "mobile fallback height drifted")
    require(page["consoleErrors"] == [], "homepage verification has console errors")
    require(page["pageErrors"] == [], "homepage verification has page errors")


def main() -> int:
    validate_source_and_route()
    validate_storyboard_and_camera()
    validate_motion_and_blender_proof()
    validate_hero_composition()
    print("PASS: fixed-ball-valve hero delivered source, route, motion, storyboard, camera and composition control facts are bound")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
