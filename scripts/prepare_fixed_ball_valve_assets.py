#!/usr/bin/env python3
"""Prepare read-only source copies and first-pass audits for Goal 9."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def copy_without_overwrite(source: Path, destination: Path) -> dict:
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_hash = sha256(source)
    if destination.exists():
        destination_hash = sha256(destination)
        if destination_hash != source_hash:
            raise SystemExit(
                f"Refusing to overwrite existing derived source with a different hash: {destination}"
            )
        copied = False
    else:
        shutil.copy2(source, destination)
        destination_hash = sha256(destination)
        copied = True
    return {
        "source": source.as_posix(),
        "destination": destination.as_posix(),
        "bytes": destination.stat().st_size,
        "sha256": destination_hash,
        "copied": copied,
    }


def flatten_tuple(text: str) -> list[float] | None:
    try:
        return [float(part) for part in text.split(",")]
    except ValueError:
        return None


def audit_step(step_path: Path, output_path: Path) -> dict:
    raw = step_path.read_bytes()
    text = raw.decode("gbk", errors="ignore")
    entities = Counter(re.findall(r"=\s*([A-Z0-9_]+)\s*\(", text))
    products = []
    for name in re.findall(r"PRODUCT\s*\(\s*'([^']*)'", text):
        clean = name.strip()
        if clean and clean not in products:
            products.append(clean)
    colors = []
    float_token = r"([-+0-9.Ee]+)"
    for match in re.findall(
        rf"COLOUR_RGB\s*\(\s*'[^']*'\s*,\s*{float_token}\s*,\s*{float_token}\s*,\s*{float_token}\s*\)",
        text,
        flags=re.DOTALL,
    ):
        color = [round(float(value), 6) for value in match]
        if color not in colors:
            colors.append(color)
    points = []
    for match in re.findall(
        rf"CARTESIAN_POINT\s*\(\s*'[^']*'\s*,\s*\(\s*{float_token}\s*,\s*{float_token}\s*,\s*{float_token}\s*\)\s*\)",
        text,
        flags=re.DOTALL,
    ):
        points.append([float(value) for value in match])
    if points:
        mins = [min(point[index] for point in points) for index in range(3)]
        maxs = [max(point[index] for point in points) for index in range(3)]
    else:
        mins = maxs = [0.0, 0.0, 0.0]
    sizes = [maxs[index] - mins[index] for index in range(3)]
    suggested_groups = [
        {
            "id": "body-pressure-shell",
            "label": "阀体/阀盖压力壳体",
            "members": [name for name in products if any(token in name for token in ("阀体", "阀盖", "堵头"))],
            "motion": "外壳分离和回装；仅作为广告可视化，不声称真实装配顺序。",
            "reviewRequired": True,
        },
        {
            "id": "ball-trunnion-core",
            "label": "球体/固定轴/轴承核心",
            "members": [name for name in products if any(token in name for token in ("球体", "固定轴", "轴承"))],
            "motion": "核心悬停、特写和轻微旋转；不声称流体性能。",
            "reviewRequired": True,
        },
        {
            "id": "stem-packing-drive",
            "label": "阀杆/填料/支架传动密封区",
            "members": [name for name in products if any(token in name for token in ("阀杆", "填料", "支架", "连接轴"))],
            "motion": "纵向层级展开与局部强调；不声称现场维修流程。",
            "reviewRequired": True,
        },
        {
            "id": "seat-seal-system",
            "label": "阀座/密封圈/盘根系统",
            "members": [name for name in products if any(token in name for token in ("阀座", "密封", "盘根"))],
            "motion": "围绕球体做对称层级显影；须由客户确认材料与功能表述。",
            "reviewRequired": True,
        },
        {
            "id": "fasteners-small-hardware",
            "label": "螺柱/螺母/垫片/弹簧小件",
            "members": [
                name
                for name in products
                if any(
                    token in name.casefold()
                    for token in ("螺柱", "螺母", "垫片", "弹簧", "stud", "nut", "washer", "screw", "pin")
                )
            ],
            "motion": "细节点亮或弱化为结构纹理；避免让画面变成零件清单。",
            "reviewRequired": True,
        },
    ]
    audit = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": {
            "path": step_path.as_posix(),
            "bytes": step_path.stat().st_size,
            "sha256": sha256(step_path),
            "format": "STEP AP214",
            "authoringTool": "SolidWorks 2018, detected from header",
            "unit": "millimeter",
            "encoding": "GBK for Chinese product names",
        },
        "entityCounts": dict(entities.most_common()),
        "productNames": products,
        "approximateBoundsMm": {
            "min": [round(value, 6) for value in mins],
            "max": [round(value, 6) for value in maxs],
            "size": [round(value, 6) for value in sizes],
        },
        "colors": colors,
        "suggestedMovableGroups": suggested_groups,
        "issues": [
            "STEP text audit cannot prove mesh-bearing node hierarchy; GLB inspection is required after conversion.",
            "Suggested groups are semantic candidates from part names and must be reviewed by the client or engineer.",
            "Assembly animation order is advertising choreography only unless the client confirms a real service sequence.",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return audit


def extract_pdf_jpegs(pdf_path: Path, output_dir: Path) -> list[dict]:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw = pdf_path.read_bytes()
    pattern = re.compile(
        rb"(\d+)\s+(\d+)\s+obj\b(.*?)\bstream\r?\n(.*?)\r?\nendstream",
        re.DOTALL,
    )
    pages = []
    for match in pattern.finditer(raw):
        object_id = int(match.group(1))
        dictionary = match.group(3)
        stream = match.group(4)
        if b"/Subtype" not in dictionary or b"/Image" not in dictionary:
            continue
        if b"/DCTDecode" not in dictionary:
            continue
        width_match = re.search(rb"/Width\s+(\d+)", dictionary)
        height_match = re.search(rb"/Height\s+(\d+)", dictionary)
        page_number = len(pages) + 1
        page_path = output_dir / f"page-{page_number:02d}.jpg"
        page_path.write_bytes(stream)
        with Image.open(page_path) as image:
            width, height = image.size
        pages.append(
            {
                "page": page_number,
                "objectId": object_id,
                "path": page_path.as_posix(),
                "bytes": page_path.stat().st_size,
                "sha256": sha256(page_path),
                "declaredWidth": int(width_match.group(1)) if width_match else None,
                "declaredHeight": int(height_match.group(1)) if height_match else None,
                "width": width,
                "height": height,
            }
        )
    return pages


def make_contact_sheet(pages: list[dict], output_path: Path) -> None:
    if not pages:
        return
    thumb_w = 322
    thumb_h = 229
    columns = 3
    rows = (len(pages) + columns - 1) // columns
    margin = 18
    label_h = 30
    sheet = Image.new(
        "RGB",
        (
            columns * thumb_w + (columns + 1) * margin,
            rows * (thumb_h + label_h) + (rows + 1) * margin,
        ),
        "#f4f1ec",
    )
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, page in enumerate(pages):
        row, column = divmod(index, columns)
        x = margin + column * (thumb_w + margin)
        y = margin + row * (thumb_h + label_h + margin)
        with Image.open(page["path"]) as image:
            thumb = image.copy()
            thumb.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        ox = x + (thumb_w - thumb.width) // 2
        oy = y + (thumb_h - thumb.height) // 2
        sheet.paste(thumb, (ox, oy))
        draw.rectangle([x, y + thumb_h, x + thumb_w, y + thumb_h + label_h], fill="#111827")
        draw.text((x + 10, y + thumb_h + 8), f"Page {page['page']:02d}", fill="#ffffff", font=font)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, quality=88)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", type=Path, required=True)
    parser.add_argument("--brochure", type=Path, required=True)
    parser.add_argument("--derived-root", type=Path, default=Path("asset/derived/fixed-ball-valve"))
    parser.add_argument("--docs-root", type=Path, default=Path("docs/assets/ztovalve/hero"))
    args = parser.parse_args()

    step_source = args.step.resolve()
    brochure_source = args.brochure.resolve()
    derived_root = args.derived_root
    docs_root = args.docs_root
    if not step_source.is_file():
        raise SystemExit(f"STEP source does not exist: {step_source}")
    if not brochure_source.is_file():
        raise SystemExit(f"Brochure PDF does not exist: {brochure_source}")

    source_manifest = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "step": copy_without_overwrite(step_source, derived_root / "source" / step_source.name),
        "brochure": copy_without_overwrite(brochure_source, derived_root / "source" / brochure_source.name),
    }
    source_manifest_path = derived_root / "source-manifest.json"
    source_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    source_manifest_path.write_text(
        json.dumps(source_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    step_audit = audit_step(derived_root / "source" / step_source.name, derived_root / "model-audit-step.json")
    pages = extract_pdf_jpegs(derived_root / "source" / brochure_source.name, derived_root / "brochure-pages")
    contact_sheet = derived_root / "brochure-contact-sheet.jpg"
    make_contact_sheet(pages, contact_sheet)
    brochure_manifest = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": source_manifest["brochure"],
        "pageImageCount": len(pages),
        "pages": pages,
        "contactSheet": contact_sheet.as_posix(),
        "selectionStatus": "pending visual review",
    }
    brochure_manifest_path = derived_root / "brochure-pages-manifest.json"
    brochure_manifest_path.write_text(
        json.dumps(brochure_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    docs_root.mkdir(parents=True, exist_ok=True)
    summary = {
        "sourceManifest": source_manifest_path.as_posix(),
        "stepAudit": {
            "path": (derived_root / "model-audit-step.json").as_posix(),
            "productNameCount": len(step_audit["productNames"]),
            "suggestedGroupCount": len(step_audit["suggestedMovableGroups"]),
        },
        "brochureManifest": brochure_manifest_path.as_posix(),
        "contactSheet": contact_sheet.as_posix(),
        "docsRoot": docs_root.as_posix(),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
