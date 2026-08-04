"""Validate Goal28 lighting-lab sample packages."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAB_DIR = ROOT / "docs/assets/ztovalve/hero/goal28-lighting-lab"
REQUIRED_VARIANTS = {"lighting-v01", "lighting-v02", "lighting-v03"}
REQUIRED_FRAMES = [0, 72, 136, 216]
REQUIRED_LIGHT_ROLES = {
    "top-left-oblique-key",
    "top-right-oblique-rim",
    "bottom-left-lift",
    "bottom-right-lift",
    "front-fill",
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
    lab_manifest = read_json(LAB_DIR / "lighting-lab-manifest.json")
    require(lab_manifest["goalId"] == "goal28-lighting-lab", "unexpected lighting lab goal id")
    require(set(item["variantId"] for item in lab_manifest["variants"]) == REQUIRED_VARIANTS, "lighting variants drifted")
    require(lab_manifest["sampleFrames"] == REQUIRED_FRAMES, "lighting sample frames drifted")
    require(project_path("docs/assets/ztovalve/hero/goal28-lighting-lab/index.html").is_file(), "lighting lab index missing")

    for variant_id in REQUIRED_VARIANTS:
        manifest = read_json(LAB_DIR / variant_id / "render-manifest.json")
        require(manifest["goalId"] == "goal28-lighting-lab", f"{variant_id} goal id drifted")
        require(manifest["variantId"] == variant_id, f"{variant_id} id drifted")
        require(manifest["product"] == "ztovalve fixed ball valve", f"{variant_id} product drifted")
        require(manifest["renderProfile"]["sequenceFrameCount"] == 4, f"{variant_id} should be a four-frame sample")
        require(manifest["renderProfile"]["sampleFrames"] == REQUIRED_FRAMES, f"{variant_id} frame list drifted")
        require(manifest["renderProfile"]["homepageConnected"] is False, f"{variant_id} must not connect homepage")
        require(manifest["renderProfile"]["heroAvifReplaced"] is False, f"{variant_id} must not replace AVIF")
        require(manifest["renderProfile"]["published"] is False, f"{variant_id} must not publish")
        require(set(item["role"] for item in manifest["lighting"]["rig"]) == REQUIRED_LIGHT_ROLES, f"{variant_id} light roles drifted")
        require(manifest["lighting"]["removedMirrorReadablePanels"] is True, f"{variant_id} panel removal flag drifted")
        require(manifest["lighting"]["backgroundMode"] == "white-cloth-natural-light", f"{variant_id} must use white cloth background")
        require(len(manifest["lighting"]["whiteClothStage"]) >= 5, f"{variant_id} white cloth stage is incomplete")
        require([frame["frame"] for frame in manifest["frames"]] == REQUIRED_FRAMES, f"{variant_id} frame records drifted")
        for frame in manifest["frames"]:
            require(project_path(frame["path"]).is_file(), f"{variant_id} frame missing: {frame['path']}")
            require(frame["bytes"] > 10000, f"{variant_id} frame looks too small: {frame['path']}")
        require(project_path(manifest["previewSurface"]["route"]).is_file(), f"{variant_id} index missing")
        require(project_path(manifest["previewSurface"]["poster"]).is_file(), f"{variant_id} poster missing")
        if variant_id == "lighting-v01":
            require(manifest["lighting"]["driverLightsHiddenFromGlossy"] is False, "v01 must remain direct-light baseline")
            require(manifest["lighting"]["driverLightMode"] == "direct-five-light-white-cloth-baseline", "v01 light mode drifted")
            require(len(manifest["lighting"]["reflectionCards"]) == 0, "v01 should not have reflection cards")
        else:
            require(
                manifest["lighting"]["driverLightMode"] == "large-soft-specular-drivers-plus-reflection-cards",
                f"{variant_id} light mode drifted",
            )
            require(len(manifest["lighting"]["reflectionCards"]) >= 6, f"{variant_id} needs reflection cards")
            require(len(manifest["lighting"]["blackFlags"]) >= 3, f"{variant_id} needs black flags")
            require(
                all(item["size"] >= 4.8 for item in manifest["lighting"]["rig"]),
                f"{variant_id} driver lights must be broad soft sources",
            )
            require(
                all(0.15 <= item["specularFactor"] <= 0.35 for item in manifest["lighting"]["rig"]),
                f"{variant_id} specular factors must stay controlled",
            )

    print("PASS: Goal28 lighting lab has three four-frame reflection-environment samples")


if __name__ == "__main__":
    main()
