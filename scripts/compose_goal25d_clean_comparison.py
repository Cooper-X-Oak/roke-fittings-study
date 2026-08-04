#!/usr/bin/env python3
"""Compose the Goal 25-D old-vs-clean material comparison still."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


GOAL25D_DIR = Path("docs/assets/ztovalve/hero/goal25d-zoned-body-material-proof")
COMPARISON_ID = "00-old-vs-clean-comparison"
OLD_ID = "01-old-trace-scratch-look"
CLEAN_ID = "02-clean-pbr-stainless-look"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    names = ["arialbd.ttf", "segoeuib.ttf"] if bold else ["arial.ttf", "segoeui.ttf"]
    for name in names:
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def find_still(manifest: dict, still_id: str) -> dict:
    for still in manifest["stills"]:
        if still["id"] == still_id:
            return still
    raise SystemExit(f"missing still in manifest: {still_id}")


def compose(repo_root: Path, manifest_path: Path, out_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    old_still = find_still(manifest, OLD_ID)
    clean_still = find_still(manifest, CLEAN_ID)
    old_image = Image.open(repo_root / old_still["path"]).convert("RGB")
    clean_image = Image.open(repo_root / clean_still["path"]).convert("RGB")

    width = old_image.width + clean_image.width
    label_height = 118
    height = label_height + max(old_image.height, clean_image.height)
    canvas = Image.new("RGB", (width, height), (226, 231, 226))
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(30, bold=True)
    caption_font = load_font(18)

    left_box = (0, label_height, old_image.width, label_height + old_image.height)
    right_box = (old_image.width, label_height, width, label_height + clean_image.height)
    canvas.paste(old_image, left_box[:2])
    canvas.paste(clean_image, right_box[:2])

    draw.rectangle((0, 0, width, label_height), fill=(226, 231, 226))
    draw.rectangle((old_image.width - 2, 0, old_image.width + 2, height), fill=(122, 129, 124))
    draw.text((32, 24), "OLD: explicit trace-scratch look", fill=(18, 23, 21), font=title_font)
    draw.text((32, 68), "Visible curve rings on flange, bore and bolt-hole zones", fill=(84, 94, 89), font=caption_font)
    draw.text((old_image.width + 32, 24), "CLEAN PBR STAINLESS", fill=(18, 23, 21), font=title_font)
    draw.text((old_image.width + 32, 68), "No explicit scratch curves in the 25-D main render", fill=(84, 94, 89), font=caption_font)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, format="PNG", optimize=True)

    comparison = {
        "id": COMPARISON_ID,
        "title": "old trace-scratch look vs clean PBR stainless look",
        "path": str(out_path.relative_to(repo_root)).replace("\\", "/"),
        "width": canvas.width,
        "height": canvas.height,
        "bytes": out_path.stat().st_size,
        "sha256": sha256(out_path),
        "inputs": [OLD_ID, CLEAN_ID],
    }
    for index, still in enumerate(manifest["stills"]):
        if still["id"] == COMPARISON_ID:
            manifest["stills"][index] = comparison
            break
    else:
        manifest["stills"].insert(0, comparison)
    manifest["comparisonStillId"] = COMPARISON_ID
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return comparison


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--manifest", default=str(GOAL25D_DIR / "render-manifest.json"))
    parser.add_argument("--out", default=str(GOAL25D_DIR / "stills" / "00-old-vs-clean-comparison.png"))
    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()
    comparison = compose(repo_root, (repo_root / args.manifest).resolve(), (repo_root / args.out).resolve())
    print(json.dumps(comparison, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
