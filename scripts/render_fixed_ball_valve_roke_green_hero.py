#!/usr/bin/env python3
"""Render the fixed-ball-valve hero as opaque green 1920x1080 PNG frames."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import bpy
    from mathutils import Matrix, Vector
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Run with Blender: blender --background --python scripts/render_fixed_ball_valve_roke_green_hero.py -- ...") from exc


EXPECTED_STEP_SHA256 = "3ddb291607730239f5a067e9d1730acda0931874c5f42c4ac0c358516efa2547"
EXPECTED_GLB_SHA256 = "89024869647b3aaf3fe5301694a2753dc87e9dd3d05b41b9c651ef4e9754384b"
HERO_GREEN_SRGB = (0x47 / 255, 0x71 / 255, 0x4D / 255)
HERO_GREEN_HEX = "#47714D"


def srgb_to_linear(value: float) -> float:
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--glb", default="outcome/public/assets/models/fixed-ball-valve.glb")
    parser.add_argument("--step", default="asset/derived/fixed-ball-valve/source/固定式球阀.STEP")
    parser.add_argument("--node-map", default="outcome/src/assets-manifest/fixed-ball-valve-roke-green-node-map.json")
    parser.add_argument("--out-dir", default=".scratch/assets/ztovalve/hero/roke-green-commercial-240")
    parser.add_argument("--manifest", default="outcome/src/assets-manifest/fixed-ball-valve-roke-green-commercial-240.json")
    parser.add_argument("--frame-count", type=int, default=240)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--samples", type=int, default=48)
    parser.add_argument("--frame-list", default="")
    parser.add_argument("--no-clear", action="store_true")
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    return parser.parse_args(argv)


def project_path(repo_root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else repo_root / path


def project_rel(repo_root: Path, path: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def parse_frame_list(value: str, frame_count: int) -> list[int] | None:
    if not value.strip():
        return None
    frames: list[int] = []
    for raw in value.split(","):
        frame = int(raw.strip())
        if frame < 0 or frame >= frame_count:
            raise RuntimeError(f"Frame {frame} is outside 0..{frame_count - 1}.")
        if frame not in frames:
            frames.append(frame)
    return frames


def remove_scene_objects() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for datablock in (bpy.data.meshes, bpy.data.images, bpy.data.lights, bpy.data.cameras):
        for item in list(datablock):
            if item.users == 0:
                datablock.remove(item)


def make_material(
    name: str,
    base_color: tuple[float, float, float, float],
    metallic: float,
    roughness: float,
    specular: float = 0.55,
    coat: float = 0.0,
) -> Any:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = base_color
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        inputs = bsdf.inputs
        if "Base Color" in inputs:
            inputs["Base Color"].default_value = base_color
        if "Metallic" in inputs:
            inputs["Metallic"].default_value = metallic
        if "Roughness" in inputs:
            inputs["Roughness"].default_value = roughness
        for name_candidate in ("Specular IOR Level", "Specular"):
            if name_candidate in inputs:
                inputs[name_candidate].default_value = specular
        for name_candidate in ("Coat Weight", "Clearcoat"):
            if name_candidate in inputs:
                inputs[name_candidate].default_value = coat
        for name_candidate in ("Coat Roughness", "Clearcoat Roughness"):
            if name_candidate in inputs:
                inputs[name_candidate].default_value = 0.28
    return material


def prepare_materials() -> dict[str, Any]:
    return {
        "body": make_material("zt_hero_warm_cast_satin_body", (0.22, 0.23, 0.21, 1), 0.58, 0.64, 0.36, 0.02),
        "machined": make_material("zt_hero_machined_flange_edges", (0.38, 0.39, 0.35, 1), 0.78, 0.42, 0.46, 0.05),
        "ball": make_material("zt_hero_restrained_metal_core", (0.43, 0.41, 0.36, 1), 0.88, 0.30, 0.50, 0.08),
        "seal": make_material("zt_hero_deep_seal_material", (0.035, 0.038, 0.034, 1), 0.03, 0.76, 0.24, 0.0),
        "fastener": make_material("zt_hero_satin_fastener_metal", (0.20, 0.21, 0.20, 1), 0.76, 0.46, 0.38, 0.02),
        "top": make_material("zt_hero_top_stack_satin_metal", (0.28, 0.30, 0.27, 1), 0.72, 0.48, 0.40, 0.03),
        "dark": make_material("zt_hero_dark_inner_shadow_metal", (0.09, 0.095, 0.085, 1), 0.45, 0.62, 0.30, 0.0),
    }


def material_key(record: dict[str, Any]) -> str:
    group = record["animationGroup"]
    product = record["productName"]
    if group == "ball-trunnion-core":
        return "ball" if product == "球体" else "machined"
    if group == "seat-seal-system":
        return "seal" if any(term in product for term in ("密封", "盘根", "垫片")) else "machined"
    if "fasteners" in group or product in {"弹簧", "体盖螺柱", "支架螺柱"}:
        return "fastener"
    if group in {"top-bracket-connector", "stem-packing-stack"}:
        return "top"
    if group == "end-caps-covers":
        return "machined"
    if product in {"阀体", "阀盖"}:
        return "body"
    return "dark"


def configure_render(width: int, height: int, samples: int) -> dict[str, Any]:
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.use_persistent_data = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.compression = 15
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1

    cycles = scene.cycles
    cycles.samples = samples
    cycles.preview_samples = min(samples, 32)
    cycles.use_denoising = True
    cycles.max_bounces = 5
    cycles.diffuse_bounces = 2
    cycles.glossy_bounces = 3
    try:
        cycles.device = "GPU"
        preferences = bpy.context.preferences.addons["cycles"].preferences
        for compute_type in ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL"):
            try:
                preferences.compute_device_type = compute_type
                break
            except Exception:
                continue
        preferences.get_devices()
        for device in preferences.devices:
            device.use = True
    except Exception:
        pass

    world = scene.world or bpy.data.worlds.new("zt_hero_green_world")
    scene.world = world
    hero_green_linear = tuple(srgb_to_linear(value) for value in HERO_GREEN_SRGB)
    world.color = hero_green_linear
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()
    output = nodes.new(type="ShaderNodeOutputWorld")
    light_path = nodes.new(type="ShaderNodeLightPath")
    camera_background = nodes.new(type="ShaderNodeBackground")
    camera_background.inputs["Color"].default_value = (*hero_green_linear, 1)
    camera_background.inputs["Strength"].default_value = 1.0
    lighting_background = nodes.new(type="ShaderNodeBackground")
    lighting_background.inputs["Color"].default_value = (*hero_green_linear, 1)
    lighting_background.inputs["Strength"].default_value = 0.36
    mix = nodes.new(type="ShaderNodeMixShader")
    links.new(light_path.outputs["Is Camera Ray"], mix.inputs[0])
    links.new(lighting_background.outputs["Background"], mix.inputs[1])
    links.new(camera_background.outputs["Background"], mix.inputs[2])
    links.new(mix.outputs["Shader"], output.inputs["Surface"])

    return {
        "renderer": "Blender Cycles",
        "width": width,
        "height": height,
        "samples": samples,
        "filmTransparent": False,
        "pngColorMode": "RGB",
        "background": HERO_GREEN_HEX,
        "backgroundLightingStrength": 0.36,
    }


def world_bounds(objects: list[Any]) -> dict[str, Any]:
    mins = Vector((math.inf, math.inf, math.inf))
    maxs = Vector((-math.inf, -math.inf, -math.inf))
    for obj in objects:
        for corner in obj.bound_box:
            point = obj.matrix_world @ Vector(corner)
            mins.x = min(mins.x, point.x)
            mins.y = min(mins.y, point.y)
            mins.z = min(mins.z, point.z)
            maxs.x = max(maxs.x, point.x)
            maxs.y = max(maxs.y, point.y)
            maxs.z = max(maxs.z, point.z)
    extent = maxs - mins
    center = (mins + maxs) * 0.5
    return {
        "min": [round(v, 6) for v in mins],
        "max": [round(v, 6) for v in maxs],
        "center": [round(v, 6) for v in center],
        "extent": [round(v, 6) for v in extent],
    }


def look_at(obj: Any, target: Vector) -> None:
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def add_lighting(center: Vector, extent: Vector) -> list[dict[str, Any]]:
    lights = [
        ("key", Vector((-1.1, -2.8, 1.8)), 240, 5.2),
        ("rim", Vector((2.2, 1.7, 1.2)), 120, 3.8),
        ("top_softbox", Vector((0.1, -0.4, 3.1)), 150, 6.2),
        ("low_lift", Vector((-0.4, -1.7, -0.7)), 30, 4.2),
    ]
    records: list[dict[str, Any]] = []
    span = max(extent.x, extent.y, extent.z, 0.4)
    for name, offset, energy, size in lights:
        data = bpy.data.lights.new(f"zt_hero_{name}_data", "AREA")
        data.energy = energy
        data.size = size
        obj = bpy.data.objects.new(f"zt_hero_{name}", data)
        bpy.context.scene.collection.objects.link(obj)
        obj.location = center + offset * span
        look_at(obj, center)
        records.append({"name": name, "energy": energy, "size": size, "location": [round(v, 5) for v in obj.location]})
    return records


def smooth_meshes(objects: list[Any]) -> None:
    for obj in objects:
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
        obj.data.update()


def ease_in_out(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


def stage_for(progress: float) -> dict[str, Any]:
    public_frame = round(progress * 239) + 1
    if public_frame <= 30:
        return {"stage": "wide-exploded-layout"}
    if public_frame <= 72:
        return {"stage": "assembly-start"}
    if public_frame <= 120:
        return {"stage": "flange-fastener-lock"}
    if public_frame <= 168:
        return {"stage": "product-push-three-quarter"}
    if public_frame <= 208:
        return {"stage": "wordmark-handoff"}
    return {"stage": "final-stable-hold"}


def state_for(progress: float) -> dict[str, float]:
    if progress < 0.125:
        assembly = 0.0
    elif progress < 0.70:
        assembly = ease_in_out((progress - 0.125) / 0.575)
    else:
        assembly = 1.0
    camera = ease_in_out(max(0, min(1, (progress - 0.36) / 0.42)))
    hold = progress >= 0.875
    return {
        "assembly": 1.0 if hold else assembly,
        "explosion": 0.0 if hold else 1.0 - assembly,
        "cameraProgress": 1.0 if hold else camera,
        "yawDegrees": -5 + 19 * (1.0 if hold else camera),
    }


def group_offset(record: dict[str, Any], center: Vector, state: dict[str, float]) -> Vector:
    explosion = state["explosion"]
    if explosion <= 0:
        return Vector((0, 0, 0))
    bounds_center = Vector(record["bounds"]["center"])
    group = record["animationGroup"]
    side_sign = -1 if bounds_center.x < center.x else 1
    depth_sign = -1 if bounds_center.y < center.y else 1

    if group == "central-body-anchor":
        direction = Vector((0.025 * side_sign, 0.010 * depth_sign, 0.0))
    elif group == "end-caps-covers":
        direction = Vector((1.86 * side_sign, 0.030 * depth_sign, 0.0))
    elif group == "seat-seal-system":
        direction = Vector((1.02 * side_sign, 0.018 * depth_sign, 0.0))
    elif group == "ball-trunnion-core":
        direction = Vector((0, 0, 0.006))
    elif group == "stem-packing-stack":
        direction = Vector((0.20 * side_sign, 0.065 * depth_sign, 0.010))
    elif group == "top-bracket-connector":
        direction = Vector((0.28 * side_sign, 0.075 * depth_sign, 0.012))
    elif group == "top-bracket-fasteners":
        direction = Vector((0.40 * side_sign, 0.080 * depth_sign, 0.014))
    else:
        direction = Vector((1.50 * side_sign, 0.035 * depth_sign, 0.004))
    if group == "fasteners-small-hardware":
        direction += Vector((0.20 * side_sign, 0.018 * depth_sign, 0.006))
    return direction * explosion


def yaw_matrix(degrees: float, center: Vector) -> Matrix:
    return Matrix.Translation(center) @ Matrix.Rotation(math.radians(degrees), 4, "Z") @ Matrix.Translation(-center)


def apply_state(records: list[dict[str, Any]], center: Vector, state: dict[str, float]) -> dict[str, Any]:
    rotation = yaw_matrix(state["yawDegrees"], center)
    moved = 0
    max_offset = 0.0
    for record in records:
        obj = record["object"]
        offset = group_offset(record, center, state)
        obj.matrix_world = Matrix.Translation(offset) @ rotation @ record["baseMatrix"]
        max_offset = max(max_offset, offset.length)
        if offset.length > 0.00001:
            moved += 1
    bpy.context.view_layer.update()
    return {
        "movedObjectCount": moved,
        "maxOffsetMeters": round(max_offset, 6),
        "yawDegrees": round(state["yawDegrees"], 4),
        "assembly": round(state["assembly"], 6),
        "explosion": round(state["explosion"], 6),
    }


def configure_camera(center: Vector, state: dict[str, float]) -> dict[str, Any]:
    scene = bpy.context.scene
    camera_data = scene.camera.data
    camera = scene.camera
    camera_progress = state["cameraProgress"]
    orbit_degrees = math.radians(88 - 10 * camera_progress)
    radius = 2.34 - 0.38 * camera_progress
    height = 0.16 + 0.50 * camera_progress
    camera.location = center + Vector((math.cos(orbit_degrees) * radius, math.sin(orbit_degrees) * radius, height))
    target = center + Vector((0.015 + 0.020 * camera_progress, 0.0, 0.006 - 0.035 * camera_progress))
    look_at(camera, target)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 2.55 - 1.50 * camera_progress
    return {"location": [round(v, 5) for v in camera.location], "target": [round(v, 5) for v in target], "orthoScale": round(camera_data.ortho_scale, 6)}


def import_and_bind(glb_path: Path, node_map: dict[str, Any], materials: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    remove_scene_objects()
    bpy.ops.import_scene.gltf(filepath=str(glb_path))
    mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if len(mesh_objects) != 138:
        raise RuntimeError(f"Expected 138 imported mesh objects, got {len(mesh_objects)}")
    records = sorted(node_map["records"], key=lambda item: item["nodeIndex"])
    bound: list[dict[str, Any]] = []
    for obj, record in zip(mesh_objects, records):
        key = material_key(record)
        obj.data.materials.clear()
        obj.data.materials.append(materials[key])
        obj["zt_node_index"] = int(record["nodeIndex"])
        obj["zt_product_name"] = record["productName"]
        obj["zt_animation_group"] = record["animationGroup"]
        bound.append({**record, "object": obj, "baseMatrix": obj.matrix_world.copy(), "materialKey": key})
    smooth_meshes(mesh_objects)
    return bound, world_bounds(mesh_objects)


def clear_previous_frames(frames_dir: Path) -> None:
    if frames_dir.is_dir():
        for path in frames_dir.glob("*.png"):
            path.unlink()


def render_frames(repo_root: Path, out_dir: Path, records: list[dict[str, Any]], product_bounds: dict[str, Any], frame_count: int, frame_list: list[int] | None) -> list[dict[str, Any]]:
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    center = Vector(product_bounds["center"])
    camera_data = bpy.data.cameras.new("zt_hero_camera_data")
    camera = bpy.data.objects.new("zt_hero_camera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    indices = frame_list if frame_list is not None else list(range(frame_count))
    frames: list[dict[str, Any]] = []
    started = time.perf_counter()
    for ordinal, frame_index in enumerate(indices, start=1):
        progress = frame_index / max(1, frame_count - 1)
        state = state_for(progress)
        motion = apply_state(records, center, state)
        camera_record = configure_camera(center, state)
        output_path = frames_dir / f"{frame_index:04d}.png"
        bpy.context.scene.render.filepath = str(output_path)
        bpy.ops.render.render(write_still=True)
        frames.append(
            {
                "frameIndex": frame_index,
                "publicFrameNumber": frame_index + 1,
                "progress": round(progress, 6),
                **stage_for(progress),
                "path": project_rel(repo_root, output_path),
                "bytes": output_path.stat().st_size,
                "sha256": sha256(output_path),
                "motion": motion,
                "camera": camera_record,
            }
        )
        if ordinal % 12 == 0 or ordinal == len(indices):
            print(f"rendered green hero frame {ordinal}/{len(indices)} in {time.perf_counter() - started:.1f}s")
    return frames


def main() -> int:
    args = parse_args()
    if args.frame_count != 240:
        raise RuntimeError("The homepage contract requires --frame-count 240.")
    if args.width != 1920 or args.height != 1080:
        raise RuntimeError("The ROKE green hero contract requires 1920x1080 frames.")

    repo_root = Path(args.repo_root).resolve()
    step_path = project_path(repo_root, args.step)
    glb_path = project_path(repo_root, args.glb)
    node_map_path = project_path(repo_root, args.node_map)
    out_dir = project_path(repo_root, args.out_dir)
    manifest_path = project_path(repo_root, args.manifest)
    frame_list = parse_frame_list(args.frame_list, args.frame_count)
    frames_dir = out_dir / "frames"

    if sha256(step_path) != EXPECTED_STEP_SHA256:
        raise RuntimeError("Fixed ball valve STEP hash drifted")
    if sha256(glb_path) != EXPECTED_GLB_SHA256:
        raise RuntimeError("Fixed ball valve GLB hash drifted")
    node_map = read_json(node_map_path)
    if node_map.get("schema") != "ztovalve-fixed-ball-valve-roke-green-node-map/v1":
        raise RuntimeError("Unexpected node map schema")

    if not args.no_clear:
        clear_previous_frames(frames_dir)
    materials = prepare_materials()
    render_profile = configure_render(args.width, args.height, args.samples)
    records, product_bounds = import_and_bind(glb_path, node_map, materials)
    center = Vector(product_bounds["center"])
    extent = Vector(product_bounds["extent"])
    lighting = add_lighting(center, extent)
    frames = render_frames(repo_root, out_dir, records, product_bounds, args.frame_count, frame_list)
    all_rendered = frame_list is None and len(frames) == args.frame_count

    manifest = {
        "schema": "ztovalve-fixed-ball-valve-roke-green-commercial-240/v1",
        "kind": "opaque_green_png_staging",
        "bundleId": "roke-green-commercial-240",
        "status": "rendered-full-sequence" if all_rendered else "rendered-sample",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "step": {"path": project_rel(repo_root, step_path), "sha256": EXPECTED_STEP_SHA256},
            "glb": {"path": project_rel(repo_root, glb_path), "sha256": EXPECTED_GLB_SHA256},
            "nodeMap": {"path": project_rel(repo_root, node_map_path), "sha256": sha256(node_map_path)},
        },
        "scope": {
            "product": "ztovalve fixed ball valve",
            "background": HERO_GREEN_HEX,
            "containsBackgroundText": False,
            "containsCameraVisibleBackdrop": True,
            "quarterTurnFunctionClaim": False,
            "homepageConnected": all_rendered,
        },
        "renderProfile": {
            **render_profile,
            "frameCount": args.frame_count,
            "renderedFrameCount": len(frames),
            "renderedFrameList": frame_list,
            "stagingFrameNames": "0000.png..0239.png",
            "publicAvifNames": "0001.avif..0240.avif",
        },
        "lookdev": {
            "body": "warm grey cast/satin stainless",
            "machinedEdges": "slightly brighter satin highlights",
            "fasteners": "dark satin metal",
            "seals": "restrained deep material",
            "ballCore": "metal core moves with assembly group only, no verified 90-degree function motion",
        },
        "productBounds": product_bounds,
        "lighting": lighting,
        "outputs": {
            "stagingDir": project_rel(repo_root, out_dir),
            "framesDir": project_rel(repo_root, frames_dir),
            "manifest": project_rel(repo_root, manifest_path),
            "publicAvifDir": "outcome/public/assets/upload/images/zt-hero-fixed-ball-valve",
            "fallback": "outcome/public/assets/hero/fixed-ball-valve-mobile-fallback.png",
        },
        "frames": frames,
    }
    write_json(manifest_path, manifest)
    print(json.dumps({"status": manifest["status"], "frames": len(frames), "manifest": project_rel(repo_root, manifest_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
