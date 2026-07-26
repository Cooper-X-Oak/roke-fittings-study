#!/usr/bin/env python3
"""Bind the post-compression GLB bytes back to the conversion report."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

GROUPS = (
    "VALVE_BODY_BONNET",
    "PNEUMATIC_ACTUATOR",
    "STEM_CASCADE_PLUG",
    "CASCADE_TRIM",
    "SEALS_SUPPORT",
    "PRODUCTION_DETAILS",
)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest().upper()


def normalize_semantic_node_names(path: Path) -> None:
    """Remove CadQuery's ``_part`` suffix without rewriting binary buffers."""

    data = bytearray(path.read_bytes())
    magic, version, declared_length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or declared_length != len(data):
        raise SystemExit("invalid GLB before semantic-name normalization")
    json_length, json_type = struct.unpack_from("<II", data, 12)
    if json_type != 0x4E4F534A:
        raise SystemExit("first GLB chunk is not JSON")
    start = 20
    end = start + json_length
    payload = bytes(data[start:end])
    for group in GROUPS:
        original = f'"{group}_part"'.encode()
        replacement = f'"{group}"'.encode() + b" " * 5
        if payload.count(original) < 1:
            raise SystemExit(f"missing CadQuery semantic suffix for {group}")
        payload = payload.replace(original, replacement)
    data[start:end] = payload
    path.write_bytes(data)


parser = argparse.ArgumentParser()
parser.add_argument("--asset", type=Path, required=True)
parser.add_argument("--report", type=Path, required=True)
args = parser.parse_args()

normalize_semantic_node_names(args.asset)
report = json.loads(args.report.read_text(encoding="utf-8"))
report["compression"] = {
    "tool": "glTF Transform 4.3.0",
    "extension": "KHR_draco_mesh_compression",
    "method": "edgebreaker",
    "optimization": "join compatible primitives within each semantic mesh, weld, then Draco",
    "primitiveCount": 6,
    "textures": "none in source asset; KTX2 not applicable",
}
report["output"] = {
    "path": args.asset.as_posix(),
    "bytes": args.asset.stat().st_size,
    "sha256": digest(args.asset),
}
args.report.write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print(json.dumps(report["output"], indent=2))
