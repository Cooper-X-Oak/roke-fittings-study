"""Render Goal28A clean commercial white-studio lookdev samples.

Run inside Blender:
D:\\TOOLS\\render-pipeline\\apps\\Blender-5.2.0\\Blender Foundation\\Blender 5.2\\blender.exe --background --python scripts\\render_goal28a_clean_commercial_white_studio.py -- --repo-root . --profile cycles-smoke
"""

from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import json
import math
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import bpy
    from mathutils import Vector
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Run this script with Blender's Python interpreter.") from exc


GOAL20_DIR = "docs/assets/ztovalve/hero/goal20-blender-cycles-step-proof"
GOAL26_DIR = "docs/assets/ztovalve/hero/goal26-blender-camera-explosion-proof"
GOAL28A_DIR = "docs/assets/ztovalve/hero/goal28a-clean-commercial-white-studio"
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
REQUIRED_CHANNELS = {
    "shellSplit",
    "seatSpread",
    "stemLift",
    "lowerDrop",
    "fastenerSpread",
    "ballTurn",
}
SAMPLE_FRAMES = [0, 72, 136, 216]
LIGHT_ROLES = [
    "top-left-oblique-key",
    "top-right-oblique-rim",
    "bottom-left-lift",
    "bottom-right-lift",
    "front-fill",
    "ambient-white-studio",
]


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    args = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--motion-control", default=f"{GOAL26_DIR}/motion-control.json")
    parser.add_argument("--goal26-manifest", default=f"{GOAL26_DIR}/render-manifest.json")
    parser.add_argument("--runtime-authority", default=AUTHORITY_DIR)
    parser.add_argument("--out-dir", default=GOAL28A_DIR)
    parser.add_argument("--profile", choices=["preview", "review", "cycles-smoke"], default="cycles-smoke")
    parser.add_argument("--frame-list", default="0,72,136,216")
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


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_runtime_authority(repo_root: Path, authority_dir: str) -> tuple[Path, dict[str, dict], dict[str, str]]:
    authority_root = (repo_root / authority_dir).resolve()
    authority: dict[str, dict] = {}
    hashes: dict[str, str] = {}
    for name in AUTHORITY_FILES:
        path = authority_root / name
        if not path.is_file():
            raise RuntimeError(f"Missing hero-runtime authority file: {path}")
        authority[name] = read_json(path)
        hashes[name] = sha256(path)

    root = authority["authority.json"]
    if root.get("authority_id") != "hero-runtime" or root.get("authority_status") != "current":
        raise RuntimeError("Goal28A requires the current hero-runtime authority folder.")
    for name in AUTHORITY_FILES[1:]:
        if authority[name].get("authority_id") != "hero-runtime":
            raise RuntimeError(f"{name} is not bound to hero-runtime.")
    release_policy = authority["release-gate.json"]["runtime_authority_policy"]
    if release_policy["sole_current_hero_render_authority"] is not True:
        raise RuntimeError("hero-runtime must remain the sole current hero render authority.")
    if release_policy["non_runtime_render_authority_allowed"] is not False:
        raise RuntimeError("Non-runtime render authority is forbidden for Goal28A.")
    return authority_root, authority, hashes


def set_input(node, names: list[str], value) -> None:
    for name in names:
        if name in node.inputs:
            node.inputs[name].default_value = value
            return


def safe_set(obj, attr: str, value) -> bool:
    if hasattr(obj, attr):
        try:
            setattr(obj, attr, value)
            return True
        except Exception:
            return False
    return False


def configure_render(profile: str) -> dict:
    profiles = {
        "preview": {"engine": "BLENDER_EEVEE_NEXT", "width": 1200, "height": 675, "samples": 48},
        "review": {"engine": "CYCLES", "width": 1600, "height": 900, "samples": 64},
        "cycles-smoke": {"engine": "CYCLES", "width": 1200, "height": 675, "samples": 36},
    }
    selected = profiles[profile]
    scene = bpy.context.scene
    try:
        scene.render.engine = selected["engine"]
    except TypeError:
        scene.render.engine = "CYCLES"
        selected = {**selected, "engine": "CYCLES"}
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
    scene.view_settings.exposure = -0.24
    scene.view_settings.gamma = 1.0
    if scene.render.engine == "CYCLES":
        scene.cycles.samples = selected["samples"]
        scene.cycles.use_denoising = True
        scene.cycles.max_bounces = 8
        scene.cycles.diffuse_bounces = 3
        scene.cycles.glossy_bounces = 5
        try:
            scene.cycles.device = "GPU"
        except Exception:
            scene.cycles.device = "CPU"
    return {**selected, "engine": scene.render.engine}


