#!/usr/bin/env node

import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import { createServer } from "node:http";
import { extname, resolve, sep } from "node:path";

function parseArgs(argv) {
  const result = {};
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index];
    const value = argv[index + 1];
    if (!key?.startsWith("--") || value === undefined) {
      throw new Error(`Invalid argument sequence near ${key ?? "<end>"}`);
    }
    result[key.slice(2)] = value;
  }
  return result;
}

const MIME_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".avif": "image/avif",
  ".mp4": "video/mp4",
  ".webm": "video/webm",
  ".glb": "model/gltf-binary",
};

const args = parseArgs(process.argv.slice(2));
const root = resolve(args.root ?? "docs");
const port = Number(args.port ?? 4182);

function safePath(url) {
  const pathname = decodeURIComponent(new URL(url, "http://local").pathname);
  const candidate = resolve(root, `.${pathname}`);
  if (candidate !== root && !candidate.startsWith(`${root}${sep}`)) {
    return null;
  }
  return candidate;
}

const server = createServer(async (request, response) => {
  try {
    let path = safePath(request.url ?? "/");
    if (!path) {
      response.writeHead(403).end("Forbidden");
      return;
    }
    let info;
    try {
      info = await stat(path);
    } catch {
      response.writeHead(404).end("Not found");
      return;
    }
    if (info.isDirectory()) {
      path = resolve(path, "index.html");
      try {
        info = await stat(path);
      } catch {
        response.writeHead(404).end("Not found");
        return;
      }
    }

    const size = info.size;
    const type = MIME_TYPES[extname(path).toLowerCase()] ??
      "application/octet-stream";
    const commonHeaders = {
      "Accept-Ranges": "bytes",
      "Cache-Control": "no-cache",
      "Content-Type": type,
    };
    const range = request.headers.range;
    if (range) {
      const match = /^bytes=(\d*)-(\d*)$/u.exec(range);
      if (!match) {
        response.writeHead(416, {
          ...commonHeaders,
          "Content-Range": `bytes */${size}`,
        }).end();
        return;
      }
      const start = match[1] ? Number(match[1]) : 0;
      const end = match[2]
        ? Math.min(Number(match[2]), size - 1)
        : size - 1;
      if (start > end || start >= size) {
        response.writeHead(416, {
          ...commonHeaders,
          "Content-Range": `bytes */${size}`,
        }).end();
        return;
      }
      response.writeHead(206, {
        ...commonHeaders,
        "Content-Length": end - start + 1,
        "Content-Range": `bytes ${start}-${end}/${size}`,
      });
      if (request.method === "HEAD") response.end();
      else createReadStream(path, { start, end }).pipe(response);
      return;
    }

    response.writeHead(200, {
      ...commonHeaders,
      "Content-Length": size,
    });
    if (request.method === "HEAD") response.end();
    else createReadStream(path).pipe(response);
  } catch (error) {
    response.writeHead(500).end(error instanceof Error ? error.message : "Error");
  }
});

server.listen(port, "127.0.0.1", () => {
  process.stdout.write(
    `Range-aware Pages server listening on http://127.0.0.1:${port}\n`,
  );
});
