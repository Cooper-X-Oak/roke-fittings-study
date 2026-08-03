#!/usr/bin/env python3
"""Render Goal 25-D isolated valve-body material zoning proof.

This pass keeps the real STEP-derived valve body as one object, but assigns
different named stainless finish materials to inferred manufacturing zones:
cast/blasted shell, machined flange faces, brushed flange outer side, machined
bores, edge burnish, bolt-hole bores and dark groove roots.

Run inside Blender:
D:\\TOOLS\\render-pipeline\\apps\\Blender-5.2.0\\Blender Foundation\\Blender 5.2\\blender.exe --background --python scripts\\render_goal25d_zoned_body_materials.py -- --repo-root . --profile smoke
"""

from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import json
import math
import random
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    import bpy
    from mathutils import Vector
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Run this script with Blender's Python interpreter.") from exc


GOAL20_DIR = "docs/assets/ztovalve/hero/goal20-blender-cycles-step-proof"
GOAL25D_DIR = "docs/assets/ztovalve/hero/goal25d-zoned-body-material-proof"
RANDOM_SEED = 250503

REFERENCE_NOTES = [
    {
        "id": "adobe-pbr-metal-roughness",
        "title": "Adobe Substance 3D - The PBR Guide",
        "url": "https://www.adobe.com/learn/substance-3d-designer/web/the-pbr-guide-part-2",
        "takeaway": "Keep metalness, roughness, normal/height and base reflection values separated; do not fake rough stainless by whitening diffuse color.",
    },
    {
        "id": "openpbr-layering",
        "title": "OpenPBR Surface Specification",
        "url": "https://academysoftwarefoundation.github.io/OpenPBR/",
        "takeaway": "Use layered base/coat/roughness/normal/tangent controls for real material behavior instead of one monolithic shader.",
    },
    {
        "id": "bssa-blasted-finish",
        "title": "BSSA - Bead and shot blasted stainless steel finishes",
        "url": "https://bssa.org.uk/bssa_articles/specifying-bead-and-shot-blasted-stainless-steel-finishes-and-their-applications/",
        "takeaway": "Blasted stainless is a non-directional low-reflective satin finish, not a powder-white coating.",
    },
    {
        "id": "bssa-mechanical-finish",
        "title": "BSSA - Mechanically polished, brushed and buffed stainless finishes",
        "url": "https://bssa.org.uk/bssa_articles/specifying-mechanically-polished-brushed-and-buffed-stainless-steel-finishes-and-their-applications/",
        "takeaway": "Machined, brushed and polished zones need named finish intent, abrasive direction and surface quality boundaries.",
    },
    {
        "id": "casting-source-surface-texture",
        "title": "Casting Source - Surface finish requirements and inspection",
        "url": "https://www.castingsource.com/articles/2024/11/21/surface-finish-requirements-and-inspection",
        "takeaway": "Casting texture should be treated as roughness, waviness and lay produced by process plus finishing, not as uniform noise.",
    },
]

ZONE_SPECS = [
    {
        "id": "G25-SS-CAST-BLASTED-SATIN-01",
        "label": "cast blasted satin shell",
        "cn": "阀体主壳/柱体",
        "intent": "investment-cast stainless body, bead/sand blasted satin, non-directional, metal reflection retained",
        "debug": (0.34, 0.53, 0.72, 1.0),
        "material": {
            "base_color": (0.33, 0.35, 0.32, 1.0),
            "roughness": 0.45,
            "anisotropic": 0.22,
            "coat": 0.018,
            "texture": "cast_noise",
            "roughness_variation": (0.40, 0.56),
            "roughness_noise_scale": 420,
            "roughness_noise_detail": 14,
            "bump": 0.0065,
            "bump_distance": 0.0011,
            "bump_scale": 880,
            "bump_detail": 15,
        },
    },
    {
        "id": "G25-SS-MACH-FLANGE-RADIAL-01",
        "label": "machined radial flange face",
        "cn": "法兰正面",
        "intent": "flat machined flange face with restrained explicit concentric tool-path trace migrated from Goal 25-C",
        "debug": (0.86, 0.78, 0.28, 1.0),
        "material": {
            "base_color": (0.52, 0.54, 0.50, 1.0),
            "roughness": 0.29,
            "anisotropic": 0.70,
            "coat": 0.055,
            "texture": "none",
            "roughness_variation": None,
            "bump": 0.0,
        },
    },
    {
        "id": "G25-SS-BRUSH-NO4-LINEAR-01",
        "label": "brushed no.4 flange side",
        "cn": "法兰外圆侧面",
        "intent": "brushed/satin stainless on flange outside diameter, directional but still industrial",
        "debug": (0.45, 0.72, 0.38, 1.0),
        "material": {
            "base_color": (0.46, 0.48, 0.44, 1.0),
            "roughness": 0.34,
            "anisotropic": 0.82,
            "coat": 0.035,
            "texture": "none",
            "roughness_variation": None,
            "bump": 0.0,
        },
    },
    {
        "id": "G25-SS-MACH-BORE-CIRCULAR-01",
        "label": "machined circular bore",
        "cn": "内孔/流道入口",
        "intent": "darker cylindrical machined bore with restrained circumferential cutting trace migrated from Goal 25-C",
        "debug": (0.82, 0.44, 0.34, 1.0),
        "material": {
            "base_color": (0.32, 0.34, 0.31, 1.0),
            "roughness": 0.31,
            "anisotropic": 0.74,
            "coat": 0.040,
            "texture": "none",
            "roughness_variation": None,
            "bump": 0.0,
        },
    },
    {
        "id": "G25-SS-EDGE-BURNISH-01",
        "label": "edge burnish",
        "cn": "倒角/棱线/凸筋高点",
        "intent": "thin brighter worn edges and bevel highlights from handling or final deburring",
        "debug": (0.96, 0.96, 0.88, 1.0),
        "material": {
            "base_color": (0.56, 0.58, 0.54, 1.0),
            "roughness": 0.24,
            "anisotropic": 0.48,
            "coat": 0.080,
            "texture": "none",
            "bump": 0.0010,
            "bump_distance": 0.0004,
        },
    },
    {
        "id": "G25-SS-MACH-BOLT-BORE-DARK-01",
        "label": "dark machined bolt bore",
        "cn": "螺栓孔内壁",
        "intent": "smaller darker, rougher machined cylindrical walls with local rim and inside-ring witness traces",
        "debug": (0.62, 0.42, 0.74, 1.0),
        "material": {
            "base_color": (0.24, 0.26, 0.24, 1.0),
            "roughness": 0.43,
            "anisotropic": 0.58,
            "coat": 0.018,
            "texture": "none",
            "roughness_variation": None,
            "bump": 0.0,
        },
    },
    {
        "id": "G25-SS-ROOT-DARK-AO-01",
        "label": "dark groove root",
        "cn": "凹槽根部",
        "intent": "dark reflection-retaining metal in shoulder grooves and root transitions; explicitly not lifted to powder white",
        "debug": (0.20, 0.22, 0.23, 1.0),
        "material": {
            "base_color": (0.28, 0.30, 0.28, 1.0),
            "roughness": 0.54,
            "anisotropic": 0.18,
            "coat": 0.010,
            "texture": "cast_noise",
            "roughness_variation": (0.48, 0.62),
            "roughness_noise_scale": 240,
            "roughness_noise_detail": 12,
            "bump": 0.0045,
            "bump_distance": 0.0009,
            "bump_scale": 760,
            "bump_detail": 12,
        },
    },
]

