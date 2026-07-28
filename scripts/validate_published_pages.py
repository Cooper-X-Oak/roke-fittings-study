#!/usr/bin/env python3
"""Validate the public GitHub Pages deployment for the control-valve story."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request


def fetch(url: str, accept: str) -> tuple[int, str]:
    request = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": "pages-publication-validator"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as error:
        return 0, f"network error: {error.reason}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--path", required=True)
    args = parser.parse_args()

    failures: list[str] = []
    page_status, html = fetch(args.url, "text/html")
    if page_status != 200:
        failures.append(f"public URL returned HTTP {page_status}, expected 200")
    for marker in ("id=\"story\"", "id=\"product-video\""):
        if marker not in html:
            failures.append(f"public page is missing required marker: {marker}")

    app_status, app_source = fetch(urllib.parse.urljoin(args.url, "app.mjs"), "text/javascript")
    if app_status != 200 or "control-valve-gop6.mp4" not in app_source:
        failures.append("public app module does not select the GOP 6 media asset")

    api_path = urllib.parse.urlparse(args.api_url).path.lstrip("/")
    api_result = subprocess.run(["gh", "api", api_path], capture_output=True, text=True, check=False)
    if api_result.returncode:
        failures.append("authenticated Pages API probe failed")
    else:
        try:
            page_config = json.loads(api_result.stdout)
        except json.JSONDecodeError:
            failures.append("Pages API response is not valid JSON")
        else:
            source = page_config.get("source") if isinstance(page_config, dict) else None
            if not isinstance(source, dict):
                failures.append("Pages API response has no source object")
            else:
                if source.get("branch") != args.branch:
                    failures.append(f"Pages source branch is {source.get('branch')!r}, expected {args.branch!r}")
                if source.get("path") != args.path:
                    failures.append(f"Pages source path is {source.get('path')!r}, expected {args.path!r}")

    if failures:
        print("FAIL: published Pages validation")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: public Pages route, source, story container and GOP 6 media are verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
