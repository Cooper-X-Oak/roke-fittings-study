#!/usr/bin/env python3
"""Validate opaque green fixed-ball-valve hero assets."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops


FRAME_COUNT = 240
WIDTH = 1920
HEIGHT = 1080
HERO_GREEN = (0x47, 0x71, 0x4D)
MAX_FILE_SIZE = 100 * 1024 * 1024


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--png-dir", default=".scratch/assets/ztovalve/hero/roke-green-commercial-240/frames")
    parser.add_argument("--avif-dir", default="outcome/public/assets/upload/images/zt-hero-fixed-ball-valve")
    parser.add_argument("--fallback", default="outcome/public/assets/hero/fixed-ball-valve-mobile-fallback.png")
    parser.add_argument("--render-manifest", default="outcome/src/assets-manifest/fixed-ball-valve-roke-green-commercial-240.json")
    parser.add_argument("--encode-manifest", default="outcome/src/assets-manifest/fixed-ball-valve-roke-green-commercial-240-encode.json")
    parser.add_argument("--out", default="outcome/src/assets-manifest/fixed-ball-valve-roke-green-commercial-240-validation.json")
    return parser.parse_args()


def project_path(repo_root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else repo_root / path


def project_rel(repo_root: Path, path: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def expected_names(start: int, extension: str) -> list[str]:
    return [f"{number:04d}.{extension}" for number in range(start, start + FRAME_COUNT)]


def non_background_bbox(image: Image.Image) -> dict[str, int] | None:
    background = Image.new("RGB", image.size, HERO_GREEN)
    diff = ImageChops.difference(image, background)
    mask = diff.convert("L").point(lambda value: 255 if value > 9 else 0)
    bbox = mask.getbbox()
    if bbox is None:
        return None
    left, top, right, bottom = bbox
    return {
        "left": left,
        "top": top,
        "right": right,
        "bottom": bottom,
        "width": right - left,
        "height": bottom - top,
        "centerX": round((left + right) / 2),
        "centerY": round((top + bottom) / 2),
    }


def image_stats(path: Path, label: str) -> dict[str, Any]:
    if path.stat().st_size == 0:
        raise RuntimeError(f"{label} is empty")
    if path.stat().st_size >= MAX_FILE_SIZE:
        raise RuntimeError(f"{label} exceeds GitHub 100 MB limit")
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        if rgb.size != (WIDTH, HEIGHT):
            raise RuntimeError(f"{label} expected {WIDTH}x{HEIGHT}, got {rgb.size}")
        corners = [
            rgb.getpixel((0, 0)),
            rgb.getpixel((WIDTH - 1, 0)),
            rgb.getpixel((0, HEIGHT - 1)),
            rgb.getpixel((WIDTH - 1, HEIGHT - 1)),
        ]
        max_delta = max(abs(value - target) for pixel in corners for value, target in zip(pixel, HERO_GREEN))
        if max_delta > 3:
            raise RuntimeError(f"{label} background corners drifted: {corners}")
        bbox = non_background_bbox(rgb)
        if bbox is None:
            raise RuntimeError(f"{label} has no non-background product pixels")
        return {
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "size": [WIDTH, HEIGHT],
            "cornerRgb": corners,
            "cornerMaxDelta": max_delta,
            "bbox": bbox,
        }


def validate_sequence(repo_root: Path, directory: Path, start: int, extension: str) -> dict[str, Any]:
    names = expected_names(start, extension)
    actual = sorted(path.name for path in directory.glob(f"*.{extension}"))
    if actual != names:
        raise RuntimeError(f"Expected {names[0]}..{names[-1]} in {directory}, found {len(actual)}")
    sample_indices = [0, 30, 72, 120, 168, 208, 239]
    samples = []
    total_bytes = 0
    for index, name in enumerate(names):
        path = directory / name
        stats = image_stats(path, f"{extension.upper()} frame {name}")
        total_bytes += stats["bytes"]
        if index in sample_indices:
            samples.append({"frameIndex": index, "path": project_rel(repo_root, path), **stats})
    first = samples[0]["bbox"]
    last = samples[-1]["bbox"]
    if extension == "png":
        if not (1500 <= first["width"] <= 1880 and 210 <= first["height"] <= 520):
            raise RuntimeError(f"First frame composition outside expected wide exploded range: {first}")
        if not (700 <= last["width"] <= 1250 and 380 <= last["height"] <= 920):
            raise RuntimeError(f"Last frame composition outside expected final product range: {last}")
    return {
        "directory": project_rel(repo_root, directory),
        "naming": f"{names[0]}..{names[-1]}",
        "frameCount": len(actual),
        "totalBytes": total_bytes,
        "sampleFrames": samples,
    }


def validate_hold(directory: Path) -> dict[str, Any]:
    hold_indices = [204, 216, 228, 239]
    bboxes = []
    for index in hold_indices:
        stats = image_stats(directory / f"{index:04d}.png", f"hold PNG {index:04d}.png")
        bboxes.append(stats["bbox"])
    width_delta = max(b["width"] for b in bboxes) - min(b["width"] for b in bboxes)
    height_delta = max(b["height"] for b in bboxes) - min(b["height"] for b in bboxes)
    center_delta = max(abs(b["centerX"] - bboxes[-1]["centerX"]) + abs(b["centerY"] - bboxes[-1]["centerY"]) for b in bboxes)
    if width_delta > 8 or height_delta > 8 or center_delta > 8:
        raise RuntimeError(f"Final hold is not stable enough: {bboxes}")
    return {"frameIndices": hold_indices, "bboxWidthDelta": width_delta, "bboxHeightDelta": height_delta, "centerDelta": center_delta}


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    png_dir = project_path(repo_root, args.png_dir)
    avif_dir = project_path(repo_root, args.avif_dir)
    fallback_path = project_path(repo_root, args.fallback)
    render_manifest_path = project_path(repo_root, args.render_manifest)
    encode_manifest_path = project_path(repo_root, args.encode_manifest)
    out_path = project_path(repo_root, args.out)

    render_manifest = read_json(render_manifest_path)
    encode_manifest = read_json(encode_manifest_path)
    if render_manifest.get("scope", {}).get("quarterTurnFunctionClaim") is not False:
        raise RuntimeError("Render manifest must explicitly avoid a 90-degree function claim")
    if encode_manifest.get("frameCount") != FRAME_COUNT:
        raise RuntimeError("Encode manifest frame count is not 240")

    png = validate_sequence(repo_root, png_dir, 0, "png")
    avif = validate_sequence(repo_root, avif_dir, 1, "avif")
    fallback = {"path": project_rel(repo_root, fallback_path), **image_stats(fallback_path, "mobile fallback")}
    hold = validate_hold(png_dir)
    result = {
        "schema": "ztovalve-fixed-ball-valve-roke-green-validation/v1",
        "kind": "opaque_green_asset_validation",
        "bundleId": "roke-green-commercial-240",
        "validatedAt": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "background": {"hex": "#47714D", "cornerTolerance": 3},
        "pngSequence": png,
        "avifSequence": avif,
        "fallback": fallback,
        "stableHold": hold,
        "renderManifest": project_rel(repo_root, render_manifest_path),
        "encodeManifest": project_rel(repo_root, encode_manifest_path),
    }
    write_json(out_path, result)
    render_manifest["assetValidation"] = {"path": project_rel(repo_root, out_path), "status": "pass", "stableHold": hold, "samplePngFrames": png["sampleFrames"]}
    write_json(render_manifest_path, render_manifest)
    print(json.dumps({"status": "pass", "out": project_rel(repo_root, out_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
