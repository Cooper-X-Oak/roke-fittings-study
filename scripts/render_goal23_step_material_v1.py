#!/usr/bin/env python3
"""Render Goal 23 STEP full-valve material v1 stills.

This pass applies a full-valve micro-tune based on the Goal 22 fine_r46 cast
satin stainless candidate to the STEP-derived full valve mesh from Goal 20. It
renders stills only: no homepage replacement, no motion test, no 240-frame
sequence.

Run inside Blender:
blender --background --python scripts/render_goal23_step_material_v1.py -- --repo-root . --profile smoke
"""

from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

try:
    import bpy
    from mathutils import Vector
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Run this script with Blender's Python interpreter.") from exc


GOAL20_DIR = "docs/assets/ztovalve/hero/goal20-blender-cycles-step-proof"
GOAL22_DIR = "docs/assets/ztovalve/hero/goal22-material-calibration-lab"
GOAL23_DIR = "docs/assets/ztovalve/hero/goal23-step-material-v1"


MATERIAL_SPECS = {
    "castBlastedStainless": {
        "base_color": (0.22, 0.24, 0.23, 1.0),
        "metallic": 1.0,
        "roughness": 0.40,
        "anisotropic": 0.28,
        "coat": 0.015,
        "bump": 0.026,
        "bump_distance": 0.0034,
        "noise_scale": 1650,
        "noise_detail": 16,
        "color_variation": ((0.16, 0.18, 0.17, 1.0), (0.36, 0.38, 0.35, 1.0)),
        "color_noise_scale": 1180,
        "color_noise_detail": 14,
        "roughness_variation": (0.34, 0.56),
        "roughness_noise_scale": 920,
        "roughness_noise_detail": 13,
    },
    "machinedStainless": {
        "base_color": (0.50, 0.51, 0.48, 1.0),
        "metallic": 1.0,
        "roughness": 0.26,
        "anisotropic": 0.72,
        "coat": 0.10,
        "bump": 0.003,
        "bump_distance": 0.0010,
        "noise_scale": 130,
        "noise_detail": 9,
        "color_variation": ((0.38, 0.39, 0.37, 1.0), (0.66, 0.67, 0.62, 1.0)),
        "color_noise_scale": 100,
        "color_noise_detail": 8,
        "roughness_variation": (0.19, 0.34),
        "roughness_noise_scale": 95,
        "roughness_noise_detail": 8,
    },
    "polishedStainlessBall": {
        "base_color": (0.72, 0.74, 0.71, 1.0),
        "metallic": 1.0,
        "roughness": 0.065,
        "anisotropic": 0.0,
        "coat": 0.16,
        "bump": 0.0,
        "noise_scale": 1,
        "noise_detail": 1,
        "roughness_variation": (0.050, 0.085),
        "roughness_noise_scale": 55,
        "roughness_noise_detail": 6,
    },
    "graphitePacking": {
        "base_color": (0.018, 0.019, 0.020, 1.0),
        "metallic": 0.12,
        "roughness": 0.66,
        "anisotropic": 0.0,
        "coat": 0.0,
        "bump": 0.020,
        "bump_distance": 0.0030,
        "noise_scale": 95,
        "noise_detail": 10,
        "color_variation": ((0.006, 0.006, 0.007, 1.0), (0.070, 0.072, 0.070, 1.0)),
        "color_noise_scale": 72,
        "color_noise_detail": 9,
        "roughness_variation": (0.52, 0.82),
        "roughness_noise_scale": 105,
    },
    "softSealPtfe": {
        "base_color": (0.66, 0.61, 0.50, 1.0),
        "metallic": 0.0,
        "roughness": 0.55,
        "anisotropic": 0.0,
        "coat": 0.02,
        "bump": 0.004,
        "bump_distance": 0.0014,
        "noise_scale": 80,
        "noise_detail": 8,
        "color_variation": ((0.50, 0.47, 0.38, 1.0), (0.82, 0.77, 0.62, 1.0)),
        "color_noise_scale": 55,
        "roughness_variation": (0.46, 0.68),
        "roughness_noise_scale": 70,
    },
    "fastenerStainless": {
        "base_color": (0.44, 0.45, 0.42, 1.0),
        "metallic": 1.0,
        "roughness": 0.30,
        "anisotropic": 0.48,
        "coat": 0.06,
        "bump": 0.003,
        "bump_distance": 0.0010,
        "noise_scale": 150,
        "noise_detail": 8,
        "color_variation": ((0.31, 0.32, 0.30, 1.0), (0.62, 0.63, 0.58, 1.0)),
        "color_noise_scale": 120,
        "roughness_variation": (0.22, 0.40),
        "roughness_noise_scale": 110,
    },
    "goal23FloorGrey": {
        "base_color": (0.30, 0.31, 0.30, 1.0),
        "metallic": 0.0,
        "roughness": 0.88,
        "anisotropic": 0.0,
        "coat": 0.0,
        "bump": 0.0,
        "noise_scale": 1,
        "noise_detail": 1,
    },
    "goal23SoftWhitePanel": {
        "base_color": (0.58, 0.60, 0.57, 1.0),
        "metallic": 0.0,
        "roughness": 0.72,
        "anisotropic": 0.0,
        "coat": 0.0,
        "bump": 0.0,
        "noise_scale": 1,
        "noise_detail": 1,
    },
    "goal23CharcoalReflectionFlag": {
        "base_color": (0.045, 0.048, 0.045, 1.0),
        "metallic": 0.0,
        "roughness": 0.74,
        "anisotropic": 0.0,
        "coat": 0.0,
        "bump": 0.0,
        "noise_scale": 1,
        "noise_detail": 1,
    },
}