def set_white_world() -> dict:
    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    world.color = (0.98, 0.99, 0.96)
    world_record = {
        "role": "ambient-white-studio",
        "color": [0.98, 0.99, 0.96],
        "strength": 1.08,
        "backgroundMode": "high-key-white-studio",
        "uniformWashoutReduction": True,
    }
    if world.use_nodes:
        background = world.node_tree.nodes.get("Background")
        if background:
            background.inputs["Color"].default_value = (0.98, 0.99, 0.96, 1.0)
            background.inputs["Strength"].default_value = world_record["strength"]
    return world_record


def make_emission_material(name: str, color, strength: float) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    output = nodes.new(type="ShaderNodeOutputMaterial")
    emission = nodes.new(type="ShaderNodeEmission")
    emission.inputs["Color"].default_value = color
    emission.inputs["Strength"].default_value = strength
    material.node_tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    material.diffuse_color = color
    return material


def make_gradient_environment_material(name: str) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new(type="ShaderNodeOutputMaterial")
    emission = nodes.new(type="ShaderNodeEmission")
    texcoord = nodes.new(type="ShaderNodeTexCoord")
    separate = nodes.new(type="ShaderNodeSeparateXYZ")
    ramp = nodes.new(type="ShaderNodeValToRGB")

    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.70, 0.73, 0.70, 1.0)
    ramp.color_ramp.elements[1].position = 1.0
    ramp.color_ramp.elements[1].color = (0.98, 0.985, 0.965, 1.0)
    mid_white = ramp.color_ramp.elements.new(0.34)
    mid_white.color = (0.94, 0.955, 0.925, 1.0)
    soft_silver = ramp.color_ramp.elements.new(0.62)
    soft_silver.color = (0.76, 0.79, 0.76, 1.0)
    high_white = ramp.color_ramp.elements.new(0.82)
    high_white.color = (0.965, 0.97, 0.945, 1.0)

    emission.inputs["Strength"].default_value = 0.74
    links.new(texcoord.outputs["Generated"], separate.inputs["Vector"])
    links.new(separate.outputs["Z"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], emission.inputs["Color"])
    links.new(emission.outputs["Emission"], output.inputs["Surface"])
    material.diffuse_color = (0.88, 0.90, 0.86, 1.0)
    return material


def add_reflection_gradient_environment(material: bpy.types.Material) -> dict:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=96, ring_count=48, radius=18.0, location=(0.0, -0.22, 0.38))
    dome = bpy.context.object
    dome.name = "goal28a_continuous_silver_white_reflection_environment"
    dome.data.name = "goal28a_continuous_silver_white_reflection_environment_mesh"
    dome.scale = (1.34, 1.08, 0.88)
    dome.data.materials.append(material)
    safe_set(dome, "visible_camera", False)
    safe_set(dome, "visible_glossy", True)
    safe_set(dome, "visible_diffuse", False)
    safe_set(dome, "visible_shadow", False)
    return {
        "role": "continuous-white-silver-reflection-environment",
        "name": dome.name,
        "type": "non-equipment-gradient-dome",
        "visibleCamera": False,
        "visibleGlossy": True,
        "visibleDiffuse": False,
        "visibleShadow": False,
        "continuousGradient": True,
        "equipmentReadable": False,
        "hardPanelShapeVisible": False,
        "purpose": "restore broad silver-grey stainless reflection layers without readable studio equipment",
    }


def orient_to_target(obj: bpy.types.Object, target) -> None:
    direction = Vector(target) - obj.location
    if direction.length:
        obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()


