#!/usr/bin/env python3
"""Render an isolated low-cost V3 preview bundle for the ztovalve hero.

The bundle is deliberately separate from the homepage AVIF sequence. It uses
the V3 semantic node map and scratch GLB fallback, creates a lightweight
Blender preview scene, renders a short assembly/function/poster sequence, and
writes review artifacts under docs/assets/ztovalve/hero/v3-low-cost-preview-bundle.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import json
import math
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import bpy
    from mathutils import Matrix, Vector
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Run this script with Blender's Python interpreter.") from exc


DEFAULT_MAP = "docs/assets/ztovalve/hero/v3-semantic-node-map.json"
DEFAULT_OUT_DIR = "docs/assets/ztovalve/hero/v3-low-cost-preview-bundle"
INSPECTION_SCRIPT = "scripts/inspect_v3_blender_closeup_asset.py"
OWNED_PREFIX = "v3_lowcost_"


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    args = argv[argv.index("--") + 1 :] if "--" in argv else argv[1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--semantic-map", default=DEFAULT_MAP)
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--frame-count", type=int, default=48)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--samples", type=int, default=48)
    parser.add_argument("--skip-video", action="store_true")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    return parser.parse_args(args)


def project_path(repo_root: Path, value: str) -> Path:
    path = (repo_root / value).resolve()
    path.relative_to(repo_root)
    return path


def project_rel(repo_root: Path, path: Path) -> str:
    return str(path.resolve().relative_to(repo_root)).replace("\\", "/")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8", newline="\n")


def clear_previous_outputs(out_dir: Path) -> None:
    frames_dir = out_dir / "frames"
    if frames_dir.is_dir():
        for frame in frames_dir.glob("frame*.png"):
            frame.unlink()
    for stale in (
        out_dir / "v3-low-cost-preview.mp4",
        out_dir / "v3-low-cost-preview-alpha.webm",
    ):
        if stale.is_file():
            stale.unlink()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_inspection_module(repo_root: Path):
    script_path = project_path(repo_root, INSPECTION_SCRIPT)
    spec = importlib.util.spec_from_file_location("v3_closeup_inspection_runtime", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load inspection helper script: {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def remove_scene_objects() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)
    for material in list(bpy.data.materials):
        if material.name.startswith(OWNED_PREFIX):
            bpy.data.materials.remove(material)
    for curve in list(bpy.data.curves):
        if curve.name.startswith(OWNED_PREFIX):
            bpy.data.curves.remove(curve)
    for camera in list(bpy.data.cameras):
        if camera.name.startswith(OWNED_PREFIX):
            bpy.data.cameras.remove(camera)
    for light in list(bpy.data.lights):
        if light.name.startswith(OWNED_PREFIX):
            bpy.data.lights.remove(light)


def set_input(node: Any, names: list[str], value: Any) -> None:
    for name in names:
        if name in node.inputs:
            node.inputs[name].default_value = value
            return


def safe_set(obj: Any, attr: str, value: Any) -> None:
    if hasattr(obj, attr):
        try:
            setattr(obj, attr, value)
        except Exception:
            pass


def make_material(
    name: str,
    color: tuple[float, float, float, float],
    metallic: float = 0.0,
    roughness: float = 0.55,
) -> Any:
    material = bpy.data.materials.new(f"{OWNED_PREFIX}{name}")
    material.use_nodes = True
    material.diffuse_color = color
    safe_set(material, "blend_method", "BLEND")
    safe_set(material, "surface_render_method", "BLENDED")
    safe_set(material, "show_transparent_back", True)
    safe_set(material, "use_screen_refraction", False)
    nodes = material.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        set_input(bsdf, ["Base Color"], color)
        set_input(bsdf, ["Metallic"], metallic)
        set_input(bsdf, ["Roughness"], roughness)
        set_input(bsdf, ["Alpha"], color[3])
    return material


def make_emission_material(
    name: str,
    color: tuple[float, float, float, float],
    strength: float,
) -> Any:
    material = bpy.data.materials.new(f"{OWNED_PREFIX}{name}")
    material.use_nodes = True
    material.diffuse_color = color
    nodes = material.node_tree.nodes
    nodes.clear()
    output = nodes.new(type="ShaderNodeOutputMaterial")
    emission = nodes.new(type="ShaderNodeEmission")
    emission.inputs["Color"].default_value = color
    emission.inputs["Strength"].default_value = strength
    material.node_tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return material


def set_material_alpha(material: Any, alpha: float) -> None:
    rgba = tuple(material.diffuse_color)
    material.diffuse_color = (rgba[0], rgba[1], rgba[2], alpha)
    if material.use_nodes:
        bsdf = material.node_tree.nodes.get("Principled BSDF")
        if bsdf and "Alpha" in bsdf.inputs:
            bsdf.inputs["Alpha"].default_value = alpha


def prepare_materials() -> dict[str, Any]:
    return {
        "body": make_material("cast_satin_stainless_body", (0.54, 0.56, 0.54, 1.0), 0.82, 0.34),
        "body_cutaway": make_material("translucent_body_shell", (0.62, 0.65, 0.62, 0.58), 0.70, 0.42),
        "ball": make_material("polished_ball_core", (0.80, 0.82, 0.78, 1.0), 0.94, 0.18),
        "seat": make_material("warm_machined_seat_contact", (0.78, 0.66, 0.45, 1.0), 0.62, 0.38),
        "seal": make_material("graphite_seal", (0.032, 0.034, 0.032, 1.0), 0.0, 0.78),
        "top": make_material("satin_top_stack", (0.50, 0.54, 0.54, 1.0), 0.76, 0.36),
        "fastener": make_material("fastener_dark_satin", (0.22, 0.235, 0.235, 1.0), 0.72, 0.32),
        "flow": make_emission_material("flow_axis_soft_blue", (0.27, 0.66, 0.92, 1.0), 0.55),
        "stem_axis": make_emission_material("stem_axis_cool_gray", (0.56, 0.76, 0.92, 1.0), 0.38),
        "reflection_white": make_emission_material("reflection_softbox_white", (0.92, 0.94, 0.92, 1.0), 1.25),
        "reflection_cool": make_emission_material("reflection_cool_strip", (0.62, 0.72, 0.78, 1.0), 0.92),
        "reflection_dark": make_material("reflection_dark_flag", (0.018, 0.020, 0.020, 1.0), 0.0, 0.92),
    }


def part_material_key(group_id: str, part_name: str) -> str:
    if part_name == "球体":
        return "ball"
    if "阀座" in part_name or "密封圈" in part_name:
        return "seat"
    if "盘根" in part_name or "填料" in part_name:
        return "seal"
    if group_id == "top-bracket-actuator" or group_id == "stem-packing-drive":
        return "top"
    if group_id == "fasteners-small-hardware":
        return "fastener"
    return "body"


def assign_preview_materials(groups: dict[str, list[Any]], materials: dict[str, Any]) -> None:
    for group_id, objects in groups.items():
        for obj in objects:
            part_name = str(obj.get("v3_part_name", ""))
            key = part_material_key(group_id, part_name)
            obj.data.materials.clear()
            obj.data.materials.append(materials[key])
            obj["v3_low_cost_material_key"] = key


def configure_render(width: int, height: int, samples: int) -> dict[str, Any]:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    try:
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "Medium High Contrast"
    except TypeError:
        pass
    scene.view_settings.exposure = -0.18
    scene.view_settings.gamma = 1.0
    eevee = getattr(scene, "eevee", None)
    if eevee:
        for attr, value in (
            ("taa_render_samples", samples),
            ("use_gtao", True),
            ("gtao_distance", 3),
            ("gtao_factor", 1.35),
            ("use_soft_shadows", True),
            ("use_bloom", False),
        ):
            if hasattr(eevee, attr):
                try:
                    setattr(eevee, attr, value)
                except Exception:
                    pass
    world = scene.world or bpy.data.worlds.new(f"{OWNED_PREFIX}world")
    scene.world = world
    world.color = (0.82, 0.84, 0.84)
    if hasattr(world, "use_nodes"):
        world.use_nodes = True
        background = world.node_tree.nodes.get("Background") if world.node_tree else None
        if background:
            background.inputs["Color"].default_value = (0.82, 0.84, 0.84, 1.0)
            background.inputs["Strength"].default_value = 0.32
    return {
        "engine": scene.render.engine,
        "width": width,
        "height": height,
        "samples": samples,
        "filmTransparent": True,
        "transparentBackground": True,
        "profile": "low-cost-eevee-transparent-product",
    }


def look_at(camera: Any, target: Vector) -> None:
    direction = target - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def add_area_light(name: str, location: tuple[float, float, float], target: Vector, energy: float, size: float) -> dict[str, Any]:
    light_data = bpy.data.lights.new(f"{OWNED_PREFIX}{name}_data", "AREA")
    light = bpy.data.objects.new(f"{OWNED_PREFIX}{name}", light_data)
    bpy.context.scene.collection.objects.link(light)
    light.location = location
    light_data.energy = energy
    light_data.size = size
    direction = target - light.location
    light.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    return {
        "name": light.name,
        "location": [round(value, 5) for value in light.location],
        "energy": energy,
        "size": size,
    }


def make_reflection_panel(
    name: str,
    location: tuple[float, float, float],
    target: Vector,
    size: tuple[float, float],
    material: Any,
) -> dict[str, Any]:
    bpy.ops.mesh.primitive_plane_add(size=1, location=location)
    panel = bpy.context.object
    panel.name = f"{OWNED_PREFIX}{name}"
    panel.scale = (size[0], size[1], 1.0)
    panel.data.materials.append(material)
    direction = target - panel.location
    panel.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    safe_set(panel, "visible_camera", False)
    safe_set(panel, "visible_shadow", False)
    safe_set(panel, "visible_diffuse", False)
    safe_set(panel, "visible_glossy", True)
    return {
        "name": panel.name,
        "location": [round(value, 5) for value in panel.location],
        "size": [round(size[0], 5), round(size[1], 5)],
        "cameraVisible": False,
        "glossyVisible": True,
    }


def add_reflection_rig(product_center: Vector, product_extent: Vector, materials: dict[str, Any]) -> list[dict[str, Any]]:
    span = max(product_extent.x, product_extent.y, product_extent.z)
    return [
        make_reflection_panel(
            "reflection_top_softbox",
            (product_center.x - span * 0.25, product_center.y - span * 1.28, product_center.z + span * 1.45),
            product_center,
            (span * 1.75, span * 0.42),
            materials["reflection_white"],
        ),
        make_reflection_panel(
            "reflection_left_vertical_softbox",
            (product_center.x - span * 1.55, product_center.y - span * 0.78, product_center.z + span * 0.22),
            product_center,
            (span * 0.46, span * 1.35),
            materials["reflection_white"],
        ),
        make_reflection_panel(
            "reflection_right_cool_strip",
            (product_center.x + span * 1.45, product_center.y - span * 0.58, product_center.z + span * 0.18),
            product_center,
            (span * 0.28, span * 1.15),
            materials["reflection_cool"],
        ),
        make_reflection_panel(
            "reflection_lower_softbox",
            (product_center.x, product_center.y - span * 0.96, product_center.z - span * 0.70),
            product_center,
            (span * 1.20, span * 0.34),
            materials["reflection_white"],
        ),
        make_reflection_panel(
            "reflection_dark_definition_flag",
            (product_center.x + span * 0.80, product_center.y - span * 0.28, product_center.z + span * 0.62),
            product_center,
            (span * 0.36, span * 0.86),
            materials["reflection_dark"],
        ),
    ]


def create_line(name: str, start: Vector, end: Vector, material: Any, bevel_depth: float = 0.003) -> Any:
    curve = bpy.data.curves.new(f"{OWNED_PREFIX}{name}_curve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = bevel_depth
    curve.bevel_resolution = 4
    spline = curve.splines.new("POLY")
    spline.points.add(1)
    spline.points[0].co = (start.x, start.y, start.z, 1.0)
    spline.points[1].co = (end.x, end.y, end.z, 1.0)
    obj = bpy.data.objects.new(f"{OWNED_PREFIX}{name}", curve)
    obj.data.materials.append(material)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def add_stage_helpers(
    ball_center: Vector,
    ball_extent: Vector,
    pipe_axis: Vector,
    stem_axis: Vector,
    materials: dict[str, Any],
) -> dict[str, Any]:
    pipe_half = max(ball_extent.length * 0.92, 0.18)
    core_half = max(ball_extent.x, ball_extent.y, ball_extent.z) * 0.36
    stem_half = max(ball_extent.length * 0.85, 0.16)
    helpers = {
        "flowLeft": create_line(
            "flow_left",
            ball_center - pipe_axis * pipe_half,
            ball_center - pipe_axis * core_half,
            materials["flow"],
            0.0032,
        ),
        "flowCenter": create_line(
            "flow_center",
            ball_center - pipe_axis * core_half,
            ball_center + pipe_axis * core_half,
            materials["flow"],
            0.0032,
        ),
        "flowRight": create_line(
            "flow_right",
            ball_center + pipe_axis * core_half,
            ball_center + pipe_axis * pipe_half,
            materials["flow"],
            0.0032,
        ),
        "stemAxis": create_line(
            "stem_axis",
            ball_center - stem_axis * stem_half,
            ball_center + stem_axis * stem_half,
            materials["stem_axis"],
            0.0022,
        ),
    }
    return helpers


def improve_mesh_shading(groups: dict[str, list[Any]]) -> None:
    for group_id, objects in groups.items():
        for obj in objects:
            if obj.type != "MESH":
                continue
            if group_id != "fasteners-small-hardware":
                for polygon in obj.data.polygons:
                    polygon.use_smooth = True
            if group_id in {"body-pressure-shell", "ball-trunnion-core", "seat-seal-system", "top-bracket-actuator"}:
                modifier = obj.modifiers.new(f"{OWNED_PREFIX}weighted_normals", "WEIGHTED_NORMAL")
                modifier.keep_sharp = True
                modifier.weight = 50


def smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def sign(value: float) -> float:
    return -1.0 if value < 0 else 1.0


def state_for(progress: float) -> dict[str, float]:
    assembly = smoothstep(progress / 0.56)
    separation = 1.0 - assembly
    ball_turn = smoothstep((progress - 0.60) / 0.18)
    seat_press = smoothstep((progress - 0.70) / 0.10)
    reveal_in = smoothstep((progress - 0.43) / 0.10)
    reveal_out = 1.0 - smoothstep((progress - 0.84) / 0.12)
    function_reveal = max(0.0, min(1.0, reveal_in * reveal_out))
    poster_hold = smoothstep((progress - 0.82) / 0.14)
    return {
        "assembly": assembly,
        "separation": separation,
        "ballTurn": ball_turn,
        "ballAngleDegrees": ball_turn * 90.0,
        "seatPress": seat_press,
        "functionReveal": function_reveal,
        "posterHold": poster_hold,
        "bodyAlpha": 1.0 - (0.52 * function_reveal * (1.0 - poster_hold)),
    }


def stage_for(progress: float) -> dict[str, str]:
    if progress < 0.42:
        return {
            "stage": "precision-suspended",
            "title": "Precision Suspended",
            "intent": "Controlled exploded posture with parts held on real axes.",
        }
    if progress < 0.60:
        return {
            "stage": "assembly-lock-in",
            "title": "Assembly Lock-In",
            "intent": "Ball, seats, flanges, fasteners, and top stack return to contact.",
        }
    if progress < 0.84:
        return {
            "stage": "quarter-turn-proof",
            "title": "Quarter-Turn Proof",
            "intent": "Ball bore rotates from aligned to blocked while seats read as contact surfaces.",
        }
    return {
        "stage": "commercial-poster-hold",
        "title": "Commercial Poster Hold",
        "intent": "Complete product returns to a homepage-style hold.",
    }


def make_records(
    inspection: Any,
    node_to_object: dict[int, Any],
    groups: dict[str, list[Any]],
    ball_center: Vector,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for group_id, objects in groups.items():
        for obj in objects:
            bounds = inspection.world_bounds([obj])
            center = inspection.center_from_bounds(bounds)
            records.append(
                {
                    "object": obj,
                    "nodeIndex": int(obj.get("v3_node_index")),
                    "group": group_id,
                    "partName": str(obj.get("v3_part_name", "")),
                    "baseMatrix": obj.matrix_world.copy(),
                    "baseLocation": obj.location.copy(),
                    "baseCenter": center,
                    "localCenter": center - ball_center,
                    "materialKey": str(obj.get("v3_low_cost_material_key", "")),
                }
            )
    records.sort(key=lambda item: item["nodeIndex"])
    return records


def object_offset(record: dict[str, Any], state: dict[str, float], axes: dict[str, Vector]) -> Vector:
    local = record["localCenter"]
    group = record["group"]
    part_name = record["partName"]
    sep = state["separation"]
    offset = Vector((0.0, 0.0, 0.0))
    pipe = axes["pipe"]
    stem = axes["stem"]
    depth = axes["depth"]
    pipe_sign = sign(local.dot(pipe))

    if group == "body-pressure-shell":
        if part_name == "阀体":
            offset += depth * -0.018 * sep
            offset += pipe * 0.018 * pipe_sign * sep
        elif "阀盖" in part_name:
            offset += pipe * 0.095 * pipe_sign * sep
            offset += depth * -0.018 * sep
        else:
            offset += stem * -0.060 * sep
    elif group == "seat-seal-system":
        offset += pipe * 0.070 * pipe_sign * sep
        offset += pipe * -0.0045 * pipe_sign * state["seatPress"]
    elif group == "ball-trunnion-core":
        if part_name == "球体":
            offset += depth * -0.105 * sep
        elif "固定轴" in part_name or local.dot(stem) < -0.055:
            offset += stem * -0.070 * sep
        else:
            offset += stem * 0.030 * sep
    elif group == "stem-packing-drive":
        offset += stem * 0.085 * sep
        offset += depth * -0.020 * sep
    elif group == "top-bracket-actuator":
        offset += stem * 0.105 * sep
    elif group == "fasteners-small-hardware":
        radial = Vector((local.x, local.y, 0.0))
        if radial.length < 0.001:
            radial = pipe * pipe_sign
        else:
            radial.normalize()
        offset += radial * 0.095 * sep
        offset += stem * sign(local.dot(stem)) * 0.035 * sep
    return offset


def apply_state(
    records: list[dict[str, Any]],
    state: dict[str, float],
    axes: dict[str, Vector],
    ball_center: Vector,
    materials: dict[str, Any],
    helpers: dict[str, Any],
) -> dict[str, Any]:
    moved_counts: dict[str, int] = {}
    max_offset = 0.0
    set_material_alpha(materials["body"], state["bodyAlpha"])
    set_material_alpha(materials["body_cutaway"], state["bodyAlpha"])

    for record in records:
        obj = record["object"]
        offset = object_offset(record, state, axes)
        max_offset = max(max_offset, offset.length)
        if offset.length > 0.0001:
            moved_counts[record["group"]] = moved_counts.get(record["group"], 0) + 1
        matrix = Matrix.Translation(offset) @ record["baseMatrix"]
        if record["partName"] == "球体":
            rotation = Matrix.Rotation(math.radians(state["ballAngleDegrees"]), 4, axes["stem"])
            matrix = Matrix.Translation(offset) @ Matrix.Translation(ball_center) @ rotation @ Matrix.Translation(-ball_center) @ record["baseMatrix"]
        obj.matrix_world = matrix
        obj.hide_render = False
        obj.hide_viewport = False

    center_visible = state["ballTurn"] < 0.52
    for name, helper in helpers.items():
        helper.hide_render = False
        helper.hide_viewport = False
        if name == "flowCenter" and not center_visible:
            helper.hide_render = True
            helper.hide_viewport = True
        if name in {"flowLeft", "flowRight", "flowCenter", "stemAxis"} and state["posterHold"] > 0.75:
            helper.hide_render = True
            helper.hide_viewport = True

    bpy.context.view_layer.update()
    return {
        "movedCounts": moved_counts,
        "maxOffsetMeters": round(max_offset, 6),
        "ballAngleDegrees": round(state["ballAngleDegrees"], 4),
        "bodyAlpha": round(state["bodyAlpha"], 4),
        "flowCenterVisible": bool(center_visible and state["posterHold"] <= 0.75),
        "seatPress": round(state["seatPress"], 4),
    }


def camera_for(
    camera: Any,
    progress: float,
    product_center: Vector,
    ball_center: Vector,
    product_extent: Vector,
) -> dict[str, Any]:
    function_focus = smoothstep((progress - 0.42) / 0.26) * (1.0 - smoothstep((progress - 0.84) / 0.12))
    poster_hold = smoothstep((progress - 0.82) / 0.14)
    wide_vector = Vector((0.48, -0.72, 0.34))
    close_vector = Vector((0.38, -0.56, 0.30))
    final_vector = Vector((0.50, -0.70, 0.34))
    vector = wide_vector.lerp(close_vector, function_focus).lerp(final_vector, poster_hold)
    distance = max(product_extent.x, product_extent.y, product_extent.z) * 2.65
    target = product_center.lerp(ball_center, min(function_focus * 0.72, 0.72))
    target.z += product_extent.z * (0.12 + 0.02 * function_focus - 0.07 * poster_hold)
    camera.location = target + vector.normalized() * distance
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = max(product_extent.x, product_extent.y, product_extent.z) * (
        2.02 - 0.25 * function_focus + 0.10 * poster_hold
    )
    look_at(camera, target)
    return {
        "position": [round(value, 6) for value in camera.location],
        "target": [round(value, 6) for value in target],
        "orthoScale": round(camera.data.ortho_scale, 6),
    }


def render_frames(
    repo_root: Path,
    out_dir: Path,
    records: list[dict[str, Any]],
    materials: dict[str, Any],
    helpers: dict[str, Any],
    axes: dict[str, Vector],
    ball_center: Vector,
    product_center: Vector,
    product_extent: Vector,
    frame_count: int,
) -> list[dict[str, Any]]:
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    camera_data = bpy.data.cameras.new(f"{OWNED_PREFIX}camera_data")
    camera = bpy.data.objects.new(f"{OWNED_PREFIX}camera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    bpy.context.scene.camera = camera

    frames: list[dict[str, Any]] = []
    started = time.perf_counter()
    for index in range(frame_count):
        progress = index / max(1, frame_count - 1)
        state = state_for(progress)
        motion = apply_state(records, state, axes, ball_center, materials, helpers)
        camera_record = camera_for(camera, progress, product_center, ball_center, product_extent)
        output_path = frames_dir / f"frame{index:04d}.png"
        bpy.context.scene.render.filepath = str(output_path)
        bpy.ops.render.render(write_still=True)
        stage = stage_for(progress)
        frame_record = {
            "previewFrame": index,
            "canonicalFrameApprox": int(round(1 + progress * 239)),
            "progress": round(progress, 6),
            **stage,
            "path": project_rel(repo_root, output_path),
            "bytes": output_path.stat().st_size,
            "sha256": sha256(output_path),
            "motion": motion,
            "camera": camera_record,
        }
        frames.append(frame_record)
        if (index + 1) % 8 == 0 or index + 1 == frame_count:
            print(f"V3 low-cost preview rendered {index + 1}/{frame_count} frames in {time.perf_counter() - started:.1f}s")
    return frames


def sample_frames(frames: list[dict[str, Any]]) -> list[dict[str, Any]]:
    desired = [0, 8, 16, 23, 30, 36, 42, len(frames) - 1]
    seen: set[int] = set()
    result: list[dict[str, Any]] = []
    for index in desired:
        bounded = max(0, min(len(frames) - 1, index))
        if bounded in seen:
            continue
        seen.add(bounded)
        result.append(frames[bounded])
    return result


def encode_video(repo_root: Path, out_dir: Path, ffmpeg: str, frame_count: int) -> dict[str, Any] | None:
    if shutil.which(ffmpeg) is None and not Path(ffmpeg).is_file():
        return None
    output_path = out_dir / "v3-low-cost-preview-alpha.webm"
    command = [
        ffmpeg,
        "-y",
        "-loglevel",
        "error",
        "-framerate",
        "12",
        "-i",
        str(out_dir / "frames" / "frame%04d.png"),
        "-c:v",
        "libvpx-vp9",
        "-pix_fmt",
        "yuva420p",
        "-auto-alt-ref",
        "0",
        "-b:v",
        "0",
        "-crf",
        "28",
        str(output_path),
    ]
    subprocess.run(command, check=True)
    return {
        "path": project_rel(repo_root, output_path),
        "bytes": output_path.stat().st_size,
        "sha256": sha256(output_path),
        "frameCount": frame_count,
        "fps": 12,
        "durationSeconds": round(frame_count / 12, 4),
        "codec": "vp9",
        "alpha": True,
    }


def html_src(path: str, out_dir_rel: str) -> str:
    prefix = f"{out_dir_rel}/"
    return html.escape(path.removeprefix(prefix))


def build_index(manifest: dict[str, Any]) -> str:
    out_dir_rel = manifest["outputs"]["bundleDir"]
    video = manifest["outputs"].get("video")
    video_markup = ""
    if video:
        video_markup = f"""
    <section class="video-band">
      <video src="{html_src(video['path'], out_dir_rel)}" controls muted playsinline loop poster="{html_src(manifest['stageSamples'][-1]['path'], out_dir_rel)}"></video>
    </section>
