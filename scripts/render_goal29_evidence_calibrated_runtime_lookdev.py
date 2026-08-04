"""Render Goal29 evidence-calibrated hero-runtime lookdev samples.

Run inside Blender:
D:\TOOLS\render-pipeline\apps\Blender-5.2.0\Blender Foundation\Blender 5.2\blender.exe --background --python scripts\render_goal29_evidence_calibrated_runtime_lookdev.py -- --repo-root . --profile cycles-smoke
"""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
import math
import shutil
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

try:
    import bpy
    from mathutils import Vector
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Run this script with Blender's Python interpreter.") from exc


GOAL20_DIR = "docs/assets/ztovalve/hero/goal20-blender-cycles-step-proof"
GOAL26_DIR = "docs/assets/ztovalve/hero/goal26-blender-camera-explosion-proof"
GOAL29_DIR = "docs/assets/ztovalve/hero/goal29-evidence-calibrated-runtime-lookdev"
AUTHORITY_DIR = "governance/control/hero-runtime"
AUTHORITY_FILES = [
    "authority.json",
    "material.json",
    "lighting.json",
    "camera.json",
    "motion.json",
    "storyboard.json",
    "release-gate.json",
]
SAMPLE_FRAMES = [0, 56, 124, 176, 216]
RUNTIME_CHANNELS = {
    "shellClosure",
    "seatSealClosure",
    "stemDriveClosure",
    "lowerSupportClosure",
    "fastenerReturn",
    "springReturn",
    "ballPresentationTurn",
    "cutawayReveal",
    "clearWaterFlow",
}
SHOT_IDS = [
    "fully-exploded-opening",
    "precision-assembly",
    "ball-core-presentation",
    "cutaway-reveal",
    "clear-water-flow-hold",
]


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    args = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--motion-control", default=f"{GOAL26_DIR}/motion-control.json")
    parser.add_argument("--goal26-manifest", default=f"{GOAL26_DIR}/render-manifest.json")
    parser.add_argument("--runtime-authority", default=AUTHORITY_DIR)
    parser.add_argument("--out-dir", default=GOAL29_DIR)
    parser.add_argument("--profile", choices=["preview", "review", "cycles-smoke"], default="cycles-smoke")
    parser.add_argument("--frame-list", default="0,56,124,176,216")
    return parser.parse_args(args)


