#!/usr/bin/env python3
"""Render a narrow cast satin stainless roughness ladder.

This is a follow-up to the Goal 22 material contact sheet. It keeps the
geometry tiny and isolates one question: how rough should the investment cast
stainless / satin blasted valve body material be?

Run inside Blender:
blender --background --python scripts/render_goal22_cast_satin_roughness_ladder.py -- --repo-root . --profile smoke
"""

from __future__ import annotations

import argparse
import hashlib
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


GOAL_DIR = "docs/assets/ztovalve/hero/goal22-material-calibration-lab"


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    args = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--out-dir", default=f"{GOAL_DIR}/stills")
    parser.add_argument("--profile", choices=["smoke", "proof"], default="smoke")
    return parser.parse_args(args)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def set_input(node, names: list[str], value) -> None:
    for name in names:
        if name in node.inputs:
            node.inputs[name].default_value = value
            return


def configure_render(profile: str) -> dict:
    profiles = {
        "smoke": {"width": 1800, "height": 1200, "samples": 72},
        "proof": {"width": 2400, "height": 1600, "samples": 144},
    }
    selected = profiles[profile]
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = selected["samples"]
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 10
    scene.cycles.diffuse_bounces = 3
    scene.cycles.glossy_bounces = 6
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
    scene.view_settings.exposure = -0.62
    scene.view_settings.gamma = 1.0
    try:
        scene.cycles.device = "GPU"
    except Exception:
        scene.cycles.device = "CPU"
    return selected


def make_principled(
    name: str,
    base_color,
    metallic: float,
    roughness: float,
    coat: float = 0.0,
    coat_roughness: float = 0.18,
    anisotropic: float = 0.0,
):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    principled = nodes.get("Principled BSDF")
    if not principled:
        material.diffuse_color = base_color
        return material, None
    set_input(principled, ["Base Color"], base_color)
    set_input(principled, ["Metallic"], metallic)
    set_input(principled, ["Roughness"], roughness)
    set_input(principled, ["Coat Weight", "Clearcoat"], coat)
    set_input(principled, ["Coat Roughness", "Clearcoat Roughness"], coat_roughness)
    set_input(principled, ["Anisotropic IOR Level", "Anisotropic"], anisotropic)
    material.diffuse_color = base_color
    return material, principled


def add_noise_variation(
    material,
    principled,
    color_low,
    color_high,
    color_scale: float,
    roughness_low: float,
    roughness_high: float,
    roughness_scale: float,
    bump_strength: float,
    bump_distance: float,
    bump_scale: float,
) -> None:
    if not principled:
        return
    nodes = material.node_tree.nodes
    links = material.node_tree.links

    color_noise = nodes.new(type="ShaderNodeTexNoise")
    color_noise.inputs["Scale"].default_value = color_scale
    color_noise.inputs["Detail"].default_value = 12
    color_noise.inputs["Roughness"].default_value = 0.54
    color_ramp = nodes.new(type="ShaderNodeValToRGB")
    color_ramp.color_ramp.elements[0].position = 0.16
    color_ramp.color_ramp.elements[0].color = color_low
    color_ramp.color_ramp.elements[1].position = 1.0
    color_ramp.color_ramp.elements[1].color = color_high
    links.new(color_noise.outputs["Fac"], color_ramp.inputs["Fac"])
    links.new(color_ramp.outputs["Color"], principled.inputs["Base Color"])

    roughness_noise = nodes.new(type="ShaderNodeTexNoise")
    roughness_noise.inputs["Scale"].default_value = roughness_scale
    roughness_noise.inputs["Detail"].default_value = 11
    roughness_noise.inputs["Roughness"].default_value = 0.52
    roughness_ramp = nodes.new(type="ShaderNodeValToRGB")
    roughness_ramp.color_ramp.elements[0].position = 0.20
    roughness_ramp.color_ramp.elements[0].color = (roughness_low, roughness_low, roughness_low, 1.0)
    roughness_ramp.color_ramp.elements[1].position = 1.0
    roughness_ramp.color_ramp.elements[1].color = (roughness_high, roughness_high, roughness_high, 1.0)
    links.new(roughness_noise.outputs["Fac"], roughness_ramp.inputs["Fac"])
    links.new(roughness_ramp.outputs["Color"], principled.inputs["Roughness"])

    if bump_strength:
        bump_noise = nodes.new(type="ShaderNodeTexNoise")
        bump_noise.inputs["Scale"].default_value = bump_scale
        bump_noise.inputs["Detail"].default_value = 14
        bump_noise.inputs["Roughness"].default_value = 0.48
        bump = nodes.new(type="ShaderNodeBump")
        bump.inputs["Strength"].default_value = bump_strength
        bump.inputs["Distance"].default_value = bump_distance
        links.new(bump_noise.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], principled.inputs["Normal"])


