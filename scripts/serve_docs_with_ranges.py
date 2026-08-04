#!/usr/bin/env python3
"""Serve docs/ with byte-range support for local video seek review."""

from __future__ import annotations

import argparse
import mimetypes
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit


class RangeRequestHandler(SimpleHTTPRequestHandler):
    server_version = "DocsRangeHTTP/1.0"

    def translate_path(self, path: str) -> str:
        root = Path(self.directory).resolve()
        requested = unquote(urlsplit(path).path).lstrip("/")
        candidate = (root / requested).resolve()
        if root not in candidate.parents and candidate != root:
            return str(root / "__blocked__")
        if candidate.is_dir():
            candidate = candidate / "index.html"
        return str(candidate)

    def send_head(self):
        path = Path(self.translate_path(self.path))
        if not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None

        file_size = path.stat().st_size
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        range_header = self.headers.get("Range")
        if not range_header:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(file_size))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            return path.open("rb")

        start, end = self.parse_range(range_header, file_size)
        if start is None:
            self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
            self.send_header("Content-Range", f"bytes */{file_size}")
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            return None

        self.send_response(HTTPStatus.PARTIAL_CONTENT)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        file = path.open("rb")
        file.seek(start)
        self.range_end = end
        return file

    def copyfile(self, source, outputfile) -> None:
        range_end = getattr(self, "range_end", None)
        if range_end is None:
            super().copyfile(source, outputfile)
            return
        remaining = range_end - source.tell() + 1
        while remaining > 0:
            chunk = source.read(min(64 * 1024, remaining))
            if not chunk:
                break
            outputfile.write(chunk)
            remaining -= len(chunk)
        self.range_end = None

    @staticmethod
    def parse_range(range_header: str, file_size: int) -> tuple[int | None, int | None]:
        if not range_header.startswith("bytes=") or "," in range_header:
            return None, None
        start_text, _, end_text = range_header.removeprefix("bytes=").partition("-")
        try:
            if start_text:
                start = int(start_text)
                end = int(end_text) if end_text else file_size - 1
            else:
                suffix = int(end_text)
                start = max(0, file_size - suffix)
                end = file_size - 1
        except ValueError:
            return None, None
        if start < 0 or end < start or start >= file_size:
            return None, None
        return start, min(end, file_size - 1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", default="docs")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4173)
    args = parser.parse_args()

    handler = lambda *handler_args, **kwargs: RangeRequestHandler(  # noqa: E731
        *handler_args,
        directory=str(Path(args.directory).resolve()),
        **kwargs,
    )
    with ThreadingHTTPServer((args.host, args.port), handler) as server:
        print(f"Serving {Path(args.directory).resolve()} at http://{args.host}:{args.port}/")
        server.serve_forever()


if __name__ == "__main__":
    main()
