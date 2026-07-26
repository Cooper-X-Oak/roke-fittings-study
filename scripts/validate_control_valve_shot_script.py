#!/usr/bin/env python3

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CREATIVE = ROOT / "creative" / "control-valve"
PLAN_PATH = CREATIVE / "creative-development.json"
SCRIPT_PATH = CREATIVE / "five-shot-script.md"
ROUTES_PATH = CREATIVE / "creative-routes.md"
BOARD_PATH = CREATIVE / "advertising-reference-board.md"


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
script = SCRIPT_PATH.read_text(encoding="utf-8")
routes = ROUTES_PATH.read_text(encoding="utf-8")
board = BOARD_PATH.read_text(encoding="utf-8")

if plan.get("selectedRouteId") != "precision-becomes-whole":
    fail("the selected route must be precision-becomes-whole")

shots = plan.get("shots", [])
expected_ids = [
    "core-suspended",
    "precision-nested",
    "body-encloses",
    "assembly-complete",
    "product-presence",
]
if [shot.get("id") for shot in shots] != expected_ids:
    fail("the plan must contain exactly the five continuous story-beat IDs")

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
        fail(f"beat {shot.get('id')} misses fields: {', '.join(missing)}")
    if not shot["camera"].get("framing") or not shot["camera"].get("movement"):
        fail(f"beat {shot['id']} misses framing or camera support")
    if len(shot["activeComponents"]) < 1:
        fail(f"beat {shot['id']} has no active component")
    if len(shot["truthConstraints"]) < 1:
        fail(f"beat {shot['id']} has no truth constraint")
    if shot["content"].get("cta") is not None:
        fail(f"beat {shot['id']} must not introduce an unapproved CTA")

ranges = [shot.get("range") for shot in shots]
if ranges[0][0] != 0 or ranges[-1][1] != 1:
    fail("story-beat ranges must cover the complete normalized timeline")
for left, right in zip(ranges, ranges[1:]):
    if left[1] != right[0]:
        fail("story-beat ranges must be ordered and gapless")

takeaways = {shot["viewerTakeaway"] for shot in shots}
actions = {shot["action"] for shot in shots}
if len(takeaways) != 5 or len(actions) != 5:
    fail("all five beats need distinct product cognition and visible product action")

for index, shot in enumerate(shots[1:], start=2):
    if "完全继承上一节拍终态" not in shot["startState"]:
        fail(f"beat {index} must explicitly inherit the prior product end state")

for shot in shots:
    continuity_language = " ".join(
        [
            shot["startState"],
            shot["endState"],
            shot["action"],
            shot["camera"]["framing"],
            shot["camera"]["movement"],
            shot["transitionIn"],
            shot["transitionOut"],
        ]
    )
    if "轴" not in continuity_language and shot["id"] != "product-presence":
        fail(f"beat {shot['id']} loses the shared mechanical-axis continuity")

camera_spectacle_terms = ("九十度", "90°", "crane-down", "正交轴测", "高速穿越")
for shot in shots[:4]:
    camera_language = f"{shot['camera']['framing']} {shot['camera']['movement']}"
    if any(term in camera_language for term in camera_spectacle_terms):
        fail(f"beat {shot['id']} reintroduces a forced camera-axis demonstration")
    if any(term in camera_language.lower() for term in ("hero arc", "orbit")):
        fail(f"beat {shot['id']} uses the hero orbit before the final beat")

final_camera = shots[-1]["camera"]["movement"]
if (
    "唯一一次" not in final_camera
    or not any(angle in final_camera for angle in ("二十四度", "二十六度"))
):
    fail("the final beat must contain the single bounded hero arc")

for required_phrase in (
    "复杂结构，沿一条机械轴归于秩序",
    "核心显露 → 层级归位 → 阀体闭合 → 整机成立 → 英雄确认",
    "一条轴",
    "一个世界",
    "一条因果链",
    "一次高潮",
    "可逆滚动",
    "产品先于相机",
    "五个节拍的差异来自产品状态和观众认知",
):
    if required_phrase not in script:
        fail(f"storyboard markdown misses continuous-story language: {required_phrase}")

for heading in (
    "01 — Core Suspended",
    "02 — Precision Nested",
    "03 — Body Encloses",
    "04 — Assembly Complete",
    "05 — Product Presence",
):
    if heading not in script:
        fail(f"storyboard markdown misses {heading}")

for required_reference in (
    "ROKE 首页 240 帧",
    "Honda Accord《Cog》",
    "FutureDeluxe × Peloton",
    "FutureDeluxe × Huawei Mate 70",
    "Lightshape × Pinion MGU",
    "Elmac FAB Valve",
):
    if required_reference not in board:
        fail(f"advertising reference board misses {required_reference}")

for decision_phrase in (
    "不采用无目标无人机穿越",
    "六节点只保留为制作控制层",
    "最终英雄旋转只出现一次",
):
    if decision_phrase not in f"{board}\n{routes}\n{script}":
        fail(f"research is not connected to the script decision: {decision_phrase}")

for forbidden_claim in (
    "流量系数",
    "泄漏等级",
    "安全认证",
    "真实 CFD",
):
    if forbidden_claim in script or forbidden_claim in routes:
        fail(f"script asserts or repeats a prohibited product claim: {forbidden_claim}")

phases = [entry.get("phase") for entry in plan.get("phaseHistory", [])]
if phases != [
    "case-research",
    "creative-routes",
    "five-shot-script",
    "animatic",
]:
    fail("creative development must preserve the script and advance only to animatic")
if plan.get("confirmation") != {"status": "pending"}:
    fail("runtime implementation release must remain pending")
if not plan.get("cameraPrevis") or not plan.get("animatic"):
    fail("the approved script must now be accompanied by camera previs and animatic")

print(
    "PASS: five cognitive beats form one reversible product transformation, "
    "keep the shared mechanical axis, remain inside observed product truth, "
    "and remains the authority for the pending grey animatic"
)
