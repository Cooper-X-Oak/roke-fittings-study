#!/usr/bin/env python3
"""Validate the current car-story preproduction package and its hard approval gate."""

from __future__ import annotations

import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CREATIVE = ROOT / "creative" / "car-concept"
PLAN = CREATIVE / "creative-development.json"
MODEL = ROOT / "docs" / "experiment" / "assets" / "models" / "car-concept-web.glb"
SKILL = ROOT / ".codex" / "skills" / "build-scroll-3d-product-story"
BASELINE_COMMIT = "eece08bf1375d419e91fb0e937f1c7094044024c"


def fail(message: str) -> None:
    raise AssertionError(message)


def run(command: list[str], *, expect_success: bool) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if expect_success and result.returncode != 0:
        fail(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"{result.stdout}\n{result.stderr}"
        )
    if not expect_success and result.returncode == 0:
        fail(f"command unexpectedly passed: {' '.join(command)}")
    return result


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as stream:
        header = stream.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        fail(f"{path.relative_to(ROOT)} is not a valid PNG")
    return struct.unpack(">II", header[16:24])


def require_text(path: Path, tokens: list[str]) -> str:
    if not path.is_file():
        fail(f"missing required artifact: {path.relative_to(ROOT)}")
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        fail(f"empty required artifact: {path.relative_to(ROOT)}")
    for token in tokens:
        if token not in text:
            fail(f"{path.relative_to(ROOT)} is missing required evidence: {token}")
    return text