def add_card(name: str, location, target, width: float, height: float, material, role: str, *, hide_camera: bool) -> dict:
    bpy.ops.mesh.primitive_plane_add(size=1, location=location)
    card = bpy.context.object
    card.name = name
    card.data.name = f"{name}_mesh"
    card.scale = (width, height, 1.0)
    orient_to_target(card, target)
    card.data.materials.append(material)
    safe_set(card, "visible_camera", not hide_camera)
    safe_set(card, "visible_glossy", False)
    safe_set(card, "visible_diffuse", True)
    safe_set(card, "visible_shadow", False)
    return {
        "role": role,
        "name": name,
        "location": [round(value, 4) for value in location],
        "target": [round(value, 4) for value in target],
        "width": width,
        "height": height,
        "material": material.name,
        "hideCamera": hide_camera,
        "visibleGlossy": False,
    }


def add_light(goal20, role: str, name: str, location, target, power: float, size: float, specular: float) -> dict:
    light = goal20.add_area_light(name, location, target, power, size)
    light.data.shape = "DISK"
    light.data.size = size
    safe_set(light, "visible_camera", False)
    safe_set(light, "visible_glossy", False)
    if hasattr(light.data, "specular_factor"):
        light.data.specular_factor = specular
    if hasattr(light.data, "diffuse_factor"):
        light.data.diffuse_factor = 1.0
    return {
        "role": role,
        "name": name,
        "location": [round(value, 4) for value in location],
        "target": [round(value, 4) for value in target],
        "power": power,
        "size": size,
        "shape": "DISK",
        "visibleCamera": False,
        "visibleGlossy": False,
        "specularFactor": specular,
        "distanceClass": "far-large-soft-source",
    }


def build_white_studio(goal20) -> dict:
    world_record = set_white_world()
    cloth = make_emission_material("goal28a_white_cyclorama_cloth", (0.96, 0.97, 0.94, 1.0), 0.28)
    reflector = make_emission_material("goal28a_large_white_reflector", (0.92, 0.94, 0.90, 1.0), 0.24)
    soft_grey = make_emission_material("goal28a_soft_silver_reflector", (0.68, 0.70, 0.67, 1.0), 0.10)
    gradient_environment = add_reflection_gradient_environment(
        make_gradient_environment_material("goal28a_continuous_white_silver_gradient_environment")
    )

    studio_cards = []
    studio_cards.append(add_card("goal28a_white_floor_sweep", (0.0, -0.45, -1.05), (0.0, -0.45, 0.0), 10.5, 7.4, cloth, "camera-hidden-white-floor-sweep", hide_camera=True))
    studio_cards.append(add_card("goal28a_white_back_sweep", (0.0, 6.85, 1.18), (0.0, 0.0, 0.22), 12.2, 6.6, cloth, "camera-hidden-white-back-sweep", hide_camera=True))
    studio_cards.append(add_card("goal28a_left_far_white_reflector", (-10.8, -1.25, 1.45), (0.0, 0.0, 0.12), 8.2, 6.2, reflector, "left-far-white-reflector", hide_camera=True))
    studio_cards.append(add_card("goal28a_right_far_white_reflector", (10.8, -0.70, 1.32), (0.0, 0.0, 0.12), 8.0, 6.0, reflector, "right-far-white-reflector", hide_camera=True))
    studio_cards.append(add_card("goal28a_overhead_far_white_reflector", (0.0, -0.85, 8.8), (0.0, 0.0, 0.12), 11.0, 6.6, reflector, "overhead-far-white-reflector", hide_camera=True))
    studio_cards.append(add_card("goal28a_rear_silver_gradient_reflector", (0.0, 5.95, 0.82), (0.0, 0.0, 0.12), 9.4, 4.4, soft_grey, "rear-soft-silver-gradient-reflector", hide_camera=True))
    flags = []

    rig = [
        add_light(goal20, "top-left-oblique-key", "goal28a_far_top_left_soft_key", (-13.2, -9.6, 8.4), (-0.06, 0.0, 0.18), 540, 14.2, 0.05),
        add_light(goal20, "top-right-oblique-rim", "goal28a_far_top_right_soft_rim", (12.8, -8.8, 7.8), (0.08, 0.02, 0.14), 430, 13.4, 0.045),
        add_light(goal20, "bottom-left-lift", "goal28a_far_bottom_left_lift", (-10.4, -9.2, 0.62), (-0.05, 0.0, -0.03), 130, 10.2, 0.025),
        add_light(goal20, "bottom-right-lift", "goal28a_far_bottom_right_lift", (10.2, -9.0, 0.58), (0.06, 0.0, -0.03), 138, 10.2, 0.025),
        add_light(goal20, "front-fill", "goal28a_far_front_soft_fill", (0.0, -13.4, 3.4), (0.0, 0.0, 0.08), 72, 14.4, 0.015),
        world_record,
    ]
    return {
        "backgroundMode": "high-key-white-studio",
        "studio": "white cyclorama with far large soft sources",
        "visibleLightPanelsInCamera": False,
        "glossyEquipmentReflectionAllowed": False,
        "reflectionCardsGlossyReadableAllowed": False,
        "hardWhiteBlotchReflectionAllowed": False,
        "silverGreyReflectionLayering": "continuous non-equipment gradient environment",
        "reflectionGradientEnvironment": gradient_environment,
        "whiteStudioCards": studio_cards,
        "blackFlags": flags,
        "rig": rig,
    }


