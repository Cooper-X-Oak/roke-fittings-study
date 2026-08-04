"""Goal30 的 hero-runtime 全量控制面快速预览执行面。

在 Blender 的当前场景中运行：

    blender --python scripts/render_goal30_consistent_motion_preview.py -- --repo-root .

脚本每次运行都读取当前 hero-runtime 的全部控制面，先把材质、灯光、镜头、
运动、分镜和交付说明应用到当前 Blender 场景，再按六个离散进度点观察部件
姿态。场景只提供稳定几何和部件基准属性，不得静默继承旧材质、灯光或镜头。
它不执行长时序列渲染、图片验证或交付门禁。
"""

from __future__ import annotations

import argparse
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
    raise SystemExit("请使用 Blender 的 Python 解释器运行此脚本。") from exc


AUTHORITY_DIR = "governance/control/hero-runtime"
CONTROL_ROOT_FILE = "control-root.json"
GOAL30_DIR = "docs/experiment/goal30-consistent-motion-preview"
DEFAULT_STATE_PROGRESS = [0.00, 0.16, 0.54, 0.70, 0.84, 0.92]
LIGHT_OBJECT_BY_ROLE = {
    "top-left-oblique-key": "preview_key_soft",
    "top-right-oblique-rim": "preview_rim_soft",
    "front-fill": "preview_front_fill",
    "top-executor-soft": "preview_top_executor_soft",
    "top-shell-wash": "preview_top_shell_wash",
    "left-side-lift": "preview_left_side_lift",
    "right-side-lift": "preview_right_side_lift",
    "top-front-fill": "preview_top_front_fill",
}
MATERIAL_ROLE_NAMES = {
    "cast-satin-body": "hero_runtime_cast_satin_body",
    "machined-flange-faces": "hero_runtime_machined_stainless",
    "fastener-stainless": "hero_runtime_fastener_stainless",
    "polished-stainless-ball": "hero_runtime_polished_stainless_ball",
    "graphite-packing": "hero_runtime_graphite_packing",
    "soft-seal-ptfe": "hero_runtime_soft_seal_ptfe",
}

OBSERVATION_STATES = [
    {
        "state_id": "fully-exploded-opening",
        "progress": 0.00,
        "focus": "完全爆炸开场的壳体、阀座密封、上下驱动和小五金层级。",
    },
    {
        "state_id": "precision-assembly-start",
        "progress": 0.16,
        "focus": "精密合体窗口起点保持完全爆炸，确认没有提前动作。",
    },
    {
        "state_id": "precision-assembly-end",
        "progress": 0.54,
        "focus": "合体完成，确认球体尚未旋转且壳体轴向连续。",
    },
    {
        "state_id": "ball-core-presentation-end",
        "progress": 0.70,
        "focus": "球体核心展示完成，确认旋转只作用于真实球体。",
    },
    {
        "state_id": "cutaway-reveal-end",
        "progress": 0.84,
        "focus": "剖面展示完成，确认内部层级清楚且清水尚未提前出现。",
    },
    {
        "state_id": "hero-hold-start",
        "progress": 0.92,
        "focus": "清水流动停留子窗口起点，确认主体动作已经稳定。",
    },
]


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    args = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output", default=f"{GOAL30_DIR}/state-observation.json")
    parser.add_argument("--progress-list", default=",".join(str(value) for value in DEFAULT_STATE_PROGRESS))
    parser.add_argument("--install-only", action="store_true")
    parser.add_argument("--restore", action="store_true")
    return parser.parse_args(args)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def relative_path(path: Path, repo_root: Path) -> str:
    return str(path.relative_to(repo_root)).replace("\\", "/")