"""
    cards = []
    for frame in manifest["stageSamples"]:
        cards.append(
            f"""
      <figure>
        <img src="{html_src(frame['path'], out_dir_rel)}" alt="{html.escape(frame['title'])}">
        <figcaption>
          <b>{html.escape(frame['title'])}</b>
          <span>preview {frame['previewFrame']:04d} / approx frame {frame['canonicalFrameApprox']:04d} | ball {frame['motion']['ballAngleDegrees']} deg | body alpha {frame['motion']['bodyAlpha']}</span>
          <em>{html.escape(frame['intent'])}</em>
        </figcaption>
      </figure>
"""
        )
    blockers = "".join(
        f"<li>{html.escape(item['gapId'])}: {html.escape(item['impact'])}</li>"
        for item in manifest["controlledGaps"]
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ztovalve V3 Low-Cost Preview Bundle</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: Inter, "Noto Sans SC", system-ui, sans-serif;
      background: #eef0f1;
      color: #172027;
    }}
    body {{ margin: 0; }}
    main {{ width: min(1440px, calc(100% - 40px)); margin: 0 auto; padding: 32px 0 56px; }}
    header {{ display: grid; gap: 10px; margin-bottom: 22px; }}
    .eyebrow {{ margin: 0; color: #64717b; font-size: 13px; text-transform: uppercase; }}
    h1 {{ margin: 0; font-size: clamp(30px, 5vw, 58px); line-height: 1.02; letter-spacing: 0; }}
    p {{ margin: 0; color: #52616b; line-height: 1.55; }}
    .metrics {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin: 20px 0 26px; }}
    .metric {{ border: 1px solid #d2d7dc; border-radius: 8px; background: #fff; padding: 14px 16px; }}
    .metric b {{ display: block; font-size: 22px; color: #172027; }}
    .metric span {{ color: #64717b; font-size: 13px; }}
    .video-band {{ margin: 0 0 18px; }}
    video {{ display: block; width: 100%; border: 1px solid #c8d0d6; border-radius: 8px; background: transparent; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }}
    figure {{ margin: 0; border: 1px solid #cfd6dc; border-radius: 8px; overflow: hidden; background: #fff; }}
    figure:first-child, figure:last-child {{ grid-column: 1 / -1; }}
    img {{ display: block; width: 100%; height: auto; background: transparent; }}
    figcaption {{ display: grid; gap: 5px; padding: 12px 14px 14px; }}
    figcaption span, figcaption em {{ color: #64717b; font-size: 13px; line-height: 1.45; font-style: normal; }}
    .notes {{ margin-top: 18px; border: 1px solid #d2d7dc; border-radius: 8px; background: #fff; padding: 16px 18px; }}
    .notes h2 {{ margin: 0 0 8px; font-size: 18px; }}
    .notes ul {{ margin: 0; padding-left: 20px; color: #52616b; line-height: 1.55; }}
    code {{ background: #e7ebee; border-radius: 5px; padding: 2px 5px; }}
    @media (max-width: 820px) {{
      main {{ width: min(100% - 24px, 720px); padding-top: 24px; }}
      .metrics, .grid {{ grid-template-columns: 1fr; }}
      figure:first-child, figure:last-child {{ grid-column: auto; }}
    }}
  </style>
</head>
<body>
<main>
  <header>
    <p class="eyebrow">ztovalve fixed ball valve | staged score v3</p>
    <h1>V3 low-cost preview bundle</h1>
    <p>独立预览包：透明背景、爆炸悬停、轴线合体、球芯 90° 功能证明、商业 poster 收束。未接首页，未替换 240 帧。</p>
  </header>
  <section class="metrics">
    <div class="metric"><b>{manifest['renderProfile']['frameCount']}</b><span>preview frames</span></div>
    <div class="metric"><b>{manifest['assetInspection']['meshNodeCount']}</b><span>bound mesh nodes</span></div>
    <div class="metric"><b>{manifest['motionEvidence']['maxBallAngleDegrees']}</b><span>max ball turn degrees</span></div>
    <div class="metric"><b>{manifest['status']}</b><span>bundle status</span></div>
  </section>
  {video_markup}
  <section class="grid">
    {''.join(cards)}
  </section>
  <section class="notes">
    <h2>Controlled gaps</h2>
    <ul>{blockers}</ul>
  </section>
</main>
</body>
</html>
"""