def load_module(repo_root: Path, path: str, name: str):
    script_path = repo_root / path
    spec = importlib.util.spec_from_file_location(name, script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def smoothstep(value: float) -> float:
    value = clamp01(value)
    return value * value * (3.0 - 2.0 * value)


def sign(value: float) -> float:
    return -1.0 if value < 0 else 1.0


def selected_frames(frame_list: str) -> list[int]:
    frames = [int(value.strip()) for value in frame_list.split(",") if value.strip()]
    return sorted(set(max(0, min(239, frame)) for frame in frames))


def progress_for_frame(frame_index: int) -> float:
    return frame_index / 239.0


def shot_for_progress(storyboard: dict, progress: float) -> str:
    for shot in storyboard["shot_order"]:
        start, end = shot["progress_range"]
        if start <= progress <= end:
            return shot["shot_id"]
    return storyboard["shot_order"][-1]["shot_id"]


def make_principled_material(name: str, color, *, metallic=0.0, roughness=0.55, alpha=1.0, coat=0.0):
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    material.blend_method = "BLEND" if alpha < 1.0 else "OPAQUE"
    material.use_screen_refraction = False
    nodes = material.node_tree.nodes
    principled = nodes.get("Principled BSDF")
    if principled:
        for input_name, value in {
            "Base Color": color,
            "Metallic": metallic,
            "Roughness": roughness,
            "Alpha": alpha,
            "Coat Weight": coat,
            "Clearcoat": coat,
            "Coat Roughness": roughness,
        }.items():
            if input_name in principled.inputs:
                principled.inputs[input_name].default_value = value
    return material


def make_water_material() -> bpy.types.Material:
    material = bpy.data.materials.new("goal29_clear_water_material")
    material.diffuse_color = (0.48, 0.74, 0.94, 0.54)
    material.use_nodes = True
    material.blend_method = "BLEND"
    nodes = material.node_tree.nodes
    principled = nodes.get("Principled BSDF")
    if principled:
        for input_name, value in {
            "Base Color": (0.48, 0.74, 0.94, 0.54),
            "Alpha": 0.54,
            "Roughness": 0.02,
            "Metallic": 0.0,
            "Transmission Weight": 0.35,
        }.items():
            if input_name in principled.inputs:
                principled.inputs[input_name].default_value = value
    return material


def make_water_highlight_material() -> bpy.types.Material:
    material = bpy.data.materials.new("goal29_clear_water_highlight_material")
    material.use_nodes = True
    material.blend_method = "BLEND"
    nodes = material.node_tree.nodes
    nodes.clear()
    output = nodes.new(type="ShaderNodeOutputMaterial")
    emission = nodes.new(type="ShaderNodeEmission")
    emission.inputs["Color"].default_value = (0.68, 0.92, 1.0, 1.0)
    emission.inputs["Strength"].default_value = 0.16
    material.node_tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    material.diffuse_color = (0.68, 0.92, 1.0, 0.62)
    return material


def configure_goal29_render(h, profile: str) -> dict:
    render_profile = h.configure_render(profile)
    scene = bpy.context.scene
    scene.view_settings.exposure = -0.08
    if scene.render.engine == "CYCLES":
        scene.cycles.samples = max(scene.cycles.samples, render_profile["samples"])
        scene.cycles.diffuse_bounces = 4
        scene.cycles.glossy_bounces = 6
    return {**render_profile, "evidenceCalibrated": True}


def set_separated_white_world() -> dict:
    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    world.color = (0.985, 0.99, 0.97)
    record = {
        "role": "ambient-white-studio",
        "color": [0.985, 0.99, 0.97],
        "strength": 0.36,
        "backgroundMode": "high-key-white-studio",
        "backgroundAsPrimarySubjectLight": False,
    }
    background = world.node_tree.nodes.get("Background") if world.use_nodes else None
    if background:
        background.inputs["Color"].default_value = (0.985, 0.99, 0.97, 1.0)
        background.inputs["Strength"].default_value = record["strength"]
    return record


def build_goal29_studio(goal20, h) -> dict:
    world_record = set_separated_white_world()
    white_cloth = make_principled_material("goal29_white_cyclorama_matte", (0.96, 0.97, 0.94, 1.0), roughness=0.82)
    white_reflector = make_principled_material("goal29_far_white_reflector_matte", (0.92, 0.94, 0.90, 1.0), roughness=0.88)
    soft_silver = make_principled_material("goal29_far_silver_reflector_matte", (0.68, 0.70, 0.67, 1.0), metallic=0.0, roughness=0.76)
    gradient = h.add_reflection_gradient_environment(
        h.make_gradient_environment_material("goal29_continuous_white_silver_gradient_environment")
    )
    gradient["name"] = "goal29_continuous_silver_white_reflection_environment"
    gradient["backgroundAsPrimarySubjectLight"] = False

    cards = [
        h.add_card("goal29_white_floor_sweep", (0.0, -0.65, -1.08), (0.0, -0.35, 0.0), 12.0, 8.0, white_cloth, "visible-white-floor-background", hide_camera=False),
        h.add_card("goal29_white_back_sweep", (0.0, 7.4, 1.25), (0.0, 0.0, 0.12), 13.4, 7.2, white_cloth, "visible-white-background-sweep", hide_camera=False),
        h.add_card("goal29_left_far_white_reflector", (-13.8, -1.4, 1.65), (0.0, 0.0, 0.08), 10.4, 7.2, white_reflector, "left-far-white-reflector", hide_camera=True),
        h.add_card("goal29_right_far_white_reflector", (13.8, -0.9, 1.42), (0.0, 0.0, 0.08), 10.2, 7.0, white_reflector, "right-far-white-reflector", hide_camera=True),
        h.add_card("goal29_overhead_far_white_reflector", (0.0, -1.1, 10.4), (0.0, 0.0, 0.08), 13.0, 7.4, white_reflector, "overhead-far-white-reflector", hide_camera=True),
        h.add_card("goal29_rear_silver_gradient_reflector", (0.0, 6.7, 0.82), (0.0, 0.0, 0.06), 10.6, 5.0, soft_silver, "rear-soft-silver-gradient-reflector", hide_camera=True),
    ]

    rig = [
        h.add_light(goal20, "top-left-oblique-key", "goal29_far_top_left_soft_key", (-15.8, -12.0, 9.2), (-0.05, 0.0, 0.12), 760, 18.0, 0.035),
        h.add_light(goal20, "top-right-oblique-rim", "goal29_far_top_right_soft_rim", (15.2, -11.2, 8.6), (0.08, 0.0, 0.12), 580, 17.2, 0.030),
        h.add_light(goal20, "bottom-left-lift", "goal29_far_bottom_left_lift", (-12.6, -10.8, 0.50), (-0.04, 0.0, -0.04), 122, 12.0, 0.018),
        h.add_light(goal20, "bottom-right-lift", "goal29_far_bottom_right_lift", (12.2, -10.6, 0.50), (0.04, 0.0, -0.04), 126, 12.0, 0.018),
        h.add_light(goal20, "front-fill", "goal29_far_front_soft_fill", (0.0, -15.4, 3.2), (0.0, 0.0, 0.06), 62, 17.0, 0.012),
        world_record,
    ]
    for item in cards:
        item["backgroundAsPrimarySubjectLight"] = False
    return {
        "backgroundMode": "high-key-white-studio",
        "lightingSeparationModel": "background-subject-reflection-contamination-separated",
        "backgroundAsPrimarySubjectLight": False,
        "whiteWorldPrimaryExposure": False,
        "visibleLightPanelsInCamera": False,
        "glossyEquipmentReflectionAllowed": False,
        "reflectionCardsGlossyReadableAllowed": False,
        "hardWhiteBlotchReflectionAllowed": False,
        "reflectionGradientEnvironment": gradient,
        "whiteStudioCards": cards,
        "blackFlags": [],
        "rig": rig,
        "roles": [
            "top-left-oblique-key",
            "top-right-oblique-rim",
            "bottom-left-lift",
            "bottom-right-lift",
            "front-fill",
            "ambient-white-studio",
        ],
    }


def isolate_polished_ball_reflections(records: list[dict], h) -> dict:
    suppressed = []
    suppressed_groups = Counter()
    allowed = []
    for record in records:
        obj = record["object"]
        if record["partName"] == "球体":
            h.safe_set(obj, "visible_glossy", True)
            allowed.append(record["partName"])
            continue
        h.safe_set(obj, "visible_glossy", False)
        suppressed.append(record["partName"])
        suppressed_groups[record["group"]] += 1
    return {
        "policy": "commercial-polished-ball-all-non-ball-product-reflection-isolation",
        "suppressedGroups": sorted(suppressed_groups),
        "suppressedGroupCounts": dict(sorted(suppressed_groups.items())),
        "suppressedCount": len(suppressed),
        "allowedGlossyProductParts": sorted(set(allowed)),
        "visibleInCamera": True,
        "visibleInDiffuseAndShadow": True,
        "visibleInGlossy": False,
        "purpose": "prevent any non-ball valve component from becoming a readable reflection on the polished ball",
        "samplePartNames": sorted(set(suppressed))[:16],
    }


def runtime_state_for(progress: float, motion_authority: dict) -> dict:
    assembly = smoothstep((progress - 0.08) / 0.48)
    ball_presentation = smoothstep((progress - 0.34) / 0.34)
    cutaway = smoothstep((progress - 0.68) / 0.12)
    water = smoothstep((progress - 0.78) / 0.14)
    hero = smoothstep((progress - 0.88) / 0.08)
    channels = {
        "shellClosure": assembly,
        "seatSealClosure": assembly,
        "stemDriveClosure": assembly,
        "lowerSupportClosure": assembly,
        "fastenerReturn": assembly,
        "springReturn": assembly,
        "ballPresentationTurn": ball_presentation,
        "cutawayReveal": cutaway,
        "clearWaterFlow": water,
        "heroHold": hero,
    }
    if set(motion_authority["channels"]) != RUNTIME_CHANNELS:
        raise RuntimeError("hero-runtime motion channel set drifted")
    return channels


def transformed_offset(record: dict, state: dict, scale: dict) -> Vector:
    local = record["local_center"]
    group = record["group"]
    part_name = record["partName"]
    offset = Vector((0, 0, 0))
    shell_open = 1.0 - state["shellClosure"]
    seat_open = 1.0 - state["seatSealClosure"]
    stem_open = 1.0 - state["stemDriveClosure"]
    lower_open = 1.0 - state["lowerSupportClosure"]
    fastener_open = 1.0 - state["fastenerReturn"]
    spring_open = 1.0 - state["springReturn"]

    if group == "bodyPressureShell":
        offset.x += sign(local.x) * scale["body_pressure_shell_x"] * 1.55 * shell_open
        offset.y += sign(local.y) * scale["body_pressure_shell_y"] * 1.35 * shell_open
    elif group == "seatSealSystem":
        offset.x += sign(local.x) * scale["seat_seal_system_x"] * 1.45 * seat_open
        offset.y += sign(local.y) * scale["seat_seal_system_y"] * 1.30 * seat_open
    elif group == "stemPackingDrive":
        offset.z += scale["stem_packing_drive_z"] * 1.65 * stem_open
        offset.y += scale["stem_packing_drive_y"] * 1.30 * stem_open
    elif group == "ballTrunnionCore":
        if part_name == "球体":
            pass
        elif "固定轴" in part_name or local.z < -0.05:
            offset.z -= scale["lower_support_z"] * 1.55 * lower_open
        elif local.z > 0.02:
            offset.z += scale["stem_packing_drive_z"] * 0.52 * stem_open
    elif group == "fastenersSmallHardware":
        radial = Vector((local.x, local.y, 0))
        if radial.length < 0.001:
            radial = Vector((sign(local.x), sign(local.y), 0))
        radial.normalize()
        amount = spring_open if part_name == "弹簧" else fastener_open
        multiplier = 1.62 if part_name == "弹簧" else 1.42
        offset += radial * scale["fastener_radial"] * multiplier * amount
        offset.z += sign(local.z) * scale["fastener_z"] * multiplier * amount
    return offset


def apply_goal29_parts(records: list[dict], state: dict, transform_scale: dict) -> dict:
    moved_counts = Counter()
    max_offset = 0.0
    ball_angle = state["ballPresentationTurn"] * 100.0
    for record in records:
        obj = record["object"]
        offset = transformed_offset(record, state, transform_scale)
        obj.location = record["base_location"] + offset
        obj.rotation_euler = record["base_rotation"].copy()
        if record["partName"] == "球体":
            obj.rotation_euler.rotate_axis("Z", math.radians(ball_angle))
        if offset.length > 0.0001:
            moved_counts[record["group"]] += 1
            max_offset = max(max_offset, offset.length)
    bpy.context.view_layer.update()
    return {
        "ballAngleDegrees": round(ball_angle, 4),
        "movedCounts": dict(moved_counts),
        "maxOffset": round(max_offset, 6),
    }


def assign_cutaway_materials(records: list[dict], cutaway_amount: float, cutaway_materials: dict) -> dict:
    affected = []
    if cutaway_amount < 0.35:
        for record in records:
            if "original_material" in record:
                record["object"].data.materials[0] = record["original_material"]
        return {"type": "none", "visible": False, "amount": round(cutaway_amount, 4), "affectedParts": []}

    for record in records:
        obj = record["object"]
        if "original_material" not in record:
            record["original_material"] = obj.data.materials[0]
        if record["partName"] in {"阀体", "阀盖"}:
            obj.data.materials[0] = cutaway_materials.get(record["material"], cutaway_materials["castBlastedStainless"])
            affected.append(record["partName"])
        else:
            obj.data.materials[0] = record["original_material"]
    return {
        "type": "transparent-shell-cutaway-proxy",
        "visible": True,
        "amount": round(cutaway_amount, 4),
        "affectedParts": sorted(set(affected)),
        "releaseNote": "lookdev proxy for cutaway readability; not a final boolean section approval",
    }


def create_cutaway_materials(material_specs: dict) -> dict:
    result = {}
    for name in ("castBlastedStainless", "machinedStainless"):
        spec = dict(material_specs[name])
        spec["alpha"] = 0.38
        spec["roughness"] = max(float(spec["roughness"]), 0.46)
        result[name] = make_principled_material(
            f"goal29_cutaway_{name}",
            spec["base_color"],
            metallic=spec.get("metallic", 1.0),
            roughness=spec["roughness"],
            alpha=spec["alpha"],
            coat=spec.get("coat", 0.0),
        )
    return result


def create_flow_objects(water_material, highlight_material) -> list[bpy.types.Object]:
    objects = []
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.034, depth=0.84, location=(0.0, 0.0, -0.095), rotation=(0.0, math.radians(90), 0.0))
    core = bpy.context.object
    core.name = "goal29_clear_water_flow_core"
    core.data.materials.append(water_material)
    objects.append(core)
    for index, x in enumerate([-0.26, 0.0, 0.26]):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.038, minor_radius=0.0022, major_segments=48, minor_segments=8, location=(x, 0.0, -0.095), rotation=(0.0, math.radians(90), 0.0))
        ring = bpy.context.object
        ring.name = f"goal29_clear_water_flow_highlight_{index + 1}"
        ring.data.materials.append(highlight_material)
        objects.append(ring)
    for obj in objects:
        obj.hide_viewport = True
        obj.hide_render = True
    return objects


