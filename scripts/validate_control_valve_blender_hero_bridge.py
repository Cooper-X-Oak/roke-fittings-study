#!/usr/bin/env python3
"""Validate the Blender-offline hero preview bridge."""

from __future__ import annotations

import json
import sys
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROUTE = ROOT / "docs" / "control-valve-blender-hero-preview"
CREATIVE = ROOT / "creative" / "control-valve-blender-hero-preview"


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"missing {path.relative_to(ROOT)}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def main() -> None:
    render_manifest_path = CREATIVE / "render-manifest.json"
    encode_manifest_path = CREATIVE / "encode-manifest.json"
    render = read_json(render_manifest_path)
    encode = read_json(encode_manifest_path)
    index = (ROUTE / "index.html").read_text(encoding="utf-8")
    app = (ROUTE / "app.mjs").read_text(encoding="utf-8")

    require(render.get("purpose") == "Blender-offline-to-web-hero technical bridge proof", "render manifest is not the Blender bridge proof")
    require(render.get("boundary", {}).get("onlineSchedulerRole", "").startswith("Three.js/WebGL"), "online scheduler boundary is missing")
    require(render.get("boundary", {}).get("offlineRendererRole", "").startswith("Blender/Cycles"), "offline renderer boundary is missing")
    require(render.get("sourceScheduler") == "creative/control-valve/camera-previs.json", "render does not consume the approved scheduler")
    require(render.get("sourceMaterialExplicitScratchCurves") is False, "clean material source still exposes explicit scratch curves")
    require(render.get("renderer", {}).get("engine") == "Blender Cycles", "renderer is not Blender Cycles")
    require(render.get("renderer", {}).get("uiFree") is True, "render must be UI-free")
    require((ROOT / render["sourceScheduler"]).is_file(), "source scheduler is missing")
    require((ROOT / render["sourceModel"]).is_file(), "source model is missing")
    require((ROOT / render["sourceMaterialManifest"]).is_file(), "source material manifest is missing")
    require(render.get("sourceSchedulerSha256") == sha256(ROOT / render["sourceScheduler"]), "render manifest scheduler hash is stale")
    require(render.get("sourceModelSha256") == sha256(ROOT / render["sourceModel"]), "render manifest model hash is stale")
    require(
        render.get("sourceMaterialManifestSha256") == sha256(ROOT / render["sourceMaterialManifest"]),
        "render manifest material-source hash is stale",
    )

    frames = render.get("frames")
    require(isinstance(frames, list) and len(frames) >= 8, "not enough Blender proof frames were rendered")
    seen_source_frames = [frame.get("sourceFrame") for frame in frames]
    require(seen_source_frames == sorted(seen_source_frames), "source frames must be ordered")
    for frame in frames:
        path = ROOT / frame["path"]
        require(path.is_file() and path.stat().st_size > 10_000, f"missing or tiny frame {frame.get('path')}")

    poster = ROOT / render["deliveryPreview"]["posterPath"]
    require(poster.is_file() and poster.stat().st_size > 10_000, "poster is missing or tiny")

    require(
        encode.get("sourceRenderManifest") == "creative/control-valve-blender-hero-preview/render-manifest.json",
        "encode manifest points at the wrong render manifest",
    )
    require(
        encode.get("sourceRenderManifestSha256") == sha256(render_manifest_path),
        "encode manifest does not match the current render manifest",
    )
    variant = encode.get("variant", {})
    video = ROOT / variant.get("path", "")
    require(variant.get("id") == "gop6", "preview must encode the GOP6 variant")
    require(video.is_file() and video.stat().st_size > 100_000, "GOP6 preview video is missing or tiny")
    require(variant.get("sha256") == sha256(video), "encode manifest video hash is stale")
    require(variant.get("codec") == "h264", "preview video must be H.264")
    require(variant.get("width") == render.get("renderer", {}).get("width"), "encoded video width does not match render")
    require(variant.get("height") == render.get("renderer", {}).get("height"), "encoded video height does not match render")
    require(variant.get("frameCount") == len(frames), "encoded frame count must match rendered frames")
    require(variant.get("keyframeCount", 0) >= 2, "preview GOP6 must contain seekable keyframes")
    policy = encode.get("matchedEncodePolicy", {})
    require(policy.get("gop") == 6, "encode policy must record GOP6")
    require(policy.get("bFrames") == 0, "preview GOP6 must not use B-frames for reverse seek proof")
    require(policy.get("fastStart") is True, "preview video must be fast-start MP4")

    require("blender-hero-preview-gop6.mp4" in index + app, "preview route does not reference the Blender GOP6 video")
    require("window.__BLENDER_HERO_PREVIEW__" in app, "preview metrics hook is missing")

    print("PASS: Blender offline render frames, GOP6 video, poster, and preview route are connected")


if __name__ == "__main__":
    main()
