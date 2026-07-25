import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import { createServer } from "node:http";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const MIME_TYPES = new Map([
  [".avif", "image/avif"],
  [".css", "text/css; charset=utf-8"],
  [".glb", "model/gltf-binary"],
  [".html", "text/html; charset=utf-8"],
  [".ico", "image/x-icon"],
  [".jpeg", "image/jpeg"],
  [".jpg", "image/jpeg"],
  [".js", "text/javascript; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".ktx2", "image/ktx2"],
  [".png", "image/png"],
  [".svg", "image/svg+xml"],
  [".wasm", "application/wasm"],
  [".webp", "image/webp"],
]);

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repositoryRoot = path.resolve(scriptDirectory, "..");
const rootArgument = process.argv[2] || "docs";
const port = Number.parseInt(process.argv[3] || "4173", 10);
const root = path.resolve(repositoryRoot, rootArgument);

function send(res, statusCode, body, contentType = "text/plain; charset=utf-8") {
  const content = Buffer.from(body);
  res.writeHead(statusCode, {
    "Cache-Control": "no-store",
    "Content-Length": String(content.length),
    "Content-Type": contentType,
  });
  res.end(content);
}

function safePathname(requestURL) {
  const url = new URL(requestURL || "/", "http://127.0.0.1");
  let pathname;

  try {
    pathname = decodeURIComponent(url.pathname);
  } catch {
    return null;
  }

  const relative = pathname.replace(/^\/+/, "");
  const candidate = path.resolve(root, relative);
  const relativeToRoot = path.relative(root, candidate);

  if (relativeToRoot.startsWith("..") || path.isAbsolute(relativeToRoot)) {
    return null;
  }

  return candidate;
}

const server = createServer(async (req, res) => {
  if (req.method !== "GET" && req.method !== "HEAD") {
    send(res, 405, "Method Not Allowed");
    return;
  }

  let filePath = safePathname(req.url);
  if (!filePath) {
    send(res, 400, "Bad Request");
    return;
  }

  try {
    let fileStat = await stat(filePath);
    if (fileStat.isDirectory()) {
      filePath = path.join(filePath, "index.html");
      fileStat = await stat(filePath);
    }

    if (!fileStat.isFile()) {
      send(res, 404, "Not Found");
      return;
    }

    const extension = path.extname(filePath).toLowerCase();
    res.writeHead(200, {
      "Accept-Ranges": "bytes",
      "Cache-Control": "no-store",
      "Content-Length": String(fileStat.size),
      "Content-Type": MIME_TYPES.get(extension) || "application/octet-stream",
      "Cross-Origin-Resource-Policy": "same-origin",
    });

    if (req.method === "HEAD") {
      res.end();
      return;
    }

    createReadStream(filePath).pipe(res);
  } catch (error) {
    if (error && error.code === "ENOENT") {
      send(res, 404, "Not Found");
      return;
    }

    console.error(error);
    send(res, 500, "Internal Server Error");
  }
});

server.listen(port, "127.0.0.1", () => {
  console.log(`Static test server listening at http://127.0.0.1:${port}`);
});

function close() {
  server.close(() => process.exit(0));
}

process.on("SIGINT", close);
process.on("SIGTERM", close);
