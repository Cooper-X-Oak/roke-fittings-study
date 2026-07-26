#!/usr/bin/env python3
"""Validate the reusable scroll-driven 3D product-story skill end to end."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".codex" / "skills" / "build-scroll-3d-product-story"
CAR_MODEL = ROOT / "docs" / "experiment" / "assets" / "models" / "car-concept-web.glb"
RUNTIME_ROUTE = ROOT / "docs" / "experiment"
FRAME_BASELINE = ROOT / "docs" / "upload" / "images" / "frames2_avif_new"
SKILL_CREATOR = (
    Path.home()
    / ".codex"
    / "skills"
    / ".system"
    / "skill-creator"
    / "scripts"
    / "quick_validate.py"
)


class ValidationError(RuntimeError):
    """Raised when the current skill contract is not satisfied."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def run(
    command: list[str],
    *,
    cwd: Path = ROOT,
    capture_json: bool = False,
) -> Any:
    result = subprocess.run(
        command,
        cwd=cwd,
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
    if capture_json:
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise ValidationError(
                f"Command did not return JSON: {' '.join(command)}\n"
                f"{result.stdout}"
            ) from error
    return result.stdout.strip()


def required_files() -> list[Path]:
    relative_paths = [
        "SKILL.md",
        "agents/openai.yaml",
        "scripts/inspect-model.mjs",
        "scripts/generate-story-manifest.mjs",
        "scripts/validate-creative-development.mjs",
        "scripts/validate-story-manifest.mjs",
        "scripts/benchmark-assets.mjs",
        "scripts/test-story-math.mjs",
        "scripts/lib/cli.mjs",
        "scripts/lib/model-analysis.mjs",
        "references/model-classification.md",
        "references/narrative-development-contract.md",
        "references/choreography-contract.md",
        "references/performance-contract.md",
        "references/threejs-runtime-patterns.md",
        "assets/product-story.schema.json",
        "assets/product-story.example.json",
        "assets/creative-development.schema.json",
        "assets/creative-development.example.json",
        "assets/threejs-scroll-story/index.html",
        "assets/threejs-scroll-story/styles.css",
        "assets/threejs-scroll-story/app.mjs",
        "assets/threejs-scroll-story/story-engine.mjs",
        "assets/threejs-scroll-story/story-math.mjs",
    ]
    return [SKILL / path for path in relative_paths]


def check_skill_shape() -> None:
    missing = [path for path in required_files() if not path.is_file()]
    require(
        not missing,
        "Skill is missing required files:\n"
        + "\n".join(f"- {path.relative_to(ROOT)}" for path in missing),
    )
    skill_text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    require("TODO" not in skill_text, "SKILL.md still contains TODO placeholders")
    require(
        len(skill_text.splitlines()) < 500,
        "SKILL.md must stay below 500 lines",
    )
    require(
        SKILL_CREATOR.is_file(),
        f"Official skill validator is unavailable: {SKILL_CREATOR}",
    )
    run([sys.executable, str(SKILL_CREATOR), str(SKILL)])


def check_node_syntax() -> None:
    scripts = [
        *SKILL.glob("scripts/**/*.mjs"),
        *SKILL.glob("assets/threejs-scroll-story/*.mjs"),
    ]
    for script in sorted(scripts):
        run(["node", "--check", str(script)])


def check_generic_runtime() -> None:
    runtime_files = [
        SKILL / "assets" / "threejs-scroll-story" / "app.mjs",
        SKILL / "assets" / "threejs-scroll-story" / "story-engine.mjs",
        SKILL / "assets" / "threejs-scroll-story" / "story-math.mjs",
    ]
    runtime_text = "\n".join(path.read_text(encoding="utf-8") for path in runtime_files)
    for product_word in (
        "automobile",
        "wheel",
        "tire",
        "tyre",
        "door",
        "chassis",
        "ferrule",
        "fitting",
    ):
        require(
            not re.search(rf"\b{re.escape(product_word)}\b", runtime_text, re.I),
            f"Generic runtime contains product-specific word: {product_word}",
        )
    require(
        "setAnimationLoop" not in runtime_text,
        "Generic runtime must not use setAnimationLoop",
    )
    require(
        "requestAnimationFrame" in runtime_text
        and "scheduledFrame" in runtime_text
        and "Math.abs(targetProgress - currentProgress) > epsilon" in runtime_text,
        "Generic runtime must use a settling, demand-driven frame scheduler",
    )


def create_fused_fixture(directory: Path) -> Path:
    fixture = {
        "asset": {"version": "2.0", "generator": "project acceptance fixture"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"name": "WholeProduct", "mesh": 0}],
        "meshes": [
            {
                "name": "WholeProduct",
                "primitives": [{"attributes": {"POSITION": 0}, "mode": 4}],
            }
        ],
        "accessors": [
            {
                "componentType": 5126,
                "count": 3,
                "type": "VEC3",
                "min": [-1, -1, -1],
                "max": [1, 1, 1],
            }
        ],
    }
    path = directory / "fused-single-mesh.gltf"
    path.write_text(f"{json.dumps(fixture, indent=2)}\n", encoding="utf-8")
    return path