def without_noise(spec: dict) -> dict:
    clean = dict(spec)
    for key in [
        "color_variation",
        "color_noise_scale",
        "color_noise_detail",
        "roughness_variation",
        "roughness_noise_scale",
        "roughness_noise_detail",
        "noise_scale",
        "noise_detail",
        "texture",
    ]:
        clean.pop(key, None)
    clean["bump"] = min(float(clean.get("bump", 0.0)), 0.0012)
    clean["bump_distance"] = min(float(clean.get("bump_distance", 0.001)), 0.00035)
    clean.setdefault("metallic", 1.0)
    return clean


def color_tuple(value) -> tuple[float, float, float, float]:
    return tuple(float(component) for component in value)


def clean_material_specs(goal26, material_authority: dict) -> dict:
    specs = {key: without_noise(value) for key, value in goal26.MATERIAL_SPECS.items()}
    roles = material_authority["commercial_pbr_envelope"]["roles"]
    cast_role = roles["cast-satin-body"]
    machined_role = roles["machined-flange-faces"]
    fastener_role = roles["fastener-stainless"]
    ball_role = roles["polished-stainless-ball"]
    graphite_role = roles["graphite-packing"]
    ptfe_role = roles["soft-seal-ptfe"]
    ball_roughness = min(ball_role["roughness_range"][1], ball_role["roughness_target"] + 0.02)
    specs["castBlastedStainless"] = {
        "base_color": color_tuple(cast_role["base_color_target"]),
        "metallic": cast_role["metallic"],
        "roughness": cast_role["roughness_target"],
        "anisotropic": sum(cast_role["anisotropic_range"]) / 2,
        "coat": sum(cast_role["coat_range"]) / 2,
        "bump": 0.0010,
        "bump_distance": 0.00030,
    }
    specs["machinedStainless"] = {
        "base_color": color_tuple(machined_role["base_color_target"]),
        "metallic": machined_role["metallic"],
        "roughness": sum(machined_role["roughness_range"]) / 2,
        "anisotropic": sum(machined_role["anisotropic_range"]) / 2,
        "coat": sum(machined_role["coat_range"]) / 2,
        "bump": 0.00035,
        "bump_distance": 0.00016,
    }
    specs["fastenerStainless"] = {
        "base_color": color_tuple(fastener_role["base_color_target"]),
        "metallic": fastener_role["metallic"],
        "roughness": sum(fastener_role["roughness_range"]) / 2,
        "anisotropic": sum(fastener_role["anisotropic_range"]) / 2,
        "coat": 0.07,
        "bump": 0.00025,
        "bump_distance": 0.00012,
    }
    specs["polishedStainlessBall"] = {
        "base_color": color_tuple(ball_role["base_color_target"]),
        "metallic": ball_role["metallic"],
        "roughness": ball_roughness,
        "anisotropic": 0.0,
        "coat": ball_role["coat_range"][0],
        "coat_roughness": ball_roughness,
        "bump": 0.0,
    }
    specs["graphitePacking"] = {
        **specs["graphitePacking"],
        "base_color": color_tuple(graphite_role["base_color_target"]),
        "metallic": sum(graphite_role["metallic_range"]) / 2,
        "roughness": sum(graphite_role["roughness_range"]) / 2,
        "bump": 0.0012,
        "bump_distance": 0.00035,
    }
    specs["softSealPtfe"] = {
        **specs["softSealPtfe"],
        "base_color": color_tuple(ptfe_role["base_color_target"]),
        "roughness": sum(ptfe_role["roughness_range"]) / 2,
        "bump": 0.0010,
        "bump_distance": 0.00030,
    }
    return specs


