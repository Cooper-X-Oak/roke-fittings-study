"""Render Goal28 lighting-lab reflection environment variants.

Run inside Blender:
D:\\TOOLS\\render-pipeline\\apps\\Blender-5.2.0\\Blender Foundation\\Blender 5.2\\blender.exe --background --python scripts\\render_goal28_lighting_lab_variants.py -- --repo-root . --profile cycles-smoke
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
GOAL25D_DIR = "docs/experiment/hero/goal25d-zoned-body-material-proof"
GOAL26_DIR = "docs/assets/ztovalve/hero/goal26-blender-camera-explosion-proof"
GOAL28_DIR = "docs/assets/ztovalve/hero/goal28-clean-pbr-motion-preview"
LAB_DIR = "docs/assets/ztovalve/hero/goal28-lighting-lab"
REQUIRED_CHANNELS = {
    "shellSplit",
    "seatSpread",
    "stemLift",
    "lowerDrop",
    "fastenerSpread",
    "ballTurn",
}
LIGHT_ROLES = [
    "top-left-oblique-key",
    "top-right-oblique-rim",
    "bottom-left-lift",
    "bottom-right-lift",
    "front-fill",
]
VARIANTS = {
    "lighting-v01": {
        "label": "v01 direct five-light on white cloth",
        "strategy": "direct-five-light-white-cloth-baseline",
        "intent": "五灯位置保持不变，但改成白色布景/自然光棚基线，确认产品不再被黑背景吃成黑阀门。",
        "cameraDistanceMultiplier": 1.0,
        "fovMultiplier": 1.0,
        "cameraOffset": (0.0, 0.0, 0.0),
    },
    "lighting-v02": {
        "label": "v02 diffused reflection cove",
        "strategy": "diffused-white-black-reflection-environment",
        "intent": "同五灯角色改为驱动大面积扩散板、白卡、黑旗和低强度正面补光，减少可读灯具反射。",
        "cameraDistanceMultiplier": 1.0,
        "fovMultiplier": 1.0,
        "cameraOffset": (0.0, 0.0, 0.0),
    },
    "lighting-v03": {
        "label": "v03 reflection family trim",
        "strategy": "v02-plus-camera-family-of-angles-trim",
        "intent": "在 v02 环境上拉远并略收视角，把主要可见反射角族从灯具/板边移动到大渐变反射区。",
        "cameraDistanceMultiplier": 1.12,
        "fovMultiplier": 0.92,
        "cameraOffset": (0.035, -0.035, 0.018),
    },
}


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    args = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--motion-control", default=f"{GOAL26_DIR}/motion-control.json")
    parser.add_argument("--goal25d-manifest", default=f"{GOAL25D_DIR}/render-manifest.json")
    parser.add_argument("--goal26-manifest", default=f"{GOAL26_DIR}/render-manifest.json")
    parser.add_argument("--out-dir", default=LAB_DIR)
    parser.add_argument("--profile", choices=["preview", "review", "cycles-smoke"], default="cycles-smoke")
    parser.add_argument("--frame-list", default="0,72,136,216")
    parser.add_argument("--variants", default="lighting-v01,lighting-v02,lighting-v03")
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


def make_reflection_material(
    name: str,
    base_color: tuple[float, float, float, float],
    roughness: float = 0.82,
    emission_strength: float = 0.0,
) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    if emission_strength > 0.0:
        nodes.clear()
        output = nodes.new(type="ShaderNodeOutputMaterial")
        emission = nodes.new(type="ShaderNodeEmission")
        emission.inputs["Color"].default_value = base_color
        emission.inputs["Strength"].default_value = emission_strength
        material.node_tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    else:
        principled = nodes.get("Principled BSDF")
        if not principled:
            principled = nodes.new(type="ShaderNodeBsdfPrincipled")
        set_input(principled, ["Base Color"], base_color)
        set_input(principled, ["Metallic"], 0.0)
        set_input(principled, ["Roughness"], roughness)
        set_input(principled, ["Alpha"], base_color[3])
        set_input(principled, ["Emission Color", "Emission"], base_color)
        set_input(principled, ["Emission Strength", "Emission Weight"], emission_strength)
    material.diffuse_color = base_color
    return material


def configure_world(goal28, profile: str) -> dict:
    render_profile = goal28.configure_render(profile)
    bpy.context.scene.view_settings.exposure = 0.06
    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.color = (1.0, 1.0, 0.96)
    if world.use_nodes:
        background = world.node_tree.nodes.get("Background")
        if background:
            background.inputs["Color"].default_value = (1.0, 1.0, 0.96, 1.0)
            background.inputs["Strength"].default_value = 1.45
    return render_profile


def apply_white_world() -> None:
    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.color = (1.0, 1.0, 0.96)
    if world.use_nodes:
        background = world.node_tree.nodes.get("Background")
        if background:
            background.inputs["Color"].default_value = (1.0, 1.0, 0.96, 1.0)
            background.inputs["Strength"].default_value = 1.45


def orient_to_target(obj: bpy.types.Object, target) -> None:
    direction = Vector(target) - obj.location
    if direction.length == 0:
        return
    obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()


def add_reflection_card(
    name: str,
    location,
    target,
    width: float,
    height: float,
    material: bpy.types.Material,
    *,
    role: str,
    hide_camera: bool = True,
    visible_glossy: bool = True,
) -> tuple[bpy.types.Object, dict]:
    bpy.ops.mesh.primitive_plane_add(size=1, location=location)
    card = bpy.context.object
    card.name = name
    card.data.name = f"{name}_mesh"
    card.scale = (width, height, 1.0)
    orient_to_target(card, target)
    card.data.materials.append(material)
    safe_set(card, "visible_camera", not hide_camera)
    safe_set(card, "visible_glossy", visible_glossy)
    safe_set(card, "visible_diffuse", True)
    safe_set(card, "visible_shadow", False)
    return card, {
        "role": role,
        "name": name,
        "location": [round(value, 4) for value in location],
        "target": [round(value, 4) for value in target],
        "width": width,
        "height": height,
        "material": material.name,
        "hideCamera": hide_camera,
        "visibleGlossy": visible_glossy,
    }


def add_white_cloth_stage() -> list[dict]:
    cloth = make_reflection_material("goal28_lab_white_cloth_stage", (0.96, 0.97, 0.93, 1.0), 0.86, 0.55)
    side_cloth = make_reflection_material("goal28_lab_side_white_cloth", (0.90, 0.92, 0.88, 1.0), 0.88, 0.30)
    records = []

    bpy.ops.mesh.primitive_plane_add(size=1, location=(0.0, -0.35, -0.92), rotation=(0.0, 0.0, 0.0))
    floor = bpy.context.object
    floor.name = "goal28_lab_white_cloth_floor"
    floor.scale = (5.9, 4.4, 1.0)
    floor.data.materials.append(cloth)
    safe_set(floor, "visible_glossy", True)
    safe_set(floor, "visible_shadow", True)
    records.append(
        {
            "role": "visible-white-cloth-floor",
            "name": floor.name,
            "location": [0.0, -0.35, -0.92],
            "width": 5.9,
            "height": 4.4,
            "material": cloth.name,
            "hideCamera": False,
            "visibleGlossy": True,
        }
    )

    for name, location, target, width, height, material, role in [
        (
            "goal28_lab_white_cloth_backdrop",
            (0.0, 2.35, 0.72),
            (0.0, 0.0, 0.20),
            7.6,
            4.4,
            cloth,
            "visible-white-cloth-backdrop",
        ),
        (
            "goal28_lab_left_white_reflection_wall",
            (-4.25, -0.18, 0.65),
            (0.0, 0.0, 0.16),
            4.6,
            3.8,
            side_cloth,
            "visible-left-white-cloth-reflector",
        ),
        (
            "goal28_lab_right_white_reflection_wall",
            (4.25, -0.12, 0.62),
            (0.0, 0.0, 0.14),
            4.4,
            3.7,
            side_cloth,
            "visible-right-white-cloth-reflector",
        ),
        (
            "goal28_lab_overhead_white_cloth",
            (0.0, -0.20, 3.10),
            (0.0, 0.0, 0.12),
            7.2,
            3.2,
            cloth,
            "visible-overhead-white-cloth-reflector",
        ),
    ]:
        _, record = add_reflection_card(
            name,
            location,
            target,
            width,
            height,
            material,
            role=role,
            hide_camera=False,
            visible_glossy=True,
        )
        records.append(record)
    return records


def add_driver_light(goal20, role: str, name: str, location, target, power: float, size: float, *, direct_specular: float) -> dict:
    light = goal20.add_area_light(name, location, target, power, size)
    light.data.shape = "DISK"
    light.data.size = size
    safe_set(light, "visible_camera", False)
    safe_set(light, "visible_glossy", direct_specular > 0.15)
    if hasattr(light.data, "specular_factor"):
        light.data.specular_factor = direct_specular
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
        "visibleGlossy": direct_specular > 0.15,
        "specularFactor": direct_specular,
    }


def build_reflection_environment(goal20, variant_id: str) -> dict:
    apply_white_world()
    white_cloth_stage = add_white_cloth_stage()
    if variant_id == "lighting-v01":
        rig = goal20_goal26_build_studio(goal20)
        apply_white_world()
        return {
            "rig": rig,
            "reflectionCards": [],
            "blackFlags": [],
            "whiteClothStage": white_cloth_stage,
            "backgroundMode": "white-cloth-natural-light",
            "driverLightMode": "direct-five-light-white-cloth-baseline",
            "driverLightsHiddenFromGlossy": False,
            "removedMirrorReadablePanels": True,
        }

    white = make_reflection_material("goal28_lab_warm_white_diffusion", (0.94, 0.96, 0.91, 1.0), 0.88, 0.58)
    soft = make_reflection_material("goal28_lab_soft_grey_diffusion", (0.74, 0.77, 0.73, 1.0), 0.90, 0.22)
    floor = make_reflection_material("goal28_lab_low_silver_bounce", (0.66, 0.69, 0.65, 1.0), 0.86, 0.16)
    black = make_reflection_material("goal28_lab_soft_black_flag", (0.025, 0.027, 0.026, 1.0), 0.94, 0.0)
    rear = make_reflection_material("goal28_lab_rear_light_grey", (0.56, 0.59, 0.56, 1.0), 0.92, 0.10)

    cards = []
    flags = []
    _, record = add_reflection_card(
        "goal28_lab_top_left_white_cove",
        (-2.95, -1.28, 2.08),
        (-0.02, 0.0, 0.10),
        5.6,
        3.0,
        white,
        role="top-left-oblique-key-diffusion-card",
    )
    cards.append(record)
    _, record = add_reflection_card(
        "goal28_lab_top_right_white_cove",
        (2.82, 0.52, 1.86),
        (0.04, 0.02, 0.08),
        4.6,
        2.7,
        soft,
        role="top-right-oblique-rim-diffusion-card",
    )
    cards.append(record)
    _, record = add_reflection_card(
        "goal28_lab_bottom_left_bounce",
        (-1.85, -1.10, -0.66),
        (-0.02, 0.0, 0.0),
        3.2,
        1.35,
        floor,
        role="bottom-left-lift-bounce-card",
    )
    cards.append(record)
    _, record = add_reflection_card(
        "goal28_lab_bottom_right_bounce",
        (1.78, -0.80, -0.62),
        (0.04, 0.0, 0.0),
        3.0,
        1.32,
        floor,
        role="bottom-right-lift-bounce-card",
    )
    cards.append(record)
    _, record = add_reflection_card(
        "goal28_lab_front_broad_fill_scrim",
        (0.0, -3.45, 0.44),
        (0.0, 0.0, 0.05),
        6.4,
        3.2,
        white if variant_id == "lighting-v03" else soft,
        role="front-fill-wide-scrim",
    )
    cards.append(record)
    _, record = add_reflection_card(
        "goal28_lab_rear_mid_grey_cove",
        (0.0, 1.88, 0.42),
        (0.0, 0.0, 0.08),
        6.2,
        3.4,
        rear,
        role="rear-mid-grey-cove",
    )
    cards.append(record)

    for name, location, target, width, height, role in [
        ("goal28_lab_left_soft_edge_flag", (-3.55, -0.02, 0.42), (0.0, 0.0, 0.08), 0.82, 2.6, "left-soft-dark-edge-flag"),
        ("goal28_lab_right_soft_edge_flag", (3.55, -0.02, 0.36), (0.0, 0.0, 0.06), 0.76, 2.4, "right-soft-dark-edge-flag"),
        ("goal28_lab_upper_soft_cut", (0.0, -0.24, 3.12), (0.0, 0.0, 0.12), 4.2, 0.58, "upper-soft-dark-cut-flag"),
    ]:
        _, record = add_reflection_card(name, location, target, width, height, black, role=role)
        flags.append(record)

    if variant_id == "lighting-v03":
        _, record = add_reflection_card(
            "goal28_lab_v03_extra_left_gradient_mass",
            (-3.85, -0.92, 1.00),
            (0.0, 0.0, 0.08),
            2.0,
            4.0,
            white,
            role="v03-broadened-left-white-mass",
        )
        cards.append(record)
        _, record = add_reflection_card(
            "goal28_lab_v03_center_dark_seam_flag",
            (0.0, -2.62, 1.45),
            (0.0, 0.0, 0.14),
            0.28,
            1.8,
            black,
            role="v03-front-dark-line-flag",
        )
        flags.append(record)

    light_specs = [
        ("top-left-oblique-key", "goal28_lab_top_left_driver", (-3.35, -2.16, 2.72), (-2.95, -1.28, 2.08), 500, 7.8),
        ("top-right-oblique-rim", "goal28_lab_top_right_driver", (3.18, 1.08, 2.34), (2.82, 0.52, 1.86), 360, 7.1),
        ("bottom-left-lift", "goal28_lab_bottom_left_driver", (-2.18, -1.82, -0.42), (-1.85, -1.10, -0.66), 105, 5.1),
        ("bottom-right-lift", "goal28_lab_bottom_right_driver", (2.14, -1.52, -0.40), (1.78, -0.80, -0.62), 112, 5.1),
        ("front-fill", "goal28_lab_front_fill_driver", (0.0, -4.18, 0.62), (0.0, -3.45, 0.44), 58, 8.8),
    ]
    direct_specular = 0.22 if variant_id == "lighting-v02" else 0.32
    rig = [add_driver_light(goal20, *spec, direct_specular=direct_specular) for spec in light_specs]
    return {
        "rig": rig,
        "reflectionCards": cards,
        "blackFlags": flags,
        "whiteClothStage": white_cloth_stage,
        "backgroundMode": "white-cloth-natural-light",
        "driverLightMode": "large-soft-specular-drivers-plus-reflection-cards",
        "driverLightsHiddenFromGlossy": False,
        "removedMirrorReadablePanels": True,
    }


def goal20_goal26_build_studio(goal20):
    goal26 = sys.modules.get("goal26_render_helpers")
    if goal26 is None:
        raise RuntimeError("Goal26 helper module is not loaded.")
    hdri_path = None
    return goal26.build_studio(goal20, {}, hdri_path)


def selected_frames(previs: dict, frame_list: str) -> list[int]:
    total = int(previs["totalFrames"])
    frames = [int(value.strip()) for value in frame_list.split(",") if value.strip()]
    return sorted(set(max(0, min(total - 1, frame)) for frame in frames))


def adjusted_camera(goal26, control: dict, previs_state: dict, part_state: dict, variant: dict):
    location, target, fov = goal26.camera_from_previs(control, previs_state, part_state)
    target_vec = Vector(target)
    offset = Vector(variant["cameraOffset"])
    distance_multiplier = float(variant["cameraDistanceMultiplier"])
    if distance_multiplier != 1.0:
        location = target_vec + (location - target_vec) * distance_multiplier
    location = location + offset
    target_vec = target_vec + offset * 0.32
    fov = max(18.0, min(62.0, fov * float(variant["fovMultiplier"])))
    return location, target_vec, fov


def camera_record(camera, target, fov: float, variant: dict) -> dict:
    return {
        "position": [round(value, 6) for value in camera.location],
        "target": [round(value, 6) for value in target],
        "fovDegrees": round(fov, 4),
        "distanceMultiplier": variant["cameraDistanceMultiplier"],
        "fovMultiplier": variant["fovMultiplier"],
        "offset": [round(value, 6) for value in variant["cameraOffset"]],
    }


def render_frames(
    goal20,
    goal26,
    repo_root: Path,
    frames_dir: Path,
    control: dict,
    previs: dict,
    records: list[dict],
    camera,
    render_profile: dict,
    frames: list[int],
    variant: dict,
) -> tuple[list[dict], dict]:
    frame_records = []
    max_offset = 0.0
    max_ball = 0.0
    started = time.perf_counter()
    for order, frame_index in enumerate(frames):
        previs_state = previs["frameStates"][frame_index]
        part_state = goal26.animation_state_for(float(previs_state["progress"]))
        motion = goal26.apply_goal26_parts(records, part_state, control["blenderTransformScale"])
        camera_location, target, fov = adjusted_camera(goal26, control, previs_state, part_state, variant)
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
                "camera": camera_record(camera, target, fov, variant),
                "channels": {key: round(value, 6) for key, value in part_state.items()},
                "motionEvidence": motion,
            }
        )
        if (order + 1) % 4 == 0 or order + 1 == len(frames):
            elapsed = time.perf_counter() - started
            print(f"{variant['label']} rendered {order + 1}/{len(frames)} frames in {elapsed:.1f}s")
    evidence = {
        "maxOffset": round(max_offset, 6),
        "maxBallAngleDegrees": round(max_ball, 4),
        "renderSeconds": round(time.perf_counter() - started, 3),
    }
    return frame_records, evidence


def write_variant_index(goal_dir: Path, manifest: dict) -> None:
    frame_paths = [frame["path"].split(f"/{manifest['variantId']}/")[-1] for frame in manifest["frames"]]
    frame_labels = [f"frame {frame['frame']:04d} | {frame['shotId']}" for frame in manifest["frames"]]
    frame_count = len(frame_paths)
    html_text = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(manifest['variantLabel'])}</title>
  <style>
    :root {{ color-scheme: dark; font-family: Inter, "Noto Sans SC", system-ui, sans-serif; background: #101413; color: #eef3ef; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; }}
    main {{ width: min(1240px, calc(100% - 32px)); margin: 0 auto; padding: 22px 0 36px; }}
    header {{ display: grid; gap: 8px; margin-bottom: 14px; }}
    h1 {{ margin: 0; font-size: clamp(24px, 4vw, 38px); line-height: 1.08; letter-spacing: 0; }}
    p {{ margin: 0; color: #aab5b0; line-height: 1.55; }}
    .stage {{ display: grid; gap: 10px; border: 1px solid #33403a; border-radius: 8px; background: #171d1a; padding: 10px; }}
    img {{ display: block; width: 100%; height: auto; border-radius: 6px; background: #070908; }}
    .controls {{ display: grid; grid-template-columns: auto 1fr auto; gap: 10px; align-items: center; }}
    button {{ width: 40px; height: 40px; border: 1px solid #52605a; border-radius: 8px; background: #202823; color: #eef3ef; cursor: pointer; }}
    input[type=range] {{ width: 100%; accent-color: #c7d1ca; }}
    output, code {{ color: #c9d4ce; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 12px; }}
    .metrics {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-top: 12px; }}
    .metric {{ border: 1px solid #33403a; border-radius: 8px; padding: 12px; background: #171d1a; }}
    .metric b {{ display: block; font-size: 18px; }}
    .metric span {{ display: block; color: #aab5b0; font-size: 12px; line-height: 1.4; }}
    @media (max-width: 760px) {{ .metrics {{ grid-template-columns: 1fr 1fr; }} }}
  </style>
</head>
<body>
<main>
  <header>
    <h1>{html.escape(manifest['variantLabel'])}</h1>
    <p>{html.escape(manifest['intent'])}</p>
    <p><code>render-manifest.json</code> / review priority: frame 0136</p>
  </header>
  <section class="stage">
    <img id="frame" src="{html.escape(frame_paths[0])}" alt="Goal28 lighting lab frame">
    <div class="controls">
      <button id="play" type="button" aria-label="Play or pause">Play</button>
      <input id="scrub" type="range" min="0" max="{frame_count - 1}" value="0">
      <output id="label">{html.escape(frame_labels[0])}</output>
    </div>
  </section>
  <section class="metrics">
    <div class="metric"><b>{frame_count}</b><span>sample frames</span></div>
    <div class="metric"><b>{len(manifest['lighting']['reflectionCards'])}</b><span>reflection cards</span></div>
    <div class="metric"><b>{len(manifest['lighting']['blackFlags'])}</b><span>black flags</span></div>
    <div class="metric"><b>{manifest['motionFusion']['maxBallAngleDegrees']}</b><span>max ball turn degrees</span></div>
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


def write_variant_status(goal_dir: Path, manifest: dict) -> None:
    text = f"""# {manifest['variantLabel']}