def update_flow_objects(objects: list[bpy.types.Object], flow_amount: float) -> dict:
    visible = flow_amount > 0.08
    for index, obj in enumerate(objects):
        obj.hide_viewport = not visible
        obj.hide_render = not visible
        if index > 0:
            phase = (flow_amount + index * 0.23) % 1.0
            obj.location.x = -0.32 + phase * 0.64
    return {
        "type": "clear-water-flow-proxy",
        "visible": visible,
        "amount": round(flow_amount, 4),
        "objectCount": len(objects),
        "material": "translucent clean water",
    }


def camera_for_state(progress: float, state: dict):
    assembly = state["shellClosure"]
    cutaway = state["cutawayReveal"]
    flow = state["clearWaterFlow"]
    opening_location = Vector((-1.88, -5.28, 1.08))
    assembly_location = Vector((-1.34, -4.18, 0.82))
    final_location = Vector((-1.18, -3.72, 0.70))
    location = opening_location.lerp(assembly_location, assembly)
    location = location.lerp(final_location, max(cutaway, flow) * 0.72)
    target = Vector((-0.01, -0.02, 0.00)).lerp(Vector((-0.02, -0.015, -0.055)), max(cutaway, flow) * 0.72)
    fov = 29.0 - 3.2 * assembly + 1.6 * max(cutaway, flow)
    return location, target, fov


