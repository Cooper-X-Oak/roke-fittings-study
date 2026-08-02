#!/usr/bin/env python3
"""Render Goal 20 Blender/Cycles STEP-first material proof stills.

Run inside Blender:
blender --background --python scripts/render_goal20_blender_step_proof.py -- --repo-root . --profile proof
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

try:
    import bpy
    from mathutils import Vector
except ImportError as exc:  # pragma: no cover - normal Python cannot provide bpy.
    raise SystemExit(
        "This script must be run by Blender's Python interpreter, not system Python."
    ) from exc


GOAL_DIR = "docs/assets/ztovalve/hero/goal20-blender-cycles-step-proof"

STATES = {
    "assembled": {
        "explode": 0.0,
        "ballReveal": 0.0,
    },
    "front-exploded": {
        "explode": 1.0,
        "ballReveal": 0.35,
    },
    "detail-open": {
        "explode": 0.55,
        "ballReveal": 1.0,
    },
}

CAMERA_SETUPS = [
    {
        "id": "assembled-product",
        "stateId": "assembled",
        "name": "完整产品",
        "filename": "01-assembled-product-cycles.png",
        "purpose": "检查 STEP-first mesh 在 Blender/Cycles 中的整体比例、法线和六类材质平衡。",
        "camera": (0.78, -1.28, 0.48),
        "target": (-0.035, 0.025, 0.0),
        "lensMm": 68,
    },
    {
        "id": "front-exploded-start",
        "stateId": "front-exploded",
        "name": "爆炸首帧",
        "filename": "02-front-exploded-start-cycles.png",
        "purpose": "验证未来滚动首帧可从完整爆炸图开始，而不是先合体再爆炸。",
        "camera": (1.02, -1.72, 0.70),
        "target": (-0.035, 0.025, 0.07),
        "lensMm": 64,
    },
    {
        "id": "polished-ball-close",
        "stateId": "detail-open",
        "name": "球体近景",
        "filename": "03-polished-ball-close-cycles.png",
        "purpose": "检查 mirror polished stainless steel ball 是否能在柔和 studio 反射下成立。",
        "targetPart": "球体",
        "cameraOffset": (0.46, -0.86, 0.24),
        "targetOffset": (0.0, -0.006, 0.0),
        "lensMm": 82,
    },
    {
        "id": "body-flange-sandblast-close",
        "stateId": "assembled",
        "name": "阀体/法兰喷砂近景",
        "filename": "04-body-flange-sandblast-close-cycles.png",
        "purpose": "检查 investment cast stainless steel, bead-blasted/sandblasted satin finish 的阀体读感。",
        "targetPart": "阀体",
        "cameraOffset": (0.46, -0.82, 0.20),
        "targetOffset": (0.055, -0.055, -0.012),
        "lensMm": 82,
    },
    {
        "id": "fastener-seal-detail",
        "stateId": "front-exploded",
        "name": "螺栓/密封圈近景",
        "filename": "05-fastener-seal-detail-cycles.png",
        "purpose": "检查 fastenerStainless、graphitePacking 和 softSealPtfe 的分层是否清楚。",
        "camera": (0.52, -1.08, 0.42),
        "target": (-0.055, 0.02, 0.075),
        "lensMm": 90,
    },
]

MATERIAL_SPECS = {
    "castBlastedStainless": {
        "base_color": (0.45, 0.47, 0.45, 1.0),
        "metallic": 1.0,
        "roughness": 0.56,
        "anisotropic": 0.18,
        "coat": 0.03,
        "bump": 0.038,
        "bump_distance": 0.004,
        "noise_scale": 680,
        "noise_detail": 16,
        "color_variation": ((0.38, 0.40, 0.38, 1.0), (0.54, 0.56, 0.53, 1.0)),
        "color_noise_scale": 520,
        "color_noise_detail": 14,
        "roughness_variation": (0.50, 0.72),
        "roughness_noise_scale": 420,
    },
    "machinedStainless": {
        "base_color": (0.58, 0.60, 0.57, 1.0),
        "metallic": 1.0,
        "roughness": 0.29,
        "anisotropic": 0.74,
        "coat": 0.14,
        "bump": 0.012,
        "bump_distance": 0.008,
        "noise_scale": 125,
        "noise_detail": 11,
        "roughness_variation": (0.18, 0.34),
        "roughness_noise_scale": 115,
    },
    "polishedStainlessBall": {
        "base_color": (0.76, 0.78, 0.75, 1.0),
        "metallic": 1.0,
        "roughness": 0.18,
        "anisotropic": 0.10,
        "coat": 0.20,
        "bump": 0.001,
        "bump_distance": 0.004,
        "noise_scale": 260,
        "noise_detail": 8,
        "roughness_variation": (0.14, 0.22),
        "roughness_noise_scale": 70,
    },
    "graphitePacking": {
        "base_color": (0.012, 0.013, 0.014, 1.0),
        "metallic": 0.16,
        "roughness": 0.64,
        "anisotropic": 0.0,
        "coat": 0.0,
        "bump": 0.034,
        "bump_distance": 0.01,
        "noise_scale": 70,
        "noise_detail": 10,
    },
    "softSealPtfe": {
        "base_color": (0.74, 0.70, 0.60, 1.0),
        "metallic": 0.0,
        "roughness": 0.50,
        "anisotropic": 0.0,
        "coat": 0.02,
        "bump": 0.01,
        "bump_distance": 0.006,
        "noise_scale": 58,
        "noise_detail": 8,
    },
    "fastenerStainless": {
        "base_color": (0.25, 0.27, 0.25, 1.0),
        "metallic": 1.0,
        "roughness": 0.30,
        "anisotropic": 0.36,
        "coat": 0.08,
        "bump": 0.014,
        "bump_distance": 0.007,
        "noise_scale": 145,
        "noise_detail": 9,
        "roughness_variation": (0.24, 0.40),
        "roughness_noise_scale": 130,
    },
    "studioWhite": {
        "base_color": (0.58, 0.59, 0.56, 1.0),
        "metallic": 0.0,
        "roughness": 0.74,
        "anisotropic": 0.0,
        "coat": 0.0,
        "bump": 0.0,
        "noise_scale": 1,
        "noise_detail": 1,
    },
    "reflectionGrey": {
        "base_color": (0.26, 0.27, 0.28, 1.0),
        "metallic": 0.0,
        "roughness": 0.78,
        "anisotropic": 0.0,
        "coat": 0.0,
        "bump": 0.0,
        "noise_scale": 1,
        "noise_detail": 1,
    },
}

MOJIBAKE_NAME_MAP = {
    "·§ͥ": "阀体",
    "µ¯»": "弹簧",
    "·§عĜ·㈦": "阀座密封圈",
    "·§عѹȦ": "阀座压圈",
    "·§×ùÅÌ¸ù": "阀座盘根",
    "·§ع": "阀座",
    "Ȳͥ": "球体",
    "¹̶¨ס": "固定轴",
    "¹̶¨סµ熬": "固定轴垫片",
    "¹̶¨סס³": "固定轴轴承",
    "·§¸": "阀盖",
    "ֹΆµ": "止推垫",
    "ͮ\x8fФ": "填料箱",
    "ͮ\x8fФµ熬": "填料箱垫片",
    "·§¸̖ᴐ": "阀杆轴承",
    "Ȳͥס³": "球体轴承",
    "ͮ\x8f": "填料",
    "ͮ\x8fѹȦ": "填料压圈",
    "ͮ\x8fѹ¸": "填料压盖",
    "אµ5熬": "中道垫片",
    "֧¼": "支架",
    "ƅϛ·§µ熬": "排污阀垫片",
    "¶Í·": "堵头",
}


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    args = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--model", default=f"{GOAL_DIR}/goal20-step-mesh.glb")
    parser.add_argument("--step-report", default=f"{GOAL_DIR}/step-mesh-report.json")
    parser.add_argument("--step-audit", default="asset/derived/fixed-ball-valve/model-audit-step.json")
    parser.add_argument("--out-dir", default=f"{GOAL_DIR}/stills")
    parser.add_argument("--hdri", default=f"{GOAL_DIR}/studio_small_09_1k.hdr")
    parser.add_argument("--profile", choices=["smoke", "proof", "final"], default="proof")
    return parser.parse_args(args)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def strip_blender_suffix(name: str) -> str:
    return re.sub(r"\.\d{3}$", "", name)


def recover_part_name(raw_name: str) -> str:
    base = strip_blender_suffix(raw_name)
    if base in MOJIBAKE_NAME_MAP:
        return MOJIBAKE_NAME_MAP[base]
    try:
        return base.encode("latin1").decode("gbk")
    except UnicodeError:
        return base


def material_for_part(part_name: str) -> str:
    name = part_name.casefold()
    if part_name == "球体":
        return "polishedStainlessBall"
    if "阀体" in part_name or "阀盖" in part_name:
        return "castBlastedStainless"
    if any(token in part_name for token in ("阀座盘根", "阀座密封圈", "填料箱垫片", "中道垫片", "排污阀垫片")):
        return "graphitePacking"
    if part_name == "填料":
        return "graphitePacking"
    if part_name == "阀座":
        return "softSealPtfe"
    if any(token in name for token in ("stud", "nut", "washer", "screw", "pin")):
        return "fastenerStainless"
    if any(token in part_name for token in ("螺柱", "螺母", "弹簧", "平键")):
        return "fastenerStainless"
    return "machinedStainless"


def group_for_part(part_name: str) -> str:
    name = part_name.casefold()
    if any(token in part_name for token in ("阀体", "阀盖", "堵头")):
        return "bodyPressureShell"
    if any(token in part_name for token in ("球体", "固定轴", "轴承", "止推垫")):
        return "ballTrunnionCore"
    if any(token in part_name for token in ("阀座", "密封圈", "盘根")):
        return "seatSealSystem"
    if any(token in part_name for token in ("阀杆", "填料", "支架", "连接轴")):
        return "stemPackingDrive"
    if any(token in name for token in ("stud", "nut", "washer", "screw", "pin")):
        return "fastenersSmallHardware"
    if any(token in part_name for token in ("螺柱", "螺母", "垫片", "弹簧", "平键")):
        return "fastenersSmallHardware"
    return "machinedDetail"


def set_input(node, names, value) -> None:
    for name in names:
        if name in node.inputs:
            node.inputs[name].default_value = value
            return


def make_material(name: str, spec: dict) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    principled = nodes.get("Principled BSDF")
    if not principled:
        material.diffuse_color = spec["base_color"]
        return material

    set_input(principled, ["Base Color"], spec["base_color"])
    set_input(principled, ["Metallic"], spec["metallic"])
    set_input(principled, ["Roughness"], spec["roughness"])
    set_input(principled, ["Alpha"], spec.get("alpha", 1.0))
    set_input(principled, ["Coat Weight", "Clearcoat"], spec.get("coat", 0.0))
    set_input(principled, ["Coat Roughness", "Clearcoat Roughness"], 0.22)
    set_input(principled, ["Anisotropic IOR Level", "Anisotropic"], spec.get("anisotropic", 0.0))

    if "color_variation" in spec:
        color_noise = nodes.new(type="ShaderNodeTexNoise")
        color_noise.inputs["Scale"].default_value = spec.get("color_noise_scale", 80)
        color_noise.inputs["Detail"].default_value = spec.get("color_noise_detail", 11)
        color_noise.inputs["Roughness"].default_value = 0.56
        color_ramp = nodes.new(type="ShaderNodeValToRGB")
        low_color, high_color = spec["color_variation"]
        color_ramp.color_ramp.elements[0].position = 0.18
        color_ramp.color_ramp.elements[0].color = low_color
        color_ramp.color_ramp.elements[1].position = 1.0
        color_ramp.color_ramp.elements[1].color = high_color
        material.node_tree.links.new(color_noise.outputs["Fac"], color_ramp.inputs["Fac"])
        if "Base Color" in principled.inputs:
            material.node_tree.links.new(color_ramp.outputs["Color"], principled.inputs["Base Color"])

    if "roughness_variation" in spec and "Roughness" in principled.inputs:
        roughness_noise = nodes.new(type="ShaderNodeTexNoise")
        roughness_noise.inputs["Scale"].default_value = spec.get("roughness_noise_scale", 90)
        roughness_noise.inputs["Detail"].default_value = spec.get("roughness_noise_detail", 9)
        roughness_noise.inputs["Roughness"].default_value = 0.61
        roughness_ramp = nodes.new(type="ShaderNodeValToRGB")
        low_roughness, high_roughness = spec["roughness_variation"]
        roughness_ramp.color_ramp.elements[0].position = 0.20
        roughness_ramp.color_ramp.elements[0].color = (
            low_roughness,
            low_roughness,
            low_roughness,
            1.0,
        )
        roughness_ramp.color_ramp.elements[1].position = 1.0
        roughness_ramp.color_ramp.elements[1].color = (
            high_roughness,
            high_roughness,
            high_roughness,
            1.0,
        )
        material.node_tree.links.new(roughness_noise.outputs["Fac"], roughness_ramp.inputs["Fac"])
        material.node_tree.links.new(roughness_ramp.outputs["Color"], principled.inputs["Roughness"])

    bump_strength = spec.get("bump", 0.0)
    if bump_strength:
        noise = nodes.new(type="ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = spec.get("noise_scale", 80)
        noise.inputs["Detail"].default_value = spec.get("noise_detail", 10)
        noise.inputs["Roughness"].default_value = 0.57
        bump = nodes.new(type="ShaderNodeBump")
        bump.inputs["Strength"].default_value = bump_strength
        bump.inputs["Distance"].default_value = spec.get("bump_distance", 0.012)
        material.node_tree.links.new(noise.outputs["Fac"], bump.inputs["Height"])
        if "Normal" in principled.inputs:
            material.node_tree.links.new(bump.outputs["Normal"], principled.inputs["Normal"])

    material.diffuse_color = spec["base_color"]
    return material


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def configure_render(profile: str) -> dict:
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    render_profiles = {
        "smoke": {"width": 1280, "height": 720, "samples": 28},
        "proof": {"width": 2560, "height": 1440, "samples": 128},
        "final": {"width": 3840, "height": 2160, "samples": 256},
    }
    selected = render_profiles[profile]
    scene.cycles.samples = selected["samples"]
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 8
    scene.cycles.diffuse_bounces = 3
    scene.cycles.glossy_bounces = 5
    scene.render.resolution_x = selected["width"]
    scene.render.resolution_y = selected["height"]
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    try:
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "Medium High Contrast"
    except TypeError:
        pass
    scene.view_settings.exposure = -0.92
    scene.view_settings.gamma = 1
    try:
        scene.cycles.device = "GPU"
    except Exception:
        scene.cycles.device = "CPU"
    return selected


def import_model(model_path: Path) -> list[bpy.types.Object]:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(model_path))
    imported = [obj for obj in bpy.data.objects if obj not in before]
    return [obj for obj in imported if obj.type == "MESH"]


def object_bounds(obj: bpy.types.Object):
    world = obj.matrix_world
    corners = [world @ Vector(corner) for corner in obj.bound_box]
    min_v = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    max_v = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    return min_v, max_v, (min_v + max_v) * 0.5, max_v - min_v


def scene_bounds(meshes: list[bpy.types.Object]):
    mins = []
    maxs = []
    for obj in meshes:
        min_v, max_v, _center, _size = object_bounds(obj)
        mins.append(min_v)
        maxs.append(max_v)
    min_all = Vector((min(v.x for v in mins), min(v.y for v in mins), min(v.z for v in mins)))
    max_all = Vector((max(v.x for v in maxs), max(v.y for v in maxs), max(v.z for v in maxs)))
    return min_all, max_all, (min_all + max_all) * 0.5, max_all - min_all


def create_rig(meshes: list[bpy.types.Object]) -> bpy.types.Object:
    rig = bpy.data.objects.new("goal20_step_product_rig", None)
    bpy.context.collection.objects.link(rig)
    _min_v, _max_v, center, _size = scene_bounds(meshes)
    for obj in meshes:
        obj.parent = rig
        obj.matrix_parent_inverse = rig.matrix_world.inverted()
    rig.location = -center
    rig.rotation_euler[2] = math.radians(-7)
    bpy.context.view_layer.update()
    return rig


def add_modifiers(obj: bpy.types.Object, material_id: str) -> None:
    bevel_width = 0.00045 if material_id == "fastenerStainless" else 0.0009
    if material_id == "castBlastedStainless":
        bevel_width = 0.0012
    bevel = obj.modifiers.new("goal20_micro_bevel", "BEVEL")
    bevel.width = bevel_width
    bevel.segments = 2
    bevel.affect = "EDGES"
    weighted = obj.modifiers.new("goal20_weighted_normals", "WEIGHTED_NORMAL")
    weighted.keep_sharp = True


def assign_materials(meshes: list[bpy.types.Object], materials: dict):
    _min_v, _max_v, all_center, all_size = scene_bounds(meshes)
    records = []
    group_counts = Counter()
    material_counts = Counter()
    part_counts = Counter()

    for obj in meshes:
        source_name = strip_blender_suffix(obj.name)
        part_name = recover_part_name(source_name)
        material_id = material_for_part(part_name)
        group_id = group_for_part(part_name)
        obj.data.materials.clear()
        obj.data.materials.append(materials[material_id])
        add_modifiers(obj, material_id)
        _min_v, _max_v, center, size = object_bounds(obj)
        record = {
            "object": obj,
            "sourceName": source_name,
            "partName": part_name,
            "group": group_id,
            "material": material_id,
            "base_location": obj.location.copy(),
            "base_rotation": obj.rotation_euler.copy(),
            "local_center": center - all_center,
            "size": size,
        }
        obj["goal20_source_name"] = source_name
        obj["goal20_part_name"] = part_name
        obj["goal20_material"] = material_id
        obj["goal20_group"] = group_id
        records.append(record)
        group_counts[group_id] += 1
        material_counts[material_id] += 1
        part_counts[part_name] += 1

    return records, dict(group_counts), dict(material_counts), dict(part_counts)


def apply_state(records: list, state_id: str) -> None:
    amount = STATES[state_id]["explode"]
    ball_reveal = STATES[state_id].get("ballReveal", amount)
    for record in records:
        obj = record["object"]
        local = record["local_center"]
        group = record["group"]
        material = record["material"]
        offset = Vector((0, 0, 0))
        radial = Vector((local.x, local.y, 0))
        if radial.length < 0.001:
            radial = Vector((1, 0, 0))
        radial.normalize()

        if group == "bodyPressureShell":
            offset += radial * (0.075 * amount)
        elif group == "seatSealSystem":
            offset += radial * (0.11 * amount)
        elif group == "ballTrunnionCore":
            offset += radial * (0.038 * amount)
            offset.z += math.copysign(0.026 * amount, local.z if abs(local.z) > 0.001 else 1)
            if record["partName"] == "球体":
                offset.y -= 0.12 * ball_reveal
                offset.z += 0.025 * ball_reveal
        elif group == "stemPackingDrive":
            offset.z += 0.145 * amount
            offset += radial * (0.052 * amount)
        elif group == "fastenersSmallHardware":
            offset += radial * (0.13 * amount)
            offset.z += math.copysign(0.035 * amount, local.z if abs(local.z) > 0.001 else 1)
        elif material == "machinedStainless":
            offset += radial * (0.052 * amount)

        obj.location = record["base_location"] + offset
        obj.rotation_euler = record["base_rotation"].copy()
        if record["partName"] == "球体":
            obj.rotation_euler.rotate_axis("Z", math.radians(28) * amount)

    bpy.context.view_layer.update()


def look_at(obj: bpy.types.Object, target) -> None:
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def add_area_light(name: str, location, target, power: float, size):
    light_data = bpy.data.lights.new(name, type="AREA")
    light_obj = bpy.data.objects.new(name, light_data)
    bpy.context.collection.objects.link(light_obj)
    light_obj.location = location
    look_at(light_obj, target)
    light_data.energy = power
    if isinstance(size, (tuple, list)):
        light_data.shape = "RECTANGLE"
        light_data.size = size[0]
        light_data.size_y = size[1]
    else:
        light_data.size = size
    return light_obj


def add_plane(name: str, material: bpy.types.Material, location, scale, rotation=(0, 0, 0), camera_visible=True):
    bpy.ops.mesh.primitive_plane_add(size=1, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(material)
    if hasattr(obj, "visible_camera"):
        obj.visible_camera = camera_visible
    return obj


def build_studio(materials: dict, hdri_path: Path | None = None) -> None:
    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    if hdri_path and hdri_path.is_file():
        world.use_nodes = True
        nodes = world.node_tree.nodes
        background = nodes.get("Background")
        if background:
            environment = nodes.new(type="ShaderNodeTexEnvironment")
            environment.image = bpy.data.images.load(str(hdri_path))
            world.node_tree.links.new(environment.outputs["Color"], background.inputs["Color"])
            background.inputs["Strength"].default_value = 0.18
    else:
        world.color = (0.76, 0.77, 0.75)

    add_plane(
        "goal20_matte_floor",
        materials["studioWhite"],
        (0, 0, -0.175),
        (4.2, 3.0, 1),
    )
    add_plane(
        "goal20_rear_soft_reflection_wall",
        materials["studioWhite"],
        (0.0, 0.78, 0.54),
        (4.1, 1.55, 1),
        rotation=(math.radians(74), 0, 0),
    )
    add_plane(
        "goal20_left_grey_reflection_card",
        materials["reflectionGrey"],
        (-1.55, -0.20, 0.40),
        (0.42, 1.55, 1),
        rotation=(0, math.radians(76), math.radians(14)),
        camera_visible=False,
    )
    add_plane(
        "goal20_right_grey_reflection_card",
        materials["reflectionGrey"],
        (1.42, 0.24, 0.36),
        (0.36, 1.30, 1),
        rotation=(0, math.radians(-76), math.radians(-14)),
        camera_visible=False,
    )

    add_area_light("goal20_left_large_softbox", (-1.42, -1.62, 1.28), (0, 0, 0.08), 270, 2.7)
    add_area_light("goal20_top_strip_highlight", (0.05, -0.38, 1.68), (0, 0, 0.04), 160, (0.24, 2.15))
    add_area_light("goal20_front_low_fill", (0.25, -1.22, 0.30), (0, 0, 0.02), 24, 1.15)
    add_area_light("goal20_right_rim_softbox", (1.28, 0.56, 0.88), (0, 0, 0.04), 105, 1.35)


def create_camera() -> bpy.types.Object:
    camera_data = bpy.data.cameras.new("goal20_cycles_camera")
    camera_obj = bpy.data.objects.new("goal20_cycles_camera", camera_data)
    bpy.context.collection.objects.link(camera_obj)
    bpy.context.scene.camera = camera_obj
    camera_data.sensor_width = 36
    camera_data.dof.use_dof = False
    return camera_obj


def render_stills(repo_root: Path, out_dir: Path, records: list, camera: bpy.types.Object):
    stills = []
    for setup in CAMERA_SETUPS:
        apply_state(records, setup["stateId"])
        if "targetPart" in setup:
            matches = [record for record in records if record["partName"] == setup["targetPart"]]
            if not matches:
                raise RuntimeError(f"No object matched targetPart={setup['targetPart']}")
            centers = [object_bounds(record["object"])[2] for record in matches]
            center = Vector((
                sum(point.x for point in centers) / len(centers),
                sum(point.y for point in centers) / len(centers),
                sum(point.z for point in centers) / len(centers),
            ))
            target = center + Vector(setup.get("targetOffset", (0, 0, 0)))
            camera.location = center + Vector(setup["cameraOffset"])
        else:
            target = Vector(setup["target"])
            camera.location = setup["camera"]
        camera.data.lens = setup["lensMm"]
        look_at(camera, target)
        output_path = out_dir / setup["filename"]
        bpy.context.scene.render.filepath = str(output_path)
        bpy.ops.render.render(write_still=True)
        stills.append(
            {
                "id": setup["id"],
                "stateId": setup["stateId"],
                "name": setup["name"],
                "purpose": setup["purpose"],
                "path": str(output_path.relative_to(repo_root)).replace("\\", "/"),
                "width": bpy.context.scene.render.resolution_x,
                "height": bpy.context.scene.render.resolution_y,
                "bytes": output_path.stat().st_size,
                "sha256": sha256(output_path),
            }
        )
    return stills


def write_index(goal_dir: Path, manifest: dict) -> None:
    cards = []
    for still in manifest["stills"]:
        cards.append(
            f"""
            <figure>
              <img src=\"{html.escape(still['path'].split('/goal20-blender-cycles-step-proof/')[-1])}\" alt=\"{html.escape(still['name'])}\">
              <figcaption><b>{html.escape(still['name'])}</b><span>{html.escape(still['purpose'])}</span></figcaption>
            </figure>
            """
        )
    html_text = f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>Goal 20 Blender/Cycles STEP Proof</title>
  <style>
    :root {{ color-scheme: light; font-family: Inter, \"Noto Sans SC\", system-ui, sans-serif; background: #f5f6f7; color: #111827; }}
    body {{ margin: 0; }}
    main {{ width: min(1440px, calc(100% - 40px)); margin: 0 auto; padding: 36px 0 56px; }}
    header {{ display: grid; gap: 10px; margin-bottom: 24px; }}
    .eyebrow {{ margin: 0; color: #5b6472; font-size: 13px; text-transform: uppercase; letter-spacing: .08em; }}
    h1 {{ margin: 0; font-size: clamp(28px, 4vw, 48px); line-height: 1.02; letter-spacing: 0; }}
    .summary {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin: 20px 0 30px; }}
    .metric {{ border: 1px solid #d9dde3; background: #fff; border-radius: 8px; padding: 14px 16px; }}
    .metric b {{ display: block; font-size: 22px; }}
    .metric span {{ color: #667085; font-size: 13px; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }}
    figure {{ margin: 0; border: 1px solid #d9dde3; background: #fff; border-radius: 8px; overflow: hidden; }}
    figure:first-child {{ grid-column: 1 / -1; }}
    img {{ display: block; width: 100%; height: auto; background: #e5e7eb; }}
    figcaption {{ display: grid; gap: 4px; padding: 12px 14px 14px; }}
    figcaption span {{ color: #667085; font-size: 13px; line-height: 1.45; }}
    code {{ background: #eef0f3; padding: 2px 5px; border-radius: 5px; }}
    @media (max-width: 820px) {{
      main {{ width: min(100% - 24px, 720px); padding-top: 24px; }}
      .summary, .grid {{ grid-template-columns: 1fr; }}
      figure:first-child {{ grid-column: auto; }}
    }}
  </style>
</head>
<body>
<main>
  <header>
    <p class=\"eyebrow\">Goal 20 / Blender Cycles / STEP-first proof</p>
    <h1>固定式球阀离线材质验证</h1>
    <p>这不是 hero 替换，也不是 240 帧序列；这里只验证 STEP 转换、零件分组、六类工业材质和 Cycles studio lighting 是否成立。</p>
  </header>
  <section class=\"summary\">
    <div class=\"metric\"><b>{manifest['renderProfile']['width']}x{manifest['renderProfile']['height']}</b><span>render size</span></div>
    <div class=\"metric\"><b>{manifest['partIdentity']['meshCount']}</b><span>STEP mesh instances</span></div>
    <div class=\"metric\"><b>{len(manifest['materialCounts'])}</b><span>material families</span></div>
    <div class=\"metric\"><b>{len(manifest['stills'])}</b><span>rendered stills</span></div>
  </section>
  <section class=\"grid\">
    {''.join(cards)}
  </section>
  <p>Manifest: <code>render-manifest.json</code>. Material map: <code>semantic-material-map.json</code>. Mesh: <code>goal20-step-mesh.glb</code>. Status: <a href=\"material-status.md\">material-status.md</a>.</p>
</main>
</body>
</html>
"""
    (goal_dir / "index.html").write_text(html_text, encoding="utf-8")


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    model_path = (repo_root / args.model).resolve()
    step_report_path = (repo_root / args.step_report).resolve()
    step_audit_path = (repo_root / args.step_audit).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    goal_dir = out_dir.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    step_report = read_json(step_report_path)
    step_audit = read_json(step_audit_path)

    clear_scene()
    render_profile = configure_render(args.profile)
    materials = {
        name: make_material(name, spec)
        for name, spec in MATERIAL_SPECS.items()
    }
    meshes = import_model(model_path)
    if not meshes:
        raise RuntimeError(f"No mesh objects imported from {model_path}")

    create_rig(meshes)
    records, group_counts, material_counts, part_counts = assign_materials(meshes, materials)
    hdri_path = (repo_root / args.hdri).resolve()
    build_studio(materials, hdri_path)
    camera = create_camera()
    stills = render_stills(repo_root, out_dir, records, camera)

    source_records = []
    for record in records:
        _min_v, _max_v, center, size = object_bounds(record["object"])
        source_records.append(
            {
                "sourceName": record["sourceName"],
                "partName": record["partName"],
                "group": record["group"],
                "material": record["material"],
                "center": [round(center.x, 6), round(center.y, 6), round(center.z, 6)],
                "size": [round(size.x, 6), round(size.y, 6), round(size.z, 6)],
            }
        )

    semantic_map = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": {
            "stepMesh": str(model_path.relative_to(repo_root)).replace("\\", "/"),
            "stepMeshSha256": sha256(model_path),
            "stepReport": str(step_report_path.relative_to(repo_root)).replace("\\", "/"),
            "stepAudit": str(step_audit_path.relative_to(repo_root)).replace("\\", "/"),
            "stepSourceSha256": step_report["source"]["sha256"],
            "stepProductNames": step_audit["productNames"],
        },
        "materialFamilies": {
            "castBlastedStainless": "investment cast stainless steel, bead-blasted / sandblasted satin finish",
            "machinedStainless": "machined stainless steel",
            "polishedStainlessBall": "mirror polished stainless steel ball",
            "graphitePacking": "graphite packing / dark sealing ring",
            "softSealPtfe": "PTFE / light soft seat visual treatment",
            "fastenerStainless": "stainless fasteners and small hardware",
        },
        "groupCounts": group_counts,
        "materialCounts": material_counts,
        "partCounts": part_counts,
        "records": source_records,
    }
    semantic_map_path = goal_dir / "semantic-material-map.json"
    write_json(semantic_map_path, semantic_map)

    manifest = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "goal": "Goal 20 Blender/Cycles STEP-first material proof",
        "renderer": "Blender Cycles",
        "profile": args.profile,
        "blender": bpy.app.version_string,
        "sourceBoundary": {
            "stepSource": step_report["source"]["path"],
            "stepSourceSha256": step_report["source"]["sha256"],
            "stepMesh": str(model_path.relative_to(repo_root)).replace("\\", "/"),
            "stepMeshSha256": sha256(model_path),
            "rule": "The homepage is not replaced, no 240-frame sequence is rendered, and material labels are visual treatments unless supplier evidence confirms exact grades.",
        },
        "lighting": {
            "hdri": str(hdri_path.relative_to(repo_root)).replace("\\", "/") if hdri_path.is_file() else None,
            "hdriSource": "Poly Haven studio_small_09 1K HDRI, CC0, used as studio reflection environment",
            "areaLights": [
                "goal20_left_large_softbox",
                "goal20_top_strip_highlight",
                "goal20_front_low_fill",
                "goal20_right_rim_softbox",
            ],
        },
        "renderProfile": {
            "width": render_profile["width"],
            "height": render_profile["height"],
            "samples": render_profile["samples"],
            "engine": "Cycles",
            "frameSequenceRendered": False,
            "fullReleaseFrameCount": 0,
            "homepageConnected": False,
        },
        "partIdentity": {
            "meshCount": len(meshes),
            "sourceStepProductNameCount": len(step_audit["productNames"]),
            "semanticMap": str(semantic_map_path.relative_to(repo_root)).replace("\\", "/"),
            "requiredFamiliesPresent": {
                material: material_counts.get(material, 0) > 0
                for material in (
                    "castBlastedStainless",
                    "machinedStainless",
                    "polishedStainlessBall",
                    "graphitePacking",
                    "softSealPtfe",
                    "fastenerStainless",
                )
            },
        },
        "groupCounts": group_counts,
        "materialCounts": material_counts,
        "partCounts": part_counts,
        "stills": stills,
        "constraints": [
            "Goal 20 validates the Blender/Cycles STEP-first minimum loop only.",
            "The STEP was converted to a Goal 20 dedicated GLB from the supplied STEP hash; the old fixed-ball-valve.glb is not overwritten.",
            "Material assignment uses supplier material descriptions as visual lookdev names, not certified alloy/coating claims.",
            "Explosion states are review choreography only and are not the final 240-frame assembly animation.",
        ],
    }
    manifest_path = goal_dir / "render-manifest.json"
    write_json(manifest_path, manifest)
    write_index(goal_dir, manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
