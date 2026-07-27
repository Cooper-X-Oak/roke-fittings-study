#!/usr/bin/env python3
"""Validate the current public-reference commercial look boundary."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "docs/control-valve/app.mjs").read_text(encoding="utf-8")
video = (ROOT / "docs/control-valve-video/assets/control-valve-gop6.mp4")
for token in ("MATERIAL_PROFILES", "VALVE_BODY_BONNET", "PNEUMATIC_ACTUATOR", "CASCADE_TRIM", "shadowMap.enabled = true"):
    if token not in source: raise SystemExit(f"FAIL: commercial material treatment misses {token}")
if "0x1d262b" in source or "0x11181c" in source: raise SystemExit("FAIL: retired black coating remains in material profiles")
if not video.is_file() or video.stat().st_size < 1_000_000: raise SystemExit("FAIL: current GOP 6 commercial render is missing")
print("PASS: differentiated metallic commercial look and current GOP 6 asset are present")
