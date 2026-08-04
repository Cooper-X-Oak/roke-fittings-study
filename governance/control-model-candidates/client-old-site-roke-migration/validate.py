#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT_ID = "client-old-site-roke-migration"
SUPPORTED_CONTROL_IDS = [
    "reference-style-ownership-boundary",
    "legacy-site-inventory-before-bulk-migration",
    "template-mapping-first-delivery-slice",
    "unresolved-client-source-package",
    "unresolved-dynamic-feature-scope",
    "unresolved-deployment-path-scope",
]


def emit(value: dict[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def root_path() -> Path:
    return Path(__file__).resolve().with_name("control-root.json")


def load_root() -> dict[str, Any]:
    return json.loads(root_path().read_text(encoding="utf-8"))


def walk_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for node in nodes:
        result.append(node)
        children = node.get("children", [])
        if isinstance(children, list):
            result.extend(walk_nodes(children))
    return result


def required_nodes(root: dict[str, Any]) -> dict[str, dict[str, Any]]:
    nodes = walk_nodes(root.get("nodes", []))
    return {
        node["control_id"]: node
        for node in nodes
        if node.get("validator_required") is True
        and node.get("node_role") in {"control", "controlled_unknown"}
        and isinstance(node.get("control_id"), str)
    }


def describe() -> int:
    emit(
        {
            "schema": "control-model-validator-describe/v0",
            "kind": "control_root_validator",
            "validator_id": f"{ROOT_ID}-validator",
            "root_id": ROOT_ID,
            "supported_control_ids": SUPPORTED_CONTROL_IDS,
        }
    )
    return 0


def pass_if(condition: bool, control_id: str, message: str) -> dict[str, str]:
    return {
        "control_id": control_id,
        "status": "pass" if condition else "fail",
        "message": message,
    }


def contains_all(
    nodes: dict[str, dict[str, Any]],
    control_id: str,
    field: str,
    terms: list[str],
) -> bool:
    value = nodes.get(control_id, {}).get(field, "")
    return isinstance(value, str) and all(term in value for term in terms)


def check() -> int:
    root = load_root()
    nodes = required_nodes(root)
    node_ids = set()
    for node in walk_nodes(root.get("nodes", [])):
        node_id = node.get("id")
        if isinstance(node_id, str):
            node_ids.add(node_id)

    graph_edges_ok = all(
        edge.get("from") in node_ids and edge.get("to") in node_ids
        for edge in root.get("edges", [])
    )
    control_ids_ok = set(nodes) == set(SUPPORTED_CONTROL_IDS)
    base_ok = (
        root.get("schema") == "control-model-root/v0"
        and root.get("kind") == "control_root"
        and root.get("authority_status") == "candidate"
        and root.get("root_id") == ROOT_ID
        and root.get("validator", {}).get("path") == "validate.py"
        and control_ids_ok
        and graph_edges_ok
    )

    results = [
        pass_if(
            base_ok
            and contains_all(
                nodes,
                "reference-style-ownership-boundary",
                "statement",
                ["ROKE", "授权"],
            )
            and contains_all(
                nodes,
                "reference-style-ownership-boundary",
                "boundary",
                ["商用"],
            ),
            "reference-style-ownership-boundary",
            "已声明 ROKE 仅作风格参考，客户商用内容必须使用自有或授权资产。",
        ),
        pass_if(
            base_ok
            and contains_all(
                nodes,
                "legacy-site-inventory-before-bulk-migration",
                "statement",
                ["清单", "URL"],
            ),
            "legacy-site-inventory-before-bulk-migration",
            "已要求批量迁移前完成旧站内容、产品、资料、表单、SEO 与 URL 映射清单。",
        ),
        pass_if(
            base_ok
            and contains_all(
                nodes,
                "template-mapping-first-delivery-slice",
                "statement",
                ["首页", "产品目录"],
            ),
            "template-mapping-first-delivery-slice",
            "已限定先做首批模板映射样板，再扩展到全站迁移。",
        ),
        pass_if(
            base_ok
            and contains_all(
                nodes,
                "unresolved-client-source-package",
                "statement",
                ["尚未登记"],
            )
            and contains_all(
                nodes,
                "unresolved-client-source-package",
                "boundary",
                ["上线内容"],
            ),
            "unresolved-client-source-package",
            "已登记客户旧站、源码包、品牌素材、产品资料与授权边界仍未解决。",
        ),
        pass_if(
            base_ok
            and contains_all(
                nodes,
                "unresolved-dynamic-feature-scope",
                "statement",
                ["表单", "静态"],
            ),
            "unresolved-dynamic-feature-scope",
            "已登记动态功能范围会决定静态站是否足够。",
        ),
        pass_if(
            base_ok
            and contains_all(
                nodes,
                "unresolved-deployment-path-scope",
                "statement",
                ["/roke-fittings-study", "部署"],
            ),
            "unresolved-deployment-path-scope",
            "已登记目标域名、路径前缀和托管平台仍未确认。",
        ),
    ]
    status = "pass" if all(item["status"] == "pass" for item in results) else "fail"
    emit(
        {
            "schema": "control-model-validator-result/v0",
            "kind": "control_root_validation_result",
            "root_id": ROOT_ID,
            "status": status,
            "results": results,
        }
    )
    return 0 if status == "pass" else 1


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in {"describe", "check"}:
        print("usage: validate.py describe|check", file=sys.stderr)
        return 2
    if argv[1] == "describe":
        return describe()
    return check()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