def main() -> int:
    args = parse_args()
    if args.frame_count < 8:
        raise RuntimeError("--frame-count must be at least 8.")

    repo_root = Path(args.repo_root).resolve()
    out_dir = project_path(repo_root, args.out_dir)
    semantic_map_path = project_path(repo_root, args.semantic_map)
    out_dir.mkdir(parents=True, exist_ok=True)
    clear_previous_outputs(out_dir)
    (out_dir / "frames").mkdir(parents=True, exist_ok=True)

    inspection = load_inspection_module(repo_root)
    semantic_map = read_json(semantic_map_path)
    if semantic_map.get("schema") != "ztovalve-v3-semantic-node-map/v1":
        raise RuntimeError("Unexpected V3 semantic map schema.")
    if semantic_map.get("scope", {}).get("homepageConnected") is not False:
        raise RuntimeError("V3 low-cost bundle must remain homepage-isolated.")

    glb_path, glb_source_kind = inspection.choose_glb(repo_root, semantic_map)
    glb_json = inspection.read_glb_json(glb_path)

    remove_scene_objects()
    render_profile = configure_render(args.width, args.height, args.samples)
    materials = prepare_materials()
    node_to_object, imported_objects, import_result = inspection.import_glb_with_node_binding(glb_path, glb_json)
    groups, missing_group_selectors = inspection.bind_groups(semantic_map, node_to_object, {group["groupId"]: materials["body"] for group in semantic_map["groups"]})
    if missing_group_selectors:
        raise RuntimeError(f"Missing V3 group selectors: {missing_group_selectors[:5]}")
    assign_preview_materials(groups, materials)
    improve_mesh_shading(groups)

    measurements = inspection.build_measurements(node_to_object, groups)
    if measurements["failCount"] > 1:
        raise RuntimeError("Unexpected V3 contact failures beyond the known independent stem gap.")

    all_mesh_objects = [obj for obj in node_to_object.values()]
    product_bounds = inspection.world_bounds(all_mesh_objects)
    product_center = inspection.center_from_bounds(product_bounds)
    product_extent = Vector(product_bounds["extent"])
    ball_bounds = inspection.part_bounds(node_to_object, [23])
    ball_center = inspection.center_from_bounds(ball_bounds)
    ball_extent = Vector(ball_bounds["extent"])
    axes_record = measurements["axisInference"]
    pipe_axis = inspection.axis_unit(axes_record["pipeAxisIndex"])
    stem_axis = inspection.axis_unit(axes_record["stemAxisIndex"])
    depth_axis = Vector((0.0, -1.0, 0.0))
    axes = {"pipe": pipe_axis, "stem": stem_axis, "depth": depth_axis}

    lighting = [
        add_area_light("key_large_left", (-0.82, -1.04, 1.14), product_center, 620, 3.0),
        add_area_light("rim_right", (0.88, -0.18, 0.92), product_center, 260, 1.8),
        add_area_light("front_soft_fill", (0.0, -1.48, 0.42), product_center, 115, 3.4),
        add_area_light("low_edge_lift", (-0.28, -0.88, -0.36), product_center, 65, 1.5),
    ]
    reflection_panels: list[dict[str, Any]] = []
    helpers = add_stage_helpers(ball_center, ball_extent, pipe_axis, stem_axis, materials)
    records = make_records(inspection, node_to_object, groups, ball_center)

    frames = render_frames(
        repo_root,
        out_dir,
        records,
        materials,
        helpers,
        axes,
        ball_center,
        product_center,
        product_extent,
        args.frame_count,
    )
    video = None if args.skip_video else encode_video(repo_root, out_dir, args.ffmpeg, args.frame_count)
    stages = sample_frames(frames)

    max_ball = max(frame["motion"]["ballAngleDegrees"] for frame in frames)
    manifest = {
        "schema": "ztovalve-v3-low-cost-preview-bundle/v1",
        "kind": "independent_blender_preview_bundle",
        "bundleId": "ztovalve-fixed-ball-valve-v3-low-cost-preview",
        "status": "pass-with-controlled-gaps",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "scope": {
            "product": "ztovalve fixed ball valve",
            "motionVersion": "v3",
            "homepageConnected": False,
            "final240FrameSequenceConnected": False,
            "touchesGoal30": False,
            "modifiesExistingRenderScripts": False,
            "replacesExistingHeroAvif": False,
        },
        "sourceBoundary": {
            "semanticMap": project_rel(repo_root, semantic_map_path),
            "semanticMapSha256": sha256(semantic_map_path),
            "glb": project_rel(repo_root, glb_path),
            "glbSourceKind": glb_source_kind,
            "glbSha256": sha256(glb_path),
            "inspectionHelper": INSPECTION_SCRIPT,
            "inspectionReport": "docs/assets/ztovalve/hero/v3-closeup-asset-inspection/inspection-report.json",
        },
        "renderProfile": {
            **render_profile,
            "frameCount": len(frames),
            "canonicalFrameApproximation": "preview frames map linearly onto Frame 0001..0240; this is not the final 240-frame release sequence.",
        },
        "stageScoreV3Binding": {
            "frame0001": "controlled exploded suspension on real axes",
            "frame0120": "assembly lock-in and ball-core quarter-turn proof",
            "frame0240": "complete product commercial poster hold",
            "quarterTurnPolicy": "Bound to 球体 nodeIndex 23 only; no visible stem-driven coupling claim.",
            "backgroundPolicy": "Transparent alpha output with no background geometry and no wordmark/text baked into frames.",
            "materialLightingPolicy": "Low-cost Eevee transparent render with metallic materials, weighted normals, and soft product-style area lights.",
        },
        "axisInference": axes_record,
        "assetInspection": {
            "importedObjectCount": import_result["importedObjectCount"],
            "meshNodeCount": import_result["meshNodeCount"],
            "boundMeshNodeCount": import_result["boundMeshNodeCount"],
            "selectorStatus": "pass" if not missing_group_selectors else "fail",
            "contactPassCount": measurements["passCount"],
            "contactWarnCount": measurements["warnCount"],
            "contactFailCount": measurements["failCount"],
        },
        "motionEvidence": {
            "maxBallAngleDegrees": round(max_ball, 4),
            "maxOffsetMeters": max(frame["motion"]["maxOffsetMeters"] for frame in frames),
            "stageSampleCount": len(stages),
            "flowCenterInterruptedWhenClosed": any(not frame["motion"]["flowCenterVisible"] and frame["motion"]["ballAngleDegrees"] > 70 for frame in frames),
            "posterHoldRestoresBodyAlpha": frames[-1]["motion"]["bodyAlpha"],
            "transparentFrameSequence": True,
        },
        "controlledGaps": [
            {
                "gapId": "missing-independent-stem-node",
                "impact": "90-degree proof is bound to the ball core only; do not claim verified stem-driven coupling until an independent 阀杆 node is recovered or rebuilt.",
            },
            {
                "gapId": "not-final-render-quality",
                "impact": "This bundle is a low-cost Blender preview, not high-quality poster approval and not the final 240-frame homepage sequence.",
            },
            {
                "gapId": "fastener-spring-weight",
                "impact": "Small hardware remains grouped for preview; final render should simplify or isolate triangle-heavy springs and fasteners.",
            },
        ],
        "outputs": {
            "bundleDir": project_rel(repo_root, out_dir),
            "framesDir": project_rel(repo_root, out_dir / "frames"),
            "index": project_rel(repo_root, out_dir / "index.html"),
            "manifest": project_rel(repo_root, out_dir / "manifest.json"),
            "video": video,
        },
        "scene": {
            "background": {
                "geometry": None,
                "wordmark": None,
                "filmTransparent": True,
            },
            "lighting": lighting,
            "reflectionPanels": reflection_panels,
            "helpers": sorted(helpers.keys()),
        },
        "stageSamples": stages,
        "frames": frames,
    }
    write_json(out_dir / "manifest.json", manifest)
    write_text(out_dir / "index.html", build_index(manifest))
    print(json.dumps({
        "status": manifest["status"],
        "bundle": manifest["outputs"]["bundleDir"],
        "index": manifest["outputs"]["index"],
        "manifest": manifest["outputs"]["manifest"],
        "frameCount": len(frames),
        "video": video["path"] if video else None,
        "maxBallAngleDegrees": manifest["motionEvidence"]["maxBallAngleDegrees"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
