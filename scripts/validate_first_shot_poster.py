#!/usr/bin/env python3
"""Validate the immediate first-shot poster and its WebGL handoff evidence."""

from __future__ import annotations

import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "docs" / "experiment"
POSTER = EXPERIMENT / "assets" / "first-shot-poster.jpg"
METRICS = ROOT / "validation-results" / "car-product-story-browser-metrics.json"
LOADING_SCREENSHOT = ROOT / "validation-results" / "car-fpv-poster-loading.png"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def jpeg_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    require(data[:2] == b"\xff\xd8", "poster must be a JPEG")
    offset = 2
    while offset + 9 < len(data):
        require(data[offset] == 0xFF, "invalid JPEG marker")
        marker = data[offset + 1]
        offset += 2
        if marker in {0xD8, 0xD9}:
            continue
        length = struct.unpack(">H", data[offset : offset + 2])[0]
        if marker in {
            0xC0,
            0xC1,
            0xC2,
            0xC3,
            0xC5,
            0xC6,
            0xC7,
            0xC9,
            0xCA,
            0xCB,
            0xCD,
            0xCE,
            0xCF,
        }:
            height, width = struct.unpack(">HH", data[offset + 3 : offset + 7])
            return width, height
        offset += length
    raise AssertionError("poster JPEG has no dimensions")


index = (EXPERIMENT / "index.html").read_text(encoding="utf-8")
styles = (EXPERIMENT / "styles.css").read_text(encoding="utf-8")
app = (EXPERIMENT / "app.js").read_text(encoding="utf-8")
metrics = json.loads(METRICS.read_text(encoding="utf-8"))

require(POSTER.is_file(), "first-shot poster is missing")
require(POSTER.stat().st_size <= 80 * 1024, "poster must remain below 80 KiB")
require(
    jpeg_dimensions(POSTER) == (1224, 765),
    "poster must match the adaptive 1440x900 canvas backing resolution",
)
require('rel="preload"' in index and 'as="image"' in index, "poster must be preloaded")
require('fetchpriority="high"' in index, "poster must have high fetch priority")
require('id="first-shot-poster"' in index, "poster image must exist in static HTML")
require('data-product-frame="poster"' in index, "HTML must start in poster state")
require("body[data-product-frame=\"ready\"] #webgl-canvas" in styles, "canvas handoff CSS is missing")
require("transition: opacity 180ms ease-out" in styles, "canvas handoff must crossfade")
require('body.dataset.productFrame = "ready"' in app, "first rendered frame must release the poster")

functional = metrics["functional"]
before = functional["posterAtDomContentLoaded"]
after = functional["posterAfterWebGLReady"]
require(before["complete"] is True and before["visible"] is True, "poster must be decoded and visible")
require(
    (before["naturalWidth"], before["naturalHeight"]) == (1224, 765),
    "browser poster dimensions changed",
)
require(before["productFrameState"] == "poster", "poster must precede the first 3D frame")
require(before["webglState"] == "loading", "poster evidence must be captured while WebGL loads")
require(before["canvasOpacity"] == 0, "empty WebGL canvas must not cover the poster")
require(after["productFrameState"] == "ready", "first 3D frame must complete the handoff")
require(after["canvasOpacity"] == 1, "ready WebGL canvas must be visible")
require(after["posterVisible"] is True, "poster must remain as a safe underlay")
require(functional["fallbackPosterVisible"] is True, "fallback must retain the poster")
require(functional["loadErrorPosterVisible"] is True, "load failure must retain the poster")

for run in metrics["runs"]:
    loading = run["loading"]
    require(loading["posterDecodedMs"] is not None, "poster decode timing is missing")
    require(
        loading["posterDecodedMs"] < loading["firstUsableProductFrameMs"],
        "poster must decode before the first usable 3D frame",
    )

require(
    LOADING_SCREENSHOT.is_file() and LOADING_SCREENSHOT.stat().st_size > 0,
    "actual loading-state screenshot is missing",
)

print("first-shot poster validation: PASS")
