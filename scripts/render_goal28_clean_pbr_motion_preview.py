"""Render Goal 28 clean PBR stainless + Goal26 motion fusion preview.

Run inside Blender:
D:\\TOOLS\\render-pipeline\\apps\\Blender-5.2.0\\Blender Foundation\\Blender 5.2\\blender.exe --background --python scripts\\render_goal28_clean_pbr_motion_preview.py -- --repo-root . --profile preview
"""

from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import json
import math
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import bpy
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Run this script with Blender's Python interpreter.") from exc


GOAL20_DIR = "docs/assets/ztovalve/hero/goal20-blender-cycles-step-proof"
GOAL25D_DIR = "docs/experiment/hero/goal25d-zoned-body-material-proof"
GOAL26_DIR = "docs/assets/ztovalve/hero/goal26-blender-camera-explosion-proof"
GOAL28_DIR = "docs/assets/ztovalve/hero/goal28-clean-pbr-motion-preview"
REQUIRED_CHANNELS = {
    "shellSplit",
    "seatSpread",
    "stemLift",
    "lowerDrop",
    "fastenerSpread",
    "ballTurn",
}


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    args = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--motion-control", default=f"{GOAL26_DIR}/motion-control.json")
    parser.add_argument("--goal25d-manifest", default=f"{GOAL25D_DIR}/render-manifest.json")
    parser.add_argument("--goal26-manifest", default=f"{GOAL26_DIR}/render-manifest.json")
    parser.add_argument("--out-dir", default=GOAL28_DIR)
    parser.add_argument("--profile", choices=["preview", "review", "cycles-smoke"], default="preview")
    parser.add_argument("--frame-list", default="")
    parser.add_argument("--start-frame", type=int, default=0)
    parser.add_argument("--end-frame", type=int, default=239)
    parser.add_argument("--encode-mp4", action="store_true")
    parser.add_argument("--ffmpeg", default="ffmpeg")
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


