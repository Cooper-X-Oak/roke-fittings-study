#!/usr/bin/env python3
"""Render Goal 24 isolated valve-body stainless material matrix.

This pass isolates the real STEP-derived valve body mesh from Goal 20 and
renders a matrix of stainless looks:

1. pure stainless steel, without coarse grit;
2. the same stainless base with progressively coarse sanded/grit texture.

Run inside Blender:
D:\\TOOLS\\render-pipeline\\apps\\Blender-5.2.0\\Blender Foundation\\Blender 5.2\\blender.exe --background --python scripts\\render_goal24_body_stainless_matrix.py -- --repo-root . --profile smoke
"""

from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import bpy
    from mathutils import Vector
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Run this script with Blender's Python interpreter.") from exc


GOAL20_DIR = "docs/assets/ztovalve/hero/goal20-blender-cycles-step-proof"
GOAL24_DIR = "docs/assets/ztovalve/hero/goal24-body-stainless-render-matrix"

REFERENCE_NOTES = [
    {
        "id": "blender-principled-bsdf",
        "title": "Blender Manual - Principled BSDF",
        "url": "https://docs.blender.org/manual/en/2.83/render/shader_nodes/shader/principled.html",
        "takeaway": "Use a metallic material model with roughness and anisotropic controls instead of treating stainless as diffuse grey.",
    },
    {
        "id": "ambientcg-metal-pbr",
        "title": "ambientCG metal PBR materials",
        "url": "https://ambientcg.com/list?category=Metal",
        "takeaway": "Industrial metal assets separate base color, roughness and normal/height information; Goal 24 mirrors that separation procedurally.",
    },
    {
        "id": "polyhaven-studio-small-09",
        "title": "Poly Haven Studio Small 09 HDRI",
        "url": "https://polyhaven.com/a/studio_small_09",
        "takeaway": "Use a studio HDRI and visible dark/bright reflection bands so metal has something real to reflect.",
    },
    {
        "id": "blender-cli-rendering",
        "title": "yuki-koyama/blender-cli-rendering",
        "url": "https://github.com/yuki-koyama/blender-cli-rendering",
        "takeaway": "Keep Blender lookdev repeatable from CLI scripts so material matrices can be rerun after small parameter changes.",
    },
]

MATRIX_COLUMNS = [
    {
        "id": "r24-bright-controlled",
        "label": "R0.24 bright controlled",
        "baseColor": (0.55, 0.57, 0.54, 1.0),
        "roughness": 0.24,
        "anisotropic": 0.32,
        "coat": 0.04,
    },
    {
        "id": "r32-commercial-satin",
        "label": "R0.32 commercial satin",
        "baseColor": (0.47, 0.49, 0.46, 1.0),
        "roughness": 0.32,
        "anisotropic": 0.46,
        "coat": 0.025,
    },
    {
        "id": "r40-industrial-satin",
        "label": "R0.40 industrial satin",
        "baseColor": (0.40, 0.42, 0.39, 1.0),
        "roughness": 0.40,
        "anisotropic": 0.55,
        "coat": 0.015,
    },
    {
        "id": "r48-muted-satin",
        "label": "R0.48 muted satin",
        "baseColor": (0.34, 0.36, 0.34, 1.0),
        "roughness": 0.48,
        "anisotropic": 0.38,
        "coat": 0.010,
    },
]

MATRIX_ROWS = [
    {
        "id": "pure-stainless",
        "label": "pure stainless",
        "name": "纯不锈钢",
        "description": "No procedural grit; only metallic base, roughness, anisotropy and studio reflections.",
        "coarse": False,
    },
    {
        "id": "coarse-grit-stainless",
        "label": "pure stainless + coarse grit",
        "name": "纯不锈钢 + 粗粒磨砂",
        "description": "Same stainless base plus coarse roughness variation and bump texture.",
        "coarse": True,
    },
]

