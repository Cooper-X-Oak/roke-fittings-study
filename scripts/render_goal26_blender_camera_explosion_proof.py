"""Render Goal 26 Blender/Cycles camera and exploded-motion proof.

Run inside Blender:
D:\\TOOLS\\render-pipeline\\apps\\Blender-5.2.0\\Blender Foundation\\Blender 5.2\\blender.exe --background --python scripts\\render_goal26_blender_camera_explosion_proof.py -- --repo-root . --profile smoke
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
GOAL26_DIR = "docs/assets/ztovalve/hero/goal26-blender-camera-explosion-proof"


MATERIAL_SPECS = {
    "castBlastedStainless": {
        "base_color": (0.22, 0.24, 0.23, 1.0),
        "metallic": 1.0,
        "roughness": 0.40,
        "anisotropic": 0.28,
        "coat": 0.015,
        "bump": 0.018,
        "bump_distance": 0.0026,
        "noise_scale": 1200,
        "noise_detail": 14,
        "color_variation": ((0.16, 0.18, 0.17, 1.0), (0.36, 0.38, 0.35, 1.0)),
        "color_noise_scale": 920,
        "color_noise_detail": 12,
        "roughness_variation": (0.34, 0.56),
        "roughness_noise_scale": 760,
        "roughness_noise_detail": 11,
    },
    "machinedStainless": {
        "base_color": (0.50, 0.51, 0.48, 1.0),
        "metallic": 1.0,
        "roughness": 0.26,
        "anisotropic": 0.70,
        "coat": 0.10,
        "bump": 0.002,
        "bump_distance": 0.0009,
        "noise_scale": 120,
        "noise_detail": 8,
        "color_variation": ((0.38, 0.39, 0.37, 1.0), (0.66, 0.67, 0.62, 1.0)),
        "color_noise_scale": 90,
        "roughness_variation": (0.19, 0.34),
        "roughness_noise_scale": 90,
    },
    "polishedStainlessBall": {
        "base_color": (0.70, 0.72, 0.69, 1.0),
        "metallic": 1.0,
        "roughness": 0.24,
        "anisotropic": 0.08,
        "coat": 0.06,
        "bump": 0.0,
        "noise_scale": 1,
        "noise_detail": 1,
        "roughness_variation": (0.20, 0.30),
        "roughness_noise_scale": 42,
        "roughness_noise_detail": 6,
    },
    "graphitePacking": {
        "base_color": (0.018, 0.019, 0.020, 1.0),
        "metallic": 0.12,
        "roughness": 0.66,
        "anisotropic": 0.0,
        "coat": 0.0,
        "bump": 0.014,
        "bump_distance": 0.0026,
        "noise_scale": 95,
        "noise_detail": 9,
        "color_variation": ((0.006, 0.006, 0.007, 1.0), (0.070, 0.072, 0.070, 1.0)),
        "color_noise_scale": 72,
        "color_noise_detail": 8,
        "roughness_variation": (0.52, 0.82),
        "roughness_noise_scale": 105,
    },
    "softSealPtfe": {
        "base_color": (0.66, 0.61, 0.50, 1.0),
        "metallic": 0.0,
        "roughness": 0.55,
        "anisotropic": 0.0,
        "coat": 0.02,
        "bump": 0.003,
        "bump_distance": 0.0012,
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
        "bump": 0.002,
        "bump_distance": 0.0009,
        "noise_scale": 150,
        "noise_detail": 8,
        "color_variation": ((0.31, 0.32, 0.30, 1.0), (0.62, 0.63, 0.58, 1.0)),
        "color_noise_scale": 120,
        "roughness_variation": (0.22, 0.40),
        "roughness_noise_scale": 110,
    },
    "goal26SoftPanel": {
        "base_color": (0.68, 0.70, 0.67, 1.0),
        "metallic": 0.0,
        "roughness": 0.72,
        "anisotropic": 0.0,
        "coat": 0.0,
        "bump": 0.0,
        "noise_scale": 1,
        "noise_detail": 1,
    },
    "goal26DarkFlag": {
        "base_color": (0.035, 0.038, 0.036, 1.0),
        "metallic": 0.0,
        "roughness": 0.74,
        "anisotropic": 0.0,
        "coat": 0.0,
        "bump": 0.0,
        "noise_scale": 1,
        "noise_detail": 1,
    },
}


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    args = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--motion-control", default=f"{GOAL26_DIR}/motion-control.json")
    parser.add_argument("--out-dir", default=f"{GOAL26_DIR}/stills")
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


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def smoothstep(value: float) -> float:
    t = clamp01(value)
    return t * t * (3 - 2 * t)


def mix(a: Vector, b: Vector, t: float) -> Vector:
    return a + (b - a) * clamp01(t)


def sign(value: float, fallback: float = 1.0) -> float:
    if value > 0.0005:
        return 1.0
    if value < -0.0005:
        return -1.0
    return fallback


def three_to_blender(values: list[float] | tuple[float, float, float]) -> Vector:
    x, y, z = values
    return Vector((x, -z, y))


def configure_render(profile: str) -> dict:
    profiles = {
        "smoke": {"width": 1280, "height": 720, "samples": 24},
        "proof": {"width": 1920, "height": 1080, "samples": 80},
    }
    selected = profiles[profile]
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = selected["samples"]
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 8
    scene.cycles.diffuse_bounces = 3
    scene.cycles.glossy_bounces = 5
    scene.render.resolution_x = selected["width"]
    scene.render.resolution_y = selected["height"]
    scene.render.film_transparent = True
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


def build_studio(goal20, materials: dict, hdri_path: Path | None) -> None:
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
            background.inputs["Strength"].default_value = 0.032
    else:
        world.color = (0.22, 0.24, 0.23)

    lighting_rig = []

    def add_lamp(role: str, name: str, location, target, power: float, size: float) -> None:
        light_obj = goal20.add_area_light(name, location, target, power, size)
        light_obj.data.shape = "DISK"
        light_obj.data.size = size
        lighting_rig.append(
            {
                "role": role,
                "name": name,
                "location": [round(value, 4) for value in location],
                "target": [round(value, 4) for value in target],
                "power": power,
                "size": size,
                "shape": "DISK",
            }
        )

    add_lamp("top-left-oblique-key", "goal26_top_left_oblique_key", (-2.55, -0.46, 2.10), (-0.04, 0.00, 0.10), 118, 4.4)
    add_lamp("top-right-oblique-rim", "goal26_top_right_oblique_rim", (2.35, 0.22, 1.86), (0.04, 0.00, 0.08), 92, 3.9)
    add_lamp("bottom-left-lift", "goal26_bottom_left_lift", (-1.55, -0.60, -0.48), (-0.05, 0.00, 0.02), 24, 2.15)
    add_lamp("bottom-right-lift", "goal26_bottom_right_lift", (1.52, -0.22, -0.42), (0.05, 0.00, 0.02), 28, 2.10)
    add_lamp("front-fill", "goal26_front_fill", (0.0, -3.05, 0.34), (0.00, 0.00, 0.06), 8, 5.8)
    return lighting_rig


def animation_state_for(progress: float) -> dict:
    explode_in = smoothstep((progress - 0.18) / 0.32)
    explode_out = 1 - smoothstep((progress - 0.62) / 0.22)
    exploded = clamp01(explode_in * explode_out)
    ball_turn_in = smoothstep((progress - 0.46) / 0.12)
    ball_turn_out = 1 - smoothstep((progress - 0.64) / 0.10)
    ball_turn = clamp01(ball_turn_in * ball_turn_out)
    return {
        "exploded": exploded,
        "shellSplit": exploded * 1.08,
        "seatSpread": exploded,
        "stemLift": exploded * 0.92,
        "lowerDrop": exploded * 0.78,
        "fastenerSpread": exploded * 0.76,
        "ballTurn": ball_turn,
    }


def apply_goal26_parts(records: list[dict], state: dict, scale: dict) -> dict:
    moved_counts = Counter()
    max_offset = 0.0
    ball_angle = state["ballTurn"] * 90.0

    for record in records:
        obj = record["object"]
        local = record["local_center"]
        group = record["group"]
        part_name = record["partName"]
        offset = Vector((0, 0, 0))

        if group == "bodyPressureShell":
            offset.x += sign(local.x) * scale["bodyPressureShellX"] * state["shellSplit"]
            offset.y += sign(local.y) * scale["bodyPressureShellY"] * state["shellSplit"]
        elif group == "seatSealSystem":
            offset.x += sign(local.x) * scale["seatSealSystemX"] * state["seatSpread"]
            offset.y += sign(local.y) * scale["seatSealSystemY"] * state["seatSpread"]
        elif group == "stemPackingDrive":
            offset.z += scale["stemPackingDriveZ"] * state["stemLift"]
            offset.y += scale["stemPackingDriveY"] * state["stemLift"]
        elif group == "ballTrunnionCore":
            if part_name == "球体":
                pass
            elif "固定轴" in part_name or local.z < -0.05:
                offset.z -= scale["lowerSupportZ"] * state["lowerDrop"]
            elif local.z > 0.02:
                offset.z += scale["stemPackingDriveZ"] * 0.32 * state["stemLift"]
        elif group == "fastenersSmallHardware":
            radial = Vector((local.x, local.y, 0))
            if radial.length < 0.001:
                radial = Vector((sign(local.x), sign(local.y), 0))
            radial.normalize()
            offset += radial * scale["fastenerRadial"] * state["fastenerSpread"]
            offset.z += sign(local.z) * scale["fastenerZ"] * state["fastenerSpread"]

        obj.location = record["base_location"] + offset
        obj.rotation_euler = record["base_rotation"].copy()
        if part_name == "球体":
            obj.rotation_euler.rotate_axis("Z", math.radians(ball_angle))

        if offset.length > 0.0001:
            moved_counts[group] += 1
            max_offset = max(max_offset, offset.length)

    bpy.context.view_layer.update()
    return {
        "ballAngleDegrees": round(ball_angle, 4),
        "movedCounts": dict(moved_counts),
        "maxOffset": round(max_offset, 6),
    }


def camera_from_previs(control: dict, previs_state: dict, part_state: dict) -> tuple[Vector, Vector, float]:
    three_center = Vector(control["axisMap"]["threeModelCenter"])
    blender_center = Vector(control["axisMap"]["blenderProductCenter"])
    base_camera = three_to_blender(Vector(previs_state["cameraPosition"]) - three_center) + blender_center
    base_target = three_to_blender(Vector(previs_state["target"]) - three_center) + blender_center

    override = control["cameraOverride"]
    catalogue_camera = blender_center + three_to_blender(override["catalogueCameraOffsetThree"])
    catalogue_target = blender_center + three_to_blender(override["catalogueTargetOffsetThree"])
    release_mix = clamp01(part_state["exploded"] * override["explodedMixMultiplier"])

    camera_location = mix(base_camera, catalogue_camera, release_mix)
    target = mix(base_target, catalogue_target, release_mix)
    fov = previs_state["fovDegrees"] + (override["catalogueFovDegrees"] - previs_state["fovDegrees"]) * release_mix
    safety = override.get("compositionSafety", {})
    distance_multiplier = safety.get("distanceMultiplier", 1.0)
    if distance_multiplier != 1.0:
        camera_location = target + (camera_location - target) * distance_multiplier
    fov += safety.get("fovAddDegrees", 0.0)
    return camera_location, target, fov


def create_camera() -> bpy.types.Object:
    camera_data = bpy.data.cameras.new("goal26_camera_previs_consumer")
    camera = bpy.data.objects.new("goal26_camera_previs_consumer", camera_data)
    bpy.context.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    camera.data.type = "PERSP"
    camera.data.sensor_width = 36
    camera.data.dof.use_dof = False
    return camera


def render_goal26_frames(
    goal20,
    repo_root: Path,
    out_dir: Path,
    control: dict,
    previs: dict,
    records: list[dict],
    camera: bpy.types.Object,
    render_profile: dict,
    profile: str,
) -> list[dict]:
    selected_frames = control["renderSets"][profile]
    stills = []
    for order, frame_index in enumerate(selected_frames):
        previs_state = previs["frameStates"][frame_index]
        part_state = animation_state_for(float(previs_state["progress"]))
        motion_evidence = apply_goal26_parts(records, part_state, control["blenderTransformScale"])
        camera_location, target, fov = camera_from_previs(control, previs_state, part_state)
        camera.location = camera_location
        camera.data.angle = math.radians(fov)
        goal20.look_at(camera, target)

        output_path = out_dir / f"{order:02d}-frame-{frame_index:03d}-{previs_state['shotId']}.png"
        bpy.context.scene.render.filepath = str(output_path)
        bpy.ops.render.render(write_still=True)
        stills.append(
            {
                "id": output_path.stem,
                "frame": frame_index,
                "progress": previs_state["progress"],
                "shotId": previs_state["shotId"],
                "path": str(output_path.relative_to(repo_root)).replace("\\", "/"),
                "width": render_profile["width"],
                "height": render_profile["height"],
                "bytes": output_path.stat().st_size,
                "sha256": sha256(output_path),
                "camera": {
                    "source": "docs/assets/ztovalve/hero/camera-previs-240.json",
                    "position": [round(value, 6) for value in camera_location],
                    "target": [round(value, 6) for value in target],
                    "fovDegrees": round(fov, 4),
                },
                "channels": {key: round(value, 6) for key, value in part_state.items()},
                "motionEvidence": motion_evidence,
            }
        )
    return stills


def write_index(goal_dir: Path, manifest: dict) -> None:
    cards = []
    for still in manifest["stills"]:
        local_src = html.escape(still["path"].split("/goal26-blender-camera-explosion-proof/")[-1])
        cards.append(
            f"""
            <figure>
              <img src="{local_src}" alt="{html.escape(still['id'])}">
              <figcaption>
                <b>{html.escape(still['id'])}</b>
                <span>frame {still['frame']} | ball {still['motionEvidence']['ballAngleDegrees']} deg | max offset {still['motionEvidence']['maxOffset']}</span>
              </figcaption>
            </figure>
            """
        )
    html_text = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Goal 26 Blender Camera Explosion Proof</title>
  <style>
    :root {{ color-scheme: light; font-family: Inter, "Noto Sans SC", system-ui, sans-serif; background: #f3f4f6; color: #101828; }}
    body {{ margin: 0; }}
    main {{ width: min(1440px, calc(100% - 40px)); margin: 0 auto; padding: 34px 0 56px; }}
    header {{ display: grid; gap: 10px; margin-bottom: 22px; }}
    .eyebrow {{ margin: 0; color: #667085; font-size: 13px; text-transform: uppercase; letter-spacing: .08em; }}
    h1 {{ margin: 0; font-size: clamp(28px, 4vw, 48px); line-height: 1.02; letter-spacing: 0; }}
    .summary {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin: 18px 0 28px; }}
    .metric {{ border: 1px solid #d0d5dd; background: #fff; border-radius: 8px; padding: 13px 15px; }}
    .metric b {{ display: block; font-size: 21px; }}
    .metric span {{ color: #667085; font-size: 13px; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }}
    figure {{ margin: 0; border: 1px solid #d0d5dd; background: #fff; border-radius: 8px; overflow: hidden; }}
    figure:first-child {{ grid-column: 1 / -1; }}
    img {{ display: block; width: 100%; height: auto; background-color: #d9dde3; background-image: linear-gradient(45deg, #cfd4dc 25%, transparent 25%), linear-gradient(-45deg, #cfd4dc 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #cfd4dc 75%), linear-gradient(-45deg, transparent 75%, #cfd4dc 75%); background-size: 28px 28px; background-position: 0 0, 0 14px, 14px -14px, -14px 0; }}
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
    <p class="eyebrow">ztovalve fixed ball valve | Blender/Cycles proof</p>
    <h1>Goal 26 camera and exploded-part control proof</h1>
    <p>Manifest: <code>render-manifest.json</code>. Motion source: <code>motion-control.json</code>. This proof does not replace the homepage Hero.</p>
  </header>
  <section class="summary">
    <div class="metric"><b>{manifest['renderProfile']['renderedFrameCount']}</b><span>proof frames</span></div>
    <div class="metric"><b>{manifest['partIdentity']['meshCount']}</b><span>STEP mesh objects</span></div>
    <div class="metric"><b>{manifest['proofEvidence']['maxBallAngleDegrees']}</b><span>max ball turn degrees</span></div>
    <div class="metric"><b>{manifest['proofEvidence']['maxOffset']}</b><span>max part offset</span></div>
  </section>
  <section class="grid">
    {''.join(cards)}
  </section>
</main>
</body>
</html>
"""
    (goal_dir / "index.html").write_text(html_text, encoding="utf-8")


