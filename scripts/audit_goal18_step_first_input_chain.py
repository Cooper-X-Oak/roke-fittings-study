#!/usr/bin/env python3
"""Generate the Goal 18 STEP-first render input-chain audit."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "asset" / "derived" / "fixed-ball-valve"
HERO = ROOT / "docs" / "assets" / "ztovalve" / "hero"
OUT = HERO / "goal18-step-first-input-chain"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path | str | None) -> str | None:
    if path is None:
        return None
    value = Path(path)
    if not value.is_absolute():
        return value.as_posix()
    try:
        return value.relative_to(ROOT).as_posix()
    except ValueError:
        return value.as_posix()


def command_probe(name: str, common_paths: list[str] | None = None) -> dict:
    common_paths = common_paths or []
    path = shutil.which(name)
    source = path
    if not source:
        for candidate in common_paths:
            candidate_path = Path(candidate)
            if candidate_path.is_file():
                source = str(candidate_path)
                break
    return {
        "name": name,
        "available": bool(source),
        "source": source.replace("\\", "/") if source else None,
    }


def python_module_probe(name: str) -> dict:
    spec = importlib.util.find_spec(name)
    return {
        "name": f"python:{name}",
        "available": spec is not None,
        "source": getattr(spec, "origin", None).replace("\\", "/") if spec and spec.origin else None,
    }


def load_node_tools() -> dict:
    package_path = ROOT / ".scratch" / "goal9-tools" / "package.json"
    if not package_path.is_file():
        return {
            "packagePath": rel(package_path),
            "available": False,
            "dependencies": {},
            "modules": [],
        }
    package = read_json(package_path)
    modules = []
    for name in ("occt-import-js", "@gltf-transform/core", "playwright-core", "sharp"):
        module_path = ROOT / ".scratch" / "goal9-tools" / "node_modules" / name
        modules.append({"name": name, "available": module_path.exists(), "path": rel(module_path)})
    return {
        "packagePath": rel(package_path),
        "available": True,
        "dependencies": package.get("dependencies", {}),
        "modules": modules,
    }


def file_fact(path: Path, expected_sha256: str | None = None) -> dict:
    actual_hash = sha256(path)
    return {
        "path": rel(path),
        "exists": path.is_file(),
        "bytes": path.stat().st_size if path.is_file() else None,
        "sha256": actual_hash,
        "hashMatchesManifest": actual_hash is not None and expected_sha256 is not None and actual_hash.lower() == expected_sha256.lower(),
    }


def build_manifest() -> dict:
    step_audit = read_json(DERIVED / "model-audit-step.json")
    conversion = read_json(DERIVED / "glb-conversion-report.json")
    inspection = read_json(DERIVED / "model-inspection.json")
    model_audit = read_json(HERO / "model-audit.json")
    goal17 = read_json(HERO / "goal17-offline-lookdev" / "render-manifest.json")
    source_manifest = read_json(DERIVED / "source-manifest.json")

    step_hash = step_audit["source"]["sha256"]
    brochure_hash = source_manifest["brochure"]["sha256"]
    glb_hash = conversion["output"]["sha256"]
    node_tools = load_node_tools()

    toolchain = {
        "commands": [
            command_probe("blender", [
                "C:/Program Files/Blender Foundation/Blender 4.5/blender.exe",
                "C:/Program Files/Blender Foundation/Blender 4.4/blender.exe",
                "C:/Program Files/Blender Foundation/Blender 4.3/blender.exe",
                "C:/Program Files/Blender Foundation/Blender 4.2/blender.exe",
            ]),
            command_probe("FreeCADCmd", [
                "C:/Program Files/FreeCAD 1.0/bin/FreeCADCmd.exe",
                "C:/Program Files/FreeCAD 0.21/bin/FreeCADCmd.exe",
            ]),
            command_probe("FreeCAD"),
            command_probe("keyshot"),
            command_probe("SolidWorksVisualize"),
            command_probe("swvisualize"),
            command_probe("gmsh"),
            command_probe("node"),
            command_probe("python"),
        ],
        "pythonModules": [
            python_module_probe("cadquery"),
            python_module_probe("OCP"),
            python_module_probe("gmsh"),
        ],
        "nodeTools": node_tools,
    }

    occt_available = any(module["name"] == "occt-import-js" and module["available"] for module in node_tools["modules"])
    offline_renderer_available = any(
        command["name"] in {"blender", "keyshot", "SolidWorksVisualize", "swvisualize"}
        and command["available"]
        for command in toolchain["commands"]
    )
    native_step_workstation_available = any(
        command["name"] in {"FreeCADCmd", "FreeCAD", "keyshot", "SolidWorksVisualize", "swvisualize"}
        and command["available"]
        for command in toolchain["commands"]
    )

    duplicate_names = inspection.get("naming", {}).get("duplicateNodeNames", [])
    manifest = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "goal": "Goal 18 STEP-first professional render input-chain validation",
        "status": "step-first-recommended-renderer-blocked",
        "verdict": {
            "primaryInputForFinalCommercialRender": "STEP-first",
            "currentOperationalFallback": "existing audited GLB for lookdev, blocking, and web-preview continuity",
            "decision": "Use the fixed-ball-valve STEP and brochure as the authoritative upstream inputs for any final commercial render. Reuse the current GLB only as a verified derivative fallback until a STEP-capable renderer or STEP re-import pass is available.",
            "confidence": "high",
            "stopCondition": "Do not label a still or 240-frame release as final photoreal output until the renderer input is rebuilt or revalidated from STEP and the material assignments are visually checked against the brochure references.",
        },
        "sourceBoundary": {
            "rule": "Original STEP, brochure PDF, and delivered GLB are read-only inputs for this audit.",
            "rawStep": file_fact(ROOT / "asset" / "固定式球阀.STEP", step_hash),
            "derivedStepCopy": file_fact(DERIVED / "source" / "固定式球阀.STEP", step_hash),
            "rawBrochure": file_fact(ROOT / "asset" / "一阀画册 2026-8.pdf", brochure_hash),
            "derivedBrochureCopy": file_fact(DERIVED / "source" / "一阀画册 2026-8.pdf", brochure_hash),
            "currentGlb": file_fact(HERO / "fixed-ball-valve.glb", glb_hash),
        },
        "stepAuthority": {
            "path": rel(DERIVED / "model-audit-step.json"),
            "format": step_audit["source"]["format"],
            "authoringTool": step_audit["source"]["authoringTool"],
            "unit": step_audit["source"]["unit"],
            "encoding": step_audit["source"]["encoding"],
            "productNameCount": len(step_audit["productNames"]),
            "suggestedMovableGroupCount": len(step_audit["suggestedMovableGroups"]),
            "sourceColorCount": len(step_audit["colors"]),
            "entityCounts": {
                "PRODUCT": step_audit["entityCounts"].get("PRODUCT"),
                "NEXT_ASSEMBLY_USAGE_OCCURRENCE": step_audit["entityCounts"].get("NEXT_ASSEMBLY_USAGE_OCCURRENCE"),
                "ADVANCED_FACE": step_audit["entityCounts"].get("ADVANCED_FACE"),
                "ADVANCED_BREP_SHAPE_REPRESENTATION": step_audit["entityCounts"].get("ADVANCED_BREP_SHAPE_REPRESENTATION"),
                "MANIFOLD_SOLID_BREP": step_audit["entityCounts"].get("MANIFOLD_SOLID_BREP"),
            },
            "productNames": step_audit["productNames"],
            "groups": step_audit["suggestedMovableGroups"],
            "issues": step_audit["issues"],
        },
        "glbDerivative": {
            "conversionReport": rel(DERIVED / "glb-conversion-report.json"),
            "modelInspection": rel(DERIVED / "model-inspection.json"),
            "engine": conversion["conversion"]["engine"],
            "outputScale": conversion["conversion"]["outputScale"],
            "outputUnit": conversion["conversion"]["outputUnit"],
            "linearDeflectionType": conversion["conversion"]["linearDeflectionType"],
            "linearDeflection": conversion["conversion"]["linearDeflection"],
            "angularDeflection": conversion["conversion"]["angularDeflection"],
            "meshCountFromOcct": conversion["conversion"]["meshCountFromOcct"],
            "meshBearingNodeCount": conversion["conversion"]["meshBearingNodeCount"],
            "triangles": inspection["counts"]["triangles"],
            "nodes": inspection["counts"]["nodes"],
            "meshNodes": inspection["counts"]["meshNodes"],
            "materials": inspection["counts"]["materials"],
            "textures": inspection["counts"]["textures"],
            "animations": inspection["counts"]["animations"],
            "cameras": inspection["counts"]["cameras"],
            "skins": inspection["counts"]["skins"],
            "meaningfulMeshNodeRatio": inspection["naming"]["meaningfulMeshNodeRatio"],
            "duplicateNodeNameGroupCount": len(duplicate_names),
            "largestDuplicateNodeNameGroups": duplicate_names[:6],
            "capability": inspection["capability"],
            "warnings": inspection["warnings"],
            "issues": conversion["issues"] + model_audit["issues"],
        },
        "goal17CarryForward": {
            "manifest": rel(HERO / "goal17-offline-lookdev" / "render-manifest.json"),
            "rendererAvailability": goal17["rendererAvailability"],
            "renderBoundary": goal17["renderBoundary"],
            "plannedOutputs": goal17["plannedOutputs"],
            "nextRequiredAction": goal17["nextRequiredAction"],
        },
        "toolchain": toolchain,
        "routes": [
            {
                "id": "step-first-native-or-reimport",
                "label": "STEP-first professional render path",
                "status": "recommended",
                "localReadiness": "blocked until a STEP-capable offline renderer or native STEP inspection workstation is available",
                "availableNow": offline_renderer_available and (native_step_workstation_available or occt_available),
                "why": [
                    "STEP preserves the decoded Chinese product tree, units, source colors, and B-Rep authority before tessellation.",
                    "Final material and part grouping decisions should be made from STEP labels plus brochure references, then carried into renderer-specific meshes.",
                    "A fresh STEP import can tune tessellation, bevel strategy, normals, and material IDs before the photoreal pass.",
                ],
                "risks": [
                    "Current machine has no detected Blender, KeyShot, SOLIDWORKS Visualize, or FreeCAD native workstation path.",
                    "occt-import-js is available as a conversion bridge, but it already produced mojibake GLB names; semantic mapping must come from the STEP audit.",
                ],
            },
            {
                "id": "existing-glb-lookdev-fallback",
                "label": "Existing GLB lookdev fallback",
                "status": "allowed for continuity, not final source authority",
                "localReadiness": "available as current Goal 17 script input if an offline renderer is installed later",
                "availableNow": (HERO / "fixed-ball-valve.glb").is_file(),
                "why": [
                    "The GLB is already hash-bound to the STEP conversion report and exposes 138 mesh-bearing nodes.",
                    "It is sufficient for current blocking, material lookdev planning, and web-preview continuity.",
                    "It keeps homepage and Goal 16/17 references stable while the STEP-first renderer path is prepared.",
                ],
                "risks": [
                    "GLB node names include duplicate groups and mojibake, so name-only material assignment is unsafe.",
                    "The GLB has no textures, cameras, or baked animations; all commercial rendering work is authored downstream.",
                    "Using the GLB as final input without STEP revalidation can lock in tessellation and naming defects.",
                ],
            },
            {
                "id": "direct-final-render-from-current-glb",
                "label": "Direct final render from current GLB",
                "status": "not recommended",
                "localReadiness": "blocked by missing renderer and by semantic-name risk",
                "availableNow": False,
                "why": [
                    "It would be fast to continue from the existing Goal 17 script, but it would not solve the input-authority problem.",
                    "It cannot recover STEP-native semantic labels, source units, B-Rep surfaces, or tessellation decisions after the fact.",
                ],
                "risks": [
                    "High risk of material assignment mistakes on repeated fasteners, seats, seals, and small hardware.",
                    "High risk of calling a render final while the upstream CAD truth was never re-imported for final quality.",
                ],
            },
        ],
        "nextGates": [
            {
                "id": "install-or-access-renderer",
                "status": "blocked",
                "acceptance": "Blender with a STEP import route, KeyShot, SOLIDWORKS Visualize, or FreeCAD-to-renderer workflow is available and records the input file hash.",
            },
            {
                "id": "rerun-step-derived-render-mesh",
                "status": "pending",
                "acceptance": "Renderer mesh or GLB is regenerated from the STEP with current hash 3ddb291607730239f5a067e9d1730acda0931874c5f42c4ac0c358516efa2547 and records tessellation/material mapping.",
            },
            {
                "id": "material-map-review",
                "status": "pending",
                "acceptance": "At least five material families are assigned using STEP labels, GLB node indices, and brochure reference pages without inventing product material grades.",
            },
            {
                "id": "photoreal-still-proof",
                "status": "pending",
                "acceptance": "Three stills are rendered by an offline renderer and visually compared against the brochure product and structure references.",
            },
        ],
    }
    if offline_renderer_available:
        manifest["status"] = "step-first-recommended-renderer-available"
        manifest["nextGates"][0]["status"] = "ready"
    return manifest


def html_escape(value: object) -> str:
    text = str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def route_markup(route: dict) -> str:
    reasons = "".join(f"<li>{html_escape(item)}</li>" for item in route["why"])
    risks = "".join(f"<li>{html_escape(item)}</li>" for item in route["risks"])
    return f"""
          <article class="route route--{html_escape(route['id'])}">
            <div>
              <p class="eyebrow">{html_escape(route['status'])}</p>
              <h3>{html_escape(route['label'])}</h3>
              <p>{html_escape(route['localReadiness'])}</p>
            </div>
            <div>
              <strong>Why</strong>
              <ul>{reasons}</ul>
            </div>
            <div>
              <strong>Risk</strong>
              <ul>{risks}</ul>
            </div>
          </article>"""


def tool_markup(manifest: dict) -> str:
    commands = manifest["toolchain"]["commands"]
    modules = manifest["toolchain"]["pythonModules"] + manifest["toolchain"]["nodeTools"]["modules"]
    rows = []
    for item in commands + modules:
        state = "available" if item["available"] else "missing"
        source = item.get("source") or item.get("path") or "not detected"
        rows.append(
            f"""
            <div class="tool-row" data-state="{state}">
              <span>{html_escape(item['name'])}</span>
              <b>{state}</b>
              <code>{html_escape(source)}</code>
            </div>"""
        )
    return "".join(rows)


def group_markup(manifest: dict) -> str:
    items = []
    for group in manifest["stepAuthority"]["groups"]:
        members = ", ".join(group["members"])
        items.append(
            f"""
            <article class="group">
              <h3>{html_escape(group['label'])}</h3>
              <p>{html_escape(members)}</p>
            </article>"""
        )
    return "".join(items)


def gate_markup(manifest: dict) -> str:
    rows = []
    for gate in manifest["nextGates"]:
        rows.append(
            f"""
            <div class="gate" data-state="{html_escape(gate['status'])}">
              <span>{html_escape(gate['status'])}</span>
              <strong>{html_escape(gate['id'])}</strong>
              <p>{html_escape(gate['acceptance'])}</p>
            </div>"""
        )
    return "".join(rows)


def build_html(manifest: dict) -> str:
    step = manifest["stepAuthority"]
    glb = manifest["glbDerivative"]
    verdict = manifest["verdict"]
    route_html = "".join(route_markup(route) for route in manifest["routes"])
    return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="icon" href="data:,">
    <title>Goal 18 STEP-first Input Chain</title>
    <style>
      :root {{
        color-scheme: light;
        --paper: #f3f4f2;
        --surface: #ffffff;
        --ink: #151a1d;
        --muted: #586164;
        --line: #d2d8d5;
        --red: #c91d26;
        --green: #167568;
        --amber: #b97619;
        --blue: #1f5e9d;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        background: var(--paper);
        color: var(--ink);
        font-family: Arial, "Microsoft YaHei", sans-serif;
      }}
      header, main, footer {{
        width: min(1440px, calc(100% - 48px));
        margin: 0 auto;
      }}
      header {{ padding: 46px 0 28px; }}
      .eyebrow {{
        margin: 0 0 10px;
        color: var(--red);
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 0;
        text-transform: uppercase;
      }}
      h1, h2, h3 {{
        margin: 0;
        line-height: 1.12;
        letter-spacing: 0;
      }}
      h1 {{
        max-width: 1160px;
        font-size: clamp(38px, 5vw, 72px);
      }}
      h2 {{ font-size: clamp(26px, 3vw, 42px); }}
      h3 {{ font-size: 20px; }}
      p {{ margin: 0; }}
      code {{
        font-family: "Cascadia Mono", Consolas, monospace;
        font-size: 12px;
        overflow-wrap: anywhere;
        word-break: break-word;
      }}
      .intro {{
        display: grid;
        grid-template-columns: minmax(0, 1fr) minmax(320px, 0.48fr);
        gap: 28px;
        align-items: end;
        margin-top: 22px;
      }}
      .intro p, .note, .route p, .route li, .group p, .gate p {{
        color: var(--muted);
        font-size: 16px;
        line-height: 1.55;
        overflow-wrap: anywhere;
      }}
      .decision {{
        display: grid;
        gap: 10px;
        padding: 18px;
        border: 1px solid var(--line);
        background: var(--surface);
      }}
      .decision-row {{
        display: grid;
        grid-template-columns: 126px minmax(0, 1fr);
        gap: 12px;
        padding-bottom: 10px;
        border-bottom: 1px solid var(--line);
        font-size: 14px;
      }}
      .decision-row:last-child {{
        padding-bottom: 0;
        border-bottom: 0;
      }}
      .decision-row span {{ color: var(--muted); }}
      .decision-row strong {{ color: var(--ink); }}
      .section {{
        padding: 32px 0;
        border-top: 1px solid var(--line);
      }}
      .section-head {{
        display: grid;
        grid-template-columns: minmax(0, 0.58fr) minmax(0, 1fr);
        gap: 24px;
        align-items: end;
        margin-bottom: 18px;
      }}
      .metric-grid {{
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 12px;
      }}
      .metric {{
        min-height: 118px;
        padding: 16px;
        border: 1px solid var(--line);
        background: var(--surface);
      }}
      .metric b {{
        display: block;
        margin-bottom: 4px;
        font-size: 28px;
      }}
      .metric span {{
        color: var(--muted);
        font-size: 13px;
      }}
      .visuals {{
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 16px;
      }}
      figure {{
        margin: 0;
        border: 1px solid var(--line);
        background: var(--surface);
      }}
      figure img {{
        display: block;
        width: 100%;
        aspect-ratio: 16 / 10;
        object-fit: cover;
      }}
      figcaption {{
        padding: 14px 16px 16px;
        color: var(--muted);
        font-size: 15px;
        line-height: 1.5;
      }}
      figcaption strong {{
        display: block;
        margin-bottom: 5px;
        color: var(--ink);
        font-size: 17px;
      }}
      .routes {{
        display: grid;
        gap: 12px;
      }}
      .route {{
        display: grid;
        grid-template-columns: minmax(220px, 0.7fr) minmax(260px, 1fr) minmax(260px, 1fr);
        gap: 16px;
        padding: 16px;
        border: 1px solid var(--line);
        border-left: 6px solid var(--green);
        background: var(--surface);
      }}
      .route--direct-final-render-from-current-glb {{ border-left-color: var(--red); }}
      .route--existing-glb-lookdev-fallback {{ border-left-color: var(--amber); }}
      .route ul {{
        margin: 8px 0 0;
        padding-left: 18px;
      }}
      .route li + li {{ margin-top: 4px; }}
      .group-grid {{
        display: grid;
        grid-template-columns: repeat(5, minmax(0, 1fr));
        gap: 10px;
      }}
      .group {{
        min-height: 142px;
        padding: 14px;
        border: 1px solid var(--line);
        background: var(--surface);
      }}
      .group h3 {{ margin-bottom: 8px; }}
      .tool-grid, .gate-grid {{
        display: grid;
        gap: 8px;
      }}
      .tool-row, .gate {{
        display: grid;
        grid-template-columns: 190px 92px minmax(0, 1fr);
        gap: 12px;
        align-items: center;
        padding: 12px;
        border: 1px solid var(--line);
        background: var(--surface);
      }}
      .tool-row b, .gate span {{
        color: var(--green);
        text-transform: uppercase;
        font-size: 12px;
      }}
      .tool-row[data-state="missing"] b,
      .gate[data-state="blocked"] span {{
        color: var(--red);
      }}
      .gate[data-state="pending"] span {{ color: var(--amber); }}
      .gate {{
        grid-template-columns: 92px 220px minmax(0, 1fr);
      }}
      footer {{
        padding: 24px 0 42px;
        border-top: 1px solid var(--line);
        color: var(--muted);
        font-size: 14px;
      }}
      @media (max-width: 1040px) {{
        .intro, .section-head, .visuals, .route, .metric-grid, .group-grid {{
          grid-template-columns: 1fr;
        }}
        .tool-row, .gate {{
          grid-template-columns: 1fr;
        }}
      }}
      @media (max-width: 640px) {{
        header, main, footer {{
          width: min(100% - 28px, 1440px);
        }}
        header {{ padding-top: 34px; }}
        .decision-row {{
          grid-template-columns: 1fr;
        }}
      }}
    </style>
  </head>
  <body>
    <header>
      <p class="eyebrow">Goal 18 / STEP-first input chain</p>
      <h1>正式商业渲染前，先把输入链路切回 STEP 权威</h1>
      <div class="intro">
        <p>
          本页验证固定式球阀后续 photoreal still 和 240 帧商业输出应从 STEP 走，
          还是继续沿用当前 GLB。结论：STEP 是最终渲染权威输入；现有 GLB 保留为
          lookdev、blocking 和网页连续性 fallback。
        </p>
        <div class="decision" aria-label="Goal 18 decision">
          <div class="decision-row"><span>Primary</span><strong>{html_escape(verdict['primaryInputForFinalCommercialRender'])}</strong></div>
          <div class="decision-row"><span>Fallback</span><strong>{html_escape(verdict['currentOperationalFallback'])}</strong></div>
          <div class="decision-row"><span>Status</span><strong>{html_escape(manifest['status'])}</strong></div>
          <div class="decision-row"><span>Confidence</span><strong>{html_escape(verdict['confidence'])}</strong></div>
        </div>
      </div>
    </header>

    <main>
      <section class="section" aria-labelledby="evidence-title">
        <div class="section-head">
          <div>
            <p class="eyebrow">01 / evidence</p>
            <h2 id="evidence-title">输入事实</h2>
          </div>
          <p class="note">{html_escape(verdict['decision'])}</p>
        </div>
        <div class="metric-grid">
          <div class="metric"><b>{step['productNameCount']}</b><span>STEP product names</span></div>
          <div class="metric"><b>{step['suggestedMovableGroupCount']}</b><span>semantic motion groups</span></div>
          <div class="metric"><b>{glb['meshBearingNodeCount']}</b><span>GLB mesh-bearing nodes</span></div>
          <div class="metric"><b>{glb['triangles']:,}</b><span>GLB triangles after OCCT tessellation</span></div>
        </div>
      </section>

      <section class="section" aria-labelledby="refs-title">
        <div class="section-head">
          <div>
            <p class="eyebrow">02 / product reference</p>
            <h2 id="refs-title">画册参考仍是材质验收线</h2>
          </div>
          <p class="note">
            STEP 决定几何和产品树，画册决定商业材质观感；GLB 只能证明当前派生模型可用，不能替代上游真值。
          </p>
        </div>
        <div class="visuals">
          <figure>
            <img src="../fixed-ball-valve-brochure-poster.jpg" alt="固定式球阀画册商业产品参考">
            <figcaption><strong>商业主图</strong>用于核对不锈钢层次、深色小件、黑位和产品摄影棚质感。</figcaption>
          </figure>
          <figure>
            <img src="../fixed-ball-valve-structure-reference.jpg" alt="固定式球阀画册结构爆炸参考">
            <figcaption><strong>结构页</strong>用于核对球芯、阀座、密封、阀体和支撑结构的语义边界。</figcaption>
          </figure>
        </div>
      </section>

      <section class="section" aria-labelledby="routes-title">
        <div class="section-head">
          <div>
            <p class="eyebrow">03 / route decision</p>
            <h2 id="routes-title">三条输入路线</h2>
          </div>
          <p class="note">{html_escape(verdict['stopCondition'])}</p>
        </div>
        <div class="routes">
{route_html}
        </div>
      </section>

      <section class="section" aria-labelledby="groups-title">
        <div class="section-head">
          <div>
            <p class="eyebrow">04 / STEP semantic authority</p>
            <h2 id="groups-title">STEP 产品树分组</h2>
          </div>
          <p class="note">
            当前 GLB 有 {glb['duplicateNodeNameGroupCount']} 组重复节点名，且中文节点经过转换后出现 mojibake；正式材质分配必须回看 STEP 审计。
          </p>
        </div>
        <div class="group-grid">
{group_markup(manifest)}
        </div>
      </section>

      <section class="section" aria-labelledby="tools-title">
        <div class="section-head">
          <div>
            <p class="eyebrow">05 / local toolchain</p>
            <h2 id="tools-title">本机链路探测</h2>
          </div>
          <p class="note">
            occt-import-js 转换桥可用；本机未检测到可直接完成商业 still 的离线渲染器。
          </p>
        </div>
        <div class="tool-grid">
{tool_markup(manifest)}
        </div>
      </section>

      <section class="section" aria-labelledby="gates-title">
        <div class="section-head">
          <div>
            <p class="eyebrow">06 / next gates</p>
            <h2 id="gates-title">正式渲染前置门</h2>
          </div>
          <p class="note">
            Goal 18 不产出 photoreal still；它把正式渲染前必须补齐的输入链路验收条件固定下来。
          </p>
        </div>
        <div class="gate-grid">
{gate_markup(manifest)}
        </div>
      </section>
    </main>

    <footer>
      Manifest: <code>input-chain-manifest.json</code>. Source audit: <code>asset/derived/fixed-ball-valve/model-audit-step.json</code>. Previous lookdev: <code>../goal17-offline-lookdev/index.html</code>.
    </footer>
  </body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=OUT)
    args = parser.parse_args()

    manifest = build_manifest()
    out_dir = args.out_dir.resolve()
    write_json(out_dir / "input-chain-manifest.json", manifest)
    (out_dir / "index.html").write_text(build_html(manifest), encoding="utf-8")
    print(json.dumps({
        "manifest": rel(out_dir / "input-chain-manifest.json"),
        "reviewPage": rel(out_dir / "index.html"),
        "status": manifest["status"],
        "primaryInput": manifest["verdict"]["primaryInputForFinalCommercialRender"],
        "fallback": manifest["verdict"]["currentOperationalFallback"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