GRAIN_BY_COLUMN = [
    {
        "bump": 0.010,
        "bumpDistance": 0.0014,
        "bumpScale": 1040,
        "roughnessBoost": 0.08,
        "roughnessSpread": 0.10,
        "colorSpread": 0.035,
        "colorScale": 980,
    },
    {
        "bump": 0.018,
        "bumpDistance": 0.0025,
        "bumpScale": 700,
        "roughnessBoost": 0.10,
        "roughnessSpread": 0.13,
        "colorSpread": 0.045,
        "colorScale": 740,
    },
    {
        "bump": 0.030,
        "bumpDistance": 0.0042,
        "bumpScale": 470,
        "roughnessBoost": 0.11,
        "roughnessSpread": 0.16,
        "colorSpread": 0.060,
        "colorScale": 560,
    },
    {
        "bump": 0.044,
        "bumpDistance": 0.0062,
        "bumpScale": 320,
        "roughnessBoost": 0.12,
        "roughnessSpread": 0.18,
        "colorSpread": 0.075,
        "colorScale": 430,
    },
]

STUDIO_MATERIALS = {
    "floorGrey": {
        "base_color": (0.30, 0.31, 0.30, 1.0),
        "metallic": 0.0,
        "roughness": 0.88,
    },
    "softPanel": {
        "base_color": (0.72, 0.73, 0.70, 1.0),
        "metallic": 0.0,
        "roughness": 0.68,
    },
    "charcoalFlag": {
        "base_color": (0.030, 0.032, 0.031, 1.0),
        "metallic": 0.0,
        "roughness": 0.78,
    },
    "cellPad": {
        "base_color": (0.24, 0.25, 0.24, 1.0),
        "metallic": 0.0,
        "roughness": 0.82,
    },
}


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    args = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--model", default=f"{GOAL20_DIR}/goal20-step-mesh.glb")
    parser.add_argument("--step-report", default=f"{GOAL20_DIR}/step-mesh-report.json")
    parser.add_argument("--semantic-map", default=f"{GOAL20_DIR}/semantic-material-map.json")
    parser.add_argument("--hdri", default=f"{GOAL20_DIR}/studio_small_09_1k.hdr")
    parser.add_argument("--out-dir", default=f"{GOAL24_DIR}/stills")
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
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_goal20_module(repo_root: Path):
    script_path = repo_root / "scripts" / "render_goal20_blender_step_proof.py"
    spec = importlib.util.spec_from_file_location("goal20_render_helpers", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def set_input(node, names, value) -> None:
    for name in names:
        if name in node.inputs:
            node.inputs[name].default_value = value
            return


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def adjust_color(color, delta: float):
    return (
        clamp(color[0] + delta, 0.0, 1.0),
        clamp(color[1] + delta, 0.0, 1.0),
        clamp(color[2] + delta, 0.0, 1.0),
        color[3],
    )


def make_simple_material(name: str, spec: dict) -> bpy.types.Material:
    material = bpy.data.materials.new(f"goal24_{name}")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    principled = nodes.get("Principled BSDF")
    if principled:
        set_input(principled, ["Base Color"], spec["base_color"])
        set_input(principled, ["Metallic"], spec.get("metallic", 0.0))
        set_input(principled, ["Roughness"], spec.get("roughness", 0.8))
    material.diffuse_color = spec["base_color"]
    return material


def make_stainless_material(row: dict, column: dict, column_index: int) -> tuple[bpy.types.Material, dict]:
    material_name = f"goal24_{row['id']}_{column['id']}"
    material = bpy.data.materials.new(material_name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    principled = nodes.get("Principled BSDF")
    if not principled:
        material.diffuse_color = column["baseColor"]
        return material, {}

    base_color = column["baseColor"]
    roughness = column["roughness"]
    anisotropic = column["anisotropic"]
    coat = column["coat"]

    set_input(principled, ["Base Color"], base_color)
    set_input(principled, ["Metallic"], 1.0)
    set_input(principled, ["Roughness"], roughness)
    set_input(principled, ["Coat Weight", "Clearcoat"], coat)
    set_input(principled, ["Coat Roughness", "Clearcoat Roughness"], 0.20)
    set_input(principled, ["Anisotropic IOR Level", "Anisotropic"], anisotropic)

    applied = {
        "baseColor": [round(v, 4) for v in base_color],
        "roughness": roughness,
        "anisotropic": anisotropic,
        "coat": coat,
        "coarseGrit": False,
    }

    if row["coarse"]:
        grain = GRAIN_BY_COLUMN[column_index]
        color_noise = nodes.new(type="ShaderNodeTexNoise")
        color_noise.inputs["Scale"].default_value = grain["colorScale"]
        color_noise.inputs["Detail"].default_value = 15
        color_noise.inputs["Roughness"].default_value = 0.58
        color_ramp = nodes.new(type="ShaderNodeValToRGB")
        spread = grain["colorSpread"]
        color_ramp.color_ramp.elements[0].position = 0.18
        color_ramp.color_ramp.elements[0].color = adjust_color(base_color, -spread)
        color_ramp.color_ramp.elements[1].position = 1.0
        color_ramp.color_ramp.elements[1].color = adjust_color(base_color, spread * 0.72)
        material.node_tree.links.new(color_noise.outputs["Fac"], color_ramp.inputs["Fac"])
        material.node_tree.links.new(color_ramp.outputs["Color"], principled.inputs["Base Color"])

        roughness_noise = nodes.new(type="ShaderNodeTexNoise")
        roughness_noise.inputs["Scale"].default_value = max(85, grain["bumpScale"] * 0.44)
        roughness_noise.inputs["Detail"].default_value = 13
        roughness_noise.inputs["Roughness"].default_value = 0.62
        roughness_ramp = nodes.new(type="ShaderNodeValToRGB")
        roughness_low = clamp(roughness + grain["roughnessBoost"] - grain["roughnessSpread"], 0.18, 0.78)
        roughness_high = clamp(roughness + grain["roughnessBoost"] + grain["roughnessSpread"], 0.22, 0.84)
        roughness_ramp.color_ramp.elements[0].position = 0.18
        roughness_ramp.color_ramp.elements[0].color = (roughness_low, roughness_low, roughness_low, 1.0)
        roughness_ramp.color_ramp.elements[1].position = 1.0
        roughness_ramp.color_ramp.elements[1].color = (roughness_high, roughness_high, roughness_high, 1.0)
        material.node_tree.links.new(roughness_noise.outputs["Fac"], roughness_ramp.inputs["Fac"])
        material.node_tree.links.new(roughness_ramp.outputs["Color"], principled.inputs["Roughness"])

        bump_noise = nodes.new(type="ShaderNodeTexNoise")
        bump_noise.inputs["Scale"].default_value = grain["bumpScale"]
        bump_noise.inputs["Detail"].default_value = 16
        bump_noise.inputs["Roughness"].default_value = 0.54
        bump = nodes.new(type="ShaderNodeBump")
        bump.inputs["Strength"].default_value = grain["bump"]
        bump.inputs["Distance"].default_value = grain["bumpDistance"]
        material.node_tree.links.new(bump_noise.outputs["Fac"], bump.inputs["Height"])
        material.node_tree.links.new(bump.outputs["Normal"], principled.inputs["Normal"])

        applied.update(
            {
                "coarseGrit": True,
                "bumpStrength": grain["bump"],
                "bumpDistance": grain["bumpDistance"],
                "bumpScale": grain["bumpScale"],
                "roughnessLow": round(roughness_low, 4),
                "roughnessHigh": round(roughness_high, 4),
            }
        )

    material.diffuse_color = base_color
    return material, applied


def configure_render(profile: str) -> dict:
    profiles = {
        "smoke": {"width": 1200, "height": 675, "samples": 32},
        "proof": {"width": 3200, "height": 1800, "samples": 144},
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
    scene.view_settings.exposure = -0.82
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
            background.inputs["Strength"].default_value = 0.105
    else:
        world.color = (0.34, 0.35, 0.34)

    add_plane(
        "goal24_floor_reflection_only",
        studio_materials["floorGrey"],
        (0.0, 0.0, -0.72),
        (4.4, 2.6, 1),
        camera_visible=False,
    )
    add_plane(
        "goal24_rear_grey_cyc_reflection_only",
        studio_materials["floorGrey"],
        (0.0, 0.78, 0.62),
        (4.4, 1.7, 1),
        rotation=(math.radians(73), 0, 0),
        camera_visible=False,
    )

    add_plane(
        "goal24_left_white_reflection",
        studio_materials["softPanel"],
        (-1.72, -0.34, 0.56),
        (0.72, 2.0, 1),
        rotation=(0, math.radians(72), math.radians(6)),
        camera_visible=False,
    )
    add_plane(
        "goal24_top_white_strip",
        studio_materials["softPanel"],
        (0.0, -0.54, 1.38),
        (2.7, 0.26, 1),
        rotation=(math.radians(82), 0, 0),
        camera_visible=False,
    )
    add_plane(
        "goal24_right_charcoal_flag",
        studio_materials["charcoalFlag"],
        (1.60, -0.10, 0.54),
        (0.64, 2.0, 1),
        rotation=(0, math.radians(-74), math.radians(-7)),
        camera_visible=False,
    )
    add_plane(
        "goal24_overhead_charcoal_flag",
        studio_materials["charcoalFlag"],
        (0.08, 0.26, 1.16),
        (2.6, 0.34, 1),
        rotation=(math.radians(78), 0, math.radians(2)),
        camera_visible=False,
    )

    add_area_light("goal24_left_large_softbox", (-1.68, -1.62, 1.22), (0, 0, 0.12), 210, 3.1)
    add_area_light("goal24_top_long_softbox", (0.0, -0.54, 1.74), (0, 0, 0.18), 132, (0.28, 2.9))
    add_area_light("goal24_right_edge_softbox", (1.46, 0.52, 0.86), (0, 0, 0.02), 55, 1.75)
    add_area_light("goal24_front_low_fill", (0.20, -1.34, 0.24), (0, 0, 0.02), 8, 1.35)


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

    body_info = {
        "sourceName": body_records[0]["sourceName"],
        "partName": body_records[0]["partName"],
        "originalCenter": [round(v, 6) for v in body_records[0]["center"]],
        "originalSize": [round(v, 6) for v in body_records[0]["size"]],
        "centeredCenter": [round(v, 6) for v in centered_center],
        "centeredSize": [round(v, 6) for v in centered_size],
    }
    return body, body_info


def add_body_modifiers(obj: bpy.types.Object, material_id: str) -> None:
    bevel = obj.modifiers.new(f"goal24_{material_id}_micro_bevel", "BEVEL")
    bevel.width = 0.00115
    bevel.segments = 3
    bevel.affect = "EDGES"
    weighted = obj.modifiers.new(f"goal24_{material_id}_weighted_normals", "WEIGHTED_NORMAL")
    weighted.keep_sharp = True


def build_matrix(body_source: bpy.types.Object, studio_materials: dict) -> list[dict]:
    records = []
    cell_w = 0.95
    row_z = [0.42, -0.42]
    start_x = -cell_w * (len(MATRIX_COLUMNS) - 1) / 2
    cell_y = 0.0

    for row_index, row in enumerate(MATRIX_ROWS):
        for column_index, column in enumerate(MATRIX_COLUMNS):
            x = start_x + column_index * cell_w
            z = row_z[row_index]
            material, material_params = make_stainless_material(row, column, column_index)

            obj = body_source.copy()
            obj.data = body_source.data.copy()
            obj.name = f"goal24_body_{row['id']}_{column['id']}"
            obj.location = body_source.location + Vector((x, cell_y, z))
            obj.data.materials.clear()
            obj.data.materials.append(material)
            bpy.context.collection.objects.link(obj)
            add_body_modifiers(obj, f"{row['id']}_{column['id']}")

            add_plane(
                f"goal24_cell_pad_{row['id']}_{column['id']}",
                studio_materials["cellPad"],
                (x, cell_y + 0.02, z - 0.245),
                (0.26, 0.18, 1),
                camera_visible=False,
            )

            records.append(
                {
                    "rowId": row["id"],
                    "rowName": row["name"],
                    "columnId": column["id"],
                    "columnLabel": column["label"],
                    "objectName": obj.name,
                    "materialName": material.name,
                    "materialParams": material_params,
                }
            )

    bpy.data.objects.remove(body_source, do_unlink=True)
    bpy.context.view_layer.update()
    return records


def create_camera() -> bpy.types.Object:
    camera_data = bpy.data.cameras.new("goal24_body_matrix_camera")
    camera = bpy.data.objects.new("goal24_body_matrix_camera", camera_data)
    bpy.context.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 0.48
    camera.data.shift_y = 0.0
    camera.location = (0.48, -1.18, 0.34)
    look_at(camera, (0.0, -0.010, 0.02))
    return camera


def render_cell_stills(body: bpy.types.Object, repo_root: Path, out_dir: Path, render_profile: dict) -> list[dict]:
    cell_dir = out_dir / "cells"
    cell_dir.mkdir(parents=True, exist_ok=True)
    body.data.materials.clear()
    add_body_modifiers(body, "single_body")

    stills = []
    index = 1
    for row in MATRIX_ROWS:
        for column_index, column in enumerate(MATRIX_COLUMNS):
            material, material_params = make_stainless_material(row, column, column_index)
            body.data.materials.clear()
            body.data.materials.append(material)
            bpy.context.view_layer.update()

            filename = f"{index:02d}-{row['id']}-{column['id']}.png"
            output_path = cell_dir / filename
            bpy.context.scene.render.filepath = str(output_path)
            bpy.ops.render.render(write_still=True)
            stills.append(
                {
                    "id": f"{row['id']}__{column['id']}",
                    "order": index,
                    "rowId": row["id"],
                    "rowName": row["name"],
                    "columnId": column["id"],
                    "columnLabel": column["label"],
                    "path": str(output_path.relative_to(repo_root)).replace("\\", "/"),
                    "width": render_profile["width"],
                    "height": render_profile["height"],
                    "bytes": output_path.stat().st_size,
                    "sha256": sha256(output_path),
                    "materialName": material.name,
                    "materialParams": material_params,
                }
            )
            index += 1
    return stills


def render_matrix(repo_root: Path, out_dir: Path, render_profile: dict) -> dict:
    output_path = out_dir / "01-body-stainless-render-matrix.png"
    bpy.context.scene.render.filepath = str(output_path)
    bpy.ops.render.render(write_still=True)
    return {
        "id": "body-stainless-render-matrix",
        "name": "阀体不锈钢材质矩阵",
        "path": str(output_path.relative_to(repo_root)).replace("\\", "/"),
        "width": render_profile["width"],
        "height": render_profile["height"],
        "bytes": output_path.stat().st_size,
        "sha256": sha256(output_path),
    }


def write_status(goal_dir: Path, manifest: dict) -> None:
    rows = "\n".join(f"- `{row['id']}`: {row['name']} - {row['description']}" for row in MATRIX_ROWS)
    columns = "\n".join(f"- `{column['id']}`: {column['label']}" for column in MATRIX_COLUMNS)
    refs = "\n".join(f"- [{ref['title']}]({ref['url']}): {ref['takeaway']}" for ref in REFERENCE_NOTES)
    cell_outputs = "\n".join(
        f"- `{still['id']}`: {still['path']}" for still in manifest["cellStills"]
    )
    text = f"""# Goal 24 Body Stainless Render Matrix

Generated: {manifest['generatedAt']}

## Boundary

- This pass isolates the real STEP-derived `阀体` mesh only.
- It does not render the full valve.
- It does not replace the homepage hero.
- It does not render a 24-frame motion test or 240-frame release sequence.
- Material labels remain visual lookdev treatments, not certified alloy claims.

## Matrix Rows

{rows}

## Matrix Columns

{columns}

## External References Used

{refs}

## Output

- Contact sheet target: {manifest['contactSheet']['path']}
- Cell stills:
{cell_outputs}

## Review Questions

- Which pure stainless column first stops reading as powdery grey and starts reading as real stainless?
- Which coarse grit column adds useful sanded texture without becoming cast iron, dirty coating, or cement-grey plastic?
- Does the studio reflection environment give the metal enough dark/bright value structure?
"""
    (goal_dir / "material-status.md").write_text(text, encoding="utf-8")


def write_index(goal_dir: Path, manifest: dict) -> None:
    row_cards = "".join(
        f"<li><b>{html.escape(row['name'])}</b><span>{html.escape(row['description'])}</span></li>"
        for row in MATRIX_ROWS
    )
    column_cards = "".join(
        f"<li><b>{html.escape(column['label'])}</b><span>roughness {column['roughness']:.2f}, anisotropic {column['anisotropic']:.2f}</span></li>"
        for column in MATRIX_COLUMNS
    )
    cells = []
    for still in manifest["cellStills"]:
        src = html.escape(still["path"].split("/goal24-body-stainless-render-matrix/")[-1])
        cells.append(
            f"""
            <figure>
              <img src=\"{src}\" alt=\"{html.escape(still['rowName'] + ' / ' + still['columnLabel'])}\">
              <figcaption><b>{html.escape(still['rowName'])}</b><span>{html.escape(still['columnLabel'])}</span></figcaption>
            </figure>
            """
        )
    html_text = f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>Goal 24 Body Stainless Render Matrix</title>
  <style>
    :root {{ color-scheme: light; font-family: Inter, \"Noto Sans SC\", system-ui, sans-serif; background: #e4e7e5; color: #101418; }}
    body {{ margin: 0; }}
    main {{ width: min(1500px, calc(100% - 40px)); margin: 0 auto; padding: 32px 0 54px; }}
    header {{ display: grid; gap: 10px; margin-bottom: 20px; }}
    .eyebrow {{ margin: 0; color: #59636f; font-size: 13px; text-transform: uppercase; letter-spacing: .08em; }}
    h1 {{ margin: 0; font-size: clamp(28px, 4vw, 46px); line-height: 1.03; letter-spacing: 0; }}
    p {{ margin: 0; max-width: 960px; color: #46515d; line-height: 1.6; }}
    .matrix {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }}
    figure {{ margin: 0; border: 1px solid #b9c1c0; border-radius: 8px; overflow: hidden; background: #2f3332; }}
    img {{ display: block; width: 100%; height: auto; }}
    figcaption {{ display: grid; gap: 2px; padding: 10px 12px 12px; background: #f5f7f5; }}
    figcaption b {{ font-size: 13px; }}
    figcaption span {{ color: #667085; font-size: 12px; }}
    .lists {{ display: grid; grid-template-columns: 0.9fr 1.1fr; gap: 16px; margin-top: 16px; }}
    section {{ border: 1px solid #b9c1c0; border-radius: 8px; background: #f5f7f5; padding: 16px; }}
    h2 {{ margin: 0 0 12px; font-size: 16px; letter-spacing: 0; }}
    ul {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }}
    li {{ display: grid; gap: 2px; }}
    li b {{ font-size: 14px; }}
    li span {{ color: #667085; font-size: 13px; line-height: 1.45; }}
    code {{ background: #dfe4e2; padding: 2px 5px; border-radius: 5px; }}
    footer {{ margin-top: 14px; color: #59636f; font-size: 13px; }}
    @media (max-width: 820px) {{
      main {{ width: min(100% - 24px, 720px); padding-top: 24px; }}
      .matrix, .lists {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
<main>
  <header>
    <p class=\"eyebrow\">Goal 24 / isolated valve body / Blender Cycles</p>
    <h1>单独阀体不锈钢渲染矩阵</h1>
    <p>同一 STEP-derived <code>阀体</code> 几何、同一断面视角、同一棚拍环境下，比较纯不锈钢与叠加粗粒磨砂后的材质差异。</p>
  </header>
  <section class=\"matrix\">
    {''.join(cells)}
  </section>
  <div class=\"lists\">
    <section>
      <h2>Rows</h2>
      <ul>{row_cards}</ul>
    </section>
    <section>
      <h2>Columns</h2>
      <ul>{column_cards}</ul>
    </section>
  </div>
  <footer>Manifest: <code>render-manifest.json</code>. Status: <code>material-status.md</code>. Source mesh: <code>../goal20-blender-cycles-step-proof/goal20-step-mesh.glb</code>.</footer>
</main>
</body>
</html>
"""
    (goal_dir / "index.html").write_text(html_text, encoding="utf-8")


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    goal20 = load_goal20_module(repo_root)
    model_path = (repo_root / args.model).resolve()
    step_report_path = (repo_root / args.step_report).resolve()
    semantic_map_path = (repo_root / args.semantic_map).resolve()
    hdri_path = (repo_root / args.hdri).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    goal_dir = out_dir.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    step_report = read_json(step_report_path)
    semantic_map = read_json(semantic_map_path)

    goal20.clear_scene()
    render_profile = configure_render(args.profile)
    studio_materials = {name: make_simple_material(name, spec) for name, spec in STUDIO_MATERIALS.items()}
    meshes = goal20.import_model(model_path)
    if not meshes:
        raise RuntimeError(f"No mesh objects imported from {model_path}")

    body_source, body_info = isolate_body_mesh(goal20, meshes)
    build_studio(studio_materials, hdri_path)
    create_camera()
    cell_stills = render_cell_stills(body_source, repo_root, out_dir, render_profile)
    contact_sheet_path = out_dir / "01-body-stainless-render-matrix.png"

    manifest = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "goal": "Goal 24 isolated valve body stainless render matrix",
        "profile": args.profile,
        "renderer": "Blender Cycles",
        "blender": bpy.app.version_string,
        "sourceBoundary": {
            "stepSource": step_report["source"]["path"],
            "stepSourceSha256": step_report["source"]["sha256"],
            "stepMesh": str(model_path.relative_to(repo_root)).replace("\\", "/"),
            "stepMeshSha256": sha256(model_path),
            "goal20SemanticMap": str(semantic_map_path.relative_to(repo_root)).replace("\\", "/"),
            "rule": "Goal 24 isolates only the STEP-derived valve body mesh for material lookdev.",
        },
        "researchReferences": REFERENCE_NOTES,
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
        },
        "lighting": {
            "hdri": str(hdri_path.relative_to(repo_root)).replace("\\", "/") if hdri_path.is_file() else None,
            "strategy": "studio HDRI plus white soft strips and charcoal reflection flags to test stainless dark/bright value structure",
            "areaLights": [
                "goal24_left_large_softbox",
                "goal24_top_long_softbox",
                "goal24_right_edge_softbox",
                "goal24_front_low_fill",
            ],
            "reflectionFlags": [
                "goal24_right_charcoal_flag",
                "goal24_overhead_charcoal_flag",
            ],
        },
        "matrix": {
            "rows": MATRIX_ROWS,
            "columns": [
                {
                    "id": column["id"],
                    "label": column["label"],
                    "roughness": column["roughness"],
                    "anisotropic": column["anisotropic"],
                    "baseColor": [round(v, 4) for v in column["baseColor"]],
                }
                for column in MATRIX_COLUMNS
            ],
            "readingOrder": "top row left-to-right, then bottom row left-to-right",
            "records": cell_stills,
        },
        "bodyIdentity": {
            **body_info,
            "goal20PartCountForBody": semantic_map["partCounts"].get("阀体", 0),
        },
        "contactSheet": {
            "id": "body-stainless-render-matrix",
            "name": "阀体不锈钢材质矩阵",
            "path": str(contact_sheet_path.relative_to(repo_root)).replace("\\", "/"),
            "composedFromCellStills": True,
            "createdBy": "Pillow post-process",
        },
        "cellStills": cell_stills,
        "constraints": [
            "Only the isolated valve body mesh is rendered.",
            "No homepage hero replacement is performed.",
            "No 24-frame or 240-frame animation is rendered.",
            "Material labels are visual lookdev treatments, not certified alloy or surface-finish claims.",
        ],
    }

    write_json(goal_dir / "render-manifest.json", manifest)
    write_status(goal_dir, manifest)
    write_index(goal_dir, manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
