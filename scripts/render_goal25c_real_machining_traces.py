#!/usr/bin/env python3
"""Render Goal 25-C real machining-trace material samples.

Goal 25-C deliberately avoids Blender procedural wave/noise/bump textures for
machining marks. The visible marks are explicit geometry: thin curve strokes,
torus rings, flush dark hole caps and small micro-pit discs. This makes the
lookdev result easier to reason about and prevents fake shader moire from
being mistaken for real tool marks.

Run inside Blender:
D:\\TOOLS\\render-pipeline\\apps\\Blender-5.2.0\\Blender Foundation\\Blender 5.2\\blender.exe --background --python scripts\\render_goal25c_real_machining_traces.py -- --repo-root . --profile smoke
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
from datetime import datetime, timezone
from pathlib import Path

try:
    import bpy
    from mathutils import Vector
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Run this script with Blender's Python interpreter.") from exc


GOAL20_DIR = "docs/assets/ztovalve/hero/goal20-blender-cycles-step-proof"
GOAL25C_DIR = "docs/assets/ztovalve/hero/goal25c-real-machining-traces"
RANDOM_SEED = 250503

TRACE_SPECS = [
    {
        "id": "G25-TRACE-MACH-FLANGE-RADIAL-GEOM-01",
        "label": "radial machined flange face",
        "cn": "法兰端面车削/平面加工痕",
        "builder": "flange_face",
        "intent": "Concentric tool-path rings and hole-rim witness marks are explicit torus geometry on a machined stainless flange coupon.",
        "appliesTo": "G25-SS-MACH-FLANGE-RADIAL-01",
    },
    {
        "id": "G25-TRACE-BRUSH-NO4-LINEAR-GEOM-01",
        "label": "No.4 linear brushed finish",
        "cn": "#4 线性拉丝/砂带痕",
        "builder": "linear_brush",
        "intent": "Overlapping short linear strokes with small angle and length variation are explicit curve geometry, not a shader wave.",
        "appliesTo": "G25-SS-BRUSH-NO4-LINEAR-01",
    },
    {
        "id": "G25-TRACE-MACH-BORE-CIRCULAR-GEOM-01",
        "label": "circular machined bore wall",
        "cn": "内孔环向加工痕",
        "builder": "bore_wall",
        "intent": "A cutaway bore wall uses circumferential curve rings at varying pitch to read as boring/turning marks inside the flow passage.",
        "appliesTo": "G25-SS-MACH-BORE-CIRCULAR-01",
    },
    {
        "id": "G25-TRACE-MACH-BOLT-BORE-DARK-GEOM-01",
        "label": "dark machined bolt bore",
        "cn": "螺栓孔暗加工内壁",
        "builder": "bolt_bore",
        "intent": "Small dark cylindrical hole caps and rim witness rings separate bolt bores from broad flange faces.",
        "appliesTo": "G25-SS-MACH-BOLT-BORE-DARK-01",
    },
    {
        "id": "G25-TRACE-EDGE-DEBURR-BURNISH-GEOM-01",
        "label": "edge deburr burnish",
        "cn": "倒角去毛刺磨亮痕",
        "builder": "edge_burnish",
        "intent": "Thin bright strokes on bevel-adjacent edges emulate final deburring and handling polish without brightening the whole part.",
        "appliesTo": "G25-SS-EDGE-BURNISH-01",
    },
    {
        "id": "G25-TRACE-BLAST-BEAD-MICROPIT-GEOM-01",
        "label": "bead blast micro pitting",
        "cn": "珠喷/喷砂微坑参考",
        "builder": "micro_pit",
        "intent": "Non-directional micro-pit dots are small geometry marks on a satin cast coupon, useful as the restrained boundary for blasted body surfaces.",
        "appliesTo": "G25-SS-CAST-BLASTED-SATIN-01",
    },
]

REFERENCE_NOTES = [
    {
        "id": "bssa-mechanical-finish",
        "title": "BSSA - Mechanically polished, brushed and buffed stainless finishes",
        "url": "https://bssa.org.uk/bssa_articles/specifying-mechanically-polished-brushed-and-buffed-stainless-steel-finishes-and-their-applications/",
        "takeaway": "Mechanical stainless finishes need named process intent and direction, not a generic roughness/noise label.",
    },
    {
        "id": "bssa-blasted-finish",
        "title": "BSSA - Bead and shot blasted stainless steel finishes",
        "url": "https://bssa.org.uk/bssa_articles/specifying-bead-and-shot-blasted-stainless-steel-finishes-and-their-applications/",
        "takeaway": "Blasted stainless is non-directional and low reflective; it should not become powder-white.",
    },
    {
        "id": "adobe-pbr-metal-roughness",
        "title": "Adobe Substance 3D - The PBR Guide",
        "url": "https://www.adobe.com/learn/substance-3d-designer/web/the-pbr-guide-part-2",
        "takeaway": "Separate metallic response from roughness/normal/detail data; machining traces should not be baked into diffuse whiteness.",
    },
    {
        "id": "openpbr-layering",
        "title": "OpenPBR Surface Specification",
        "url": "https://academysoftwarefoundation.github.io/OpenPBR/",
        "takeaway": "Layer material response and micro-surface detail explicitly so reusable trace methods can be attached to named base materials.",
    },
]

MATERIAL_SPECS = {
    "machinedFace": {
        "base_color": (0.46, 0.48, 0.45, 1.0),
        "metallic": 1.0,
        "roughness": 0.30,
        "anisotropic": 0.62,
        "coat": 0.040,
    },
    "brushedFace": {
        "base_color": (0.42, 0.44, 0.41, 1.0),
        "metallic": 1.0,
        "roughness": 0.36,
        "anisotropic": 0.86,
        "coat": 0.030,
    },
    "boreDark": {
        "base_color": (0.20, 0.22, 0.20, 1.0),
        "metallic": 1.0,
        "roughness": 0.38,
        "anisotropic": 0.58,
        "coat": 0.016,
    },
    "castSatin": {
        "base_color": (0.32, 0.34, 0.31, 1.0),
        "metallic": 1.0,
        "roughness": 0.48,
        "anisotropic": 0.18,
        "coat": 0.014,
    },
    "traceBright": {
        "base_color": (0.58, 0.60, 0.56, 1.0),
        "metallic": 1.0,
        "roughness": 0.28,
        "anisotropic": 0.55,
        "coat": 0.040,
    },
    "traceDark": {
        "base_color": (0.26, 0.28, 0.26, 1.0),
        "metallic": 1.0,
        "roughness": 0.62,
        "anisotropic": 0.25,
        "coat": 0.006,
    },
    "pitDark": {
        "base_color": (0.22, 0.24, 0.22, 1.0),
        "metallic": 1.0,
        "roughness": 0.64,
        "anisotropic": 0.10,
        "coat": 0.004,
    },
    "studioGrey": {
        "base_color": (0.30, 0.31, 0.30, 1.0),
        "metallic": 0.0,
        "roughness": 0.84,
        "anisotropic": 0.0,
        "coat": 0.0,
    },
    "softPanel": {
        "base_color": (0.76, 0.77, 0.73, 1.0),
        "metallic": 0.0,
        "roughness": 0.70,
        "anisotropic": 0.0,
        "coat": 0.0,
    },
    "charcoalFlag": {
        "base_color": (0.030, 0.032, 0.031, 1.0),
        "metallic": 0.0,
        "roughness": 0.78,
        "anisotropic": 0.0,
        "coat": 0.0,
    },
}


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    args = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--step-report", default=f"{GOAL20_DIR}/step-mesh-report.json")
    parser.add_argument("--hdri", default=f"{GOAL20_DIR}/studio_small_09_1k.hdr")
    parser.add_argument("--out-dir", default=f"{GOAL25C_DIR}/stills")
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


def make_material(name: str, spec: dict) -> bpy.types.Material:
    material = bpy.data.materials.new(f"goal25c_{name}")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    principled = nodes.get("Principled BSDF")
    if principled:
        set_input(principled, ["Base Color"], spec["base_color"])
        set_input(principled, ["Metallic"], spec.get("metallic", 0.0))
        set_input(principled, ["Roughness"], spec.get("roughness", 0.8))
        set_input(principled, ["Coat Weight", "Clearcoat"], spec.get("coat", 0.0))
        set_input(principled, ["Coat Roughness", "Clearcoat Roughness"], 0.18)
        set_input(principled, ["Anisotropic IOR Level", "Anisotropic"], spec.get("anisotropic", 0.0))
    material.diffuse_color = spec["base_color"]
    return material


def configure_render(profile: str) -> dict:
    profiles = {
        "smoke": {"contactWidth": 1800, "contactHeight": 1050, "cellWidth": 1000, "cellHeight": 640, "samples": 40},
        "proof": {"contactWidth": 2600, "contactHeight": 1517, "cellWidth": 1600, "cellHeight": 1024, "samples": 112},
    }
    selected = profiles[profile]
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = selected["samples"]
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 10
    scene.cycles.diffuse_bounces = 3
    scene.cycles.glossy_bounces = 7
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    try:
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "Medium High Contrast"
    except TypeError:
        pass
    scene.view_settings.exposure = -0.78
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


def build_studio(materials: dict[str, bpy.types.Material], hdri_path: Path | None) -> None:
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

    add_plane("goal25c_floor_reflection_only", materials["studioGrey"], (0.0, 0.20, -0.78), (5.0, 3.2, 1), camera_visible=False)
    add_plane(
        "goal25c_top_white_strip_reflection",
        materials["softPanel"],
        (0.0, -0.30, 1.22),
        (4.1, 0.28, 1),
        rotation=(math.radians(82), 0, 0),
        camera_visible=False,
    )
    add_plane(
        "goal25c_left_white_panel_reflection",
        materials["softPanel"],
        (-1.90, -0.30, 0.18),
        (0.62, 2.0, 1),
        rotation=(0, math.radians(74), 0),
        camera_visible=False,
    )
    add_plane(
        "goal25c_right_charcoal_flag_reflection",
        materials["charcoalFlag"],
        (1.88, -0.18, 0.18),
        (0.62, 2.0, 1),
        rotation=(0, math.radians(-74), 0),
        camera_visible=False,
    )

    add_area_light("goal25c_large_left_softbox", (-1.60, -1.72, 1.12), (0, 0, 0.1), 190, 3.2)
    add_area_light("goal25c_top_softbox", (0.0, -0.65, 1.55), (0, 0, 0.08), 118, (0.30, 3.2))
    add_area_light("goal25c_low_front_fill", (0.0, -1.55, -0.05), (0, 0, 0.0), 8, 1.45)


def add_disc_face(name: str, loc: tuple[float, float, float], radius: float, depth: float, material: bpy.types.Material, vertices: int = 192):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=loc,
        rotation=(math.radians(90), 0, 0),
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    bevel = obj.modifiers.new(f"{name}_soft_edge", "BEVEL")
    bevel.width = 0.004
    bevel.segments = 3
    weighted = obj.modifiers.new(f"{name}_weighted_normals", "WEIGHTED_NORMAL")
    weighted.keep_sharp = True
    return obj


def add_box_coupon(name: str, loc: tuple[float, float, float], dimensions: tuple[float, float, float], material: bpy.types.Material, bevel_width: float = 0.006):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    bevel = obj.modifiers.new(f"{name}_bevel", "BEVEL")
    bevel.width = bevel_width
    bevel.segments = 4
    weighted = obj.modifiers.new(f"{name}_weighted_normals", "WEIGHTED_NORMAL")
    weighted.keep_sharp = True
    return obj


def add_poly_curve(name: str, points: list[tuple[float, float, float]], material: bpy.types.Material, bevel_depth: float, resolution: int = 2):
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
    return obj


def add_ring(name: str, loc: tuple[float, float, float], radius: float, material: bpy.types.Material, thickness: float = 0.00055, segments: int = 240):
    bpy.ops.mesh.primitive_torus_add(
        major_segments=segments,
        minor_segments=6,
        major_radius=radius,
        minor_radius=thickness,
        location=loc,
        rotation=(math.radians(90), 0, 0),
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    return obj


def add_flush_disc(name: str, loc: tuple[float, float, float], radius: float, material: bpy.types.Material, depth: float = 0.0012, vertices: int = 48):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=loc,
        rotation=(math.radians(90), 0, 0),
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    return obj


def build_flange_face(origin: Vector, materials: dict[str, bpy.types.Material], rng: random.Random) -> dict:
    base = add_disc_face("trace_flange_radial_base", tuple(origin), 0.215, 0.030, materials["machinedFace"])
    front_y = origin.y - 0.016
    add_flush_disc("trace_flange_center_bore_dark", (origin.x, front_y - 0.001, origin.z), 0.060, materials["boreDark"], depth=0.002)
    add_ring("trace_flange_center_bore_bright_rim", (origin.x, front_y - 0.002, origin.z), 0.064, materials["traceBright"], thickness=0.00048)

    ring_radii = []
    radius = 0.074
    while radius < 0.199:
        pitch = rng.uniform(0.0048, 0.0094)
        if len(ring_radii) % 5 == 3:
            pitch += rng.uniform(0.0030, 0.0080)
        radius += pitch
        if radius < 0.199 and rng.random() > 0.12:
            ring_radii.append(radius + rng.uniform(-0.0007, 0.0009))
    last_bright = False
    for index, radius in enumerate(ring_radii):
        bright = (not last_bright) and rng.random() < 0.12
        last_bright = bright
        material = materials["traceBright"] if bright else materials["traceDark"]
        thickness = rng.uniform(0.00012, 0.00018) if bright else rng.uniform(0.00010, 0.00018)
        add_ring(f"trace_flange_tool_ring_{index:02d}", (origin.x, front_y - 0.0022, origin.z), radius, material, thickness=thickness, segments=256)

    for index in range(6):
        angle = math.radians(index * 60 + 12)
        hole_x = origin.x + math.cos(angle) * 0.156
        hole_z = origin.z + math.sin(angle) * 0.156
        add_flush_disc(f"trace_flange_bolt_hole_dark_{index:02d}", (hole_x, front_y - 0.0025, hole_z), 0.0145, materials["traceDark"], depth=0.002)
        add_ring(f"trace_flange_bolt_hole_rim_{index:02d}", (hole_x, front_y - 0.0032, hole_z), 0.0168, materials["traceBright"], thickness=0.00042, segments=72)

    return {"base": base.name, "rings": len(ring_radii), "boltHoles": 6}


def build_linear_brush(origin: Vector, materials: dict[str, bpy.types.Material], rng: random.Random) -> dict:
    add_box_coupon("trace_brush_plate_base", tuple(origin), (0.44, 0.030, 0.255), materials["brushedFace"], bevel_width=0.004)
    front_y = origin.y - 0.017
    stroke_count = 106
    for index in range(stroke_count):
        z = origin.z - 0.112 + rng.random() * 0.224
        x_center = origin.x + (rng.random() - 0.5) * 0.300
        length = 0.055 + rng.random() * 0.195
        if rng.random() < 0.18:
            length *= 1.25
        angle = math.radians((rng.random() - 0.5) * 1.25)
        dx = math.cos(angle) * length * 0.5
        dz = math.sin(angle) * length * 0.5
        x0 = max(origin.x - 0.200, x_center - dx)
        x1 = min(origin.x + 0.200, x_center + dx)
        z0 = z - dz
        z1 = z + dz
        bright = rng.random() < 0.055
        material = materials["traceBright"] if bright else materials["traceDark"]
        bevel = rng.uniform(0.00012, 0.00018) if bright else rng.uniform(0.00011, 0.00020)
        add_poly_curve(f"trace_brush_stroke_{index:03d}", [(x0, front_y - 0.0015, z0), (x1, front_y - 0.0015, z1)], material, bevel)

    return {"strokes": stroke_count}


def build_bore_wall(origin: Vector, materials: dict[str, bpy.types.Material], rng: random.Random) -> dict:
    radius = 0.150
    height = 0.280
    theta_min = math.radians(208)
    theta_max = math.radians(332)
    theta_steps = 36
    z_steps = 10
    verts = []
    faces = []
    for zi in range(z_steps + 1):
        z = origin.z - height * 0.5 + height * zi / z_steps
        for ti in range(theta_steps + 1):
            theta = theta_min + (theta_max - theta_min) * ti / theta_steps
            verts.append((origin.x + radius * math.cos(theta), origin.y + radius * math.sin(theta), z))
    for zi in range(z_steps):
        for ti in range(theta_steps):
            a = zi * (theta_steps + 1) + ti
            faces.append((a, a + 1, a + theta_steps + 2, a + theta_steps + 1))
    mesh = bpy.data.meshes.new("trace_bore_wall_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("trace_bore_wall_base", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(materials["boreDark"])
    weighted = obj.modifiers.new("trace_bore_wall_weighted_normals", "WEIGHTED_NORMAL")
    weighted.keep_sharp = True

    ring_positions = []
    local_z = -height * 0.43
    while local_z < height * 0.43:
        local_z += rng.uniform(0.0100, 0.0190)
        if rng.random() < 0.20:
            local_z += rng.uniform(0.0060, 0.0140)
        if local_z < height * 0.43:
            ring_positions.append(origin.z + local_z + rng.uniform(-0.0014, 0.0012))
    for index, z in enumerate(ring_positions):
        theta_a = theta_min + math.radians(rng.uniform(0.0, 10.0))
        theta_b = theta_max - math.radians(rng.uniform(0.0, 14.0))
        phase = rng.random() * math.tau
        wave = rng.choice((2.0, 3.0, 4.0))
        r = radius + rng.uniform(0.0004, 0.0011)
        points = []
        for ti in range(theta_steps + 1):
            theta = theta_a + (theta_b - theta_a) * ti / theta_steps
            z_wobble = z + math.sin(ti * wave / theta_steps * math.tau + phase) * 0.00055
            points.append((origin.x + r * math.cos(theta), origin.y + r * math.sin(theta) - 0.0004, z_wobble))
        bright = rng.random() < 0.07
        material = materials["traceBright"] if bright else materials["traceDark"]
        bevel = rng.uniform(0.00016, 0.00022) if bright else rng.uniform(0.00014, 0.00024)
        add_poly_curve(f"trace_bore_circular_mark_{index:02d}", points, material, bevel)

    return {"rings": len(ring_positions), "arcDegrees": round(math.degrees(theta_max - theta_min), 1)}


def build_bolt_bore(origin: Vector, materials: dict[str, bpy.types.Material]) -> dict:
    add_box_coupon("trace_bolt_bore_plate_base", tuple(origin), (0.42, 0.030, 0.250), materials["machinedFace"], bevel_width=0.004)
    front_y = origin.y - 0.017
    hole_positions = [(-0.115, 0.065), (0.015, 0.075), (0.125, 0.015), (-0.020, -0.080), (-0.135, -0.055)]
    for index, (dx, dz) in enumerate(hole_positions):
        x = origin.x + dx
        z = origin.z + dz
        add_flush_disc(f"trace_bolt_bore_dark_cap_{index:02d}", (x, front_y - 0.0015, z), 0.025, materials["boreDark"], depth=0.002, vertices=56)
        add_ring(f"trace_bolt_bore_outer_rim_{index:02d}", (x, front_y - 0.0024, z), 0.0275, materials["traceBright"], thickness=0.00055, segments=72)
        for ring in range(3):
            add_ring(
                f"trace_bolt_bore_inside_ring_{index:02d}_{ring:02d}",
                (x, front_y - 0.0030, z),
                0.0095 + ring * 0.0048,
                materials["traceDark"] if ring % 2 else materials["traceBright"],
                thickness=0.00032,
                segments=56,
            )
    return {"boltBores": len(hole_positions), "insideRingsPerHole": 3}


def build_edge_burnish(origin: Vector, materials: dict[str, bpy.types.Material], rng: random.Random) -> dict:
    add_box_coupon("trace_edge_burnish_block_base", tuple(origin), (0.42, 0.040, 0.235), materials["castSatin"], bevel_width=0.012)
    front_y = origin.y - 0.023
    strokes = [
        ((origin.x - 0.190, front_y - 0.0016, origin.z + 0.110), (origin.x + 0.190, front_y - 0.0016, origin.z + 0.110)),
        ((origin.x - 0.190, front_y - 0.0016, origin.z - 0.110), (origin.x + 0.190, front_y - 0.0016, origin.z - 0.110)),
        ((origin.x - 0.205, front_y - 0.0016, origin.z - 0.094), (origin.x - 0.205, front_y - 0.0016, origin.z + 0.094)),
        ((origin.x + 0.205, front_y - 0.0016, origin.z - 0.094), (origin.x + 0.205, front_y - 0.0016, origin.z + 0.094)),
    ]
    for index, (start, end) in enumerate(strokes):
        add_poly_curve(f"trace_edge_continuous_burnish_{index:02d}", [start, end], materials["traceBright"], 0.00075)
    short_count = 34
    for index in range(short_count):
        side = rng.randrange(4)
        if side < 2:
            z = origin.z + (0.106 if side == 0 else -0.106) + (rng.random() - 0.5) * 0.006
            x = origin.x - 0.170 + rng.random() * 0.340
            length = 0.015 + rng.random() * 0.035
            points = [(x - length * 0.5, front_y - 0.0022, z), (x + length * 0.5, front_y - 0.0022, z)]
        else:
            x = origin.x + (0.200 if side == 2 else -0.200) + (rng.random() - 0.5) * 0.006
            z = origin.z - 0.085 + rng.random() * 0.170
            length = 0.010 + rng.random() * 0.025
            points = [(x, front_y - 0.0022, z - length * 0.5), (x, front_y - 0.0022, z + length * 0.5)]
        add_poly_curve(f"trace_edge_short_witness_{index:02d}", points, materials["traceBright"], 0.00038)
    return {"continuousEdges": len(strokes), "shortWitnessMarks": short_count}


def build_micro_pit(origin: Vector, materials: dict[str, bpy.types.Material], rng: random.Random) -> dict:
    add_disc_face("trace_micro_pit_cast_base", tuple(origin), 0.205, 0.028, materials["castSatin"], vertices=160)
    front_y = origin.y - 0.0155
    dot_count = 118
    for index in range(dot_count):
        radius = 0.190 * math.sqrt(rng.random())
        angle = rng.random() * math.tau
        x = origin.x + math.cos(angle) * radius
        z = origin.z + math.sin(angle) * radius
        dot_radius = 0.0016 + rng.random() * 0.0030
        material = materials["pitDark"] if index % 4 else materials["traceBright"]
        add_flush_disc(f"trace_micro_pit_dot_{index:03d}", (x, front_y - 0.0012, z), dot_radius, material, depth=0.0009, vertices=14)
    return {"microPitDots": dot_count}


def build_trace_scene(materials: dict[str, bpy.types.Material]) -> dict:
    rng = random.Random(RANDOM_SEED)
    positions = {
        "G25-TRACE-MACH-FLANGE-RADIAL-GEOM-01": Vector((-0.56, 0.0, 0.245)),
        "G25-TRACE-BRUSH-NO4-LINEAR-GEOM-01": Vector((0.0, 0.0, 0.245)),
        "G25-TRACE-MACH-BORE-CIRCULAR-GEOM-01": Vector((0.56, 0.0, 0.245)),
        "G25-TRACE-MACH-BOLT-BORE-DARK-GEOM-01": Vector((-0.56, 0.0, -0.245)),
        "G25-TRACE-EDGE-DEBURR-BURNISH-GEOM-01": Vector((0.0, 0.0, -0.245)),
        "G25-TRACE-BLAST-BEAD-MICROPIT-GEOM-01": Vector((0.56, 0.0, -0.245)),
    }
    builders = {
        "flange_face": lambda origin: build_flange_face(origin, materials, rng),
        "linear_brush": lambda origin: build_linear_brush(origin, materials, rng),
        "bore_wall": lambda origin: build_bore_wall(origin, materials, rng),
        "bolt_bore": lambda origin: build_bolt_bore(origin, materials),
        "edge_burnish": lambda origin: build_edge_burnish(origin, materials, rng),
        "micro_pit": lambda origin: build_micro_pit(origin, materials, rng),
    }
    records = []
    for spec in TRACE_SPECS:
        origin = positions[spec["id"]]
        detail = builders[spec["builder"]](origin)
        records.append({**spec, "origin": [round(origin.x, 4), round(origin.y, 4), round(origin.z, 4)], "geometryDetail": detail})
    return {"records": records, "positions": {key: [round(v.x, 4), round(v.y, 4), round(v.z, 4)] for key, v in positions.items()}}


def create_camera() -> bpy.types.Object:
    camera_data = bpy.data.cameras.new("goal25c_trace_camera")
    camera = bpy.data.objects.new("goal25c_trace_camera", camera_data)
    bpy.context.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    camera.data.type = "ORTHO"
    set_contact_camera(camera)
    return camera


def set_contact_camera(camera: bpy.types.Object) -> None:
    camera.data.ortho_scale = 1.70
    camera.data.shift_y = 0.0
    camera.location = (0.0, -2.55, 0.02)
    look_at(camera, (0.0, 0.0, 0.02))


def set_cell_camera(camera: bpy.types.Object, origin: list[float]) -> None:
    camera.data.ortho_scale = 0.47
    camera.data.shift_y = 0.0
    camera.location = (origin[0], -2.10, origin[2] + 0.012)
    look_at(camera, (origin[0], 0.0, origin[2] + 0.012))


def render_png(repo_root: Path, output_path: Path, width: int, height: int, title: str) -> dict:
    scene = bpy.context.scene
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.filepath = str(output_path)
    bpy.ops.render.render(write_still=True)
    return {
        "id": output_path.stem,
        "title": title,
        "path": str(output_path.relative_to(repo_root)).replace("\\", "/"),
        "width": width,
        "height": height,
        "bytes": output_path.stat().st_size,
        "sha256": sha256(output_path),
    }


def write_status(goal_dir: Path, manifest: dict) -> None:
    trace_lines = "\n".join(
        f"- `{record['id']}`: {record['cn']} - {record['intent']} Applies to `{record['appliesTo']}`."
        for record in manifest["traceLibrary"]
    )
    outputs = "\n".join(f"- `{still['id']}`: {still['path']}" for still in manifest["stills"])
    refs = "\n".join(f"- [{ref['title']}]({ref['url']}): {ref['takeaway']}" for ref in REFERENCE_NOTES)
    text = f"""# Goal 25-C Real Machining Traces

