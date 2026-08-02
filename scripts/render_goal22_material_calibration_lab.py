#!/usr/bin/env python3
"""Render a tiny Blender/Cycles material calibration contact sheet.

This intentionally avoids the full valve model. It renders small centered
primitives so industrial metal materials can be judged in minutes before any
full STEP/GLB valve render is attempted again.

Run inside Blender:
blender --background --python scripts/render_goal22_material_calibration_lab.py -- --repo-root . --profile smoke
"""

from __future__ import annotations

import argparse
import hashlib
import html
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

REFERENCE_IMAGES = [
    {
        "id": "reference-full-valve",
        "name": "商业参考：完整阀门",
        "path": "references/reference-full-valve.png",
    },
    {
        "id": "reference-exploded",
        "name": "商业参考：爆炸图",
        "path": "references/reference-exploded.png",
    },
]

RESEARCH_LINKS = [
    {
        "label": "Poly Haven CC0 HDRIs / textures",
        "url": "https://polyhaven.com/license",
        "note": "可用 CC0 studio HDRI 和反射环境，但本轮先用程序化棚拍反射板，避免下载依赖。",
    },
    {
        "label": "ambientCG CC0 PBR materials",
        "url": "https://ambientcg.com/",
        "note": "有 CC0 PBR 贴图和 metal 类资源，可作为下一轮真实贴图库来源。",
    },
    {
        "label": "Blender Principled BSDF",
        "url": "https://docs.blender.org/manual/en/latest/render/shader_nodes/shader/principled.html",
        "note": "金属/粗糙度/各向异性控制仍是 Blender/Cycles 主线做法。",
    },
    {
        "label": "Sketchfab flanged valve examples",
        "url": "https://sketchfab.com/search?features=downloadable&q=flanged%20ball%20valve&type=models",
        "note": "只做视觉学习；下载或复用必须逐个检查模型授权。",
    },
    {
        "label": "GrabCAD flanged ball valve examples",
        "url": "https://grabcad.com/library?query=flanged%20ball%20valve&sort=most_downloaded",
        "note": "常见工业 CAD/KeyShot 预览可学习镜头和材质，但授权不可默认商用复用。",
    },
]


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
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.lights, bpy.data.cameras):
        for item in list(block):
            if item.users == 0:
                block.remove(item)


def set_input(node, names: list[str], value) -> None:
    for name in names:
        if name in node.inputs:
            node.inputs[name].default_value = value
            return


def configure_render(profile: str) -> dict:
    profiles = {
        "smoke": {"width": 1800, "height": 1440, "samples": 64},
        "proof": {"width": 2400, "height": 1920, "samples": 128},
    }
    selected = profiles[profile]
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = selected["samples"]
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 10
    scene.cycles.diffuse_bounces = 3
    scene.cycles.glossy_bounces = 6
    scene.cycles.transparent_max_bounces = 8
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
    roughness_low: float | None = None,
    roughness_high: float | None = None,
    roughness_scale: float = 80.0,
    bump_strength: float = 0.0,
    bump_distance: float = 0.001,
    bump_scale: float = 100.0,
    noise_detail: float = 12.0,
) -> None:
    if not principled:
        return
    nodes = material.node_tree.nodes
    links = material.node_tree.links

    color_noise = nodes.new(type="ShaderNodeTexNoise")
    color_noise.inputs["Scale"].default_value = color_scale
    color_noise.inputs["Detail"].default_value = noise_detail
    color_noise.inputs["Roughness"].default_value = 0.56
    color_ramp = nodes.new(type="ShaderNodeValToRGB")
    color_ramp.color_ramp.elements[0].position = 0.12
    color_ramp.color_ramp.elements[0].color = color_low
    color_ramp.color_ramp.elements[1].position = 1.0
    color_ramp.color_ramp.elements[1].color = color_high
    links.new(color_noise.outputs["Fac"], color_ramp.inputs["Fac"])
    links.new(color_ramp.outputs["Color"], principled.inputs["Base Color"])

    if roughness_low is not None and roughness_high is not None:
        roughness_noise = nodes.new(type="ShaderNodeTexNoise")
        roughness_noise.inputs["Scale"].default_value = roughness_scale
        roughness_noise.inputs["Detail"].default_value = noise_detail
        roughness_noise.inputs["Roughness"].default_value = 0.55
        roughness_ramp = nodes.new(type="ShaderNodeValToRGB")
        roughness_ramp.color_ramp.elements[0].position = 0.18
        roughness_ramp.color_ramp.elements[0].color = (roughness_low, roughness_low, roughness_low, 1.0)
        roughness_ramp.color_ramp.elements[1].position = 1.0
        roughness_ramp.color_ramp.elements[1].color = (roughness_high, roughness_high, roughness_high, 1.0)
        links.new(roughness_noise.outputs["Fac"], roughness_ramp.inputs["Fac"])
        links.new(roughness_ramp.outputs["Color"], principled.inputs["Roughness"])

    if bump_strength:
        bump_noise = nodes.new(type="ShaderNodeTexNoise")
        bump_noise.inputs["Scale"].default_value = bump_scale
        bump_noise.inputs["Detail"].default_value = noise_detail
        bump_noise.inputs["Roughness"].default_value = 0.50
        bump = nodes.new(type="ShaderNodeBump")
        bump.inputs["Strength"].default_value = bump_strength
        bump.inputs["Distance"].default_value = bump_distance
        links.new(bump_noise.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], principled.inputs["Normal"])


