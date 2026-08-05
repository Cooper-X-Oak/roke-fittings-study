#!/usr/bin/env python3
"""Encode opaque green fixed-ball-valve PNG hero frames to public AVIF."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image


FRAME_COUNT = 240
WIDTH = 1920
HEIGHT = 1080
HERO_GREEN = (0x47, 0x71, 0x4D)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--png-dir", default=".scratch/assets/ztovalve/hero/roke-green-commercial-240/frames")
    parser.add_argument("--avif-dir", default="outcome/public/assets/upload/images/zt-hero-fixed-ball-valve")
    parser.add_argument("--fallback", default="outcome/public/assets/hero/fixed-ball-valve-mobile-fallback.png")
    parser.add_argument("--render-manifest", default="outcome/src/assets-manifest/fixed-ball-valve-roke-green-commercial-240.json")
    parser.add_argument("--out", default="outcome/src/assets-manifest/fixed-ball-valve-roke-green-commercial-240-encode.json")
    parser.add_argument("--quality", type=int, default=58)
    parser.add_argument("--speed", type=int, default=6)
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


def validate_green_rgb(path: Path, label: str) -> dict[str, Any]:
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
            raise RuntimeError(f"{label} corner RGB must be {HERO_GREEN} +/- 3, got {corners}")
        return {"size": list(rgb.size), "cornerRgb": corners, "cornerMaxDelta": max_delta}


def normalize_green_edges(path: Path, border: int = 2) -> dict[str, Any]:
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        if rgb.size != (WIDTH, HEIGHT):
            raise RuntimeError(f"source PNG {path.name} expected {WIDTH}x{HEIGHT}, got {rgb.size}")
        changed = 0
        pixels = rgb.load()
        for x in range(WIDTH):
            for y in range(border):
                if pixels[x, y] != HERO_GREEN:
                    pixels[x, y] = HERO_GREEN
                    changed += 1
                bottom_y = HEIGHT - 1 - y
                if pixels[x, bottom_y] != HERO_GREEN:
                    pixels[x, bottom_y] = HERO_GREEN
                    changed += 1
        for y in range(border, HEIGHT - border):
            for x in range(border):
                if pixels[x, y] != HERO_GREEN:
                    pixels[x, y] = HERO_GREEN
                    changed += 1
                right_x = WIDTH - 1 - x
                if pixels[right_x, y] != HERO_GREEN:
                    pixels[right_x, y] = HERO_GREEN
                    changed += 1
        if changed:
            rgb.save(path, format="PNG", compress_level=9)
        return {"borderPixels": border, "changedPixels": changed}


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    png_dir = project_path(repo_root, args.png_dir)
    avif_dir = project_path(repo_root, args.avif_dir)
    fallback_path = project_path(repo_root, args.fallback)
    render_manifest_path = project_path(repo_root, args.render_manifest)
    out_path = project_path(repo_root, args.out)

    render_manifest = read_json(render_manifest_path)
    if render_manifest.get("status") != "rendered-full-sequence":
        raise RuntimeError("Render manifest must be a full 240-frame sequence before public encoding")

    source_names = expected_names(0, "png")
    actual_source_names = sorted(path.name for path in png_dir.glob("*.png"))
    if actual_source_names != source_names:
        raise RuntimeError(f"Expected PNG frames 0000.png..0239.png in {png_dir}, found {len(actual_source_names)}")

    avif_dir.mkdir(parents=True, exist_ok=True)
    combined = hashlib.sha256()
    frames: list[dict[str, Any]] = []
    source_normalizations: list[dict[str, Any]] = []
    started = time.perf_counter()
    for index, source_name in enumerate(source_names):
        public_name = f"{index + 1:04d}.avif"
        source_path = png_dir / source_name
        avif_path = avif_dir / public_name
        normalization = normalize_green_edges(source_path)
        if normalization["changedPixels"]:
            source_normalizations.append({"frameIndex": index, "sourcePng": source_name, **normalization})
        validate_green_rgb(source_path, f"source PNG {source_name}")
        with Image.open(source_path) as image:
            rgb = image.convert("RGB")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".avif", dir=avif_dir) as tmp:
                tmp_path = Path(tmp.name)
            try:
                rgb.save(tmp_path, format="AVIF", quality=args.quality, speed=args.speed)
                decoded = validate_green_rgb(tmp_path, f"decoded AVIF {public_name}")
                tmp_path.replace(avif_path)
            finally:
                if tmp_path.exists():
                    tmp_path.unlink()
        digest = sha256(avif_path)
        bytes_size = avif_path.stat().st_size
        combined.update(f"{index}:{digest}:{bytes_size}\n".encode("utf-8"))
        frames.append(
            {
                "frameIndex": index,
                "filename": public_name,
                "path": project_rel(repo_root, avif_path),
                "sourcePng": project_rel(repo_root, source_path),
                "bytes": bytes_size,
                "sha256": digest,
                "decoded": decoded,
            }
        )
        if (index + 1) % 30 == 0 or index == FRAME_COUNT - 1:
            print(f"encoded opaque-green AVIF {index + 1}/{FRAME_COUNT}")

    fallback_source = png_dir / "0239.png"
    fallback_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(fallback_source) as image:
        image.convert("RGB").save(fallback_path, format="PNG", compress_level=9)
    fallback = validate_green_rgb(fallback_path, "mobile fallback")

    manifest = {
        "schema": "ztovalve-fixed-ball-valve-opaque-green-avif-encode/v1",
        "kind": "opaque_green_public_encode",
        "bundleId": "roke-green-commercial-240",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "encoder": {"tool": "Pillow", "quality": args.quality, "speed": args.speed},
        "sourcePngDirectory": project_rel(repo_root, png_dir),
        "sourcePngNaming": "0000.png..0239.png",
        "avifDirectory": project_rel(repo_root, avif_dir),
        "avifNaming": "0001.avif..0240.avif",
        "frameCount": len(frames),
        "dimensions": {"width": WIDTH, "height": HEIGHT},
        "background": {"hex": "#47714D", "cornerTolerance": 3},
        "sourcePngNormalization": {
            "contract": "set the two-pixel outer edge to opaque green after Cycles render",
            "normalizedFrameCount": len(source_normalizations),
            "changedPixelTotal": sum(item["changedPixels"] for item in source_normalizations),
            "frames": source_normalizations,
        },
        "fallback": {
            "path": project_rel(repo_root, fallback_path),
            "sourceFrame": project_rel(repo_root, fallback_source),
            "bytes": fallback_path.stat().st_size,
            "sha256": sha256(fallback_path),
            **fallback,
        },
        "totalAvifBytes": sum(frame["bytes"] for frame in frames),
        "combinedAvifSha256": combined.hexdigest(),
        "encodeDurationMs": round((time.perf_counter() - started) * 1000),
        "frames": frames,
    }
    write_json(out_path, manifest)
    render_manifest["publicEncode"] = {
        "path": project_rel(repo_root, out_path),
        "frameCount": len(frames),
        "dimensions": manifest["dimensions"],
        "combinedAvifSha256": manifest["combinedAvifSha256"],
        "fallback": manifest["fallback"],
        "sourcePngNormalization": manifest["sourcePngNormalization"],
    }
    render_frames = {frame.get("frameIndex"): frame for frame in render_manifest.get("frames", [])}
    for index, source_name in enumerate(source_names):
        frame = render_frames.get(index)
        if frame is not None:
            source_path = png_dir / source_name
            frame["bytes"] = source_path.stat().st_size
            frame["sha256"] = sha256(source_path)
    write_json(render_manifest_path, render_manifest)
    print(json.dumps({"status": "pass", "frames": len(frames), "out": project_rel(repo_root, out_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