def load_control_surface(repo_root: Path) -> dict:
    """Load the single current hero-runtime control root before touching the scene."""
    authority_root = (repo_root / AUTHORITY_DIR).resolve()
    root_path = authority_root / CONTROL_ROOT_FILE
    if not root_path.is_file():
        raise RuntimeError(f"当前 hero-runtime 控制根缺少文件：{root_path}")
    root = read_json(root_path)
    if root.get("schema") != "control-model-root/v0" or root.get("root_id") != "hero-runtime":
        raise RuntimeError("当前控制根不是 hero-runtime Control Model 根。")
    if root.get("authority_status") != "current":
        raise RuntimeError("当前 hero-runtime 控制根不是 current 权威。")

    runtime = root.get("runtime")
    runtime_order = list(root.get("runtime_order", []))
    nodes = []
    for locator in root.get("nodes", []):
        nodes.extend(locator.get("children", []))
    declared_controls = {
        node.get("control_id"): node.get("runtime_section")
        for node in nodes
        if node.get("node_role") == "control"
    }
    if not isinstance(runtime, dict) or set(runtime_order) != set(declared_controls):
        raise RuntimeError("hero-runtime 控制根的运行时控制集合不完整。")
    if any(declared_controls[control_id] not in runtime for control_id in runtime_order):
        raise RuntimeError("hero-runtime 控制根缺少运行时控制参数。")

    camera_source = runtime["camera"]
    lighting_source = runtime["lighting"]
    material_source = runtime["material"]
    motion_source = runtime["motion"]
    storyboard_source = runtime["storyboard"]
    if any(source.get("control_id") not in runtime_order for source in (camera_source, lighting_source, material_source, motion_source, storyboard_source)):
        raise RuntimeError("hero-runtime 运行时参数没有绑定声明的控制节点。")

    camera_control = {
        "control_id": camera_source["control_id"],
        "runtime_binding": {
            "required_scene_object_name": camera_source["scene_object_name"],
            "fallback_to_scene_camera": False,
        },
        "runtime_pose_blender": {
            "location": camera_source["location_blender"],
            "target": camera_source["target_blender"],
        },
        "controlled_override": {
            "catalogue_fov_degrees": camera_source["fov_degrees"],
        },
        "composition_state": camera_source["composition"],
        "camera_phase_policy": storyboard_source["shots"],
    }
    lighting_control = {
        "control_id": lighting_source["control_id"],
        "interactive_preview_calibration": {
            "renderer": lighting_source["renderer"],
            "color_management": lighting_source["color_management"],
            "subject_light_rig": lighting_source["lights"],
            "reflection_environment": lighting_source["reflection_environment"],
            "reflection_surfaces": lighting_source.get("reflection_surfaces", []),
            "studio_background": lighting_source.get("studio_background", {}),
        },
    }
    material_roles = {}
    for role_name, role in material_source["roles"].items():
        material_roles[role_name] = {
            "base_color_target": role["base_color"],
            "metallic": role["metallic"],
            "roughness_target": role["roughness"],
            "anisotropic_range": [role["anisotropic"], role["anisotropic"]],
            "coat_range": [role["coat"], role["coat"]],
        }
    material_control = {
        "control_id": material_source["control_id"],
        "commercial_pbr_envelope": {"roles": material_roles},
        "runtime_assignment": {
            "active_runtime_roles": list(material_roles),
            **material_source["assignment"],
        },
    }
    motion_control = {
        "control_id": motion_source["control_id"],
        "blender_transform_scale": motion_source["blender_transform_scale"],
        "channels": motion_source["channels"],
        "storyboard_schedule_binding": {
            "source_control_id": storyboard_source["control_id"],
            "phase_bindings": motion_source["schedule"],
        },
    }
    storyboard_control = {
        "control_id": storyboard_source["control_id"],
        "shot_order": storyboard_source["shots"],
    }
    controls = {
        "authority.json": root,
        "camera.json": camera_control,
        "lighting.json": lighting_control,
        "material.json": material_control,
        "motion.json": motion_control,
        "storyboard.json": storyboard_control,
    }
    loaded_ids = list(runtime_order)
    application_order = ["authority-root", *loaded_ids]

    return {
        "root": root,
        "controls": controls,
        "paths": {CONTROL_ROOT_FILE: relative_path(root_path, repo_root)},
        "execution_surface": {"surface_id": "hero-runtime"},
        "loaded_control_ids": loaded_ids,
        "loaded_files": [CONTROL_ROOT_FILE],
        "control_ids_by_file": {
            filename: control.get("control_id")
            for filename, control in controls.items()
            if filename != "authority.json"
        },
        "application_order": application_order,
        "release_gate_mode": "none",
    }


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def smoothstep(value: float) -> float:
    value = clamp01(value)
    return value * value * (3.0 - 2.0 * value)


def sign(value: float) -> float:
    return -1.0 if float(value) < 0.0 else 1.0


def vector3(value) -> Vector:
    return Vector((float(value[0]), float(value[1]), float(value[2])))


def group_for_part(part_name: str) -> str:
    name = str(part_name or "")
    folded = name.casefold()
    if any(token in name for token in ("阀体", "阀盖", "堵头")):
        return "bodyPressureShell"
    if any(token in name for token in ("球体", "固定轴", "轴承", "止推垫")):
        return "ballTrunnionCore"
    if any(token in name for token in ("阀座", "密封圈", "盘根")):
        return "seatSealSystem"
    if any(token in name for token in ("阀杆", "填料", "支架", "连接轴")):
        return "stemPackingDrive"
    if any(token in name for token in ("螺柱", "螺母", "垫片", "弹簧", "平键")):
        return "fastenersSmallHardware"
    if any(token in folded for token in ("stud", "nut", "washer", "screw", "pin", "bolt")):
        return "fastenersSmallHardware"
    return "machinedDetail"


def state_metadata(progress: float) -> dict:
    for item in OBSERVATION_STATES:
        if math.isclose(float(progress), item["progress"], abs_tol=1e-6):
            return dict(item)
    return {
        "state_id": f"progress-{float(progress):.4f}",
        "progress": round(float(progress), 4),
        "focus": "观察当前控制面在指定进度的部件状态。",
    }


def shot_ranges(storyboard: dict) -> dict[str, tuple[float, float]]:
    return {
        item["shot_id"]: tuple(float(value) for value in item["progress_range"])
        for item in storyboard["shot_order"]
    }


def shot_for_progress(storyboard: dict, progress: float) -> str:
    shots = storyboard["shot_order"]
    value = float(progress)
    for index, shot in enumerate(shots):
        start, end = (float(part) for part in shot["progress_range"])
        is_last = index == len(shots) - 1
        if start <= value < end or (is_last and start <= value <= end):
            return shot["shot_id"]
    return shots[-1]["shot_id"]


def build_bindings(motion: dict, storyboard: dict) -> dict:
    ranges = shot_ranges(storyboard)
    bindings = {}
    for item in motion["storyboard_schedule_binding"]["phase_bindings"]:
        shot_id = item["storyboard_shot_id"]
        bindings[item["motion_channel"]] = {
            "shot_id": shot_id,
            "effective_range": ranges[shot_id],
            "configured_range": tuple(float(value) for value in item["progress_range"]),
        }
    return bindings


def sample_channels(progress: float, motion: dict, bindings: dict) -> tuple[dict, dict]:
    sampled = {}
    for channel, binding in bindings.items():
        start, end = binding["effective_range"]
        sampled[channel] = smoothstep((float(progress) - start) / (end - start))

    values = {}
    for channel, spec in motion["channels"].items():
        values[channel] = sampled.get(spec.get("from"), 0.0)
    values["heroHold"] = sampled.get("heroHold", 0.0)
    return values, sampled


