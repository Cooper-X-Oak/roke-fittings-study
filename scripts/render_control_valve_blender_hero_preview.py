#!/usr/bin/env python3
"""Render a Blender-offline proof clip from the approved control-valve scheduler.

This is a bridge proof, not the final full-quality 330-frame render. It keeps
the existing online Three.js scheduler as the authority for frame states, but
uses Blender/Cycles to produce the media frames consumed by the web hero.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    import bpy
    from mathutils import Matrix, Vector
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Run this script with Blender's Python interpreter.") from exc


GOAL25D_MANIFEST = "docs/assets/ztovalve/hero/goal25d-zoned-body-material-proof/render-manifest.json"
MODEL_PATH = "docs/control-valve/assets/control-valve-shot-ready.glb"
CAMERA_PREVIS = "creative/control-valve/camera-previs.json"
PREVIEW_DIR = "docs/control-valve-blender-hero-preview"
CREATIVE_DIR = "creative/control-valve-blender-hero-preview"
HDRI_PATH = "docs/assets/ztovalve/hero/goal20-blender-cycles-step-proof/studio_small_09_1k.hdr"

GROUP_NAMES = [
    "VALVE_BODY_BONNET",
    "PNEUMATIC_ACTUATOR",
    "STEM_CASCADE_PLUG",
    "CASCADE_TRIM",
    "SEALS_SUPPORT",
    "PRODUCTION_DETAILS",
]

TRIM_SEPARATION_WORLD = [-1.35, -0.45, 0.45, 1.35]
BODY_OPEN_OFFSET_WORLD = 0.92
ACTUATOR_OPEN_OFFSET_WORLD = -1.75
ACTUATOR_SEAT_OFFSET_WORLD = 0.16
SUPPORT_OPEN_OFFSET_WORLD = -0.9
DETAILS_OPEN_OFFSET_WORLD = 0.64
STEM_OPEN_OFFSET_WORLD = 0.72

MATERIALS = {
    "VALVE_BODY_BONNET": {
        "label": "clean cast/blasted valve body and machined flange treatment",
        "base_color": (0.52, 0.55, 0.51, 1.0),
        "metallic": 1.0,
        "roughness": 0.37,
        "anisotropic": 0.34,
        "coat": 0.035,
    },
    "PNEUMATIC_ACTUATOR": {
        "label": "slightly darker clean satin actuator metal",
        "base_color": (0.42, 0.46, 0.44, 1.0),
        "metallic": 0.92,
        "roughness": 0.43,
        "anisotropic": 0.22,
        "coat": 0.020,
    },
    "STEM_CASCADE_PLUG": {
        "label": "bright clean machined internal stem and plug",
        "base_color": (0.70, 0.73, 0.70, 1.0),
        "metallic": 1.0,
        "roughness": 0.21,
        "anisotropic": 0.46,
        "coat": 0.055,
    },
    "CASCADE_TRIM": {
        "label": "clean precision cascade trim with higher specular bite",
        "base_color": (0.76, 0.80, 0.78, 1.0),
        "metallic": 1.0,
        "roughness": 0.18,
        "anisotropic": 0.50,
        "coat": 0.060,
    },
    "SEALS_SUPPORT": {
        "label": "dark clean support metal and non-highlight details",
        "base_color": (0.34, 0.38, 0.37, 1.0),
        "metallic": 0.65,
        "roughness": 0.48,
        "anisotropic": 0.16,
        "coat": 0.010,
    },
    "PRODUCTION_DETAILS": {
        "label": "clean bolt and production detail metal",
        "base_color": (0.58, 0.62, 0.59, 1.0),
        "metallic": 1.0,
        "roughness": 0.30,
        "anisotropic": 0.36,
        "coat": 0.045,
    },
}


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    args = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--model", default=MODEL_PATH)
    parser.add_argument("--camera-previs", default=CAMERA_PREVIS)
    parser.add_argument("--material-manifest", default=GOAL25D_MANIFEST)
    parser.add_argument("--hdri", default=HDRI_PATH)
    parser.add_argument("--frame-dir", default=f"{PREVIEW_DIR}/assets/frames")
    parser.add_argument("--poster", default=f"{PREVIEW_DIR}/assets/first-frame.png")
    parser.add_argument("--out", default=f"{CREATIVE_DIR}/render-manifest.json")
    parser.add_argument("--profile", choices=["smoke", "proof"], default="smoke")
    parser.add_argument("--sample-count", type=int, default=18)
    parser.add_argument("--frame-list", default="")
    parser.add_argument("--delivery-fps", type=float, default=6.0)
    return parser.parse_args(args)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def set_input(node, names: list[str], value) -> None:
    for name in names:
        if name in node.inputs:
            node.inputs[name].default_value = value
            return


def configure_render(profile: str) -> dict:
    profiles = {
        "smoke": {"width": 960, "height": 600, "samples": 20},
        "proof": {"width": 1280, "height": 800, "samples": 64},
    }
    selected = profiles[profile]
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = selected["samples"]
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 8
    scene.cycles.diffuse_bounces = 2
    scene.cycles.glossy_bounces = 5
    scene.render.resolution_x = selected["width"]
    scene.render.resolution_y = selected["height"]
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    try:
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "Medium High Contrast"
    except TypeError:
        pass
    scene.view_settings.exposure = -0.45
    scene.view_settings.gamma = 1.0
    try:
        scene.cycles.device = "GPU"
    except Exception:
        scene.cycles.device = "CPU"
    return selected


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for data_block in (
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.images,
        bpy.data.lights,
        bpy.data.cameras,
    ):
        for item in list(data_block):
            if item.users == 0:
                data_block.remove(item)


def make_material(name: str, spec: dict, alpha: float = 1.0) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = (*spec["base_color"][:3], alpha)
    material.blend_method = "BLEND"
    material.use_screen_refraction = False
    nodes = material.node_tree.nodes
    principled = nodes.get("Principled BSDF")
    if principled:
        set_input(principled, ["Base Color"], spec["base_color"])
        set_input(principled, ["Alpha"], alpha)
        set_input(principled, ["Metallic"], spec.get("metallic", 1.0))
        set_input(principled, ["Roughness"], spec.get("roughness", 0.35))
        set_input(principled, ["Coat Weight", "Clearcoat"], spec.get("coat", 0.0))
        set_input(principled, ["Coat Roughness", "Clearcoat Roughness"], 0.16)
        set_input(principled, ["Anisotropic IOR Level", "Anisotropic"], spec.get("anisotropic", 0.0))
    return material


def set_material_alpha(material: bpy.types.Material, alpha: float) -> None:
    material.diffuse_color = (material.diffuse_color[0], material.diffuse_color[1], material.diffuse_color[2], alpha)
    material.blend_method = "BLEND" if alpha < 0.995 else "OPAQUE"
    principled = material.node_tree.nodes.get("Principled BSDF") if material.use_nodes else None
    if principled and "Alpha" in principled.inputs:
        principled.inputs["Alpha"].default_value = alpha


def world_bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
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
    return mins, maxs


def bake_world_transforms(objects: list[bpy.types.Object]) -> None:
    for obj in objects:
        world = obj.matrix_world.copy()
        obj.parent = None
        obj.data.transform(world)
        obj.matrix_world = Matrix.Identity(4)
        obj.data.update()


def transform_meshes(objects: list[bpy.types.Object], matrix: Matrix) -> None:
    for obj in objects:
        obj.data.transform(matrix)
        obj.data.update()


def canonicalize_meshes(objects: list[bpy.types.Object]) -> dict:
    bake_world_transforms(objects)
    mins, maxs = world_bounds(objects)
    size = maxs - mins
    rotation = Matrix.Identity(4)
    if size.x > size.z and size.x > size.y:
        rotation = Matrix.Rotation(math.radians(90), 4, "Y")
    elif size.y > size.z and size.y > size.x:
        rotation = Matrix.Rotation(math.radians(-90), 4, "X")
    transform_meshes(objects, rotation)

    mins, maxs = world_bounds(objects)
    center = (mins + maxs) * 0.5
    size = maxs - mins
    scale = 3.4 / max(0.001, size.z)
    canonical = Matrix.Scale(scale, 4) @ Matrix.Translation(-center)
    transform_meshes(objects, canonical)
    mins, maxs = world_bounds(objects)
    return {
        "localBounds": {
            "min": [round(value, 6) for value in mins],
            "max": [round(value, 6) for value in maxs],
            "size": [round(value, 6) for value in (maxs - mins)],
        },
        "scaleToHeroWorld": scale,
    }


def connected_face_components(mesh: bpy.types.Mesh) -> list[list[int]]:
    vertex_to_faces: dict[int, list[int]] = defaultdict(list)
    for polygon in mesh.polygons:
        for vertex in polygon.vertices:
            vertex_to_faces[vertex].append(polygon.index)

    seen: set[int] = set()
    components: list[list[int]] = []
    for polygon in mesh.polygons:
        if polygon.index in seen:
            continue
        stack = [polygon.index]
        seen.add(polygon.index)
        component = []
        while stack:
            current = stack.pop()
            component.append(current)
            for vertex in mesh.polygons[current].vertices:
                for neighbor in vertex_to_faces[vertex]:
                    if neighbor not in seen:
                        seen.add(neighbor)
                        stack.append(neighbor)
        if len(component) >= 8:
            components.append(component)
    return components


def make_component_object(source: bpy.types.Object, component: list[int], index: int, material: bpy.types.Material) -> bpy.types.Object:
    mesh = source.data
    vertex_map: dict[int, int] = {}
    vertices: list[tuple[float, float, float]] = []
    faces: list[list[int]] = []
    for polygon_index in component:
        polygon = mesh.polygons[polygon_index]
        face = []
        for old_index in polygon.vertices:
            if old_index not in vertex_map:
                vertex_map[old_index] = len(vertices)
                vertices.append(tuple(mesh.vertices[old_index].co))
            face.append(vertex_map[old_index])
        faces.append(face)
    new_mesh = bpy.data.meshes.new(f"CASCADE_GEOMETRY_ISLAND_{index:02d}_mesh")
    new_mesh.from_pydata(vertices, [], faces)
    new_mesh.update()
    obj = bpy.data.objects.new(f"CASCADE_GEOMETRY_ISLAND_{index}", new_mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    bevel = obj.modifiers.new(f"trim_island_{index}_micro_bevel", "BEVEL")
    bevel.width = 0.006
    bevel.segments = 2
    obj.modifiers.new(f"trim_island_{index}_weighted_normals", "WEIGHTED_NORMAL")
    return obj


def assign_materials(groups: dict[str, bpy.types.Object]) -> dict[str, list[bpy.types.Material]]:
    assigned = {}
    for name, obj in groups.items():
        spec = MATERIALS.get(name, MATERIALS["PRODUCTION_DETAILS"])
        material = make_material(f"blender_hero_{name}", spec)
        obj.data.materials.clear()
        obj.data.materials.append(material)
        bevel = obj.modifiers.new(f"{name.lower()}_clean_bevel_highlight", "BEVEL")
        bevel.width = 0.0035 if name != "CASCADE_TRIM" else 0.002
        bevel.segments = 2
        obj.modifiers.new(f"{name.lower()}_weighted_normals", "WEIGHTED_NORMAL")
        assigned[name] = [material]
    return assigned


def split_trim(groups: dict[str, bpy.types.Object], product_rig: bpy.types.Object) -> list[dict]:
    source = groups["CASCADE_TRIM"]
    components = connected_face_components(source.data)
    records = []
    if len(components) < 4:
        source.parent = product_rig
        return [{"name": source.name, "object": source, "axisOrder": 1, "triangleCount": len(source.data.polygons)}]

    centers = []
    for component in components:
        coords = []
        for polygon_index in component:
            for vertex_index in source.data.polygons[polygon_index].vertices:
                coords.append(source.data.vertices[vertex_index].co.copy())
        center = sum(coords, Vector()) / max(1, len(coords))
        centers.append(center)
    ordered = sorted(zip(components, centers), key=lambda item: item[1].z)
    selected = ordered[:4]
    selected.sort(key=lambda item: item[1].z)
    source.hide_render = True
    source.hide_viewport = True
    source.parent = product_rig

    for index, (component, center) in enumerate(selected, start=1):
        material = make_material(f"blender_hero_CASCADE_TRIM_island_{index}", MATERIALS["CASCADE_TRIM"])
        obj = make_component_object(source, component, index, material)
        obj.parent = product_rig
        records.append(
            {
                "name": obj.name,
                "object": obj,
                "axisOrder": index,
                "triangleCount": len(component),
                "localCenter": [round(value, 6) for value in center],
            }
        )
    return records


def map_three_vector(value: list[float]) -> Vector:
    return Vector((value[0], -value[2], value[1]))


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def build_lighting(hdri_path: Path | None) -> None:
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
            background.inputs["Strength"].default_value = 0.18
    else:
        world.color = (0.18, 0.19, 0.18)

    def add_area(name: str, location, target, power: float, size: float) -> None:
        light = bpy.data.lights.new(name, type="AREA")
        obj = bpy.data.objects.new(name, light)
        bpy.context.collection.objects.link(obj)
        obj.location = Vector(location)
        look_at(obj, Vector(target))
        light.energy = power
        light.size = size

    add_area("blender_hero_key_softbox", (-3.8, -4.2, 4.6), (0, 0, 0.6), 430, 4.2)
    add_area("blender_hero_rim_softbox", (4.5, 3.6, 3.1), (0, 0, 0.4), 190, 2.6)
    add_area("blender_hero_top_strip", (0.0, -1.2, 5.0), (0, 0, 0.8), 180, 3.1)


def apply_state(
    state: dict,
    camera: bpy.types.Object,
    product_rig: bpy.types.Object,
    groups: dict[str, bpy.types.Object],
    group_materials: dict[str, list[bpy.types.Material]],
    trim_islands: list[dict],
) -> None:
    product = state["product"]
    product_rig.rotation_euler = (0.0, 0.0, math.radians(product["productYawDegrees"]))

    for obj in groups.values():
        obj.location = (0, 0, 0)
    for island in trim_islands:
        island["object"].location = (0, 0, 0)

    groups["VALVE_BODY_BONNET"].location.z = -BODY_OPEN_OFFSET_WORLD * (1 - product["bodyClosure"])
    groups["PNEUMATIC_ACTUATOR"].location.z = -(
        ACTUATOR_OPEN_OFFSET_WORLD * (1 - product["actuatorAssembly"])
        + ACTUATOR_SEAT_OFFSET_WORLD * product["actuatorAssembly"]
    )
    groups["SEALS_SUPPORT"].location.z = -SUPPORT_OPEN_OFFSET_WORLD * (1 - product["detailAssembly"])
    groups["PRODUCTION_DETAILS"].location.z = -DETAILS_OPEN_OFFSET_WORLD * (1 - product["detailAssembly"])
    groups["STEM_CASCADE_PLUG"].location.z = -STEM_OPEN_OFFSET_WORLD * (1 - product["stemAssembly"])

    for index, island in enumerate(trim_islands):
        island["object"].location.z = TRIM_SEPARATION_WORLD[min(index, 3)] * (1 - product["trimAssembly"][min(index, 3)])

    alpha_by_group = {
        "VALVE_BODY_BONNET": product["bodyOpacity"],
        "PNEUMATIC_ACTUATOR": 0.35 + 0.65 * product["actuatorAssembly"],
        "SEALS_SUPPORT": 0.28 + 0.72 * product["detailAssembly"],
        "PRODUCTION_DETAILS": 0.2 + 0.8 * product["detailAssembly"],
        "STEM_CASCADE_PLUG": 1.0,
        "CASCADE_TRIM": 1.0,
    }
    for name, materials in group_materials.items():
        for material in materials:
            set_material_alpha(material, alpha_by_group.get(name, 1.0))
    for island in trim_islands:
        for material in island["object"].data.materials:
            set_material_alpha(material, 1.0)

    camera.location = map_three_vector(state["camera"]["position"])
    target = map_three_vector(state["camera"]["target"])
    camera.data.lens_unit = "FOV"
    camera.data.angle = math.radians(state["camera"]["fovDegrees"])
    look_at(camera, target)


def resolve_sample_frames(camera_previs: dict, args: argparse.Namespace) -> list[int]:
    total = camera_previs["totalFrames"]
    if args.frame_list.strip():
        frames = [int(value.strip()) for value in args.frame_list.split(",") if value.strip()]
    else:
        count = max(2, args.sample_count)
        frames = [round(index * (total - 1) / (count - 1)) for index in range(count)]
    return sorted(set(max(0, min(total - 1, frame)) for frame in frames))


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    model_path = (repo_root / args.model).resolve()
    camera_previs_path = (repo_root / args.camera_previs).resolve()
    material_manifest_path = (repo_root / args.material_manifest).resolve()
    hdri_path = (repo_root / args.hdri).resolve()
    frame_dir = (repo_root / args.frame_dir).resolve()
    poster_path = (repo_root / args.poster).resolve()
    manifest_path = (repo_root / args.out).resolve()

    camera_previs = json.loads(camera_previs_path.read_text(encoding="utf-8"))
    material_manifest = json.loads(material_manifest_path.read_text(encoding="utf-8"))
    source_frames = resolve_sample_frames(camera_previs, args)

    clear_scene()
    render_profile = configure_render(args.profile)
    build_lighting(hdri_path)
    bpy.ops.import_scene.gltf(filepath=str(model_path))
    imported_meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not imported_meshes:
        raise RuntimeError(f"No mesh objects imported from {model_path}")

    fit_report = canonicalize_meshes(imported_meshes)
    groups = {}
    for name in GROUP_NAMES:
        obj = bpy.data.objects.get(name)
        if obj is None or obj.type != "MESH":
            raise RuntimeError(f"GLB is missing semantic mesh object: {name}")
        groups[name] = obj

    group_materials = assign_materials(groups)
    product_rig = bpy.data.objects.new("BLENDER_OFFLINE_PRODUCT_RIG", None)
    bpy.context.collection.objects.link(product_rig)
    for obj in groups.values():
        obj.parent = product_rig
    trim_islands = split_trim(groups, product_rig)

    camera_data = bpy.data.cameras.new("blender_offline_hero_camera")
    camera = bpy.data.objects.new("blender_offline_hero_camera", camera_data)
    bpy.context.collection.objects.link(camera)
    bpy.context.scene.camera = camera

    frame_dir.mkdir(parents=True, exist_ok=True)
    for path in frame_dir.glob("frame*.png"):
        path.unlink()

    frame_records = []
    for output_index, source_frame in enumerate(source_frames):
        state = camera_previs["frames"][source_frame]
        apply_state(state, camera, product_rig, groups, group_materials, trim_islands)
        bpy.context.view_layer.update()
        output_path = frame_dir / f"frame{output_index:04d}.png"
        bpy.context.scene.render.filepath = str(output_path)
        bpy.ops.render.render(write_still=True)
        frame_records.append(
            {
                "frame": output_index,
                "sourceFrame": source_frame,
                "sourceProgress": round(source_frame / (camera_previs["totalFrames"] - 1), 6),
                "shotId": state["shotId"],
                "path": str(output_path.relative_to(repo_root)).replace("\\", "/"),
                "bytes": output_path.stat().st_size,
                "sha256": sha256(output_path),
            }
        )
        print(f"rendered Blender preview frame {output_index + 1}/{len(source_frames)} from source frame {source_frame}")

    poster_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(frame_dir / "frame0000.png", poster_path)

    manifest = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "purpose": "Blender-offline-to-web-hero technical bridge proof",
        "boundary": {
            "onlineSchedulerRole": "Three.js/WebGL remains a fast animation and camera scheduling validator.",
            "offlineRendererRole": "Blender/Cycles is the image-production source for deliverable hero media.",
            "deliveryRole": "The web hero consumes Blender-rendered H.264 video and poster assets.",
            "notFinalFullRender": True,
        },
        "sourceScheduler": str(camera_previs_path.relative_to(repo_root)).replace("\\", "/"),
        "sourceSchedulerSha256": sha256(camera_previs_path),
        "sourceModel": str(model_path.relative_to(repo_root)).replace("\\", "/"),
        "sourceModelSha256": sha256(model_path),
        "sourceMaterialManifest": str(material_manifest_path.relative_to(repo_root)).replace("\\", "/"),
        "sourceMaterialManifestSha256": sha256(material_manifest_path),
        "sourceMaterialMainStill": material_manifest.get("mainStillId"),
        "sourceMaterialExplicitScratchCurves": material_manifest.get("renderProfile", {}).get("mainStillExplicitScratchCurves"),
        "renderer": {
            "engine": "Blender Cycles",
            "blender": bpy.app.version_string,
            "profile": args.profile,
            **render_profile,
            "captureSurface": "Blender offline PNG frames",
            "uiFree": True,
        },
        "deliveryPreview": {
            "route": "docs/control-valve-blender-hero-preview/index.html",
            "frameDirectory": str(frame_dir.relative_to(repo_root)).replace("\\", "/"),
            "posterPath": str(poster_path.relative_to(repo_root)).replace("\\", "/"),
            "deliveryFps": args.delivery_fps,
            "sampledSourceFrames": source_frames,
            "sourceTotalFrames": camera_previs["totalFrames"],
            "sourceFps": camera_previs["fps"],
        },
        "assetMapping": {
            "semanticGroups": GROUP_NAMES,
            "trimIslandCount": len(trim_islands),
            "trimDiagnostics": [
                {key: value for key, value in island.items() if key != "object"}
                for island in trim_islands
            ],
            "fit": fit_report,
        },
        "materialTreatment": {
            key: {sub_key: value for sub_key, value in spec.items() if sub_key != "base_color"}
            for key, spec in MATERIALS.items()
        },
        "frames": frame_records,
    }
    write_json(manifest_path, manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
