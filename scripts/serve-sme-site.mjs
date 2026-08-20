import {createServer} from "node:http";
import {existsSync, readFileSync, statSync} from "node:fs";
import {dirname, extname, resolve, sep} from "node:path";
import {fileURLToPath} from "node:url";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const webRoot = resolve(projectRoot, "web");
const host = process.env.HERMES_SME_SITE_HOST ?? "127.0.0.1";
const port = Number(process.env.PORT ?? 4185);

const contentTypes = new Map([
  [".css", "text/css; charset=utf-8"],
  [".html", "text/html; charset=utf-8"],
  [".js", "application/javascript; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".md", "text/markdown; charset=utf-8"],
  [".png", "image/png"],
  [".svg", "image/svg+xml"]
]);

function resolveRequestPath(pathname) {
  let decoded;
  try {
    decoded = decodeURIComponent(pathname);
  } catch {
    return null;
  }
  const relative = decoded.replace(/^\/+/, "");
  const requested = resolve(webRoot, relative.endsWith("/") ? `${relative}index.html` : relative);
  if (requested !== webRoot && !requested.startsWith(`${webRoot}${sep}`)) return null;
  if (!existsSync(requested) || !statSync(requested).isFile()) return null;
  return requested;
}

export function createSmeSiteServer() {
  return createServer((request, response) => {
    if (!request.url || !["GET", "HEAD"].includes(request.method ?? "GET")) {
      response.writeHead(405, {allow: "GET, HEAD"});
      response.end();
      return;
    }

    const url = new URL(request.url, "http://localhost");
    if (url.pathname === "/") {
      response.writeHead(302, {location: "/sme/", "cache-control": "no-store"});
      response.end();
      return;
    }
    if (url.pathname === "/sme") {
      response.writeHead(308, {location: "/sme/", "cache-control": "no-store"});
      response.end();
      return;
    }

    const path = resolveRequestPath(url.pathname);
    if (!path) {
      response.writeHead(404, {"content-type": "text/plain; charset=utf-8", "cache-control": "no-store"});
      response.end("Not found.\n");
      return;
    }

    const body = readFileSync(path);
    response.writeHead(200, {
      "content-type": contentTypes.get(extname(path)) ?? "application/octet-stream",
      "content-length": body.byteLength,
      "cache-control": "no-store",
      "x-content-type-options": "nosniff"
    });
    if (request.method === "HEAD") response.end();
    else response.end(body);
  });
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const server = createSmeSiteServer();
  server.listen(port, host, () => {
    process.stdout.write(`Hermes SME site: http://${host}:${port}/sme/\n`);
  });
}