Generated: {manifest['generatedAt']}

## Boundary

- This pass isolates machining-trace implementation methods as reusable samples.
- It does not render the full valve or replace the Goal 25-D zoned body proof.
- It does not publish Pages or create animation frames.
- Visible machining marks are explicit curve/torus/dot geometry, not Blender procedural `Wave`, `Noise`, or `Bump` shader nodes.
- Material names remain visual lookdev targets, not certified surface-finish claims.

## Trace Library

{trace_lines}

## Anti-Fake-Texture Rule

- No `ShaderNodeTexWave`.
- No `ShaderNodeTexNoise`.
- No shader `Bump` node.
- Trace direction comes from manufacturing semantics: concentric tool rings, linear brush strokes, bore circumferential bands, hole rims, edge witness marks and non-directional pit dots.

## External References Used

{refs}

## Output

{outputs}

## Review Questions

- Which trace family looks real enough to migrate back into the Goal 25-D valve-body zones?
- Are any marks too visually loud for commercial industrial photography?
- Should 25-C next add UV/tangent-bound texture maps for the actual STEP body, or keep the marks as explicit geometric overlays?
"""
    write_text_lf(goal_dir / "material-status.md", text)


def write_index(goal_dir: Path, manifest: dict) -> None:
    figures = []
    for still in manifest["stills"]:
        src = html.escape(still["path"].split("/goal25c-real-machining-traces/")[-1])
        figures.append(
            f"""
            <figure>
              <img src="{src}" alt="{html.escape(still['title'])}">
              <figcaption><b>{html.escape(still['title'])}</b><span>{html.escape(still['id'])}</span></figcaption>
            </figure>
            """
        )
    library = "".join(
        f"<li><b>{html.escape(record['id'])}</b><small>{html.escape(record['cn'])}</small><em>{html.escape(record['intent'])}</em><code>{html.escape(record['appliesTo'])}</code></li>"
        for record in manifest["traceLibrary"]
    )
    html_text = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Goal 25-C Real Machining Traces</title>
  <style>
    :root {{ color-scheme: light; font-family: Inter, "Noto Sans SC", system-ui, sans-serif; background: #e3e7e4; color: #101514; }}
    body {{ margin: 0; }}
    main {{ width: min(1480px, calc(100% - 40px)); margin: 0 auto; padding: 32px 0 56px; }}
    header {{ display: grid; gap: 10px; margin-bottom: 18px; }}
    .eyebrow {{ margin: 0; color: #5b6661; font-size: 13px; text-transform: uppercase; letter-spacing: .08em; }}
    h1 {{ margin: 0; font-size: clamp(28px, 4vw, 46px); line-height: 1.04; letter-spacing: 0; }}
    p {{ margin: 0; max-width: 980px; color: #4d5853; line-height: 1.6; }}
    .stills {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }}
    figure {{ margin: 0; border: 1px solid #b7c0bc; border-radius: 8px; overflow: hidden; background: #303532; }}
    img {{ display: block; width: 100%; height: auto; }}
    figcaption {{ display: grid; gap: 2px; padding: 10px 12px 12px; background: #f5f7f5; }}
    figcaption b {{ font-size: 13px; }}
    figcaption span {{ color: #68736e; font-size: 12px; }}
    .library {{ margin-top: 14px; border: 1px solid #b7c0bc; border-radius: 8px; background: #f5f7f5; padding: 16px; }}
    h2 {{ margin: 0 0 12px; font-size: 16px; letter-spacing: 0; }}
    ul {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 12px; }}
    li {{ display: grid; grid-template-columns: minmax(260px, .85fr) minmax(120px, .38fr) minmax(280px, 1.35fr) minmax(220px, .8fr); gap: 10px; align-items: start; }}
    li b, li small, li em, code {{ font-size: 12px; line-height: 1.4; font-style: normal; }}
    li small, li em {{ color: #5d6863; }}
    code {{ background: #dfe4e1; padding: 2px 5px; border-radius: 5px; color: #26312d; }}
    footer {{ margin-top: 14px; color: #5b6661; font-size: 13px; }}
    @media (max-width: 980px) {{
      main {{ width: min(100% - 24px, 760px); padding-top: 24px; }}
      .stills {{ grid-template-columns: 1fr; }}
      li {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
<main>
  <header>
    <p class="eyebrow">Goal 25-C / real machining traces / no procedural wave</p>
    <h1>真实加工痕迹样片</h1>
    <p>这组样片把加工痕迹从 Goal 25-D 的材质分区中单独拆出来，用显式几何痕迹表达车削、拉丝、内孔、螺栓孔、倒角磨亮和珠喷微坑，避免用 procedural shader 直接冒充制造痕。</p>
  </header>
  <section class="stills">
    {''.join(figures)}
  </section>
  <section class="library">
    <h2>Trace IDs</h2>
    <ul>{library}</ul>
  </section>
  <footer>Manifest: <code>render-manifest.json</code>. Status: <code>material-status.md</code>. These traces are implementation candidates for Goal 25-D material zones.</footer>
</main>
</body>
</html>
"""
    write_text_lf(goal_dir / "index.html", html_text)


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    goal_dir = out_dir.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    step_report_path = (repo_root / args.step_report).resolve()
    hdri_path = (repo_root / args.hdri).resolve()

    goal20 = load_goal20_module(repo_root)
    goal20.clear_scene()
    step_report = read_json(step_report_path)
    profile = configure_render(args.profile)
    materials = {name: make_material(name, spec) for name, spec in MATERIAL_SPECS.items()}
    build_studio(materials, hdri_path)
    scene_records = build_trace_scene(materials)
    camera = create_camera()

    stills = []
    set_contact_camera(camera)
    stills.append(
        render_png(
            repo_root,
            out_dir / "01-real-machining-trace-contact-sheet.png",
            profile["contactWidth"],
            profile["contactHeight"],
            "real machining trace contact sheet",
        )
    )

    for index, record in enumerate(scene_records["records"], start=2):
        set_cell_camera(camera, record["origin"])
        filename = f"{index:02d}-{record['id'].lower()}.png"
        stills.append(
            render_png(
                repo_root,
                out_dir / filename,
                profile["cellWidth"],
                profile["cellHeight"],
                record["label"],
            )
        )

    manifest = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "goal": "Goal 25-C real machining trace library",
        "profile": args.profile,
        "renderer": "Blender Cycles",
        "blender": bpy.app.version_string,
        "sourceBoundary": {
            "stepSource": step_report["source"]["path"],
            "stepSourceSha256": step_report["source"]["sha256"],
            "rule": "Goal 25-C creates independent trace implementation samples for later use in the STEP-derived valve body zones.",
        },
        "researchReferences": REFERENCE_NOTES,
        "traceLibrary": scene_records["records"],
        "renderProfile": {
            "contactWidth": profile["contactWidth"],
            "contactHeight": profile["contactHeight"],
            "cellWidth": profile["cellWidth"],
            "cellHeight": profile["cellHeight"],
            "samples": profile["samples"],
            "engine": "Cycles",
            "fullValveRendered": False,
            "homepageConnected": False,
            "motionTestRendered": False,
            "frameSequenceRendered": False,
            "published": False,
        },
        "antiFakeTextureRule": {
            "shaderNodeTexWaveUsed": False,
            "shaderNodeTexNoiseUsed": False,
            "shaderBumpNodeUsed": False,
            "visibleMarksImplementedAs": [
                "torus rings",
                "curve strokes",
                "flush dark hole caps",
                "small micro-pit discs",
                "beveled coupon geometry",
            ],
            "randomSeed": RANDOM_SEED,
        },
        "lighting": {
            "hdri": str(hdri_path.relative_to(repo_root)).replace("\\", "/") if hdri_path.is_file() else None,
            "strategy": "studio HDRI plus white strips and charcoal flags so trace geometry changes reflected metal rather than diffuse whiteness",
        },
        "stills": stills,
        "constraints": [
            "No full valve render is produced.",
            "No homepage hero replacement is performed.",
            "No GitHub Pages publication is performed.",
            "No animation frames are rendered.",
            "Trace labels are reusable visual lookdev IDs, not certified machining specifications.",
        ],
    }

    write_json(goal_dir / "render-manifest.json", manifest)
    write_status(goal_dir, manifest)
    write_index(goal_dir, manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
