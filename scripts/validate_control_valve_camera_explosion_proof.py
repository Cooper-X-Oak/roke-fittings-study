#!/usr/bin/env python3
"""Validate camera control and coded exploded-part movement for the control valve.

This probes the existing WebGL grey animatic as the scheduling authority. It is
not a final-render or material approval check.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Python Playwright is required. On this machine use "
        "D:\\program\\Python\\Python312\\python.exe to run this script."
    ) from exc


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_URL = "http://127.0.0.1:4173/control-valve/index.html?debug"
DEFAULT_CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
DEFAULT_OUTPUT = "creative/control-valve-camera-explosion-proof/evidence/camera-explosion-proof-report.json"

SAMPLES = [
    ("start-exploded", 0.0),
    ("core-partial", 0.15),
    ("body-closing", 0.45),
    ("assembly-near-complete", 0.72),
    ("hero-assembled", 1.0),
]

EXPECTED_GROUPS = {
    "VALVE_BODY_BONNET",
    "PNEUMATIC_ACTUATOR",
    "STEM_CASCADE_PLUG",
    "CASCADE_TRIM",
    "SEALS_SUPPORT",
    "PRODUCTION_DETAILS",
}

MOVING_GROUPS = {
    "VALVE_BODY_BONNET",
    "PNEUMATIC_ACTUATOR",
    "STEM_CASCADE_PLUG",
    "SEALS_SUPPORT",
    "PRODUCTION_DETAILS",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--chrome", default=DEFAULT_CHROME)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    return parser.parse_args()


def distance(left: list[float], right: list[float]) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))


def axis_range(values: list[dict], axis: str) -> float:
    index = {"x": 0, "y": 1, "z": 2}[axis]
    coordinates = [item["worldCenter"][index] for item in values]
    return max(coordinates) - min(coordinates)


def group_map(state: dict) -> dict[str, dict]:
    return {entry["name"]: entry for entry in state["groups"]}


def require(condition: bool, findings: list[dict], message: str, details: dict | None = None) -> None:
    if not condition:
        findings.append(
            {
                "severity": "blocker",
                "message": message,
                "details": details or {},
            }
        )


def main() -> None:
    args = parse_args()
    output_path = (ROOT / args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    screenshot_dir = output_path.parent / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    findings: list[dict] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.chrome)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        console_messages: list[dict] = []
        failed_requests: list[dict] = []
        page.on("console", lambda msg: console_messages.append({"type": msg.type, "text": msg.text}))
        page.on(
            "requestfailed",
            lambda request: failed_requests.append({"url": request.url, "failure": request.failure}),
        )

        response = page.goto(args.url, wait_until="networkidle", timeout=25_000)
        ready = page.evaluate("window.__CONTROL_VALVE_METRICS__.waitForReady()")
        samples = []
        for label, progress in SAMPLES:
            state = page.evaluate("progress => window.__CONTROL_VALVE_METRICS__.setProgressForTest(progress)", progress)
            screenshot_path = screenshot_dir / f"{label}-{state['shotId']}.png"
            page.screenshot(path=str(screenshot_path), full_page=False)
            samples.append(
                {
                    "label": label,
                    "progress": progress,
                    "screenshot": str(screenshot_path.relative_to(ROOT)).replace("\\", "/"),
                    "state": state,
                }
            )
        motion_summary = page.evaluate("window.__CONTROL_VALVE_METRICS__.canonicalMotionSummary()")
        browser.close()

    start = samples[0]["state"]
    hero = samples[-1]["state"]
    start_groups = group_map(start)
    hero_groups = group_map(hero)
    present_groups = set(start_groups)
    group_motion = {
        name: distance(start_groups[name]["worldPosition"], hero_groups[name]["worldPosition"])
        for name in sorted(present_groups & set(hero_groups))
    }

    start_trim = start["trimIslands"]
    hero_trim = hero["trimIslands"]
    start_trim_y_range = axis_range(start_trim, "y")
    hero_trim_y_range = axis_range(hero_trim, "y")
    trim_collapse_ratio = start_trim_y_range / max(hero_trim_y_range, 0.0001)

    camera_delta = distance(start["cameraPosition"], hero["cameraPosition"])
    camera_samples = [sample["state"]["cameraPosition"] for sample in samples]
    unique_camera_positions = {
        tuple(round(value, 4) for value in position)
        for position in camera_samples
    }

    require(response is not None and response.status == 200, findings, "preview route did not return HTTP 200")
    require(not failed_requests, findings, "preview route had failed network requests", {"failedRequests": failed_requests})
    require(
        not [message for message in console_messages if message["type"] == "error"],
        findings,
        "preview route logged console errors",
        {"consoleErrors": [message for message in console_messages if message["type"] == "error"]},
    )
    require(ready.get("groups") == 6, findings, "runtime did not expose six semantic control groups", ready)
    require(
        ready.get("trimConnectedComponentCount") == 4,
        findings,
        "runtime did not split CASCADE_TRIM into four connected geometry islands",
        ready,
    )
    require(EXPECTED_GROUPS <= present_groups, findings, "semantic group set is incomplete", {"presentGroups": sorted(present_groups)})
    require(
        start.get("mechanicalAxisWorld") == [0, 1, 0],
        findings,
        "mechanical axis is not declared as vertical Three.js Y",
        {"mechanicalAxisWorld": start.get("mechanicalAxisWorld")},
    )
    require(
        start_trim_y_range > 2.5 and start_trim_y_range > axis_range(start_trim, "x") * 20 and start_trim_y_range > axis_range(start_trim, "z") * 20,
        findings,
        "start exploded trim islands are not arranged along the vertical axis",
        {
            "startTrimYRange": start_trim_y_range,
            "startTrimXRange": axis_range(start_trim, "x"),
            "startTrimZRange": axis_range(start_trim, "z"),
        },
    )
    require(
        trim_collapse_ratio > 3.0,
        findings,
        "trim islands do not collapse enough from exploded to assembled state",
        {"startTrimYRange": start_trim_y_range, "heroTrimYRange": hero_trim_y_range, "ratio": trim_collapse_ratio},
    )
    require(
        all(group_motion.get(name, 0) > 0.15 for name in MOVING_GROUPS),
        findings,
        "one or more semantic groups did not move enough between exploded and assembled states",
        {"groupMotion": group_motion},
    )
    require(camera_delta > 6.0, findings, "camera position is not materially controlled across the proof", {"cameraDelta": camera_delta})
    require(len(unique_camera_positions) >= 4, findings, "camera samples do not expose enough distinct viewpoints")
    require(motion_summary.get("productYawRange", 0) >= 150, findings, "product yaw range is too small", motion_summary)
    require(motion_summary.get("coordinatedFrameCount", 0) >= 250, findings, "camera/product motion is not coordinated enough", motion_summary)

    report = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "purpose": "Validate code control of product camera viewpoints and exploded semantic-part movement.",
        "boundary": {
            "validated": [
                "WebGL scheduling authority can set camera viewpoint and product yaw by code.",
                "Runtime can move six semantic groups and four connected CASCADE_TRIM islands by code.",
                "The proof route keeps the product on a vertical mechanical axis.",
            ],
            "notValidated": [
                "Blender executable availability in this shell.",
                "Final Cycles render quality.",
                "Final commercial composition approval.",
            ],
        },
        "target": {
            "url": args.url,
            "browserExecutable": args.chrome,
            "httpStatus": response.status if response else None,
        },
        "ready": ready,
        "motionSummary": motion_summary,
        "metrics": {
            "cameraDeltaStartToHero": camera_delta,
            "uniqueCameraPositionCount": len(unique_camera_positions),
            "groupMotionStartToHero": group_motion,
            "startTrimYRange": start_trim_y_range,
            "heroTrimYRange": hero_trim_y_range,
            "trimCollapseRatio": trim_collapse_ratio,
        },
        "samples": samples,
        "consoleErrors": [message for message in console_messages if message["type"] == "error"],
        "failedRequests": failed_requests,
        "findings": findings,
        "verdict": "pass" if not findings else "fail",
    }
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if findings:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