def main() -> None:
    node = shutil.which("node")
    git = shutil.which("git")
    if not node or not git:
        fail("node and git must be available")

    board = require_text(
        CREATIVE / "advertising-reference-board.md",
        [
            "Honda Cog",
            "Mercedes-AMG ONE",
            "Formula E Gen2",
            "Toyota LC150",
            "Petrol Ofisi — Adaptech Maxima",
            "模型对创意的实际约束",
        ],
    )
    if board.count("https://") < 5:
        fail("advertising reference board must retain at least five traceable URLs")

    require_text(
        CREATIVE / "creative-routes.md",
        [
            "Precision Becomes Presence",
            "Beneath The Surface",
            "Designed Around The Driver",
            "confirmation.status",
            "pending",
        ],
    )
    require_text(
        CREATIVE / "five-shot-script.md",
        [
            "Shot 01 — INTERCEPT",
            "Shot 02 — THREAD",
            "Shot 03 — COCKPIT RUN",
            "Shot 04 — BREAKOUT",
            "Shot 05 — ARREST",
            "Camera Previs 验收契约",
        ],
    )

    inspection = json.loads(
        (CREATIVE / "model-inspection.json").read_text(encoding="utf-8")
    )
    expected_counts = {
        "nodes": 101,
        "meshNodes": 97,
        "primitives": 109,
        "triangles": 211306,
        "textures": 14,
    }
    for key, expected in expected_counts.items():
        actual = inspection["counts"].get(key)
        if actual != expected:
            fail(f"model inspection {key} changed: expected {expected}, got {actual}")
    if inspection["source"].get("bytes") != MODEL.stat().st_size:
        fail("model inspection byte count does not match the current GLB")
    if inspection["capability"].get("capability") != "structured-named-parts":
        fail("current GLB must remain classified as structured-named-parts")
    if inspection["compression"].get("dracoPrimitiveCount") != 109:
        fail("all 109 primitives must remain Draco compressed")
    if inspection["compression"].get("ktx2ImageCount") != 14:
        fail("all 14 images must remain KTX2")

    for index in range(1, 6):
        frame = CREATIVE / "storyboards" / f"shot-{index:02d}.png"
        if not frame.is_file():
            fail(f"missing storyboard frame: {frame.relative_to(ROOT)}")
        if png_dimensions(frame) != (1920, 1080):
            fail(f"{frame.relative_to(ROOT)} must be 1920x1080")

    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    if plan.get("selectedRouteId") != "precision-becomes-presence":
        fail("the reviewed candidate route identity changed")
    if plan.get("confirmation") != {"status": "pending"}:
        fail("preproduction must remain pending external confirmation")
    if plan.get("animatic", {}).get("durationSeconds") != 16:
        fail("animatic duration must remain 16 seconds")
    if plan.get("animatic", {}).get("reviewed") is not True:
        fail("animatic must retain explicit visual-review evidence")
    if len(plan.get("shots", [])) != 5:
        fail("creative development must contain exactly five shots")
    if [shot.get("id") for shot in plan.get("shots", [])] != [
        "intercept",
        "thread",
        "cockpit-run",
        "breakout",
        "arrest",
    ]:
        fail("the selected route must use the approved virtual-FPV five-shot arc")

    camera_previs_path = CREATIVE / "camera-previs.json"
    camera_previs = json.loads(camera_previs_path.read_text(encoding="utf-8"))
    if camera_previs.get("fps") != 30 or camera_previs.get("totalFrames") != 480:
        fail("camera previs must be the canonical 480-frame, 30fps playback")
    frames = camera_previs.get("frames", [])
    if len(frames) != 480:
        fail("camera previs must contain exactly one state for every frame")
    if [entry.get("frame") for entry in frames] != list(range(480)):
        fail("camera previs frame identities must be contiguous and deterministic")
    if camera_previs.get("stableHeroHold") != [408, 479]:
        fail("camera previs must reserve the final 15% for the stable hero")
    if camera_previs.get("maxAbsRollDegrees", 99) > 10:
        fail("camera previs roll must remain within the authored 10-degree limit")
    hidden_cut = camera_previs.get("hiddenCut", {})
    if (hidden_cut.get("fromFrame"), hidden_cut.get("toFrame")) != (123, 124):
        fail("camera previs must retain the brake-disc-motivated hidden cut")
    stable_frames = frames[408:]
    stable_projection = [
        (
            frame["camera"],
            frame["product"],
            frame["light"],
            frame["transition"],
        )
        for frame in stable_frames
    ]
    if len({json.dumps(value, sort_keys=True) for value in stable_projection}) != 1:
        fail("camera, product, light, and transition states must be stable from frame 408")
    if max(abs(frame["camera"]["rollDegrees"]) for frame in frames) > 10:
        fail("sampled camera roll exceeds the authored limit")
    reverse_projection = [
        json.dumps(frames[index], sort_keys=True)
        for index in range(479, -1, -1)
    ][::-1]
    forward_projection = [json.dumps(frame, sort_keys=True) for frame in frames]
    if reverse_projection != forward_projection:
        fail("camera previs is not exactly reversible by frame index")
    if [entry.get("phase") for entry in plan.get("phaseHistory", [])] != [
        "case-research",
        "creative-routes",
        "five-shot-script",
        "animatic",
    ]:
        fail("phase history must stop at the reviewed animatic gate")

    validator = str(SKILL / "scripts" / "validate-creative-development.mjs")
    animatic_gate = run(
        [
            node,
            validator,
            "--plan",
            str(PLAN),
            "--through",
            "animatic",
        ],
        expect_success=True,
    )
    if "PASS:" not in animatic_gate.stdout:
        fail("animatic phase validator did not report PASS")

    confirmation_gate = run(
        [node, validator, "--plan", str(PLAN)],
        expect_success=False,
    )
    confirmation_output = confirmation_gate.stdout + confirmation_gate.stderr
    if "confirmation.status must be approved" not in confirmation_output:
        fail("pending confirmation did not fail for the expected reason")

    generator = str(SKILL / "scripts" / "generate-story-manifest.mjs")
    generation = run(
        [
            node,
            generator,
            "--model",
            str(MODEL),
            "--creative-plan",
            str(PLAN),
        ],
        expect_success=False,
    )
    generation_output = generation.stdout + generation.stderr
    if "confirmation.status must be approved" not in generation_output:
        fail("runtime generation was not blocked by pending confirmation")

    runtime_diff = run(
        [git, "diff", "--quiet", BASELINE_COMMIT, "--", "docs/experiment"],
        expect_success=True,
    )
    if runtime_diff.returncode != 0:
        fail("public runtime changed during preproduction-only work")

    print(
        "PASS: car story has traceable professional-camera research, three routes, "
        "a deterministic 480-frame camera previs, five reviewed storyboard shots, "
        "a 16-second path animatic record, and a closed runtime gate"
    )


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, KeyError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