def capture_records() -> list[dict]:
    records = []
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH" or not obj.get("hero_runtime_part_name"):
            continue
        base_location = vector3(obj.get("hero_runtime_base_location", obj.location))
        base_rotation = vector3(obj.get("hero_runtime_base_rotation", obj.rotation_euler))
        records.append(
            {
                "object": obj,
                "part_name": str(obj.get("hero_runtime_part_name")),
                "group": group_for_part(obj.get("hero_runtime_part_name")),
                "base_location": base_location,
                "base_rotation": base_rotation,
                "initial_location": obj.location.copy(),
                "initial_rotation": obj.rotation_euler.copy(),
                "original_display_type": obj.display_type,
                "original_show_wire": obj.show_wire,
                "original_show_all_edges": obj.show_all_edges,
            }
        )
    return records


def set_material_input(node, names, value) -> None:
    for name in names:
        if name in node.inputs:
            node.inputs[name].default_value = value
            return


def midpoint(value, default: float) -> float:
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return (float(value[0]) + float(value[1])) / 2.0
    return float(default)


def role_scalar(role: dict, target_key: str, range_key: str, default: float) -> float:
    target = role.get(target_key)
    if target is not None:
        return float(target)
    return midpoint(role.get(range_key), default)


def material_role_for_record(record: dict, material_control: dict) -> str | None:
    part_name = record["part_name"]
    assignment = material_control.get("runtime_assignment") or {}
    active_roles = set(assignment.get("active_runtime_roles", []))
    part_overrides = assignment.get("part_name_overrides") or {}
    group_role_map = assignment.get("group_role_map") or {}

    role_name = part_overrides.get(part_name) or group_role_map.get(record["group"])
    if role_name not in active_roles:
        return None
    return role_name


def build_control_materials(material_control: dict) -> tuple[dict, dict]:
    roles = material_control["commercial_pbr_envelope"]["roles"]
    assignment = material_control.get("runtime_assignment") or {}
    active_role_names = list(assignment.get("active_runtime_roles", []))
    if not active_role_names:
        raise RuntimeError("material.json 未声明 active_runtime_roles。")
    if set(active_role_names) != set(MATERIAL_ROLE_NAMES):
        raise RuntimeError("material.json active_runtime_roles 与执行器材质角色集合不一致。")
    materials = {}
    snapshot = {}
    for role_name in active_role_names:
        material_name = MATERIAL_ROLE_NAMES[role_name]
        role = roles.get(role_name)
        if not role or not role.get("base_color_target"):
            continue

        base_color = tuple(float(value) for value in role["base_color_target"])
        metallic = role_scalar(role, "metallic", "metallic_range", 0.0)
        roughness = role_scalar(role, "roughness_target", "roughness_range", 0.5)
        anisotropic = midpoint(role.get("anisotropic_range"), 0.0)
        coat = midpoint(role.get("coat_range"), 0.0)

        material = bpy.data.materials.get(material_name) or bpy.data.materials.new(material_name)
        material.use_nodes = True
        material.diffuse_color = base_color
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        nodes.clear()
        output = nodes.new(type="ShaderNodeOutputMaterial")
        principled = nodes.new(type="ShaderNodeBsdfPrincipled")
        principled.name = "Principled BSDF"
        links.new(principled.outputs["BSDF"], output.inputs["Surface"])
        set_material_input(principled, ["Base Color"], base_color)
        set_material_input(principled, ["Metallic"], metallic)
        set_material_input(principled, ["Roughness"], roughness)
        set_material_input(principled, ["Anisotropic IOR Level", "Anisotropic"], anisotropic)
        set_material_input(principled, ["Coat Weight", "Clearcoat"], coat)
        set_material_input(principled, ["Coat Roughness", "Clearcoat Roughness"], roughness)
        materials[role_name] = material
        snapshot[role_name] = {
            "material": material_name,
            "baseColor": list(base_color),
            "metallic": round(metallic, 6),
            "roughness": round(roughness, 6),
            "anisotropic": round(anisotropic, 6),
            "coat": round(coat, 6),
            "source": "hero-runtime material.json",
        }
    return materials, snapshot


def apply_material_control_surface(records: list[dict], material_control: dict) -> dict:
    materials, snapshot = build_control_materials(material_control)
    assigned = Counter()
    unassigned = []
    for record in records:
        role_name = material_role_for_record(record, material_control)
        material = materials.get(role_name)
        if material is None:
            unassigned.append(f"{record['object'].name}<{record['part_name']}>")
            continue
        obj = record["object"]
        if obj.data.materials:
            obj.data.materials[0] = material
        else:
            obj.data.materials.append(material)
        assigned[role_name] += 1

    if unassigned:
        raise RuntimeError("有部件没有可用的 hero-runtime 材质角色：" + ", ".join(sorted(set(unassigned))))
    return {
        "assignedPartCount": sum(assigned.values()),
        "assignedRoles": dict(sorted(assigned.items())),
        "materialParameterSnapshot": snapshot,
    }


def set_object_visibility(obj, *, camera=None, glossy=None, diffuse=None, shadow=None) -> None:
    values = {
        "visible_camera": camera,
        "visible_glossy": glossy,
        "visible_diffuse": diffuse,
        "visible_shadow": shadow,
    }
    for attribute, value in values.items():
        if value is None or not hasattr(obj, attribute):
            continue
        try:
            setattr(obj, attribute, bool(value))
        except (AttributeError, TypeError, ValueError):
            pass