CAMERA_SETUPS = [
    {
        "id": "assembled-material-v1",
        "stateId": "assembled",
        "name": "完整整阀材质 v1",
        "filename": "01-assembled-material-v1.png",
        "purpose": "检查基于 fine_r46 微调后的铸造缎面不锈钢在整阀上的商业质感、色调和材质分离。",
        "camera": (0.88, -1.42, 0.54),
        "target": (-0.025, 0.015, 0.025),
        "lensMm": 70,
    },
    {
        "id": "body-flange-cast-satin-close",
        "stateId": "assembled",
        "name": "阀体/法兰铸造缎面近景",
        "filename": "02-body-flange-cast-satin-close.png",
        "purpose": "专门检查阀体、阀盖、法兰上的铸后磨砂/喷砂缎面不锈钢是否还有粉感、白感或粗糙度不足。",
        "targetPart": "阀体",
        "cameraOffset": (0.54, -0.92, 0.24),
        "targetOffset": (0.045, -0.050, -0.010),
        "lensMm": 84,
    },
    {
        "id": "ball-seat-seal-close",
        "stateId": "detail-open",
        "name": "球体/阀座/密封近景",
        "filename": "03-ball-seat-seal-close.png",
        "purpose": "检查抛光球体、PTFE 阀座和石墨密封在同一真实阀门局部里的分离度。",
        "targetPart": "球体",
        "cameraOffset": (0.50, -0.88, 0.28),
        "targetOffset": (0.0, -0.010, 0.000),
        "lensMm": 86,
    },
]


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    args = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--model", default=f"{GOAL20_DIR}/goal20-step-mesh.glb")
    parser.add_argument("--step-report", default=f"{GOAL20_DIR}/step-mesh-report.json")
    parser.add_argument("--step-audit", default="asset/derived/fixed-ball-valve/model-audit-step.json")
    parser.add_argument("--semantic-map", default=f"{GOAL20_DIR}/semantic-material-map.json")
    parser.add_argument("--goal22-ladder", default=f"{GOAL22_DIR}/cast-satin-roughness-ladder.json")
    parser.add_argument("--hdri", default=f"{GOAL20_DIR}/studio_small_09_1k.hdr")
    parser.add_argument("--out-dir", default=f"{GOAL23_DIR}/stills")
    parser.add_argument("--profile", choices=["smoke", "proof"], default="smoke")
    return parser.parse_args(args)


