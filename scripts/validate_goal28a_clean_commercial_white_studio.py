"""Validate Goal28A clean commercial white-studio lookdev evidence."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GOAL_DIR = ROOT / "docs/assets/ztovalve/hero/goal28a-clean-commercial-white-studio"
AUTHORITY_DIR = ROOT / "governance/control/hero-runtime"
REQUIRED_FRAMES = [0, 72, 136, 216]
REQUIRED_CHANNELS = {
    "shellSplit",
    "seatSpread",
    "stemLift",
    "lowerDrop",
    "fastenerSpread",
    "ballTurn",
}
REQUIRED_ROLES = {
    "top-left-oblique-key",
    "top-right-oblique-rim",
    "bottom-left-lift",
    "bottom-right-lift",
    "front-fill",
    "ambient-white-studio",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def read_json(path: Path) -> dict:
    require(path.is_file(), f"missing {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def project_path(value: str) -> Path:
    return ROOT / value.replace("/", "\\")


def main() -> None:
    manifest = read_json(GOAL_DIR / "render-manifest.json")
    require(manifest["goalId"] == "goal28a-clean-commercial-white-studio", "unexpected Goal28A id")
    require(manifest["product"] == "ztovalve fixed ball valve", "Goal28A product drifted")
    require("control-valve" not in json.dumps(manifest["sourceBoundary"], ensure_ascii=False).lower(), "Goal28A must not consume control-valve assets")
    require("goal25dMaterialManifest" not in manifest["sourceBoundary"], "Goal28A must not treat Goal25D as material authority")

    runtime = manifest.get("runtimeAuthority")
    require(isinstance(runtime, dict), "Goal28A must declare runtimeAuthority")
    require(runtime["authorityId"] == "hero-runtime", "Goal28A must bind to hero-runtime")
    require(runtime["authorityStatus"] == "current", "Goal28A must bind to current runtime authority")
    require(runtime["soleCurrentHeroRenderAuthority"] is True, "Goal28A must use hero-runtime as sole current hero render authority")
    require(runtime["manifestAuthorityBindingRequired"] is True, "Goal28A runtime authority binding must be mandatory")
    require(runtime["nonRuntimeRenderAuthorityAllowed"] is False, "Goal28A must reject non-runtime render authority")
    hashes = runtime.get("authorityFileSha256")
    require(isinstance(hashes, dict), "Goal28A must record runtime authority file hashes")
    for name in ["authority.json", "material.json", "lighting.json", "camera.json", "motion.json", "storyboard.json", "release-gate.json"]:
        require((AUTHORITY_DIR / name).is_file(), f"missing runtime authority file {name}")
        require(name in hashes and len(hashes[name]) == 64, f"missing runtime authority hash for {name}")

    profile = manifest["renderProfile"]
    require(profile["sequenceFrameCount"] == 4, "Goal28A must stay a four-frame lookdev sample")
    require(profile["sampleFrames"] == REQUIRED_FRAMES, "Goal28A sample frames drifted")
    require(profile["sourceTotalFrames"] == 240, "Goal28A must consume the 240-frame camera previs")
    require(profile["homepageConnected"] is False, "Goal28A must not connect homepage")
    require(profile["heroAvifReplaced"] is False, "Goal28A must not replace hero AVIF")
    require(profile["published"] is False, "Goal28A must not publish Pages")

    material = manifest["materialDirection"]
    require(material["productMaterialTruth"] == "silica-sol investment-cast stainless steel visual", "Goal28A material truth drifted")
    require("not WCB" in material["negativeBoundary"], "Goal28A must reject WCB/cast-carbon-steel interpretation")
    require("not black cast steel" in material["negativeBoundary"], "Goal28A must reject black cast-steel interpretation")
    require("not war-damaged" in material["negativeBoundary"], "Goal28A must reject war-damage look")
    require(material["cleanPbr"] is True, "Goal28A must be clean PBR")
    require(material["explicitScratchGeometryVisible"] is False, "Goal28A must not show explicit scratch geometry")
    require(material["dirtyBlotchNoiseVisible"] is False, "Goal28A must not show dirty blotch noise")
    require(material["dirtyBlotchHighlightsVisible"] is False, "Goal28A must not show dirty white/highlight blotches")
    require(material["polygonZoneArtifactsVisible"] is False, "Goal28A must not show polygon-zone artifacts")
    require(material["productFacingMaterialHardEdgesVisible"] is False, "Goal28A must not show product-facing material hard edges")
    require(material["nonRuntimeMaterialSourceUsed"] is False, "Goal28A must not use non-runtime material authority")
    require(material["commercialBodyAssignmentPolicy"] == "continuous-commercial-body", "Goal28A body assignment policy drifted")
    require(material["polishedBallRoughness"] <= 0.18, "Goal28A polished ball must stay clean/polished")
    require(material["bodyZoneCount"] == 1, "Goal28A commercial body must use one continuous body zone")
    require(material["zoneAssignment"]["policy"] == "continuous-commercial-body", "Goal28A body zone policy drifted")
    require(material["zoneAssignment"]["productFacingPolygonMaterialHardEdgesVisible"] is False, "Goal28A body hard-edge audit drifted")
    require(material["zoneAssignment"]["polygonMaterialHardEdgesAllowed"] is False, "Goal28A body hard-edge allowance drifted")

    motion = manifest["motionFusion"]
    require(set(motion["controlledChannels"]) == REQUIRED_CHANNELS, "Goal28A motion channel set drifted")
    require(motion["maxOffset"] > 0.05, "Goal28A exploded motion amplitude is too low")
    require(motion["maxBallAngleDegrees"] > 80, "Goal28A ball turn amplitude is too low")

    lighting = manifest["lighting"]
    require(lighting["backgroundMode"] == "high-key-white-studio", "Goal28A background must be high-key white")
    require(lighting["visibleLightPanelsInCamera"] is False, "Goal28A must not show light panels in camera")
    require(lighting["glossyEquipmentReflectionAllowed"] is False, "Goal28A must not allow glossy equipment reflections")
    require(lighting["reflectionCardsGlossyReadableAllowed"] is False, "Goal28A must not allow glossy-readable reflector cards")
    require(lighting["hardWhiteBlotchReflectionAllowed"] is False, "Goal28A must not allow hard white blotch reflections")
    gradient = lighting.get("reflectionGradientEnvironment")
    require(isinstance(gradient, dict), "Goal28A must declare a continuous reflection gradient environment")
    require(gradient["type"] == "non-equipment-gradient-dome", "Goal28A reflection environment type drifted")
    require(gradient["visibleCamera"] is False, "Goal28A reflection gradient must not be camera-visible equipment")
    require(gradient["visibleGlossy"] is True, "Goal28A reflection gradient must be available to metal reflections")
    require(gradient["continuousGradient"] is True, "Goal28A reflection environment must be continuous")
    require(gradient["equipmentReadable"] is False, "Goal28A reflection gradient must not be readable equipment")
    require(gradient["hardPanelShapeVisible"] is False, "Goal28A reflection gradient must not show hard panel shape")
    retouch = lighting.get("productGlossyReflectionRetouch")
    require(isinstance(retouch, dict), "Goal28A must declare product glossy reflection retouch")
    require(retouch["policy"] == "commercial-polished-ball-clean-reflection", "Goal28A glossy retouch policy drifted")
    require(retouch["suppressedGroup"] == "fastenersSmallHardware", "Goal28A must suppress small hardware glossy speckles")
    require(retouch["suppressedCount"] >= 100, "Goal28A small hardware glossy suppression count drifted")
    require(retouch["visibleInCamera"] is True, "Goal28A small hardware must remain camera-visible")
    require(retouch["visibleInGlossy"] is False, "Goal28A small hardware must not be glossy-visible")
    require(set(lighting["roles"]) == REQUIRED_ROLES, "Goal28A light roles drifted")
    require(len(lighting["whiteStudioCards"]) >= 6, "Goal28A needs white studio cards")
    require(len(lighting["blackFlags"]) <= 2, "Goal28A black flags must stay restrained")
    far_lights = [item for item in lighting["rig"] if item["role"] != "ambient-white-studio"]
    require(all(item["size"] >= 6.4 for item in far_lights), "Goal28A lights must be large soft sources")
    require(all(item["distanceClass"] == "far-large-soft-source" for item in far_lights), "Goal28A lights must be far large soft sources")
    require(all(item["visibleGlossy"] is False for item in far_lights), "Goal28A driver lights must not be glossy-readable")
    require(all(item["visibleGlossy"] is False for item in lighting["whiteStudioCards"]), "Goal28A reflector cards must not be glossy-readable")
    require(all(item["visibleGlossy"] is False for item in lighting["blackFlags"]), "Goal28A black flags must not be glossy-readable")

    camera = manifest["cameraDirection"]
    require(camera["distanceMultiplier"] >= 2.0, "Goal28A camera must be pulled back")
    require(camera["fovMultiplier"] <= 0.60, "Goal28A camera must use a longer-lens feel")
    require(camera["visibleLightPanelsInCamera"] is False, "Goal28A camera must not see light panels")

    frames = manifest["frames"]
    require([frame["frame"] for frame in frames] == REQUIRED_FRAMES, "Goal28A frame records drifted")
    for frame in frames:
        require(project_path(frame["path"]).is_file(), f"missing frame {frame['path']}")
        require(frame["bytes"] > 20000, f"frame looks too small: {frame['path']}")

    require(project_path(manifest["previewSurface"]["route"]).is_file(), "Goal28A index.html missing")
    require(project_path(manifest["previewSurface"]["poster"]).is_file(), "Goal28A poster missing")
    require((GOAL_DIR / "lookdev-status.md").is_file(), "Goal28A status markdown missing")
    print("PASS: Goal28A clean commercial white-studio lookdev evidence is complete")


if __name__ == "__main__":
    main()
