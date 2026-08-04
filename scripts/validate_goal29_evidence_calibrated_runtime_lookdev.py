#!/usr/bin/env python3
"""Validate Goal29 evidence-calibrated runtime lookdev output."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_ROOT = ROOT / "governance" / "control" / "hero-runtime"
GOAL_DIR = ROOT / "docs" / "assets" / "ztovalve" / "hero" / "goal29-evidence-calibrated-runtime-lookdev"
MANIFEST = GOAL_DIR / "render-manifest.json"
REQUIRED_AUTHORITY_FILES = [
    "authority.json",
    "material.json",
    "lighting.json",
    "camera.json",
    "motion.json",
    "storyboard.json",
    "release-gate.json",
]
REQUIRED_FRAMES = [0, 56, 124, 176, 216]
REQUIRED_SHOTS = [
    "fully-exploded-opening",
    "precision-assembly",
    "ball-core-presentation",
    "cutaway-reveal",
    "clear-water-flow-hold",
]
REQUIRED_CHANNELS = {
    "shellClosure",
    "seatSealClosure",
    "stemDriveClosure",
    "lowerSupportClosure",
    "fastenerReturn",
    "springReturn",
    "ballPresentationTurn",
    "cutawayReveal",
    "clearWaterFlow",
}
REFLECTION_SUPPRESSED_GROUPS = {
    "bodyPressureShell",
    "seatSealSystem",
    "stemPackingDrive",
    "fastenersSmallHardware",
}


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def read_json(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"missing {path.relative_to(ROOT)}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path.relative_to(ROOT)} must contain a JSON object")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_runtime_binding(manifest: dict[str, Any]) -> None:
    binding = manifest["runtimeAuthority"]
    authority = read_json(AUTHORITY_ROOT / "authority.json")
    require(binding["authorityId"] == "hero-runtime", "Goal29 runtime authority id drifted")
    require(binding["authorityStatus"] == "current", "Goal29 must bind to current authority")
    require(binding["authorityVersion"] == authority["authority_version"], "Goal29 authority version mismatch")
    require(binding["soleCurrentHeroRenderAuthority"] is True, "Goal29 must bind to sole current hero authority")
    require(binding["nonRuntimeRenderAuthorityAllowed"] is False, "Goal29 allowed non-runtime authority")
    hashes = binding["authorityFileSha256"]
    require(set(hashes) == set(REQUIRED_AUTHORITY_FILES), "Goal29 authority hash file set drifted")
    for name in REQUIRED_AUTHORITY_FILES:
        require(hashes[name] == sha256(AUTHORITY_ROOT / name), f"Goal29 authority hash mismatch for {name}")


def validate_material(manifest: dict[str, Any]) -> None:
    material = manifest["materialDirection"]
    require(material["pbrWorkflow"] == "metallic-roughness-clean-commercial-pbr", "Goal29 PBR workflow drifted")
    require(material["cleanPbr"] is True, "Goal29 clean PBR flag drifted")
    require(material["whiteDiffuseShortcut"] is False, "Goal29 white diffuse shortcut became allowed")
    require(material["explicitScratchGeometryVisible"] is False, "Goal29 scratch geometry became visible")
    require(material["dirtyBlotchNoiseVisible"] is False, "Goal29 dirty blotch noise became visible")
    require(material["dirtyBlotchHighlightsVisible"] is False, "Goal29 dirty blotch highlights became visible")
    require(material["polygonZoneArtifactsVisible"] is False, "Goal29 polygon zone artifacts became visible")
    require(material["productFacingMaterialHardEdgesVisible"] is False, "Goal29 product-facing material hard edges became visible")
    require(material["nonRuntimeMaterialSourceUsed"] is False, "Goal29 used non-runtime material source")
    snapshot = material["materialParameterSnapshot"]["familyMaterials"]
    ball = snapshot["polishedStainlessBall"]
    cast = snapshot["castBlastedStainless"]
    require(0.06 <= ball["roughness"] <= 0.10, "Goal29 polished ball roughness outside authority range")
    require(0.38 <= cast["roughness"] <= 0.46, "Goal29 cast body roughness outside authority range")
    require(max(cast["base_color"][:3]) <= 0.55, "Goal29 cast body base color used white diffuse shortcut")


def validate_lighting(manifest: dict[str, Any]) -> None:
    lighting = manifest["lighting"]
    require(lighting["lightingSeparationModel"] == "background-subject-reflection-contamination-separated", "Goal29 lighting separation model drifted")
    require(lighting["backgroundAsPrimarySubjectLight"] is False, "Goal29 background became primary subject light")
    require(lighting["whiteWorldPrimaryExposure"] is False, "Goal29 white world became primary exposure")
    require(lighting["visibleLightPanelsInCamera"] is False, "Goal29 light panels became camera-visible")
    require(lighting["glossyEquipmentReflectionAllowed"] is False, "Goal29 allowed glossy equipment reflection")
    require(lighting["reflectionCardsGlossyReadableAllowed"] is False, "Goal29 reflector cards became glossy-readable")
    require(lighting["hardWhiteBlotchReflectionAllowed"] is False, "Goal29 hard white blotch reflection became allowed")
    far_lights = [item for item in lighting["rig"] if item["role"] != "ambient-white-studio"]
    require(all(item["size"] >= 10.0 for item in far_lights), "Goal29 far soft light size below authority")
    require(all(item["visibleGlossy"] is False for item in far_lights), "Goal29 driver light became glossy-readable")
    require(all(item["visibleGlossy"] is False for item in lighting["whiteStudioCards"]), "Goal29 studio card became glossy-readable")
    gradient = lighting["reflectionGradientEnvironment"]
    require(gradient["visibleCamera"] is False, "Goal29 gradient environment became camera-visible")
    require(gradient["visibleGlossy"] is True, "Goal29 gradient environment must remain glossy-visible")
    require(gradient["equipmentReadable"] is False, "Goal29 gradient environment became readable equipment")
    retouch = lighting["productGlossyReflectionRetouch"]
    require(retouch["policy"] == "commercial-polished-ball-all-non-ball-product-reflection-isolation", "Goal29 product reflection isolation policy drifted")
    require(set(retouch["suppressedGroups"]).issuperset(REFLECTION_SUPPRESSED_GROUPS), "Goal29 did not suppress all required non-ball reflection groups")
    require(retouch["suppressedCount"] >= manifest["partIdentity"]["meshCount"] - 1, "Goal29 non-ball reflection suppression count too low")
    require(retouch["allowedGlossyProductParts"] == ["球体"], "Goal29 glossy product allow-list drifted")
    require(retouch["visibleInCamera"] is True, "Goal29 suppressed product parts must remain camera-visible")
    require(retouch["visibleInDiffuseAndShadow"] is True, "Goal29 suppressed product parts must keep diffuse/shadow visibility")


def validate_camera_motion_story(manifest: dict[str, Any]) -> None:
    profile = manifest["renderProfile"]
    require(profile["sampleFrames"] == REQUIRED_FRAMES, "Goal29 sample frames drifted")
    require(profile["sequenceFrameCount"] == len(REQUIRED_FRAMES), "Goal29 frame count drifted")
    require(profile["homepageConnected"] is False, "Goal29 must not connect homepage")
    camera = manifest["cameraDirection"]
    require(camera["distanceMultiplier"] >= 2.15, "Goal29 camera distance multiplier below authority")
    require(camera["fovMultiplier"] <= 0.55, "Goal29 camera fov multiplier exceeds authority")
    require(camera["visibleLightPanelsInCamera"] is False, "Goal29 camera sees light panels")
    require([item["phase"] for item in camera["phasePolicy"]] == REQUIRED_SHOTS, "Goal29 camera phase order drifted")

    storyboard = manifest["storyboard"]
    require([item["shot_id"] for item in storyboard["shotOrder"]] == REQUIRED_SHOTS, "Goal29 storyboard order drifted")
    rhythm = storyboard["storyRhythmPolicy"]
    require(rhythm["single_primary_motion"] == "assembly", "Goal29 storyboard primary motion drifted")
    require(rhythm["opening_explosion_motion_allowed"] is False, "Goal29 storyboard allowed opening explosion motion")

    motion = manifest["motionFusion"]
    require(set(motion["controlledChannels"]) == REQUIRED_CHANNELS, "Goal29 motion channel set drifted")
    route = motion["route"]
    initial = motion["initialExplodedRequirements"]
    require(route["initial_state"] == "fully exploded", "Goal29 initial state drifted")
    require(route["initial_assembled_state_allowed"] is False, "Goal29 allowed assembled first frame")
    require(route["explode_then_reassemble_loop_allowed"] is False, "Goal29 allowed round-trip motion")
    require(all(initial.values()), "Goal29 initial exploded requirements are not all true")
    require(motion["maxOffset"] > 0.22, "Goal29 exploded opening amplitude is too low")
    require(motion["maxBallAngleDegrees"] >= 90, "Goal29 ball presentation turn is too low")
    require(motion["maxCutawayReveal"] >= 0.9, "Goal29 cutaway reveal did not complete")
    require(motion["maxClearWaterFlow"] >= 0.9, "Goal29 clear water flow did not complete")

    frames = manifest["frames"]
    require([frame["frame"] for frame in frames] == REQUIRED_FRAMES, "Goal29 frame records drifted")
    require([frame["shotId"] for frame in frames] == REQUIRED_SHOTS, "Goal29 frame shot order drifted")
    first = frames[0]
    final = frames[-1]
    require(first["channels"]["shellClosure"] == 0.0, "Goal29 first frame is not fully exploded")
    require(first["motionEvidence"]["maxOffset"] > 0.22, "Goal29 first frame explosion amplitude too low")
    require(first["motionEvidence"]["movedCounts"].get("bodyPressureShell", 0) >= 3, "Goal29 first frame body shell is not separated")
    require(first["motionEvidence"]["movedCounts"].get("stemPackingDrive", 0) >= 10, "Goal29 first frame upper assembly is not separated")
    require(first["motionEvidence"]["movedCounts"].get("fastenersSmallHardware", 0) >= 100, "Goal29 first frame small hardware is not separated")
    require(final["channels"]["shellClosure"] > 0.98, "Goal29 final frame assembly did not complete")
    require(final["cutaway"]["visible"] is True, "Goal29 final frame cutaway is not visible")
    require(final["clearWaterFlow"]["visible"] is True, "Goal29 final frame clear water flow is not visible")


def validate_release_state(manifest: dict[str, Any]) -> None:
    release = manifest["releaseState"]
    require(release["currentVisualApproval"] is False, "Goal29 must not self-approve visual lookdev")
    require(release["approvedFor240FrameRender"] is False, "Goal29 must keep 240-frame render blocked")
    require(release["approvedForHomepageReplacement"] is False, "Goal29 must keep homepage replacement blocked")
    require(release["approvedForPagesPublication"] is False, "Goal29 must keep Pages publication blocked")
    require(release["nextRequiredMilestone"] == "evidence-calibrated-runtime-lookdev", "Goal29 next milestone drifted")


def validate_files(manifest: dict[str, Any]) -> None:
    require((GOAL_DIR / "index.html").is_file(), "Goal29 preview index missing")
    require((GOAL_DIR / "lookdev-status.md").is_file(), "Goal29 lookdev status missing")
    for frame in manifest["frames"]:
        path = ROOT / frame["path"]
        require(path.is_file(), f"missing frame {frame['path']}")
        require(path.stat().st_size == frame["bytes"], f"frame byte count mismatch: {frame['path']}")
        require(sha256(path) == frame["sha256"], f"frame hash mismatch: {frame['path']}")


def main() -> None:
    manifest = read_json(MANIFEST)
    require(manifest["schemaVersion"] == 1, "Goal29 schema drifted")
    require(manifest["goalId"] == "goal29-evidence-calibrated-runtime-lookdev", "Goal29 id drifted")
    require(manifest["product"] == "ztovalve fixed ball valve", "Goal29 product drifted")
    validate_runtime_binding(manifest)
    validate_material(manifest)
    validate_lighting(manifest)
    validate_camera_motion_story(manifest)
    validate_release_state(manifest)
    validate_files(manifest)
    print("PASS: Goal29 evidence-calibrated runtime lookdev satisfies hero-runtime A-E controls while release remains blocked")


if __name__ == "__main__":
    main()
