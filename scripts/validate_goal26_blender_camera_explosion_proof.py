"""Validate Goal 26 ztovalve Blender camera/explosion proof outputs."""

from __future__ import annotations

import json
import sys
from pathlib import Path


GOAL_DIR = Path("docs/assets/ztovalve/hero/goal26-blender-camera-explosion-proof")
CONTROL_PATH = GOAL_DIR / "motion-control.json"
MANIFEST_PATH = GOAL_DIR / "render-manifest.json"
REQUIRED_CHANNELS = {
    "shellSplit",
    "seatSpread",
    "stemLift",
    "lowerDrop",
    "fastenerSpread",
    "ballTurn",
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    require(CONTROL_PATH.is_file(), f"missing {CONTROL_PATH}")
    require(MANIFEST_PATH.is_file(), f"missing {MANIFEST_PATH}")

    control = read_json(CONTROL_PATH)
    manifest = read_json(MANIFEST_PATH)
    consumed_sources = json.dumps(
        {
            "controlSources": control["sources"],
            "manifestSources": {
                "stepMesh": manifest["sourceBoundary"]["stepMesh"],
                "cameraPrevis": manifest["sourceBoundary"]["cameraPrevis"],
                "motionControl": manifest["sourceBoundary"]["motionControl"],
                "goal20SemanticMap": manifest["sourceBoundary"]["goal20SemanticMap"],
            },
            "stillCameraSources": [still["camera"]["source"] for still in manifest["stills"]],
        },
        ensure_ascii=False,
    ).lower()

    require(control["product"] == "ztovalve fixed ball valve", "motion control is not for ztovalve fixed ball valve")
    require(manifest["product"] == "ztovalve fixed ball valve", "render manifest is not for ztovalve fixed ball valve")
    require("control-valve" not in consumed_sources, "goal26 must not consume control-valve assets")
    require(
        control["sources"]["stepMesh"] == "docs/assets/ztovalve/hero/goal20-blender-cycles-step-proof/goal20-step-mesh.glb",
        "motion control does not use the Goal20 STEP-derived full-valve mesh",
    )
    require(
        manifest["sourceBoundary"]["stepMesh"] == control["sources"]["stepMesh"],
        "render manifest step mesh does not match motion control",
    )
    require(
        manifest["sourceBoundary"]["cameraPrevis"] == control["sources"]["cameraPrevis"],
        "render manifest camera previs does not match motion control",
    )
    require(
        set(control["partChannels"]) == REQUIRED_CHANNELS,
        "motion control does not expose the required six channels",
    )
    require(
        set(manifest["controlledChannels"]) == REQUIRED_CHANNELS,
        "render manifest does not expose the required six channels",
    )
    require(manifest["renderProfile"]["homepageConnected"] is False, "goal26 must not connect homepage")
    require(manifest["renderProfile"]["frameSequenceRendered"] is False, "goal26 must not render final frame sequence")
    require(manifest["renderProfile"]["heroAvifReplaced"] is False, "goal26 must not replace hero AVIF")
    require(manifest["renderProfile"]["renderedFrameCount"] >= 4, "expected at least four proof frames")
    require(manifest["proofEvidence"]["cameraControlVerified"] is True, "camera control was not verified")
    require(manifest["proofEvidence"]["partMotionControlVerified"] is True, "part motion control was not verified")
    require(manifest["proofEvidence"]["ballTurnControlVerified"] is True, "ball turn control was not verified")

    for still in manifest["stills"]:
        path = Path(still["path"])
        require(path.is_file(), f"missing still {path}")
        require(path.stat().st_size > 0, f"empty still {path}")
        require(still["camera"]["source"] == control["sources"]["cameraPrevis"], "still camera source mismatch")
        require(set(still["channels"]) == {"exploded", *REQUIRED_CHANNELS}, "still channel set mismatch")

    print("PASS: Goal26 ztovalve Blender camera/explosion proof is internally consistent")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
