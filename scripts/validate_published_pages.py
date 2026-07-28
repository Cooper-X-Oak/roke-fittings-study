#!/usr/bin/env python3
"""Validate the public GitHub Pages deployment for the control-valve story."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def fetch(url: str, accept: str) -> tuple[int, str]:
    request = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": "pages-publication-validator"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", errors="replace")


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
    for marker in ("id=\"story\"", "id=\"product-video\"", "control-valve-gop6.mp4"):
        if marker not in html:
            failures.append(f"public page is missing required marker: {marker}")

    api_status, api_body = fetch(args.api_url, "application/vnd.github+json")
    if api_status != 200:
        failures.append(f"Pages API returned HTTP {api_status}, expected 200")
    else:
        try:
            page_config = json.loads(api_body)
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
