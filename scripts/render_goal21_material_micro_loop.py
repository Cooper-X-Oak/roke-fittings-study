#!/usr/bin/env python3
"""Render Goal 21 two-still Blender/Cycles material micro-loop.

Run inside Blender:
blender --background --python scripts/render_goal21_material_micro_loop.py -- --repo-root . --profile smoke
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
except ImportError as exc:  # pragma: no cover - normal Python cannot provide bpy.
    raise SystemExit(
        "This script must be run by Blender's Python interpreter, not system Python."
    ) from exc


GOAL20_DIR = "docs/assets/ztovalve/hero/goal20-blender-cycles-step-proof"
GOAL21_DIR = "docs/assets/ztovalve/hero/goal21-blender-material-micro-loop"


MATERIAL_OVERRIDES = {
    "castBlastedStainless": {
        "base_color": (0.40, 0.42, 0.40, 1.0),
        "metallic": 1.0,
        "roughness": 0.60,
        "anisotropic": 0.16,
        "coat": 0.03,
        "bump": 0.018,
        "bump_distance": 0.0022,
        "noise_scale": 1800,
        "noise_detail": 15,
        "color_variation": ((0.34, 0.36, 0.34, 1.0), (0.52, 0.54, 0.50, 1.0)),
        "color_noise_scale": 1500,
        "color_noise_detail": 12,
        "roughness_variation": (0.52, 0.74),
        "roughness_noise_scale": 1200,
        "roughness_noise_detail": 12,
    },
    "machinedStainless": {
        "base_color": (0.56, 0.58, 0.55, 1.0),
        "metallic": 1.0,
        "roughness": 0.26,
        "anisotropic": 0.78,
        "coat": 0.12,
        "bump": 0.01,
        "bump_distance": 0.006,
        "noise_scale": 180,
        "noise_detail": 10,
        "roughness_variation": (0.18, 0.36),
        "roughness_noise_scale": 160,
    },
    "polishedStainlessBall": {
        "base_color": (0.76, 0.78, 0.75, 1.0),
        "metallic": 1.0,
        "roughness": 0.16,
        "anisotropic": 0.04,
        "coat": 0.16,
        "bump": 0.0,
        "bump_distance": 0.0,
        "noise_scale": 280,
        "noise_detail": 6,
        "roughness_variation": (0.145, 0.18),
        "roughness_noise_scale": 65,
        "roughness_noise_detail": 7,
    },
    "graphitePacking": {
        "base_color": (0.008, 0.009, 0.010, 1.0),
        "metallic": 0.08,
        "roughness": 0.70,
        "anisotropic": 0.0,
        "coat": 0.0,
        "bump": 0.028,
        "bump_distance": 0.006,
        "noise_scale": 90,
        "noise_detail": 10,
    },
    "softSealPtfe": {
        "base_color": (0.66, 0.62, 0.52, 1.0),
        "metallic": 0.0,
        "roughness": 0.58,
        "anisotropic": 0.0,
        "coat": 0.01,
        "bump": 0.006,
        "bump_distance": 0.004,
        "noise_scale": 80,
        "noise_detail": 8,
    },
    "fastenerStainless": {
        "base_color": (0.22, 0.24, 0.23, 1.0),
        "metallic": 1.0,
        "roughness": 0.34,
        "anisotropic": 0.40,
        "coat": 0.05,
        "bump": 0.012,
        "bump_distance": 0.005,
        "noise_scale": 190,
        "noise_detail": 9,
        "roughness_variation": (0.25, 0.44),
        "roughness_noise_scale": 180,
    },
    "goal21FloorGrey": {
        "base_color": (0.48, 0.49, 0.47, 1.0),
        "metallic": 0.0,
        "roughness": 0.82,
        "anisotropic": 0.0,
        "coat": 0.0,
        "bump": 0.0,
        "noise_scale": 1,
        "noise_detail": 1,
    },
    "goal21SoftWhitePanel": {
        "base_color": (0.72, 0.73, 0.70, 1.0),
        "metallic": 0.0,
        "roughness": 0.68,
        "anisotropic": 0.0,
        "coat": 0.0,
        "bump": 0.0,
        "noise_scale": 1,
        "noise_detail": 1,
    },
    "goal21CharcoalPanel": {
        "base_color": (0.22, 0.23, 0.23, 1.0),
        "metallic": 0.0,
        "roughness": 0.90,
        "anisotropic": 0.0,
        "coat": 0.0,
        "bump": 0.0,
        "noise_scale": 1,
        "noise_detail": 1,
    },
}


CAMERA_SETUPS = [
    {
        "id": "cast-blasted-body",
        "stateId": "assembled",
        "name": "喷砂不锈钢阀体",
        "filename": "01-cast-blasted-stainless-body.png",
        "purpose": "专门检查 castBlastedStainless 是否脱离白模感，呈现较暗的喷砂/珠喷 satin stainless 中灰表面。",
        "targetPart": "阀体",
        "cameraOffset": (0.58, -0.98, 0.25),
        "targetOffset": (0.045, -0.045, -0.015),
        "lensMm": 74,
    },
    {
        "id": "polished-ball-reflection",
        "stateId": "detail-open",
        "name": "抛光球体棚拍反射",
        "filename": "02-polished-stainless-ball-reflection.png",
        "purpose": "专门检查 polishedStainlessBall 是否使用宽软棚拍反射，减少硬黑白块。",
        "targetPart": "球体",
        "cameraOffset": (0.55, -0.92, 0.28),
        "targetOffset": (0.0, -0.008, 0.0),
        "lensMm": 82,
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
    parser.add_argument("--hdri", default=f"{GOAL20_DIR}/studio_small_09_1k.hdr")
    parser.add_argument("--out-dir", default=f"{GOAL21_DIR}/stills")
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


def configure_render(profile: str) -> dict:
    profiles = {
        "smoke": {"width": 1600, "height": 900, "samples": 48},
        "proof": {"width": 2560, "height": 1440, "samples": 128},
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
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    try:
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "Medium High Contrast"
    except TypeError:
        pass
    scene.view_settings.exposure = -0.70
    scene.view_settings.gamma = 1
    try:
        scene.cycles.device = "GPU"
    except Exception:
        scene.cycles.device = "CPU"
    return selected


def make_goal21_materials(goal20) -> dict:
    specs = dict(goal20.MATERIAL_SPECS)
    specs.update(MATERIAL_OVERRIDES)
    return {name: goal20.make_material(name, spec) for name, spec in specs.items()}


def add_area_light(goal20, name: str, location, target, power: float, size):
    return goal20.add_area_light(name, location, target, power, size)


def add_plane(goal20, name: str, material, location, scale, rotation=(0, 0, 0), camera_visible=True):
    return goal20.add_plane(name, material, location, scale, rotation, camera_visible)


def build_goal21_studio(goal20, materials: dict, hdri_path: Path | None) -> None:
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
            background.inputs["Strength"].default_value = 0.08
    else:
        world.color = (0.54, 0.55, 0.53)

    add_plane(
        goal20,
        "goal21_neutral_floor",
        materials["goal21FloorGrey"],
        (0, 0, -0.178),
        (4.4, 3.2, 1),
    )
    add_plane(
        goal20,
        "goal21_soft_rear_cyc",
        materials["goal21FloorGrey"],
        (0, 0.86, 0.50),
        (4.4, 1.65, 1),
        rotation=(math.radians(74), 0, 0),
    )

    add_plane(
        goal20,
        "goal21_left_soft_reflection_panel",
        materials["goal21SoftWhitePanel"],
        (-1.85, -0.78, 0.46),
        (0.95, 2.25, 1),
        rotation=(0, math.radians(72), math.radians(9)),
        camera_visible=False,
    )
    add_plane(
        goal20,
        "goal21_right_soft_reflection_panel",
        materials["goal21SoftWhitePanel"],
        (1.78, -0.10, 0.42),
        (0.72, 1.95, 1),
        rotation=(0, math.radians(-74), math.radians(-7)),
        camera_visible=False,
    )
    add_plane(
        goal20,
        "goal21_top_charcoal_reflection_flag",
        materials["goal21CharcoalPanel"],
        (0.05, -0.50, 1.65),
        (2.7, 0.72, 1),
        rotation=(math.radians(80), 0, 0),
        camera_visible=False,
    )

    add_area_light(goal20, "goal21_left_broad_softbox", (-1.55, -1.65, 1.10), (0, 0, 0.05), 170, 3.1)
    add_area_light(goal20, "goal21_top_long_soft_strip", (0.10, -0.38, 1.78), (0, 0, 0.04), 90, (0.40, 2.90))
    add_area_light(goal20, "goal21_right_low_rim", (1.22, 0.58, 0.72), (0, 0, 0.02), 48, 1.75)
    add_area_light(goal20, "goal21_front_gentle_fill", (0.25, -1.28, 0.24), (0, 0, 0.02), 10, 1.45)


def render_stills(goal20, repo_root: Path, out_dir: Path, records: list, camera) -> list[dict]:
    stills = []
    for setup in CAMERA_SETUPS:
        goal20.apply_state(records, setup["stateId"])
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
        camera.data.lens = setup["lensMm"]
        goal20.look_at(camera, target)
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
        src = html.escape(still["path"].split("/goal21-blender-material-micro-loop/")[-1])
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
  <title>Goal 21 Blender Material Micro Loop</title>
  <style>
    :root {{ color-scheme: light; font-family: Inter, \"Noto Sans SC\", system-ui, sans-serif; background: #eceeec; color: #111827; }}
    body {{ margin: 0; }}
    main {{ width: min(1440px, calc(100% - 40px)); margin: 0 auto; padding: 34px 0 54px; }}
    header {{ display: grid; gap: 10px; margin-bottom: 22px; }}
    .eyebrow {{ margin: 0; color: #58606c; font-size: 13px; text-transform: uppercase; letter-spacing: .08em; }}
    h1 {{ margin: 0; font-size: clamp(28px, 4vw, 46px); line-height: 1.03; letter-spacing: 0; }}
    .summary {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin: 18px 0 26px; }}
    .metric {{ border: 1px solid #d0d5dd; background: #fff; border-radius: 8px; padding: 14px 16px; }}
    .metric b {{ display: block; font-size: 22px; }}
    .metric span {{ color: #667085; font-size: 13px; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }}
    figure {{ margin: 0; border: 1px solid #d0d5dd; background: #fff; border-radius: 8px; overflow: hidden; }}
    img {{ display: block; width: 100%; height: auto; background: #d7dad8; }}
    figcaption {{ display: grid; gap: 4px; padding: 12px 14px 14px; }}
    figcaption span {{ color: #667085; font-size: 13px; line-height: 1.45; }}
    code {{ background: #e4e7ec; padding: 2px 5px; border-radius: 5px; }}
    @media (max-width: 820px) {{
      main {{ width: min(100% - 24px, 720px); padding-top: 24px; }}
      .summary, .grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
<main>
  <header>
    <p class=\"eyebrow\">Goal 21 / Blender Cycles / material micro-loop</p>
    <h1>喷砂不锈钢与抛光球体</h1>
    <p>这里只做两张材质 still：阀体喷砂不锈钢和球体棚拍反射。不替换 hero，不生成 24 或 240 帧。</p>
  </header>
  <section class=\"summary\">
    <div class=\"metric\"><b>{manifest['renderProfile']['width']}x{manifest['renderProfile']['height']}</b><span>render size</span></div>
    <div class=\"metric\"><b>{manifest['partIdentity']['meshCount']}</b><span>STEP mesh instances</span></div>
    <div class=\"metric\"><b>2</b><span>focused materials</span></div>
    <div class=\"metric\"><b>{len(manifest['stills'])}</b><span>rendered stills</span></div>
  </section>
  <section class=\"grid\">
    {''.join(cards)}
  </section>
  <p>Manifest: <code>render-manifest.json</code>. Material status: <code>material-status.md</code>. Source mesh remains Goal 20's STEP-derived <code>goal20-step-mesh.glb</code>.</p>
</main>
</body>
</html>
"""
    (goal_dir / "index.html").write_text(html_text, encoding="utf-8")