def validate_manifest_file(path: Path) -> None:
    run(
        [
            "node",
            str(SKILL / "scripts" / "validate-story-manifest.mjs"),
            "--manifest",
            str(path),
        ]
    )


def expect_failure(command: list[str], expected: str) -> None:
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    require(result.returncode != 0, f"Command unexpectedly passed: {' '.join(command)}")
    require(
        expected in result.stdout,
        f"Expected failure text {expected!r} was missing:\n{result.stdout}",
    )


def check_models_and_benchmark() -> dict[str, Any]:
    require(CAR_MODEL.is_file(), f"Car validation model is missing: {CAR_MODEL}")
    require(FRAME_BASELINE.is_dir(), f"Frame baseline is missing: {FRAME_BASELINE}")
    inspection_script = SKILL / "scripts" / "inspect-model.mjs"
    generator_script = SKILL / "scripts" / "generate-story-manifest.mjs"
    creative_validator = SKILL / "scripts" / "validate-creative-development.mjs"
    benchmark_script = SKILL / "scripts" / "benchmark-assets.mjs"
    creative_example_path = SKILL / "assets" / "creative-development.example.json"
    creative_example = json.loads(creative_example_path.read_text(encoding="utf-8"))
    run(
        [
            "node",
            str(creative_validator),
            "--plan",
            str(creative_example_path),
        ]
    )

    car_inspection = run(
        ["node", str(inspection_script), "--model", str(CAR_MODEL)],
        capture_json=True,
    )
    require(
        car_inspection["capability"]["capability"] == "structured-named-parts",
        "Existing car model must be recognized as structured named parts",
    )
    require(
        car_inspection["counts"]["meshNodes"] >= 4,
        "Existing car model must expose independently transformable parts",
    )

    with tempfile.TemporaryDirectory(prefix="scroll-3d-skill-") as temporary:
        temp = Path(temporary)
        car_manifest_path = temp / "car-product-story.json"
        car_manifest = run(
            [
                "node",
                str(generator_script),
                "--model",
                str(CAR_MODEL),
                "--creative-plan",
                str(creative_example_path),
                "--public-uri",
                "./assets/models/car-concept-web.glb",
            ],
            capture_json=True,
        )
        car_manifest_path.write_text(
            f"{json.dumps(car_manifest, indent=2)}\n",
            encoding="utf-8",
        )
        validate_manifest_file(car_manifest_path)
        require(
            car_manifest["schemaVersion"] == 2
            and car_manifest["creativeDevelopment"]["planId"]
            == creative_example["planId"],
            "Runtime story must retain the approved creative-development identity",
        )
        require(
            [stage["id"] for stage in car_manifest["story"]["stages"]]
            == [shot["id"] for shot in creative_example["shots"]],
            "Runtime stages must come from the approved five-shot script",
        )
        require(
            car_manifest["story"]["mode"] == "semantic-assembly",
            "Structured car model must produce semantic-assembly mode",
        )
        require(
            car_manifest["review"]["required"] is True
            and all(group["reviewRequired"] for group in car_manifest["groups"]),
            "Generated semantic groups must remain review candidates",
        )
        selected_indices = {
            node_index
            for group in car_manifest["groups"]
            for node_index in group["selector"].get("nodeIndices", [])
        }
        require(
            len(selected_indices) == car_inspection["counts"]["meshNodes"],
            "Generated groups must cover every independently transformable mesh node",
        )

        fused_path = create_fused_fixture(temp)
        fused_creative = json.loads(json.dumps(creative_example))
        fused_creative["planId"] = "fused-product-approved-story"
        fused_creative["modelAudit"]["modelPath"] = str(fused_path)
        fused_creative["modelAudit"]["capability"] = "fused-single-mesh"
        fused_creative_path = temp / "fused-creative-development.json"
        fused_creative_path.write_text(
            f"{json.dumps(fused_creative, indent=2)}\n",
            encoding="utf-8",
        )
        run(
            [
                "node",
                str(creative_validator),
                "--plan",
                str(fused_creative_path),
            ]
        )
        fused_inspection = run(
            ["node", str(inspection_script), "--model", str(fused_path)],
            capture_json=True,
        )
        fused_manifest = run(
            [
                "node",
                str(generator_script),
                "--model",
                str(fused_path),
                "--creative-plan",
                str(fused_creative_path),
            ],
            capture_json=True,
        )
        fused_manifest_path = temp / "fused-product-story.json"
        fused_manifest_path.write_text(
            f"{json.dumps(fused_manifest, indent=2)}\n",
            encoding="utf-8",
        )
        validate_manifest_file(fused_manifest_path)
        require(
            fused_inspection["capability"]["capability"] == "fused-single-mesh",
            "Single-mesh fixture must be classified as fused",
        )
        require(
            fused_manifest["story"]["mode"] == "whole-product"
            and fused_manifest["fallback"]["fusedMeshStrategy"] == "whole-product",
            "Fused models must degrade to whole-product behavior",
        )
        require(
            all(
                group["explodedOffset"] == [0, 0, 0]
                for group in fused_manifest["groups"]
            ),
            "Fused models must not receive fabricated part offsets",
        )

        unapproved = json.loads(json.dumps(creative_example))
        unapproved["confirmation"]["status"] = "pending"
        for key in ["approvalId", "confirmedBy", "confirmedAt", "evidenceRef"]:
            unapproved["confirmation"].pop(key)
        unapproved["phaseHistory"] = unapproved["phaseHistory"][:4]
        unapproved_path = temp / "unapproved-creative-development.json"
        unapproved_path.write_text(
            f"{json.dumps(unapproved, indent=2)}\n",
            encoding="utf-8",
        )
        expect_failure(
            [
                "node",
                str(creative_validator),
                "--plan",
                str(unapproved_path),
            ],
            "confirmation.status must be approved",
        )
        run(
            [
                "node",
                str(creative_validator),
                "--plan",
                str(unapproved_path),
                "--through",
                "animatic",
            ]
        )
        reordered = json.loads(json.dumps(creative_example))
        reordered["confirmation"] = {"status": "pending"}
        reordered["phaseHistory"] = reordered["phaseHistory"][:4]
        reordered["phaseHistory"][1], reordered["phaseHistory"][2] = (
            reordered["phaseHistory"][2],
            reordered["phaseHistory"][1],
        )
        reordered_path = temp / "reordered-creative-development.json"
        reordered_path.write_text(
            f"{json.dumps(reordered, indent=2)}\n",
            encoding="utf-8",
        )
        expect_failure(
            [
                "node",
                str(creative_validator),
                "--plan",
                str(reordered_path),
                "--through",
                "animatic",
            ],
            "phaseHistory[1].phase must be creative-routes",
        )
        expect_failure(
            [
                "node",
                str(generator_script),
                "--model",
                str(CAR_MODEL),
            ],
            "Missing required option: --creative-plan",
        )

    run(["node", str(SKILL / "scripts" / "test-story-math.mjs")])
    benchmark = run(
        [
            "node",
            str(benchmark_script),
            "--runtime-dir",
            str(RUNTIME_ROUTE),
            "--frames-dir",
            str(FRAME_BASELINE),
        ],
        capture_json=True,
    )
    require(
        benchmark["comparison"]["frameSequence"]["frameCount"] == 240,
        "Baseline must contain exactly 240 image frames",
    )
    require(
        benchmark["releaseAssumptions"]["fixedWeakNetworkGate"] is False,
        "A fixed weak-network gate must not be introduced",
    )
    require(
        "frameTimeP95Ms" in benchmark["browserMetricsToCollect"]
        and "idleFramesAfterSettled" in benchmark["browserMetricsToCollect"],
        "Benchmark must declare browser runtime evidence fields",
    )

    return {
        "schemaVersion": 1,
        "skill": {
            "path": ".codex/skills/build-scroll-3d-product-story",
            "officialQuickValidate": "pass",
            "nodeSyntax": "pass",
            "genericRuntime": "pass",
            "deterministicReversibleTransforms": "pass",
            "narrativeFirstGate": "pass",
            "missingReorderedOrUnconfirmedCreativeDevelopmentRejected": "pass",
        },
        "carModel": {
            "source": "docs/experiment/assets/models/car-concept-web.glb",
            "bytes": car_inspection["source"]["bytes"],
            "counts": car_inspection["counts"],
            "compression": car_inspection["compression"],
            "capability": car_inspection["capability"],
            "generatedStory": {
                "mode": car_manifest["story"]["mode"],
                "groups": [
                    {
                        "id": group["id"],
                        "nodeCount": len(group["selector"].get("nodeIndices", [])),
                        "confidence": group["confidence"],
                        "reviewRequired": group["reviewRequired"],
                    }
                    for group in car_manifest["groups"]
                ],
                "reviewRequired": car_manifest["review"]["required"],
            },
        },
        "fusedModelFixture": {
            "capability": fused_inspection["capability"]["capability"],
            "storyMode": fused_manifest["story"]["mode"],
            "strategy": fused_manifest["fallback"]["fusedMeshStrategy"],
            "fabricatedPartOffsets": False,
        },
        "assetBaseline": benchmark,
        "browserRuntimeMeasurement": {
            "status": "contract-defined-not-fabricated",
            "reason": (
                "The project skill packages the measurement contract; apply it "
                "to a target route on the same device and browser before making "
                "runtime performance claims."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write-report",
        type=Path,
        help="Write the deterministic validation summary to this path.",
    )
    args = parser.parse_args()
    try:
        check_skill_shape()
        check_node_syntax()
        check_generic_runtime()
        report = check_models_and_benchmark()
        if args.write_report:
            output = args.write_report
            if not output.is_absolute():
                output = ROOT / output
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(
                f"{json.dumps(report, indent=2)}\n",
                encoding="utf-8",
            )
        print("PASS: reusable scroll-driven 3D product-story skill contract")
        return 0
    except ValidationError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