ZONE_INDEX = {spec["id"]: index for index, spec in enumerate(ZONE_SPECS)}

STUDIO_MATERIALS = {
    "floorGrey": {"base_color": (0.30, 0.31, 0.30, 1.0), "roughness": 0.88},
    "softPanel": {"base_color": (0.74, 0.75, 0.71, 1.0), "roughness": 0.68},
    "charcoalFlag": {"base_color": (0.026, 0.028, 0.027, 1.0), "roughness": 0.80},
}

TRACE_MATERIAL_SPECS = {
    "traceBright": {
        "base_color": (0.54, 0.56, 0.52, 1.0),
        "metallic": 1.0,
        "roughness": 0.34,
        "anisotropic": 0.55,
        "coat": 0.026,
    },
    "traceDark": {
        "base_color": (0.39, 0.41, 0.38, 1.0),
        "metallic": 1.0,
        "roughness": 0.66,
        "anisotropic": 0.25,
        "coat": 0.006,
    },
}

MIGRATED_TRACE_IDS = [
    "G25-TRACE-MACH-FLANGE-RADIAL-GEOM-01",
    "G25-TRACE-MACH-BORE-CIRCULAR-GEOM-01",
    "G25-TRACE-MACH-BOLT-BORE-DARK-GEOM-01",
]


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    args = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--model", default=f"{GOAL20_DIR}/goal20-step-mesh.glb")
    parser.add_argument("--step-report", default=f"{GOAL20_DIR}/step-mesh-report.json")
    parser.add_argument("--semantic-map", default=f"{GOAL20_DIR}/semantic-material-map.json")
    parser.add_argument("--hdri", default=f"{GOAL20_DIR}/studio_small_09_1k.hdr")
    parser.add_argument("--out-dir", default=f"{GOAL25D_DIR}/stills")
    parser.add_argument("--profile", choices=["smoke", "proof"], default="smoke")
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
    write_text_lf(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def write_text_lf(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file:
        file.write(text)


def load_goal20_module(repo_root: Path):
    script_path = repo_root / "scripts" / "render_goal20_blender_step_proof.py"
    spec = importlib.util.spec_from_file_location("goal20_render_helpers", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def set_input(node, names: list[str], value) -> None:
    for name in names:
        if name in node.inputs:
            node.inputs[name].default_value = value
            return


def make_simple_material(name: str, spec: dict) -> bpy.types.Material:
    material = bpy.data.materials.new(f"goal25d_{name}")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    principled = nodes.get("Principled BSDF")
    if principled:
        set_input(principled, ["Base Color"], spec["base_color"])
        set_input(principled, ["Metallic"], spec.get("metallic", 0.0))
        set_input(principled, ["Roughness"], spec.get("roughness", 0.8))
    material.diffuse_color = spec["base_color"]
    return material


def make_trace_material(name: str, spec: dict) -> bpy.types.Material:
    material = bpy.data.materials.new(f"goal25d_{name}")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    principled = nodes.get("Principled BSDF")
    if principled:
        set_input(principled, ["Base Color"], spec["base_color"])
        set_input(principled, ["Metallic"], spec.get("metallic", 1.0))
        set_input(principled, ["Roughness"], spec.get("roughness", 0.5))
        set_input(principled, ["Coat Weight", "Clearcoat"], spec.get("coat", 0.0))
        set_input(principled, ["Coat Roughness", "Clearcoat Roughness"], 0.18)
        set_input(principled, ["Anisotropic IOR Level", "Anisotropic"], spec.get("anisotropic", 0.0))
    material.diffuse_color = spec["base_color"]
    return material


def make_debug_material(spec: dict) -> bpy.types.Material:
    material = bpy.data.materials.new(f"debug_{spec['id']}")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    output = nodes.new(type="ShaderNodeOutputMaterial")
    emission = nodes.new(type="ShaderNodeEmission")
    emission.inputs["Color"].default_value = spec["debug"]
    emission.inputs["Strength"].default_value = 1.0
    material.node_tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    material.diffuse_color = spec["debug"]
    return material


def make_zone_material(spec: dict) -> bpy.types.Material:
    params = spec["material"]
    material = bpy.data.materials.new(spec["id"])
    material.use_nodes = True
    nodes = material.node_tree.nodes
    principled = nodes.get("Principled BSDF")
    if not principled:
        material.diffuse_color = params["base_color"]
        return material

    set_input(principled, ["Base Color"], params["base_color"])
    set_input(principled, ["Metallic"], 1.0)
    set_input(principled, ["Roughness"], params["roughness"])
    set_input(principled, ["Coat Weight", "Clearcoat"], params.get("coat", 0.0))
    set_input(principled, ["Coat Roughness", "Clearcoat Roughness"], 0.18)
    set_input(principled, ["Anisotropic IOR Level", "Anisotropic"], params.get("anisotropic", 0.0))

    low_high = params.get("roughness_variation")
    if low_high:
        texture = make_height_texture(nodes, params)
        ramp = nodes.new(type="ShaderNodeValToRGB")
        low, high = low_high
        ramp.color_ramp.elements[0].position = 0.18
        ramp.color_ramp.elements[0].color = (low, low, low, 1.0)
        ramp.color_ramp.elements[1].position = 1.0
        ramp.color_ramp.elements[1].color = (high, high, high, 1.0)
        material.node_tree.links.new(texture, ramp.inputs["Fac"])
        material.node_tree.links.new(ramp.outputs["Color"], principled.inputs["Roughness"])

    if params.get("bump", 0.0) > 0:
        texture = make_height_texture(nodes, params)
        bump = nodes.new(type="ShaderNodeBump")
        bump.inputs["Strength"].default_value = params["bump"]
        bump.inputs["Distance"].default_value = params.get("bump_distance", 0.001)
        material.node_tree.links.new(texture, bump.inputs["Height"])
        material.node_tree.links.new(bump.outputs["Normal"], principled.inputs["Normal"])

    material.diffuse_color = params["base_color"]
    return material


def make_height_texture(nodes, params: dict):
    texture_type = params.get("texture", "none")
    if texture_type == "radial_wave":
        wave = nodes.new(type="ShaderNodeTexWave")
        wave.wave_type = "RINGS"
        if hasattr(wave, "rings_direction"):
            wave.rings_direction = "X"
        wave.inputs["Scale"].default_value = params.get("wave_scale", 70)
        wave.inputs["Distortion"].default_value = params.get("wave_distortion", 5.0)
        return wave.outputs["Fac"]
    if texture_type == "linear_wave":
        wave = nodes.new(type="ShaderNodeTexWave")
        wave.wave_type = "BANDS"
        if hasattr(wave, "bands_direction"):
            wave.bands_direction = "Z"
        wave.inputs["Scale"].default_value = params.get("wave_scale", 70)
        wave.inputs["Distortion"].default_value = params.get("wave_distortion", 2.5)
        return wave.outputs["Fac"]
    noise = nodes.new(type="ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = params.get("bump_scale", params.get("roughness_noise_scale", 300))
    noise.inputs["Detail"].default_value = params.get("bump_detail", params.get("roughness_noise_detail", 12))
    noise.inputs["Roughness"].default_value = 0.58
    return noise.outputs["Fac"]


def configure_render(profile: str) -> dict:
    profiles = {
        "smoke": {"width": 1200, "height": 675, "samples": 40},
        "proof": {"width": 2200, "height": 1238, "samples": 112},
    }
    selected = profiles[profile]
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = selected["samples"]
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 10
    scene.cycles.diffuse_bounces = 3
    scene.cycles.glossy_bounces = 7
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
    scene.view_settings.exposure = -0.86
    scene.view_settings.gamma = 1.0
    try:
        scene.cycles.device = "GPU"
    except Exception:
        scene.cycles.device = "CPU"
    return selected


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
    if not camera_visible:
        if hasattr(obj, "cycles_visibility"):
            obj.cycles_visibility.camera = False
            obj.cycles_visibility.shadow = False
            obj.cycles_visibility.diffuse = False
            obj.cycles_visibility.glossy = True
            obj.cycles_visibility.transmission = False
            obj.cycles_visibility.scatter = False
        for attr, value in (
            ("visible_camera", False),
            ("visible_shadow", False),
            ("visible_diffuse", False),
            ("visible_glossy", True),
            ("visible_transmission", False),
            ("visible_volume_scatter", False),
        ):
            if hasattr(obj, attr):
                setattr(obj, attr, value)
    return obj


def build_studio(studio_materials: dict, hdri_path: Path | None) -> None:
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
            background.inputs["Strength"].default_value = 0.095
    else:
        world.color = (0.32, 0.33, 0.32)

    add_plane("goal25d_floor_reflection_only", studio_materials["floorGrey"], (0.0, 0.0, -0.72), (4.4, 2.6, 1), camera_visible=False)
    add_plane(
        "goal25d_rear_reflection_only",
        studio_materials["floorGrey"],
        (0.0, 0.78, 0.62),
        (4.4, 1.7, 1),
        rotation=(math.radians(73), 0, 0),
        camera_visible=False,
    )
    add_plane(
        "goal25d_left_white_panel",
        studio_materials["softPanel"],
        (-1.72, -0.34, 0.56),
        (0.76, 2.05, 1),
        rotation=(0, math.radians(72), math.radians(6)),
        camera_visible=False,
    )
    add_plane(
        "goal25d_top_white_strip",
        studio_materials["softPanel"],
        (0.0, -0.54, 1.38),
        (2.7, 0.25, 1),
        rotation=(math.radians(82), 0, 0),
        camera_visible=False,
    )
    add_plane(
        "goal25d_right_charcoal_flag",
        studio_materials["charcoalFlag"],
        (1.55, -0.12, 0.54),
        (0.68, 2.05, 1),
        rotation=(0, math.radians(-74), math.radians(-7)),
        camera_visible=False,
    )
    add_plane(
        "goal25d_low_charcoal_flag",
        studio_materials["charcoalFlag"],
        (-0.12, -0.48, -0.08),
        (2.35, 0.26, 1),
        rotation=(math.radians(80), 0, math.radians(1)),
        camera_visible=False,
    )

    add_area_light("goal25d_left_large_softbox", (-1.68, -1.62, 1.22), (0, 0, 0.12), 220, 3.1)
    add_area_light("goal25d_top_long_softbox", (0.0, -0.54, 1.74), (0, 0, 0.18), 128, (0.28, 2.9))
    add_area_light("goal25d_right_edge_softbox", (1.46, 0.52, 0.86), (0, 0, 0.02), 58, 1.75)
    add_area_light("goal25d_front_low_fill", (0.20, -1.34, 0.24), (0, 0, 0.02), 6, 1.35)


def isolate_body_mesh(goal20, meshes: list[bpy.types.Object]) -> tuple[bpy.types.Object, dict]:
    body_records = []
    for obj in meshes:
        source_name = goal20.strip_blender_suffix(obj.name)
        part_name = goal20.recover_part_name(source_name)
        if part_name == "阀体":
            min_v, max_v, center, size = goal20.object_bounds(obj)
            body_records.append(
                {
                    "object": obj,
                    "sourceName": source_name,
                    "partName": part_name,
                    "center": center,
                    "size": size,
                    "min": min_v,
                    "max": max_v,
                }
            )
    if len(body_records) != 1:
        raise RuntimeError(f"Expected exactly one 阀体 mesh, found {len(body_records)}")

    body = body_records[0]["object"]
    for obj in list(meshes):
        if obj is not body:
            bpy.data.objects.remove(obj, do_unlink=True)

    bpy.context.view_layer.update()
    _min_v, _max_v, center, _size = goal20.object_bounds(body)
    body.location -= center
    body.rotation_euler.rotate_axis("Z", math.radians(-7))
    bpy.context.view_layer.update()
    _min_v, _max_v, centered_center, centered_size = goal20.object_bounds(body)
    return body, {
        "sourceName": body_records[0]["sourceName"],
        "partName": body_records[0]["partName"],
        "originalCenter": [round(v, 6) for v in body_records[0]["center"]],
        "originalSize": [round(v, 6) for v in body_records[0]["size"]],
        "centeredCenter": [round(v, 6) for v in centered_center],
        "centeredSize": [round(v, 6) for v in centered_size],
    }


def mesh_local_metrics(mesh: bpy.types.Mesh) -> dict:
    axes = "xyz"
    coords = [vertex.co.copy() for vertex in mesh.vertices]
    mins = [min(getattr(coord, axis) for coord in coords) for axis in axes]
    maxs = [max(getattr(coord, axis) for coord in coords) for axis in axes]
    centers = [(mins[index] + maxs[index]) * 0.5 for index in range(3)]
    sizes = [maxs[index] - mins[index] for index in range(3)]
    return {"axes": axes, "coords": coords, "mins": mins, "maxs": maxs, "centers": centers, "sizes": sizes}


def infer_flow_axis(mesh: bpy.types.Mesh, metrics: dict) -> tuple[int, dict]:
    axes = metrics["axes"]
    coords = metrics["coords"]
    mins = metrics["mins"]
    maxs = metrics["maxs"]
    sizes = metrics["sizes"]
    scores = []
    for axis_index, axis_name in enumerate(axes):
        band = sizes[axis_index] * 0.08
        side_areas = []
        for label, limit in (("min", mins[axis_index]), ("max", maxs[axis_index])):
            area = 0.0
            for polygon in mesh.polygons:
                center = polygon_center(mesh, coords, polygon)
                coord = getattr(center, axis_name)
                normal_axis = abs(getattr(polygon.normal, axis_name))
                near_side = coord < limit + band if label == "min" else coord > limit - band
                if near_side and normal_axis > 0.72:
                    area += polygon.area
            side_areas.append(area)
        combined = sum(side_areas)
        score = combined + min(side_areas) * 1.5
        scores.append({"axis": axis_name, "index": axis_index, "sideAreas": side_areas, "score": score})
    selected = max(scores, key=lambda item: item["score"])
    return selected["index"], {"scores": scores, "selectedAxis": selected["axis"]}


def polygon_center(mesh: bpy.types.Mesh, coords: list[Vector], polygon: bpy.types.MeshPolygon) -> Vector:
    return sum((coords[index] for index in polygon.vertices), Vector()) / len(polygon.vertices)


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * fraction)))
    return ordered[index]


def assign_zone_materials(body: bpy.types.Object, materials: list[bpy.types.Material]) -> dict:
    mesh = body.data
    mesh.materials.clear()
    for material in materials:
        mesh.materials.append(material)

    metrics = mesh_local_metrics(mesh)
    flow_axis, axis_report = infer_flow_axis(mesh, metrics)
    axes = metrics["axes"]
    coords = metrics["coords"]
    mins = metrics["mins"]
    maxs = metrics["maxs"]
    centers = metrics["centers"]
    sizes = metrics["sizes"]
    radial_axes = [index for index in range(3) if index != flow_axis]
    flow_name = axes[flow_axis]
    band = sizes[flow_axis] * 0.13
    shoulder_band = sizes[flow_axis] * 0.11

    end_face_radii = []
    for polygon in mesh.polygons:
        center = polygon_center(mesh, coords, polygon)
        radius = radial_radius(center, axes, centers, radial_axes)
        coord = getattr(center, flow_name)
        normal_axis = abs(getattr(polygon.normal, flow_name))
        near_end = coord < mins[flow_axis] + band or coord > maxs[flow_axis] - band
        if near_end and normal_axis > 0.72:
            end_face_radii.append(radius)

    inner_radius = percentile(end_face_radii, 0.08) * 0.96
    outer_radius = percentile(end_face_radii, 0.96) * 1.02
    if not inner_radius or not outer_radius:
        inner_radius = max(sizes[radial_axes[0]], sizes[radial_axes[1]]) * 0.28
        outer_radius = max(sizes[radial_axes[0]], sizes[radial_axes[1]]) * 0.50

    counts: Counter[str] = Counter()
    areas: dict[str, float] = defaultdict(float)
    zone_examples: dict[str, list[list[float]]] = defaultdict(list)

    for polygon in mesh.polygons:
        center = polygon_center(mesh, coords, polygon)
        radius = radial_radius(center, axes, centers, radial_axes)
        flow_coord = getattr(center, flow_name)
        normal_axis = abs(getattr(polygon.normal, flow_name))
        min_distance = flow_coord - mins[flow_axis]
        max_distance = maxs[flow_axis] - flow_coord
        distance_to_end = min(min_distance, max_distance)
        near_end = distance_to_end < band
        in_shoulder = band <= distance_to_end <= band + shoulder_band

        zone_id = "G25-SS-CAST-BLASTED-SATIN-01"

        if near_end and (radius < inner_radius * 1.22) and normal_axis < 0.60:
            zone_id = "G25-SS-MACH-BORE-CIRCULAR-01"
        elif near_end and inner_radius * 1.15 < radius < outer_radius * 0.86 and normal_axis < 0.52:
            zone_id = "G25-SS-MACH-BOLT-BORE-DARK-01"
        elif near_end and normal_axis > 0.34 and radius > inner_radius * 0.90:
            zone_id = "G25-SS-MACH-FLANGE-RADIAL-01"
        elif near_end and (radius < inner_radius * 1.06 or radius > outer_radius * 0.94) and 0.24 < normal_axis < 0.78:
            zone_id = "G25-SS-EDGE-BURNISH-01"
        elif near_end and radius > outer_radius * 0.86 and normal_axis < 0.68:
            zone_id = "G25-SS-BRUSH-NO4-LINEAR-01"
        elif (
            in_shoulder
            and outer_radius * 0.74 < radius < outer_radius * 0.99
            and normal_axis < 0.46
            and polygon.area < 0.000018
        ):
            zone_id = "G25-SS-ROOT-DARK-AO-01"

        polygon.material_index = ZONE_INDEX[zone_id]
        counts[zone_id] += 1
        areas[zone_id] += polygon.area
        if len(zone_examples[zone_id]) < 5:
            zone_examples[zone_id].append([round(center.x, 5), round(center.y, 5), round(center.z, 5)])

    edge_bevel = body.modifiers.new("goal25d_edge_burnish_micro_bevel", "BEVEL")
    edge_bevel.width = 0.00070
    edge_bevel.segments = 2
    edge_bevel.affect = "EDGES"
    if hasattr(edge_bevel, "material"):
        edge_bevel.material = ZONE_INDEX["G25-SS-EDGE-BURNISH-01"]
    weighted = body.modifiers.new("goal25d_weighted_normals", "WEIGHTED_NORMAL")
    weighted.keep_sharp = True

    mesh.update()
    return {
        "flowAxis": flow_name,
        "axisInference": axis_report,
        "localBounds": {
            "min": [round(value, 6) for value in mins],
            "max": [round(value, 6) for value in maxs],
            "center": [round(value, 6) for value in centers],
            "size": [round(value, 6) for value in sizes],
        },
        "radialAxes": [axes[index] for index in radial_axes],
        "innerRadiusEstimate": round(inner_radius, 6),
        "outerRadiusEstimate": round(outer_radius, 6),
        "zoneCounts": dict(counts),
        "zoneAreas": {zone_id: round(area, 8) for zone_id, area in areas.items()},
        "zoneExamples": dict(zone_examples),
        "classificationRule": [
            "Infer the main flow axis from the largest paired planar end-face area.",
            "Classify end planar rings as machined radial flange faces.",
            "Classify central low-radius cylindrical surfaces as machined bores.",
            "Classify smaller non-planar end-band holes as darker bolt bores.",
            "Classify outside flange side walls as brushed No.4/satin side finish.",
            "Classify shoulder bands as dark groove/root reflection zones.",
            "Use a bevel modifier with edge-burnish material for thin worn highlights.",
        ],
    }


def add_poly_curve_local(
    name: str,
    points: list[tuple[float, float, float]],
    material: bpy.types.Material,
    bevel_depth: float,
    parent: bpy.types.Object,
    resolution: int = 2,
) -> bpy.types.Object:
    curve = bpy.data.curves.new(name, type="CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = resolution
    curve.bevel_depth = bevel_depth
    curve.bevel_resolution = 2
    spline = curve.splines.new(type="POLY")
    spline.points.add(len(points) - 1)
    for point, coord in zip(spline.points, points):
        point.co = (coord[0], coord[1], coord[2], 1.0)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    obj.parent = parent
    obj.matrix_parent_inverse.identity()
    return obj


def point_on_flow_plane(
    axes: str,
    flow_axis: int,
    radial_axes: list[int],
    center: list[float],
    flow_coord: float,
    radius: float,
    theta: float,
) -> tuple[float, float, float]:
    coord = [center[0], center[1], center[2]]
    coord[flow_axis] = flow_coord
    coord[radial_axes[0]] = center[radial_axes[0]] + math.cos(theta) * radius
    coord[radial_axes[1]] = center[radial_axes[1]] + math.sin(theta) * radius
    return (coord[0], coord[1], coord[2])


def angle_delta(a: float, b: float) -> float:
    return abs((a - b + math.pi) % math.tau - math.pi)


def angle_inside_gap(theta: float, gaps: list[tuple[float, float]]) -> bool:
    return any(angle_delta(theta, center) < width for center, width in gaps)


def add_gapped_ring_local(
    name: str,
    axes: str,
    flow_axis: int,
    radial_axes: list[int],
    center: list[float],
    flow_coord: float,
    radius: float,
    gaps: list[tuple[float, float]],
    material: bpy.types.Material,
    bevel_depth: float,
    parent: bpy.types.Object,
    rng: random.Random,
    steps: int = 192,
    wobble: float = 0.0,
) -> list[bpy.types.Object]:
    objects = []
    segment: list[tuple[float, float, float]] = []
    phase = rng.random() * math.tau
    wave = rng.choice((2.0, 3.0, 4.0))
    for step in range(steps + 1):
        theta = math.tau * step / steps
        if angle_inside_gap(theta, gaps):
            if len(segment) >= 3:
                objects.append(
                    add_poly_curve_local(
                        f"{name}_seg_{len(objects):02d}",
                        segment,
                        material,
                        bevel_depth,
                        parent,
                    )
                )
            segment = []
            continue
        local_radius = radius + math.sin(theta * wave + phase) * wobble
        segment.append(point_on_flow_plane(axes, flow_axis, radial_axes, center, flow_coord, local_radius, theta))
    if len(segment) >= 3:
        objects.append(add_poly_curve_local(f"{name}_seg_{len(objects):02d}", segment, material, bevel_depth, parent))
    return objects


def collect_bolt_hole_clusters(
    mesh: bpy.types.Mesh,
    metrics: dict,
    flow_axis: int,
    radial_axes: list[int],
    side_label: str,
    side_coord: float,
    band: float,
    inner_radius: float,
    outer_radius: float,
) -> list[dict]:
    axes = metrics["axes"]
    coords = metrics["coords"]
    centers = metrics["centers"]
    flow_name = axes[flow_axis]
    bolt_index = ZONE_INDEX["G25-SS-MACH-BOLT-BORE-DARK-01"]
    samples = []
    for polygon in mesh.polygons:
        if polygon.material_index != bolt_index:
            continue
        center = polygon_center(mesh, coords, polygon)
        flow_coord = getattr(center, flow_name)
        if abs(flow_coord - side_coord) > band:
            continue
        first = getattr(center, axes[radial_axes[0]]) - centers[radial_axes[0]]
        second = getattr(center, axes[radial_axes[1]]) - centers[radial_axes[1]]
        theta = math.atan2(second, first) % math.tau
        samples.append({"center": center, "theta": theta})

    if len(samples) < 12:
        bolt_circle = inner_radius + (outer_radius - inner_radius) * 0.62
        return [
            {
                "theta": math.tau * index / 6 + math.radians(12),
                "center": point_on_flow_plane(axes, flow_axis, radial_axes, centers, side_coord, bolt_circle, math.tau * index / 6 + math.radians(12)),
                "radius": outer_radius * 0.085,
                "sampleCount": 0,
                "side": side_label,
            }
            for index in range(6)
        ]

    samples.sort(key=lambda item: item["theta"])
    gaps = []
    for index, sample in enumerate(samples):
        next_theta = samples[(index + 1) % len(samples)]["theta"]
        if index == len(samples) - 1:
            next_theta += math.tau
        gaps.append(next_theta - sample["theta"])
    start_index = (max(range(len(gaps)), key=lambda index: gaps[index]) + 1) % len(samples)

    ordered = samples[start_index:] + samples[:start_index]
    previous = ordered[0]["theta"]
    if start_index:
        for sample in ordered:
            if sample["theta"] < previous:
                sample["theta"] += math.tau
            previous = sample["theta"]

    clusters: list[list[dict]] = []
    current: list[dict] = []
    previous_theta = None
    for sample in ordered:
        if previous_theta is not None and sample["theta"] - previous_theta > 0.34:
            clusters.append(current)
            current = []
        current.append(sample)
        previous_theta = sample["theta"]
    if current:
        clusters.append(current)

    records = []
    for cluster in clusters:
        if len(cluster) < 5:
            continue
        y_value = sum(getattr(sample["center"], axes[radial_axes[0]]) for sample in cluster) / len(cluster)
        z_value = sum(getattr(sample["center"], axes[radial_axes[1]]) for sample in cluster) / len(cluster)
        flow_value = sum(getattr(sample["center"], flow_name) for sample in cluster) / len(cluster)
        local_center = [centers[0], centers[1], centers[2]]
        local_center[flow_axis] = flow_value
        local_center[radial_axes[0]] = y_value
        local_center[radial_axes[1]] = z_value
        distances = []
        for sample in cluster:
            dy = getattr(sample["center"], axes[radial_axes[0]]) - y_value
            dz = getattr(sample["center"], axes[radial_axes[1]]) - z_value
            distances.append(math.sqrt(dy * dy + dz * dz))
        radius = max(outer_radius * 0.055, min(outer_radius * 0.14, percentile(distances, 0.82)))
        theta = math.atan2(z_value - centers[radial_axes[1]], y_value - centers[radial_axes[0]]) % math.tau
        records.append(
            {
                "theta": theta,
                "center": (local_center[0], local_center[1], local_center[2]),
                "radius": radius,
                "sampleCount": len(cluster),
                "side": side_label,
            }
        )

    return sorted(records, key=lambda item: item["theta"])


def build_migrated_trace_geometry(
    body: bpy.types.Object,
    zone_assignment: dict,
    trace_materials: dict[str, bpy.types.Material],
) -> dict:
    rng = random.Random(RANDOM_SEED + 25)
    mesh = body.data
    metrics = mesh_local_metrics(mesh)
    axes = metrics["axes"]
    mins = metrics["mins"]
    maxs = metrics["maxs"]
    centers = metrics["centers"]
    sizes = metrics["sizes"]
    flow_axis = axes.index(zone_assignment["flowAxis"])
    radial_axes = [index for index in range(3) if index != flow_axis]
    inner_radius = zone_assignment["innerRadiusEstimate"]
    outer_radius = zone_assignment["outerRadiusEstimate"]
    band = sizes[flow_axis] * 0.13
    plane_offset = 0.00085
    trace_objects: list[bpy.types.Object] = []
    sides = [
        {"label": "min", "coord": mins[flow_axis], "sign": -1.0},
        {"label": "max", "coord": maxs[flow_axis], "sign": 1.0},
    ]

    side_holes: dict[str, list[dict]] = {}
    for side in sides:
        side_holes[side["label"]] = collect_bolt_hole_clusters(
            mesh,
            metrics,
            flow_axis,
            radial_axes,
            side["label"],
            side["coord"],
            band,
            inner_radius,
            outer_radius,
        )

    flange_segments = 0
    flange_ring_count = 9
    for side in sides:
        flow_coord = side["coord"] + side["sign"] * plane_offset
        holes = side_holes[side["label"]]
        for index in range(flange_ring_count):
            t = index / max(1, flange_ring_count - 1)
            radius = inner_radius * 1.12 + t * (outer_radius * 0.92 - inner_radius * 1.12)
            radius += rng.uniform(-0.00055, 0.00065)
            gaps = []
            for hole in holes:
                radial_to_hole = radial_radius(Vector(hole["center"]), axes, centers, radial_axes)
                if abs(radius - radial_to_hole) < hole["radius"] * 1.35:
                    width = min(0.30, math.asin(min(0.95, hole["radius"] * 1.35 / max(radius, 0.0001))))
                    gaps.append((hole["theta"], width))
            bright = rng.random() < 0.055
            material = trace_materials["traceBright"] if bright else trace_materials["traceDark"]
            bevel = rng.uniform(0.00007, 0.00012) if not bright else rng.uniform(0.00008, 0.00013)
            objects = add_gapped_ring_local(
                f"goal25d_trace_flange_{side['label']}_{index:02d}",
                axes,
                flow_axis,
                radial_axes,
                centers,
                flow_coord,
                radius,
                gaps,
                material,
                bevel,
                body,
                rng,
                steps=224,
                wobble=0.00018,
            )
            flange_segments += len(objects)
            trace_objects.extend(objects)

    bore_rings = 0
    bore_mouth_rings = 0
    for side in sides:
        mouth_coord = side["coord"] + side["sign"] * (plane_offset * 1.45)
        for mouth_index, radius in enumerate((inner_radius * 0.965, inner_radius * 1.018)):
            material = trace_materials["traceBright"] if mouth_index == 1 else trace_materials["traceDark"]
            objects = add_gapped_ring_local(
                f"goal25d_trace_bore_mouth_{side['label']}_{mouth_index:02d}",
                axes,
                flow_axis,
                radial_axes,
                centers,
                mouth_coord,
                radius,
                [],
                material,
                0.00016 if mouth_index == 1 else 0.00013,
                body,
                rng,
                steps=192,
                wobble=0.00010,
            )
            bore_mouth_rings += len(objects)
            trace_objects.extend(objects)

        depths = [0.004, 0.011, 0.021, 0.036, 0.056]
        for index, depth in enumerate(depths):
            flow_coord = side["coord"] - side["sign"] * (depth + rng.uniform(-0.0015, 0.0022))
            radius = inner_radius * rng.uniform(0.982, 0.992)
            material = trace_materials["traceBright"] if index == 0 or rng.random() < 0.16 else trace_materials["traceDark"]
            objects = add_gapped_ring_local(
                f"goal25d_trace_bore_{side['label']}_{index:02d}",
                axes,
                flow_axis,
                radial_axes,
                centers,
                flow_coord,
                radius,
                [],
                material,
                rng.uniform(0.00015, 0.00023),
                body,
                rng,
                steps=192,
                wobble=0.00025,
            )
            bore_rings += len(objects)
            trace_objects.extend(objects)

    bolt_rings = 0
    for side in sides:
        flow_coord = side["coord"] + side["sign"] * (plane_offset * 1.35)
        for hole_index, hole in enumerate(side_holes[side["label"]]):
            center = list(hole["center"])
            center[flow_axis] = flow_coord
            ring_radii = [hole["radius"] * 0.72, hole["radius"] * 1.02]
            for ring_index, radius in enumerate(ring_radii):
                material = trace_materials["traceBright"] if ring_index == 1 else trace_materials["traceDark"]
                objects = add_gapped_ring_local(
                    f"goal25d_trace_bolt_{side['label']}_{hole_index:02d}_{ring_index:02d}",
                    axes,
                    flow_axis,
                    radial_axes,
                    center,
                    flow_coord,
                    radius,
                    [],
                    material,
                    0.00016 if ring_index == 1 else 0.00013,
                    body,
                    rng,
                    steps=72,
                    wobble=0.00008,
                )
                bolt_rings += len(objects)
                trace_objects.extend(objects)

    return {
        "source": "Goal 25-C restrained geometric machining traces",
        "sourceManifest": f"{GOAL25D_DIR.replace('goal25d-zoned-body-material-proof', 'goal25c-real-machining-traces')}/render-manifest.json",
        "appliedTraceIds": MIGRATED_TRACE_IDS,
        "targetZoneIds": [
            "G25-SS-MACH-FLANGE-RADIAL-01",
            "G25-SS-MACH-BORE-CIRCULAR-01",
            "G25-SS-MACH-BOLT-BORE-DARK-01",
        ],
        "implementedAs": "explicit body-local bevel curve geometry parented to the STEP-derived valve body",
        "randomSeed": RANDOM_SEED + 25,
        "flangeTraceRingsPerEnd": flange_ring_count,
        "flangeTraceCurveSegments": flange_segments,
        "boreCircumferentialRings": bore_rings,
        "boreMouthRimObjects": bore_mouth_rings,
        "boltHoleRingObjects": bolt_rings,
        "detectedBoltHoleClusters": {
            side: [
                {
                    "thetaDegrees": round(math.degrees(hole["theta"] % math.tau), 2),
                    "radius": round(hole["radius"], 6),
                    "sampleCount": hole["sampleCount"],
                }
                for hole in holes
            ]
            for side, holes in side_holes.items()
        },
        "visibleTraceObjects": len(trace_objects),
        "objects": trace_objects,
    }


def set_render_visibility(objects: list[bpy.types.Object], visible: bool) -> None:
    for obj in objects:
        obj.hide_render = not visible
        obj.hide_viewport = not visible


def radial_radius(center: Vector, axes: str, bounds_center: list[float], radial_axes: list[int]) -> float:
    first = getattr(center, axes[radial_axes[0]]) - bounds_center[radial_axes[0]]
    second = getattr(center, axes[radial_axes[1]]) - bounds_center[radial_axes[1]]
    return math.sqrt(first * first + second * second)


def set_material_slots(obj: bpy.types.Object, materials: list[bpy.types.Material]) -> None:
    slots = obj.data.materials
    while len(slots) < len(materials):
        slots.append(materials[len(slots)])
    for index, material in enumerate(materials):
        slots[index] = material
    while len(slots) > len(materials):
        slots.pop(index=len(slots) - 1)


def create_camera(name: str = "goal25d_camera") -> bpy.types.Object:
    camera_data = bpy.data.cameras.new(name)
    camera = bpy.data.objects.new(name, camera_data)
    bpy.context.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    camera.data.type = "ORTHO"
    set_main_camera(camera)
    return camera


def set_main_camera(camera: bpy.types.Object) -> None:
    camera.data.ortho_scale = 0.48
    camera.data.shift_y = 0.0
    camera.location = (0.48, -1.18, 0.34)
    look_at(camera, (0.0, -0.010, 0.02))


def set_flange_close_camera(camera: bpy.types.Object) -> None:
    camera.data.ortho_scale = 0.29
    camera.data.shift_y = 0.0
    camera.location = (0.42, -0.90, 0.31)
    look_at(camera, (0.062, -0.030, 0.015))


def render_still(repo_root: Path, output_path: Path, render_profile: dict, title: str) -> dict:
    bpy.context.scene.render.filepath = str(output_path)
    bpy.ops.render.render(write_still=True)
    return {
        "id": output_path.stem,
        "title": title,
        "path": str(output_path.relative_to(repo_root)).replace("\\", "/"),
        "width": render_profile["width"],
        "height": render_profile["height"],
        "bytes": output_path.stat().st_size,
        "sha256": sha256(output_path),
    }


def write_status(goal_dir: Path, manifest: dict) -> None:
    materials = "\n".join(
        f"- `{spec['id']}`: {spec['cn']} - {spec['intent']}" for spec in ZONE_SPECS
    )
    outputs = "\n".join(f"- `{still['id']}`: {still['path']}" for still in manifest["stills"])
    refs = "\n".join(f"- [{ref['title']}]({ref['url']}): {ref['takeaway']}" for ref in REFERENCE_NOTES)
    counts = "\n".join(
        f"- `{zone_id}`: {count} faces, area {manifest['zoneAssignment']['zoneAreas'].get(zone_id, 0)}"
        for zone_id, count in manifest["zoneAssignment"]["zoneCounts"].items()
    )
    text = f"""# Goal 25-D Zoned Body Material Proof

Generated: {manifest['generatedAt']}

## Boundary

- This pass isolates the real STEP-derived `阀体` mesh only.
- It keeps the valve body as one mesh but assigns material IDs per polygon using geometry-derived manufacturing zones.
- It migrates restrained Goal 25-C explicit machining trace geometry back onto the flange face, main bore and bolt-hole zones.
- It does not render the full valve, replace a homepage hero, publish Pages, or create animation frames.
- Material names are visual lookdev targets, not certified alloy or surface-finish claims.

## Material Library

{materials}

## Zone Assignment Evidence

- Inferred flow axis: `{manifest['zoneAssignment']['flowAxis']}`
- Estimated bore inner radius: `{manifest['zoneAssignment']['innerRadiusEstimate']}`
- Estimated flange outer radius: `{manifest['zoneAssignment']['outerRadiusEstimate']}`

{counts}

## Migrated 25-C Trace Geometry

- Source manifest: `{manifest['traceMigration']['sourceManifest']}`
- Applied trace IDs: {", ".join(f"`{trace_id}`" for trace_id in manifest['traceMigration']['appliedTraceIds'])}
- Implementation: {manifest['traceMigration']['implementedAs']}
- Flange trace rings per end: `{manifest['traceMigration']['flangeTraceRingsPerEnd']}`
- Flange trace curve segments: `{manifest['traceMigration']['flangeTraceCurveSegments']}`
- Bore circumferential rings: `{manifest['traceMigration']['boreCircumferentialRings']}`
- Bore mouth rim objects: `{manifest['traceMigration']['boreMouthRimObjects']}`
- Bolt-hole ring objects: `{manifest['traceMigration']['boltHoleRingObjects']}`

## External References Used

{refs}

## Output

{outputs}

## Review Questions

- Does the main cast/blasted shell keep a real metal value structure instead of becoming powder white?
- Do the flange face, bore and bolt-hole migrated trace families read as real manufacturing evidence without becoming decorative striping?
- Are the edge highlights useful, or do they need to be restricted to fewer raised/chamfered features?
- Does the dark groove/root treatment make the body feel heavier and more machined without looking dirty?
"""
    write_text_lf(goal_dir / "material-status.md", text)


def write_index(goal_dir: Path, manifest: dict) -> None:
    cards = []
    for still in manifest["stills"]:
        src = html.escape(still["path"].split("/goal25d-zoned-body-material-proof/")[-1])
        cards.append(
            f"""
            <figure>
              <img src="{src}" alt="{html.escape(still['title'])}">
              <figcaption><b>{html.escape(still['title'])}</b><span>{html.escape(still['id'])}</span></figcaption>
            </figure>
            """
        )
    zone_items = "".join(
        f"<li><span style=\"--swatch:{rgb_css(spec['debug'])}\"></span><b>{html.escape(spec['id'])}</b><small>{html.escape(spec['cn'])}</small><em>{html.escape(spec['intent'])}</em></li>"
        for spec in ZONE_SPECS
    )
    html_text = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Goal 25-D Zoned Body Material Proof</title>
  <style>
    :root {{ color-scheme: light; font-family: Inter, "Noto Sans SC", system-ui, sans-serif; background: #e3e7e4; color: #111615; }}
    body {{ margin: 0; }}
    main {{ width: min(1480px, calc(100% - 40px)); margin: 0 auto; padding: 32px 0 56px; }}
    header {{ display: grid; gap: 10px; margin-bottom: 18px; }}
    .eyebrow {{ margin: 0; color: #59635f; font-size: 13px; text-transform: uppercase; letter-spacing: .08em; }}
    h1 {{ margin: 0; font-size: clamp(28px, 4vw, 46px); line-height: 1.04; letter-spacing: 0; }}
    p {{ margin: 0; max-width: 960px; color: #4b5752; line-height: 1.6; }}
    .stills {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }}
    figure {{ margin: 0; border: 1px solid #b6bfba; border-radius: 8px; overflow: hidden; background: #303533; }}
    img {{ display: block; width: 100%; height: auto; }}
    figcaption {{ display: grid; gap: 2px; padding: 10px 12px 12px; background: #f5f7f5; }}
    figcaption b {{ font-size: 13px; }}
    figcaption span {{ color: #68736f; font-size: 12px; }}
    .library {{ margin-top: 14px; border: 1px solid #b6bfba; border-radius: 8px; background: #f5f7f5; padding: 16px; }}
    h2 {{ margin: 0 0 12px; font-size: 16px; letter-spacing: 0; }}
    ul {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }}
    li {{ display: grid; grid-template-columns: 18px minmax(230px, .8fr) minmax(120px, .4fr) minmax(280px, 1.4fr); gap: 10px; align-items: start; }}
    li span {{ width: 14px; height: 14px; border-radius: 50%; background: var(--swatch); border: 1px solid rgba(0,0,0,.28); margin-top: 2px; }}
    li b, li small, li em {{ font-size: 13px; line-height: 1.35; font-style: normal; }}
    li small, li em {{ color: #59645f; }}
    code {{ background: #dfe4e1; padding: 2px 5px; border-radius: 5px; }}
    footer {{ margin-top: 14px; color: #59635f; font-size: 13px; }}
    @media (max-width: 980px) {{
      main {{ width: min(100% - 24px, 760px); padding-top: 24px; }}
      .stills {{ grid-template-columns: 1fr; }}
      li {{ grid-template-columns: 18px 1fr; }}
      li small, li em {{ grid-column: 2; }}
    }}
  </style>
</head>
<body>
<main>
  <header>
    <p class="eyebrow">Goal 25-D / isolated valve body / material zoning proof</p>
    <h1>阀体多材质分区渲染</h1>
    <p>同一个 STEP-derived <code>阀体</code> 网格按制造区域分配可复用不锈钢材质编号，并把 Goal 25-C 更克制的显式几何加工痕回迁到法兰端面、主内孔和螺栓孔口。</p>
  </header>
  <section class="stills">
    {''.join(cards)}
  </section>
  <section class="library">
    <h2>Material IDs</h2>
    <ul>{zone_items}</ul>
  </section>
  <footer>Manifest: <code>render-manifest.json</code>. Status: <code>material-status.md</code>. Trace source: <code>../goal25c-real-machining-traces/render-manifest.json</code>.</footer>
</main>
</body>
</html>
"""
    write_text_lf(goal_dir / "index.html", html_text)


def rgb_css(color: tuple[float, float, float, float]) -> str:
    return f"rgb({round(color[0] * 255)} {round(color[1] * 255)} {round(color[2] * 255)})"


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    model_path = (repo_root / args.model).resolve()
    step_report_path = (repo_root / args.step_report).resolve()
    semantic_map_path = (repo_root / args.semantic_map).resolve()
    hdri_path = (repo_root / args.hdri).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    goal_dir = out_dir.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    goal20 = load_goal20_module(repo_root)
    step_report = read_json(step_report_path)
    semantic_map = read_json(semantic_map_path)

    goal20.clear_scene()
    render_profile = configure_render(args.profile)
    studio_materials = {name: make_simple_material(name, spec) for name, spec in STUDIO_MATERIALS.items()}
    zone_materials = [make_zone_material(spec) for spec in ZONE_SPECS]
    debug_materials = [make_debug_material(spec) for spec in ZONE_SPECS]
    trace_materials = {name: make_trace_material(name, spec) for name, spec in TRACE_MATERIAL_SPECS.items()}

    meshes = goal20.import_model(model_path)
    if not meshes:
        raise RuntimeError(f"No mesh objects imported from {model_path}")

    body, body_info = isolate_body_mesh(goal20, meshes)
    zone_assignment = assign_zone_materials(body, zone_materials)
    trace_migration = build_migrated_trace_geometry(body, zone_assignment, trace_materials)
    trace_objects = trace_migration.pop("objects")
    build_studio(studio_materials, hdri_path)
    camera = create_camera()

    stills = []
    set_material_slots(body, zone_materials)
    set_render_visibility(trace_objects, True)
    set_main_camera(camera)
    stills.append(render_still(repo_root, out_dir / "01-zoned-body-material-proof.png", render_profile, "zoned body material proof"))

    set_material_slots(body, debug_materials)
    set_render_visibility(trace_objects, False)
    set_main_camera(camera)
    stills.append(render_still(repo_root, out_dir / "02-material-zone-id.png", render_profile, "material zone id map"))

    set_material_slots(body, zone_materials)
    set_render_visibility(trace_objects, True)
    set_flange_close_camera(camera)
    stills.append(render_still(repo_root, out_dir / "03-flange-bore-zone-close.png", render_profile, "flange and bore zoning close-up"))

    manifest = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "goal": "Goal 25-D isolated valve body material zoning proof",
        "profile": args.profile,
        "renderer": "Blender Cycles",
        "blender": bpy.app.version_string,
        "sourceBoundary": {
            "stepSource": step_report["source"]["path"],
            "stepSourceSha256": step_report["source"]["sha256"],
            "stepMesh": str(model_path.relative_to(repo_root)).replace("\\", "/"),
            "stepMeshSha256": sha256(model_path),
            "goal20SemanticMap": str(semantic_map_path.relative_to(repo_root)).replace("\\", "/"),
            "rule": "Goal 25-D isolates only the STEP-derived valve body mesh and assigns per-zone material IDs.",
        },
        "researchReferences": REFERENCE_NOTES,
        "bodyIdentity": {
            **body_info,
            "goal20PartCountForBody": semantic_map["partCounts"].get("阀体", 0),
        },
        "materialLibrary": [
            {
                "id": spec["id"],
                "label": spec["label"],
                "cn": spec["cn"],
                "intent": spec["intent"],
                "debugColor": [round(value, 4) for value in spec["debug"]],
                "parameters": spec["material"],
            }
            for spec in ZONE_SPECS
        ],
        "zoneAssignment": zone_assignment,
        "traceMigration": trace_migration,
        "renderProfile": {
            "width": render_profile["width"],
            "height": render_profile["height"],
            "samples": render_profile["samples"],
            "engine": "Cycles",
            "isolatedBodyOnly": True,
            "fullValveRendered": False,
            "homepageConnected": False,
            "motionTestRendered": False,
            "frameSequenceRendered": False,
            "published": False,
        },
        "lighting": {
            "hdri": str(hdri_path.relative_to(repo_root)).replace("\\", "/") if hdri_path.is_file() else None,
            "strategy": "studio HDRI plus white panels and charcoal reflection flags, keeping metal dark/bright value evidence visible",
            "areaLights": [
                "goal25d_left_large_softbox",
                "goal25d_top_long_softbox",
                "goal25d_right_edge_softbox",
                "goal25d_front_low_fill",
            ],
            "reflectionFlags": [
                "goal25d_right_charcoal_flag",
                "goal25d_low_charcoal_flag",
            ],
        },
        "stills": stills,
        "constraints": [
            "Only the isolated valve body mesh is rendered.",
            "No homepage hero replacement is performed.",
            "No GitHub Pages publication is performed.",
            "No 24-frame or 240-frame animation is rendered.",
            "Material labels are reusable visual lookdev IDs, not certified alloy or surface finish claims.",
        ],
    }

    write_json(goal_dir / "render-manifest.json", manifest)
    write_status(goal_dir, manifest)
    write_index(goal_dir, manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
