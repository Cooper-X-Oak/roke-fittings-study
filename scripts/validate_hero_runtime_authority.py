#!/usr/bin/env python3
"""Validate the fixed-ball-valve hero-runtime authority folder."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_ROOT = ROOT / "governance" / "control" / "hero-runtime"
LOOKDEV = ROOT / "docs" / "assets" / "ztovalve" / "hero" / "goal28a-clean-commercial-white-studio" / "render-manifest.json"
MOTION_CONTROL = ROOT / "docs" / "assets" / "ztovalve" / "hero" / "goal26-blender-camera-explosion-proof" / "motion-control.json"
CAMERA_PREVIS = ROOT / "docs" / "assets" / "ztovalve" / "hero" / "camera-previs-240.json"
FORBIDDEN_AUTHORITY_FRAGMENTS = [
    "docs/",
    "docs\\",
    "governance/",
    "governance\\",
    "scripts/",
    "scripts\\",
    "goal27",
    "goal28",
    "goal26",
    "goal25",
]
COMPONENT_FILES = [
    "material.json",
    "lighting.json",
    "camera.json",
    "motion.json",
    "storyboard.json",
    "release-gate.json",
]
EXPECTED_CONTROL_IDS = {
    "hero-runtime-material-authority",
    "hero-runtime-lighting-authority",
    "hero-runtime-camera-authority",
    "hero-runtime-motion-authority",
    "hero-runtime-storyboard-authority",
    "hero-runtime-delivery-gate",
}
EXPECTED_CHANNELS = {
    "shellClosure",
    "seatSealClosure",
    "stemDriveClosure",
    "lowerSupportClosure",
    "fastenerReturn",
    "springReturn",
    "ballPresentationTurn",
    "cutawayReveal",
    "clearWaterFlow",
}
EXPECTED_SHOTS = [
    "fully-exploded-opening",
    "precision-assembly",
    "ball-core-presentation",
    "cutaway-reveal",
    "clear-water-flow-hold",
]
REVALIDATION_SCOPE = {
    "lighting",
    "material",
    "camera",
    "motion",
    "storyboard",
    "delivery",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def read_json(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"missing {path.relative_to(ROOT)}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path.relative_to(ROOT)} must be a JSON object")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def walk_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        strings: list[str] = []
        for item in value:
            strings.extend(walk_strings(item))
        return strings
    if isinstance(value, dict):
        strings = []
        for key, item in value.items():
            strings.extend(walk_strings(key))
            strings.extend(walk_strings(item))
        return strings
    return []


def require_no_external_refs(name: str, value: dict[str, Any]) -> None:
    lowered = [text.lower() for text in walk_strings(value)]
    for fragment in FORBIDDEN_AUTHORITY_FRAGMENTS:
        require(
            not any(fragment in text for text in lowered),
            f"{name} must not reference project/test artifacts: {fragment}",
        )


def require_terms(values: list[str], terms: list[str], message: str) -> None:
    text = " ".join(values)
    require(all(term in text for term in terms), message)


def require_vector(value: Any, label: str) -> list[float]:
    require(isinstance(value, list) and len(value) == 4, f"{label} must be a four-component color")
    result = []
    for index, component in enumerate(value):
        require(isinstance(component, (int, float)), f"{label}[{index}] must be numeric")
        result.append(float(component))
    return result


def require_range(value: Any, label: str) -> tuple[float, float]:
    require(isinstance(value, list) and len(value) == 2, f"{label} must be a numeric pair")
    low, high = value
    require(isinstance(low, (int, float)) and isinstance(high, (int, float)), f"{label} must be numeric")
    require(float(low) <= float(high), f"{label} must be ordered")
    return float(low), float(high)


def require_number_between(value: Any, low: float, high: float, label: str) -> None:
    require(isinstance(value, (int, float)), f"{label} must be numeric")
    current = float(value)
    require(low <= current <= high, f"{label} {current} outside authority range {low}..{high}")


def require_color_inside(value: Any, range_value: Any, label: str) -> None:
    color = require_vector(value, label)
    require(isinstance(range_value, list) and len(range_value) == 2, f"{label} authority range must have low/high colors")
    low = require_vector(range_value[0], f"{label} low range")
    high = require_vector(range_value[1], f"{label} high range")
    for index, component in enumerate(color):
        require(low[index] <= component <= high[index], f"{label}[{index}] {component} outside authority range")


def find_zone_material(snapshot: dict[str, Any], zone_id: str) -> dict[str, Any]:
    for item in snapshot.get("bodyZoneMaterials", []):
        if item.get("id") == zone_id:
            material = item.get("material")
            require(isinstance(material, dict), f"{zone_id} material snapshot missing")
            return material
    raise SystemExit(f"FAIL: missing body zone material snapshot: {zone_id}")


def load_authority_folder() -> dict[str, dict[str, Any]]:
    require(AUTHORITY_ROOT.is_dir(), "governance/control/hero-runtime authority folder is missing")
    files: dict[str, dict[str, Any]] = {"authority.json": read_json(AUTHORITY_ROOT / "authority.json")}
    for component in COMPONENT_FILES:
        files[component] = read_json(AUTHORITY_ROOT / component)
    for name, value in files.items():
        require_no_external_refs(name, value)
    return files


def validate_folder_shape(files: dict[str, dict[str, Any]]) -> None:
    root = files["authority.json"]
    require(root.get("kind") == "control_authority_folder", "authority root kind drifted")
    require(root.get("status") == "active", "authority root must be active")
    require(root.get("authority_status") == "current", "authority root must be current")
    require(root.get("authority_id") == "hero-runtime", "authority id drifted")
    require(root.get("folder_policy", {}).get("self_contained") is True, "authority folder must be self-contained")
    require(root.get("folder_policy", {}).get("external_artifact_references_allowed") is False, "authority must forbid external artifact references")
    require(root.get("folder_policy", {}).get("single_json_scatter_allowed") is False, "authority must not be a scattered single JSON")
    require(root.get("components") == COMPONENT_FILES, "authority component file list drifted")

    control_ids = {files[name].get("control_id") for name in COMPONENT_FILES}
    require(control_ids == EXPECTED_CONTROL_IDS, "authority component control ids drifted")
    require(all(files[name].get("authority_id") == "hero-runtime" for name in COMPONENT_FILES), "component authority ids drifted")


def release_blocks_delivery(release: dict[str, Any]) -> bool:
    approval = release["approval_state"]
    return (
        approval["approved_for_240_frame_render"] is False
        and approval["approved_for_homepage_replacement"] is False
        and approval["approved_for_pages_publication"] is False
    )


def stale_lookdev_revalidation_allowed(release: dict[str, Any]) -> bool:
    evidence = release.get("lookdev_evidence_state", {})
    return (
        isinstance(evidence, dict)
        and evidence.get("current_visual_approval") is False
        and evidence.get("current_authority_lookdev_revalidation_required") is True
        and set(evidence.get("runtime_revalidation_scope", [])) == REVALIDATION_SCOPE
        and evidence.get("stale_lookdev_binding_allowed_only_while_release_blocked") is True
        and release_blocks_delivery(release)
    )


def validate_runtime_authority_binding(files: dict[str, dict[str, Any]], lookdev: dict[str, Any], release: dict[str, Any]) -> bool:
    policy = files["release-gate.json"]["runtime_authority_policy"]
    binding = lookdev.get("runtimeAuthority")
    require(isinstance(binding, dict), "lookdev must declare runtimeAuthority")
    require(binding.get("authorityId") == "hero-runtime", "lookdev runtime authority id drifted")
    require(
        binding.get("soleCurrentHeroRenderAuthority") is policy["sole_current_hero_render_authority"],
        "lookdev must bind to hero-runtime as the sole current hero render authority",
    )
    require(
        binding.get("manifestAuthorityBindingRequired") is policy["render_manifest_authority_binding_required"],
        "lookdev runtime authority binding requirement drifted",
    )
    require(
        binding.get("nonRuntimeRenderAuthorityAllowed") is policy["non_runtime_render_authority_allowed"],
        "lookdev allowed a non-runtime render authority",
    )

    hashes = binding.get("authorityFileSha256")
    require(isinstance(hashes, dict), "runtime authority file hashes missing")
    expected_files = ["authority.json", *COMPONENT_FILES]
    require(set(hashes) == set(expected_files), "runtime authority hash file set drifted")
    binding_is_current = binding.get("authorityStatus") == files["authority.json"]["authority_status"]
    for name in expected_files:
        binding_is_current = binding_is_current and hashes[name] == sha256(AUTHORITY_ROOT / name)
    if binding_is_current:
        return True
    require(
        stale_lookdev_revalidation_allowed(release),
        "lookdev authority binding is stale but release gate does not explicitly require current-authority revalidation",
    )
    return False


def validate_material(authority: dict[str, Any], lookdev: dict[str, Any]) -> None:
    state = authority["appearance_state"]
    require(state["body_material_truth"] == "silica-sol investment-cast stainless steel visual", "material truth drifted")
    require(state["rendering_model"] == "clean PBR", "material rendering model drifted")
    require(
        state["material_profile"] == "commercial-silica-sol-cast-stainless-v1",
        "commercial material profile drifted",
    )
    pbr_policy = authority["pbr_calibration_policy"]
    require(pbr_policy["workflow"] == "metallic-roughness-clean-commercial-pbr", "material PBR workflow drifted")
    require(pbr_policy["metallic_materials_require_metallic_one"] is True, "metallic material policy drifted")
    require(pbr_policy["base_color_is_material_substrate_not_lighting"] is True, "base-color material boundary drifted")
    require(pbr_policy["roughness_controls_reflection_spread_not_dirt"] is True, "roughness/dirt boundary drifted")
    require(pbr_policy["displacement_damage_or_scratch_geometry_allowed"] is False, "damage displacement became allowed")
    require_terms(
        authority.get("forbidden", []),
        [
            "WCB interpretation",
            "war-damaged look",
            "dirty blotch procedural color noise",
            "white diffuse shortcut on stainless body",
            "visible polygon material-zone triangles",
            "non-runtime material experiment",
        ],
        "material negative boundary drifted",
    )

    expectations = authority["release_expectations"]
    surface = authority["commercial_surface_integrity"]
    require(surface["sole_runtime_material_authority"] is True, "material authority must be sole runtime material authority")
    require(surface["material_lighting_separation_required"] is True, "material/lighting separation must be required")
    require(surface["body_must_not_be_lightened_by_white_diffuse_shortcut"] is True, "body white diffuse shortcut boundary drifted")
    require(
        surface["visual_priority_order"][:2] == ["polished ball core", "continuous cast stainless body"],
        "material visual priority order drifted",
    )
    require(expectations["metallic_roughness_workflow_required"] is True, "metallic-roughness release expectation drifted")
    require(expectations["commercial_clean_micro_surface_required"] is True, "clean micro-surface release expectation drifted")
    require(expectations["material_lighting_separation_required"] is True, "material/lighting release expectation drifted")
    require(
        surface["product_facing_polygon_material_hard_edges_visible_allowed"] is False,
        "material authority allowed product-facing hard zone edges",
    )
    require(surface["polygon_zone_triangles_visible_allowed"] is False, "material authority allowed polygon-zone triangles")
    require(surface["dirty_blotch_highlights_visible_allowed"] is False, "material authority allowed dirty blotch highlights")

    material = lookdev["materialDirection"]
    require(material["productMaterialTruth"] == state["body_material_truth"], "lookdev material truth does not match authority")
    require(material["commercialMaterialProfile"] == state["material_profile"], "lookdev commercial material profile mismatch")
    require(material["whiteDiffuseShortcut"] is expectations["stainless_white_diffuse_shortcut_allowed"], "white diffuse shortcut boundary drifted")
    require(material["cleanPbr"] is expectations["clean_pbr"], "lookdev clean PBR flag drifted")
    require(material["explicitScratchGeometryVisible"] is expectations["explicit_scratch_geometry_visible"], "scratch geometry boundary drifted")
    require(material["dirtyBlotchNoiseVisible"] is expectations["dirty_blotch_noise_visible"], "dirty blotch boundary drifted")
    require(material["dirtyBlotchHighlightsVisible"] is expectations["dirty_blotch_highlights_visible"], "dirty blotch highlight boundary drifted")
    require(material["polygonZoneArtifactsVisible"] is expectations["polygon_zone_artifacts_visible"], "polygon-zone artifact boundary drifted")
    require(
        material["productFacingMaterialHardEdgesVisible"] is expectations["product_facing_material_hard_edges_visible"],
        "product-facing material hard-edge boundary drifted",
    )
    require(material["nonRuntimeMaterialSourceUsed"] is expectations["non_runtime_material_source_used"], "lookdev used a non-runtime material source")
    require(material["commercialBodyAssignmentPolicy"] == expectations["commercial_body_assignment_policy"], "commercial body assignment policy drifted")
    require(material["bodyZoneCount"] == expectations["commercial_body_zone_count"], "commercial body zone count drifted")
    require(
        "materialParameterSnapshot" in material,
        "material parameter snapshot missing from lookdev",
    )
    snapshot = material["materialParameterSnapshot"]
    require(isinstance(snapshot, dict), "material parameter snapshot must be an object")
    family = snapshot.get("familyMaterials", {})
    require(isinstance(family, dict), "family material snapshot must be an object")

    envelope = authority["commercial_pbr_envelope"]["roles"]
    cast_authority = envelope["cast-satin-body"]
    cast_family = family.get("castBlastedStainless")
    require(isinstance(cast_family, dict), "cast body family material snapshot missing")
    require_color_inside(cast_family["base_color"], cast_authority["base_color_range"], "cast body family base_color")
    require(max(require_vector(cast_family["base_color"], "cast body family base_color")[:3]) <= expectations["dominant_body_base_color_max_component"], "cast body family base color is too white")
    low, high = require_range(cast_authority["roughness_range"], "cast body roughness authority")
    require_number_between(cast_family["roughness"], low, high, "cast body family roughness")
    low, high = require_range(cast_authority["anisotropic_range"], "cast body anisotropic authority")
    require_number_between(cast_family["anisotropic"], low, high, "cast body family anisotropic")

    cast_zone = find_zone_material(snapshot, "commercial-continuous-cast-satin-body")
    require_color_inside(cast_zone["base_color"], cast_authority["base_color_range"], "dominant cast body zone base_color")
    require(max(require_vector(cast_zone["base_color"], "dominant cast body zone base_color")[:3]) <= expectations["dominant_body_base_color_max_component"], "dominant body zone base color is too white")
    require_number_between(
        cast_zone["roughness"],
        expectations["dominant_body_roughness_min"],
        expectations["dominant_body_roughness_max"],
        "dominant body zone roughness",
    )
    micro = cast_authority["micro_variation"]
    require(float(cast_zone.get("bump", 0.0)) <= micro["bump_strength_max"], "dominant body bump too strong")
    require(float(cast_zone.get("bump_distance", 0.0)) <= micro["bump_distance_max"], "dominant body bump distance too high")

    ball_authority = envelope["polished-stainless-ball"]
    ball = family.get("polishedStainlessBall")
    require(isinstance(ball, dict), "polished ball material snapshot missing")
    require_color_inside(ball["base_color"], ball_authority["base_color_range"], "polished ball base_color")
    require_number_between(
        material["polishedBallRoughness"],
        expectations["polished_ball_roughness_min"],
        expectations["polished_ball_roughness_max"],
        "polished ball roughness",
    )
    require_number_between(
        ball["roughness"],
        expectations["polished_ball_roughness_min"],
        expectations["polished_ball_roughness_max"],
        "polished ball material roughness",
    )


def validate_lighting(authority: dict[str, Any], lookdev: dict[str, Any], release: dict[str, Any], lookdev_binding_current: bool) -> None:
    state = authority["lighting_state"]
    policy = authority["reflection_policy"]
    subject_policy = authority["subject_light_policy"]
    background_policy = authority["background_policy"]
    ray_visibility = authority["ray_visibility_requirements"]
    lighting = lookdev["lighting"]
    require(state["background_mode"] == "high-key-white-studio", "authority lighting background drifted")
    require(
        state["lighting_separation_model"] == "background-subject-reflection-contamination-separated",
        "lighting separation model drifted",
    )
    require(state["background_subject_lighting_separation_required"] is True, "background and subject lighting must be separated")
    require(state["large_apparent_source_required"] is True, "large apparent source requirement drifted")
    require(state["far_distance_requires_larger_source_or_diffusion"] is True, "far soft source policy drifted")
    require(state["background_as_primary_subject_light_allowed"] is False, "background became allowed as subject key")
    require(state["white_world_primary_exposure_allowed"] is False, "white world became allowed as primary exposure")
    require(subject_policy["background_as_primary_subject_light_allowed"] is False, "subject policy allowed background-as-key")
    require(subject_policy["white_world_as_main_exposure_allowed"] is False, "subject policy allowed world-as-main")
    require(subject_policy["direct_parallel_flat_wash_allowed"] is False, "subject policy allowed flat front wash")
    require(subject_policy["overbright_background_spill_allowed"] is False, "subject policy allowed background spill washout")
    require(subject_policy["subject_and_background_lights_must_be_tunable_independently"] is True, "subject/background tunability drifted")
    require(background_policy["white_background_required"] is True, "white background requirement drifted")
    require(background_policy["background_primary_light_allowed"] is False, "background policy allowed primary subject light")
    require(background_policy["background_spill_must_not_wash_subject"] is True, "background spill washout boundary drifted")
    require(background_policy["dark_or_black_dominant_stage_allowed"] is False, "dark stage became allowed")
    require(lighting["backgroundMode"] == state["background_mode"], "lookdev lighting background mismatch")
    require(lighting["visibleLightPanelsInCamera"] is policy["visible_light_panels_in_camera"], "light panels became camera-visible")

    required_roles = {item["role"] for item in authority["roles"]}
    require(set(lighting["roles"]) == required_roles, "lookdev lighting roles do not match authority")
    far_lights = [item for item in lighting["rig"] if item["role"] != "ambient-white-studio"]
    require(all(item["size"] >= state["minimum_far_light_size"] for item in far_lights), "far soft light size drifted")
    require(all(item["distanceClass"] == state["source_distance_class"] for item in far_lights), "light distance class drifted")

    require(policy["driver_light_glossy_readable_allowed"] is False, "approved runtime must not allow driver-light glossy pollution")
    require(policy["black_flags_glossy_readable_allowed"] is False, "approved runtime must not allow black-flag glossy pollution")
    require(policy["reflection_cards_glossy_readable_allowed"] is False, "approved runtime must not allow reflection-card glossy pollution")
    require(policy["glossy_equipment_reflection_allowed"] is False, "approved runtime must not allow glossy equipment reflection")
    require(policy["hard_white_blotch_reflection_allowed"] is False, "approved runtime must not allow hard white blotch reflection")
    require(policy["product_part_glossy_reflection_on_polished_ball_allowed"] is False, "approved runtime must not allow product-part ball reflections")
    require(policy["readable_left_right_body_reflection_on_polished_ball_allowed"] is False, "approved runtime must not allow body reflections on ball")
    require(policy["readable_seat_stem_fastener_reflection_on_polished_ball_allowed"] is False, "approved runtime must not allow seat/stem/fastener ball reflections")
    require(policy["non_ball_product_parts_glossy_visible_to_ball_allowed"] is False, "approved runtime must isolate non-ball product glossy visibility")
    require_terms(
        policy["polished_ball_allowed_reflection_sources"],
        ["continuous white-silver environment", "soft studio gradient", "own bore and edge depth"],
        "polished ball allowed reflection source boundary drifted",
    )
    require(ray_visibility["driver_lights"]["visible_camera"] is False, "driver lights became camera-visible in ray policy")
    require(ray_visibility["driver_lights"]["visible_glossy"] is False, "driver lights became glossy-visible in ray policy")
    require(ray_visibility["continuous_reflection_environment"]["visible_camera"] is False, "reflection environment became camera-visible")
    require(ray_visibility["continuous_reflection_environment"]["visible_glossy"] is True, "reflection environment must remain glossy-visible")
    require(ray_visibility["non_ball_product_parts"]["visible_camera"] is True, "non-ball product parts must remain camera-visible")
    require(ray_visibility["non_ball_product_parts"]["visible_diffuse_and_shadow"] is True, "non-ball product parts must keep diffuse/shadow visibility")
    require(ray_visibility["non_ball_product_parts"]["visible_glossy_to_polished_ball"] is False, "non-ball product parts must not reflect on polished ball")
    require(ray_visibility["polished_ball_core"]["visible_camera"] is True, "polished ball must remain camera-visible")
    require(ray_visibility["polished_ball_core"]["visible_glossy"] is True, "polished ball must remain glossy-capable")
    require(lighting["glossyEquipmentReflectionAllowed"] is policy["glossy_equipment_reflection_allowed"], "lookdev glossy equipment policy drifted")
    require(lighting["reflectionCardsGlossyReadableAllowed"] is policy["reflection_cards_glossy_readable_allowed"], "lookdev reflection-card glossy policy drifted")
    require(lighting["hardWhiteBlotchReflectionAllowed"] is policy["hard_white_blotch_reflection_allowed"], "lookdev hard white blotch policy drifted")
    gradient = lighting.get("reflectionGradientEnvironment")
    require(isinstance(gradient, dict), "lookdev must declare the continuous reflection gradient environment")
    require(gradient.get("type") == "non-equipment-gradient-dome", "reflection gradient environment type drifted")
    require(gradient.get("visibleCamera") is False, "reflection gradient must not become camera-visible equipment")
    require(gradient.get("visibleGlossy") is True, "reflection gradient must remain available to glossy metal")
    require(gradient.get("continuousGradient") is True, "reflection gradient must remain continuous")
    require(gradient.get("equipmentReadable") is False, "reflection gradient became readable equipment")
    require(gradient.get("hardPanelShapeVisible") is False, "reflection gradient became a hard panel shape")
    retouch = lighting.get("productGlossyReflectionRetouch")
    require(isinstance(retouch, dict), "lookdev must declare product glossy reflection retouch")
    if lookdev_binding_current:
        require(
            retouch.get("policy") == "commercial-polished-ball-all-non-ball-product-reflection-isolation",
            "current lookdev must isolate all non-ball product reflections from polished ball",
        )
        suppressed_groups = set(retouch.get("suppressedGroups", []))
        require(
            {"fastenersSmallHardware", "bodyPressureShell", "seatSealSystem", "stemPackingDrive"}.issubset(suppressed_groups),
            "current lookdev product reflection isolation group set is incomplete",
        )
    else:
        require(
            retouch.get("policy") == "commercial-polished-ball-clean-reflection",
            "stale lookdev baseline glossy retouch policy drifted",
        )
        require(retouch.get("suppressedGroup") == "fastenersSmallHardware", "stale lookdev small hardware glossy retouch group drifted")
        require(retouch.get("suppressedCount", 0) >= 100, "stale lookdev small hardware glossy suppression count drifted")
    require(retouch.get("visibleInCamera") is True, "small hardware must remain camera-visible")
    require(retouch.get("visibleInGlossy") is False, "small hardware must not remain glossy-visible")
    require(
        all(item.get("visibleGlossy") is False for item in lighting["whiteStudioCards"]),
        "white studio cards must not be readable in glossy reflections",
    )
    require(
        all(item.get("visibleGlossy") is False for item in lighting["blackFlags"]),
        "black flags must not be readable in glossy reflections",
    )
    require(
        all(item.get("visibleGlossy") is False for item in far_lights),
        "driver lights must not be readable in glossy reflections",
    )
    require(
        release["approval_state"]["approved_for_240_frame_render"] is False,
        "release gate must block 240-frame render until reflection correction is approved",
    )


def validate_camera(authority: dict[str, Any], lookdev: dict[str, Any], camera_previs: dict[str, Any], lookdev_binding_current: bool) -> None:
    timeline = authority["timeline_state"]
    composition = authority["composition_state"]
    phases = [item["phase"] for item in authority["camera_phase_policy"]]
    require(phases == EXPECTED_SHOTS, "camera phase policy drifted")
    require(camera_previs["fps"] == timeline["fps"], "camera fps mismatch")
    require(camera_previs["totalFrames"] == timeline["total_frames"], "camera total frame count mismatch")
    require(camera_previs["durationSeconds"] == timeline["duration_seconds"], "camera duration mismatch")
    require(camera_previs["maxAbsRollDegrees"] <= timeline["max_abs_roll_degrees"], "camera roll envelope drifted")
    require(composition["close_crop_allowed"] is False, "camera authority allowed close crop")
    require(composition["hero_light_or_panel_crop_allowed"] is False, "camera authority allowed light/panel crop")
    require(composition["ball_core_priority_during_mid_story"] is True, "camera ball-core priority drifted")
    require(composition["cutaway_visibility_required_after_assembly"] is True, "camera cutaway visibility requirement drifted")
    require(composition["clear_water_flow_visibility_required_at_end"] is True, "camera flow visibility requirement drifted")
    if not lookdev_binding_current:
        return
    camera = lookdev["cameraDirection"]
    require(camera["distanceMultiplier"] >= composition["distance_multiplier_min"], "camera distance multiplier below authority")
    require(camera["fovMultiplier"] <= composition["fov_multiplier_max"], "camera fov multiplier exceeds authority")
    require(camera["visibleLightPanelsInCamera"] is composition["visible_light_panels_in_camera"], "camera sees light panels")


def validate_motion(authority: dict[str, Any], lookdev: dict[str, Any], motion_control: dict[str, Any], lookdev_binding_current: bool) -> None:
    channels = authority["channels"]
    require(set(channels) == EXPECTED_CHANNELS, "authority motion channel set drifted")
    route = authority["route_policy"]
    initial = authority["initial_exploded_requirements"]
    require(route["initial_state"] == "fully exploded", "motion initial state drifted")
    require(route["initial_assembled_state_allowed"] is False, "motion route allowed assembled first frame")
    require(route["explode_then_reassemble_loop_allowed"] is False, "motion route allowed round trip")
    require(route["primary_motion"] == "one-way precision assembly", "motion primary route drifted")
    require(route["cutaway_after_assembly_required"] is True, "cutaway timing requirement drifted")
    require(route["clear_water_flow_after_cutaway_required"] is True, "clear-water timing requirement drifted")
    require(all(initial.values()), "initial exploded component requirements must all remain true")
    require(channels["ballPresentationTurn"]["degrees"] >= 90, "ball presentation turn is too small")
    if not lookdev_binding_current:
        return
    require(set(motion_control["partChannels"]) == EXPECTED_CHANNELS, "motion-control channel set drifted")
    for channel, expected in channels.items():
        current = motion_control["partChannels"][channel]
        require(current.get("from") == expected.get("from"), f"{channel} source sampler drifted")
        if "multiplier" in expected:
            require(current.get("multiplier") == expected["multiplier"], f"{channel} multiplier drifted")
        if "degrees" in expected:
            require(current.get("degrees") == expected["degrees"], f"{channel} degrees drifted")

    motion = lookdev["motionFusion"]
    thresholds = authority["proof_thresholds"]
    require(set(motion["controlledChannels"]) == EXPECTED_CHANNELS, "lookdev motion channel set drifted")
    require(motion["maxOffset"] > thresholds["max_offset_min"], "lookdev motion offset too low")
    require(motion["maxBallAngleDegrees"] > thresholds["max_ball_angle_degrees_min"], "lookdev ball turn too low")


def validate_storyboard(authority: dict[str, Any], camera_previs: dict[str, Any], lookdev_binding_current: bool) -> None:
    shot_ids = [shot["shot_id"] for shot in authority["shot_order"]]
    require(shot_ids == EXPECTED_SHOTS, "authority storyboard shot order drifted")
    rhythm = authority["story_rhythm_policy"]
    require(rhythm["single_primary_motion"] == "assembly", "storyboard primary motion drifted")
    require(rhythm["opening_explosion_motion_allowed"] is False, "storyboard allowed opening explosion motion")
    require(rhythm["maximum_major_story_events"] == 5, "storyboard event count drifted")
    require_terms(
        authority.get("forbidden", []),
        ["random CAD explosion", "explode then reassemble", "opaque liquid", "unsupported pressure"],
        "storyboard negative boundary drifted",
    )
    if not lookdev_binding_current:
        return
    require([item["shotId"] for item in camera_previs["shotBoundaries"]] == EXPECTED_SHOTS, "camera shot boundary order drifted")


def validate_release_gate(authority: dict[str, Any]) -> None:
    approval = authority["approval_state"]
    runtime_policy = authority["runtime_authority_policy"]
    require(runtime_policy["sole_current_hero_render_authority"] is True, "runtime must remain the sole current hero render authority")
    require(runtime_policy["render_manifest_authority_binding_required"] is True, "runtime manifest binding must be required")
    require(runtime_policy["non_runtime_render_authority_allowed"] is False, "non-runtime render authority must be forbidden")
    require(runtime_policy["runtime_authority_files_must_be_hashed"] is True, "runtime authority hashes must be required")
    require_terms(
        authority.get("required_before_release", []),
        [
            "render manifest declares hero-runtime",
            "no non-runtime material experiment",
            "no product-facing polygon material-zone artifacts",
            "white background is proven",
            "polished ball is proven free",
            "material is proven",
            "camera is proven",
            "motion is proven",
            "storyboard is proven",
        ],
        "release gate runtime authority requirements drifted",
    )
    evidence = authority.get("lookdev_evidence_state")
    require(isinstance(evidence, dict), "release gate must declare lookdev evidence state")
    require(evidence["current_visual_approval"] is False, "current visual approval must remain false")
    require(evidence["current_authority_lookdev_revalidation_required"] is True, "current authority lookdev revalidation must be required")
    require(set(evidence["runtime_revalidation_scope"]) == REVALIDATION_SCOPE, "runtime revalidation scope drifted")
    require(
        evidence["stale_lookdev_binding_allowed_only_while_release_blocked"] is True,
        "stale lookdev binding must only be allowed while release is blocked",
    )
    require(approval["approved_for_240_frame_render"] is False, "runtime must not be approved for 240-frame render yet")
    require(approval["approved_for_homepage_replacement"] is False, "runtime must not be approved for homepage replacement yet")
    require(approval["approved_for_pages_publication"] is False, "runtime must not be approved for Pages publication yet")
    unknowns = authority["controlled_unknowns"]
    required_unknowns = {
        "unresolved-reflection-contamination-policy",
        "unresolved-background-as-primary-light",
        "unresolved-product-part-reflection-contamination",
        "unresolved-lighting-lookdev-revalidation",
        "unresolved-material-lookdev-revalidation",
        "unresolved-camera-lookdev-revalidation",
        "unresolved-motion-route-revalidation",
        "unresolved-storyboard-delivery-revalidation",
    }
    require({item["control_id"] for item in unknowns} == required_unknowns, "release gate controlled unknowns drifted")
    for unknown in unknowns:
        require(unknown["status"] == "open", f"{unknown['control_id']} must remain open")
        require("approved_for_240_frame_render" in unknown["blocks"], f"{unknown['control_id']} must block 240-frame render")
    require(
        authority["next_required_milestone"] == "evidence-calibrated-runtime-lookdev",
        "next milestone drifted",
    )


def main() -> int:
    files = load_authority_folder()
    validate_folder_shape(files)

    lookdev = read_json(LOOKDEV)
    motion_control = read_json(MOTION_CONTROL)
    camera_previs = read_json(CAMERA_PREVIS)

    lookdev_binding_current = validate_runtime_authority_binding(files, lookdev, files["release-gate.json"])
    validate_material(files["material.json"], lookdev)
    validate_lighting(files["lighting.json"], lookdev, files["release-gate.json"], lookdev_binding_current)
    validate_camera(files["camera.json"], lookdev, camera_previs, lookdev_binding_current)
    validate_motion(files["motion.json"], lookdev, motion_control, lookdev_binding_current)
    validate_storyboard(files["storyboard.json"], camera_previs, lookdev_binding_current)
    validate_release_gate(files["release-gate.json"])

    print("PASS: fixed-ball-valve hero-runtime authority folder is self-contained and blocks 240-frame delivery until reflection lookdev is approved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