def make_material_catalog() -> list[dict]:
    specs = [
        {
            "id": "cast_satin_baseline",
            "label": "cast satin stainless baseline",
            "primitive": "coupon",
            "material": {
                "base": (0.37, 0.38, 0.36, 1.0),
                "metallic": 1.0,
                "roughness": 0.38,
                "coat": 0.04,
                "anisotropic": 0.18,
                "noise": {
                    "low": (0.30, 0.31, 0.30, 1.0),
                    "high": (0.45, 0.46, 0.43, 1.0),
                    "color_scale": 520,
                    "roughness_low": 0.34,
                    "roughness_high": 0.48,
                    "roughness_scale": 380,
                    "bump_strength": 0.004,
                    "bump_distance": 0.0010,
                    "bump_scale": 700,
                },
            },
        },
        {
            "id": "cast_darker_satin",
            "label": "cast darker satin stainless",
            "primitive": "coupon",
            "material": {
                "base": (0.30, 0.31, 0.30, 1.0),
                "metallic": 1.0,
                "roughness": 0.34,
                "coat": 0.03,
                "anisotropic": 0.16,
                "noise": {
                    "low": (0.24, 0.25, 0.24, 1.0),
                    "high": (0.40, 0.41, 0.39, 1.0),
                    "color_scale": 440,
                    "roughness_low": 0.30,
                    "roughness_high": 0.45,
                    "roughness_scale": 310,
                    "bump_strength": 0.003,
                    "bump_distance": 0.0008,
                    "bump_scale": 620,
                },
            },
        },
        {
            "id": "fine_bead_blast_low",
            "label": "fine bead blast low contrast",
            "primitive": "coupon",
            "material": {
                "base": (0.35, 0.36, 0.34, 1.0),
                "metallic": 1.0,
                "roughness": 0.48,
                "coat": 0.0,
                "anisotropic": 0.12,
                "noise": {
                    "low": (0.29, 0.30, 0.29, 1.0),
                    "high": (0.43, 0.44, 0.41, 1.0),
                    "color_scale": 1150,
                    "roughness_low": 0.42,
                    "roughness_high": 0.56,
                    "roughness_scale": 900,
                    "bump_strength": 0.006,
                    "bump_distance": 0.0011,
                    "bump_scale": 1400,
                },
            },
        },
        {
            "id": "fine_bead_blast_normal",
            "label": "fine bead blast stronger normal",
            "primitive": "coupon",
            "material": {
                "base": (0.34, 0.35, 0.33, 1.0),
                "metallic": 1.0,
                "roughness": 0.52,
                "coat": 0.0,
                "anisotropic": 0.10,
                "noise": {
                    "low": (0.28, 0.29, 0.28, 1.0),
                    "high": (0.42, 0.43, 0.40, 1.0),
                    "color_scale": 1550,
                    "roughness_low": 0.46,
                    "roughness_high": 0.60,
                    "roughness_scale": 1250,
                    "bump_strength": 0.011,
                    "bump_distance": 0.0013,
                    "bump_scale": 1900,
                },
            },
        },
        {
            "id": "sandblast_mid_grey",
            "label": "sandblast grey midtone",
            "primitive": "coupon",
            "material": {
                "base": (0.32, 0.33, 0.31, 1.0),
                "metallic": 1.0,
                "roughness": 0.58,
                "coat": 0.0,
                "anisotropic": 0.04,
                "noise": {
                    "low": (0.25, 0.26, 0.25, 1.0),
                    "high": (0.39, 0.40, 0.38, 1.0),
                    "color_scale": 1900,
                    "roughness_low": 0.52,
                    "roughness_high": 0.66,
                    "roughness_scale": 1450,
                    "bump_strength": 0.014,
                    "bump_distance": 0.0016,
                    "bump_scale": 2300,
                },
            },
        },
        {
            "id": "brochure_satin_cast",
            "label": "brochure-like smooth satin",
            "primitive": "coupon",
            "material": {
                "base": (0.42, 0.43, 0.40, 1.0),
                "metallic": 1.0,
                "roughness": 0.30,
                "coat": 0.08,
                "anisotropic": 0.24,
                "noise": {
                    "low": (0.34, 0.35, 0.33, 1.0),
                    "high": (0.52, 0.53, 0.49, 1.0),
                    "color_scale": 250,
                    "roughness_low": 0.26,
                    "roughness_high": 0.40,
                    "roughness_scale": 180,
                    "bump_strength": 0.002,
                    "bump_distance": 0.0007,
                    "bump_scale": 420,
                },
            },
        },
        {
            "id": "machined_stainless_bright",
            "label": "machined stainless bright",
            "primitive": "cylinder",
            "material": {
                "base": (0.58, 0.59, 0.56, 1.0),
                "metallic": 1.0,
                "roughness": 0.20,
                "coat": 0.12,
                "anisotropic": 0.72,
                "noise": {
                    "low": (0.45, 0.46, 0.44, 1.0),
                    "high": (0.72, 0.73, 0.68, 1.0),
                    "color_scale": 95,
                    "roughness_low": 0.16,
                    "roughness_high": 0.28,
                    "roughness_scale": 80,
                    "bump_strength": 0.002,
                    "bump_distance": 0.0008,
                    "bump_scale": 130,
                },
            },
        },
        {
            "id": "machined_stainless_darker",
            "label": "machined stainless darker",
            "primitive": "cylinder",
            "material": {
                "base": (0.42, 0.43, 0.41, 1.0),
                "metallic": 1.0,
                "roughness": 0.24,
                "coat": 0.08,
                "anisotropic": 0.76,
                "noise": {
                    "low": (0.32, 0.33, 0.31, 1.0),
                    "high": (0.58, 0.59, 0.55, 1.0),
                    "color_scale": 115,
                    "roughness_low": 0.18,
                    "roughness_high": 0.32,
                    "roughness_scale": 95,
                    "bump_strength": 0.003,
                    "bump_distance": 0.0010,
                    "bump_scale": 165,
                },
            },
        },
        {
            "id": "brushed_aniso_stainless",
            "label": "brushed anisotropic stainless",
            "primitive": "cylinder",
            "material": {
                "base": (0.48, 0.49, 0.46, 1.0),
                "metallic": 1.0,
                "roughness": 0.31,
                "coat": 0.06,
                "anisotropic": 0.92,
                "noise": {
                    "low": (0.36, 0.37, 0.35, 1.0),
                    "high": (0.68, 0.69, 0.64, 1.0),
                    "color_scale": 55,
                    "roughness_low": 0.22,
                    "roughness_high": 0.42,
                    "roughness_scale": 65,
                    "bump_strength": 0.004,
                    "bump_distance": 0.0011,
                    "bump_scale": 75,
                },
            },
        },
        {
            "id": "polished_ball_mirror",
            "label": "polished stainless ball mirror",
            "primitive": "sphere",
            "material": {
                "base": (0.78, 0.79, 0.76, 1.0),
                "metallic": 1.0,
                "roughness": 0.045,
                "coat": 0.18,
                "coat_roughness": 0.06,
                "anisotropic": 0.0,
            },
        },
        {
            "id": "polished_ball_soft_studio",
            "label": "polished ball soft studio",
            "primitive": "sphere",
            "material": {
                "base": (0.72, 0.74, 0.71, 1.0),
                "metallic": 1.0,
                "roughness": 0.080,
                "coat": 0.16,
                "coat_roughness": 0.08,
                "anisotropic": 0.0,
            },
        },
        {
            "id": "polished_ball_darker",
            "label": "polished ball darker studio",
            "primitive": "sphere",
            "material": {
                "base": (0.60, 0.61, 0.58, 1.0),
                "metallic": 1.0,
                "roughness": 0.060,
                "coat": 0.12,
                "coat_roughness": 0.07,
                "anisotropic": 0.0,
            },
        },
        {
            "id": "chrome_like_ring",
            "label": "chrome-like machined ring",
            "primitive": "torus",
            "material": {
                "base": (0.74, 0.75, 0.72, 1.0),
                "metallic": 1.0,
                "roughness": 0.115,
                "coat": 0.18,
                "coat_roughness": 0.06,
                "anisotropic": 0.18,
            },
        },
        {
            "id": "fastener_stainless",
            "label": "fastener stainless",
            "primitive": "bolt",
            "material": {
                "base": (0.47, 0.48, 0.45, 1.0),
                "metallic": 1.0,
                "roughness": 0.27,
                "coat": 0.08,
                "anisotropic": 0.55,
                "noise": {
                    "low": (0.35, 0.36, 0.34, 1.0),
                    "high": (0.62, 0.63, 0.58, 1.0),
                    "color_scale": 130,
                    "roughness_low": 0.20,
                    "roughness_high": 0.38,
                    "roughness_scale": 105,
                    "bump_strength": 0.002,
                    "bump_distance": 0.0009,
                    "bump_scale": 155,
                },
            },
        },
        {
            "id": "graphite_matte_black",
            "label": "graphite packing matte black",
            "primitive": "torus",
            "material": {
                "base": (0.016, 0.017, 0.018, 1.0),
                "metallic": 0.08,
                "roughness": 0.72,
                "coat": 0.0,
                "anisotropic": 0.0,
                "noise": {
                    "low": (0.006, 0.006, 0.007, 1.0),
                    "high": (0.060, 0.062, 0.062, 1.0),
                    "color_scale": 70,
                    "roughness_low": 0.62,
                    "roughness_high": 0.88,
                    "roughness_scale": 100,
                    "bump_strength": 0.020,
                    "bump_distance": 0.0032,
                    "bump_scale": 110,
                },
            },
        },
        {
            "id": "graphite_slight_metal",
            "label": "graphite packing slight sheen",
            "primitive": "torus",
            "material": {
                "base": (0.025, 0.026, 0.027, 1.0),
                "metallic": 0.22,
                "roughness": 0.54,
                "coat": 0.02,
                "anisotropic": 0.12,
                "noise": {
                    "low": (0.010, 0.010, 0.011, 1.0),
                    "high": (0.090, 0.092, 0.090, 1.0),
                    "color_scale": 80,
                    "roughness_low": 0.44,
                    "roughness_high": 0.70,
                    "roughness_scale": 115,
                    "bump_strength": 0.015,
                    "bump_distance": 0.0026,
                    "bump_scale": 125,
                },
            },
        },
        {
            "id": "black_rubber_seal",
            "label": "black rubber seal",
            "primitive": "torus",
            "material": {
                "base": (0.010, 0.011, 0.011, 1.0),
                "metallic": 0.0,
                "roughness": 0.44,
                "coat": 0.08,
                "coat_roughness": 0.18,
                "anisotropic": 0.0,
                "noise": {
                    "low": (0.006, 0.006, 0.006, 1.0),
                    "high": (0.042, 0.044, 0.043, 1.0),
                    "color_scale": 45,
                    "roughness_low": 0.34,
                    "roughness_high": 0.56,
                    "roughness_scale": 60,
                    "bump_strength": 0.004,
                    "bump_distance": 0.0016,
                    "bump_scale": 70,
                },
            },
        },
        {
            "id": "ptfe_warm_off_white",
            "label": "PTFE warm off-white",
            "primitive": "torus",
            "material": {
                "base": (0.70, 0.64, 0.50, 1.0),
                "metallic": 0.0,
                "roughness": 0.56,
                "coat": 0.03,
                "coat_roughness": 0.24,
                "anisotropic": 0.0,
                "noise": {
                    "low": (0.52, 0.48, 0.38, 1.0),
                    "high": (0.84, 0.78, 0.62, 1.0),
                    "color_scale": 55,
                    "roughness_low": 0.48,
                    "roughness_high": 0.70,
                    "roughness_scale": 72,
                    "bump_strength": 0.003,
                    "bump_distance": 0.0015,
                    "bump_scale": 90,
                },
            },
        },
        {
            "id": "ptfe_pale_grey",
            "label": "PTFE pale grey",
            "primitive": "torus",
            "material": {
                "base": (0.62, 0.62, 0.58, 1.0),
                "metallic": 0.0,
                "roughness": 0.52,
                "coat": 0.03,
                "coat_roughness": 0.22,
                "anisotropic": 0.0,
                "noise": {
                    "low": (0.48, 0.49, 0.46, 1.0),
                    "high": (0.78, 0.78, 0.72, 1.0),
                    "color_scale": 45,
                    "roughness_low": 0.44,
                    "roughness_high": 0.66,
                    "roughness_scale": 65,
                    "bump_strength": 0.003,
                    "bump_distance": 0.0013,
                    "bump_scale": 82,
                },
            },
        },
        {
            "id": "dark_inner_bore",
            "label": "dark inner bore / cavity",
            "primitive": "cylinder",
            "material": {
                "base": (0.030, 0.031, 0.030, 1.0),
                "metallic": 0.85,
                "roughness": 0.38,
                "coat": 0.02,
                "anisotropic": 0.20,
                "noise": {
                    "low": (0.012, 0.013, 0.013, 1.0),
                    "high": (0.120, 0.122, 0.116, 1.0),
                    "color_scale": 100,
                    "roughness_low": 0.30,
                    "roughness_high": 0.54,
                    "roughness_scale": 120,
                    "bump_strength": 0.005,
                    "bump_distance": 0.0012,
                    "bump_scale": 150,
                },
            },
        },
    ]

    catalog = []
    for spec in specs:
        params = spec["material"]
        material, principled = make_principled(
            f"goal22_{spec['id']}",
            params["base"],
            params["metallic"],
            params["roughness"],
            params.get("coat", 0.0),
            params.get("coat_roughness", 0.18),
            params.get("anisotropic", 0.0),
        )
        if "noise" in params:
            noise = params["noise"]
            add_noise_variation(
                material,
                principled,
                noise["low"],
                noise["high"],
                noise["color_scale"],
                noise.get("roughness_low"),
                noise.get("roughness_high"),
                noise.get("roughness_scale", 80),
                noise.get("bump_strength", 0.0),
                noise.get("bump_distance", 0.001),
                noise.get("bump_scale", 100),
            )
        catalog.append({**spec, "blenderMaterial": material})
    return catalog


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


