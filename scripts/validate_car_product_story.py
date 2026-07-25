#!/usr/bin/env python3
"""Validate the delivered car product story and its browser evidence."""

from __future__ import annotations

import json
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ROUTE = ROOT / "docs" / "experiment"
MANIFEST_PATH = ROUTE / "product-story.json"
MODEL_PATH = ROUTE / "assets" / "models" / "car-concept-web.glb"
METRICS_PATH = ROOT / "validation-results" / "car-product-story-browser-metrics.json"
SKILL_VALIDATOR = (
    ROOT
    / ".codex"
    / "skills"
    / "build-scroll-3d-product-story"
    / "scripts"
    / "validate-story-manifest.mjs"
)


class ValidationError(RuntimeError):
    """Raised when the current car product-story contract is not satisfied."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def run(command: list[str]) -> str:
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode:
        raise ValidationError(
            f"Command failed ({result.returncode}): {' '.join(command)}\n"
            f"{result.stdout}"
        )
    return result.stdout.strip()


def read_glb_json(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    require(len(payload) >= 20, "GLB is too small to contain a JSON chunk")
    magic, version, declared_length = struct.unpack_from("<III", payload, 0)
    require(magic == 0x46546C67, "Model is not a binary glTF file")
    require(version == 2, "Model must use glTF 2.0")
    require(declared_length == len(payload), "GLB declared length does not match file size")

    chunk_length, chunk_type = struct.unpack_from("<II", payload, 12)
    require(chunk_type == 0x4E4F534A, "GLB first chunk must be JSON")
    json_bytes = payload[20 : 20 + chunk_length]
    return json.loads(json_bytes.decode("utf-8").rstrip(" \t\r\n\0"))


def validate_manifest_and_model() -> dict[str, Any]:
    require(MANIFEST_PATH.is_file(), "Product story manifest is missing")
    require(MODEL_PATH.is_file(), "Car GLB is missing")
    run(
        [
            "node",
            str(SKILL_VALIDATOR),
            "--manifest",
            str(MANIFEST_PATH),
        ]
    )

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    gltf = read_glb_json(MODEL_PATH)
    nodes = gltf["nodes"]

    require(
        manifest["model"]["bytes"] == MODEL_PATH.stat().st_size,
        "Manifest model byte count must equal the delivered GLB",
    )
    require(
        manifest["model"]["capability"] == "structured-named-parts",
        "The reviewed car must remain classified as structured-named-parts",
    )
    require(
        manifest["review"] == {"required": False, "reasons": []},
        "The delivered manifest must record completed semantic review",
    )
    require(
        all(not group["reviewRequired"] for group in manifest["groups"]),
        "No delivered semantic group may remain review-required",
    )
    require(
        len(manifest["groups"]) == 10,
        "The reviewed car product story must contain exactly ten semantic groups",
    )

    selected: dict[int, str] = {}
    for group in manifest["groups"]:
        indices = group["selector"].get("nodeIndices", [])
        names = group["selector"].get("nodeNames", [])
        require(
            len(indices) == len(names),
            f"Group {group['id']} must pair every node index with its reviewed name",
        )
        for node_index, node_name in zip(indices, names, strict=True):
            require(node_index not in selected, f"Node {node_index} is selected twice")
            require(node_index < len(nodes), f"Node {node_index} is out of range")
            require(
                nodes[node_index].get("name") == node_name,
                f"Node {node_index} name does not match manifest selector {node_name}",
            )
            selected[node_index] = group["id"]

    foundation = next(
        (group for group in manifest["groups"] if group["id"] == "foundation"),
        None,
    )
    require(foundation is not None, "Manifest is missing the stationary foundation group")
    require(
        foundation["selector"]["nodeIndices"] == [0],
        "Foundation must control only GLB node 0",
    )
    require(
        foundation["explodedOffset"] == [0, 0, 0],
        "The parent foundation must remain stationary to avoid compounded transforms",
    )

    direct_children = set(nodes[0].get("children", []))
    require(
        set(selected) == direct_children | {0},
        "Reviewed selectors must cover node 0 and every direct assembly child exactly once",
    )
    require(
        set(selected) - {0} == direct_children,
        "Every moving selector must be a non-overlapping direct child of node 0",
    )

    extensions_required = set(gltf.get("extensionsRequired", []))
    require(
        "KHR_draco_mesh_compression" in extensions_required,
        "Delivered GLB must require Draco geometry compression",
    )
    require(
        "KHR_texture_basisu" in extensions_required,
        "Delivered GLB must require BasisU/KTX2 texture compression",
    )
    draco_primitives = sum(
        1
        for mesh in gltf.get("meshes", [])
        for primitive in mesh.get("primitives", [])
        if "KHR_draco_mesh_compression" in primitive.get("extensions", {})
    )
    require(draco_primitives == 109, "Expected 109 Draco-compressed primitives")
    require(len(gltf.get("images", [])) == 14, "Expected 14 embedded KTX2 images")

    return manifest


def validate_page_and_runtime(manifest: dict[str, Any]) -> None:
    index = (ROUTE / "index.html").read_text(encoding="utf-8")
    app = (ROUTE / "app.js").read_text(encoding="utf-8")
    engine = (ROUTE / "story-engine.mjs").read_text(encoding="utf-8")
    math = (ROUTE / "story-math.mjs").read_text(encoding="utf-8")
    runtime = "\n".join([app, engine, math])

    for stage in manifest["story"]["stages"]:
        require(
            f'data-stage="{stage["id"]}"' in index,
            f"HTML is missing the {stage['id']} stage",
        )
        require(
            stage["content"]["body"] in index,
            f"HTML body copy diverges from manifest stage {stage['id']}",
        )

    for forbidden in [
        "BodyUnderside",
        "BodyDoor",
        "BodyHood",
        "WheelFront",
        "WheelRear",
        "InteriorCage",
        '"Engine"',
    ]:
        require(
            forbidden not in runtime,
            f"Generic runtime contains car-specific selector token: {forbidden}",
        )

    require("createStoryController" in app, "Page must use the manifest story controller")
    require(
        'fetch("./product-story.json")' in app,
        "Page must load the delivered product story manifest",
    )
    require(
        "requestAnimationFrame(tick)" in engine,
        "Demand controller must schedule its bounded progress tick",
    )
    require("function animate" not in runtime, "Runtime must not contain a permanent animate loop")
    require("setAnimationLoop" not in runtime, "Runtime must not enable a permanent render loop")
    require(
        "requestAnimationFrame(animate)" not in runtime,
        "Runtime must not reschedule an unbounded animation function",
    )
    require(
        "basePosition" in engine and "baseRotation" in engine,
        "Transforms must be recalculated from captured base transforms",
    )
    require(
        "idleRendererFramesAfterSettle" in app,
        "Runtime metrics must expose the idle-render proof",
    )
    require(
        "long-animation-frame" in app and '"longtask"' in app,
        "Runtime must collect supported LoAF and main-thread signals",
    )
    require(
        "performance.memory" in app,
        "Runtime must report memory or an explicit browser-unavailable result",
    )
    require(
        'query.has("fallback")' in app and 'query.has("fail-model")' in app,
        "Runtime must retain deterministic fallback and load-error routes",
    )
    require(
        "reducedMotion.matches" in app and "storyProgressValue = motionIsEnabled() ? progress : 1" in app,
        "Reduced motion must resolve directly to the final assembled hero",
    )
    require(
        (ROUTE / "MODEL-LICENSE.txt").is_file(),
        "Model license file must remain beside the experiment",
    )
    require(
        "creativecommons.org/licenses/by/4.0/" in index,
        "Published page must link the model's CC BY 4.0 license",
    )

    for script in [
        "docs/experiment/app.js",
        "docs/experiment/story-engine.mjs",
        "docs/experiment/story-math.mjs",
    ]:
        run(["node", "--check", script])


def validate_browser_metrics() -> dict[str, Any]:
    require(
        METRICS_PATH.is_file(),
        "Browser metrics are missing; run the desktop story benchmark first",
    )
    evidence = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    require(evidence.get("schemaVersion") == 1, "Metrics evidence schemaVersion must be 1")
    runs = evidence.get("runs")
    require(isinstance(runs, list) and runs, "Metrics evidence must contain at least one run")

    passing_runs = []
    for run_result in runs:
        environment = run_result["environment"]
        runtime = run_result["runtime"]
        browser_signals = run_result["browserSignals"]
        loading = run_result["loading"]
        intervals = runtime["frameIntervalMs"]

        require(
            environment["viewport"] == {"width": 1440, "height": 900},
            "Desktop metrics must use the locked 1440x900 viewport",
        )
        require(
            environment["devicePixelRatio"] > 0,
            "Metrics must record devicePixelRatio",
        )
        require(environment["userAgent"], "Metrics must record browser user agent")
        require(
            environment["cacheState"] in {"cold", "warm"},
            "Metrics must label the browser cache state",
        )
        require(
            loading["firstUsableProductFrameMs"] > 0,
            "Metrics must record first usable product frame",
        )
        require(
            loading["modelResource"] is not None,
            "Metrics must keep model transfer evidence separate from runtime evidence",
        )
        require(
            runtime["measuredRendererFrames"] >= 60,
            "Scroll benchmark must measure at least 60 renderer frames",
        )
        require(intervals["p50"] is not None, "Frame interval p50 is missing")
        require(intervals["p95"] is not None, "Frame interval p95 is missing")
        require(
            runtime["idleRendererFramesAfterSettle"] == 0,
            "Demand rendering must produce zero frames during the idle observation",
        )
        for signal_name in [
            "longAnimationFrame",
            "mainThreadLongTask",
            "memory",
        ]:
            signal = browser_signals[signal_name]
            require(
                isinstance(signal.get("available"), bool),
                f"{signal_name} must record availability instead of fabricating data",
            )
            if not signal["available"]:
                require(signal.get("reason"), f"{signal_name} unavailable result needs a reason")

        passes_budget = (
            intervals["p50"] <= 18.5
            and intervals["p95"] <= 25
            and runtime["frameIntervalOver33_3Ms"]["ratio"] <= 0.02
            and runtime["idleRendererFramesAfterSettle"] == 0
        )
        if passes_budget:
            passing_runs.append(run_result["label"])

    require(
        passing_runs,
        "No browser run satisfies p50<=18.5ms, p95<=25ms, >33.3ms<=2%, idle=0",
    )
    return {
        "runCount": len(runs),
        "passingRuns": passing_runs,
    }


def main() -> int:
    manifest = validate_manifest_and_model()
    validate_page_and_runtime(manifest)
    browser = validate_browser_metrics()
    report = {
        "status": "pass",
        "manifest": str(MANIFEST_PATH.relative_to(ROOT)).replace("\\", "/"),
        "groups": len(manifest["groups"]),
        "stages": len(manifest["story"]["stages"]),
        "browser": browser,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1) from error