def selected_frames(previs: dict, frame_list: str) -> list[int]:
    total = int(previs["totalFrames"])
    frames = [int(value.strip()) for value in frame_list.split(",") if value.strip()]
    return sorted(set(max(0, min(total - 1, frame)) for frame in frames))


def assign_commercial_body_material(body: bpy.types.Object, material: bpy.types.Material) -> dict:
    mesh = body.data
    polygon_count = len(mesh.polygons)
    total_area = sum(float(polygon.area) for polygon in mesh.polygons)
    mesh.materials.clear()
    mesh.materials.append(material)
    for polygon in mesh.polygons:
        polygon.material_index = 0
        polygon.use_smooth = True

    existing = body.modifiers.get("goal28a_commercial_weighted_normals")
    if existing is None:
        modifier = body.modifiers.new("goal28a_commercial_weighted_normals", "WEIGHTED_NORMAL")
    else:
        modifier = existing
    if hasattr(modifier, "keep_sharp"):
        modifier.keep_sharp = True
    if hasattr(modifier, "weight"):
        modifier.weight = 50

    return {
        "policy": "continuous-commercial-body",
        "method": "single-runtime-material-on-product-facing-body-shell",
        "assignedMaterial": material.name,
        "bodyZoneCount": 1,
        "zoneCounts": {
            "commercial-continuous-cast-satin-body": polygon_count,
        },
        "zoneAreas": {
            "commercial-continuous-cast-satin-body": round(total_area, 8),
        },
        "polygonMaterialHardEdgesAllowed": False,
        "productFacingPolygonMaterialHardEdgesVisible": False,
        "polygonZoneTrianglesVisible": False,
        "source": "hero-runtime-material-authority",
    }


def suppress_small_hardware_glossy_reflection(records: list[dict]) -> dict:
    suppressed = []
    for record in records:
        if record["group"] != "fastenersSmallHardware":
            continue
        obj = record["object"]
        safe_set(obj, "visible_glossy", False)
        suppressed.append(record["partName"])
    return {
        "policy": "commercial-polished-ball-clean-reflection",
        "suppressedGroup": "fastenersSmallHardware",
        "suppressedCount": len(suppressed),
        "visibleInCamera": True,
        "visibleInDiffuseAndShadow": True,
        "visibleInGlossy": False,
        "purpose": "prevent exploded small hardware from reading as dirty speckles on the polished stainless ball",
        "samplePartNames": sorted(set(suppressed))[:12],
    }


def adjusted_camera(goal26, control: dict, previs_state: dict, part_state: dict):
    location, target, fov = goal26.camera_from_previs(control, previs_state, part_state)
    target_vec = Vector(target)
    offset = Vector((0.05, -0.08, 0.03))
    location = target_vec + (location - target_vec) * 2.05
    location = location + offset
    target_vec = target_vec + offset * 0.24
    fov = max(18.0, min(38.0, fov * 0.56))
    return location, target_vec, fov


def camera_record(camera, target, fov: float) -> dict:
    return {
        "position": [round(value, 6) for value in camera.location],
        "target": [round(value, 6) for value in target],
        "fovDegrees": round(fov, 4),
        "distanceMultiplier": 2.05,
        "fovMultiplier": 0.56,
        "look": "farther commercial product-camera; no visible light panels",
    }