def add_bevelled_cube(name: str, material, location, scale, bevel_width: float = 0.055):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.rotation_euler = (math.radians(0), math.radians(0), math.radians(-7))
    obj.data.materials.append(material)
    bevel = obj.modifiers.new("goal22_soft_radius", "BEVEL")
    bevel.width = bevel_width
    bevel.segments = 10
    bevel.affect = "EDGES"
    weighted = obj.modifiers.new("goal22_weighted_normals", "WEIGHTED_NORMAL")
    weighted.keep_sharp = True
    return obj


def add_cylinder(name: str, material, location, radius: float = 0.28, depth: float = 0.46, rotation=(math.radians(90), 0, math.radians(-8)), vertices: int = 96):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    bevel = obj.modifiers.new("goal22_edge_break", "BEVEL")
    bevel.width = 0.025
    bevel.segments = 5
    weighted = obj.modifiers.new("goal22_weighted_normals", "WEIGHTED_NORMAL")
    weighted.keep_sharp = True
    return obj


def add_torus(name: str, material, location, major_radius: float = 0.24, minor_radius: float = 0.055, rotation=(math.radians(90), 0, math.radians(-9))):
    bpy.ops.mesh.primitive_torus_add(
        major_segments=128,
        minor_segments=24,
        location=location,
        major_radius=major_radius,
        minor_radius=minor_radius,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    weighted = obj.modifiers.new("goal22_weighted_normals", "WEIGHTED_NORMAL")
    weighted.keep_sharp = True
    return obj


def add_bolt(name: str, material, location):
    x, y, z = location
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.24, depth=0.20, location=(x, y, z + 0.16), rotation=(0, 0, math.radians(30)))
    head = bpy.context.object
    head.name = f"{name}_hex_head"
    head.data.materials.append(material)
    bevel = head.modifiers.new("goal22_head_edge_break", "BEVEL")
    bevel.width = 0.018
    bevel.segments = 3
    head.modifiers.new("goal22_head_weighted_normals", "WEIGHTED_NORMAL")

    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.13, depth=0.36, location=(x, y, z - 0.10), rotation=(0, 0, 0))
    shaft = bpy.context.object
    shaft.name = f"{name}_shaft"
    shaft.data.materials.append(material)
    shaft.modifiers.new("goal22_shaft_weighted_normals", "WEIGHTED_NORMAL")
    return head