def make_cast_material(spec: dict):
    roughness = spec["roughness"]
    texture = spec["texture"]
    material, principled = make_principled(
        f"goal22_cast_satin_{texture['id']}_r{int(roughness * 100):02d}",
        (0.37, 0.38, 0.36, 1.0),
        metallic=1.0,
        roughness=roughness,
        coat=0.035,
        coat_roughness=0.18,
        anisotropic=0.18,
    )
    spread = texture["roughness_spread"]
    add_noise_variation(
        material,
        principled,
        (0.29, 0.30, 0.29, 1.0),
        (0.46, 0.47, 0.44, 1.0),
        color_scale=texture["color_scale"],
        roughness_low=max(0.18, roughness - spread),
        roughness_high=min(0.76, roughness + spread),
        roughness_scale=texture["roughness_scale"],
        bump_strength=texture["bump_strength"],
        bump_distance=texture["bump_distance"],
        bump_scale=texture["bump_scale"],
    )
    return material


def look_at(obj, target) -> None:
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def add_area_light(name: str, location, target, power: float, size):
    light_data = bpy.data.lights.new(name, type="AREA")
    light_obj = bpy.data.objects.new(name, light_data)
    bpy.context.collection.objects.link(light_obj)
    light_obj.location = location
    look_at(light_obj, target)
    light_data.energy = power
    if isinstance(size, tuple):
        light_data.shape = "RECTANGLE"
        light_data.size = size[0]
        light_data.size_y = size[1]
    else:
        light_data.size = size
    return light_obj


def add_plane(name: str, material, location, scale, rotation=(0, 0, 0), camera_visible=True):
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


def add_simple_material(name: str, color, roughness: float = 0.82):
    material, _ = make_principled(name, color, metallic=0.0, roughness=roughness)
    return material


def add_cast_coupon(name: str, material, location):
    x, y, z = location
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, z + 0.27))
    block = bpy.context.object
    block.name = f"{name}_rounded_cast_block"
    block.scale = (0.50, 0.40, 0.24)
    block.rotation_euler = (0, 0, math.radians(-7))
    block.data.materials.append(material)
    bevel = block.modifiers.new("goal22_cast_soft_edges", "BEVEL")
    bevel.width = 0.060
    bevel.segments = 12
    bevel.affect = "EDGES"
    weighted = block.modifiers.new("goal22_cast_weighted_normals", "WEIGHTED_NORMAL")
    weighted.keep_sharp = True

    bpy.ops.mesh.primitive_cylinder_add(
        vertices=96,
        radius=0.24,
        depth=0.42,
        location=(x + 0.10, y - 0.20, z + 0.22),
        rotation=(math.radians(86), 0, math.radians(-9)),
    )
    cylinder = bpy.context.object
    cylinder.name = f"{name}_curved_cast_face"
    cylinder.data.materials.append(material)
    cylinder.modifiers.new("goal22_cylinder_weighted_normals", "WEIGHTED_NORMAL")
    return block


def make_ladder_specs() -> list[dict]:
    textures = [
        {
            "id": "smooth",
            "label": "smooth satin cast",
            "color_scale": 240,
            "roughness_scale": 190,
            "roughness_spread": 0.045,
            "bump_strength": 0.0018,
            "bump_distance": 0.0007,
            "bump_scale": 420,
        },
        {
            "id": "fine",
            "label": "fine cast satin",
            "color_scale": 520,
            "roughness_scale": 390,
            "roughness_spread": 0.060,
            "bump_strength": 0.0038,
            "bump_distance": 0.0010,
            "bump_scale": 720,
        },
        {
            "id": "bead",
            "label": "bead-blasted satin",
            "color_scale": 950,
            "roughness_scale": 740,
            "roughness_spread": 0.075,
            "bump_strength": 0.0068,
            "bump_distance": 0.0012,
            "bump_scale": 1180,
        },
    ]
    roughness_values = [0.30, 0.38, 0.46, 0.54]
    specs = []
    for texture in textures:
        for roughness in roughness_values:
            specs.append(
                {
                    "id": f"{texture['id']}_r{int(roughness * 100):02d}",
                    "label": f"{texture['label']} / roughness {roughness:.2f}",
                    "texture": texture,
                    "roughness": roughness,
                }
            )
    return specs


