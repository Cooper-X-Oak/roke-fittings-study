#!/usr/bin/env python3

from control_valve_validation import CREATIVE, ROUTE, fail, read_json


audit = read_json(CREATIVE / "source-audit.json")
truth = audit.get("truthBoundary", {})
if len(truth.get("verifiedSourceLabels", [])) < 8:
    fail("verified source labels are incomplete")
if len(truth.get("prohibitedClaims", [])) < 8:
    fail("prohibited product claims are incomplete")

runtime_text = "\n".join(
    path.read_text(encoding="utf-8")
    for path in (ROUTE / "index.html", ROUTE / "app.mjs")
)
for forbidden in (
    "抗气蚀性能",
    "降噪性能",
    "密封等级",
    "流量系数",
    "安全认证",
    "真实 CFD",
    "维修顺序",
):
    if forbidden in runtime_text:
        fail(f"runtime asserts prohibited product claim: {forbidden}")
if "不模拟流体" not in runtime_text:
    fail("runtime must disclose that the path light is not fluid simulation")
if "source labels" not in str(truth).lower() and not truth.get("verifiedSourceLabels"):
    fail("source-label boundary is missing")

print(
    "PASS: runtime copy remains bound to STEP labels and explicitly excludes "
    "performance, certification, CFD and maintenance claims"
)