def add_primitive_for_spec(spec: dict, location):
    material = spec["blenderMaterial"]
    primitive = spec["primitive"]
    name = f"goal22_swatch_{spec['id']}"
    if primitive == "coupon":
        return add_bevelled_cube(name, material, (location[0], location[1], location[2] + 0.20), (0.46, 0.38, 0.22))
    if primitive == "cylinder":
        return add_cylinder(name, material, (location[0], location[1], location[2] + 0.26))
    if primitive == "sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(segments=128, ring_count=64, radius=0.30, location=(location[0], location[1], location[2] + 0.31))
        obj = bpy.context.object
        obj.name = name
        obj.data.materials.append(material)
        obj.modifiers.new("goal22_sphere_weighted_normals", "WEIGHTED_NORMAL")
        return obj
    if primitive == "torus":
        return add_torus(name, material, (location[0], location[1], location[2] + 0.31))
    if primitive == "bolt":
        return add_bolt(name, material, (location[0], location[1], location[2] + 0.14))
    raise ValueError(f"Unknown primitive: {primitive}")


def build_scene(catalog: list[dict]) -> None:
    floor = add_simple_material("goal22_contact_sheet_warm_grey_floor", (0.36, 0.37, 0.35, 1.0), 0.86)
    pad = add_simple_material("goal22_contact_sheet_cell_pad", (0.44, 0.45, 0.43, 1.0), 0.80)
    white_panel = add_simple_material("goal22_contact_sheet_white_reflection_panel", (0.78, 0.79, 0.76, 1.0), 0.66)
    black_panel = add_simple_material("goal22_contact_sheet_black_reflection_flag", (0.028, 0.030, 0.032, 1.0), 0.78)
    charcoal_panel = add_simple_material("goal22_contact_sheet_charcoal_reflection_flag", (0.10, 0.105, 0.10, 1.0), 0.82)

    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.color = (0.34, 0.35, 0.34)

    add_plane("goal22_contact_sheet_floor", floor, (0, 0, -0.015), (8.3, 5.7, 1))
    add_plane(
        "goal22_contact_sheet_rear_cyc_wall",
        floor,
        (0, 4.20, 2.10),
        (8.4, 5.1, 1),
        rotation=(math.radians(68), 0, 0),
    )

    add_plane(
        "goal22_left_softbox_reflection",
        white_panel,
        (-5.4, -0.65, 1.55),
        (1.20, 5.0, 1),
        rotation=(0, math.radians(70), 0),
        camera_visible=False,
    )
    add_plane(
        "goal22_right_softbox_reflection",
        white_panel,
        (5.4, -0.25, 1.40),
        (1.10, 5.0, 1),
        rotation=(0, math.radians(-70), 0),
        camera_visible=False,
    )
    add_plane(
        "goal22_top_black_reflection_flag",
        black_panel,
        (0, -0.60, 4.15),
        (6.5, 0.62, 1),
        rotation=(math.radians(82), 0, 0),
        camera_visible=False,
    )
    add_plane(
        "goal22_front_charcoal_reflection_flag",
        charcoal_panel,
        (0, -4.40, 0.95),
        (7.5, 0.70, 1),
        rotation=(math.radians(78), 0, 0),
        camera_visible=False,
    )
    add_plane(
        "goal22_center_dark_vertical_flag",
        black_panel,
        (0.05, -4.85, 1.25),
        (0.34, 2.8, 1),
        rotation=(0, 0, 0),
        camera_visible=False,
    )

    add_area_light("goal22_contact_left_key", (-4.6, -4.1, 4.2), (0, 0, 0.5), 780, 5.6)
    add_area_light("goal22_contact_top_strip", (0.0, -1.4, 5.2), (0, 0.2, 0.2), 260, (0.48, 5.6))
    add_area_light("goal22_contact_right_edge", (4.4, -0.2, 2.4), (0, 0, 0.35), 135, 3.4)
    add_area_light("goal22_contact_front_fill", (0.0, -5.2, 1.35), (0, 0, 0.20), 35, 4.0)

    columns = 5
    cell_w = 1.38
    cell_d = 1.14
    start_x = -cell_w * (columns - 1) / 2
    start_y = 1.70
    for index, spec in enumerate(catalog):
        col = index % columns
        row = index // columns
        x = start_x + col * cell_w
        y = start_y - row * cell_d
        add_plane(
            f"goal22_cell_pad_{spec['id']}",
            pad,
            (x, y, 0.005),
            (0.64, 0.48, 1),
            rotation=(0, 0, 0),
        )
        add_primitive_for_spec(spec, (x, y, 0.0))

    camera_data = bpy.data.cameras.new("goal22_contact_sheet_camera")
    camera = bpy.data.objects.new("goal22_contact_sheet_camera", camera_data)
    bpy.context.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    camera.location = (0.0, -7.8, 4.65)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 7.55
    camera.data.shift_y = -0.13
    look_at(camera, (0.0, 0.04, 0.46))


