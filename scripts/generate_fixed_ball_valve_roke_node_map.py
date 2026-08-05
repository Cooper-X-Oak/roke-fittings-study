#!/usr/bin/env python3
"""Generate the fixed-ball-valve STEP-to-GLB node map for the green hero."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPECTED_STEP_SHA256 = "3ddb291607730239f5a067e9d1730acda0931874c5f42c4ac0c358516efa2547"
EXPECTED_GLB_SHA256 = "89024869647b3aaf3fe5301694a2753dc87e9dd3d05b41b9c651ef4e9754384b"
EXPECTED_MESH_NODE_COUNT = 138


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--step", default="asset/derived/fixed-ball-valve/source/固定式球阀.STEP")
    parser.add_argument("--glb", default="outcome/public/assets/models/fixed-ball-valve.glb")
    parser.add_argument("--inspection", default="asset/derived/fixed-ball-valve/model-inspection.json")
    parser.add_argument("--out", default="outcome/src/assets-manifest/fixed-ball-valve-roke-green-node-map.json")
    return parser.parse_args()


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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def read_step_text(path: Path) -> tuple[str, str]:
    for encoding in ("gb18030", "utf-8"):
        try:
            return path.read_text(encoding=encoding), encoding
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"Could not read STEP as gb18030 or UTF-8: {path}")


def parse_step_instances(text: str) -> dict[str, Any]:
    product_rows = re.findall(
        r"#(\d+)\s*=\s*PRODUCT\s*\(\s*'((?:''|[^'])*)'",
        text,
        flags=re.IGNORECASE,
    )
    formation_rows = re.findall(
        r"#(\d+)\s*=\s*PRODUCT_DEFINITION_FORMATION(?:_WITH_SPECIFIED_SOURCE)?\s*"
        r"\([^;]*?#(\d+)\s*(?:,|\))",
        text,
        flags=re.IGNORECASE,
    )
    definition_rows = re.findall(
        r"#(\d+)\s*=\s*PRODUCT_DEFINITION\s*\([^;]*?#(\d+)\s*,\s*#(\d+)\s*\)",
        text,
        flags=re.IGNORECASE,
    )
    usage_rows = re.findall(
        r"#(\d+)\s*=\s*NEXT_ASSEMBLY_USAGE_OCCURRENCE\s*"
        r"\(\s*'([^']*)'\s*,\s*'[^']*'\s*,\s*'[^']*'\s*,\s*#(\d+)\s*,\s*#(\d+)\s*,",
        text,
        flags=re.IGNORECASE,
    )

    product_by_id = {row_id: name.replace("''", "'").strip() for row_id, name in product_rows}
    product_by_formation = {
        formation_id: product_by_id.get(product_id)
        for formation_id, product_id in formation_rows
    }
    product_by_definition = {
        definition_id: product_by_formation.get(formation_id)
        for definition_id, formation_id, _context_id in definition_rows
    }

    instances: list[dict[str, Any]] = []
    for ordinal, (usage_id, usage_name, parent_definition, child_definition) in enumerate(usage_rows):
        product_name = product_by_definition.get(child_definition)
        instances.append(
            {
                "assemblyOrdinal": ordinal,
                "usageEntity": f"#{usage_id}",
                "usageName": usage_name,
                "parentProductDefinition": f"#{parent_definition}",
                "childProductDefinition": f"#{child_definition}",
                "productName": product_name,
            }
        )

    require(len(product_rows) > 0, "STEP has no PRODUCT rows")
    require(len(formation_rows) > 0, "STEP has no PRODUCT_DEFINITION_FORMATION rows")
    require(len(definition_rows) > 0, "STEP has no PRODUCT_DEFINITION rows")
    require(len(instances) == EXPECTED_MESH_NODE_COUNT, f"Expected 138 STEP assembly instances, got {len(instances)}")
    missing = [item for item in instances if not item["productName"]]
    require(not missing, f"STEP assembly instances could not be resolved to products: {missing[:3]}")

    return {
        "entityCounts": {
            "product": len(product_rows),
            "productDefinitionFormation": len(formation_rows),
            "productDefinition": len(definition_rows),
            "nextAssemblyUsageOccurrence": len(instances),
        },
        "instances": instances,
    }


def classify_group(product_name: str, node_index: int, center: list[float]) -> str:
    lower = product_name.lower()
    if product_name in {"阀体", "堵头"}:
        return "central-body-anchor"
    if product_name == "阀盖":
        return "end-caps-covers"
    if product_name in {"球体", "固定轴", "球体轴承", "固定轴轴承", "固定轴垫片"}:
        return "ball-trunnion-core"
    if product_name in {"阀座", "阀座密封圈", "阀座压圈", "阀座盘根", "中道垫片"}:
        return "seat-seal-system"
    if product_name in {"阀杆", "填料", "填料压盖", "填料压圈", "填料箱", "填料箱垫片", "阀杆轴承", "止推垫"}:
        return "stem-packing-stack"
    if product_name in {"支架", "连接轴", "平键"}:
        return "top-bracket-connector"
    if "支架螺柱" in product_name:
        return "top-bracket-fasteners"
    fastener_terms = ("螺柱", "螺母", "螺栓", "垫片", "弹簧", "screw", "stud", "nut", "washer", "pin", "bolt")
    if any(term in lower or term in product_name for term in fastener_terms):
        return "fasteners-small-hardware"
    if center[1] > 0.14 or node_index >= 107:
        return "top-bracket-connector"
    return "end-caps-covers"


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    step_path = project_path(repo_root, args.step)
    glb_path = project_path(repo_root, args.glb)
    inspection_path = project_path(repo_root, args.inspection)
    out_path = project_path(repo_root, args.out)

    require(step_path.is_file(), f"STEP source is missing: {step_path}")
    require(glb_path.is_file(), f"GLB source is missing: {glb_path}")
    require(inspection_path.is_file(), f"GLB inspection file is missing: {inspection_path}")
    require(sha256(step_path) == EXPECTED_STEP_SHA256, "Fixed ball valve STEP hash drifted")
    require(sha256(glb_path) == EXPECTED_GLB_SHA256, "Fixed ball valve GLB hash drifted")

    inspection = read_json(inspection_path)
    counts = inspection.get("counts", {})
    capability = inspection.get("capability", {})
    require(counts.get("nodes") == 140, f"GLB node count expected 140, got {counts.get('nodes')!r}")
    require(counts.get("meshNodes") == EXPECTED_MESH_NODE_COUNT, "GLB mesh node count drifted")
    require(counts.get("meshes") == EXPECTED_MESH_NODE_COUNT, "GLB mesh count drifted")
    require(counts.get("triangles") == 559104, "GLB triangle count drifted")
    require(capability.get("capability") == "structured-named-parts", "GLB capability is not structured-named-parts")

    step_text, step_encoding = read_step_text(step_path)
    step_parse = parse_step_instances(step_text)
    part_candidates = sorted(inspection.get("partCandidates", []), key=lambda item: item["nodeIndex"])
    require(len(part_candidates) == EXPECTED_MESH_NODE_COUNT, "Inspection part candidate count drifted")

    records: list[dict[str, Any]] = []
    for instance, candidate in zip(step_parse["instances"], part_candidates):
        bounds = candidate.get("bounds", {})
        center = bounds.get("center", [0, 0, 0])
        product_name = instance["productName"]
        side = "center"
        if center[1] < -0.015:
            side = "front"
        elif center[1] > 0.12:
            side = "rear"
        records.append(
            {
                **instance,
                "nodeIndex": int(candidate["nodeIndex"]),
                "meshIndex": int(candidate["meshIndex"]),
                "glbNodeName": candidate["name"],
                "glbNodePath": candidate["path"],
                "triangleCount": int(candidate["triangleCount"]),
                "bounds": bounds,
                "animationGroup": classify_group(product_name, int(candidate["nodeIndex"]), center),
                "side": side,
            }
        )

    name_counts = Counter(record["productName"] for record in records)
    required_parts = ["球体", "阀座", "阀盖", "阀体", "阀杆", "支架"]
    for part in required_parts:
        require(name_counts[part] > 0, f"Required STEP part missing from mapping: {part}")
    fastener_count = sum(
        count
        for name, count in name_counts.items()
        if any(term in name.lower() or term in name for term in ("螺柱", "螺母", "螺栓", "screw", "stud", "nut", "washer"))
    )
    require(fastener_count >= 30, f"Expected grouped fastener coverage, got {fastener_count}")

    groups: dict[str, dict[str, Any]] = {}
    for record in records:
        group = groups.setdefault(record["animationGroup"], {"groupId": record["animationGroup"], "nodeIndices": [], "productNames": [], "triangleCount": 0})
        group["nodeIndices"].append(record["nodeIndex"])
        if record["productName"] not in group["productNames"]:
            group["productNames"].append(record["productName"])
        group["triangleCount"] += record["triangleCount"]

    manifest = {
        "schema": "ztovalve-fixed-ball-valve-roke-green-node-map/v1",
        "kind": "step_to_glb_node_map",
        "bundleId": "roke-green-commercial-240",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "sources": {
            "step": {"path": project_rel(repo_root, step_path), "sha256": EXPECTED_STEP_SHA256, "encodingUsed": step_encoding},
            "glb": {"path": project_rel(repo_root, glb_path), "sha256": EXPECTED_GLB_SHA256},
            "inspection": project_rel(repo_root, inspection_path),
        },
        "counts": {**step_parse["entityCounts"], "meshNodeCount": EXPECTED_MESH_NODE_COUNT, "mappedRecordCount": len(records), "uniqueProductNames": len(name_counts)},
        "validation": {
            "requiredChinesePartsPresent": required_parts,
            "fastenerLikeInstanceCount": fastener_count,
            "nodeOrderPolicy": "Records map STEP assembly occurrence order to GLB mesh-bearing node order from model-inspection.json.",
            "quarterTurnPolicy": "No 90-degree ball-core function claim is made by this map.",
        },
        "groups": sorted(groups.values(), key=lambda item: item["groupId"]),
        "records": records,
    }
    write_json(out_path, manifest)
    print(json.dumps({"status": "pass", "out": project_rel(repo_root, out_path), "records": len(records)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
