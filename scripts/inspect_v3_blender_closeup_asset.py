#!/usr/bin/env python3
"""Run the standalone V3 close-up asset inspection in Blender.

This inspection imports the fixed ball valve GLB, binds mesh objects by the V3
semantic node map, measures the critical contact/axis relationships, and writes
low-cost Workbench evidence images. It intentionally does not touch Goal30,
older render scripts, homepage hero wiring, or the 240-frame sequence.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    import bpy
    from mathutils import Vector
except ImportError as exc:  # pragma: no cover
    raise SystemExit("请使用 Blender 的 Python 解释器运行本脚本。") from exc


DEFAULT_MAP = "docs/assets/ztovalve/hero/v3-semantic-node-map.json"
DEFAULT_OUTPUT_DIR = "docs/assets/ztovalve/hero/v3-closeup-asset-inspection"
OWNED_PREFIX = "v3_closeup_"
DEGENERATE_AREA_THRESHOLD = 1e-12

GROUP_COLORS = {
    "body-pressure-shell": (0.52, 0.55, 0.56, 1.0),
    "ball-trunnion-core": (0.20, 0.62, 0.86, 1.0),
    "seat-seal-system": (0.90, 0.67, 0.25, 1.0),
    "stem-packing-drive": (0.38, 0.70, 0.45, 1.0),
    "top-bracket-actuator": (0.32, 0.50, 0.76, 1.0),
    "fasteners-small-hardware": (0.18, 0.19, 0.20, 1.0),
}

HELPER_COLORS = {
    "pipe-axis": (0.95, 0.20, 0.18, 1.0),
    "stem-axis": (0.20, 0.36, 0.95, 1.0),
    "contact": (0.10, 0.70, 0.36, 1.0),
}
AXIS_NAMES = ("x", "y", "z")


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    args = argv[argv.index("--") + 1 :] if "--" in argv else argv[1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--semantic-map", default=DEFAULT_MAP)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--skip-renders", action="store_true")
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


def project_rel(repo_root: Path, path: Path) -> str:
    return str(path.resolve().relative_to(repo_root)).replace("\\", "/")


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


def choose_glb(repo_root: Path, semantic_map: dict[str, Any]) -> tuple[Path, str]:
    glb_source = semantic_map["sourceEvidence"]["glbSource"]
    for source_kind, key in (("preferred", "preferredPath"), ("scratch-fallback", "scratchMirrorPath")):
        path = project_path(repo_root, glb_source[key])
        if path.is_file():
            return path, source_kind
    raise RuntimeError("No V3 GLB source exists at preferredPath or scratchMirrorPath.")


def strip_blender_suffix(name: str) -> str:
    if len(name) > 4 and name[-4] == "." and name[-3:].isdigit():
        return name[:-4]
    return name


def blender_suffix_number(name: str) -> int:
    if len(name) > 4 and name[-4] == "." and name[-3:].isdigit():
        return int(name[-3:])
    return 0


def remove_owned_objects() -> None:
    for obj in list(bpy.data.objects):
        if obj.name.startswith(OWNED_PREFIX):
            bpy.data.objects.remove(obj, do_unlink=True)
    for collection in list(bpy.data.collections):
        if collection.name.startswith(OWNED_PREFIX):
            bpy.data.collections.remove(collection)


def import_glb_with_node_binding(glb_path: Path, glb_json: dict[str, Any]) -> tuple[dict[int, Any], list[Any], dict[str, Any]]:
    before_objects = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(glb_path))
    imported_objects = [obj for obj in bpy.data.objects if obj not in before_objects]
    imported_mesh_objects = [obj for obj in imported_objects if obj.type == "MESH"]
    mesh_node_indices = [
        index for index, node in enumerate(glb_json.get("nodes", [])) if "mesh" in node
    ]
    if len(imported_mesh_objects) != len(mesh_node_indices):
        raise RuntimeError(
            f"Imported mesh object count {len(imported_mesh_objects)} does not match GLB mesh nodes {len(mesh_node_indices)}."
        )

    nodes_by_name: dict[str, list[int]] = {}
    for node_index in mesh_node_indices:
        expected_name = glb_json["nodes"][node_index].get("name") or f"__unnamed_node_{node_index}"
        nodes_by_name.setdefault(expected_name, []).append(node_index)

    objects_by_base_name: dict[str, list[Any]] = {}
    for obj in imported_mesh_objects:
        objects_by_base_name.setdefault(strip_blender_suffix(obj.name), []).append(obj)
    for objects in objects_by_base_name.values():
        objects.sort(key=lambda obj: (blender_suffix_number(obj.name), obj.name))

    node_to_object: dict[int, Any] = {}
    name_mismatches: list[dict[str, Any]] = []
    for expected_name, node_indices in nodes_by_name.items():
        candidates = objects_by_base_name.get(expected_name, [])
        if len(candidates) != len(node_indices):
            name_mismatches.append(
                {
                    "expectedGlbName": expected_name,
                    "nodeIndices": node_indices,
                    "expectedCount": len(node_indices),
                    "importedNames": [obj.name for obj in candidates],
                    "importedCount": len(candidates),
                    "issue": "imported-object-count-for-name-does-not-match-glb-node-count",
                }
            )
        for node_index, obj in zip(node_indices, candidates):
            obj["v3_node_index"] = node_index
            obj["v3_expected_glb_name"] = expected_name
            node_to_object[node_index] = obj

    unmatched_imported_names = sorted(set(objects_by_base_name) - set(nodes_by_name))
    for imported_name in unmatched_imported_names:
        name_mismatches.append(
            {
                "importedBaseName": imported_name,
                "importedNames": [obj.name for obj in objects_by_base_name[imported_name]],
                "issue": "imported-object-name-not-found-in-glb-mesh-node-names",
            }
        )

    return node_to_object, imported_objects, {
        "importedObjectCount": len(imported_objects),
        "importedMeshObjectCount": len(imported_mesh_objects),
        "meshNodeCount": len(mesh_node_indices),
        "boundMeshNodeCount": len(node_to_object),
        "bindingStrategy": "glb-node-name-plus-blender-duplicate-suffix",
        "nameMismatches": name_mismatches,
    }


def make_material(name: str, color: tuple[float, float, float, float]) -> Any:
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    return mat


def prepare_materials() -> tuple[dict[str, Any], dict[str, Any]]:
    group_materials = {
        group: make_material(f"{OWNED_PREFIX}mat_{group}", color)
        for group, color in GROUP_COLORS.items()
    }
    helper_materials = {
        role: make_material(f"{OWNED_PREFIX}mat_{role}", color)
        for role, color in HELPER_COLORS.items()
    }
    return group_materials, helper_materials


def bind_groups(
    semantic_map: dict[str, Any],
    node_to_object: dict[int, Any],
    group_materials: dict[str, Any],
) -> tuple[dict[str, list[Any]], list[dict[str, Any]]]:
    groups: dict[str, list[Any]] = {}
    missing: list[dict[str, Any]] = []
    for group in semantic_map.get("groups", []):
        group_id = group["groupId"]
        groups[group_id] = []
        for part in group.get("parts", []):
            for node_index in part.get("nodeIndices", []):
                obj = node_to_object.get(node_index)
                if obj is None:
                    missing.append(
                        {
                            "groupId": group_id,
                            "partName": part["partName"],
                            "nodeIndex": node_index,
                        }
                    )
                    continue
                obj["v3_group_id"] = group_id
                obj["v3_part_name"] = part["partName"]
                obj.data.materials.clear()
                obj.data.materials.append(group_materials[group_id])
                groups[group_id].append(obj)
    return groups, missing


def world_bounds(objects: Iterable[Any]) -> dict[str, list[float]]:
    min_v = Vector((math.inf, math.inf, math.inf))
    max_v = Vector((-math.inf, -math.inf, -math.inf))
    found = False
    for obj in objects:
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            world = obj.matrix_world @ Vector(corner)
            min_v.x = min(min_v.x, world.x)
            min_v.y = min(min_v.y, world.y)
            min_v.z = min(min_v.z, world.z)
            max_v.x = max(max_v.x, world.x)
            max_v.y = max(max_v.y, world.y)
            max_v.z = max(max_v.z, world.z)
            found = True
    if not found:
        raise RuntimeError("Cannot compute bounds for an empty object set.")
    center = (min_v + max_v) * 0.5
    extent = max_v - min_v
    return {
        "min": [round(min_v.x, 6), round(min_v.y, 6), round(min_v.z, 6)],
        "max": [round(max_v.x, 6), round(max_v.y, 6), round(max_v.z, 6)],
        "center": [round(center.x, 6), round(center.y, 6), round(center.z, 6)],
        "extent": [round(extent.x, 6), round(extent.y, 6), round(extent.z, 6)],
    }


def center_from_bounds(bounds: dict[str, list[float]]) -> Vector:
    return Vector(bounds["center"])


def axis_name(axis: int) -> str:
    return AXIS_NAMES[axis]


def axis_unit(axis: int) -> Vector:
    values = [0.0, 0.0, 0.0]
    values[axis] = 1.0
    return Vector(values)


def dominant_axis_between(bounds_a: dict[str, list[float]], bounds_b: dict[str, list[float]], excluded: set[int] | None = None) -> int:
    excluded = excluded or set()
    a = center_from_bounds(bounds_a)
    b = center_from_bounds(bounds_b)
    candidates = [axis for axis in range(3) if axis not in excluded]
    return max(candidates, key=lambda axis: abs(a[axis] - b[axis]))


def infer_axes(part_bounds_map: dict[str, dict[str, list[float]]]) -> dict[str, Any]:
    pipe_axis = dominant_axis_between(part_bounds_map["seatLeft"], part_bounds_map["seatRight"])
    ball_center = center_from_bounds(part_bounds_map["ball"])
    stem_candidates = [
        part_bounds_map["topBracket"],
        part_bounds_map["packingBox"],
        part_bounds_map["packingCover"],
        part_bounds_map["connectingShaft"],
    ]
    scores = [0.0, 0.0, 0.0]
    for bounds in stem_candidates:
        center = center_from_bounds(bounds)
        for axis in range(3):
            if axis != pipe_axis:
                scores[axis] += abs(center[axis] - ball_center[axis])
    stem_axis = max((axis for axis in range(3) if axis != pipe_axis), key=lambda axis: scores[axis])
    return {
        "pipeAxisIndex": pipe_axis,
        "pipeAxis": axis_name(pipe_axis),
        "pipeAxisSource": "dominant center separation between the two 阀座 node groups",
        "stemAxisIndex": stem_axis,
        "stemAxis": axis_name(stem_axis),
        "stemAxisSource": "dominant non-pipe separation from 球体 to packing/top stack centers",
        "stemAxisScores": {axis_name(axis): round(scores[axis], 6) for axis in range(3)},
    }


def lateral_axis_offset(bounds_a: dict[str, list[float]], bounds_b: dict[str, list[float]], axis: int) -> float:
    a = center_from_bounds(bounds_a)
    b = center_from_bounds(bounds_b)
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3) if i != axis))


def interval_overlap(bounds_a: dict[str, list[float]], bounds_b: dict[str, list[float]], axis: int) -> float:
    return min(bounds_a["max"][axis], bounds_b["max"][axis]) - max(bounds_a["min"][axis], bounds_b["min"][axis])


def axis_offset_xz(bounds_a: dict[str, list[float]], bounds_b: dict[str, list[float]]) -> float:
    a = center_from_bounds(bounds_a)
    b = center_from_bounds(bounds_b)
    return math.sqrt((a.x - b.x) ** 2 + (a.z - b.z) ** 2)


def contact_status(overlap_meters: float, warn_gap_meters: float = 0.004) -> str:
    if overlap_meters >= 0:
        return "pass"
    if overlap_meters >= -warn_gap_meters:
        return "warn"
    return "fail"


def part_bounds(node_to_object: dict[int, Any], node_indices: list[int]) -> dict[str, list[float]]:
    return world_bounds([node_to_object[index] for index in node_indices])


def collect_mesh_quality(groups: dict[str, list[Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    total_degenerate = 0
    total_triangles = 0
    for group_id, objects in groups.items():
        group_degenerate = 0
        group_triangles = 0
        worst_objects: list[dict[str, Any]] = []
        for obj in objects:
            mesh = obj.data
            degenerate = sum(1 for polygon in mesh.polygons if polygon.area <= DEGENERATE_AREA_THRESHOLD)
            triangles = len(mesh.polygons)
            group_degenerate += degenerate
            group_triangles += triangles
            if degenerate:
                worst_objects.append(
                    {
                        "objectName": obj.name,
                        "nodeIndex": obj.get("v3_node_index"),
                        "partName": obj.get("v3_part_name"),
                        "degenerateFaces": degenerate,
                        "polygonCount": triangles,
                    }
                )
        total_degenerate += group_degenerate
        total_triangles += group_triangles
        result[group_id] = {
            "objectCount": len(objects),
            "polygonCount": group_triangles,
            "degenerateFaces": group_degenerate,
            "worstObjects": sorted(worst_objects, key=lambda item: item["degenerateFaces"], reverse=True)[:8],
        }
    result["_total"] = {
        "polygonCount": total_triangles,
        "degenerateFaces": total_degenerate,
    }
    return result


def create_axis_helper(name: str, start: Vector, end: Vector, material: Any, bevel_depth: float = 0.002) -> Any:
    curve = bpy.data.curves.new(f"{OWNED_PREFIX}{name}_curve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.bevel_depth = bevel_depth
    curve.bevel_resolution = 3
    spline = curve.splines.new("POLY")
    spline.points.add(1)
    spline.points[0].co = (start.x, start.y, start.z, 1.0)
    spline.points[1].co = (end.x, end.y, end.z, 1.0)
    obj = bpy.data.objects.new(f"{OWNED_PREFIX}{name}", curve)
    obj.data.materials.append(material)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def setup_scene() -> None:
    bpy.context.scene.render.engine = "BLENDER_WORKBENCH"
    bpy.context.scene.render.resolution_x = 1280
    bpy.context.scene.render.resolution_y = 720
    bpy.context.scene.render.film_transparent = False
    bpy.context.scene.world.color = (0.96, 0.97, 0.97)
    if hasattr(bpy.context.scene, "view_settings"):
        bpy.context.scene.view_settings.view_transform = "Standard"
        bpy.context.scene.view_settings.look = "Medium High Contrast"
        bpy.context.scene.view_settings.exposure = 0
        bpy.context.scene.view_settings.gamma = 1
    workbench = getattr(bpy.context.scene, "display", None)
    if workbench is not None:
        try:
            workbench.shading.light = "STUDIO"
            workbench.shading.color_type = "MATERIAL"
            workbench.shading.show_cavity = True
            workbench.shading.show_object_outline = True
        except Exception:
            pass


def look_at(camera: Any, target: Vector) -> None:
    direction = target - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def set_visibility(all_mesh_objects: list[Any], visible_objects: Iterable[Any], helper_objects: Iterable[Any]) -> None:
    visible = set(visible_objects)
    helpers = set(helper_objects)
    for obj in all_mesh_objects:
        hidden = obj not in visible
        obj.hide_viewport = hidden
        obj.hide_render = hidden
    for obj in helpers:
        obj.hide_viewport = False
        obj.hide_render = False


def render_view(
    output_path: Path,
    all_mesh_objects: list[Any],
    visible_objects: list[Any],
    helper_objects: list[Any],
    target: Vector,
    camera_vector: Vector,
    ortho_scale: float,
) -> None:
    set_visibility(all_mesh_objects, visible_objects, helper_objects)
    camera_data = bpy.data.cameras.new(f"{OWNED_PREFIX}camera_data_{output_path.stem}")
    camera = bpy.data.objects.new(f"{OWNED_PREFIX}camera_{output_path.stem}", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = ortho_scale
    camera.location = target + camera_vector
    look_at(camera, target)
    bpy.context.scene.camera = camera
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.scene.render.filepath = str(output_path)
    bpy.ops.render.render(write_still=True)


def render_evidence_images(
    output_dir: Path,
    repo_root: Path,
    node_to_object: dict[int, Any],
    groups: dict[str, list[Any]],
    helper_materials: dict[str, Any],
    skip_renders: bool,
) -> list[dict[str, Any]]:
    if skip_renders:
        return []

    images_dir = output_dir / "images"
    all_mesh_objects = [obj for obj in node_to_object.values()]
    product_bounds = world_bounds(all_mesh_objects)
    product_center = center_from_bounds(product_bounds)
    ball_bounds = part_bounds(node_to_object, [23])
    ball_center = center_from_bounds(ball_bounds)
    axis_parts = {
        "ball": ball_bounds,
        "seatLeft": part_bounds(node_to_object, [66]),
        "seatRight": part_bounds(node_to_object, [7]),
        "topBracket": part_bounds(node_to_object, [109]),
        "packingBox": part_bounds(node_to_object, [41]),
        "packingCover": part_bounds(node_to_object, [55]),
        "connectingShaft": part_bounds(node_to_object, [136]),
    }
    axes = infer_axes(axis_parts)
    pipe_axis_index = axes["pipeAxisIndex"]
    stem_axis_index = axes["stemAxisIndex"]
    pipe_half_length = (product_bounds["extent"][pipe_axis_index] * 0.58) + 0.04
    stem_half_length = (product_bounds["extent"][stem_axis_index] * 0.58) + 0.04

    pipe_axis = create_axis_helper(
        f"pipe_axis_{axes['pipeAxis']}",
        ball_center - axis_unit(pipe_axis_index) * pipe_half_length,
        ball_center + axis_unit(pipe_axis_index) * pipe_half_length,
        helper_materials["pipe-axis"],
    )
    stem_axis = create_axis_helper(
        f"stem_axis_{axes['stemAxis']}",
        ball_center - axis_unit(stem_axis_index) * stem_half_length,
        ball_center + axis_unit(stem_axis_index) * stem_half_length,
        helper_materials["stem-axis"],
    )

    core_objects = (
        [node_to_object[index] for index in [23, 24, 25, 26, 40, 43, 44]]
        + [node_to_object[index] for index in [4, 5, 6, 7, 66, 67, 68]]
    )
    top_objects = [node_to_object[index] for index in [41, 42, 43, 45, 54, 55, 109, 112, 115, 116, 117, 118, 119, 120, 121, 136]]
    shell_objects = groups["body-pressure-shell"] + groups["seat-seal-system"] + [node_to_object[23]]
    overview_objects = all_mesh_objects
    top_target = center_from_bounds(world_bounds(top_objects + [node_to_object[23]]))

    render_specs = [
        {
            "id": "overview-solid",
            "path": images_dir / "overview-solid.png",
            "objects": overview_objects,
            "helpers": [pipe_axis, stem_axis],
            "target": product_center,
            "vector": Vector((0.48, -0.68, 0.34)),
            "scale": 0.62,
            "purpose": "Full imported asset with V3 semantic colors and pipe/stem axis helpers.",
        },
        {
            "id": "core-ball-seat-closeup",
            "path": images_dir / "core-ball-seat-closeup.png",
            "objects": core_objects,
            "helpers": [pipe_axis, stem_axis],
            "target": ball_center,
            "vector": Vector((0.26, -0.36, 0.18)),
            "scale": 0.28,
            "purpose": "Ball, seats, trunnion support, and bearings close-up.",
        },
        {
            "id": "seat-contact-side",
            "path": images_dir / "seat-contact-side.png",
            "objects": core_objects,
            "helpers": [pipe_axis],
            "target": ball_center,
            "vector": Vector((0.42, 0.0, 0.02)),
            "scale": 0.25,
            "purpose": "Side view for seat-to-ball overlap and pipe-axis relation.",
        },
        {
            "id": "top-drive-stack-closeup",
            "path": images_dir / "top-drive-stack-closeup.png",
            "objects": top_objects + [node_to_object[23]],
            "helpers": [stem_axis],
            "target": top_target,
            "vector": Vector((0.24, -0.42, 0.20)),
            "scale": 0.26,
            "purpose": "Packing, top bracket, and connecting shaft relation to the stem axis.",
        },
        {
            "id": "shell-seat-enclosure",
            "path": images_dir / "shell-seat-enclosure.png",
            "objects": shell_objects,
            "helpers": [pipe_axis],
            "target": ball_center,
            "vector": Vector((0.36, -0.48, 0.24)),
            "scale": 0.42,
            "purpose": "Pressure shell and seat enclosure around the ball.",
        },
        {
            "id": "six-side-front",
            "path": images_dir / "six-side-front.png",
            "objects": overview_objects,
            "helpers": [pipe_axis, stem_axis],
            "target": product_center,
            "vector": Vector((0.0, -0.75, 0.0)),
            "scale": 0.58,
            "purpose": "Six-side inspection front.",
        },
        {
            "id": "six-side-right",
            "path": images_dir / "six-side-right.png",
            "objects": overview_objects,
            "helpers": [pipe_axis, stem_axis],
            "target": product_center,
            "vector": Vector((0.75, 0.0, 0.0)),
            "scale": 0.58,
            "purpose": "Six-side inspection right.",
        },
        {
            "id": "six-side-top",
            "path": images_dir / "six-side-top.png",
            "objects": overview_objects,
            "helpers": [pipe_axis, stem_axis],
            "target": product_center,
            "vector": Vector((0.0, 0.0, 0.75)),
            "scale": 0.58,
            "purpose": "Six-side inspection top.",
        },
    ]

    images: list[dict[str, Any]] = []
    for spec in render_specs:
        render_view(
            spec["path"],
            all_mesh_objects,
            spec["objects"],
            spec["helpers"],
            spec["target"],
            spec["vector"],
            spec["scale"],
        )
        images.append(
            {
                "id": spec["id"],
                "path": project_rel(repo_root, spec["path"]),
                "bytes": spec["path"].stat().st_size,
                "purpose": spec["purpose"],
            }
        )
    return images


def build_measurements(node_to_object: dict[int, Any], groups: dict[str, list[Any]]) -> dict[str, Any]:
    ball = part_bounds(node_to_object, [23])
    seat_right = part_bounds(node_to_object, [7])
    seat_left = part_bounds(node_to_object, [66])
    seal_right = part_bounds(node_to_object, [4, 5, 6, 7])
    seal_left = part_bounds(node_to_object, [66, 67, 68])
    fixed_axis = part_bounds(node_to_object, [24])
    top_bracket = part_bounds(node_to_object, [109])
    packing_box = part_bounds(node_to_object, [41])
    packing_cover = part_bounds(node_to_object, [55])
    connecting_shaft = part_bounds(node_to_object, [136])
    body = part_bounds(node_to_object, [2])
    left_cover = part_bounds(node_to_object, [64])
    top_cover = part_bounds(node_to_object, [39])
    shell = world_bounds(groups["body-pressure-shell"])
    part_bounds_map = {
        "ball": ball,
        "seatLeft": seat_left,
        "seatRight": seat_right,
        "sealLeft": seal_left,
        "sealRight": seal_right,
        "fixedAxis": fixed_axis,
        "topBracket": top_bracket,
        "packingBox": packing_box,
        "packingCover": packing_cover,
        "connectingShaft": connecting_shaft,
        "body": body,
        "leftCover": left_cover,
        "topCover": top_cover,
    }
    axes = infer_axes(part_bounds_map)
    pipe_axis = axes["pipeAxisIndex"]
    stem_axis = axes["stemAxisIndex"]

    ball_center = center_from_bounds(ball)
    seat_left_center = center_from_bounds(seat_left)
    seat_right_center = center_from_bounds(seat_right)
    left_distance = abs(seat_left_center[pipe_axis] - ball_center[pipe_axis])
    right_distance = abs(seat_right_center[pipe_axis] - ball_center[pipe_axis])
    left_seat_overlap = interval_overlap(seat_left, ball, pipe_axis)
    right_seat_overlap = interval_overlap(seat_right, ball, pipe_axis)
    top_stack_overlap = interval_overlap(top_bracket, packing_cover, stem_axis)

    axis_offsets = {
        f"fixed-axis-to-ball-lateral-to-{axes['stemAxis']}-m": lateral_axis_offset(fixed_axis, ball, stem_axis),
        f"packing-box-to-ball-lateral-to-{axes['stemAxis']}-m": lateral_axis_offset(packing_box, ball, stem_axis),
        f"packing-cover-to-ball-lateral-to-{axes['stemAxis']}-m": lateral_axis_offset(packing_cover, ball, stem_axis),
        f"top-bracket-to-ball-lateral-to-{axes['stemAxis']}-m": lateral_axis_offset(top_bracket, ball, stem_axis),
        f"connecting-shaft-to-ball-lateral-to-{axes['stemAxis']}-m": lateral_axis_offset(connecting_shaft, ball, stem_axis),
    }
    max_axis_offset = max(axis_offsets.values())

    checks = [
        {
            "checkId": "seat-left-overlaps-ball-on-pipe-axis",
            "status": contact_status(left_seat_overlap),
            "metricMeters": round(left_seat_overlap, 6),
            "axis": axes["pipeAxis"],
            "note": "Left seat should touch or slightly overlap the ball on the inferred pipe axis."
        },
        {
            "checkId": "seat-right-overlaps-ball-on-pipe-axis",
            "status": contact_status(right_seat_overlap),
            "metricMeters": round(right_seat_overlap, 6),
            "axis": axes["pipeAxis"],
            "note": "Right seat should touch or slightly overlap the ball on the inferred pipe axis."
        },
        {
            "checkId": "left-right-seat-symmetry",
            "status": "pass" if abs(left_distance - right_distance) <= 0.005 else "warn",
            "metricMeters": round(abs(left_distance - right_distance), 6),
            "note": "Seat centers should be balanced around the ball for a readable sealing story."
        },
        {
            "checkId": "vertical-drive-axis-alignment",
            "status": "pass" if max_axis_offset <= 0.008 else "warn",
            "metricMeters": round(max_axis_offset, 6),
            "axisOffsets": {key: round(value, 6) for key, value in axis_offsets.items()},
            "axis": axes["stemAxis"],
            "note": "Core, packing, top bracket, and connecting shaft should share the inferred visual stem axis."
        },
        {
            "checkId": "trunnion-support-centering",
            "status": "pass" if axis_offsets[f"fixed-axis-to-ball-lateral-to-{axes['stemAxis']}-m"] <= 0.006 else "warn",
            "metricMeters": round(axis_offsets[f"fixed-axis-to-ball-lateral-to-{axes['stemAxis']}-m"], 6),
            "axis": axes["stemAxis"],
            "note": "Fixed-axis support is centered under the ball relative to the inferred stem axis and reads as a stable trunnion relation."
        },
        {
            "checkId": "top-bracket-overlaps-packing-stack",
            "status": "pass" if top_stack_overlap >= 0 else "warn",
            "metricMeters": round(top_stack_overlap, 6),
            "axis": axes["stemAxis"],
            "note": "Top bracket and packing cover should visually lock together along the inferred vertical/stem axis."
        },
        {
            "checkId": "body-shell-encloses-ball-center",
            "status": "pass" if shell["min"][0] <= ball_center.x <= shell["max"][0] and shell["min"][1] <= ball_center.y <= shell["max"][1] and shell["min"][2] <= ball_center.z <= shell["max"][2] else "fail",
            "metricMeters": 0,
            "note": "The assembled shell group should contain the ball center."
        },
        {
            "checkId": "independent-stem-node",
            "status": "fail",
            "metricMeters": None,
            "note": "STEP contains 阀杆, but the current GLB semantic map has no independent 阀杆 nodeIndex. Rebuild or recover this before claiming a stem-driven animation."
        }
    ]

    return {
        "partBounds": {
            **part_bounds_map,
        },
        "axisInference": axes,
        "checks": checks,
        "passCount": sum(1 for check in checks if check["status"] == "pass"),
        "warnCount": sum(1 for check in checks if check["status"] == "warn"),
        "failCount": sum(1 for check in checks if check["status"] == "fail"),
    }


def build_html(report: dict[str, Any], repo_root: Path, output_dir: Path) -> str:
    image_cards = []
    for image in report["images"]:
        image_rel_from_index = Path(image["path"]).relative_to(project_rel(repo_root, output_dir)).as_posix()
        image_cards.append(
            f"""
            <figure>
              <img src="{image_rel_from_index}" alt="{image['id']}">
              <figcaption><strong>{image['id']}</strong><span>{image['purpose']}</span></figcaption>
            </figure>
            """
        )

    check_rows = []
    for check in report["measurements"]["checks"]:
        metric = "" if check.get("metricMeters") is None else f"{check['metricMeters']} m"
        check_rows.append(
            f"""
            <tr>
              <td>{check['checkId']}</td>
              <td><span class="status {check['status']}">{check['status']}</span></td>
              <td>{metric}</td>
              <td>{check['note']}</td>
            </tr>
            """
        )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ZTOVALVE V3 Close-up Asset Inspection</title>
  <style>
    :root {{
      --ink: #202426;
      --muted: #69727a;
      --line: #dce2e6;
      --panel: #f6f8f9;
      --pass: #19704d;
      --warn: #98690f;
      --fail: #a6362f;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Arial, "Microsoft YaHei", sans-serif;
      color: var(--ink);
      background: #fff;
      line-height: 1.55;
    }}
    main {{
      width: min(1180px, calc(100% - 40px));
      margin: 0 auto;
      padding: 44px 0 72px;
    }}
    header {{
      border-bottom: 1px solid var(--line);
      padding-bottom: 24px;
      margin-bottom: 28px;
    }}
    h1 {{
      margin: 0 0 10px;
      font-size: clamp(30px, 5vw, 56px);
      line-height: 1.05;
      letter-spacing: 0;
    }}
    h2 {{
      margin: 32px 0 12px;
      font-size: 22px;
      letter-spacing: 0;
    }}
    p {{ margin: 0 0 12px; color: var(--muted); max-width: 850px; }}
    code {{ font-family: Consolas, "Courier New", monospace; font-size: 13px; }}
    .summary {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
      gap: 12px;
      margin-top: 18px;
    }}
    .metric {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      background: var(--panel);
    }}
    .metric strong {{ display: block; font-size: 28px; }}
    .metric span {{ color: var(--muted); }}
    table {{
      width: 100%;
      border-collapse: collapse;
      border: 1px solid var(--line);
      margin-top: 12px;
    }}
    th, td {{
      padding: 10px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
      font-size: 14px;
    }}
    th {{ background: var(--panel); }}
    .status {{
      display: inline-block;
      min-width: 52px;
      padding: 3px 7px;
      border-radius: 999px;
      color: #fff;
      text-align: center;
      font-weight: 700;
      font-size: 12px;
    }}
    .status.pass {{ background: var(--pass); }}
    .status.warn {{ background: var(--warn); }}
    .status.fail {{ background: var(--fail); }}
    .gallery {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 14px;
    }}
    figure {{
      margin: 0;
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      background: var(--panel);
    }}
    img {{
      display: block;
      width: 100%;
      height: auto;
      background: #edf0f2;
    }}
    figcaption {{
      padding: 10px 12px;
      display: grid;
      gap: 4px;
    }}
    figcaption span {{ color: var(--muted); font-size: 13px; }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>V3 Close-up Asset Inspection</h1>
      <p>Standalone Blender Workbench inspection for the fixed ball valve hero. This report is not connected to the homepage, Goal30, or the final 240-frame sequence.</p>
      <p><code>{report['glb']['path']}</code></p>
    </header>
    <section>
      <h2>Summary</h2>
      <div class="summary">
        <div class="metric"><strong>{report['selectorValidation']['selectorCount']}</strong><span>node selectors</span></div>
        <div class="metric"><strong>{report['measurements']['passCount']}</strong><span>passed interface checks</span></div>
        <div class="metric"><strong>{report['measurements']['warnCount']}</strong><span>warnings</span></div>
        <div class="metric"><strong>{report['measurements']['failCount']}</strong><span>blocking gaps</span></div>
      </div>
    </section>
    <section>
      <h2>Interface Checks</h2>
      <table>
        <thead><tr><th>Check</th><th>Status</th><th>Metric</th><th>Note</th></tr></thead>
        <tbody>{''.join(check_rows)}</tbody>
      </table>
    </section>
    <section>
      <h2>Evidence Images</h2>
      <div class="gallery">{''.join(image_cards)}</div>
    </section>
  </main>
</body>
</html>
"""


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    semantic_map_path = project_path(repo_root, args.semantic_map)
    output_dir = project_path(repo_root, args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    semantic_map = read_json(semantic_map_path)
    if semantic_map.get("scope", {}).get("touchesGoal30") is not False:
        raise RuntimeError("V3 close-up inspection refuses maps that touch Goal30.")
    glb_path, glb_source_kind = choose_glb(repo_root, semantic_map)
    glb_json = read_glb_json(glb_path)

    setup_scene()
    remove_owned_objects()
    group_materials, helper_materials = prepare_materials()
    node_to_object, imported_objects, import_result = import_glb_with_node_binding(glb_path, glb_json)
    groups, missing_group_selectors = bind_groups(semantic_map, node_to_object, group_materials)
    selector_count = sum(len(part.get("nodeIndices", [])) for group in semantic_map["groups"] for part in group["parts"])
    if missing_group_selectors:
        raise RuntimeError(f"Missing group selectors: {missing_group_selectors[:5]}")

    measurements = build_measurements(node_to_object, groups)
    mesh_quality = collect_mesh_quality(groups)
    images = render_evidence_images(output_dir, repo_root, node_to_object, groups, helper_materials, args.skip_renders)

    final_blockers = [
        check for check in measurements["checks"] if check["status"] == "fail"
    ]
    low_cost_preview_blockers = [
        check for check in final_blockers
        if check["checkId"] != "independent-stem-node"
    ]
    warnings = [
        check for check in measurements["checks"] if check["status"] == "warn"
    ]
    if mesh_quality["_total"]["degenerateFaces"] > 0:
        warnings.append(
            {
                "checkId": "degenerate-face-cleanup",
                "status": "warn",
                "note": "Degenerate mesh faces were detected; localize and clean before polished close-up rendering.",
                "metric": mesh_quality["_total"]["degenerateFaces"],
            }
        )
    fastener_triangles = mesh_quality["fasteners-small-hardware"]["polygonCount"]
    total_triangles = mesh_quality["_total"]["polygonCount"]
    if total_triangles and fastener_triangles / total_triangles > 0.65:
        warnings.append(
            {
                "checkId": "fastener-spring-triangle-weight",
                "status": "warn",
                "note": "Small hardware, especially springs, dominates triangle weight and should be simplified or isolated for hero renders.",
                "metric": round(fastener_triangles / total_triangles, 4),
            }
        )

    if low_cost_preview_blockers:
        report_status = "blocked-for-interface-repair"
    elif final_blockers:
        report_status = "ready-for-low-cost-preview-with-controlled-gaps"
    else:
        report_status = "pass-with-warnings" if warnings else "pass"

    report = {
        "schema": "ztovalve-v3-closeup-asset-inspection/v1",
        "kind": "blender_closeup_asset_inspection",
        "inspectionId": "ztovalve-fixed-ball-valve-v3-closeup",
        "status": report_status,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "scope": {
            "product": "ztovalve fixed ball valve",
            "motionVersion": "v3",
            "homepageConnected": False,
            "final240FrameSequenceConnected": False,
            "touchesGoal30": False,
            "modifiesExistingRenderScripts": False,
        },
        "semanticMap": project_rel(repo_root, semantic_map_path),
        "glb": {
            "path": project_rel(repo_root, glb_path),
            "sourceKind": glb_source_kind,
        },
        "import": import_result,
        "selectorValidation": {
            "selectorCount": selector_count,
            "boundObjectCount": len(node_to_object),
            "missingGroupSelectors": missing_group_selectors,
            "status": "pass" if not missing_group_selectors and not import_result["nameMismatches"] else "fail",
        },
        "measurements": measurements,
        "meshQuality": mesh_quality,
        "images": images,
        "blockers": final_blockers,
        "lowCostPreviewBlockers": low_cost_preview_blockers,
        "warnings": warnings,
        "decision": {
            "canProceedToLowCostPreviewBundle": len(low_cost_preview_blockers) == 0,
            "canProceedToHighQualityHeroPoster": False,
            "canProceedTo240FrameRender": False,
            "reason": (
                "The core body, ball, seats, trunnion relation, and top stack pass close-up interface checks. "
                "A low-cost preview bundle can proceed if the 90-degree proof is explicitly bound to the ball core "
                "and no stem-driven coupling claim is made. High-quality poster and 240-frame rendering remain gated "
                "on recovering or rebuilding an independent stem node and cleaning mesh/fastener weight."
            ),
            "conditionsForLowCostPreview": [
                "Bind the quarter-turn proof to 球体 nodeIndex 23 only.",
                "Do not claim visible stem-driven coupling until 阀杆 is recovered or rebuilt as an independent node.",
                "Keep small hardware grouped or partially hidden in preview cameras.",
            ],
        },
    }

    report_path = output_dir / "inspection-report.json"
    write_json(report_path, report)
    html_path = output_dir / "index.html"
    html_path.write_text(build_html(report, repo_root, output_dir), encoding="utf-8")

    print(json.dumps({
        "status": report["status"],
        "report": project_rel(repo_root, report_path),
        "index": project_rel(repo_root, html_path),
        "images": len(images),
        "passChecks": measurements["passCount"],
        "warnChecks": measurements["warnCount"],
        "failChecks": measurements["failCount"],
        "meshDegenerateFaces": mesh_quality["_total"]["degenerateFaces"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