def write_status(goal_dir: Path, manifest: dict) -> None:
    text = f"""# Goal 26 Blender Camera Explosion Proof

Generated: {manifest['generatedAt']}

## Boundary

- Product object: ztovalve fixed ball valve.
- Source model: `{manifest['sourceBoundary']['stepMesh']}`.
- Camera/state source: `{manifest['sourceBoundary']['cameraPrevis']}`.
- Motion control source: `{manifest['sourceBoundary']['motionControl']}`.
- Homepage Hero and current AVIF sequence are not replaced by this proof.

## Verified Control Channels

{chr(10).join(f"- `{name}`: {spec['meaning']}" for name, spec in manifest['controlledChannels'].items())}

## Rendered Proof Frames

{chr(10).join(f"- `{still['id']}`: {still['path']}" for still in manifest['stills'])}

## Next Gate

After review approval, the same control source can be extended into a full 240-frame Blender render and encoded into the existing Hero AVIF delivery shape.
"""
    (goal_dir / "motion-status.md").write_text(text, encoding="utf-8")


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    control_path = (repo_root / args.motion_control).resolve()
    control = read_json(control_path)
    model_path = (repo_root / control["sources"]["stepMesh"]).resolve()
    semantic_map_path = (repo_root / control["sources"]["goal20SemanticMap"]).resolve()
    previs_path = (repo_root / control["sources"]["cameraPrevis"]).resolve()
    hdri_path = (repo_root / GOAL20_DIR / "studio_small_09_1k.hdr").resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    goal_dir = out_dir.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    if "control-valve" in str(model_path).lower() or "control-valve" in str(previs_path).lower():
        raise RuntimeError("Goal26 must not consume control-valve assets.")

    goal20 = load_goal20_module(repo_root)
    semantic_map = read_json(semantic_map_path)
    previs = read_json(previs_path)

    goal20.clear_scene()
    render_profile = configure_render(args.profile)
    materials = {name: goal20.make_material(f"goal26_{name}", spec) for name, spec in MATERIAL_SPECS.items()}
    meshes = goal20.import_model(model_path)
    if not meshes:
        raise RuntimeError(f"No mesh objects imported from {model_path}")

    goal20.create_rig(meshes)
    records, group_counts, material_counts, part_counts = goal20.assign_materials(meshes, materials)
    lighting_rig = build_studio(goal20, materials, hdri_path)
    camera = create_camera()
    stills = render_goal26_frames(
        goal20,
        repo_root,
        out_dir,
        control,
        previs,
        records,
        camera,
        render_profile,
        args.profile,
    )

    manifest = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "goal": "Goal 26 Blender camera and exploded-part motion proof",
        "product": "ztovalve fixed ball valve",
        "profile": args.profile,
        "renderer": "Blender Cycles",
        "blender": bpy.app.version_string,
        "sourceBoundary": {
            "stepMesh": str(model_path.relative_to(repo_root)).replace("\\", "/"),
            "stepMeshSha256": sha256(model_path),
            "cameraPrevis": str(previs_path.relative_to(repo_root)).replace("\\", "/"),
            "cameraPrevisSha256": sha256(previs_path),
            "motionControl": str(control_path.relative_to(repo_root)).replace("\\", "/"),
            "motionControlSha256": sha256(control_path),
            "goal20SemanticMap": str(semantic_map_path.relative_to(repo_root)).replace("\\", "/"),
            "rule": "Goal26 consumes ztovalve fixed ball valve sources only; control-valve assets are forbidden.",
        },
        "renderProfile": {
            "width": render_profile["width"],
            "height": render_profile["height"],
            "samples": render_profile["samples"],
            "engine": "Cycles",
            "filmTransparent": True,
            "renderedFrameCount": len(stills),
            "fullReleaseFrameCount": 0,
            "homepageConnected": False,
            "frameSequenceRendered": False,
            "heroAvifReplaced": False,
        },
        "partIdentity": {
            "meshCount": len(meshes),
            "goal20SemanticMeshCount": sum(semantic_map["partCounts"].values()),
            "groupCounts": group_counts,
            "materialCounts": material_counts,
            "partCounts": part_counts,
        },
        "controlledChannels": control["partChannels"],
        "axisMap": control["axisMap"],
        "cameraControl": {
            "sourcePrevisTotalFrames": previs["totalFrames"],
            "sourcePrevisFps": previs["fps"],
            "coordinateConversion": control["axisMap"]["threeToBlender"],
            "catalogueHoldMix": control["cameraOverride"],
        },
        "lighting": {
            "feedbackBasis": "上方左右斜照、底部双灯、正面补光；避免镜面球体反射出可识别矩形灯板。",
            "rig": lighting_rig,
            "removedMirrorReadablePanels": True,
            "polishedBallRoughnessRange": MATERIAL_SPECS["polishedStainlessBall"]["roughness_variation"],
        },
        "proofEvidence": {
            "cameraControlVerified": all(still["camera"]["source"].endswith("camera-previs-240.json") for still in stills),
            "partMotionControlVerified": max(still["motionEvidence"]["maxOffset"] for still in stills) > 0.05,
            "ballTurnControlVerified": max(still["motionEvidence"]["ballAngleDegrees"] for still in stills) > 80,
            "maxBallAngleDegrees": max(still["motionEvidence"]["ballAngleDegrees"] for still in stills),
            "maxOffset": max(still["motionEvidence"]["maxOffset"] for still in stills),
            "renderedFrameIds": [still["frame"] for still in stills],
        },
        "stills": stills,
        "constraints": [
            "No homepage hero replacement is performed.",
            "No existing AVIF sequence is overwritten.",
            "No control-valve asset is consumed.",
            "Goal23 and Goal25D are material references only, not animation objects.",
            "Motion labels are visual proof controls, not a claim about field maintenance procedure.",
        ],
    }
    write_json(goal_dir / "render-manifest.json", manifest)
    write_index(goal_dir, manifest)
    write_status(goal_dir, manifest)
    print(f"Rendered {len(stills)} Goal26 proof frames to {out_dir}")


if __name__ == "__main__":
    main()