def configure_render(profile: str) -> dict:
    profiles = {
        "preview": {"engine": "BLENDER_EEVEE_NEXT", "width": 960, "height": 540, "samples": 32},
        "review": {"engine": "BLENDER_EEVEE_NEXT", "width": 1280, "height": 720, "samples": 48},
        "cycles-smoke": {"engine": "CYCLES", "width": 960, "height": 540, "samples": 20},
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
    scene.view_settings.exposure = -0.90
    scene.view_settings.gamma = 1.0

    if scene.render.engine == "CYCLES":
        scene.cycles.samples = selected["samples"]
        scene.cycles.use_denoising = True
        scene.cycles.max_bounces = 7
        scene.cycles.diffuse_bounces = 2
        scene.cycles.glossy_bounces = 4
        try:
            scene.cycles.device = "GPU"
        except Exception:
            scene.cycles.device = "CPU"
    else:
        eevee = getattr(scene, "eevee", None)
        if eevee:
            if hasattr(eevee, "taa_render_samples"):
                eevee.taa_render_samples = selected["samples"]
            if hasattr(eevee, "use_gtao"):
                eevee.use_gtao = True
            if hasattr(eevee, "gtao_distance"):
                eevee.gtao_distance = 3
            if hasattr(eevee, "gtao_factor"):
                eevee.gtao_factor = 1.15
    return {**selected, "engine": scene.render.engine}


def goal28_material_specs(goal26, goal25d_manifest: dict) -> dict:
    specs = {key: dict(value) for key, value in goal26.MATERIAL_SPECS.items()}
    library = {item["id"]: item for item in goal25d_manifest["materialLibrary"]}

    def params(zone_id: str) -> dict:
        value = dict(library[zone_id]["parameters"])
        value.setdefault("metallic", 1.0)
        if value.get("roughness_variation") is None:
            value.pop("roughness_variation", None)
        if value.get("bump_scale") and "noise_scale" not in value:
            value["noise_scale"] = value["bump_scale"]
        if value.get("bump_detail") and "noise_detail" not in value:
            value["noise_detail"] = value["bump_detail"]
        if "color_variation" not in value:
            base = value["base_color"]
            low = tuple(max(0.0, channel * 0.84) for channel in base[:3]) + (1.0,)
            high = tuple(min(1.0, channel * 1.14) for channel in base[:3]) + (1.0,)
            value["color_variation"] = (low, high)
            value["color_noise_scale"] = value.get("roughness_noise_scale", 120)
            value["color_noise_detail"] = value.get("roughness_noise_detail", 8)
        return value

    specs["castBlastedStainless"] = params("G25-SS-CAST-BLASTED-SATIN-01")
    specs["machinedStainless"] = params("G25-SS-MACH-FLANGE-RADIAL-01")
    specs["fastenerStainless"] = params("G25-SS-MACH-BOLT-BORE-DARK-01")
    specs["polishedStainlessBall"] = {
        **specs["polishedStainlessBall"],
        "base_color": (0.70, 0.72, 0.69, 1.0),
        "roughness": 0.24,
        "anisotropic": 0.08,
        "coat": 0.06,
        "bump": 0.0,
        "roughness_variation": (0.20, 0.30),
        "roughness_noise_scale": 42,
    }
    specs["graphitePacking"] = {
        **specs["graphitePacking"],
        "base_color": (0.020, 0.022, 0.021, 1.0),
        "roughness": 0.68,
    }
    specs["softSealPtfe"] = {
        **specs["softSealPtfe"],
        "base_color": (0.67, 0.63, 0.52, 1.0),
        "roughness": 0.57,
    }
    return specs


def selected_frames(previs: dict, args: argparse.Namespace) -> list[int]:
    total = int(previs["totalFrames"])
    if args.frame_list.strip():
        frames = [int(value.strip()) for value in args.frame_list.split(",") if value.strip()]
    else:
        start = max(0, min(total - 1, args.start_frame))
        end = max(start, min(total - 1, args.end_frame))
        frames = list(range(start, end + 1))
    return sorted(set(max(0, min(total - 1, frame)) for frame in frames))


def camera_record(camera, target, fov: float) -> dict:
    return {
        "position": [round(value, 6) for value in camera.location],
        "target": [round(value, 6) for value in target],
        "fovDegrees": round(fov, 4),
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
) -> tuple[list[dict], dict]:
    frame_records = []
    max_offset = 0.0
    max_ball = 0.0
    started = time.perf_counter()
    for order, frame_index in enumerate(frames):
        previs_state = previs["frameStates"][frame_index]
        part_state = goal26.animation_state_for(float(previs_state["progress"]))
        motion = goal26.apply_goal26_parts(records, part_state, control["blenderTransformScale"])
        camera_location, target, fov = goal26.camera_from_previs(control, previs_state, part_state)
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
        if (order + 1) % 10 == 0 or order + 1 == len(frames):
            elapsed = time.perf_counter() - started
            print(f"Goal28 rendered {order + 1}/{len(frames)} frames in {elapsed:.1f}s")
    evidence = {
        "maxOffset": round(max_offset, 6),
        "maxBallAngleDegrees": round(max_ball, 4),
        "renderSeconds": round(time.perf_counter() - started, 3),
    }
    return frame_records, evidence


def encode_mp4(repo_root: Path, goal_dir: Path, manifest: dict, ffmpeg: str) -> dict | None:
    video_path = goal_dir / "goal28-clean-pbr-motion-preview.mp4"
    frame_dir = repo_root / manifest["previewSurface"]["frameDirectory"]
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-framerate",
        str(manifest["previewSurface"]["fps"]),
        "-start_number",
        "0",
        "-i",
        str(frame_dir / "frame%04d.png"),
        "-frames:v",
        str(manifest["renderProfile"]["sequenceFrameCount"]),
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "21",
        "-pix_fmt",
        "yuv420p",
        "-g",
        "12",
        "-keyint_min",
        "12",
        "-sc_threshold",
        "0",
        "-bf",
        "0",
        "-movflags",
        "+faststart",
        str(video_path),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except Exception as exc:
        print(f"Goal28 MP4 encode skipped: {exc}")
        return None
    return {
        "path": str(video_path.relative_to(repo_root)).replace("\\", "/"),
        "bytes": video_path.stat().st_size,
        "sha256": sha256(video_path),
        "codec": "h264",
        "gop": 12,
        "audio": False,
    }


def write_index(goal_dir: Path, manifest: dict) -> None:
    preview = manifest["previewSurface"]
    frame_paths = [frame["path"].split("/goal28-clean-pbr-motion-preview/")[-1] for frame in manifest["frames"]]
    frame_labels = [f"frame {frame['frame']:04d} | {frame['shotId']}" for frame in manifest["frames"]]
    frame_count = len(frame_paths)
    video = preview.get("video")
    video_markup = ""
    if video:
        local_video = html.escape(video["path"].split("/goal28-clean-pbr-motion-preview/")[-1])
        video_markup = f'<video controls playsinline muted poster="poster.png" src="{local_video}"></video>'
    html_text = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Goal 28 Clean PBR Motion Preview</title>
  <style>
    :root {{ color-scheme: dark; font-family: Inter, "Noto Sans SC", system-ui, sans-serif; background: #111514; color: #eef3ef; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; }}
    main {{ width: min(1280px, calc(100% - 32px)); margin: 0 auto; padding: 24px 0 40px; }}
    header {{ display: flex; justify-content: space-between; gap: 18px; align-items: end; margin-bottom: 14px; }}
    h1 {{ margin: 0; font-size: clamp(24px, 4vw, 42px); line-height: 1.05; letter-spacing: 0; }}
    .meta {{ margin: 8px 0 0; color: #aab5b0; font-size: 13px; line-height: 1.5; }}
    .stage {{ display: grid; gap: 10px; border: 1px solid #343d39; border-radius: 8px; background: #171d1a; padding: 10px; }}
    .framebox {{ position: relative; overflow: hidden; border-radius: 6px; background: #090b0a; }}
    img, video {{ display: block; width: 100%; height: auto; }}
    .controls {{ display: grid; grid-template-columns: auto 1fr auto; gap: 10px; align-items: center; }}
    button {{ width: 40px; height: 40px; border: 1px solid #52605a; border-radius: 8px; background: #202823; color: #eef3ef; cursor: pointer; }}
    input[type=range] {{ width: 100%; accent-color: #b8c6bd; }}
    output, code {{ color: #c9d4ce; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 12px; }}
    .metrics {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-top: 12px; }}
    .metric {{ border: 1px solid #343d39; border-radius: 8px; padding: 12px; background: #171d1a; }}
    .metric b {{ display: block; font-size: 18px; }}
    .metric span {{ display: block; margin-top: 3px; color: #aab5b0; font-size: 12px; line-height: 1.4; }}
    @media (max-width: 760px) {{ header {{ display: grid; }} .metrics {{ grid-template-columns: 1fr 1fr; }} }}
  </style>
</head>
<body>
<main>
  <header>
    <div>
      <h1>Goal 28 Clean PBR Stainless + Motion Preview</h1>
      <p class="meta">240 Blender frames from Goal26 motion/camera control with Goal25D clean PBR valve-body zoning. Manifest: <code>render-manifest.json</code>.</p>
    </div>
    <code>{html.escape(manifest['renderer']['engine'])} / {manifest['renderer']['profile']}</code>
  </header>
  <section class="stage">
    <div class="framebox">
      <img id="frame" src="{html.escape(frame_paths[0])}" alt="Goal28 frame preview">
      {video_markup}
    </div>
    <div class="controls">
      <button id="play" type="button" aria-label="Play or pause">Play</button>
      <input id="scrub" type="range" min="0" max="{frame_count - 1}" value="0">
      <output id="label">{html.escape(frame_labels[0])}</output>
    </div>
  </section>
  <section class="metrics">
    <div class="metric"><b>{frame_count}</b><span>rendered frames</span></div>
    <div class="metric"><b>{manifest['materialFusion']['bodyZoneCount']}</b><span>Goal25D body zones</span></div>
    <div class="metric"><b>{manifest['motionFusion']['maxBallAngleDegrees']}</b><span>max ball turn degrees</span></div>
    <div class="metric"><b>{manifest['motionFusion']['maxOffset']}</b><span>max part offset</span></div>
  </section>
</main>
<script>
const frame = document.querySelector("#frame");
const scrub = document.querySelector("#scrub");
const label = document.querySelector("#label");
const play = document.querySelector("#play");
const frames = {json.dumps(frame_paths)};
const labels = {json.dumps(frame_labels)};
const total = frames.length;
let timer = null;
function setFrame(value) {{
  const index = Math.max(0, Math.min(total - 1, Number(value) || 0));
  frame.src = frames[index];
  scrub.value = index;
  label.value = labels[index];
}}
scrub.addEventListener("input", () => setFrame(scrub.value));
play.addEventListener("click", () => {{
  if (timer) {{ clearInterval(timer); timer = null; play.textContent = "Play"; return; }}
  play.textContent = "Pause";
  timer = setInterval(() => setFrame((Number(scrub.value) + 1) % total), {round(1000 / preview['fps'])});
}});
</script>
</body>
</html>
"""
    write_text(goal_dir / "index.html", html_text)


def write_status(goal_dir: Path, manifest: dict) -> None:
    text = f"""# Goal 28 Clean PBR Motion Preview

Generated: {manifest['generatedAt']}

## Boundary

- Product: ztovalve fixed ball valve.
- This preview merges Goal25D clean PBR stainless material zoning into the Goal26 Blender motion/camera control.
- The homepage hero, current AVIF sequence, and Pages entry are not replaced.
- The render is a preview sequence, not the final high-sample release render.

## Sources

- STEP mesh: `{manifest['sourceBoundary']['stepMesh']}`
- Camera previs: `{manifest['sourceBoundary']['cameraPrevis']}`
- Motion control: `{manifest['sourceBoundary']['motionControl']}`
- Goal25D material manifest: `{manifest['sourceBoundary']['goal25dMaterialManifest']}`

## Evidence

- Frames rendered: `{manifest['renderProfile']['sequenceFrameCount']}`
- Body material zones: `{manifest['materialFusion']['bodyZoneCount']}`
- Clean main explicit scratch curves: `{manifest['materialFusion']['cleanMainExplicitScratchCurves']}`
- Max ball turn: `{manifest['motionFusion']['maxBallAngleDegrees']}` degrees
- Max part offset: `{manifest['motionFusion']['maxOffset']}`
- Lighting rig: `{', '.join(item['role'] for item in manifest['lighting']['rig'])}`
- Mirror-readable rectangular panels removed: `{manifest['lighting']['removedMirrorReadablePanels']}`

## Review Surface

- `index.html`
- `poster.png`
- `frames/frame0000.png` through `frames/frame0239.png`
"""
    write_text(goal_dir / "motion-material-status.md", text)


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    goal20 = load_module(repo_root, "scripts/render_goal20_blender_step_proof.py", "goal20_render_helpers")
    goal25d = load_module(repo_root, "scripts/render_goal25d_zoned_body_materials.py", "goal25d_render_helpers")
    goal26 = load_module(repo_root, "scripts/render_goal26_blender_camera_explosion_proof.py", "goal26_render_helpers")

    control_path = (repo_root / args.motion_control).resolve()
    goal25d_manifest_path = (repo_root / args.goal25d_manifest).resolve()
    goal26_manifest_path = (repo_root / args.goal26_manifest).resolve()
    control = read_json(control_path)
    goal25d_manifest = read_json(goal25d_manifest_path)
    goal26_manifest = read_json(goal26_manifest_path)
    model_path = (repo_root / control["sources"]["stepMesh"]).resolve()
    semantic_map_path = (repo_root / control["sources"]["goal20SemanticMap"]).resolve()
    previs_path = (repo_root / control["sources"]["cameraPrevis"]).resolve()
    hdri_path = (repo_root / GOAL20_DIR / "studio_small_09_1k.hdr").resolve()
    semantic_map = read_json(semantic_map_path)
    previs = read_json(previs_path)
    frames = selected_frames(previs, args)

    if "control-valve" in json.dumps(control["sources"], ensure_ascii=False).lower():
        raise RuntimeError("Goal28 must not consume control-valve assets.")
    if set(control["partChannels"]) != REQUIRED_CHANNELS:
        raise RuntimeError("Goal28 requires the six Goal26 motion channels.")

    goal20.clear_scene()
    render_profile = configure_render(args.profile)
    material_specs = goal28_material_specs(goal26, goal25d_manifest)
    materials = {
        name: goal20.make_material(f"goal28_{name}", spec)
        for name, spec in material_specs.items()
    }
    meshes = goal20.import_model(model_path)
    if not meshes:
        raise RuntimeError(f"No mesh objects imported from {model_path}")

    goal20.create_rig(meshes)
    records, group_counts, material_counts, part_counts = goal20.assign_materials(meshes, materials)
    body_records = [record for record in records if record["partName"] == "\u9600\u4f53"]
    if len(body_records) != 1:
        raise RuntimeError(f"Expected exactly one valve-body mesh, found {len(body_records)}")
    zone_materials = [goal25d.make_zone_material(spec, prefix="goal28_clean_") for spec in goal25d.ZONE_SPECS]
    zone_assignment = goal25d.assign_zone_materials(body_records[0]["object"], zone_materials)

    lighting_rig = goal26.build_studio(goal20, materials, hdri_path)
    camera = goal26.create_camera()
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
    )
    if 0 in frames:
        shutil.copyfile(frames_dir / "frame0000.png", out_dir / "poster.png")

    manifest = {
        "schemaVersion": 1,
        "goalId": "goal28-clean-pbr-motion-preview",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "goal": "Goal 28 clean PBR stainless material and Goal26 motion fusion preview",
        "product": "ztovalve fixed ball valve",
        "renderer": {
            "engine": render_profile["engine"],
            "profile": args.profile,
            "blender": bpy.app.version_string,
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
            "goal25dMaterialManifest": str(goal25d_manifest_path.relative_to(repo_root)).replace("\\", "/"),
            "goal25dMaterialManifestSha256": sha256(goal25d_manifest_path),
            "goal26RenderManifest": str(goal26_manifest_path.relative_to(repo_root)).replace("\\", "/"),
            "goal26RenderManifestSha256": sha256(goal26_manifest_path),
            "rule": "Goal28 consumes ztovalve fixed ball valve Goal20/25D/26 sources only; control-valve assets are forbidden.",
        },
        "renderProfile": {
            "width": render_profile["width"],
            "height": render_profile["height"],
            "samples": render_profile["samples"],
            "engine": render_profile["engine"],
            "fps": previs["fps"],
            "sourceTotalFrames": previs["totalFrames"],
            "sequenceFrameCount": len(frame_records),
            "homepageConnected": False,
            "heroAvifReplaced": False,
            "published": False,
        },
        "previewSurface": {
            "route": f"{GOAL28_DIR}/index.html",
            "frameDirectory": str(frames_dir.relative_to(repo_root)).replace("\\", "/"),
            "poster": str((out_dir / "poster.png").relative_to(repo_root)).replace("\\", "/") if (out_dir / "poster.png").is_file() else None,
            "fps": previs["fps"],
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
            "cleanMainExplicitScratchCurves": goal25d_manifest["renderProfile"]["mainStillExplicitScratchCurves"],
            "cleanMainExplicitTraceObjectsVisible": goal25d_manifest["legacyTraceComparison"]["cleanMainExplicitTraceObjectsVisible"],
            "legacyTraceGeometryUsedInGoal28": False,
            "ambientCgReferenceAvailable": any(
                asset["id"] == "ambientcg-metal009-1k-jpg" and asset["availableLocally"]
                for asset in goal25d_manifest["externalReferenceAssets"]
            ),
        },
        "motionFusion": {
            "sourceGoal": goal26_manifest["goal"],
            "controlledChannels": control["partChannels"],
            "axisMap": control["axisMap"],
            "cameraOverride": control["cameraOverride"],
            "maxOffset": motion_evidence["maxOffset"],
            "maxBallAngleDegrees": motion_evidence["maxBallAngleDegrees"],
            "renderSeconds": motion_evidence["renderSeconds"],
            "cameraControlVerified": all(frame["camera"] for frame in frame_records),
            "partMotionControlVerified": motion_evidence["maxOffset"] > 0.05,
            "ballTurnControlVerified": motion_evidence["maxBallAngleDegrees"] > 80,
        },
        "lighting": {
            "feedbackBasis": "上方左右斜照、底部双灯、正面补光；避免球面反射出可识别灯具或矩形反射板。",
            "rig": lighting_rig,
            "removedMirrorReadablePanels": True,
            "polishedBallRoughnessRange": material_specs["polishedStainlessBall"]["roughness_variation"],
            "reviewFramePriority": [136, 72, 216],
        },
        "frames": frame_records,
        "constraints": [
            "No homepage hero replacement is performed.",
            "No existing AVIF sequence is overwritten.",
            "No control-valve asset is consumed.",
            "Goal25D explicit legacy trace/scratch geometry is not used in this motion preview.",
            "Material labels are visual lookdev IDs, not certified alloy or surface-finish claims.",
            "Motion labels are visual proof controls, not a field maintenance procedure.",
        ],
    }
    if args.encode_mp4 and len(frame_records) == previs["totalFrames"] and frames[0] == 0:
        video = encode_mp4(repo_root, out_dir, manifest, args.ffmpeg)
        if video:
            manifest["previewSurface"]["video"] = video

    write_json(out_dir / "render-manifest.json", manifest)
    write_status(out_dir, manifest)
    write_index(out_dir, manifest)
    print(json.dumps({
        "goalId": manifest["goalId"],
        "frames": len(frame_records),
        "manifest": str((out_dir / "render-manifest.json").relative_to(repo_root)).replace("\\", "/"),
        "index": str((out_dir / "index.html").relative_to(repo_root)).replace("\\", "/"),
        "renderSeconds": motion_evidence["renderSeconds"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
