"""Shared dependency-free helpers for control-valve acceptance checks."""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "docs/control-valve/assets/control-valve-shot-ready.glb"
CREATIVE = ROOT / "creative/control-valve"
ROUTE = ROOT / "docs/control-valve"
EXPECTED_GROUPS = {
    "VALVE_BODY_BONNET",
    "PNEUMATIC_ACTUATOR",
    "STEM_CASCADE_PLUG",
    "CASCADE_TRIM",
    "SEALS_SUPPORT",
    "PRODUCTION_DETAILS",
}


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def read_json(path: Path):
    if not path.is_file():
        fail(f"missing JSON artifact: {path.relative_to(ROOT)}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"invalid UTF-8 JSON {path.relative_to(ROOT)}: {exc}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def read_glb_json(path: Path = ASSET):
    if not path.is_file():
        fail(f"missing GLB: {path.relative_to(ROOT)}")
    data = path.read_bytes()
    if len(data) < 20:
        fail("GLB is truncated")
    magic, version, declared_length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or declared_length != len(data):
        fail("GLB header is invalid")
    offset = 12
    while offset + 8 <= len(data):
        chunk_length, chunk_type = struct.unpack_from("<II", data, offset)
        offset += 8
        payload = data[offset : offset + chunk_length]
        offset += chunk_length
        if chunk_type == 0x4E4F534A:
            return json.loads(payload.rstrip(b" \t\r\n\0").decode("utf-8"))
    fail("GLB has no JSON chunk")


def node_parent_map(document: dict) -> dict[int, int]:
    parents = {}
    for parent_index, node in enumerate(document.get("nodes", [])):
        for child_index in node.get("children", []):
            parents[child_index] = parent_index
    return parents


def controlled_ancestor(
    document: dict,
    node_index: int,
    parents: dict[int, int],
) -> str | None:
    nodes = document.get("nodes", [])
    cursor = node_index
    while cursor in range(len(nodes)):
        name = nodes[cursor].get("name")
        if name in EXPECTED_GROUPS:
            return name
        if cursor not in parents:
            break
        cursor = parents[cursor]
    return None
