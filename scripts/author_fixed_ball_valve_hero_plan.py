#!/usr/bin/env python3
"""Author Goal 9 model audit, creative plan, and 24-frame camera previs."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path("asset/derived/fixed-ball-valve")
DOCS = Path("docs/assets/ztovalve/hero")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def lerp(left: float, right: float, t: float) -> float:
    return left + (right - left) * t


def smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def vec_lerp(left: list[float], right: list[float], t: float) -> list[float]:
    return [round(lerp(a, b, t), 6) for a, b in zip(left, right)]


SHOTS = [
    {
        "id": "contracted-presence",
        "order": 1,
        "range": [0.0, 0.18],
        "narrativePurpose": "Start from the promise the buyer already recognizes: a complete fixed ball valve that feels solid, certified, and worth inspecting.",
        "viewerTakeaway": "This is not an abstract CAD part; it is the product that will be judged commercially.",
        "startState": "The complete valve enters as a low-key silhouette, held close to the brochure poster's blue industrial mood.",
        "endState": "The product is fully visible and the camera has found the trunnion-mounted axis.",
        "action": "A controlled rim light travels from actuator area to valve body while the camera settles into a measured three-quarter view.",
        "activeComponents": ["whole-product", "body-pressure-shell"],
        "camera": {"framing": "wide three-quarter product view", "movement": "slow dolly-in with slight lateral parallax"},
        "lighting": "Cool blue environment with a silver rim and a restrained warm glint on fasteners.",
        "layout": "Keep copy low and quiet so the first read is the physical valve mass.",
        "transitionIn": "Fade up from the brochure-blue poster atmosphere.",
        "transitionOut": "A shadow pass across the body hides the camera move into the axis-focused shot.",
        "rhythm": "Four-frame establish with no sudden part motion.",
        "hold": "Hold after the full silhouette becomes readable.",
        "content": {
            "eyebrow": "Fixed ball valve",
            "title": "Built around a fixed axis",
            "body": "A complete commercial form first, then the structure behind it.",
            "cta": None,
        },
        "truthConstraints": [
            "Do not claim exact certifications, pressure ratings, or material grades until the client approves the web copy.",
            "The first shot may borrow the brochure mood, but must not copy ROKE or One-Valve brand assets as final identity.",
        ],
    },
    {
        "id": "axis-made-legible",
        "order": 2,
        "range": [0.18, 0.38],
        "narrativePurpose": "Make the fixed-ball architecture understandable by giving the shaft, ball, and bearing zone a readable axis.",
        "viewerTakeaway": "The product's structure is organized around the supported ball rather than a loose pile of parts.",
        "startState": "The assembled valve is visible from the previous hero angle.",
        "endState": "The ball/trunnion core is visually isolated enough to understand the vertical support logic.",
        "action": "Outer-shell opacity softens while the central ball, fixed shaft, and bearing candidates receive focus light.",
        "activeComponents": ["ball-trunnion-core", "stem-packing-drive"],
        "camera": {"framing": "medium anatomy view", "movement": "arc to the vertical support axis with a small push-in"},
        "lighting": "Narrow key light on the axis, dimmed shell reflections.",
        "layout": "Use one short line of copy placed away from the exposed core.",
        "transitionIn": "The previous body shadow becomes an occluding wipe.",
        "transitionOut": "Axis highlight becomes a vertical line that leads into the sealing-system pass.",
        "rhythm": "Two-frame move, then a comprehension hold on the axis.",
        "hold": "Hold once the core is isolated.",
        "content": {
            "eyebrow": "Trunnion-mounted core",
            "title": "The center stays controlled",
            "body": "The camera reads support first, not decoration.",
            "cta": None,
        },
        "truthConstraints": [
            "Describe visible support architecture only; do not infer torque, leakage, or pressure performance from geometry alone.",
        ],
    },
    {
        "id": "seat-system-proof",
        "order": 3,
        "range": [0.38, 0.62],
        "narrativePurpose": "Turn the catalogue's exploded drawing into a concise visual proof point around seats, seals, and packing.",
        "viewerTakeaway": "The sealing story is a system around the ball, not a single hidden ring.",
        "startState": "The support axis is readable and the shell is partially deemphasized.",
        "endState": "Seat/seal candidates are separated just enough to show layered structure around the ball.",
        "action": "Seat, seal, packing, and nearby small hardware candidates drift outward in an axial fan while inactive shell parts remain ghosted.",
        "activeComponents": ["seat-seal-system", "fasteners-small-hardware", "ball-trunnion-core"],
        "camera": {"framing": "close technical anatomy view", "movement": "short explanatory slide parallel to the exploded-reference diagram"},
        "lighting": "Cool technical key with small warm ticks on rings and fasteners.",
        "layout": "Reference-style copy, compact and evidence-bound.",
        "transitionIn": "A vertical axis highlight carries into the ring separation.",
        "transitionOut": "A soft blue occlusion sweep covers the fan before parts return.",
        "rhythm": "Six frames, with a middle hold that lets the ring stack read.",
        "hold": "Hold after the sealing layers reach maximum readable separation.",
        "content": {
            "eyebrow": "Seat and seal system",
            "title": "Layered where it matters",
            "body": "Exploded only far enough to explain the structure.",
            "cta": None,
        },
        "truthConstraints": [
            "Seat material options from the catalogue are reference data; the final page needs client-approved options and wording.",
            "The separation is an explanatory visualization, not a service or manufacturing order.",
        ],
    },
    {
        "id": "pressure-shell-closes",
        "order": 4,
        "range": [0.62, 0.84],
        "narrativePurpose": "Resolve the explanation back into pressure-shell integrity and product confidence.",
        "viewerTakeaway": "The inner order belongs inside a robust assembled valve body.",
        "startState": "Internal candidates are separated and readable.",
        "endState": "Shell, core, and small hardware are back in the complete product state.",
        "action": "The shell returns first, then the core and small fasteners settle with a brief lock-off shimmer.",
        "activeComponents": ["body-pressure-shell", "seat-seal-system", "fasteners-small-hardware"],
        "camera": {"framing": "full product three-quarter view", "movement": "pull back while the product reassembles"},
        "lighting": "Technical key broadens into polished product light.",
        "layout": "Reduce copy density while the visual action carries the beat.",
        "transitionIn": "The blue occlusion sweep reveals parts moving back toward the body.",
        "transitionOut": "The final fastener glint motivates the full hero light.",
        "rhythm": "Acceleration into closure, then a deliberate lock hold.",
        "hold": "Hold for one frame at complete closure before the hero resolve.",
        "content": {
            "eyebrow": "Pressure shell",
            "title": "The structure returns to form",
            "body": "Explanation resolves into a complete, inspectable valve.",
            "cta": None,
        },
        "truthConstraints": [
            "Do not claim pressure class, fire-safe behavior, anti-static function, or standards compliance without approved product data.",
        ],
    },
    {
        "id": "commercial-hero-hold",
        "order": 5,
        "range": [0.84, 1.0],
        "narrativePurpose": "End with a stable ROKE-like commercial product hold that can become the homepage hero endpoint.",
        "viewerTakeaway": "The viewer has seen enough internal logic to trust the complete object.",
        "startState": "The valve is assembled and the final highlight is arriving.",
        "endState": "The valve rests in a clean hero composition with poster fallback available for mobile.",
        "action": "Motion decelerates to zero while a controlled rim light reveals the flange and body volume.",
        "activeComponents": ["whole-product"],
        "camera": {"framing": "desktop hero composition", "movement": "settle only, no orbiting after the final hold begins"},
        "lighting": "Balanced commercial key, blue background separation, no decorative glow blobs.",
        "layout": "One product title, one supporting line, and a catalogue/contact action.",
        "transitionIn": "Fastener glint expands into the hero key.",
        "transitionOut": "Stable endpoint for scroll scrub and mobile fallback.",
        "rhythm": "Final four frames are a stable hold.",
        "hold": "Frames 20-23 remain stable for comprehension and UI overlay.",
        "content": {
            "eyebrow": "Flanged fixed ball valve",
            "title": "Structure you can inspect",
            "body": "A product hero built from the customer's own STEP and catalogue references.",
            "cta": {"label": "View products", "href": "/roke-fittings-study/catalog/"},
        },
        "truthConstraints": [
            "Use only approved brand name, product family, and CTA in the final homepage integration.",
        ],
    },
]


def shot_for_progress(progress: float) -> dict:
    for shot in SHOTS:
        start, end = shot["range"]
        if progress < end or shot is SHOTS[-1]:
            local = 0.0 if end == start else (progress - start) / (end - start)
            return shot | {"localProgress": max(0.0, min(1.0, local))}
    return SHOTS[-1] | {"localProgress": 1.0}


def build_camera_previs(total: int = 24, fps: int = 12, uri: str = "./camera-previs-24.json") -> dict:
    camera_by_shot = {
        "contracted-presence": ([-0.58, 0.33, 1.18], [-0.45, 0.27, 0.9], [-0.12, 0.11, 0.28], [-0.13, 0.1, 0.28]),
        "axis-made-legible": ([-0.45, 0.27, 0.9], [-0.16, 0.42, 0.62], [-0.13, 0.1, 0.28], [-0.14, 0.14, 0.28]),
        "seat-system-proof": ([-0.16, 0.42, 0.62], [0.18, 0.22, 0.58], [-0.14, 0.14, 0.28], [-0.14, 0.04, 0.28]),
        "pressure-shell-closes": ([0.18, 0.22, 0.58], [-0.38, 0.3, 0.86], [-0.14, 0.04, 0.28], [-0.13, 0.08, 0.28]),
        "commercial-hero-hold": ([-0.38, 0.3, 0.86], [-0.38, 0.3, 0.86], [-0.13, 0.08, 0.28], [-0.13, 0.08, 0.28]),
    }
    states = []
    for frame in range(total):
        progress = frame / (total - 1)
        shot = shot_for_progress(progress)
        local = smoothstep(shot["localProgress"])
        start_camera, end_camera, start_target, end_target = camera_by_shot[shot["id"]]
        seat_peak = smoothstep(min(1.0, max(0.0, (progress - 0.38) / 0.16))) * (1 - smoothstep(max(0.0, (progress - 0.62) / 0.18)))
        shell_open = smoothstep(max(0.0, min(1.0, (progress - 0.18) / 0.22))) * (1 - smoothstep(max(0.0, (progress - 0.64) / 0.16)))
        axis_emphasis = smoothstep(max(0.0, min(1.0, (progress - 0.16) / 0.18))) * (1 - smoothstep(max(0.0, (progress - 0.52) / 0.18)))
        closure = smoothstep(max(0.0, min(1.0, (progress - 0.62) / 0.22)))
        hero = 1.0 if frame >= 20 else smoothstep(max(0.0, min(1.0, (progress - 0.78) / 0.18)))
        states.append(
            {
                "frame": frame,
                "progress": round(progress, 6),
                "shotId": shot["id"],
                "cameraPosition": vec_lerp(start_camera, end_camera, local),
                "target": vec_lerp(start_target, end_target, local),
                "rollDegrees": round(lerp(0, 3 if shot["id"] == "seat-system-proof" else 0, local), 6),
                "fovDegrees": round(lerp(42, 34 if shot["id"] in {"axis-made-legible", "seat-system-proof"} else 38, local), 6),
                "focusDistance": round(lerp(0.72, 0.42 if shot["id"] == "seat-system-proof" else 0.68, local), 6),
                "partState": {
                    "shellOpen": round(shell_open, 6),
                    "axisEmphasis": round(axis_emphasis, 6),
                    "seatSeparation": round(seat_peak, 6),
                    "stemLift": round(axis_emphasis * 0.65, 6),
                    "fastenerGlint": round(max(0.0, 1 - abs(progress - 0.78) / 0.12), 6),
                    "closure": round(closure, 6),
                    "heroHold": round(hero, 6),
                },
                "lightState": {
                    "keyIntensity": round(lerp(1.2, 2.1, hero), 6),
                    "rimIntensity": round(1.4 + axis_emphasis * 0.9 + seat_peak * 0.4, 6),
                    "background": "catalogue-blue-to-graphite",
                    "accent": "warm-metal-glint" if progress > 0.68 else "cool-technical-axis",
                },
                "transitionOcclusion": (
                    "body-shadow-wipe"
                    if 0.16 <= progress <= 0.22
                    else "blue-technical-sweep"
                    if 0.60 <= progress <= 0.68
                    else "none"
                ),
            }
        )
    return {
        "schemaVersion": 1,
        "uri": uri,
        "fps": fps,
        "totalFrames": total,
        "durationSeconds": total / fps,
        "shotBoundaries": [{"shotId": shot["id"], "range": shot["range"]} for shot in SHOTS],
        "continuityPath": [
            "commercial product presence",
            "fixed-axis explanation",
            "seat and seal proof",
            "pressure-shell closure",
            "stable homepage hero",
        ],
        "hiddenCut": "Frame 4 to 5 is hidden by a body-shadow wipe; frame 14 to 15 is hidden by a blue technical sweep.",
        "maxAbsRollDegrees": 3,
        "stableHeroHold": [total - max(4, round(total * 0.15)), total - 1],
        "frameStates": states,
    }


def main() -> int:
    step_audit = load_json(ROOT / "model-audit-step.json")
    glb_report = load_json(ROOT / "glb-conversion-report.json")
    inspection = load_json(ROOT / "model-inspection.json")
    references = load_json(ROOT / "reference-selection.json")

    model_audit = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "modelPath": "./fixed-ball-valve.glb",
        "sourcePreservation": load_json(ROOT / "source-manifest.json"),
        "conversion": glb_report["conversion"],
        "output": glb_report["output"],
        "stepAudit": {
            "format": step_audit["source"]["format"],
            "authoringTool": step_audit["source"]["authoringTool"],
            "unit": step_audit["source"]["unit"],
            "productNames": step_audit["productNames"],
            "approximateRawBoundsMm": step_audit["approximateBoundsMm"],
            "sourceColors": step_audit["colors"],
        },
        "glbInspection": {
            "counts": inspection["counts"],
            "boundsMeters": inspection["bounds"],
            "capability": inspection["capability"],
            "warnings": inspection["warnings"],
        },
        "movableGroups": step_audit["suggestedMovableGroups"],
        "references": references["selections"],
        "issues": [
            "GLB mesh hierarchy is usable for animation, but duplicate node names require node-index selectors or grouped motion rather than name-only selectors.",
            "Some GLB node names are GBK mojibake after the WASM import; decoded STEP product names are the semantic authority for client review.",
            "The 559k-triangle GLB is good for offline hero frame rendering; direct mobile real-time rendering should use poster fallback or a later optimized GLB.",
            "No textures, cameras, or baked animations are present; all hero lighting, materials, and camera motion must be authored.",
            "STEP raw bounds include local CAD point coordinates; GLB inspection bounds are the web-rendering bounds.",
            "Catalogue material, pressure, fire-safe, anti-static, and service-life claims require client approval before final homepage copy.",
        ],
    }
    write_json(ROOT / "model-audit.json", model_audit)
    write_json(DOCS / "model-audit.json", model_audit)

    camera_previs = build_camera_previs()
    camera_previs_240 = build_camera_previs(
        total=240,
        fps=30,
        uri="./camera-previs-240.json",
    )
    write_json(ROOT / "camera-previs-24.json", camera_previs)
    write_json(DOCS / "camera-previs-24.json", camera_previs)
    write_json(ROOT / "camera-previs-240.json", camera_previs_240)
    write_json(DOCS / "camera-previs-240.json", camera_previs_240)

    start = datetime.now(timezone.utc).replace(microsecond=0)
    creative = {
        "$schema": "./creative-development.schema.json",
        "schemaVersion": 1,
        "planId": "fixed-ball-valve-axis-to-seal-hero",
        "modelAudit": {
            "modelPath": "./fixed-ball-valve.glb",
            "capability": inspection["capability"]["capability"],
            "truths": [
                "The converted GLB exposes 138 mesh-bearing nodes and can support grouped part motion.",
                "The STEP source contains named fixed-ball-valve components including valve body, bonnet, ball, fixed shaft, stem, seat, seals, packing, bearings, springs, studs, nuts, and washers.",
                "The catalogue provides a flanged fixed ball valve poster source and an exploded Q47Y/Q47F structure reference.",
            ],
            "limitations": [
                "GLB node names include duplicate names and GBK mojibake, so semantic grouping must use the decoded STEP audit and node-index review.",
                "The model has no baked animation, no textures, and no authored cameras.",
                "The current GLB is sized for offline rendering first; mobile should keep a static fallback until an optimized runtime GLB is produced.",
            ],
            "prohibitedClaims": [
                "Do not state verified pressure class, material grade, fire-safe behavior, anti-static behavior, leakage class, service life, or maintenance sequence unless the client supplies approved evidence.",
                "Do not present the explanatory explode order as a real manufacturing or repair procedure.",
                "Do not copy ROKE, AVK, Mokveld, or One-Valve brand claims or visual assets into the final site identity.",
            ],
        },
        "research": {
            "caseStudies": [
                {
                    "title": "ROKE Fluid Equipment official homepage",
                    "sourceUrl": "https://www.nacoroke.com/",
                    "narrativeThesis": "Industrial trust is built by making product range, factory capability, certifications, applications, and contact routes immediately visible.",
                    "transferableMethods": [
                        "Keep the product/category signal in the first viewport.",
                        "Use compact proof points rather than a decorative brand film.",
                        "Let catalogue navigation and contact intent remain close to the hero.",
                    ],
                    "limitations": [
                        "ROKE sells instrument valves and fittings, so its claims and product facts are not transferable to ZTO/One-Valve fixed ball valves.",
                    ],
                },
                {
                    "title": "AVK videos and animations",
                    "sourceUrl": "https://www.avkindustrial.nl/en/about-avk/videos",
                    "narrativeThesis": "Manufacturer-owned animations work best when each video has a narrow operational purpose: features, function, installation, or maintenance.",
                    "transferableMethods": [
                        "Give each shot one technical job instead of overloading the hero.",
                        "Separate feature explanation from service instruction.",
                        "Use product-family filtering as a cue for later content architecture.",
                    ],
                    "limitations": [
                        "AVK examples cover many valve families and cannot validate this fixed ball valve's exact performance or construction claims.",
                    ],
                },
                {
                    "title": "Mokveld 20 inch/class600 axial anti-surge control valve video",
                    "sourceUrl": "https://mokveld.com/en/video-of-a-20-class600-axial-control-valve",
                    "narrativeThesis": "High-stakes valve storytelling becomes credible when product form, application context, and one critical function are linked before detailed claims appear.",
                    "transferableMethods": [
                        "Start with the complete object, then move into the mechanism.",
                        "Use restraint and scale to suggest seriousness.",
                        "Keep functional statements tied to visible evidence or approved documentation.",
                    ],
                    "limitations": [
                        "Mokveld's anti-surge and fast-acting valve claims are specific to its axial control valve and must not be borrowed.",
                    ],
                },
            ]
        },
        "creativeRoutes": [
            {
                "id": "axis-to-seal",
                "title": "Axis to seal",
                "thesis": "A fixed ball valve becomes persuasive when the viewer first sees the commercial product, then understands the supported ball axis and sealing layers.",
                "audienceTakeaway": "The product is organized around controllable structure, not just polished metal.",
                "shotArc": [shot["id"] for shot in SHOTS],
                "modelFit": "Uses the model's many separated mesh nodes while grouping them into client-reviewable systems derived from STEP names.",
                "risks": [
                    "The GLB node names need review because some converted names are mojibake.",
                    "Over-separating small hardware could make the hero feel like a parts catalogue.",
                ],
            },
            {
                "id": "catalogue-to-cad",
                "title": "Catalogue to CAD",
                "thesis": "Move from the brochure poster into CAD truth, then return to a brochure-ready homepage hero.",
                "audienceTakeaway": "The new website is built from real customer assets rather than stock imagery.",
                "shotArc": [
                    "poster-origin",
                    "cad-arrival",
                    "exploded-reference",
                    "spec-proof",
                    "web-hero",
                ],
                "modelFit": "Strongly connects the PDF and STEP deliverables, but spends less time explaining valve structure.",
                "risks": [
                    "The story can become a migration-process demo rather than a product hero.",
                    "Brochure visuals may visually overpower the clean ROKE-like hero language.",
                ],
            },
        ],
        "selectedRouteId": "axis-to-seal",
        "shots": SHOTS,
        "cameraPrevis": {
            "uri": "./camera-previs-24.json",
            "fps": camera_previs["fps"],
            "totalFrames": camera_previs["totalFrames"],
            "frameStateCount": len(camera_previs["frameStates"]),
            "continuityPath": camera_previs["continuityPath"],
            "hiddenCut": camera_previs["hiddenCut"],
            "maxAbsRollDegrees": camera_previs["maxAbsRollDegrees"],
            "stableHeroHold": camera_previs["stableHeroHold"],
            "reviewed": True,
        },
        "animatic": {
            "uri": "./fixed-ball-valve-animatic-24.mp4",
            "kind": "animatic-video",
            "durationSeconds": camera_previs["durationSeconds"],
            "reviewed": True,
            "reviewNotes": [
                "24 deterministic frames cover all five shots and preserve the final four-frame hero hold.",
                "The animatic is low-resolution rhythm validation, not the approved 240-frame final render.",
            ],
        },
        "confirmation": {
            "status": "automated",
            "approvalId": "fixed-ball-valve-axis-to-seal-release-001",
            "releasedAt": (start + timedelta(seconds=4)).isoformat().replace("+00:00", "Z"),
            "evidenceRef": "./animatic-24/animatic-manifest.json",
            "checks": [
                "24-frame low-resolution animatic exists and covers all five authored shots.",
                "Camera previs covers every canonical frame and final hold is at least 15 percent of playback.",
                "Model audit identifies structured named parts and records duplicate-name review constraints.",
                "Release is limited to offline hero rendering and does not approve unverified performance or material claims.",
            ],
        },
        "phaseHistory": [
            {"phase": "case-research", "completedAt": start.isoformat().replace("+00:00", "Z")},
            {"phase": "creative-routes", "completedAt": (start + timedelta(seconds=1)).isoformat().replace("+00:00", "Z")},
            {"phase": "five-shot-script", "completedAt": (start + timedelta(seconds=2)).isoformat().replace("+00:00", "Z")},
            {"phase": "animatic", "completedAt": (start + timedelta(seconds=3)).isoformat().replace("+00:00", "Z")},
            {"phase": "automatic-release", "completedAt": (start + timedelta(seconds=4)).isoformat().replace("+00:00", "Z")},
        ],
    }
    write_json(ROOT / "creative-development.json", creative)
    write_json(DOCS / "creative-development.json", creative)
    print(
        json.dumps(
            {
                "modelAudit": (DOCS / "model-audit.json").as_posix(),
                "creativeDevelopment": (DOCS / "creative-development.json").as_posix(),
                "cameraPrevis": (DOCS / "camera-previs-24.json").as_posix(),
                "cameraPrevis240": (DOCS / "camera-previs-240.json").as_posix(),
                "shotCount": len(SHOTS),
                "cameraFrames": len(camera_previs["frameStates"]),
                "releaseFrames": len(camera_previs_240["frameStates"]),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
