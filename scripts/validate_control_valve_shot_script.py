#!/usr/bin/env python3

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CREATIVE = ROOT / "creative" / "control-valve"
PLAN_PATH = CREATIVE / "creative-development.json"
SCRIPT_PATH = CREATIVE / "five-shot-script.md"
ROUTES_PATH = CREATIVE / "creative-routes.md"


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
script = SCRIPT_PATH.read_text(encoding="utf-8")
routes = ROUTES_PATH.read_text(encoding="utf-8")

if plan.get("selectedRouteId") != "command-becomes-precision":
    fail("the selected route must be command-becomes-precision")

shots = plan.get("shots", [])
expected_ids = [
    "actuator-origin",
    "axis-in-motion",
    "cascade-precision",
    "six-systems-one-axis",
    "complexity-resolved",
]
if [shot.get("id") for shot in shots] != expected_ids:
    fail("the plan must contain exactly the five released script shot IDs")

required_fields = {
    "narrativePurpose",
    "viewerTakeaway",
    "startState",
    "endState",
    "action",
    "activeComponents",
    "lighting",
    "layout",
    "transitionIn",
    "transitionOut",
    "rhythm",
    "hold",
    "camera",
    "truthConstraints",
    "content",
}
for shot in shots:
    missing = sorted(required_fields - shot.keys())
    if missing:
        fail(f"shot {shot.get('id')} misses fields: {', '.join(missing)}")
    if not shot["camera"].get("framing") or not shot["camera"].get("movement"):
        fail(f"shot {shot['id']} misses framing or camera movement")
    if len(shot["activeComponents"]) < 1:
        fail(f"shot {shot['id']} has no active component")
    if len(shot["truthConstraints"]) < 1:
        fail(f"shot {shot['id']} has no truth constraint")

ranges = [shot.get("range") for shot in shots]
if ranges[0][0] != 0 or ranges[-1][1] != 1:
    fail("shot ranges must cover the complete normalized timeline")
for left, right in zip(ranges, ranges[1:]):
    if left[1] != right[0]:
        fail("shot ranges must be ordered and gapless")

framings = {shot["camera"]["framing"] for shot in shots}
movements = {shot["camera"]["movement"] for shot in shots}
if len(framings) != 5 or len(movements) != 5:
    fail("all five shots need materially distinct framing and camera language")

phases = [entry.get("phase") for entry in plan.get("phaseHistory", [])]
if phases != ["case-research", "creative-routes", "five-shot-script"]:
    fail("creative development must stop exactly at five-shot-script")
if plan.get("confirmation") != {"status": "pending"}:
    fail("implementation release must remain pending")
for stale_key in ("cameraPrevis", "animatic"):
    if stale_key in plan:
        fail(f"{stale_key} must not remain current during script-only development")

for heading in (
    "01 — Actuator Origin",
    "02 — Axis in Motion",
    "03 — Cascade Precision",
    "04 — Six Systems, One Axis",
    "05 — Complexity Resolved",
):
    if heading not in script:
        fail(f"storyboard markdown misses {heading}")

for required_phrase in (
    "起点 → 路径 → 核心 → 系统 → 产品",
    "极近特写",
    "俯视轴向",
    "剖面微距",
    "正交轴测",
    "低机位英雄",
    "匹配剪辑",
):
    if required_phrase not in script:
        fail(f"storyboard markdown misses required narrative language: {required_phrase}")

for forbidden_claim in (
    "抗气蚀性能",
    "降噪性能",
    "流量系数",
    "泄漏等级",
    "安全认证",
    "故障安全方向",
    "维修顺序",
    "真实 CFD",
):
    if forbidden_claim in script or forbidden_claim in routes:
        fail(f"script asserts or repeats a prohibited product claim: {forbidden_claim}")

allowed_paths = {
    "ACCEPTANCE.md",
    "AGENTS.md",
    "creative/control-valve/creative-development.json",
    "creative/control-valve/creative-routes.md",
    "creative/control-valve/five-shot-script.md",
    "governance/project-rules.json",
    "governance/project-validation.json",
    "scripts/validate_control_valve_shot_script.py",
}
commands = [
    ["git", "diff", "--name-only", "origin/main...HEAD"],
    ["git", "diff", "--name-only"],
    ["git", "diff", "--name-only", "--cached"],
    ["git", "ls-files", "--others", "--exclude-standard"],
]
changed = set()
for command in commands:
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    changed.update(line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip())
unexpected = sorted(changed - allowed_paths)
if unexpected:
    fail(f"script-only phase changed forbidden paths: {', '.join(unexpected)}")

print(
    "PASS: five materially different shots form one causal product story, "
    "remain inside observed product truth, and stop before previs or runtime"
)