def orient_object_to_target(obj, target) -> None:
    direction = vector3(target) - obj.location
    if direction.length:
        obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()


def build_reflection_surface_material(surface: dict) -> bpy.types.Material:
    role = str(surface["role"]).replace("-", "_")
    material_name = f"hero_runtime_{role}"
    material = bpy.data.materials.get(material_name) or bpy.data.materials.new(material_name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new(type="ShaderNodeOutputMaterial")
    principled = nodes.new(type="ShaderNodeBsdfPrincipled")
    principled.name = "Principled BSDF"
    links.new(principled.outputs["BSDF"], output.inputs["Surface"])
    base_color = tuple(float(value) for value in surface["base_color"])
    set_material_input(principled, ["Base Color"], base_color)
    set_material_input(principled, ["Metallic"], float(surface.get("metallic", 0.0)))
    set_material_input(principled, ["Roughness"], float(surface.get("roughness", 0.8)))
    set_material_input(principled, ["Coat Weight", "Clearcoat"], 0.0)
    material.diffuse_color = base_color
    return material


def ensure_reflection_surface(surface: dict) -> dict:
    name = str(surface["scene_object_name"])
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "MESH":
        bpy.ops.mesh.primitive_plane_add(size=1.0, location=vector3(surface["location_blender"]))
        obj = bpy.context.object
        obj.name = name
        obj.data.name = f"{name}_mesh"

    obj.location = vector3(surface["location_blender"])
    obj.scale = (float(surface["width"]), float(surface["height"]), 1.0)
    orient_object_to_target(obj, surface["target_blender"])
    material = build_reflection_surface_material(surface)
    obj.data.materials.clear()
    obj.data.materials.append(material)
    obj.hide_viewport = False
    obj.hide_render = False
    set_object_visibility(
        obj,
        camera=surface["visible_camera"],
        glossy=surface["visible_glossy"],
        diffuse=surface["visible_diffuse"],
        shadow=surface["visible_shadow"],
    )
    return {
        "role": surface["role"],
        "object": obj.name,
        "location": [round(float(value), 6) for value in obj.location],
        "target": [round(float(value), 6) for value in vector3(surface["target_blender"])],
        "width": float(surface["width"]),
        "height": float(surface["height"]),
        "material": material.name,
        "materialModel": surface["material_model"],
        "visibleCamera": bool(surface["visible_camera"]),
        "visibleGlossy": bool(surface["visible_glossy"]),
        "visibleDiffuse": bool(surface["visible_diffuse"]),
        "visibleShadow": bool(surface["visible_shadow"]),
        "emission": bool(surface.get("emission", False)),
    }


def apply_reflection_surfaces(reflection_surfaces: list[dict]) -> list[dict]:
    return [ensure_reflection_surface(surface) for surface in reflection_surfaces]


def build_reflection_environment_material(reflection_control: dict) -> bpy.types.Material:
    material_name = "hero_runtime_reflection_environment"
    material = bpy.data.materials.get(material_name) or bpy.data.materials.new(material_name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new(type="ShaderNodeOutputMaterial")
    principled = nodes.new(type="ShaderNodeBsdfPrincipled")
    texcoord = nodes.new(type="ShaderNodeTexCoord")
    separate = nodes.new(type="ShaderNodeSeparateXYZ")
    ramp = nodes.new(type="ShaderNodeValToRGB")
    principled.name = "Principled BSDF"
    ramp.name = "Control Surface Color Ramp"
    links.new(texcoord.outputs["Generated"], separate.inputs["Vector"])
    links.new(separate.outputs["Z"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], principled.inputs["Base Color"])
    links.new(principled.outputs["BSDF"], output.inputs["Surface"])

    set_material_input(principled, ["Metallic"], float(reflection_control.get("metallic", 0.0)))
    set_material_input(principled, ["Roughness"], float(reflection_control.get("roughness", 0.7)))
    color_ramp = reflection_control.get("base_color_ramp", [])
    if color_ramp:
        while len(ramp.color_ramp.elements) > 2:
            ramp.color_ramp.elements.remove(ramp.color_ramp.elements[-1])
        for index, item in enumerate(color_ramp):
            element = ramp.color_ramp.elements[0] if index == 0 else (
                ramp.color_ramp.elements[1] if index == 1 else ramp.color_ramp.elements.new(float(item["position"]))
            )
            element.position = float(item["position"])
            element.color = tuple(float(value) for value in item["color"])
    material.diffuse_color = tuple(float(value) for value in color_ramp[-1]["color"]) if color_ramp else (0.8, 0.8, 0.8, 1.0)
    return material


def apply_lighting_control_surface(lighting_control: dict, records: list[dict]) -> dict:
    preview = lighting_control["interactive_preview_calibration"]
    renderer = preview["renderer"]
    scene = bpy.context.scene
    scene.render.engine = str(renderer["engine"])
    if scene.render.engine == "CYCLES":
        scene.cycles.samples = int(renderer["samples"])
        scene.cycles.max_bounces = int(renderer["max_bounces"])
        scene.cycles.diffuse_bounces = int(renderer["diffuse_bounces"])
        scene.cycles.glossy_bounces = int(renderer["glossy_bounces"])
        scene.cycles.use_denoising = bool(renderer["denoising"])
    color_management = preview["color_management"]
    scene.view_settings.view_transform = color_management["view_transform"]
    scene.view_settings.look = color_management["look"]
    scene.view_settings.exposure = float(color_management["exposure"])

    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background") if world.node_tree else None
    if background:
        world_color = color_management.get("world_color")
        if world_color is not None:
            set_material_input(background, ["Color"], tuple(float(value) for value in world_color))
        background.inputs["Strength"].default_value = float(color_management["world_strength"])

    applied_lights = []
    missing_lights = []
    for light_spec in preview["subject_light_rig"]:
        role = light_spec["role"]
        obj = bpy.data.objects.get(LIGHT_OBJECT_BY_ROLE.get(role, ""))
        if obj is None or obj.type != "LIGHT":
            missing_lights.append(role)
            continue
        data = obj.data
        data.energy = float(light_spec["power"])
        data.shape = light_spec["shape"]
        data.size = float(light_spec["size"])
        if light_spec.get("location_blender"):
            obj.location = vector3(light_spec["location_blender"])
        if light_spec.get("target_blender"):
            orient_object_to_target(obj, light_spec["target_blender"])
        if "specular_factor" in light_spec and hasattr(data, "specular_factor"):
            data.specular_factor = float(light_spec["specular_factor"])
        if "diffuse_factor" in light_spec and hasattr(data, "diffuse_factor"):
            data.diffuse_factor = float(light_spec["diffuse_factor"])
        set_object_visibility(obj, camera=light_spec["visible_camera"], glossy=light_spec["visible_glossy"])
        applied_lights.append({
            "role": role,
            "object": obj.name,
            "location": [round(float(value), 6) for value in obj.location],
            "target": [round(float(value), 6) for value in vector3(light_spec.get("target_blender", obj.location))],
            "power": float(data.energy),
            "size": float(data.size),
            "specularFactor": float(getattr(data, "specular_factor", light_spec.get("specular_factor", 1.0))),
            "diffuseFactor": float(getattr(data, "diffuse_factor", light_spec.get("diffuse_factor", 1.0))),
            "distanceClass": light_spec.get("distance_class"),
            "visibleCamera": bool(light_spec["visible_camera"]),
            "visibleGlossy": bool(light_spec["visible_glossy"]),
        })
    if missing_lights:
        raise RuntimeError("当前 Blender 场景缺少控制面要求的灯光角色：" + ", ".join(missing_lights))

    reflection = preview["reflection_environment"]
    dome = bpy.data.objects.get("preview_reflection_dome")
    if dome is None or dome.type != "MESH":
        raise RuntimeError("当前 Blender 场景缺少 preview_reflection_dome，拒绝继承未声明的反射环境。")
    geometry_declaration = reflection.get("geometry")
    geometry = geometry_declaration if isinstance(geometry_declaration, dict) else {}
    location_blender = geometry.get("location_blender") or reflection.get("location_blender")
    scale_blender = geometry.get("scale_blender") or reflection.get("scale_blender")
    if location_blender:
        dome.location = vector3(location_blender)
    if scale_blender:
        dome.scale = vector3(scale_blender)
    dome_material = build_reflection_environment_material(reflection)
    dome.data.materials.clear()
    dome.data.materials.append(dome_material)
    set_object_visibility(
        dome,
        camera=reflection["visible_camera"],
        glossy=reflection["visible_glossy"],
        diffuse=reflection["visible_diffuse"],
        shadow=reflection["visible_shadow"],
    )
    reflection_surfaces = apply_reflection_surfaces(preview.get("reflection_surfaces", []))

    background_control = preview["studio_background"]
    backdrop_material_spec = background_control.get("backdrop_material")
    backdrop_material_result = None
    if backdrop_material_spec:
        backdrop_name = background_control["backdrop_scene_object_name"]
        backdrop_object = bpy.data.objects.get(backdrop_name)
        if backdrop_object is None or backdrop_object.type != "MESH" or not backdrop_object.data.materials:
            raise RuntimeError("当前 Blender 场景缺少控制面指定的背景材质对象：" + backdrop_name)
        backdrop_material = backdrop_object.data.materials[0]
        shader = str(backdrop_material_spec.get("shader", ""))
        if shader != "emission":
            raise RuntimeError("当前执行面只支持已声明的 emission 背景材质。")
        emission = backdrop_material.node_tree.nodes.get("Emission")
        if emission is None:
            raise RuntimeError("当前 Blender 背景材质缺少控制面指定的 Emission 节点。")
        color = tuple(float(value) for value in backdrop_material_spec["color"])
        emission.inputs["Color"].default_value = color
        emission.inputs["Strength"].default_value = float(backdrop_material_spec["strength"])
        backdrop_material.diffuse_color = color
        backdrop_material_result = {
            "object": backdrop_object.name,
            "shader": shader,
            "color": list(color),
            "strength": float(emission.inputs["Strength"].default_value),
        }
    background_specs = [
        {
            "role": "backdrop",
            "name": background_control["backdrop_scene_object_name"],
            "camera": bool(background_control["backdrop_visible_camera"]),
            "shadow": False,
        },
        {
            "role": "floor",
            "name": background_control["floor_scene_object_name"],
            "camera": bool(background_control["floor_visible_camera"]),
            "shadow": bool(background_control["floor_visible_shadow"]),
        },
    ]
    background_objects = []
    for background_spec in background_specs:
        obj = bpy.data.objects.get(background_spec["name"])
        if obj is None:
            raise RuntimeError(
                "当前 Blender 场景缺少控制面指定的 studio_background 对象："
                + background_spec["name"]
            )
        set_object_visibility(
            obj,
            camera=background_spec["camera"],
            glossy=False,
            diffuse=True,
            shadow=background_spec["shadow"],
        )
        background_objects.append({
            "role": background_spec["role"],
            "object": obj.name,
            "visibleCamera": background_spec["camera"],
            "visibleGlossy": False,
            "visibleDiffuse": True,
            "visibleShadow": background_spec["shadow"],
        })

    for record in records:
        set_object_visibility(record["object"], glossy=record["part_name"] == "球体")

    return {
        "renderer": {
            "engine": scene.render.engine,
            "samples": int(renderer["samples"]),
            "colorManagement": {
                "viewTransform": scene.view_settings.view_transform,
                "look": scene.view_settings.look,
                "exposure": float(scene.view_settings.exposure),
                "worldStrength": float(background.inputs["Strength"].default_value) if background else None,
            },
        },
        "lights": applied_lights,
        "reflectionEnvironment": {
            "object": dome.name,
            "material": dome_material.name,
            "visibleCamera": bool(reflection["visible_camera"]),
            "visibleGlossy": bool(reflection["visible_glossy"]),
            "visibleDiffuse": bool(reflection["visible_diffuse"]),
            "visibleShadow": bool(reflection["visible_shadow"]),
            "emission": bool(reflection.get("emission", False)),
        },
        "reflectionSurfaces": reflection_surfaces,
        "backdropMaterial": backdrop_material_result,
        "backgroundObjects": background_objects,
        "nonBallProductPartsVisibleGlossy": False,
    }


def apply_camera_control_surface(camera_control: dict) -> dict:
    scene = bpy.context.scene
    binding = camera_control.get("runtime_binding") or {}
    camera_name = binding.get("required_scene_object_name")
    camera = bpy.data.objects.get(camera_name) if camera_name else None
    if camera is None or camera.type != "CAMERA":
        raise RuntimeError("当前 Blender 场景缺少控制面指定的 preview_camera，拒绝继承现场相机状态。")
    scene.camera = camera
    override = camera_control["controlled_override"]
    pose = camera_control.get("runtime_pose_blender")
    if not isinstance(pose, dict) or not pose.get("location") or not pose.get("target"):
        raise RuntimeError("camera.json 未提供确定性的 Blender 相机位置和目标点。")
    camera.location = vector3(pose["location"])
    target = vector3(pose["target"])
    direction = target - camera.location
    if direction.length == 0:
        raise RuntimeError("camera.json 的相机位置和目标点不能相同。")
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    fov_degrees = float(override["catalogue_fov_degrees"])
    sensor_width = float(camera.data.sensor_width or 36.0)
    camera.data.lens = sensor_width / (2.0 * math.tan(math.radians(fov_degrees) / 2.0))
    return {
        "camera": camera.name,
        "requiredSceneObjectName": camera_name,
        "fallbackToSceneCamera": False,
        "location": [round(float(value), 6) for value in camera.location],
        "target": [round(float(value), 6) for value in target],
        "catalogueFovDegrees": fov_degrees,
        "lensMillimeters": round(float(camera.data.lens), 6),
        "productCenterPreserved": bool(camera_control["composition_state"]["product_center_preserved"]),
        "pipeAxisReadabilityPreserved": bool(camera_control["composition_state"]["pipe_axis_readability_preserved"]),
        "phasePolicyLoaded": len(camera_control["camera_phase_policy"]),
    }


def apply_full_control_surface(control_surface: dict, records: list[dict]) -> dict:
    controls = control_surface["controls"]
    camera_result = None
    lighting_result = None
    material_result = None
    applied_order = []
    file_by_control_id = {
        control.get("control_id"): filename
        for filename, control in controls.items()
        if filename != "authority.json"
    }
    for control_id in control_surface["application_order"]:
        applied_order.append(control_id)
        if control_id == "authority-root":
            continue
        filename = file_by_control_id[control_id]
        if control_id == "hero-runtime-camera-control":
            camera_result = apply_camera_control_surface(controls[filename])
        elif control_id == "hero-runtime-lighting-control":
            lighting_result = apply_lighting_control_surface(controls[filename], records)
        elif control_id == "hero-runtime-material-control":
            material_result = apply_material_control_surface(records, controls[filename])
    return {
        "surfaceId": control_surface["execution_surface"]["surface_id"],
        "loadedFiles": control_surface["loaded_files"],
        "loadedControlIds": control_surface["loaded_control_ids"],
        "applicationOrder": applied_order,
        "camera": camera_result,
        "lighting": lighting_result,
        "material": material_result,
        "motionAndStoryboardLoaded": True,
        "releaseGateLoadedAs": control_surface["release_gate_mode"],
        "fallbackToStaleSceneState": False,
        "imageValidator": "none",
        "renderGate": "none",
    }


def make_preview_material(name: str, color, alpha: float, roughness: float) -> bpy.types.Material:
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = (*color, alpha)
    try:
        material.surface_render_method = "DITHERED" if alpha < 1.0 else "DITHERED"
    except (AttributeError, TypeError, ValueError):
        pass
    try:
        material.blend_method = "BLEND" if alpha < 1.0 else "OPAQUE"
    except (AttributeError, TypeError, ValueError):
        pass
    principled = material.node_tree.nodes.get("Principled BSDF")
    if principled:
        set_material_input(principled, ["Base Color"], (*color, 1.0))
        set_material_input(principled, ["Metallic"], 0.0)
        set_material_input(principled, ["Roughness"], roughness)
        set_material_input(principled, ["Alpha"], alpha)
        set_material_input(principled, ["Transmission Weight", "Transmission"], 0.12)
    return material


def ensure_flow_preview() -> list[bpy.types.Object]:
    existing = [
        bpy.data.objects.get("goal30_preview_clear_water_core"),
        bpy.data.objects.get("goal30_preview_clear_water_ring_1"),
        bpy.data.objects.get("goal30_preview_clear_water_ring_2"),
        bpy.data.objects.get("goal30_preview_clear_water_ring_3"),
    ]
    if all(existing):
        return existing

    material = make_preview_material("goal30_preview_clear_water_material", (0.20, 0.64, 0.92), 0.62, 0.08)
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=32,
        radius=0.027,
        depth=0.46,
        location=(0.0, 0.0, -0.085),
        rotation=(0.0, math.radians(90.0), 0.0),
    )
    core = bpy.context.object
    core.name = "goal30_preview_clear_water_core"
    core.data.materials.append(material)
    result = [core]
    for index, x in enumerate((-0.16, 0.0, 0.16), start=1):
        bpy.ops.mesh.primitive_torus_add(
            major_radius=0.034,
            minor_radius=0.0022,
            major_segments=32,
            minor_segments=8,
            location=(x, 0.0, -0.085),
            rotation=(0.0, math.radians(90.0), 0.0),
        )
        ring = bpy.context.object
        ring.name = f"goal30_preview_clear_water_ring_{index}"
        ring.data.materials.append(material)
        result.append(ring)
    for obj in result:
        obj.hide_viewport = True
        obj.hide_render = True
    return result


def apply_motion(records: list[dict], values: dict, motion: dict) -> dict:
    scale = motion["blender_transform_scale"]
    channel_specs = motion["channels"]
    moved_counts = Counter()
    max_offset = 0.0
    ball_angle = 0.0

    for record in records:
        obj = record["object"]
        part_name = record["part_name"]
        group = record["group"]
        base = record["base_location"]
        exploded = record["initial_location"]
        offset = Vector((0.0, 0.0, 0.0))

        if group == "bodyPressureShell":
            amount = values["shellClosure"]
            multiplier = float(channel_specs["shellClosure"]["multiplier"])
            offset.x = sign(exploded.x - base.x) * float(scale["body_pressure_shell_x"]) * multiplier * (1.0 - amount)
            offset.y = sign(exploded.y - base.y) * float(scale["body_pressure_shell_y"]) * multiplier * (1.0 - amount)
        elif group == "seatSealSystem":
            amount = values["seatSealClosure"]
            multiplier = float(channel_specs["seatSealClosure"]["multiplier"])
            offset.x = sign(exploded.x - base.x) * float(scale["seat_seal_system_x"]) * multiplier * (1.0 - amount)
            offset.y = sign(exploded.y - base.y) * float(scale["seat_seal_system_y"]) * multiplier * (1.0 - amount)
        elif group == "stemPackingDrive":
            amount = values["stemDriveClosure"]
            multiplier = float(channel_specs["stemDriveClosure"]["multiplier"])
            offset.z = sign(exploded.z - base.z) * float(scale["stem_packing_drive_z"]) * multiplier * (1.0 - amount)
            offset.y = sign(exploded.y - base.y) * float(scale["stem_packing_drive_y"]) * multiplier * (1.0 - amount)
        elif group == "ballTrunnionCore" and part_name != "球体":
            if "固定轴" in part_name or exploded.z < base.z - 0.05:
                amount = values["lowerSupportClosure"]
                multiplier = float(channel_specs["lowerSupportClosure"]["multiplier"])
                offset.z = sign(exploded.z - base.z) * float(scale["lower_support_z"]) * multiplier * (1.0 - amount)
            elif exploded.z > base.z + 0.02:
                amount = values["stemDriveClosure"]
                multiplier = float(channel_specs["stemDriveClosure"]["multiplier"])
                offset.z = sign(exploded.z - base.z) * float(scale["stem_packing_drive_z"]) * 0.52 * multiplier * (1.0 - amount)
        elif group == "fastenersSmallHardware":
            channel = "springReturn" if part_name == "弹簧" else "fastenerReturn"
            amount = values[channel]
            multiplier = float(channel_specs[channel]["multiplier"])
            radial = Vector((exploded.x - base.x, exploded.y - base.y, 0.0))
            if radial.length < 0.001:
                radial = Vector((1.0, 0.0, 0.0))
            radial.normalize()
            offset += radial * float(scale["fastener_radial"]) * multiplier * (1.0 - amount)
            offset.z = sign(exploded.z - base.z) * float(scale["fastener_z"]) * multiplier * (1.0 - amount)

        obj.location = base + offset
        obj.rotation_euler = record["base_rotation"].copy()
        if part_name == "球体":
            ball_angle = values["ballPresentationTurn"] * float(channel_specs["ballPresentationTurn"]["degrees"])
            obj.rotation_euler.rotate_axis("Z", math.radians(ball_angle))

        if offset.length > 0.0001:
            moved_counts[group] += 1
            max_offset = max(max_offset, float(offset.length))

    bpy.context.view_layer.update()
    return {
        "movedCounts": dict(sorted(moved_counts.items())),
        "maxOffset": round(max_offset, 6),
        "ballAngleDegrees": round(ball_angle, 4),
    }


def apply_cutaway_preview(records: list[dict], amount: float) -> dict:
    visible = float(amount) > 0.35
    affected = []
    for record in records:
        if record["part_name"] not in {"阀体", "阀盖"}:
            continue
        obj = record["object"]
        if visible:
            obj.display_type = "WIRE"
            obj.show_wire = True
            obj.show_all_edges = True
            affected.append(record["part_name"])
        else:
            obj.display_type = record["original_display_type"]
            obj.show_wire = record["original_show_wire"]
            obj.show_all_edges = record["original_show_all_edges"]
    return {
        "mode": "wireframe-shell-preview" if visible else "closed-shell-preview",
        "visible": visible,
        "amount": round(float(amount), 4),
        "affectedParts": sorted(set(affected)),
        "note": "快速观察代理，不代表最终剖面布尔结果。",
    }


def apply_flow_preview(flow_objects: list[bpy.types.Object], amount: float) -> dict:
    visible = float(amount) > 0.08
    for index, obj in enumerate(flow_objects):
        obj.hide_viewport = not visible
        obj.hide_render = not visible
        if visible and index > 0:
            phase = (float(amount) + index * 0.23) % 1.0
            obj.location.x = -0.20 + phase * 0.40
    return {
        "mode": "clear-water-flow-preview" if visible else "hidden-water-preview",
        "visible": visible,
        "amount": round(float(amount), 4),
        "objectCount": len(flow_objects),
        "note": "低成本清水流动代理，不执行长时渲染。",
    }


def install_runtime(control_surface: dict) -> dict:
    controls = control_surface["controls"]
    motion = controls["motion.json"]
    storyboard = controls["storyboard.json"]
    records = capture_records()
    control_application = apply_full_control_surface(control_surface, records)
    bindings = build_bindings(motion, storyboard)
    flow_objects = ensure_flow_preview()

    def apply_state(progress: float) -> dict:
        values, sampled = sample_channels(progress, motion, bindings)
        motion_result = apply_motion(records, values, motion)
        cutaway_result = apply_cutaway_preview(records, values["cutawayReveal"])
        flow_result = apply_flow_preview(flow_objects, values["clearWaterFlow"])
        metadata = state_metadata(progress)
        result = {
            **metadata,
            "storyboardShotId": shot_for_progress(storyboard, progress),
            "state": {key: round(float(value), 4) for key, value in values.items()},
            "sampledChannels": {key: round(float(value), 4) for key, value in sampled.items()},
            "scheduledBy": {
                key: binding["shot_id"] for key, binding in bindings.items()
            },
            "motionEvidence": motion_result,
            "cutawayPreview": cutaway_result,
            "flowPreview": flow_result,
            "partCount": len(records),
        }
        return result

    def restore() -> None:
        for record in records:
            obj = record["object"]
            obj.location = record["initial_location"].copy()
            obj.rotation_euler = record["initial_rotation"].copy()
            obj.display_type = record["original_display_type"]
            obj.show_wire = record["original_show_wire"]
            obj.show_all_edges = record["original_show_all_edges"]
        for obj in flow_objects:
            obj.hide_viewport = True
            obj.hide_render = True
        bpy.context.view_layer.update()

    runtime = {
        "apply_state": apply_state,
        "restore": restore,
        "controlSurface": control_surface,
        "controlApplication": control_application,
        "motion": motion,
        "storyboard": storyboard,
        "bindings": bindings,
        "records": records,
        "flowObjects": flow_objects,
        "policy": {
            "mode": "blender-mcp-quick-preview",
            "fullControlSurfaceLoad": True,
            "staleSceneFallback": False,
            "singleFrameObservation": True,
            "fullSequenceRender": False,
            "imageValidator": "none",
            "renderGate": "none",
        },
    }
    bpy.app.driver_namespace["goal30_consistent_motion_preview"] = runtime
    return runtime


def parse_progress_list(value: str) -> list[float]:
    result = []
    for item in value.split(","):
        if item.strip():
            result.append(round(clamp01(float(item.strip())), 6))
    return sorted(set(result))


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    if args.restore:
        existing_runtime = bpy.app.driver_namespace.get("goal30_consistent_motion_preview")
        if existing_runtime is None:
            print(json.dumps({"status": "ok", "goal": "goal30-consistent-motion-preview", "restored": False, "reason": "当前 Blender 会话没有已安装的 Goal30 runtime。"}, ensure_ascii=False))
            return
        existing_runtime["restore"]()
        print(json.dumps({"status": "ok", "goal": "goal30-consistent-motion-preview", "restored": True}, ensure_ascii=False))
        return

    existing_runtime = bpy.app.driver_namespace.get("goal30_consistent_motion_preview")
    if existing_runtime is not None:
        existing_runtime["restore"]()
    control_surface = load_control_surface(repo_root)
    runtime = install_runtime(control_surface)

    progress_values = parse_progress_list(args.progress_list)
    if args.install_only:
        print(json.dumps({
            "status": "ok",
            "goal": "goal30-consistent-motion-preview",
            "installed": True,
            "fullControlSurfaceLoad": runtime["policy"]["fullControlSurfaceLoad"],
            "loadedControlIds": runtime["controlApplication"]["loadedControlIds"],
            "partCount": len(runtime["records"]),
        }, ensure_ascii=False))
        return

    observations = [runtime["apply_state"](progress) for progress in progress_values]
    output_path = (repo_root / args.output).resolve()
    write_json(
        output_path,
        {
            "schemaVersion": 1,
            "goalId": "goal30-consistent-motion-preview",
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "description": "Goal30 使用当前 hero-runtime 控制面驱动 Blender 快速观察的六个离散运动状态。",
            "authority": {
                "fullControlSurface": runtime["controlSurface"]["paths"],
                "loadedControlIds": runtime["controlApplication"]["loadedControlIds"],
                "executionSurfaceId": runtime["controlApplication"]["surfaceId"],
                "fullControlSurfaceIsRuntimeInput": True,
                "motionControlIsRuntimeInput": True,
                "storyboardControlsSchedule": True,
                "staleSceneFallback": False,
            },
            "previewPolicy": runtime["policy"],
            "controlApplication": runtime["controlApplication"],
            "capturePose": "当前 Blender 场景首次安装时的完全爆炸姿态",
            "observations": observations,
        },
    )
    print(json.dumps({"status": "ok", "goal": "goal30-consistent-motion-preview", "states": len(observations), "output": str(output_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
