#!/usr/bin/env python3
"""Validate the Goal27 fixed-ball-valve hero delivery bridge."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs" / "assets" / "ztovalve" / "hero" / "goal27-delivery-bridge-manifest.json"
INDEX = ROOT / "docs" / "index.html"
EXPECTED_FALLBACK_REF = "/roke-fittings-study/assets/ztovalve/hero/fixed-ball-valve-mobile-fallback.png"


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_json(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"missing {rel(path)}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{rel(path)} must be a JSON object")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    require(manifest["goalId"] == "goal27-fixed-ball-valve-hero-delivery-bridge", "unexpected Goal27 manifest id")
    require(manifest["sourceRoot"] == "docs/experiment/hero", "source root drifted")
    require(manifest["deliveryRoot"] == "docs/assets/ztovalve/hero", "delivery root drifted")

    mappings = manifest.get("mappings")
    require(isinstance(mappings, list) and mappings, "Goal27 mappings must be a non-empty list")

    visitor_targets = []
    seen_targets = set()
    for index, mapping in enumerate(mappings):
        require(isinstance(mapping, dict), f"mapping {index} must be an object")
        source = project_path(mapping["source"])
        target = project_path(mapping["target"])
        require(source.is_file(), f"missing source {rel(source)}")
        require(target.is_file(), f"missing target {rel(target)}")
        require(rel(target).startswith(manifest["deliveryRoot"] + "/"), f"target is outside delivery root: {rel(target)}")
        require(rel(source).startswith(manifest["sourceRoot"] + "/"), f"source is outside experiment root: {rel(source)}")
        require(rel(target) not in seen_targets, f"duplicate delivery target: {rel(target)}")
        seen_targets.add(rel(target))
        require(target.stat().st_size == mapping["bytes"], f"byte size drifted for {rel(target)}")
        require(target.stat().st_size < 100 * 1024 * 1024, f"delivery file exceeds GitHub Pages size limit: {rel(target)}")
        target_hash = sha256(target)
        source_hash = sha256(source)
        require(target_hash == mapping["sha256"], f"target hash drifted for {rel(target)}")
        require(source_hash == mapping["sha256"], f"source/target hash mismatch for {rel(target)}")
        if mapping.get("visitorFacing") is True:
            visitor_targets.append(rel(target))

    fallback = "docs/assets/ztovalve/hero/fixed-ball-valve-mobile-fallback.png"
    require(fallback in visitor_targets, "visitor-facing fixed ball valve fallback is not mapped")
    require(INDEX.is_file(), "docs/index.html is missing")
    index_text = INDEX.read_text(encoding="utf-8")
    require(index_text.count(EXPECTED_FALLBACK_REF) >= 2, "docs/index.html no longer references the delivered fallback")
    require("goal26-blender-camera-explosion-proof/index.html" not in index_text, "Goal26 review page must not be linked from homepage")

    sequence_dir = project_path(manifest["pagesContract"]["runtimeSequence"])
    require(sequence_dir.is_dir(), "runtime AVIF sequence directory is missing")
    frame_count = len([path for path in sequence_dir.iterdir() if path.suffix.lower() == ".avif" and path.stat().st_size > 100])
    require(frame_count == manifest["pagesContract"]["currentSequenceFrameCount"], "runtime AVIF frame count drifted")

    goal26_manifest = read_json(ROOT / "docs" / "assets" / "ztovalve" / "hero" / "goal26-blender-camera-explosion-proof" / "render-manifest.json")
    for key in ("stepMesh", "cameraPrevis", "motionControl", "goal20SemanticMap"):
        require(project_path(goal26_manifest["sourceBoundary"][key]).is_file(), f"Goal26 delivery source is missing: {key}")
    for still in goal26_manifest["stills"]:
        require(project_path(still["path"]).is_file(), f"Goal26 delivery still is missing: {still['path']}")

    print("PASS: Goal27 fixed-ball-valve hero delivery bridge is mapped and Pages-ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
