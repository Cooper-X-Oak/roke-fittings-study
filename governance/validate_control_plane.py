#!/usr/bin/env python3
"""External fail-closed validation for this project's current governance pair."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


EXIT_DECISION = 20
EXIT_ENTRY = 21
EXIT_SPECIFICATION = 30
EXIT_ALIGNMENT = 31
EXIT_RELEASE = 40


def load(path: Path, label: str) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, [f"{label} is missing: {path}"]
    except (OSError, json.JSONDecodeError) as error:
        return None, [f"{label} is unreadable: {error}"]
    if not isinstance(value, dict):
        return None, [f"{label} must be a JSON object"]
    return value, []


def required_string(value: Any, name: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{name} must be a non-empty string")


def active_artifacts(
    project_root: Path, filename: str, kind: str
) -> list[Path]:
    matches: list[Path] = []
    for candidate in project_root.rglob(filename):
        try:
            value = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if (
            isinstance(value, dict)
            and value.get("kind") == kind
            and value.get("status") == "active"
        ):
            matches.append(candidate.resolve())
    return matches


def validate_rules(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version",
        "kind",
        "status",
        "ruleset_id",
        "ruleset_version",
        "business_gate",
        "rules",
    }
    if set(value) != required:
        errors.append("project rules must contain exactly the current control-plane fields")
    if value.get("schema_version") != 1 or value.get("kind") != "project_rules":
        errors.append("project rules schema or kind is invalid")
    if value.get("status") != "active":
        errors.append("project rules must be active; retired rules must leave the worktree")
    required_string(value.get("ruleset_id"), "ruleset_id", errors)
    required_string(value.get("ruleset_version"), "ruleset_version", errors)
    if value.get("business_gate") != {"development_entry_required": True}:
        errors.append("business_gate must require development entry")
    rules = value.get("rules")
    if not isinstance(rules, list) or not rules:
        errors.append("rules must be a non-empty current rule list")
        return errors
    seen: set[str] = set()
    for index, rule in enumerate(rules):
        prefix = f"rules[{index}]"
        if not isinstance(rule, dict) or set(rule) != {
            "id",
            "statement",
            "development_entry_ids",
        }:
            errors.append(
                f"{prefix} must contain only id, statement, development_entry_ids"
            )
            continue
        rule_id = rule.get("id")
        required_string(rule_id, f"{prefix}.id", errors)
        if isinstance(rule_id, str) and rule_id in seen:
            errors.append(f"duplicate current rule id: {rule_id}")
        if isinstance(rule_id, str):
            seen.add(rule_id)
        required_string(rule.get("statement"), f"{prefix}.statement", errors)
        entries = rule.get("development_entry_ids")
        if (
            not isinstance(entries, list)
            or not entries
            or any(
                not isinstance(item, str) or not item.strip() for item in entries
            )
        ):
            errors.append(
                f"{prefix}.development_entry_ids must be a non-empty string list"
            )
    return errors


def validate_validation(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version",
        "kind",
        "status",
        "ruleset_id",
        "ruleset_version",
        "validation_contract_version",
        "acceptance_gate",
        "checks",
    }
    if set(value) != required:
        errors.append(
            "project validation must contain exactly the current control-plane fields"
        )
    if value.get("schema_version") != 1 or value.get("kind") != "project_validation":
        errors.append("project validation schema or kind is invalid")
    if value.get("status") != "active":
        errors.append(
            "project validation must be active; retired validation must leave the worktree"
        )
    for key in ("ruleset_id", "ruleset_version", "validation_contract_version"):
        required_string(value.get(key), key, errors)
    if value.get("acceptance_gate") != {
        "development_acceptance_required": True
    }:
        errors.append("acceptance_gate must require development acceptance")
    checks = value.get("checks")
    if not isinstance(checks, list) or not checks:
        errors.append("checks must be a non-empty current validation list")
        return errors
    seen: set[str] = set()
    required_count = 0
    for index, check in enumerate(checks):
        prefix = f"checks[{index}]"
        if not isinstance(check, dict) or set(check) != {
            "id",
            "behavior_id",
            "required_for_current_contract",
            "command",
        }:
            errors.append(
                f"{prefix} must contain only id, behavior_id, "
                "required_for_current_contract, command"
            )
            continue
        check_id = check.get("id")
        required_string(check_id, f"{prefix}.id", errors)
        if isinstance(check_id, str) and check_id in seen:
            errors.append(f"duplicate current validation id: {check_id}")
        if isinstance(check_id, str):
            seen.add(check_id)
        required_string(check.get("behavior_id"), f"{prefix}.behavior_id", errors)
        required_string(check.get("command"), f"{prefix}.command", errors)
        if not isinstance(check.get("required_for_current_contract"), bool):
            errors.append(
                f"{prefix}.required_for_current_contract must be boolean"
            )
        elif check["required_for_current_contract"]:
            required_count += 1
    if required_count == 0:
        errors.append("at least one current acceptance check must be required")
    return errors


def validate_pair(
    rules_path: Path, validation_path: Path
) -> tuple[
    dict[str, Any] | None, dict[str, Any] | None, int, list[str]
]:
    rules_path = rules_path.resolve()
    validation_path = validation_path.resolve()
    project_root = Path(
        os.path.commonpath([rules_path.parent, validation_path.parent])
    ).parent
    current_rules = active_artifacts(
        project_root, "project-rules.json", "project_rules"
    )
    if current_rules != [rules_path]:
        return None, None, EXIT_DECISION, [
            "exactly one active project-rules.json must exist at the declared "
            f"path; found: {[str(path) for path in current_rules]}"
        ]
    current_validation = active_artifacts(
        project_root, "project-validation.json", "project_validation"
    )
    if current_validation != [validation_path]:
        return None, None, EXIT_SPECIFICATION, [
            "exactly one active project-validation.json must exist at the "
            f"declared path; found: {[str(path) for path in current_validation]}"
        ]
    rules, errors = load(rules_path, "project rules")
    if errors:
        return None, None, EXIT_DECISION, errors
    assert rules is not None
    errors = validate_rules(rules)
    if errors:
        return None, None, EXIT_DECISION, errors
    validation, errors = load(validation_path, "project validation")
    if errors:
        return rules, None, EXIT_SPECIFICATION, errors
    assert validation is not None
    errors = validate_validation(validation)
    if errors:
        return rules, None, EXIT_SPECIFICATION, errors
    if (
        rules["ruleset_id"],
        rules["ruleset_version"],
    ) != (
        validation["ruleset_id"],
        validation["ruleset_version"],
    ):
        return rules, validation, EXIT_ALIGNMENT, [
            "rules and validation must reference the same current ruleset id and version"
        ]
    return rules, validation, 0, []


def report(code: int, errors: list[str]) -> int:
    if code == 0:
        print("PASS: current project business and acceptance gates are aligned")
        return 0
    states = {
        EXIT_DECISION: "blocked_decision",
        EXIT_ENTRY: "blocked_decision",
        EXIT_SPECIFICATION: "blocked_specification",
        EXIT_ALIGNMENT: "blocked_specification",
        EXIT_RELEASE: "blocked_release",
    }
    print(f"FAIL: {states[code]}")
    for error in errors:
        print(f"- {error}")
    return code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("validate", "entry", "accept"))
    parser.add_argument("--rules", required=True, type=Path)
    parser.add_argument("--validation", required=True, type=Path)
    parser.add_argument("--entry-id")
    parser.add_argument("--run-checks", action="store_true")
    parser.add_argument("--workdir", type=Path, default=Path.cwd())
    args = parser.parse_args()

    rules, validation, code, errors = validate_pair(
        args.rules, args.validation
    )
    if code:
        return report(code, errors)
    assert rules is not None and validation is not None
    if args.mode == "entry":
        if not args.entry_id:
            return report(EXIT_ENTRY, ["entry requires --entry-id"])
        if not any(
            args.entry_id in rule["development_entry_ids"]
            for rule in rules["rules"]
        ):
            return report(
                EXIT_ENTRY,
                [f"entry id is not authorized by current rules: {args.entry_id}"],
            )
    if args.mode == "accept" and args.run_checks:
        workdir = args.workdir.resolve()
        for check in validation["checks"]:
            if not check["required_for_current_contract"]:
                continue
            result = subprocess.run(
                check["command"],
                shell=True,
                cwd=workdir,
                check=False,
            )
            if result.returncode:
                return report(
                    EXIT_RELEASE,
                    [f"required acceptance check failed: {check['id']}"],
                )
    return report(0, [])


if __name__ == "__main__":
    raise SystemExit(main())