def render(repo_root: Path, out_dir: Path, render_profile: dict) -> dict:
    output_path = out_dir / "01-material-contact-sheet.png"
    bpy.context.scene.render.filepath = str(output_path)
    bpy.ops.render.render(write_still=True)
    return {
        "id": "material-contact-sheet",
        "name": "20 材质小样 contact sheet",
        "path": str(output_path.relative_to(repo_root)).replace("\\", "/"),
        "width": render_profile["width"],
        "height": render_profile["height"],
        "bytes": output_path.stat().st_size,
        "sha256": sha256(output_path),
    }


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def existing_references(goal_dir: Path) -> list[dict]:
    result = []
    for ref in REFERENCE_IMAGES:
        full_path = goal_dir / ref["path"]
        if not full_path.exists():
            continue
        result.append(
            {
                **ref,
                "bytes": full_path.stat().st_size,
                "sha256": sha256(full_path),
            }
        )
    return result


def write_index(goal_dir: Path, manifest: dict) -> None:
    still = manifest["still"]
    still_src = html.escape(still["path"].split("/goal22-material-calibration-lab/")[-1])
    reference_figures = []
    for ref in manifest["references"]:
        reference_figures.append(
            f"""    <figure>
      <img src=\"{html.escape(ref['path'])}\" alt=\"{html.escape(ref['name'])}\">
      <figcaption>
        <b>{html.escape(ref['name'])}</b>
        <span>目标：中灰喷砂/缎面铸造不锈钢 + 受控棚拍反射 + 深色密封/内腔。</span>
      </figcaption>
    </figure>"""
        )
    reference_html = "\n".join(reference_figures) or "    <p>参考图尚未复制到 references/。</p>"
    swatch_items = "\n".join(
        f"<li><code>{html.escape(item['id'])}</code><span>{html.escape(item['label'])}</span></li>"
        for item in manifest["swatches"]
    )
    research_items = "\n".join(
        f"<li><a href=\"{html.escape(link['url'])}\">{html.escape(link['label'])}</a><span>{html.escape(link['note'])}</span></li>"
        for link in manifest["researchLinks"]
    )
    html_text = f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>Goal 22 Material Contact Sheet</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: Inter, \"Noto Sans SC\", system-ui, sans-serif;
      background: #e6e8e6;
      color: #101418;
    }}
    body {{ margin: 0; }}
    main {{ width: min(1440px, calc(100% - 36px)); margin: 0 auto; padding: 32px 0 56px; }}
    header {{ display: grid; gap: 10px; margin-bottom: 20px; }}
    .eyebrow {{ margin: 0; color: #667085; font-size: 13px; text-transform: uppercase; letter-spacing: .08em; }}
    h1 {{ margin: 0; font-size: clamp(28px, 4vw, 48px); line-height: 1.04; letter-spacing: 0; }}
    p {{ max-width: 860px; color: #475467; line-height: 1.6; margin: 0; }}
    section {{ margin-top: 28px; }}
    h2 {{ margin: 0 0 12px; font-size: 20px; letter-spacing: 0; }}
    .reference-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }}
    figure {{ margin: 0; border: 1px solid #cbd2d9; border-radius: 8px; background: #f7f8f6; overflow: hidden; }}
    img {{ display: block; width: 100%; height: auto; background: #d4d7d3; }}
    figcaption {{ display: grid; gap: 4px; padding: 11px 13px 13px; color: #475467; line-height: 1.45; }}
    figcaption b {{ color: #111827; }}
    code {{ background: #dfe3e6; padding: 2px 5px; border-radius: 5px; }}
    .swatches {{ columns: 2; padding-left: 20px; color: #475467; line-height: 1.55; }}
    .swatches li {{ break-inside: avoid; margin: 0 0 5px; }}
    .swatches span {{ margin-left: 6px; }}
    .links {{ display: grid; gap: 8px; padding-left: 20px; color: #475467; line-height: 1.55; }}
    .links li {{ padding-left: 2px; }}
    .links a {{ color: #1f4f76; font-weight: 650; text-decoration-thickness: 1px; }}
    .links span {{ display: block; }}
    @media (max-width: 780px) {{
      .reference-grid {{ grid-template-columns: 1fr; }}
      .swatches {{ columns: 1; }}
      main {{ width: min(100% - 24px, 1440px); padding-top: 22px; }}
    }}
  </style>
</head>
<body>
<main>
  <header>
    <p class=\"eyebrow\">Goal 22 / Blender Cycles tiny material lab</p>
    <h1>商业参考在前，20 个材质小样在后</h1>
    <p>这轮只验证材质和棚拍反射，不导入整台阀门，不做网页 hero，不做 24 帧或 240 帧动画。喷砂不锈钢不再往白色粉末方向调，优先看中灰金属底色和受控高光。</p>
  </header>

  <section>
    <h2>Commercial References</h2>
    <div class=\"reference-grid\">
{reference_html}
    </div>
  </section>

  <section>
    <h2>Contact Sheet</h2>
    <figure>
      <img src=\"{still_src}\" alt=\"{html.escape(still['name'])}\">
      <figcaption>
        <b>{html.escape(still['name'])}</b>
        <span>{manifest['renderProfile']['width']}x{manifest['renderProfile']['height']} / {manifest['renderProfile']['samples']} samples / Blender Cycles / full valve not imported</span>
      </figcaption>
    </figure>
  </section>

  <section>
    <h2>Swatch Order</h2>
    <ol class=\"swatches\">
{swatch_items}
    </ol>
  </section>

  <section>
    <h2>Research Notes</h2>
    <ul class=\"links\">
{research_items}
    </ul>
  </section>
</main>
</body>
</html>
"""
    (goal_dir / "index.html").write_text(html_text, encoding="utf-8")


def write_status(goal_dir: Path, manifest: dict) -> None:
    swatches = "\n".join(f"{idx}. `{item['id']}` - {item['label']}" for idx, item in enumerate(manifest["swatches"], 1))
    links = "\n".join(f"- [{link['label']}]({link['url']}): {link['note']}" for link in manifest["researchLinks"])
    text = f"""# Goal 22 Material Calibration Contact Sheet

Generated: {manifest['generatedAt']}

## Boundary

- This is a tiny Blender/Cycles material test.
- It renders 20 centered primitive swatches in one contact sheet.
- It does not import the full STEP/GLB valve.
- It does not replace the homepage hero.
- It does not render 24-frame or 240-frame animation.

## Visual Correction From Previous Attempt

- The cast/sandblasted stainless variants use medium grey metallic base values, not near-white.
- Roughness is tested in several moderate bands instead of pushing everything chalky and diffuse.
- The polished ball variants rely on broad reflection panels and dark flags, not random hard blocks.
- Graphite, rubber, PTFE, fastener, machined, and dark bore materials are separated so the white/grey pieces do not wash out the whole valve later.

## Swatches

{swatches}

## Open/Public Reference Direction

{links}

## Current Judgment

Use `index.html` for review: commercial references appear first, followed by the 20-swatch render. If none of the cast stainless variants hits the catalogue look, iterate this contact sheet again before touching the full valve.
"""
    (goal_dir / "material-status.md").write_text(text, encoding="utf-8")


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    goal_dir = out_dir.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    clear_scene()
    render_profile = configure_render(args.profile)
    catalog = make_material_catalog()
    build_scene(catalog)
    still = render(repo_root, out_dir, render_profile)

    manifest = {
        "schemaVersion": 2,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "goal": "Goal 22 tiny Blender material calibration contact sheet",
        "profile": args.profile,
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
        "references": existing_references(goal_dir),
        "researchLinks": RESEARCH_LINKS,
        "swatches": [
            {
                "id": item["id"],
                "label": item["label"],
                "primitive": item["primitive"],
                "materialName": item["blenderMaterial"].name,
            }
            for item in catalog
        ],
        "studio": {
            "strategy": "neutral grey studio, broad area lights, glossy-visible white panels, black and charcoal reflection flags",
            "purpose": "calibrate material appearance quickly before returning to the full CAD valve",
        },
        "still": still,
        "constraints": [
            "No full valve model is loaded.",
            "No homepage hero replacement is performed.",
            "No 24-frame or 240-frame animation is rendered.",
        ],
    }
    write_json(goal_dir / "render-manifest.json", manifest)
    write_status(goal_dir, manifest)
    write_index(goal_dir, manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