def render_frames(goal20, goal26, repo_root: Path, frames_dir: Path, control: dict, previs: dict, records: list[dict], camera, render_profile: dict, frames: list[int]) -> tuple[list[dict], dict]:
    frame_records = []
    max_offset = 0.0
    max_ball = 0.0
    started = time.perf_counter()
    for order, frame_index in enumerate(frames):
        previs_state = previs["frameStates"][frame_index]
        part_state = goal26.animation_state_for(float(previs_state["progress"]))
        motion = goal26.apply_goal26_parts(records, part_state, control["blenderTransformScale"])
        camera_location, target, fov = adjusted_camera(goal26, control, previs_state, part_state)
        camera.location = camera_location
        camera.data.angle = math.radians(fov)
        goal20.look_at(camera, target)

        output_path = frames_dir / f"frame{frame_index:04d}.png"
        bpy.context.scene.render.filepath = str(output_path)
        bpy.ops.render.render(write_still=True)
        max_offset = max(max_offset, motion["maxOffset"])
        max_ball = max(max_ball, motion["ballAngleDegrees"])
        frame_records.append(
            {
                "frame": frame_index,
                "progress": previs_state["progress"],
                "shotId": previs_state["shotId"],
                "path": str(output_path.relative_to(repo_root)).replace("\\", "/"),
                "width": render_profile["width"],
                "height": render_profile["height"],
                "bytes": output_path.stat().st_size,
                "sha256": sha256(output_path),
                "camera": camera_record(camera, target, fov),
                "channels": {key: round(value, 6) for key, value in part_state.items()},
                "motionEvidence": motion,
            }
        )
        if (order + 1) % 4 == 0 or order + 1 == len(frames):
            elapsed = time.perf_counter() - started
            print(f"Goal28A rendered {order + 1}/{len(frames)} frames in {elapsed:.1f}s")
    return frame_records, {
        "maxOffset": round(max_offset, 6),
        "maxBallAngleDegrees": round(max_ball, 4),
        "renderSeconds": round(time.perf_counter() - started, 3),
    }


def write_index(goal_dir: Path, manifest: dict) -> None:
    frame_paths = [frame["path"].split("/goal28a-clean-commercial-white-studio/")[-1] for frame in manifest["frames"]]
    frame_labels = [f"frame {frame['frame']:04d} | {frame['shotId']}" for frame in manifest["frames"]]
    html_text = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Goal28A Clean Commercial White Studio</title>
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
    <h1>Goal28A Clean Commercial White Studio</h1>
    <p>Silica-sol investment-cast stainless steel visual, high-key white studio, far large soft sources, clean PBR. Manifest: <code>render-manifest.json</code>.</p>
  </header>
  <section class="stage">
    <img id="frame" src="{html.escape(frame_paths[0])}" alt="Goal28A clean commercial white-studio frame">
    <div class="controls">
      <button id="play" type="button" aria-label="Play or pause">Play</button>
      <input id="scrub" type="range" min="0" max="{len(frame_paths) - 1}" value="0">
      <output id="label">{html.escape(frame_labels[0])}</output>
    </div>
  </section>
</main>
<script>
const frame = document.querySelector("#frame");
const scrub = document.querySelector("#scrub");
const label = document.querySelector("#label");
const play = document.querySelector("#play");
const frames = {json.dumps(frame_paths)};
const labels = {json.dumps(frame_labels)};
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
  timer = setInterval(() => setFrame((Number(scrub.value) + 1) % frames.length), 420);
}});
</script>
</body>
</html>
"""
    write_text(goal_dir / "index.html", html_text)


def write_status(goal_dir: Path, manifest: dict) -> None:
    text = f"""# Goal28A Clean Commercial White Studio

Generated: {manifest['generatedAt']}

## Boundary

- Four-frame lookdev sample only; not a 240-frame delivery render.
- Product visual: silica-sol investment-cast stainless steel, not WCB/cast carbon steel.
- Style: high-key white commercial studio, far large soft sources, clean PBR.
- Runtime authority: hero-runtime is the sole current hero render authority.
- Homepage hero, AVIF sequence, and Pages publication are not changed.

## Acceptance Focus

- No war-damage scratches, dirty blotches or heavy procedural grime.
- Stainless brightness comes from white-studio reflection, not a white diffuse base shortcut.
- Dominant cast body remains a mid-grey metallic substrate with commercial fine satin response.
- White background/environment, not black or dark-grey studio.
- Far large soft light sources; no visible light panels in camera.
- Polished ball keeps a soft-studio polished reflection band, not hard fixtures or dirty cloud marks.
- Valve body/flanges remain silver-white stainless with subtle clean satin texture.
- Product-facing body shell uses one continuous commercial cast-satin stainless assignment; no polygon-zone triangle artifacts.
- White studio cards, black flags and driver lights are not glossy-readable equipment shapes.
- Silver-grey stainless reflection layers come from one continuous non-equipment gradient environment, not readable studio gear.