def write_material_status(goal_dir: Path, manifest: dict) -> None:
    text = f"""# Goal 21 Blender/Cycles Material Micro Loop

Generated: 2026-08-02

## Boundary

- Goal 21 renders exactly two material stills.
- It does not replace the homepage hero.
- It does not render a 24-frame motion test or 240-frame release sequence.
- The source mesh remains the Goal 20 STEP-derived GLB.

## Focus

1. `castBlastedStainless`: darker midtone stainless with fine procedural bead-blast roughness.
2. `polishedStainlessBall`: wider, softer studio reflections with reduced hard black/white blocks.

## Implementation Notes

- The white-dominant Goal 20 studio was replaced with a neutral grey floor/cyc and camera-invisible soft reflection panels.
- The ball material uses low roughness variation to keep a polished read while softening card-shaped reflections.
- The cast body uses high-frequency procedural noise for bump, roughness and subtle color variation. This avoids UV dependency on the STEP-derived CAD mesh.
- External PBR texture libraries were not imported in this pass because this CAD mesh has no reviewed UV unwrap. Procedural object-space shading is the safer small-loop test.

## Current Assessment

This is a material-direction iteration, not final approval.

- The body has moved away from the obvious white engineering-preview material.
- The body now has more usable midtone metal and shadow separation.
- The bead-blasted / sandblasted surface is still not fully convincing as a premium commercial product material.
- The ball is back to a polished read, but the reflection is still more card-shaped than a high-end KeyShot studio setup.
- The next commercial-quality route should test a better light tent/HDRI setup and, if UVs can be generated cleanly, CC0 PBR metal roughness/normal maps.

## External Material Route Checked

- Blender's native Principled BSDF remains the right base shader for this loop because it exposes metallic, roughness, coat and anisotropy controls.
- Poly Haven provides CC0 HDRIs and can be used for studio/environment lighting.
- ambientCG provides CC0 PBR materials, including metal material maps, but those are safer after UV/tri-planar mapping is designed for this CAD mesh.

## Render

- Profile: `{manifest['profile']}`
- Size: `{manifest['renderProfile']['width']}x{manifest['renderProfile']['height']}`
- Samples: `{manifest['renderProfile']['samples']}`
- Stills: `{len(manifest['stills'])}`

"""
    (goal_dir / "material-status.md").write_text(text, encoding="utf-8")


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    goal20 = load_goal20_module(repo_root)
    model_path = (repo_root / args.model).resolve()
    step_report_path = (repo_root / args.step_report).resolve()
    step_audit_path = (repo_root / args.step_audit).resolve()
    hdri_path = (repo_root / args.hdri).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    goal_dir = out_dir.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    step_report = read_json(step_report_path)
    step_audit = read_json(step_audit_path)

    goal20.clear_scene()
    render_profile = configure_render(args.profile)
    materials = make_goal21_materials(goal20)
    meshes = goal20.import_model(model_path)
    if not meshes:
        raise RuntimeError(f"No mesh objects imported from {model_path}")

    goal20.create_rig(meshes)
    records, group_counts, material_counts, part_counts = goal20.assign_materials(meshes, materials)
    build_goal21_studio(goal20, materials, hdri_path)
    camera = goal20.create_camera()
    stills = render_stills(goal20, repo_root, out_dir, records, camera)

    focused_records = []
    for record in records:
        if record["material"] not in ("castBlastedStainless", "polishedStainlessBall"):
            continue
        _min_v, _max_v, center, size = goal20.object_bounds(record["object"])
        focused_records.append(
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
        "goal": "Goal 21 Blender/Cycles material micro-loop",
        "profile": args.profile,
        "renderer": "Blender Cycles",
        "blender": bpy.app.version_string,
        "sourceBoundary": {
            "stepSource": step_report["source"]["path"],
            "stepSourceSha256": step_report["source"]["sha256"],
            "stepMesh": str(model_path.relative_to(repo_root)).replace("\\", "/"),
            "stepMeshSha256": sha256(model_path),
            "sourceMeshAuthority": "Goal 21 reuses the Goal 20 STEP-derived mesh and does not overwrite source CAD or the homepage GLB.",
        },
        "renderProfile": {
            "width": render_profile["width"],
            "height": render_profile["height"],
            "samples": render_profile["samples"],
            "engine": "Cycles",
            "frameSequenceRendered": False,
            "motionTestRendered": False,
            "fullReleaseFrameCount": 0,
            "homepageConnected": False,
        },
        "materialFocus": {
            "castBlastedStainless": "investment cast stainless steel, bead-blasted / sandblasted satin finish visual treatment",
            "polishedStainlessBall": "mirror polished stainless steel ball with softened studio reflection",
        },
        "lighting": {
            "hdri": str(hdri_path.relative_to(repo_root)).replace("\\", "/") if hdri_path.is_file() else None,
            "strategy": "neutral grey studio, low HDRI strength, large camera-invisible soft reflection panels, restrained softboxes",
            "sources": [
                "goal21_left_broad_softbox",
                "goal21_top_long_soft_strip",
                "goal21_right_low_rim",
                "goal21_front_gentle_fill",
                "goal21_left_soft_reflection_panel",
                "goal21_right_soft_reflection_panel",
                "goal21_top_charcoal_reflection_flag",
            ],
        },
        "partIdentity": {
            "meshCount": len(meshes),
            "sourceStepProductNameCount": len(step_audit["productNames"]),
            "focusedRecordCount": len(focused_records),
            "focusedPartCounts": dict(Counter(record["partName"] for record in focused_records)),
        },
        "groupCounts": group_counts,
        "materialCounts": material_counts,
        "partCounts": part_counts,
        "focusedRecords": focused_records,
        "stills": stills,
        "constraints": [
            "Goal 21 is a two-still material loop only.",
            "No homepage hero replacement is performed.",
            "No 24-frame or 240-frame animation is rendered.",
            "Material labels remain visual treatments, not certified product material claims.",
        ],
    }
    write_json(goal_dir / "render-manifest.json", manifest)
    write_material_status(goal_dir, manifest)
    write_index(goal_dir, manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