def camera_record(camera, target, fov: float, distance_multiplier: float) -> dict:
    return {
        "position": [round(value, 6) for value in camera.location],
        "target": [round(value, 6) for value in target],
        "fovDegrees": round(fov, 4),
        "distanceMultiplier": round(distance_multiplier, 4),
        "fovMultiplier": 0.53,
        "look": "short-scroll far long-lens commercial product camera; no visible light panels",
    }


def render_frames(h, repo_root: Path, frames_dir: Path, authority: dict, records: list[dict], camera, render_profile: dict, frames: list[int], cutaway_materials: dict, flow_objects: list[bpy.types.Object]) -> tuple[list[dict], dict]:
    frame_records = []
    max_offset = 0.0
    max_ball = 0.0
    max_cutaway = 0.0
    max_flow = 0.0
    started = time.perf_counter()
    motion_authority = authority["motion.json"]
    camera_authority = authority["camera.json"]
    storyboard = authority["storyboard.json"]
    transform_scale = motion_authority["blender_transform_scale"]
    for order, frame_index in enumerate(frames):
        progress = progress_for_frame(frame_index)
        state = runtime_state_for(progress, motion_authority)
        motion = apply_goal29_parts(records, state, transform_scale)
        cutaway = assign_cutaway_materials(records, state["cutawayReveal"], cutaway_materials)
        water = update_flow_objects(flow_objects, state["clearWaterFlow"])
        location, target, fov = camera_for_state(progress, state)
        distance_multiplier = camera_authority["composition_state"]["distance_multiplier_min"] + 0.10
        camera.location = location
        camera.data.angle = math.radians(fov)
        h.goal20.look_at(camera, target)

        output_path = frames_dir / f"frame{frame_index:04d}.png"
        bpy.context.scene.render.filepath = str(output_path)
        bpy.ops.render.render(write_still=True)
        max_offset = max(max_offset, motion["maxOffset"])
        max_ball = max(max_ball, motion["ballAngleDegrees"])
        max_cutaway = max(max_cutaway, state["cutawayReveal"])
        max_flow = max(max_flow, state["clearWaterFlow"])
        frame_records.append(
            {
                "frame": frame_index,
                "progress": round(progress, 6),
                "shotId": shot_for_progress(storyboard, progress),
                "path": str(output_path.relative_to(repo_root)).replace("\\", "/"),
                "width": render_profile["width"],
                "height": render_profile["height"],
                "bytes": output_path.stat().st_size,
                "sha256": h.sha256(output_path),
                "camera": camera_record(camera, target, fov, distance_multiplier),
                "channels": {key: round(value, 6) for key, value in state.items()},
                "motionEvidence": motion,
                "cutaway": cutaway,
                "clearWaterFlow": water,
            }
        )
        if (order + 1) % 2 == 0 or order + 1 == len(frames):
            print(f"Goal29 rendered {order + 1}/{len(frames)} frames in {time.perf_counter() - started:.1f}s")
    return frame_records, {
        "maxOffset": round(max_offset, 6),
        "maxBallAngleDegrees": round(max_ball, 4),
        "maxCutawayReveal": round(max_cutaway, 4),
        "maxClearWaterFlow": round(max_flow, 4),
        "renderSeconds": round(time.perf_counter() - started, 3),
    }


