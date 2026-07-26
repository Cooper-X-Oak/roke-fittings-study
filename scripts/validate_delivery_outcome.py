import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSPECTION = ROOT / "creative" / "car-concept" / "delivery-inspection.json"
METRICS = ROOT / "validation-results" / "car-product-story-browser-metrics.json"
SCREENSHOTS = [
    "car-fpv-intercept.png",
    "car-fpv-thread-before-cut.png",
    "car-fpv-thread-after-cut.png",
    "car-fpv-cockpit-run.png",
    "car-fpv-breakout.png",
    "car-fpv-arrest.png",
    "car-fpv-hero.png",
]
EXPECTED_CLAIMS = {
    "continuous-five-shot-runtime",
    "deterministic-reversible-cinematic-state",
    "high-performance-demand-rendering",
    "runtime-fallback-and-truthfulness",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


inspection = json.loads(INSPECTION.read_text(encoding="utf-8"))
metrics = json.loads(METRICS.read_text(encoding="utf-8"))

require(inspection["verdict"] == "pass", "delivery inspection must pass")
require(inspection["scope"]["status"] == "applicable", "inspection scope must be applicable")
require(not inspection["findings"], "passing inspection may not retain findings")

planned = {claim["claim_id"] for claim in inspection["plan"]["claims"]}
coverage = {item["claim_id"]: item for item in inspection["coverage"]}
require(planned == EXPECTED_CLAIMS, "inspection must plan all current delivery claims")
require(set(coverage) == EXPECTED_CLAIMS, "inspection coverage must match planned claims")
for claim_id, item in coverage.items():
    require(item["status"] == "checked", f"{claim_id} must be checked")
    require(item["evidence_refs"], f"{claim_id} must have direct evidence")

evidence = {item["id"]: item for item in inspection["evidence"]}
for item in coverage.values():
    for evidence_id in item["evidence_refs"]:
        require(evidence_id in evidence, f"missing evidence {evidence_id}")
        require(evidence[evidence_id]["quality"] == "direct", f"{evidence_id} must be direct")

for screenshot in SCREENSHOTS:
    path = ROOT / "validation-results" / screenshot
    require(path.exists() and path.stat().st_size > 0, f"missing screenshot {screenshot}")

runs = metrics["runs"]
require(len(runs) >= 2, "cold and warm browser runs are required")
def passes_performance_budget(run: dict) -> bool:
    runtime = run["runtime"]
    return (
        runtime["frameIntervalMs"]["p50"] <= 18.5
        and runtime["frameIntervalMs"]["p95"] <= 50
        and runtime["frameIntervalOver33_3Ms"]["ratio"] <= 0.15
        and runtime["renderCpuDurationMs"]["p95"] <= 10
        and runtime["idleRendererFramesAfterSettle"] == 0
    )


require(any(passes_performance_budget(run) for run in runs), "at least one run must pass")
functional = metrics["functional"]
require(functional["consoleErrors"] == [], "browser console must not contain errors")
require(functional["pageErrors"] == [], "page must not contain errors")
require(functional["failedRequests"] == [], "browser must not contain failed requests")
require(
    functional["deterministicTransformMaxDifference"] == 0,
    "scroll replay must be deterministic",
)
for run in runs:
    runtime = run["runtime"]
    require(
        runtime["idleRendererFramesAfterSettle"] == 0,
        "demand renderer must not render while idle",
    )
    require(
        run["browserSignals"]["longAnimationFrame"]["count"] == 0,
        "browser run must not contain long animation frames",
    )

print("delivery outcome inspection validation: PASS")
