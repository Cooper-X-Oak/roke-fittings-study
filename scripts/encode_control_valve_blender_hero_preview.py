#!/usr/bin/env python3
"""Encode Blender-rendered hero proof frames into a short-GOP web video."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


RENDER_MANIFEST = "creative/control-valve-blender-hero-preview/render-manifest.json"
OUTPUT_DIR = "docs/control-valve-blender-hero-preview/assets"
ENCODE_MANIFEST = "creative/control-valve-blender-hero-preview/encode-manifest.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--render-manifest", default=RENDER_MANIFEST)
    parser.add_argument("--output-dir", default=OUTPUT_DIR)
    parser.add_argument("--out", default=ENCODE_MANIFEST)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument("--gop", type=int, default=6)
    parser.add_argument("--crf", type=int, default=20)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: str, args: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run([command, *args], capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f"{command} exited {result.returncode}\n{result.stderr}")
    return result


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    render_manifest_path = (repo_root / args.render_manifest).resolve()
    output_dir = (repo_root / args.output_dir).resolve()
    encode_manifest_path = (repo_root / args.out).resolve()

    render_manifest = json.loads(render_manifest_path.read_text(encoding="utf-8"))
    frames = render_manifest["frames"]
    if not frames:
        raise RuntimeError("Render manifest has no frames")
    frame_dir = (repo_root / render_manifest["deliveryPreview"]["frameDirectory"]).resolve()
    fps = render_manifest["deliveryPreview"]["deliveryFps"]
    width = render_manifest["renderer"]["width"]
    height = render_manifest["renderer"]["height"]
    frame_count = len(frames)

    output_dir.mkdir(parents=True, exist_ok=True)
    encode_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"blender-hero-preview-gop{args.gop}.mp4"
    ffmpeg_args = [
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-framerate",
        str(fps),
        "-start_number",
        "0",
        "-i",
        str(frame_dir / "frame%04d.png"),
        "-frames:v",
        str(frame_count),
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        str(args.crf),
        "-profile:v",
        "high",
        "-level",
        "4.1",
        "-pix_fmt",
        "yuv420p",
        "-g",
        str(args.gop),
        "-keyint_min",
        str(args.gop),
        "-sc_threshold",
        "0",
        "-bf",
        "0",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    run(args.ffmpeg, ffmpeg_args)

    stream_probe = run(
        args.ffprobe,
        [
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-count_frames",
            "-show_entries",
            "stream=codec_name,codec_type,width,height,avg_frame_rate,duration,nb_read_frames",
            "-of",
            "json",
            str(output_path),
        ],
    )
    frame_probe = run(
        args.ffprobe,
        [
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_frames",
            "-show_entries",
            "frame=key_frame",
            "-of",
            "csv=p=0",
            str(output_path),
        ],
    )
    stream = json.loads(stream_probe.stdout).get("streams", [{}])[0]
    keyframe_count = sum(1 for line in frame_probe.stdout.splitlines() if line.strip().startswith("1"))
    manifest = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceRenderManifest": str(render_manifest_path.relative_to(repo_root)).replace("\\", "/"),
        "sourceRenderManifestSha256": sha256(render_manifest_path),
        "independentVariable": "Blender offline render frames encoded for web hero preview",
        "variant": {
            "id": f"gop{args.gop}",
            "gop": args.gop,
            "path": str(output_path.relative_to(repo_root)).replace("\\", "/"),
            "bytes": output_path.stat().st_size,
            "sha256": sha256(output_path),
            "codec": stream.get("codec_name"),
            "codecType": stream.get("codec_type"),
            "width": int(stream.get("width", 0)),
            "height": int(stream.get("height", 0)),
            "frameRate": stream.get("avg_frame_rate"),
            "durationSeconds": float(stream.get("duration", 0)),
            "frameCount": int(stream.get("nb_read_frames", 0)),
            "keyframeCount": keyframe_count,
            "audioStreamCount": 0,
        },
        "matchedEncodePolicy": {
            "container": "MP4",
            "codec": "H.264/libx264",
            "width": width,
            "height": height,
            "frameRate": fps,
            "frameCount": frame_count,
            "preset": "medium",
            "crf": args.crf,
            "profile": "high",
            "level": "4.1",
            "pixelFormat": "yuv420p",
            "gop": args.gop,
            "bFrames": 0,
            "sceneCutDetection": False,
            "fastStart": True,
            "audio": False,
        },
    }
    encode_manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
