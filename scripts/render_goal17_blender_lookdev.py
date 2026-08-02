#!/usr/bin/env python3
"""Build and render the Goal 17 Blender Cycles lookdev scene.

Run inside Blender:
blender --background --python scripts/render_goal17_blender_lookdev.py -- --repo-root . --profile preview
"""

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

try:
    import bpy
    from mathutils import Vector
except ImportError as exc:  # pragma: no cover - normal Python cannot provide bpy.
    raise SystemExit(
        "This script must be run by Blender's Python interpreter, not system Python."
    ) from exc


STATES = {
    "assembled": {
        "shellSplit": 0.0,
        "seatSpread": 0.0,
        "stemLift": 0.0,
        "lowerDrop": 0.0,
        "fastenerSpread": 0.0,
        "ballTurn": 0.0,
    },
    "exploded": {
        "shellSplit": 1.08,
        "seatSpread": 1.0,
        "stemLift": 0.92,
        "lowerDrop": 0.78,
        "fastenerSpread": 0.76,
        "ballTurn": 0.0,
    },
    "ball-open": {
        "shellSplit": 0.34,
        "seatSpread": 0.52,
        "stemLift": 0.28,
        "lowerDrop": 0.22,
        "fastenerSpread": 0.18,
        "ballTurn": 1.0,
    },
}


CAMERA_SETUPS = [
    {
        "id": "assembled-photoreal",
        "stateId": "assembled",
        "filename": "01-assembled-photoreal.png",
        "camera": (0.78, -1.26, 0.52),
        "target": (0.0, 0.0, 0.03),
        "lensMm": 70,
    },
    {
        "id": "exploded-photoreal",
        "stateId": "exploded",
        "filename": "02-exploded-photoreal.png",
        "camera": (1.02, -1.68, 0.62),
        "target": (0.05, 0.0, 0.04),
        "lensMm": 72,
    },
    {
        "id": "ball-seat-photoreal",
        "stateId": "ball-open",
        "filename": "03-ball-seat-photoreal.png",
        "camera": (0.68, -1.02, 0.42),
        "target": (0.0, 0.0, 0.03),
        "lensMm": 82,
    },
]


MATERIALS = {
    "satin-cast-pressure-shell": {
        "base_color": (0.714, 0.722, 0.706, 1.0),
        "metallic": 1.0,
        "roughness": 0.34,
        "anisotropic": 0.28,
        "clearcoat": 0.08,
        "bump": 0.025,
        "noise_scale": 85,
    },
    "machined-flange-cut-stainless": {
        "base_color": (0.831, 0.843, 0.827, 1.0),
        "metallic": 1.0,
        "roughness": 0.18,
        "anisotropic": 0.72,
        "clearcoat": 0.18,
        "bump": 0.012,
        "noise_scale": 130,
    },
    "polished-ball-core": {
        "base_color": (0.91, 0.925, 0.914, 1.0),
        "metallic": 1.0,
        "roughness": 0.07,
        "anisotropic": 0.12,
        "clearcoat": 0.38,
        "bump": 0.006,
        "noise_scale": 180,
    },
    "darkened-fastener-steel": {
        "base_color": (0.018, 0.021, 0.024, 1.0),
        "metallic": 1.0,
        "roughness": 0.31,
        "anisotropic": 0.22,
        "clearcoat": 0.05,
        "bump": 0.018,
        "noise_scale": 95,
    },
    "light-soft-seat-and-ptfe": {
        "base_color": (0.73, 0.69, 0.60, 1.0),
        "metallic": 0.0,
        "roughness": 0.48,
        "anisotropic": 0.0,
        "clearcoat": 0.03,
        "bump": 0.01,
        "noise_scale": 70,
    },
    "graphite-packing-dark-cavity": {
        "base_color": (0.006, 0.007, 0.008, 1.0),
        "metallic": 0.2,
        "roughness": 0.62,
        "anisotropic": 0.0,
        "clearcoat": 0.0,
        "bump": 0.035,
        "noise_scale": 55,
    },
    "machined-drive-stack": {
        "base_color": (0.776, 0.792, 0.780, 1.0),
        "metallic": 1.0,
        "roughness": 0.22,
        "anisotropic": 0.58,
        "clearcoat": 0.14,
        "bump": 0.014,
        "noise_scale": 115,
    },
    "matte-white-studio": {
        "base_color": (0.94, 0.94, 0.92, 1.0),
        "metallic": 0.0,
        "roughness": 0.72,
        "anisotropic": 0.0,
        "clearcoat": 0.0,
        "bump": 0.0,
        "noise_scale": 1,
    },
    "black-reflection-card": {
        "base_color": (0.0, 0.0, 0.0, 1.0),
        "metallic": 0.0,
        "roughness": 0.55,
        "anisotropic": 0.0,
        "clearcoat": 0.0,
        "bump": 0.0,
        "noise_scale": 1,
    },
}


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    args = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--model", default="docs/assets/ztovalve/hero/fixed-ball-valve.glb")
    parser.add_argument(
        "--out-dir",
        default="docs/assets/ztovalve/hero/goal17-offline-lookdev/renders",
    )
    parser.add_argument("--profile", choices=["preview", "final"], default="preview")
    return parser.parse_args(args)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def set_input(node, names, value) -> None:
    for name in names:
        if name in node.inputs:
            node.inputs[name].default_value = value
            return


