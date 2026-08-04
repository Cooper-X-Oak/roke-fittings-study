#!/usr/bin/env python3
"""Standalone V3 Blender preview entry for the ztovalve fixed ball valve hero.

This script is intentionally independent from the older render scripts. It
loads the V3 semantic node map, verifies GLB nodeIndex selectors against the
target GLB, and can optionally import the GLB into Blender for a low-cost scene
probe. It does not render the final hero, connect the homepage, or generate a
240-frame sequence.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_MAP = "docs/assets/ztovalve/hero/v3-semantic-node-map.json"
DEFAULT_OUTPUT = "docs/assets/ztovalve/hero/v3-blender-preview-entry/latest-preview-state.json"
OWNED_PREFIX = "v3_preview_"


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    args = argv[argv.index("--") + 1 :] if "--" in argv else argv[1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--semantic-map", default=DEFAULT_MAP)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--import-scene", action="store_true")
    parser.add_argument("--save-blend", default="")
    return parser.parse_args(args)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def project_path(repo_root: Path, value: str) -> Path:
    path = (repo_root / value).resolve()
    path.relative_to(repo_root)
    return path


def read_glb_json(path: Path) -> dict[str, Any]:
    with path.open("rb") as file:
        header = file.read(12)
        if len(header) != 12:
            raise RuntimeError(f"Invalid GLB header: {path}")
        magic, version, total_length = struct.unpack("<III", header)
        if magic != 0x46546C67 or version != 2:
            raise RuntimeError(f"Expected glTF 2.0 GLB: {path}")
        chunk_header = file.read(8)
        if len(chunk_header) != 8:
            raise RuntimeError(f"Missing GLB JSON chunk: {path}")
        chunk_length, chunk_type = struct.unpack("<II", chunk_header)
        if chunk_type != 0x4E4F534A:
            raise RuntimeError(f"First GLB chunk is not JSON: {path}")
        json_bytes = file.read(chunk_length)
        if len(json_bytes) != chunk_length:
            raise RuntimeError(f"Truncated GLB JSON chunk: {path}")
        if total_length != path.stat().st_size:
            raise RuntimeError(f"GLB length mismatch: {path}")
    return json.loads(json_bytes.decode("utf-8"))


def flatten_selectors(semantic_map: dict[str, Any]) -> list[dict[str, Any]]:
    selectors: list[dict[str, Any]] = []
    for group in semantic_map.get("groups", []):
        for part in group.get("parts", []):
            for node_index in part.get("nodeIndices", []):
                selectors.append(
                    {
                        "groupId": group["groupId"],
                        "partName": part["partName"],
                        "expectedGlbName": part.get("expectedGlbName"),
                        "nodeIndex": node_index,
                    }
                )
    return selectors


def choose_glb(repo_root: Path, semantic_map: dict[str, Any]) -> tuple[Path, str]:
    glb_source = semantic_map["sourceEvidence"]["glbSource"]
    candidates = [
        ("preferred", glb_source["preferredPath"]),
        ("scratch-fallback", glb_source["scratchMirrorPath"]),
    ]
    for source_kind, value in candidates:
        path = project_path(repo_root, value)
        if path.is_file():
            return path, source_kind
    raise RuntimeError("No V3 GLB source exists at preferredPath or scratchMirrorPath.")


def validate_selectors(semantic_map: dict[str, Any], glb: dict[str, Any]) -> dict[str, Any]:
    nodes = glb.get("nodes", [])
    selectors = flatten_selectors(semantic_map)
    missing: list[dict[str, Any]] = []
    name_mismatches: list[dict[str, Any]] = []
    seen_indices: set[int] = set()
    for selector in selectors:
        node_index = selector["nodeIndex"]
        seen_indices.add(node_index)
        if node_index < 0 or node_index >= len(nodes):
            missing.append(selector)
            continue
        actual_name = nodes[node_index].get("name")
        expected_name = selector.get("expectedGlbName")
        if expected_name and actual_name != expected_name:
            name_mismatches.append(
                {
                    **selector,
                    "actualGlbName": actual_name,
                }
            )

    group_counts = {
        group["groupId"]: sum(len(part.get("nodeIndices", [])) for part in group.get("parts", []))
        for group in semantic_map.get("groups", [])
    }
    return {
        "selectorCount": len(selectors),
        "uniqueNodeIndexCount": len(seen_indices),
        "groupCounts": group_counts,
        "missingSelectors": missing,
        "nameMismatches": name_mismatches,
        "status": "pass" if not missing and not name_mismatches else "fail",
    }


def maybe_import_scene(repo_root: Path, glb_path: Path, semantic_map: dict[str, Any], selector_result: dict[str, Any]) -> dict[str, Any]:
    try:
        import bpy  # type: ignore
    except ImportError as exc:
        raise RuntimeError("Blender import requested, but bpy is unavailable. Run through blender --background.") from exc

    if selector_result["status"] != "pass":
        raise RuntimeError("Selector validation must pass before importing the scene.")

    for obj in list(bpy.context.scene.objects):
        if obj.name.startswith(OWNED_PREFIX):
            bpy.data.objects.remove(obj, do_unlink=True)
    for collection in list(bpy.data.collections):
        if collection.name.startswith(OWNED_PREFIX):
            bpy.data.collections.remove(collection)

    root_collection = bpy.data.collections.new(f"{OWNED_PREFIX}ztovalve_v3")
    bpy.context.scene.collection.children.link(root_collection)

    before_objects = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(glb_path))
    imported_objects = [obj for obj in bpy.data.objects if obj not in before_objects]
    imported_collection = bpy.data.collections.new(f"{OWNED_PREFIX}imported_glb")
    root_collection.children.link(imported_collection)
    for obj in imported_objects:
        for collection in list(obj.users_collection):
            collection.objects.unlink(obj)
        imported_collection.objects.link(obj)
        obj["v3_source"] = "fixed-ball-valve.glb"

    selector_by_group = selector_result["groupCounts"]
    empty_names: list[str] = []
    for group in semantic_map["groups"]:
        empty = bpy.data.objects.new(f"{OWNED_PREFIX}{group['groupId']}", None)
        empty.empty_display_type = "CUBE"
        empty.empty_display_size = 0.08
        empty["semantic_group_id"] = group["groupId"]
        empty["node_indices"] = json.dumps(
            [
                node_index
                for part in group.get("parts", [])
                for node_index in part.get("nodeIndices", [])
            ],
            ensure_ascii=False,
        )
        empty["selector_count"] = selector_by_group[group["groupId"]]
        root_collection.objects.link(empty)
        empty_names.append(empty.name)

    camera_data = bpy.data.cameras.new(f"{OWNED_PREFIX}camera_data")
    camera = bpy.data.objects.new(f"{OWNED_PREFIX}camera", camera_data)
    camera.location = (0.42, -0.72, 0.46)
    camera.rotation_euler = (1.1, 0.0, 0.54)
    camera_data.lens = 70
    root_collection.objects.link(camera)
    bpy.context.scene.camera = camera

    light_data = bpy.data.lights.new(f"{OWNED_PREFIX}key_area_data", "AREA")
    light = bpy.data.objects.new(f"{OWNED_PREFIX}key_area", light_data)
    light.location = (0.12, -0.45, 0.95)
    light_data.energy = 450
    light_data.size = 2.2
    root_collection.objects.link(light)

    return {
        "importedObjectCount": len(imported_objects),
        "semanticGroupEmptyNames": empty_names,
        "camera": camera.name,
        "keyLight": light.name,
    }


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    semantic_map_path = project_path(repo_root, args.semantic_map)
    output_path = project_path(repo_root, args.output)
    semantic_map = read_json(semantic_map_path)
    if semantic_map.get("schema") != "ztovalve-v3-semantic-node-map/v1":
        raise RuntimeError("Unexpected semantic map schema.")
    if semantic_map.get("scope", {}).get("touchesGoal30") is not False:
        raise RuntimeError("V3 semantic map must remain isolated from Goal30.")

    glb_path, glb_source_kind = choose_glb(repo_root, semantic_map)
    glb = read_glb_json(glb_path)
    selector_result = validate_selectors(semantic_map, glb)
    if selector_result["status"] != "pass":
        state = {
            "schema": "ztovalve-v3-blender-preview-state/v1",
            "status": "selector-validation-failed",
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "semanticMap": str(semantic_map_path.relative_to(repo_root)).replace("\\", "/"),
            "glb": str(glb_path.relative_to(repo_root)).replace("\\", "/"),
            "selectorValidation": selector_result,
        }
        write_json(output_path, state)
        print(json.dumps(state, ensure_ascii=False, indent=2))
        return 1

    import_result: dict[str, Any] | None = None
    if args.import_scene:
        import_result = maybe_import_scene(repo_root, glb_path, semantic_map, selector_result)
        if args.save_blend:
            import bpy  # type: ignore

            blend_path = project_path(repo_root, args.save_blend)
            blend_path.parent.mkdir(parents=True, exist_ok=True)
            bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
            import_result["savedBlend"] = str(blend_path.relative_to(repo_root)).replace("\\", "/")

    state = {
        "schema": "ztovalve-v3-blender-preview-state/v1",
        "status": "pass",
        "mode": "import-scene" if args.import_scene else "dry-run",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "semanticMap": str(semantic_map_path.relative_to(repo_root)).replace("\\", "/"),
        "glb": str(glb_path.relative_to(repo_root)).replace("\\", "/"),
        "glbSourceKind": glb_source_kind,
        "selectorValidation": selector_result,
        "importResult": import_result,
        "nextStep": "Run Blender close-up contact and six-side inspection before rendering preview stills.",
    }
    write_json(output_path, state)
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)
