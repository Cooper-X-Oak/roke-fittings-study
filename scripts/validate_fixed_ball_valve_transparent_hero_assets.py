#!/usr/bin/env python3
"""Validate the transparent fixed ball valve hero assets."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image


FRAME_COUNT = 240


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--png-dir", default=".scratch/assets/ztovalve/hero/v3-transparent-commercial-240/frames")
    parser.add_argument("--avif-dir", default="docs/upload/images/zt-hero-fixed-ball-valve")
    parser.add_argument("--fallback", default="docs/assets/ztovalve/hero/fixed-ball-valve-mobile-fallback.png")
    parser.add_argument("--render-manifest", default="docs/assets/ztovalve/hero/v3-transparent-commercial-240-manifest.json")
    parser.add_argument("--encode-manifest", default="docs/assets/ztovalve/hero/v3-transparent-commercial-240-encode-manifest.json")
    parser.add_argument("--update-manifest", default="true")
    parser.add_argument("--expected-width", type=int, default=960)
    parser.add_argument("--expected-height", type=int, default=540)
    return parser.parse_args()


def project_path(repo_root: Path, value: str) -> Path:
    path = (repo_root / value).resolve()
    path.relative_to(repo_root)
    return path


def project_rel(repo_root: Path, path: Path) -> str:
    return str(path.resolve().relative_to(repo_root)).replace("\\", "/")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def expected_names(start: int, extension: str) -> list[str]:
    return [f"{number:04d}.{extension}" for number in range(start, start + FRAME_COUNT)]


def alpha_stats(path: Path) -> dict[str, Any]:
    with Image.open(path) as image:
        has_alpha = "A" in image.getbands()
        rgba = image.convert("RGBA")
        alpha = rgba.getchannel("A")
        histogram = alpha.histogram()
        width, height = rgba.size
        total = width * height
        transparent = histogram[0]
        opaque = histogram[255]
        nontransparent = total - transparent
        corners = [
            alpha.getpixel((0, 0)),
            alpha.getpixel((width - 1, 0)),
            alpha.getpixel((0, height - 1)),
            alpha.getpixel((width - 1, height - 1)),
        ]
    return {
        "path": str(path).replace("\\", "/"),
        "width": width,
        "height": height,
        "mode": image.mode,
        "hasAlpha": has_alpha,
        "bytes": path.stat().st_size,
        "cornerAlpha": corners,
        "cornerAlphaMax": max(corners),
        "transparentPixels": transparent,
        "opaquePixels": opaque,
        "nonTransparentPixels": nontransparent,
        "transparentRatio": transparent / total,
        "opaqueRatio": opaque / total,
        "nonTransparentRatio": nontransparent / total,
    }


def compact_stats(stats: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    path = Path(stats["path"]).resolve()
    try:
        rel_path = project_rel(repo_root, path)
    except ValueError:
        rel_path = stats["path"]
    return {
        "path": rel_path,
        "width": stats["width"],
        "height": stats["height"],
        "mode": stats["mode"],
        "hasAlpha": stats["hasAlpha"],
        "bytes": stats["bytes"],
        "cornerAlpha": stats["cornerAlpha"],
        "transparentRatio": round(stats["transparentRatio"], 6),
        "nonTransparentRatio": round(stats["nonTransparentRatio"], 6),
    }


def validate_stats(stats: dict[str, Any], label: str, expected_width: int | None, expected_height: int | None) -> None:
    if expected_width and stats["width"] != expected_width:
        raise RuntimeError(f"{label} width expected {expected_width}, got {stats['width']}")
    if expected_height and stats["height"] != expected_height:
        raise RuntimeError(f"{label} height expected {expected_height}, got {stats['height']}")
    if not stats["hasAlpha"]:
        raise RuntimeError(f"{label} does not contain an alpha channel")
    if stats["cornerAlphaMax"] != 0:
        raise RuntimeError(f"{label} corner alpha must be 0, got {stats['cornerAlpha']}")
    if stats["transparentPixels"] == 0 or stats["opaquePixels"] == stats["width"] * stats["height"]:
        raise RuntimeError(f"{label} is fully opaque")
    if stats["nonTransparentPixels"] < 400:
        raise RuntimeError(f"{label} has too few visible product pixels")


def validate_sequence(
    repo_root: Path,
    directory: Path,
    start: int,
    extension: str,
    expected_width: int,
    expected_height: int,
) -> dict[str, Any]:
    if not directory.is_dir():
        raise RuntimeError(f"Missing sequence directory: {directory}")
    expected = expected_names(start, extension)
    actual = sorted(path.name for path in directory.glob(f"*.{extension}"))
    if actual != expected:
        raise RuntimeError(f"Expected {expected[0]}..{expected[-1]} in {directory}, found {len(actual)} matching files")

    samples: list[dict[str, Any]] = []
    transparent_ratios: list[float] = []
    nontransparent_ratios: list[float] = []
    total_bytes = 0
    for index, name in enumerate(actual):
        path = directory / name
        stats = alpha_stats(path)
        validate_stats(stats, f"{extension.upper()} frame {name}", expected_width, expected_height)
        transparent_ratios.append(stats["transparentRatio"])
        nontransparent_ratios.append(stats["nonTransparentRatio"])
        total_bytes += stats["bytes"]
        if index in {0, 119, 183, 239}:
            samples.append(compact_stats(stats, repo_root))

    return {
        "directory": project_rel(repo_root, directory),
        "naming": f"{expected[0]}..{expected[-1]}",
        "frameCount": len(actual),
        "dimensions": {"width": expected_width, "height": expected_height},
        "totalBytes": total_bytes,
        "transparentRatioRange": [round(min(transparent_ratios), 6), round(max(transparent_ratios), 6)],
        "nonTransparentRatioRange": [round(min(nontransparent_ratios), 6), round(max(nontransparent_ratios), 6)],
        "sampleFrames": samples,
    }


def validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    motion = manifest.get("motionEvidence", {})
    max_angle = motion.get("maxBallAngleDegrees")
    if not isinstance(max_angle, (int, float)) or max_angle < 89.0 or max_angle > 90.5:
        raise RuntimeError(f"Manifest maxBallAngleDegrees must prove a 90-degree turn, got {max_angle!r}")
    if motion.get("ballNodeIndex") != 23:
        raise RuntimeError("Manifest must bind the quarter-turn proof to ball nodeIndex 23")
    if motion.get("transparentFrameSequence") is not True:
        raise RuntimeError("Manifest must declare transparentFrameSequence=true")
    scope = manifest.get("scope", {})
    if scope.get("containsBackgroundText") is not False:
        raise RuntimeError("Manifest must declare containsBackgroundText=false")
    if scope.get("containsCameraVisibleBackdrop") is not False:
        raise RuntimeError("Manifest must declare containsCameraVisibleBackdrop=false")
    return {
        "ballNodeIndex": motion.get("ballNodeIndex"),
        "maxBallAngleDegrees": max_angle,
        "transparentFrameSequence": True,
        "containsBackgroundText": False,
        "containsCameraVisibleBackdrop": False,
    }


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    png_dir = project_path(repo_root, args.png_dir)
    avif_dir = project_path(repo_root, args.avif_dir)
    fallback_path = project_path(repo_root, args.fallback)
    render_manifest_path = project_path(repo_root, args.render_manifest)
    encode_manifest_path = project_path(repo_root, args.encode_manifest)

    render_manifest = read_json(render_manifest_path)
    encode_manifest = read_json(encode_manifest_path)
    png = validate_sequence(repo_root, png_dir, 0, "png", args.expected_width, args.expected_height)
    avif = validate_sequence(repo_root, avif_dir, 1, "avif", args.expected_width, args.expected_height)
    fallback_stats = alpha_stats(fallback_path)
    validate_stats(fallback_stats, "mobile fallback", args.expected_width, args.expected_height)
    manifest_evidence = validate_manifest(render_manifest)

    if encode_manifest.get("frameCount") != FRAME_COUNT:
        raise RuntimeError("Encode manifest does not record 240 frames")
    transparent_delivery = encode_manifest.get("transparentDelivery", {})
    if transparent_delivery.get("allDecodedAvifCornersAlphaZero") is not True:
        raise RuntimeError("Encode manifest did not pass decoded AVIF corner alpha checks")

    result = {
        "schema": "ztovalve-fixed-ball-valve-transparent-hero-validation/v1",
        "validatedAt": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "pngSequence": png,
        "avifSequence": avif,
        "fallback": compact_stats(fallback_stats, repo_root),
        "manifestEvidence": manifest_evidence,
        "encodeManifest": {
            "path": project_rel(repo_root, encode_manifest_path),
            "frameCount": encode_manifest.get("frameCount"),
            "dimensions": encode_manifest.get("dimensions"),
            "transparentDelivery": transparent_delivery,
            "totalAvifBytes": encode_manifest.get("totalAvifBytes"),
            "combinedAvifSha256": encode_manifest.get("combinedAvifSha256"),
        },
    }

    if args.update_manifest == "true":
        render_manifest["assetValidation"] = result
        render_manifest["publicEncode"] = result["encodeManifest"]
        write_json(render_manifest_path, render_manifest)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
