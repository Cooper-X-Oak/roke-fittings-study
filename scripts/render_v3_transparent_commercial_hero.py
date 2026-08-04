#!/usr/bin/env python3
"""Render the fixed ball valve hero as transparent commercial PNG frames.

This script promotes the V3 semantic preview into the homepage asset pipeline:
transparent RGBA frames, no background geometry or text, restrained metallic
materials, product-studio lighting, and the existing V3 motion rhythm.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import bpy
    from mathutils import Matrix, Vector
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Run this script with Blender's Python interpreter.") from exc


DEFAULT_MAP = "docs/assets/ztovalve/hero/v3-semantic-node-map.json"
DEFAULT_OUT_DIR = ".scratch/assets/ztovalve/hero/v3-transparent-commercial-240"
DEFAULT_MANIFEST = "docs/assets/ztovalve/hero/v3-transparent-commercial-240-manifest.json"
DEFAULT_FALLBACK = "docs/assets/ztovalve/hero/fixed-ball-valve-mobile-fallback.png"
LOW_COST_SCRIPT = "scripts/render_v3_low_cost_preview_bundle.py"
OWNED_PREFIX = "v3_commercial_"


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    args = argv[argv.index("--") + 1 :] if "--" in argv else argv[1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--semantic-map", default=DEFAULT_MAP)
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--fallback-out", default=DEFAULT_FALLBACK)
    parser.add_argument("--frame-count", type=int, default=240)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=540)
    parser.add_argument("--samples", type=int, default=96)
    parser.add_argument("--frame-list", default="")
    parser.add_argument("--skip-fallback", action="store_true")
    parser.add_argument("--no-clear", action="store_true")
    return parser.parse_args(args)


def project_path(repo_root: Path, value: str) -> Path:
    path = (repo_root / value).resolve()
    path.relative_to(repo_root)
    return path


def project_rel(repo_root: Path, path: Path) -> str:
    return str(path.resolve().relative_to(repo_root)).replace("\\", "/")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_frame_list(value: str, frame_count: int) -> list[int] | None:
    if not value.strip():
        return None
    frames: list[int] = []
    for item in value.split(","):
        frame = int(item.strip())
        if frame < 0 or frame >= frame_count:
            raise RuntimeError(f"Frame {frame} is outside 0..{frame_count - 1}.")
        if frame not in frames:
            frames.append(frame)
    return frames


def load_base_module(repo_root: Path) -> Any:
    script_path = project_path(repo_root, LOW_COST_SCRIPT)
    spec = importlib.util.spec_from_file_location("v3_low_cost_base_for_commercial", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load base V3 renderer: {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.OWNED_PREFIX = OWNED_PREFIX
    return module


def clear_previous_outputs(out_dir: Path) -> None:
    frames_dir = out_dir / "frames"
    if frames_dir.is_dir():
        for frame in frames_dir.glob("*.png"):
            frame.unlink()


def set_input(node: Any, names: list[str], value: Any) -> None:
    for name in names:
        if name in node.inputs:
            node.inputs[name].default_value = value
            return


def safe_set(obj: Any, attr: str, value: Any) -> None:
    if hasattr(obj, attr):
        try:
            setattr(obj, attr, value)
        except Exception:
            pass


def make_material(
    name: str,
    color: tuple[float, float, float, float],
    metallic: float,
    roughness: float,
    *,
    specular: float = 0.55,
    coat: float = 0.0,
    coat_roughness: float = 0.32,
) -> Any:
    material = bpy.data.materials.new(f"{OWNED_PREFIX}{name}")
    material.use_nodes = True
    material.diffuse_color = color
    safe_set(material, "blend_method", "BLEND")
    safe_set(material, "surface_render_method", "BLENDED")
    safe_set(material, "show_transparent_back", False)
    nodes = material.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        set_input(bsdf, ["Base Color"], color)
        set_input(bsdf, ["Metallic"], metallic)
        set_input(bsdf, ["Roughness"], roughness)
        set_input(bsdf, ["Alpha"], color[3])
        set_input(bsdf, ["Specular IOR Level", "Specular"], specular)
        set_input(bsdf, ["Coat Weight", "Clearcoat"], coat)
        set_input(bsdf, ["Coat Roughness", "Clearcoat Roughness"], coat_roughness)
    return material


def make_emission_material(name: str, color: tuple[float, float, float, float], strength: float) -> Any:
    material = bpy.data.materials.new(f"{OWNED_PREFIX}{name}")
    material.use_nodes = True
    material.diffuse_color = color
    safe_set(material, "blend_method", "BLEND")
    nodes = material.node_tree.nodes
    nodes.clear()
    output = nodes.new(type="ShaderNodeOutputMaterial")
    emission = nodes.new(type="ShaderNodeEmission")
    emission.inputs["Color"].default_value = color
    emission.inputs["Strength"].default_value = strength
    material.node_tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return material


def set_material_alpha(material: Any, alpha: float) -> None:
    rgba = tuple(material.diffuse_color)
    material.diffuse_color = (rgba[0], rgba[1], rgba[2], alpha)
    if material.use_nodes:
        bsdf = material.node_tree.nodes.get("Principled BSDF")
        if bsdf and "Alpha" in bsdf.inputs:
            bsdf.inputs["Alpha"].default_value = alpha


def prepare_materials() -> dict[str, Any]:
    return {
        "body": make_material("satin_cast_stainless_body", (0.20, 0.225, 0.225, 1.0), 0.92, 0.44, specular=0.70),
        "machined": make_material("machined_stainless_edges", (0.34, 0.36, 0.35, 1.0), 0.96, 0.28, specular=0.78, coat=0.16),
        "ball": make_material("polished_stainless_ball", (0.48, 0.49, 0.46, 1.0), 1.0, 0.12, specular=0.86, coat=0.32, coat_roughness=0.20),
        "seat": make_material("warm_satin_seat_ring", (0.46, 0.37, 0.23, 1.0), 0.74, 0.35, specular=0.64),
        "seal": make_material("controlled_dark_seal", (0.028, 0.030, 0.030, 1.0), 0.05, 0.68, specular=0.32),
        "top": make_material("top_stack_satin_metal", (0.24, 0.275, 0.27, 1.0), 0.88, 0.38, specular=0.62),
        "fastener": make_material("dark_satin_fasteners", (0.12, 0.135, 0.135, 1.0), 0.82, 0.38, specular=0.54),
        "flow": make_emission_material("subtle_flow_cue", (0.16, 0.50, 0.78, 1.0), 0.32),
        "stem_axis": make_emission_material("hidden_stem_axis_reference", (0.34, 0.47, 0.55, 1.0), 0.08),
        "reflection_white": make_emission_material("reflection_softbox_white", (0.84, 0.86, 0.84, 1.0), 0.86),
        "reflection_cool": make_emission_material("reflection_cool_strip", (0.44, 0.55, 0.60, 1.0), 0.58),
        "reflection_dark": make_material("reflection_dark_flag", (0.010, 0.012, 0.012, 1.0), 0.0, 0.92),
    }


def part_material_key(group_id: str, part_name: str) -> str:
    if part_name == "球体":
        return "ball"
    if "密封圈" in part_name or "盘根" in part_name or "填料" in part_name:
        return "seal"
    if "阀座" in part_name or "压圈" in part_name:
        return "seat"
    if group_id == "body-pressure-shell":
        return "body" if part_name == "阀体" else "machined"
    if group_id in {"top-bracket-actuator", "stem-packing-drive"}:
        return "top"
    if group_id == "fasteners-small-hardware":
        return "fastener"
    return "machined"


def assign_materials(groups: dict[str, list[Any]], materials: dict[str, Any]) -> None:
    for group_id, objects in groups.items():
        for obj in objects:
            part_name = str(obj.get("v3_part_name", ""))
            key = part_material_key(group_id, part_name)
            obj.data.materials.clear()
            obj.data.materials.append(materials[key])
            obj["v3_commercial_material_key"] = key


def configure_render(width: int, height: int, samples: int) -> dict[str, Any]:
    scene = bpy.context.scene
    engine = "BLENDER_EEVEE"
    for candidate in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = candidate
            engine = candidate
            break
        except Exception:
            continue

    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.film_transparent = True
    scene.render.use_persistent_data = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.compression = 12

    try:
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "Medium High Contrast"
    except Exception:
        pass
    scene.view_settings.exposure = -0.48
    scene.view_settings.gamma = 1.0

    eevee = getattr(scene, "eevee", None)
    if eevee:
        for attr, value in (
            ("taa_render_samples", samples),
            ("taa_samples", min(samples, 64)),
            ("use_gtao", True),
            ("gtao_distance", 3),
            ("gtao_factor", 1.12),
            ("use_soft_shadows", True),
            ("use_bloom", False),
            ("use_ssr", True),
            ("use_ssr_refraction", False),
        ):
            if hasattr(eevee, attr):
                try:
                    setattr(eevee, attr, value)
                except Exception:
                    pass

    world = scene.world or bpy.data.worlds.new(f"{OWNED_PREFIX}world")
    scene.world = world
    world.color = (0.64, 0.66, 0.65)
    if hasattr(world, "use_nodes"):
        world.use_nodes = True
        background = world.node_tree.nodes.get("Background") if world.node_tree else None
        if background:
            background.inputs["Color"].default_value = (0.64, 0.66, 0.65, 1.0)
            background.inputs["Strength"].default_value = 0.18

    return {
        "engine": engine,
        "width": width,
        "height": height,
        "samples": samples,
        "filmTransparent": True,
        "pngColorMode": "RGBA",
        "profile": "transparent-commercial-pbr-studio",
    }


def look_at(obj: Any, target: Vector) -> None:
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def add_area_light(
    name: str,
    product_center: Vector,
    span: float,
    offset: tuple[float, float, float],
    energy: float,
    size_factor: float,
) -> dict[str, Any]:
    light_data = bpy.data.lights.new(f"{OWNED_PREFIX}{name}_data", "AREA")
    light = bpy.data.objects.new(f"{OWNED_PREFIX}{name}", light_data)
    bpy.context.scene.collection.objects.link(light)
    light.location = product_center + Vector(offset) * span
    light_data.energy = energy
    light_data.size = span * size_factor
    safe_set(light_data, "use_shadow", True)
    safe_set(light_data, "use_contact_shadow", True)
    look_at(light, product_center)
    return {
        "name": light.name,
        "location": [round(value, 5) for value in light.location],
        "energy": energy,
        "size": round(light_data.size, 5),
    }


def add_lighting(product_center: Vector, product_extent: Vector) -> list[dict[str, Any]]:
    span = max(product_extent.x, product_extent.y, product_extent.z)
    return [
        add_area_light("key_large_left", product_center, span, (-1.25, -2.20, 1.72), 360, 5.4),
        add_area_light("rim_right_edge", product_center, span, (1.75, -0.42, 1.22), 240, 3.0),
        add_area_light("front_soft_fill", product_center, span, (0.05, -2.85, 0.38), 54, 5.8),
        add_area_light("low_lift", product_center, span, (-0.48, -1.35, -0.82), 38, 2.4),
        add_area_light("top_long_strip", product_center, span, (-0.12, -1.35, 2.35), 96, 4.8),
    ]


def improve_mesh_shading(groups: dict[str, list[Any]]) -> None:
    for group_id, objects in groups.items():
        for obj in objects:
            if obj.type != "MESH":
                continue
            if group_id != "fasteners-small-hardware":
                for polygon in obj.data.polygons:
                    polygon.use_smooth = True
            if group_id in {"body-pressure-shell", "ball-trunnion-core", "seat-seal-system", "top-bracket-actuator", "stem-packing-drive"}:
                modifier = obj.modifiers.new(f"{OWNED_PREFIX}weighted_normals", "WEIGHTED_NORMAL")
                modifier.keep_sharp = True
                modifier.weight = 55


def make_records(inspection: Any, node_to_object: dict[int, Any], groups: dict[str, list[Any]], ball_center: Vector) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for group_id, objects in groups.items():
        for obj in objects:
            bounds = inspection.world_bounds([obj])
            center = inspection.center_from_bounds(bounds)
            records.append(
                {
                    "object": obj,
                    "nodeIndex": int(obj.get("v3_node_index")),
                    "group": group_id,
                    "partName": str(obj.get("v3_part_name", "")),
                    "baseMatrix": obj.matrix_world.copy(),
                    "baseCenter": center,
                    "localCenter": center - ball_center,
                    "materialKey": str(obj.get("v3_commercial_material_key", "")),
                }
            )
    records.sort(key=lambda item: item["nodeIndex"])
    return records


def apply_state(
    base: Any,
    records: list[dict[str, Any]],
    state: dict[str, float],
    axes: dict[str, Vector],
    ball_center: Vector,
    materials: dict[str, Any],
    helpers: dict[str, Any],
) -> dict[str, Any]:
    moved_counts: dict[str, int] = {}
    max_offset = 0.0
    for key in ("body", "machined"):
        set_material_alpha(materials[key], state["bodyAlpha"])

    for record in records:
        obj = record["object"]
        offset = base.object_offset(record, state, axes)
        max_offset = max(max_offset, offset.length)
        if offset.length > 0.0001:
            moved_counts[record["group"]] = moved_counts.get(record["group"], 0) + 1
        matrix = Matrix.Translation(offset) @ record["baseMatrix"]
        if record["partName"] == "球体":
            rotation = Matrix.Rotation(math.radians(state["ballAngleDegrees"]), 4, axes["stem"])
            matrix = Matrix.Translation(offset) @ Matrix.Translation(ball_center) @ rotation @ Matrix.Translation(-ball_center) @ record["baseMatrix"]
        obj.matrix_world = matrix
        obj.hide_render = False
        obj.hide_viewport = False

    function_visible = state["functionReveal"] > 0.10 and state["posterHold"] <= 0.75
    center_visible = function_visible and state["ballTurn"] < 0.52
    for name, helper in helpers.items():
        helper.hide_render = not function_visible
        helper.hide_viewport = not function_visible
        if name == "stemAxis":
            helper.hide_render = True
            helper.hide_viewport = True
        if name == "flowCenter" and not center_visible:
            helper.hide_render = True
            helper.hide_viewport = True

    bpy.context.view_layer.update()
    return {
        "movedCounts": moved_counts,
        "maxOffsetMeters": round(max_offset, 6),
        "ballNodeIndex": 23,
        "ballAngleDegrees": round(state["ballAngleDegrees"], 4),
        "bodyAlpha": round(state["bodyAlpha"], 4),
        "flowCenterVisible": bool(center_visible),
        "seatPress": round(state["seatPress"], 4),
    }


def render_frames(
    base: Any,
    repo_root: Path,
    out_dir: Path,
    records: list[dict[str, Any]],
    materials: dict[str, Any],
    helpers: dict[str, Any],
    axes: dict[str, Vector],
    ball_center: Vector,
    product_center: Vector,
    product_extent: Vector,
    frame_count: int,
    frame_list: list[int] | None,
) -> list[dict[str, Any]]:
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    camera_data = bpy.data.cameras.new(f"{OWNED_PREFIX}camera_data")
    camera = bpy.data.objects.new(f"{OWNED_PREFIX}camera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    bpy.context.scene.camera = camera

    indices = frame_list if frame_list is not None else list(range(frame_count))
    frames: list[dict[str, Any]] = []
    started = time.perf_counter()
    for ordinal, index in enumerate(indices, start=1):
        progress = index / max(1, frame_count - 1)
        state = base.state_for(progress)
        motion = apply_state(base, records, state, axes, ball_center, materials, helpers)
        camera_record = base.camera_for(camera, progress, product_center, ball_center, product_extent)
        output_path = frames_dir / f"{index:04d}.png"
        bpy.context.scene.render.filepath = str(output_path)
        bpy.ops.render.render(write_still=True)
        stage = base.stage_for(progress)
        frame_record = {
            "frameIndex": index,
            "publicFrameNumber": index + 1,
            "progress": round(progress, 6),
            **stage,
            "path": project_rel(repo_root, output_path),
            "bytes": output_path.stat().st_size,
            "sha256": sha256(output_path),
            "motion": motion,
            "camera": camera_record,
        }
        frames.append(frame_record)
        if ordinal % 12 == 0 or ordinal == len(indices):
            elapsed = time.perf_counter() - started
            print(f"transparent commercial render {ordinal}/{len(indices)} frames in {elapsed:.1f}s")
    return frames


def stage_samples(frames: list[dict[str, Any]], frame_count: int) -> list[dict[str, Any]]:
    desired = [0, 72, 120, 156, 184, frame_count - 1]
    by_index = {frame["frameIndex"]: frame for frame in frames}
    return [by_index[index] for index in desired if index in by_index]


def copy_fallback(repo_root: Path, frames_dir: Path, fallback_path: Path, frame_count: int) -> dict[str, Any] | None:
    source = frames_dir / f"{frame_count - 1:04d}.png"
    if not source.is_file():
        return None
    fallback_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, fallback_path)
    return {
        "path": project_rel(repo_root, fallback_path),
        "sourceFrame": project_rel(repo_root, source),
        "bytes": fallback_path.stat().st_size,
        "sha256": sha256(fallback_path),
        "transparentRgba": True,
    }


def build_manifest(
    repo_root: Path,
    out_dir: Path,
    semantic_map_path: Path,
    glb_path: Path,
    glb_source_kind: str,
    render_profile: dict[str, Any],
    import_result: dict[str, Any],
    measurements: dict[str, Any],
    axes_record: dict[str, Any],
    frames: list[dict[str, Any]],
    frame_count: int,
    frame_list: list[int] | None,
    lighting: list[dict[str, Any]],
    reflection_panels: list[dict[str, Any]],
    fallback: dict[str, Any] | None,
) -> dict[str, Any]:
    max_ball = max(frame["motion"]["ballAngleDegrees"] for frame in frames)
    all_rendered = frame_list is None and len(frames) == frame_count
    return {
        "schema": "ztovalve-v3-transparent-commercial-hero/v1",
        "kind": "transparent_commercial_png_staging",
        "bundleId": "ztovalve-fixed-ball-valve-v3-transparent-commercial-240",
        "status": "rendered-full-sequence" if all_rendered else "rendered-sample",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "scope": {
            "product": "ztovalve fixed ball valve",
            "motionVersion": "v3",
            "homepageConnected": all_rendered,
            "final240FrameSequencePrepared": all_rendered,
            "usesTransparentFrames": True,
            "touchesGoal30": False,
            "containsBackgroundText": False,
            "containsCameraVisibleBackdrop": False,
        },
        "sourceBoundary": {
            "semanticMap": project_rel(repo_root, semantic_map_path),
            "semanticMapSha256": sha256(semantic_map_path),
            "glb": project_rel(repo_root, glb_path),
            "glbSourceKind": glb_source_kind,
            "glbSha256": sha256(glb_path),
            "inspectionHelper": "scripts/inspect_v3_blender_closeup_asset.py",
        },
        "renderProfile": {
            **render_profile,
            "frameCount": frame_count,
            "renderedFrameCount": len(frames),
            "renderedFrameList": frame_list,
            "stagingFrameNames": "0000.png..0239.png",
            "publicAvifNames": "0001.avif..0240.avif",
            "backgroundPolicy": "film_transparent=True, PNG RGBA, no text, no wordmark, no black studio backdrop.",
            "materialPolicy": "Satin cast stainless body, brighter machined edges, polished ball, warm seat rings, restrained dark seals, dark satin fasteners.",
            "lightingPolicy": "Large product-studio key/rim/fill/low-lift area lights with transparent film; world contributes reflection/ambient light but is not camera-visible.",
        },
        "assetInspection": {
            "importedObjectCount": import_result["importedObjectCount"],
            "meshNodeCount": import_result["meshNodeCount"],
            "boundMeshNodeCount": import_result["boundMeshNodeCount"],
            "contactPassCount": measurements["passCount"],
            "contactWarnCount": measurements["warnCount"],
            "contactFailCount": measurements["failCount"],
        },
        "motionEvidence": {
            "ballNodeIndex": 23,
            "maxBallAngleDegrees": round(max_ball, 4),
            "maxOffsetMeters": max(frame["motion"]["maxOffsetMeters"] for frame in frames),
            "flowCenterInterruptedWhenClosed": any(
                not frame["motion"]["flowCenterVisible"] and frame["motion"]["ballAngleDegrees"] > 70 for frame in frames
            ),
            "transparentFrameSequence": True,
            "quarterTurnPolicy": "90-degree proof is bound to 球体 nodeIndex 23 only; no verified stem-driven coupling claim.",
        },
        "controlledGaps": [
            {
                "gapId": "missing-independent-stem-node",
                "impact": "The ball rotation is real for nodeIndex 23, but the current GLB does not expose an independent 阀杆 node; do not claim stem-driven coupling.",
            },
            {
                "gapId": "grouped-small-hardware",
                "impact": "Fasteners and springs remain grouped as secondary detail, not a verified maintenance or service sequence.",
            },
        ],
        "axisInference": axes_record,
        "scene": {
            "background": {
                "filmTransparent": True,
                "cameraVisibleGeometry": None,
                "wordmark": None,
                "textObjects": None,
            },
            "lighting": lighting,
            "reflectionPanels": reflection_panels,
            "helpers": {
                "flowCue": "Subtle internal cue only during function proof; hidden during final product hold.",
                "stemAxis": "Hidden because independent stem coupling is not verified.",
            },
        },
        "outputs": {
            "stagingDir": project_rel(repo_root, out_dir),
            "framesDir": project_rel(repo_root, out_dir / "frames"),
            "manifest": "docs/assets/ztovalve/hero/v3-transparent-commercial-240-manifest.json",
            "publicAvifDir": "docs/upload/images/zt-hero-fixed-ball-valve",
            "fallback": fallback,
        },
        "stageSamples": stage_samples(frames, frame_count),
        "frames": frames,
    }


def main() -> int:
    args = parse_args()
    if args.frame_count != 240:
        raise RuntimeError("The homepage contract requires --frame-count 240.")

    repo_root = Path(args.repo_root).resolve()
    out_dir = project_path(repo_root, args.out_dir)
    semantic_map_path = project_path(repo_root, args.semantic_map)
    manifest_path = project_path(repo_root, args.manifest)
    fallback_path = project_path(repo_root, args.fallback_out)
    frame_list = parse_frame_list(args.frame_list, args.frame_count)
    if not args.no_clear:
        clear_previous_outputs(out_dir)
    (out_dir / "frames").mkdir(parents=True, exist_ok=True)

    base = load_base_module(repo_root)
    inspection = base.load_inspection_module(repo_root)
    semantic_map = read_json(semantic_map_path)
    if semantic_map.get("schema") != "ztovalve-v3-semantic-node-map/v1":
        raise RuntimeError("Unexpected V3 semantic map schema.")
    glb_path, glb_source_kind = inspection.choose_glb(repo_root, semantic_map)
    glb_json = inspection.read_glb_json(glb_path)

    base.remove_scene_objects()
    render_profile = configure_render(args.width, args.height, args.samples)
    materials = prepare_materials()
    node_to_object, _imported_objects, import_result = inspection.import_glb_with_node_binding(glb_path, glb_json)
    groups, missing_group_selectors = inspection.bind_groups(
        semantic_map,
        node_to_object,
        {group["groupId"]: materials["body"] for group in semantic_map["groups"]},
    )
    if missing_group_selectors:
        raise RuntimeError(f"Missing V3 group selectors: {missing_group_selectors[:5]}")
    assign_materials(groups, materials)
    improve_mesh_shading(groups)

    measurements = inspection.build_measurements(node_to_object, groups)
    if measurements["failCount"] > 1:
        raise RuntimeError("Unexpected V3 contact failures beyond the known independent stem gap.")

    all_mesh_objects = [obj for obj in node_to_object.values()]
    product_bounds = inspection.world_bounds(all_mesh_objects)
    product_center = inspection.center_from_bounds(product_bounds)
    product_extent = Vector(product_bounds["extent"])
    ball_bounds = inspection.part_bounds(node_to_object, [23])
    ball_center = inspection.center_from_bounds(ball_bounds)
    ball_extent = Vector(ball_bounds["extent"])
    axes_record = measurements["axisInference"]
    axes = {
        "pipe": inspection.axis_unit(axes_record["pipeAxisIndex"]),
        "stem": inspection.axis_unit(axes_record["stemAxisIndex"]),
        "depth": Vector((0.0, -1.0, 0.0)),
    }

    lighting = add_lighting(product_center, product_extent)
    reflection_panels = base.add_reflection_rig(product_center, product_extent, materials)
    helpers = base.add_stage_helpers(ball_center, ball_extent, axes["pipe"], axes["stem"], materials)
    records = make_records(inspection, node_to_object, groups, ball_center)
    frames = render_frames(
        base,
        repo_root,
        out_dir,
        records,
        materials,
        helpers,
        axes,
        ball_center,
        product_center,
        product_extent,
        args.frame_count,
        frame_list,
    )

    fallback = None
    if not args.skip_fallback and frame_list is None:
        fallback = copy_fallback(repo_root, out_dir / "frames", fallback_path, args.frame_count)

    manifest = build_manifest(
        repo_root,
        out_dir,
        semantic_map_path,
        glb_path,
        glb_source_kind,
        render_profile,
        import_result,
        measurements,
        axes_record,
        frames,
        args.frame_count,
        frame_list,
        lighting,
        reflection_panels,
        fallback,
    )
    write_json(manifest_path, manifest)
    print(json.dumps({
        "status": manifest["status"],
        "frames": len(frames),
        "framesDir": manifest["outputs"]["framesDir"],
        "manifest": project_rel(repo_root, manifest_path),
        "fallback": fallback["path"] if fallback else None,
        "maxBallAngleDegrees": manifest["motionEvidence"]["maxBallAngleDegrees"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