def build_scene(specs: list[dict]) -> None:
    floor = add_simple_material("goal22_ladder_warm_grey_floor", (0.36, 0.37, 0.35, 1.0), 0.86)
    pad = add_simple_material("goal22_ladder_cell_pad", (0.44, 0.45, 0.43, 1.0), 0.80)
    white_panel = add_simple_material("goal22_ladder_white_reflection_panel", (0.80, 0.81, 0.78, 1.0), 0.66)

    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.color = (0.34, 0.35, 0.34)

    add_plane("goal22_ladder_floor", floor, (0, 0, -0.018), (9.0, 8.0, 1))
    add_plane(
        "goal22_ladder_left_white_panel",
        white_panel,
        (-4.0, -0.45, 1.35),
        (1.0, 3.8, 1),
        rotation=(0, math.radians(70), 0),
        camera_visible=False,
    )
    add_plane(
        "goal22_ladder_right_white_panel",
        white_panel,
        (4.0, -0.25, 1.35),
        (1.0, 3.8, 1),
        rotation=(0, math.radians(-70), 0),
        camera_visible=False,
    )
    add_area_light("goal22_ladder_left_key", (-3.9, -3.3, 3.5), (0, 0, 0.45), 620, 4.8)
    add_area_light("goal22_ladder_top_strip", (0.0, -1.0, 4.0), (0, 0.1, 0.25), 220, (0.42, 4.8))
    add_area_light("goal22_ladder_right_edge", (3.6, -0.1, 2.1), (0, 0, 0.30), 110, 2.8)
    add_area_light("goal22_ladder_front_fill", (0.0, -4.2, 1.2), (0, 0, 0.22), 28, 3.6)

    columns = 4
    cell_w = 1.34
    cell_d = 1.12
    start_x = -cell_w * (columns - 1) / 2
    start_y = 1.18
    for index, spec in enumerate(specs):
        col = index % columns
        row = index // columns
        x = start_x + col * cell_w
        y = start_y - row * cell_d
        add_plane(
            f"goal22_ladder_pad_{spec['id']}",
            pad,
            (x, y, 0.005),
            (0.58, 0.42, 1),
        )
        material = make_cast_material(spec)
        add_cast_coupon(f"goal22_ladder_{spec['id']}", material, (x, y, 0))

    camera_data = bpy.data.cameras.new("goal22_ladder_camera")
    camera = bpy.data.objects.new("goal22_ladder_camera", camera_data)
    bpy.context.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    camera.location = (0.0, -5.45, 4.85)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 4.95
    camera.data.shift_y = -0.02
    look_at(camera, (0.0, 0.02, 0.24))


def render(repo_root: Path, out_dir: Path, render_profile: dict) -> dict:
    output_path = out_dir / "02-cast-satin-roughness-ladder.png"
    bpy.context.scene.render.filepath = str(output_path)
    bpy.ops.render.render(write_still=True)
    return {
        "id": "cast-satin-roughness-ladder",
        "name": "Cast satin stainless roughness ladder",
        "path": str(output_path.relative_to(repo_root)).replace("\\", "/"),
        "width": render_profile["width"],
        "height": render_profile["height"],
        "bytes": output_path.stat().st_size,
        "sha256": sha256(output_path),
    }


def write_ladder_manifest(goal_dir: Path, still: dict, specs: list[dict], render_profile: dict, profile: str) -> None:
    manifest = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "goal": "Goal 22 cast satin stainless roughness ladder",
        "profile": profile,
        "renderer": "Blender Cycles",
        "blender": bpy.app.version_string,
        "renderProfile": {
            "width": render_profile["width"],
            "height": render_profile["height"],
            "samples": render_profile["samples"],
            "engine": "Cycles",
            "fullValveImported": False,
            "homepageConnected": False,
            "frameSequenceRendered": False,
        },
        "matrix": {
            "columns": ["roughness 0.30", "roughness 0.38", "roughness 0.46", "roughness 0.54"],
            "rows": ["smooth satin cast", "fine cast satin", "bead-blasted satin"],
            "readingOrder": "left-to-right, top-to-bottom",
        },
        "swatches": [
            {
                "id": spec["id"],
                "label": spec["label"],
                "roughness": spec["roughness"],
                "textureBand": spec["texture"]["id"],
                "materialName": f"goal22_cast_satin_{spec['texture']['id']}_r{int(spec['roughness'] * 100):02d}",
            }
            for spec in specs
        ],
        "still": still,
        "constraints": [
            "Only cast satin stainless candidates are tested.",
            "No full valve model is loaded.",
            "No homepage hero replacement is performed.",
            "No 24-frame or 240-frame animation is rendered.",
        ],
    }
    path = goal_dir / "cast-satin-roughness-ladder.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    goal_dir = out_dir.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    clear_scene()
    render_profile = configure_render(args.profile)
    specs = make_ladder_specs()
    build_scene(specs)
    still = render(repo_root, out_dir, render_profile)
    write_ladder_manifest(goal_dir, still, specs, render_profile, args.profile)


if __name__ == "__main__":
    main()