def write_index(goal_dir: Path, manifest: dict) -> None:
    frame_paths = [frame["path"].split("/goal29-evidence-calibrated-runtime-lookdev/")[-1] for frame in manifest["frames"]]
    labels = [f"frame {frame['frame']:04d} | {frame['shotId']}" for frame in manifest["frames"]]
    html_text = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Goal29 Evidence-Calibrated Runtime Lookdev</title>
  <style>
    :root {{ color-scheme: light; font-family: Inter, "Noto Sans SC", system-ui, sans-serif; background: #f7f8f6; color: #202421; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; }}
    main {{ width: min(1320px, calc(100% - 32px)); margin: 0 auto; padding: 24px 0 40px; }}
    header {{ display: grid; gap: 8px; margin-bottom: 16px; }}
    h1 {{ margin: 0; font-size: clamp(24px, 4vw, 40px); line-height: 1.08; letter-spacing: 0; }}
    p {{ margin: 0; color: #66706a; line-height: 1.55; }}
    .stage {{ display: grid; gap: 10px; border: 1px solid #d6ddd8; border-radius: 8px; background: #fff; padding: 10px; }}
    img {{ display: block; width: 100%; height: auto; border-radius: 6px; background: #fff; }}
    .controls {{ display: grid; grid-template-columns: auto 1fr auto; gap: 10px; align-items: center; }}
    button {{ width: 40px; height: 40px; border: 1px solid #b7c1bb; border-radius: 8px; background: #f5f7f5; color: #202421; cursor: pointer; }}
    input[type=range] {{ width: 100%; accent-color: #65756b; }}
    output, code {{ color: #59645e; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 12px; }}
  </style>
</head>
<body>
<main>
  <header>
    <h1>Goal29 Evidence-Calibrated Runtime Lookdev</h1>
    <p>Hero-runtime 2026-08-03.4: lighting, material, camera, motion, storyboard and delivery controls are tested as a blocked lookdev sample. Manifest: <code>render-manifest.json</code>.</p>
  </header>
  <section class="stage">
    <img id="frame" src="{html.escape(frame_paths[0])}" alt="Goal29 evidence-calibrated runtime lookdev frame">
    <div class="controls">
      <button id="play" type="button" aria-label="Play or pause">Play</button>
      <input id="scrub" type="range" min="0" max="{len(frame_paths) - 1}" value="0">
      <output id="label">{html.escape(labels[0])}</output>
    </div>
  </section>
</main>
<script>
const frame = document.querySelector("#frame");
const scrub = document.querySelector("#scrub");
const label = document.querySelector("#label");
const play = document.querySelector("#play");
const frames = {json.dumps(frame_paths)};
const labels = {json.dumps(labels)};
let timer = null;
function setFrame(value) {{
  const index = Math.max(0, Math.min(frames.length - 1, Number(value) || 0));
  frame.src = frames[index];
  scrub.value = index;
  label.value = labels[index];
}}
scrub.addEventListener("input", () => setFrame(scrub.value));
play.addEventListener("click", () => {{
  if (timer) {{ clearInterval(timer); timer = null; play.textContent = "Play"; return; }}
  play.textContent = "Pause";
  timer = setInterval(() => setFrame((Number(scrub.value) + 1) % frames.length), 520);
}});
</script>
</body>
</html>
"""
    h = sys.modules.get("goal29_helpers")
    if h:
        h.write_text(goal_dir / "index.html", html_text)
    else:
        (goal_dir / "index.html").write_text(html_text, encoding="utf-8")


def write_status(goal_dir: Path, manifest: dict, h) -> None:
    text = f"""# Goal29 Evidence-Calibrated Runtime Lookdev

Generated: {manifest['generatedAt']}

## Boundary

- Five-frame lookdev sample only; not a 240-frame delivery render.
- Runtime authority: hero-runtime {manifest['runtimeAuthority']['authorityVersion']}.
- The release gate remains closed: no homepage replacement and no Pages publication.
- Existing samples remain history; this lookdev probes the updated A-E control route.

## Acceptance Focus

- Lighting: background is not the subject key; far large soft sources and clean white/silver reflection environment drive metal shape.
- Material: clean metallic-roughness stainless, no dirty scratches or white diffuse shortcut.
- Camera: farther long-lens composition with enough opening margin.
- Motion: fully exploded opening moves one way into assembly.
- Storyboard: ball core, cutaway reveal and clean water flow are distinct late-stage beats.

## Review Frames

{chr(10).join(f"- `{frame['path'].split('/goal29-evidence-calibrated-runtime-lookdev/')[-1]}` - {frame['shotId']}" for frame in manifest['frames'])}
"""
    h.write_text(goal_dir / "lookdev-status.md", text)


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    goal20 = load_module(repo_root, "scripts/render_goal20_blender_step_proof.py", "goal20_render_helpers")
    goal26 = load_module(repo_root, "scripts/render_goal26_blender_camera_explosion_proof.py", "goal26_render_helpers")
    h = load_module(repo_root, "scripts/render_goal28a_clean_commercial_white_studio.py", "goal29_helpers")
    h.goal20 = goal20

    authority_root, runtime_authority, authority_hashes = h.load_runtime_authority(repo_root, args.runtime_authority)
    motion_control_path = (repo_root / args.motion_control).resolve()
    goal26_manifest_path = (repo_root / args.goal26_manifest).resolve()
    old_control = h.read_json(motion_control_path)
    goal26_manifest = h.read_json(goal26_manifest_path)
    model_path = (repo_root / old_control["sources"]["stepMesh"]).resolve()
    semantic_map_path = (repo_root / old_control["sources"]["goal20SemanticMap"]).resolve()
    semantic_map = h.read_json(semantic_map_path)
    frames = selected_frames(args.frame_list)

    goal20.clear_scene()
    render_profile = configure_goal29_render(h, args.profile)
    material_specs = h.clean_material_specs(goal26, runtime_authority["material.json"])
    materials = {name: goal20.make_material(f"goal29_clean_{name}", spec) for name, spec in material_specs.items()}
    cutaway_materials = create_cutaway_materials(material_specs)
    meshes = goal20.import_model(model_path)
    if not meshes:
        raise RuntimeError(f"No mesh objects imported from {model_path}")
    goal20.create_rig(meshes)
    records, group_counts, material_counts, part_counts = goal20.assign_materials(meshes, materials)
    for record in records:
        record["original_material"] = record["object"].data.materials[0]
    body_records = [record for record in records if record["partName"] == "阀体"]
    if len(body_records) != 1:
        raise RuntimeError(f"Expected exactly one valve-body mesh, found {len(body_records)}")
    zone_assignment = h.assign_commercial_body_material(body_records[0]["object"], materials["castBlastedStainless"])
    glossy_isolation = isolate_polished_ball_reflections(records, h)
    lighting = build_goal29_studio(goal20, h)
    water_objects = create_flow_objects(make_water_material(), make_water_highlight_material())
    camera = goal26.create_camera()

    frame_records, motion_evidence = render_frames(
        h,
        repo_root,
        frames_dir,
        runtime_authority,
        records,
        camera,
        render_profile,
        frames,
        cutaway_materials,
        water_objects,
    )
    if 0 in frames:
        shutil.copyfile(frames_dir / "frame0000.png", out_dir / "poster.png")

    manifest = {
        "schemaVersion": 1,
        "goalId": "goal29-evidence-calibrated-runtime-lookdev",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "goal": "Goal29 evidence-calibrated 3D industrial Blender runtime lookdev",
        "product": "ztovalve fixed ball valve",
        "renderer": {
            "engine": render_profile["engine"],
            "profile": args.profile,
            "blender": bpy.app.version_string,
        },
        "runtimeAuthority": {
            "authorityId": "hero-runtime",
            "authorityStatus": runtime_authority["authority.json"]["authority_status"],
            "authorityVersion": runtime_authority["authority.json"]["authority_version"],
            "authorityPath": str(authority_root.relative_to(repo_root)).replace("\\", "/"),
            "soleCurrentHeroRenderAuthority": True,
            "manifestAuthorityBindingRequired": runtime_authority["release-gate.json"]["runtime_authority_policy"]["render_manifest_authority_binding_required"],
            "nonRuntimeRenderAuthorityAllowed": runtime_authority["release-gate.json"]["runtime_authority_policy"]["non_runtime_render_authority_allowed"],
            "authorityFileSha256": authority_hashes,
        },
        "sourceBoundary": {
            "stepMesh": str(model_path.relative_to(repo_root)).replace("\\", "/"),
            "stepMeshSha256": h.sha256(model_path),
            "goal20SemanticMap": str(semantic_map_path.relative_to(repo_root)).replace("\\", "/"),
            "goal20SemanticMapSha256": h.sha256(semantic_map_path),
            "legacyMotionEvidence": str(motion_control_path.relative_to(repo_root)).replace("\\", "/"),
            "legacyMotionEvidenceSha256": h.sha256(motion_control_path),
            "goal26RenderManifest": str(goal26_manifest_path.relative_to(repo_root)).replace("\\", "/"),
            "goal26RenderManifestSha256": h.sha256(goal26_manifest_path),
            "rule": "Geometry and historical motion evidence may be consumed, but material, lighting, camera, motion, storyboard and release decisions are bound to hero-runtime.",
        },
        "renderProfile": {
            "width": render_profile["width"],
            "height": render_profile["height"],
            "samples": render_profile["samples"],
            "engine": render_profile["engine"],
            "fps": runtime_authority["camera.json"]["timeline_state"]["fps"],
            "sourceTotalFrames": runtime_authority["camera.json"]["timeline_state"]["total_frames"],
            "sampleFrames": frames,
            "sequenceFrameCount": len(frame_records),
            "homepageConnected": False,
            "heroAvifReplaced": False,
            "published": False,
        },
        "previewSurface": {
            "route": str((out_dir / "index.html").relative_to(repo_root)).replace("\\", "/"),
            "frameDirectory": str(frames_dir.relative_to(repo_root)).replace("\\", "/"),
            "poster": str((out_dir / "poster.png").relative_to(repo_root)).replace("\\", "/") if (out_dir / "poster.png").is_file() else None,
        },
        "partIdentity": {
            "meshCount": len(meshes),
            "goal20SemanticMeshCount": sum(semantic_map["partCounts"].values()),
            "groupCounts": group_counts,
            "materialCounts": material_counts,
            "partCounts": part_counts,
        },
        "materialDirection": {
            "productMaterialTruth": runtime_authority["material.json"]["appearance_state"]["body_material_truth"],
            "commercialMaterialProfile": runtime_authority["material.json"]["appearance_state"]["material_profile"],
            "pbrWorkflow": runtime_authority["material.json"]["pbr_calibration_policy"]["workflow"],
            "whiteDiffuseShortcut": False,
            "commercialBodyAssignmentPolicy": runtime_authority["material.json"]["release_expectations"]["commercial_body_assignment_policy"],
            "bodyZoneCount": zone_assignment["bodyZoneCount"],
            "zoneAssignment": zone_assignment,
            "materialParameterSnapshot": {
                "familyMaterials": {
                    "castBlastedStainless": material_specs["castBlastedStainless"],
                    "machinedStainless": material_specs["machinedStainless"],
                    "fastenerStainless": material_specs["fastenerStainless"],
                    "polishedStainlessBall": material_specs["polishedStainlessBall"],
                    "graphitePacking": material_specs["graphitePacking"],
                    "softSealPtfe": material_specs["softSealPtfe"],
                }
            },
            "cleanPbr": True,
            "explicitScratchGeometryVisible": False,
            "dirtyBlotchNoiseVisible": False,
            "dirtyBlotchHighlightsVisible": False,
            "polygonZoneArtifactsVisible": False,
            "productFacingMaterialHardEdgesVisible": False,
            "nonRuntimeMaterialSourceUsed": False,
            "polishedBallRoughness": material_specs["polishedStainlessBall"]["roughness"],
        },
        "lighting": {
            "evidenceCalibrated": True,
            **lighting,
            "productGlossyReflectionRetouch": glossy_isolation,
            "reviewFramePriority": [0, 124, 176, 216, 56],
        },
        "cameraDirection": {
            "mode": runtime_authority["camera.json"]["composition_state"]["mode"],
            "distanceMultiplier": runtime_authority["camera.json"]["composition_state"]["distance_multiplier_min"] + 0.10,
            "fovMultiplier": 0.53,
            "visibleLightPanelsInCamera": False,
            "phasePolicy": runtime_authority["camera.json"]["camera_phase_policy"],
        },
        "motionFusion": {
            "sourceGoal": goal26_manifest["goal"],
            "route": runtime_authority["motion.json"]["route_policy"],
            "initialExplodedRequirements": runtime_authority["motion.json"]["initial_exploded_requirements"],
            "controlledChannels": runtime_authority["motion.json"]["channels"],
            "axisMap": runtime_authority["motion.json"]["axis_map"],
            "maxOffset": motion_evidence["maxOffset"],
            "maxBallAngleDegrees": motion_evidence["maxBallAngleDegrees"],
            "maxCutawayReveal": motion_evidence["maxCutawayReveal"],
            "maxClearWaterFlow": motion_evidence["maxClearWaterFlow"],
            "renderSeconds": motion_evidence["renderSeconds"],
        },
        "storyboard": {
            "shotOrder": runtime_authority["storyboard.json"]["shot_order"],
            "storyRhythmPolicy": runtime_authority["storyboard.json"]["story_rhythm_policy"],
        },
        "releaseState": {
            "currentVisualApproval": runtime_authority["release-gate.json"]["lookdev_evidence_state"]["current_visual_approval"],
            "approvedFor240FrameRender": runtime_authority["release-gate.json"]["approval_state"]["approved_for_240_frame_render"],
            "approvedForHomepageReplacement": runtime_authority["release-gate.json"]["approval_state"]["approved_for_homepage_replacement"],
            "approvedForPagesPublication": runtime_authority["release-gate.json"]["approval_state"]["approved_for_pages_publication"],
            "nextRequiredMilestone": runtime_authority["release-gate.json"]["next_required_milestone"],
        },
        "frames": frame_records,
        "constraints": [
            "Five-frame Goal29 lookdev sample only.",
            "No homepage hero replacement is performed.",
            "No existing AVIF sequence is overwritten.",
            "No Pages publication is performed.",
            "hero-runtime is the sole current hero render authority.",
            "The release gate remains closed until visual approval.",
        ],
    }
    h.write_json(out_dir / "render-manifest.json", manifest)
    write_status(out_dir, manifest, h)
    write_index(out_dir, manifest)
    print(json.dumps({"status": "ok", "goal": manifest["goalId"], "frames": len(frame_records), "outDir": str(out_dir)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