def make_material(name: str, spec: dict) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    principled = nodes.get("Principled BSDF")
    if not principled:
        return material

    set_input(principled, ["Base Color"], spec["base_color"])
    set_input(principled, ["Metallic"], spec["metallic"])
    set_input(principled, ["Roughness"], spec["roughness"])
    set_input(principled, ["Alpha"], spec.get("alpha", 1.0))
    set_input(principled, ["Coat Weight", "Clearcoat"], spec.get("clearcoat", 0.0))
    set_input(principled, ["Coat Roughness", "Clearcoat Roughness"], 0.18)
    set_input(principled, ["Anisotropic IOR Level", "Anisotropic"], spec.get("anisotropic", 0.0))

    bump_strength = spec.get("bump", 0.0)
    if bump_strength:
        noise = nodes.new(type="ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = spec.get("noise_scale", 80)
        noise.inputs["Detail"].default_value = 14
        noise.inputs["Roughness"].default_value = 0.58
        bump = nodes.new(type="ShaderNodeBump")
        bump.inputs["Strength"].default_value = bump_strength
        bump.inputs["Distance"].default_value = 0.018
        material.node_tree.links.new(noise.outputs["Fac"], bump.inputs["Height"])
        if "Normal" in principled.inputs:
            material.node_tree.links.new(bump.outputs["Normal"], principled.inputs["Normal"])

    material.diffuse_color = spec["base_color"]
    return material


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def configure_render(profile: str) -> None:
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 96 if profile == "preview" else 384
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 3840
    scene.render.resolution_y = 2160
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    try:
        scene.view_settings.view_transform = "AgX"
    except TypeError:
        try:
            scene.view_settings.view_transform = "Filmic"
        except TypeError:
            pass
    try:
        scene.view_settings.look = "Medium High Contrast"
    except TypeError:
        try:
            scene.view_settings.look = "None"
        except TypeError:
            pass
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    try:
        scene.cycles.device = "GPU"
    except Exception:
        pass


def import_model(model_path: Path) -> list:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(model_path))
    imported = [obj for obj in bpy.data.objects if obj not in before]
    return [obj for obj in imported if obj.type == "MESH"]


def object_bounds(obj: bpy.types.Object):
    world = obj.matrix_world
    corners = [world @ Vector(corner) for corner in obj.bound_box]
    min_v = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    max_v = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    return min_v, max_v, (min_v + max_v) * 0.5, max_v - min_v


def scene_bounds(meshes: list):
    mins = []
    maxs = []
    for obj in meshes:
        min_v, max_v, _center, _size = object_bounds(obj)
        mins.append(min_v)
        maxs.append(max_v)
    min_all = Vector((min(v.x for v in mins), min(v.y for v in mins), min(v.z for v in mins)))
    max_all = Vector((max(v.x for v in maxs), max(v.y for v in maxs), max(v.z for v in maxs)))
    return min_all, max_all, (min_all + max_all) * 0.5, max_all - min_all


def create_rig(meshes: list):
    rig = bpy.data.objects.new("goal17_product_rig", None)
    bpy.context.collection.objects.link(rig)
    _min_v, _max_v, center, _size = scene_bounds(meshes)
    for obj in meshes:
        obj.parent = rig
        obj.matrix_parent_inverse = rig.matrix_world.inverted()
    rig.location = -center
    rig.rotation_euler[2] = math.radians(-9)
    bpy.context.view_layer.update()
    return rig


