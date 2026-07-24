import fs from "node:fs";
import http from "node:http";
import path from "node:path";

const root = path.resolve(process.argv[2] ?? "docs");
const prefix = (process.argv[3] ?? "/roke-fittings-study").replace(/\/$/, "");
const port = Number(process.argv[4] ?? 4177);
const mimeTypes = {
  ".avif": "image/avif",
  ".css": "text/css; charset=utf-8",
  ".gif": "image/gif",
  ".glb": "model/gltf-binary",
  ".html": "text/html; charset=utf-8",
  ".ico": "image/x-icon",
  ".jpeg": "image/jpeg",
  ".jpg": "image/jpeg",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".mp4": "video/mp4",
  ".pdf": "application/pdf",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".webp": "image/webp",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".zip": "application/zip",
};

http
  .createServer((request, response) => {
    const requestUrl = new URL(request.url, `http://${request.headers.host}`);
    let pathname = decodeURIComponent(requestUrl.pathname);
    if (prefix && pathname.startsWith(prefix)) {
      pathname = pathname.slice(prefix.length);
    }
    if (!pathname || pathname.endsWith("/")) {
      pathname += "index.html";
    }

    const target = path.resolve(root, `.${pathname}`);
    if (target !== root && !target.startsWith(`${root}${path.sep}`)) {
      response.writeHead(403).end("Forbidden");
      return;
    }
    if (!fs.existsSync(target) || !fs.statSync(target).isFile()) {
      response.writeHead(404).end("Not found");
      return;
    }

    const stat = fs.statSync(target);
    const headers = {
      "Accept-Ranges": "bytes",
      "Content-Type": mimeTypes[path.extname(target).toLowerCase()] ?? "application/octet-stream",
    };
    const range = request.headers.range?.match(/^bytes=(\d*)-(\d*)$/);

    if (range) {
      const start = range[1] ? Number(range[1]) : 0;
      const end = range[2] ? Math.min(Number(range[2]), stat.size - 1) : stat.size - 1;
      if (start > end || start >= stat.size) {
        response.writeHead(416, { "Content-Range": `bytes */${stat.size}` }).end();
        return;
      }
      response.writeHead(206, {
        ...headers,
        "Content-Length": end - start + 1,
        "Content-Range": `bytes ${start}-${end}/${stat.size}`,
      });
      fs.createReadStream(target, { start, end }).pipe(response);
      return;
    }

    response.writeHead(200, { ...headers, "Content-Length": stat.size });
    if (request.method === "HEAD") {
      response.end();
      return;
    }
    fs.createReadStream(target).pipe(response);
  })
  .listen(port, "127.0.0.1", () => {
    console.log(`Previewing ${root} at http://127.0.0.1:${port}${prefix}/`);
  });