def load_goal20_module(repo_root: Path):
    script_path = repo_root / "scripts" / "render_goal20_blender_step_proof.py"
    spec = importlib.util.spec_from_file_location("goal20_render_helpers", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


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


def set_input(node, names, value) -> None:
    for name in names:
        if name in node.inputs:
            node.inputs[name].default_value = value
            return


def make_material(name: str, spec: dict) -> bpy.types.Material:
    material = bpy.data.materials.new(f"goal23_{name}")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    principled = nodes.get("Principled BSDF")
    if not principled:
        material.diffuse_color = spec["base_color"]
        return material

    set_input(principled, ["Base Color"], spec["base_color"])
    set_input(principled, ["Metallic"], spec["metallic"])
    set_input(principled, ["Roughness"], spec["roughness"])
    set_input(principled, ["Coat Weight", "Clearcoat"], spec.get("coat", 0.0))
    set_input(principled, ["Coat Roughness", "Clearcoat Roughness"], 0.18)
    set_input(principled, ["Anisotropic IOR Level", "Anisotropic"], spec.get("anisotropic", 0.0))

    if "color_variation" in spec:
        color_noise = nodes.new(type="ShaderNodeTexNoise")
        color_noise.inputs["Scale"].default_value = spec.get("color_noise_scale", 80)
        color_noise.inputs["Detail"].default_value = spec.get("color_noise_detail", 10)
        color_noise.inputs["Roughness"].default_value = 0.54
        color_ramp = nodes.new(type="ShaderNodeValToRGB")
        low_color, high_color = spec["color_variation"]
        color_ramp.color_ramp.elements[0].position = 0.16
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
        roughness_noise.inputs["Roughness"].default_value = 0.52
        roughness_ramp = nodes.new(type="ShaderNodeValToRGB")
        low_roughness, high_roughness = spec["roughness_variation"]
        roughness_ramp.color_ramp.elements[0].position = 0.20
        roughness_ramp.color_ramp.elements[0].color = (low_roughness, low_roughness, low_roughness, 1.0)
        roughness_ramp.color_ramp.elements[1].position = 1.0
        roughness_ramp.color_ramp.elements[1].color = (high_roughness, high_roughness, high_roughness, 1.0)
        material.node_tree.links.new(roughness_noise.outputs["Fac"], roughness_ramp.inputs["Fac"])
        material.node_tree.links.new(roughness_ramp.outputs["Color"], principled.inputs["Roughness"])

    bump_strength = spec.get("bump", 0.0)
    if bump_strength:
        bump_noise = nodes.new(type="ShaderNodeTexNoise")
        bump_noise.inputs["Scale"].default_value = spec.get("noise_scale", 80)
        bump_noise.inputs["Detail"].default_value = spec.get("noise_detail", 10)
        bump_noise.inputs["Roughness"].default_value = 0.50
        bump = nodes.new(type="ShaderNodeBump")
        bump.inputs["Strength"].default_value = bump_strength
        bump.inputs["Distance"].default_value = spec.get("bump_distance", 0.001)
        material.node_tree.links.new(bump_noise.outputs["Fac"], bump.inputs["Height"])
        if "Normal" in principled.inputs:
            material.node_tree.links.new(bump.outputs["Normal"], principled.inputs["Normal"])

    material.diffuse_color = spec["base_color"]
    return material


def configure_render(profile: str) -> dict:
    profiles = {
        "smoke": {"width": 1600, "height": 900, "samples": 44},
        "proof": {"width": 2560, "height": 1440, "samples": 128},
    }
    selected = profiles[profile]
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = selected["samples"]
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 9
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
    scene.view_settings.exposure = -1.04
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


def build_studio(materials: dict, hdri_path: Path | None) -> None:
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
            background.inputs["Strength"].default_value = 0.055
    else:
        world.color = (0.44, 0.45, 0.43)

    add_plane("goal23_neutral_grey_floor", materials["goal23FloorGrey"], (0, 0, -0.176), (4.8, 3.4, 1))
    add_plane(
        "goal23_soft_rear_cyc",
        materials["goal23FloorGrey"],
        (0.0, 0.88, 0.52),
        (4.8, 1.8, 1),
        rotation=(math.radians(74), 0, 0),
    )

    add_plane(
        "goal23_left_white_reflection_panel",
        materials["goal23SoftWhitePanel"],
        (-1.9, -0.62, 0.52),
        (0.92, 2.25, 1),
        rotation=(0, math.radians(72), math.radians(8)),
        camera_visible=False,
    )
    add_plane(
        "goal23_right_white_reflection_panel",
        materials["goal23SoftWhitePanel"],
        (1.85, -0.12, 0.48),
        (0.78, 2.05, 1),
        rotation=(0, math.radians(-72), math.radians(-6)),
        camera_visible=False,
    )
    add_plane(
        "goal23_top_white_strip_reflection",
        materials["goal23SoftWhitePanel"],
        (0.0, -0.58, 1.72),
        (2.9, 0.28, 1),
        rotation=(math.radians(82), 0, 0),
        camera_visible=False,
    )
    add_plane(
        "goal23_left_charcoal_reflection_flag",
        materials["goal23CharcoalReflectionFlag"],
        (-1.72, 0.34, 0.44),
        (0.64, 1.8, 1),
        rotation=(0, math.radians(78), math.radians(-4)),
        camera_visible=False,
    )
    add_plane(
        "goal23_overhead_charcoal_reflection_flag",
        materials["goal23CharcoalReflectionFlag"],
        (-0.28, 0.32, 1.46),
        (1.95, 0.34, 1),
        rotation=(math.radians(78), 0, math.radians(2)),
        camera_visible=False,
    )

    add_area_light("goal23_left_broad_softbox", (-1.55, -1.72, 1.18), (0, 0, 0.05), 145, 3.0)
    add_area_light("goal23_top_long_soft_strip", (0.06, -0.42, 1.82), (0, 0, 0.04), 82, (0.34, 2.65))
    add_area_light("goal23_right_edge_softbox", (1.32, 0.52, 0.82), (0, 0, 0.02), 52, 1.75)
    add_area_light("goal23_front_low_fill", (0.24, -1.32, 0.26), (0, 0, 0.02), 7, 1.45)


def render_stills(goal20, repo_root: Path, out_dir: Path, records: list, camera) -> list[dict]:
    stills = []
    for setup in CAMERA_SETUPS:
        goal20.apply_state(records, setup["stateId"])
        if "targetPart" in setup:
            matches = [record for record in records if record["partName"] == setup["targetPart"]]
            if not matches:
                raise RuntimeError(f"No object matched targetPart={setup['targetPart']}")
            centers = [goal20.object_bounds(record["object"])[2] for record in matches]
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
        src = html.escape(still["path"].split("/goal23-step-material-v1/")[-1])
        cards.append(
            f"""
            <figure>
              <img src=\"{src}\" alt=\"{html.escape(still['name'])}\">
              <figcaption><b>{html.escape(still['name'])}</b><span>{html.escape(still['purpose'])}</span></figcaption>
            </figure>
            """
        )
    html_text = f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>Goal 23 STEP Material V1</title>
  <style>
    :root {{ color-scheme: light; font-family: Inter, \"Noto Sans SC\", system-ui, sans-serif; background: #eceeec; color: #101418; }}
    body {{ margin: 0; }}
    main {{ width: min(1440px, calc(100% - 40px)); margin: 0 auto; padding: 34px 0 54px; }}
    header {{ display: grid; gap: 10px; margin-bottom: 22px; }}
    .eyebrow {{ margin: 0; color: #59636f; font-size: 13px; text-transform: uppercase; letter-spacing: .08em; }}
    h1 {{ margin: 0; font-size: clamp(28px, 4vw, 46px); line-height: 1.03; letter-spacing: 0; }}
    p {{ max-width: 880px; color: #475467; line-height: 1.6; margin: 0; }}
    .summary {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin: 18px 0 26px; }}
    .metric {{ border: 1px solid #cbd2d9; background: #f8f9f7; border-radius: 8px; padding: 14px 16px; }}
    .metric b {{ display: block; font-size: 22px; }}
    .metric span {{ color: #667085; font-size: 13px; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }}
    figure {{ margin: 0; border: 1px solid #cbd2d9; background: #f8f9f7; border-radius: 8px; overflow: hidden; }}
    figure:first-child {{ grid-column: 1 / -1; }}
    img {{ display: block; width: 100%; height: auto; background: #d8dbd7; }}
    figcaption {{ display: grid; gap: 4px; padding: 12px 14px 14px; }}
    figcaption span {{ color: #667085; font-size: 13px; line-height: 1.45; }}
    code {{ background: #dfe3e6; padding: 2px 5px; border-radius: 5px; }}
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
    <p class=\"eyebrow\">Goal 23 / STEP full-valve material v1 / Blender Cycles</p>
    <h1>固定式球阀整阀材质首版</h1>
    <p>本轮把 Goal 22 的 <code>fine_r46</code> 铸造缎面不锈钢作为起点，在 Goal 20 的 STEP-derived 整阀模型上做中灰钢感和铸后磨砂微调，只输出 still 用于材质审阅；不替换 hero，不渲染动画序列。</p>
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
  <p>Manifest: <code>render-manifest.json</code>. Material status: <code>material-status.md</code>. Source mesh: <code>../goal20-blender-cycles-step-proof/goal20-step-mesh.glb</code>. Material evidence: <code>../goal22-material-calibration-lab/cast-satin-roughness-ladder.json</code>.</p>
</main>
</body>
</html>
"""
    (goal_dir / "index.html").write_text(html_text, encoding="utf-8")


def write_material_status(goal_dir: Path, manifest: dict) -> None:
    text = f"""# Goal 23 STEP Full-Valve Material V1

Generated: {manifest['generatedAt']}

## Boundary

- This pass renders STEP-derived full-valve stills only.
- It does not replace the homepage hero.
- It does not render a 24-frame motion test or 240-frame release sequence.
- It reuses the Goal 20 STEP-derived GLB and does not overwrite source CAD.

## Material Decision

- Body/bonnet/flange: `castBlastedStainless` starts from the Goal 22 `fine_r46` direction, then darkens and strengthens cast/sanded micro-roughness for full-valve scale.
- Ball: `polishedStainlessBall`, low roughness mirror stainless with broad soft studio reflection.
- Seat: `softSealPtfe`, warm off-white PTFE treatment.
- Packing/seals: `graphitePacking`, dark grey graphite treatment.
- Fasteners: `fastenerStainless`, medium-bright stainless hardware.
- Machined parts: `machinedStainless`, brighter anisotropic stainless.

## Rendered Stills

{chr(10).join(f"- `{still['id']}`: {still['path']}" for still in manifest['stills'])}

## Current Review Questions

- Does the full-valve cast body now read as satin cast stainless instead of powdery near-white plastic?
- Is the cast/sanded micro-grain visible enough without becoming noisy or dirty?
- Are PTFE and graphite parts separated enough from the metal body?
- Are fasteners too dark, too bright, or about right against the cast body?

## Constraints

- Material labels are visual lookdev treatments, not certified alloy or coating claims.
- The next step after review should be parameter micro-tuning, not animation rendering.
"""
    (goal_dir / "material-status.md").write_text(text, encoding="utf-8")


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    goal20 = load_goal20_module(repo_root)
    model_path = (repo_root / args.model).resolve()
    step_report_path = (repo_root / args.step_report).resolve()
    step_audit_path = (repo_root / args.step_audit).resolve()
    semantic_map_path = (repo_root / args.semantic_map).resolve()
    ladder_path = (repo_root / args.goal22_ladder).resolve()
    hdri_path = (repo_root / args.hdri).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    goal_dir = out_dir.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    step_report = read_json(step_report_path)
    step_audit = read_json(step_audit_path)
    goal20_semantic_map = read_json(semantic_map_path)
    goal22_ladder = read_json(ladder_path)

    goal20.clear_scene()
    render_profile = configure_render(args.profile)
    materials = {name: make_material(name, spec) for name, spec in MATERIAL_SPECS.items()}
    meshes = goal20.import_model(model_path)
    if not meshes:
        raise RuntimeError(f"No mesh objects imported from {model_path}")

    goal20.create_rig(meshes)
    records, group_counts, material_counts, part_counts = goal20.assign_materials(meshes, materials)
    build_studio(materials, hdri_path)
    camera = goal20.create_camera()
    stills = render_stills(goal20, repo_root, out_dir, records, camera)

    focus_parts = []
    for record in records:
        if record["material"] not in ("castBlastedStainless", "polishedStainlessBall", "softSealPtfe", "graphitePacking"):
            continue
        _min_v, _max_v, center, size = goal20.object_bounds(record["object"])
        focus_parts.append(
            {
                "sourceName": record["sourceName"],
                "partName": record["partName"],
                "group": record["group"],
                "material": record["material"],
                "center": [round(center.x, 6), round(center.y, 6), round(center.z, 6)],
                "size": [round(size.x, 6), round(size.y, 6), round(size.z, 6)],
            }
        )

    manifest = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "goal": "Goal 23 STEP full-valve material v1",
        "profile": args.profile,
        "renderer": "Blender Cycles",
        "blender": bpy.app.version_string,
        "sourceBoundary": {
            "stepSource": step_report["source"]["path"],
            "stepSourceSha256": step_report["source"]["sha256"],
            "stepMesh": str(model_path.relative_to(repo_root)).replace("\\", "/"),
            "stepMeshSha256": sha256(model_path),
            "goal20SemanticMap": str(semantic_map_path.relative_to(repo_root)).replace("\\", "/"),
            "goal22Ladder": str(ladder_path.relative_to(repo_root)).replace("\\", "/"),
            "rule": "Goal 23 reuses the STEP-derived Goal 20 GLB and only renders stills for material review.",
        },
        "renderProfile": {
            "width": render_profile["width"],
            "height": render_profile["height"],
            "samples": render_profile["samples"],
            "engine": "Cycles",
            "homepageConnected": False,
            "motionTestRendered": False,
            "frameSequenceRendered": False,
            "fullReleaseFrameCount": 0,
        },
        "materialDecision": {
            "castBlastedStainless": {
                "source": "Goal 22 cast satin roughness ladder",
                "selectedCandidate": "fine_r46_full_valve_micro_tune",
                "sourceCandidate": "fine_r46",
                "textureBand": "fine/bead hybrid cast satin",
                "roughness": 0.40,
                "materialName": "goal23_castBlastedStainless",
            },
            "polishedStainlessBall": "Goal 22 polished ball soft/mirror direction, kept unchanged after review focus moved to satin cast body",
            "softSealPtfe": "Goal 22 warm off-white PTFE direction",
            "graphitePacking": "Goal 22 matte graphite/dark seal direction",
            "fastenerStainless": "Goal 22 fastener stainless direction, brightened for full-valve separation",
        },
        "goal22Evidence": {
            "ladderStill": goal22_ladder["still"]["path"],
            "ladderSha256": goal22_ladder["still"]["sha256"],
            "selectedCandidate": next(
                item for item in goal22_ladder["swatches"] if item["id"] == "fine_r46"
            ),
        },
        "lighting": {
            "hdri": str(hdri_path.relative_to(repo_root)).replace("\\", "/") if hdri_path.is_file() else None,
            "strategy": "darker neutral grey studio, reduced HDRI/white-panel strength, broad softboxes, and camera-invisible charcoal reflection flags for steel dark values; no animation lighting",
            "areaLights": [
                "goal23_left_broad_softbox",
                "goal23_top_long_soft_strip",
                "goal23_right_edge_softbox",
                "goal23_front_low_fill",
            ],
            "reflectionFlags": [
                "goal23_left_charcoal_reflection_flag",
                "goal23_overhead_charcoal_reflection_flag",
            ],
        },
        "partIdentity": {
            "meshCount": len(meshes),
            "sourceStepProductNameCount": len(step_audit["productNames"]),
            "goal20MeshCount": goal20_semantic_map["partCounts"],
            "focusPartCount": len(focus_parts),
        },
        "groupCounts": group_counts,
        "materialCounts": material_counts,
        "partCounts": part_counts,
        "focusParts": focus_parts,
        "stills": stills,
        "constraints": [
            "No homepage hero replacement is performed.",
            "No 24-frame or 240-frame animation is rendered.",
            "Material labels remain visual treatments, not certified product material claims.",
            "Goal 23 is a first full-valve material still pass for review and micro-tuning only.",
        ],
    }
    write_json(goal_dir / "render-manifest.json", manifest)
    write_material_status(goal_dir, manifest)
    write_index(goal_dir, manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