def classify(obj: bpy.types.Object, all_center: Vector, all_size: Vector):
    min_v, max_v, center, size = object_bounds(obj)
    diagonal = size.length
    max_extent = max(size.x, size.y, size.z)
    min_extent = min(size.x, size.y, size.z)
    extent_ratio = min_extent / max_extent if max_extent else 0
    name = obj.name.lower()

    near_core_x = abs(center.x - all_center.x) < all_size.x * 0.28
    near_core_y = abs(center.y - all_center.y) < all_size.y * 0.55
    z_delta = center.z - all_center.z
    sphere_like = extent_ratio > 0.66
    thin_axial_seat = (
        near_core_x
        and near_core_y
        and 0.07 < diagonal < 0.34
        and extent_ratio < 0.24
        and min(size.x, size.y, size.z) < max(size.x, size.y, size.z) * 0.24
    )
    true_ball_core = (
        near_core_x
        and near_core_y
        and sphere_like
        and 0.24 < diagonal < 0.38
        and z_delta > -all_size.z * 0.24
        and z_delta < all_size.z * 0.16
    )

    fastener_tokens = ["bolt", "nut", "washer", "screw", "stud", "pin", "fastener"]
    dark_tokens = ["packing", "gasket", "graphite"]

    if true_ball_core:
        return "ball", "polished-ball-core"
    if any(token in name for token in fastener_tokens) or diagonal < 0.04:
        return "fastener", "darkened-fastener-steel"
    if any(token in name for token in dark_tokens):
        return "seat", "graphite-packing-dark-cavity"
    if thin_axial_seat or (near_core_x and diagonal < 0.13):
        return "seat", "light-soft-seat-and-ptfe"
    if near_core_x and z_delta > all_size.z * 0.16 and diagonal < 0.34:
        return "upperDrive", "machined-drive-stack"
    if near_core_x and z_delta < -all_size.z * 0.2 and diagonal < 0.22:
        return "lowerSupport", "machined-drive-stack"
    if center.x < all_center.x - all_size.x * 0.13:
        return "leftBody", "machined-flange-cut-stainless"
    if center.x > all_center.x + all_size.x * 0.13:
        return "rightBody", "satin-cast-pressure-shell"
    return "centerBody", "satin-cast-pressure-shell"


def add_modifiers(obj: bpy.types.Object, group_id: str) -> None:
    width = 0.00075 if group_id == "fastener" else 0.0015
    bevel = obj.modifiers.new("goal17_micro_bevel", "BEVEL")
    bevel.width = width
    bevel.segments = 2
    bevel.affect = "EDGES"
    weighted = obj.modifiers.new("goal17_weighted_normals", "WEIGHTED_NORMAL")
    weighted.keep_sharp = True


def assign_materials(meshes: list, materials: dict):
    _min_v, _max_v, all_center, all_size = scene_bounds(meshes)
    records = []
    counts = {}
    material_counts = {}
    for obj in meshes:
        group_id, material_id = classify(obj, all_center, all_size)
        obj.data.materials.clear()
        obj.data.materials.append(materials[material_id])
        add_modifiers(obj, group_id)
        _min_v, _max_v, center, _size = object_bounds(obj)
        records.append(
            {
                "object": obj,
                "group": group_id,
                "material": material_id,
                "base_location": obj.location.copy(),
                "base_rotation": obj.rotation_euler.copy(),
                "local_center": center - all_center,
            }
        )
        counts[group_id] = counts.get(group_id, 0) + 1
        material_counts[material_id] = material_counts.get(material_id, 0) + 1
    return records, counts, material_counts


def apply_state(records: list, state_id: str) -> None:
    state = STATES[state_id]
    for record in records:
        obj = record["object"]
        group = record["group"]
        local_center = record["local_center"]
        offset = Vector((0, 0, 0))
        x_sign = 1 if local_center.x >= 0 else -1
        y_sign = 1 if local_center.y >= 0 else -1
        z_sign = 1 if local_center.z >= 0 else -1

        if group == "leftBody":
            offset.x -= state["shellSplit"] * 0.235
        elif group == "rightBody":
            offset.x += state["shellSplit"] * 0.235
        elif group == "upperDrive":
            offset.z += state["stemLift"] * 0.155
            offset.y += state["stemLift"] * 0.035
        elif group == "lowerSupport":
            offset.z -= state["lowerDrop"] * 0.132
            offset.y -= state["lowerDrop"] * 0.025
        elif group == "seat":
            offset.x += x_sign * state["seatSpread"] * 0.1
            offset.y += y_sign * state["seatSpread"] * 0.024
        elif group == "fastener":
            offset.x += x_sign * state["fastenerSpread"] * 0.074
            offset.y += y_sign * state["fastenerSpread"] * 0.04
            offset.z += z_sign * state["fastenerSpread"] * 0.032

        obj.location = record["base_location"] + offset
        obj.rotation_euler = record["base_rotation"].copy()
        if group == "ball":
            obj.rotation_euler.rotate_axis("Z", math.radians(90) * state["ballTurn"])
    bpy.context.view_layer.update()