Generated: {manifest['generatedAt']}

## Boundary

- Goal: Goal28 Lighting Lab reflection environment sample.
- This is a four-frame lighting sample, not the 240-frame Goal28 delivery preview.
- Homepage hero, AVIF sequence, and Pages publication are not changed.

## Intent

{manifest['intent']}

## Lighting

- Roles: `{', '.join(item['role'] for item in manifest['lighting']['rig'])}`
- Reflection cards: `{len(manifest['lighting']['reflectionCards'])}`
- Black flags: `{len(manifest['lighting']['blackFlags'])}`
- Driver lights hidden from glossy rays: `{manifest['lighting']['driverLightsHiddenFromGlossy']}`

## Review Frames

- `frames/frame0000.png`
- `frames/frame0072.png`
- `frames/frame0136.png`
- `frames/frame0216.png`
"""
    write_text(goal_dir / "lighting-status.md", text)


def render_variant(
    repo_root: Path,
    lab_dir: Path,
    args: argparse.Namespace,
    modules: dict,
    source_paths: dict,
    source_data: dict,
    variant_id: str,
) -> dict:
    variant = VARIANTS[variant_id]
    goal20 = modules["goal20"]
    goal25d = modules["goal25d"]
    goal26 = modules["goal26"]
    goal28 = modules["goal28"]
    control = source_data["control"]
    previs = source_data["previs"]
    semantic_map = source_data["semantic_map"]
    goal25d_manifest = source_data["goal25d_manifest"]
    goal26_manifest = source_data["goal26_manifest"]
    frames = source_data["frames"]
    model_path = source_paths["model_path"]

    goal20.clear_scene()
    render_profile = configure_world(goal28, args.profile)
    material_specs = goal28.goal28_material_specs(goal26, goal25d_manifest)
    materials = {
        name: goal20.make_material(f"goal28_lab_{variant_id}_{name}", spec)
        for name, spec in material_specs.items()
    }
    meshes = goal20.import_model(model_path)
    if not meshes:
        raise RuntimeError(f"No mesh objects imported from {model_path}")
    goal20.create_rig(meshes)
    records, group_counts, material_counts, part_counts = goal20.assign_materials(meshes, materials)
    body_records = [record for record in records if record["partName"] == "阀体"]
    if len(body_records) != 1:
        raise RuntimeError(f"Expected exactly one valve-body mesh, found {len(body_records)}")
    zone_materials = [goal25d.make_zone_material(spec, prefix=f"goal28_lab_{variant_id}_") for spec in goal25d.ZONE_SPECS]
    zone_assignment = goal25d.assign_zone_materials(body_records[0]["object"], zone_materials)

    lighting = build_reflection_environment(goal20, variant_id)
    camera = goal26.create_camera()
    variant_dir = lab_dir / variant_id
    frames_dir = variant_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    frame_records, motion_evidence = render_frames(
        goal20,
        goal26,
        repo_root,
        frames_dir,
        control,
        previs,
        records,
        camera,
        render_profile,
        frames,
        variant,
    )
    if 0 in frames:
        shutil.copyfile(frames_dir / "frame0000.png", variant_dir / "poster.png")

    manifest = {
        "schemaVersion": 1,
        "goalId": "goal28-lighting-lab",
        "variantId": variant_id,
        "variantLabel": variant["label"],
        "strategy": variant["strategy"],
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "intent": variant["intent"],
        "product": "ztovalve fixed ball valve",
        "renderer": {
            "engine": render_profile["engine"],
            "profile": args.profile,
            "blender": bpy.app.version_string,
        },
        "sourceBoundary": {
            "stepMesh": str(source_paths["model_path"].relative_to(repo_root)).replace("\\", "/"),
            "stepMeshSha256": sha256(source_paths["model_path"]),
            "goal20SemanticMap": str(source_paths["semantic_map_path"].relative_to(repo_root)).replace("\\", "/"),
            "goal20SemanticMapSha256": sha256(source_paths["semantic_map_path"]),
            "cameraPrevis": str(source_paths["previs_path"].relative_to(repo_root)).replace("\\", "/"),
            "cameraPrevisSha256": sha256(source_paths["previs_path"]),
            "motionControl": str(source_paths["control_path"].relative_to(repo_root)).replace("\\", "/"),
            "motionControlSha256": sha256(source_paths["control_path"]),
            "goal25dMaterialManifest": str(source_paths["goal25d_manifest_path"].relative_to(repo_root)).replace("\\", "/"),
            "goal25dMaterialManifestSha256": sha256(source_paths["goal25d_manifest_path"]),
            "goal26RenderManifest": str(source_paths["goal26_manifest_path"].relative_to(repo_root)).replace("\\", "/"),
            "goal26RenderManifestSha256": sha256(source_paths["goal26_manifest_path"]),
            "rule": "Lighting lab consumes Goal20/25D/26/28 fixed-ball-valve sources only; it does not publish or replace homepage assets.",
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
            "route": str((variant_dir / "index.html").relative_to(repo_root)).replace("\\", "/"),
            "frameDirectory": str(frames_dir.relative_to(repo_root)).replace("\\", "/"),
            "poster": str((variant_dir / "poster.png").relative_to(repo_root)).replace("\\", "/") if (variant_dir / "poster.png").is_file() else None,
        },
        "partIdentity": {
            "meshCount": len(meshes),
            "goal20SemanticMeshCount": sum(semantic_map["partCounts"].values()),
            "groupCounts": group_counts,
            "materialCounts": material_counts,
            "partCounts": part_counts,
        },
        "materialFusion": {
            "sourceGoal": goal25d_manifest["goal"],
            "bodyZoneCount": len(goal25d_manifest["materialLibrary"]),
            "zoneAssignment": zone_assignment,
            "zoneMaterialIds": [spec["id"] for spec in goal25d.ZONE_SPECS],
            "fullValveFamilyMaterialIds": sorted(material_specs),
            "polishedBallRoughnessRange": material_specs["polishedStainlessBall"]["roughness_variation"],
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
            "feedbackBasis": "上方左右斜照、底部双灯、正面补光；镜面球体需要环境反射梯度，而不是可识别灯具形状。",
            "acceptanceFocus": [
                "frame0136 polished ball must not show hard readable light fixtures.",
                "ball should retain broad white, dark and mid-gray reflection zones.",
                "body/cylinder/flange should show dark edge, bright edge and mid-gray transition.",
                "front fill remains weak; top/side/bottom roles shape the metal.",
            ],
            **lighting,
            "reviewFramePriority": [136, 72, 216, 0],
        },
        "frames": frame_records,
        "constraints": [
            "Four-frame lighting sample only.",
            "No homepage hero replacement is performed.",
            "No existing AVIF sequence is overwritten.",
            "No Pages publication is performed.",
            "No control-valve asset is consumed.",
        ],
    }
    write_json(variant_dir / "render-manifest.json", manifest)
    write_variant_status(variant_dir, manifest)
    write_variant_index(variant_dir, manifest)
    return manifest


def write_lab_index(lab_dir: Path, lab_manifest: dict) -> None:
    cards = []
    for variant in lab_manifest["variants"]:
        rel = variant["route"].split("/goal28-lighting-lab/")[-1]
        image = variant["priorityFrame"].split("/goal28-lighting-lab/")[-1]
        cards.append(
            f"""<article>
      <a href="{html.escape(rel)}"><img src="{html.escape(image)}" alt="{html.escape(variant['label'])} frame 0136"></a>
      <h2>{html.escape(variant['label'])}</h2>
      <p>{html.escape(variant['intent'])}</p>
      <code>{html.escape(variant['strategy'])}</code>
    </article>"""
        )
    html_text = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Goal28 Lighting Lab</title>
  <style>
    :root {{ color-scheme: dark; font-family: Inter, "Noto Sans SC", system-ui, sans-serif; background: #101413; color: #eef3ef; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; }}
    main {{ width: min(1440px, calc(100% - 32px)); margin: 0 auto; padding: 24px 0 42px; }}
    header {{ display: grid; gap: 8px; margin-bottom: 18px; }}
    h1 {{ margin: 0; font-size: clamp(28px, 5vw, 48px); line-height: 1.04; letter-spacing: 0; }}
    p {{ margin: 0; color: #aab5b0; line-height: 1.55; }}
    .grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }}
    article {{ border: 1px solid #33403a; border-radius: 8px; background: #171d1a; padding: 10px; display: grid; gap: 10px; }}
    img {{ display: block; width: 100%; height: auto; border-radius: 6px; background: #070908; }}
    h2 {{ margin: 0; font-size: 18px; line-height: 1.25; letter-spacing: 0; }}
    code {{ color: #c9d4ce; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 12px; }}
    @media (max-width: 920px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
<main>
  <header>
    <h1>Goal28 Lighting Lab</h1>
    <p>Three four-frame reflection-environment samples for the fixed-ball-valve hero. Main judgment frame: 0136.</p>
    <p><code>lighting-lab-manifest.json</code></p>
  </header>
  <section class="grid">
    {"".join(cards)}
  </section>
</main>
</body>
</html>
"""
    write_text(lab_dir / "index.html", html_text)


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    lab_dir = (repo_root / args.out_dir).resolve()
    lab_dir.mkdir(parents=True, exist_ok=True)
    requested_variants = [value.strip() for value in args.variants.split(",") if value.strip()]
    unknown = [variant for variant in requested_variants if variant not in VARIANTS]
    if unknown:
        raise RuntimeError(f"Unknown lighting variants: {', '.join(unknown)}")

    modules = {
        "goal20": load_module(repo_root, "scripts/render_goal20_blender_step_proof.py", "goal20_render_helpers"),
        "goal25d": load_module(repo_root, "scripts/render_goal25d_zoned_body_materials.py", "goal25d_render_helpers"),
        "goal26": load_module(repo_root, "scripts/render_goal26_blender_camera_explosion_proof.py", "goal26_render_helpers"),
        "goal28": load_module(repo_root, "scripts/render_goal28_clean_pbr_motion_preview.py", "goal28_render_helpers"),
    }

    control_path = (repo_root / args.motion_control).resolve()
    goal25d_manifest_path = (repo_root / args.goal25d_manifest).resolve()
    goal26_manifest_path = (repo_root / args.goal26_manifest).resolve()
    control = read_json(control_path)
    if "control-valve" in json.dumps(control["sources"], ensure_ascii=False).lower():
        raise RuntimeError("Goal28 Lighting Lab must not consume control-valve assets.")
    if set(control["partChannels"]) != REQUIRED_CHANNELS:
        raise RuntimeError("Goal28 Lighting Lab requires the six Goal26 motion channels.")
    model_path = (repo_root / control["sources"]["stepMesh"]).resolve()
    semantic_map_path = (repo_root / control["sources"]["goal20SemanticMap"]).resolve()
    previs_path = (repo_root / control["sources"]["cameraPrevis"]).resolve()
    source_data = {
        "control": control,
        "goal25d_manifest": read_json(goal25d_manifest_path),
        "goal26_manifest": read_json(goal26_manifest_path),
        "semantic_map": read_json(semantic_map_path),
        "previs": read_json(previs_path),
    }
    source_data["frames"] = selected_frames(source_data["previs"], args.frame_list)
    source_paths = {
        "control_path": control_path,
        "goal25d_manifest_path": goal25d_manifest_path,
        "goal26_manifest_path": goal26_manifest_path,
        "model_path": model_path,
        "semantic_map_path": semantic_map_path,
        "previs_path": previs_path,
    }

    variant_manifests = [
        render_variant(repo_root, lab_dir, args, modules, source_paths, source_data, variant_id)
        for variant_id in requested_variants
    ]
    lab_manifest = {
        "schemaVersion": 1,
        "goalId": "goal28-lighting-lab",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "product": "ztovalve fixed ball valve",
        "purpose": "Compare three reflection-environment lighting samples before any Goal28 240-frame render.",
        "sampleFrames": source_data["frames"],
        "reviewFramePriority": [136, 72, 216, 0],
        "variants": [
            {
                "variantId": manifest["variantId"],
                "label": manifest["variantLabel"],
                "strategy": manifest["strategy"],
                "intent": manifest["intent"],
                "route": manifest["previewSurface"]["route"],
                "manifest": str((lab_dir / manifest["variantId"] / "render-manifest.json").relative_to(repo_root)).replace("\\", "/"),
                "priorityFrame": next(frame["path"] for frame in manifest["frames"] if frame["frame"] == 136),
                "driverLightsHiddenFromGlossy": manifest["lighting"]["driverLightsHiddenFromGlossy"],
                "reflectionCardCount": len(manifest["lighting"]["reflectionCards"]),
                "blackFlagCount": len(manifest["lighting"]["blackFlags"]),
            }
            for manifest in variant_manifests
        ],
        "sourceBoundary": {
            "motionControl": str(control_path.relative_to(repo_root)).replace("\\", "/"),
            "cameraPrevis": str(previs_path.relative_to(repo_root)).replace("\\", "/"),
            "goal25dMaterialManifest": str(goal25d_manifest_path.relative_to(repo_root)).replace("\\", "/"),
            "goal26RenderManifest": str(goal26_manifest_path.relative_to(repo_root)).replace("\\", "/"),
        },
        "constraints": [
            "Lighting lab only; no homepage connection.",
            "Lighting lab only; no 240-frame completion claim.",
            "Lighting lab only; no Pages publication.",
        ],
    }
    write_json(lab_dir / "lighting-lab-manifest.json", lab_manifest)
    write_lab_index(lab_dir, lab_manifest)
    print(json.dumps({
        "goalId": lab_manifest["goalId"],
        "variants": [variant["variantId"] for variant in lab_manifest["variants"]],
        "index": str((lab_dir / "index.html").relative_to(repo_root)).replace("\\", "/"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
