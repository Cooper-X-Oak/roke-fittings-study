#!/usr/bin/env python3
"""Static contract checks for the visitor-facing control-valve story."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROUTE = ROOT / "docs" / "control-valve-video"


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def required(source: str, token: str, message: str) -> None:
    if token not in source:
        fail(message)


html = (ROUTE / "index.html").read_text(encoding="utf-8")
script = (ROUTE / "app.mjs").read_text(encoding="utf-8")
styles = (ROUTE / "styles.css").read_text(encoding="utf-8")
poster = ROUTE / "assets" / "first-frame.png"
video = ROUTE / "assets" / "control-valve-gop6.mp4"

if not poster.is_file() or poster.stat().st_size < 100_000:
    fail("business page has no substantive first-frame poster")
if not video.is_file() or video.stat().st_size < 1_000_000:
    fail("business page has no substantive selected GOP 6 video")

for token, message in (
    ('<main id="story"', "business page lacks a main landmark"),
    ('class="video-scroll-shell"', "business page lacks a dedicated video scroll track"),
    ('<nav class="site-nav"', "business page lacks semantic navigation"),
    ('<h1 id="title"', "business page lacks a primary product heading"),
    ('href="../catalog/"', "business page lacks a real catalog action"),
    ('id="poster"', "business page lacks the static poster"),
    ('aria-label="控制阀产品叙事"', "business page route is not identified as a product story"),
):
    required(html, token, message)

for forbidden in (
    "LIVE SEEK EVIDENCE",
    "GOP 3",
    "GOP 10",
    "视频滚动实验",
    "不替代实时 GLB 路线",
    "<form",
):
    if forbidden in html:
        fail(f"visitor-facing route still exposes experiment-only content: {forbidden}")

for token, message in (
    ('const requestedVariant = new URLSearchParams(location.search).get("variant")', "runtime does not expose the isolated benchmark variant selector"),
    ('? `./assets/control-valve-${requestedVariant}.mp4`', "runtime does not resolve benchmark variants safely"),
    (': "./assets/control-valve-gop6.mp4"', "runtime does not default visitors to GOP 6"),
    ("video.currentTime = targetTime", "runtime no longer maps scroll to video time"),
    ("catalogAction", "runtime does not preserve the primary catalog action"),
    ("const sourceFrameCount = 330", "runtime does not target the compact source frame count"),
    ("const lastFrameTime = (sourceFrameCount - 1) / frameRate", "runtime does not map the complete compact source"),
    ("scrollShell.offsetHeight", "runtime does not map video time to the dedicated scroll track"),
    ("prefers-reduced-motion", "runtime does not respect reduced motion"),
):
    required(script, token, message)

for token, message in (
    ("@media (max-width: 900px)", "business page lacks narrow-screen layout"),
    (".video-scroll-shell { height: 280vh; }", "business page does not use the compact 280vh video scroll track"),
    ("@media (prefers-reduced-motion: reduce)", "business page lacks reduced-motion fallback"),
    (":focus-visible", "business page lacks a visible keyboard focus treatment"),
):
    required(styles, token, message)

print("PASS: visitor-facing control-valve product story keeps the verified GOP 6 fallback and truth boundaries")