def look_at(obj: bpy.types.Object, target) -> None:
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def add_area_light(name: str, location, target, power: float, size, materials=None):
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


def add_plane(
    name: str,
    material: bpy.types.Material,
    location,
    scale,
    rotation=(0, 0, 0),
    visible=True,
    camera_visible=True,
):
    bpy.ops.mesh.primitive_plane_add(size=1, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(material)
    obj.hide_render = not visible
    obj.hide_viewport = not visible
    if hasattr(obj, "visible_camera"):
        obj.visible_camera = camera_visible
    return obj


def build_studio(materials: dict) -> None:
    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.color = (1.0, 1.0, 1.0)

    add_plane(
        "goal17_shadow_catcher_floor",
        materials["matte-white-studio"],
        (0, 0, -0.24),
        (3.4, 2.4, 1),
    )
    floor = bpy.context.object
    if hasattr(floor, "cycles"):
        floor.cycles.is_shadow_catcher = True

    add_plane(
        "goal17_left_black_reflection_card",
        materials["black-reflection-card"],
        (-0.85, -0.2, 0.28),
        (0.55, 0.9, 1),
        rotation=(0, math.radians(72), math.radians(18)),
        camera_visible=False,
    )
    add_plane(
        "goal17_right_black_reflection_card",
        materials["black-reflection-card"],
        (0.95, 0.15, 0.32),
        (0.55, 0.95, 1),
        rotation=(0, math.radians(-72), math.radians(-18)),
        camera_visible=False,
    )

    add_area_light("goal17_left_softbox_key", (-1.35, -1.65, 1.35), (0, 0, 0.08), 520, 2.4)
    add_area_light("goal17_top_strip_machined_edge", (0.15, -0.45, 1.82), (0, 0, 0), 360, (0.24, 1.85))
    add_area_light("goal17_right_rim_cutout", (1.35, 0.75, 0.82), (0, 0, 0.02), 210, 1.2)
    add_area_light("goal17_low_front_fill", (0.45, -1.35, 0.28), (0, 0, 0), 55, 1.1)


def create_camera() -> bpy.types.Object:
    camera_data = bpy.data.cameras.new("goal17_render_camera")
    camera_obj = bpy.data.objects.new("goal17_render_camera", camera_data)
    bpy.context.collection.objects.link(camera_obj)
    bpy.context.scene.camera = camera_obj
    camera_data.sensor_width = 36
    camera_data.dof.use_dof = False
    return camera_obj


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    model_path = (repo_root / args.model).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    clear_scene()
    configure_render(args.profile)
    materials = {name: make_material(f"goal17_{name}", spec) for name, spec in MATERIALS.items()}
    meshes = import_model(model_path)
    if not meshes:
        raise RuntimeError(f"No mesh objects imported from {model_path}")
    create_rig(meshes)
    records, group_counts, material_counts = assign_materials(meshes, materials)
    build_studio(materials)
    camera = create_camera()

    stills = []
    for setup in CAMERA_SETUPS:
        apply_state(records, setup["stateId"])
        camera.location = setup["camera"]
        camera.data.lens = setup["lensMm"]
        look_at(camera, setup["target"])
        output_path = out_dir / setup["filename"]
        bpy.context.scene.render.filepath = str(output_path)
        bpy.ops.render.render(write_still=True)
        stills.append(
            {
                "id": setup["id"],
                "stateId": setup["stateId"],
                "path": str(output_path.relative_to(repo_root)).replace("\\", "/"),
                "width": bpy.context.scene.render.resolution_x,
                "height": bpy.context.scene.render.resolution_y,
                "bytes": output_path.stat().st_size,
                "sha256": sha256(output_path),
            }
        )

    results = {
        "schemaVersion": 1,
        "renderer": "Blender Cycles",
        "profile": args.profile,
        "sourceModel": str(model_path.relative_to(repo_root)).replace("\\", "/"),
        "sourceModelSha256": sha256(model_path),
        "renderBoundary": {
            "stillCount": len(stills),
            "frameSequenceRendered": False,
            "fullReleaseFrameCount": 0,
            "homepageConnected": False,
        },
        "groupCounts": group_counts,
        "materialCounts": material_counts,
        "ballIsolation": {
            "actualBallMeshCount": group_counts.get("ball", 0),
            "invariant": "Only the classified true ball core receives the ball-open quarter-turn.",
        },
        "stills": stills,
    }
    results_path = out_dir.parent / "render-results.json"
    results_path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