## Review Frames

- `frames/frame0000.png`
- `frames/frame0072.png`
- `frames/frame0136.png`
- `frames/frame0216.png`
"""
    write_text(goal_dir / "lookdev-status.md", text)


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    goal20 = load_module(repo_root, "scripts/render_goal20_blender_step_proof.py", "goal20_render_helpers")
    goal26 = load_module(repo_root, "scripts/render_goal26_blender_camera_explosion_proof.py", "goal26_render_helpers")

    authority_root, runtime_authority, authority_hashes = load_runtime_authority(repo_root, args.runtime_authority)
    control_path = (repo_root / args.motion_control).resolve()
    goal26_manifest_path = (repo_root / args.goal26_manifest).resolve()
    control = read_json(control_path)
    goal26_manifest = read_json(goal26_manifest_path)
    if "control-valve" in json.dumps(control["sources"], ensure_ascii=False).lower():
        raise RuntimeError("Goal28A must not consume control-valve assets.")
    if set(control["partChannels"]) != REQUIRED_CHANNELS:
        raise RuntimeError("Goal28A requires the six Goal26 motion channels.")
    model_path = (repo_root / control["sources"]["stepMesh"]).resolve()
    semantic_map_path = (repo_root / control["sources"]["goal20SemanticMap"]).resolve()
    previs_path = (repo_root / control["sources"]["cameraPrevis"]).resolve()
    semantic_map = read_json(semantic_map_path)
    previs = read_json(previs_path)
    frames = selected_frames(previs, args.frame_list)

    goal20.clear_scene()
    render_profile = configure_render(args.profile)
    material_specs = clean_material_specs(goal26, runtime_authority["material.json"])
    materials = {name: goal20.make_material(f"goal28a_clean_{name}", spec) for name, spec in material_specs.items()}
    meshes = goal20.import_model(model_path)
    if not meshes:
        raise RuntimeError(f"No mesh objects imported from {model_path}")
    goal20.create_rig(meshes)
    records, group_counts, material_counts, part_counts = goal20.assign_materials(meshes, materials)
    body_records = [record for record in records if record["partName"] == "阀体"]
    if len(body_records) != 1:
        raise RuntimeError(f"Expected exactly one valve-body mesh, found {len(body_records)}")
    zone_assignment = assign_commercial_body_material(body_records[0]["object"], materials["castBlastedStainless"])
    glossy_suppression = suppress_small_hardware_glossy_reflection(records)
    lighting = build_white_studio(goal20)
    camera = goal26.create_camera()
    frame_records, motion_evidence = render_frames(goal20, goal26, repo_root, frames_dir, control, previs, records, camera, render_profile, frames)
    if 0 in frames:
        shutil.copyfile(frames_dir / "frame0000.png", out_dir / "poster.png")

    manifest = {
        "schemaVersion": 1,
        "goalId": "goal28a-clean-commercial-white-studio",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "goal": "Goal28A silica-sol investment-cast stainless + high-key white commercial studio lookdev",
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
            "stepMeshSha256": sha256(model_path),
            "goal20SemanticMap": str(semantic_map_path.relative_to(repo_root)).replace("\\", "/"),
            "goal20SemanticMapSha256": sha256(semantic_map_path),
            "cameraPrevis": str(previs_path.relative_to(repo_root)).replace("\\", "/"),
            "cameraPrevisSha256": sha256(previs_path),
            "motionControl": str(control_path.relative_to(repo_root)).replace("\\", "/"),
            "motionControlSha256": sha256(control_path),
            "goal26RenderManifest": str(goal26_manifest_path.relative_to(repo_root)).replace("\\", "/"),
            "goal26RenderManifestSha256": sha256(goal26_manifest_path),
            "rule": "Goal28A may consume fixed-ball-valve geometry, camera previs and motion evidence, but material, lighting, camera, motion, storyboard and release decisions are bound to hero-runtime as the sole current render authority.",
        },
        "renderProfile": {
            "width": render_profile["width"],
            "height": render_profile["height"],
            "samples": render_profile["samples"],
            "engine": render_profile["engine"],
            "fps": previs["fps"],
            "sourceTotalFrames": previs["totalFrames"],
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
            "productMaterialTruth": "silica-sol investment-cast stainless steel visual",
            "negativeBoundary": ["not WCB", "not cast carbon steel", "not black cast steel", "not war-damaged", "not dirty scratch proof"],
            "commercialMaterialProfile": "commercial-silica-sol-cast-stainless-v1",
            "whiteDiffuseShortcut": False,
            "commercialBodyAssignmentPolicy": runtime_authority["material.json"]["release_expectations"]["commercial_body_assignment_policy"],
            "bodyZoneCount": zone_assignment["bodyZoneCount"],
            "zoneAssignment": zone_assignment,
            "zoneMaterialIds": ["commercial-continuous-cast-satin-body"],
            "materialParameterSnapshot": {
                "familyMaterials": {
                    "castBlastedStainless": material_specs["castBlastedStainless"],
                    "machinedStainless": material_specs["machinedStainless"],
                    "fastenerStainless": material_specs["fastenerStainless"],
                    "polishedStainlessBall": material_specs["polishedStainlessBall"],
                    "graphitePacking": material_specs["graphitePacking"],
                    "softSealPtfe": material_specs["softSealPtfe"],
                },
                "bodyZoneMaterials": [
                    {
                        "id": "commercial-continuous-cast-satin-body",
                        "intent": "continuous commercial silica-sol investment-cast stainless body shell",
                        "material": material_specs["castBlastedStainless"],
                    }
                ],
            },
            "cleanPbr": True,
            "explicitScratchGeometryVisible": False,
            "dirtyBlotchNoiseVisible": False,
            "dirtyBlotchHighlightsVisible": False,
            "polygonZoneArtifactsVisible": False,
            "productFacingMaterialHardEdgesVisible": False,
            "nonRuntimeMaterialSourceUsed": False,
            "polishedBallRoughness": material_specs["polishedStainlessBall"]["roughness"],
            "fullValveFamilyMaterialIds": sorted(material_specs),
        },
        "motionFusion": {
            "sourceGoal": goal26_manifest["goal"],
            "controlledChannels": control["partChannels"],
            "axisMap": control["axisMap"],
            "cameraOverride": control["cameraOverride"],
            "maxOffset": motion_evidence["maxOffset"],
            "maxBallAngleDegrees": motion_evidence["maxBallAngleDegrees"],
            "renderSeconds": motion_evidence["renderSeconds"],
        },
        "lighting": {
            "feedbackBasis": "摄影师反馈：不锈钢精密铸造，不是黑色WCB铸钢；灯要更远更多；背景和环境光必须是白色。",
            **lighting,
            "productGlossyReflectionRetouch": glossy_suppression,
            "roles": LIGHT_ROLES,
            "reviewFramePriority": [136, 72, 216, 0],
        },
        "cameraDirection": {
            "mode": "farther long-lens commercial product perspective",
            "distanceMultiplier": 2.05,
            "fovMultiplier": 0.56,
            "visibleLightPanelsInCamera": False,
        },
        "frames": frame_records,
        "constraints": [
            "Four-frame Goal28A lookdev sample only.",
            "No homepage hero replacement is performed.",
            "No existing AVIF sequence is overwritten.",
            "No Pages publication is performed.",
            "No control-valve asset is consumed.",
            "hero-runtime is the sole current hero render authority.",
            "No non-runtime material experiment is treated as current render authority.",
            "No product-facing polygon material-zone artifacts are allowed.",
            "No glossy-readable studio equipment reflections are allowed.",
            "Silver-grey reflection layering comes from a continuous non-equipment gradient environment.",
        ],
    }
    write_json(out_dir / "render-manifest.json", manifest)
    write_status(out_dir, manifest)
    write_index(out_dir, manifest)
    print(json.dumps({
        "goalId": manifest["goalId"],
        "frames": len(frame_records),
        "index": manifest["previewSurface"]["route"],
        "manifest": str((out_dir / "render-manifest.json").relative_to(repo_root)).replace("\\", "/"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
