// Static server for the viewer + a POST /report endpoint used by the bench/walk tests.
// Usage: node tools/serve.mjs [port] [dir=dist]   (no dependencies)
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repo = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const dir = path.resolve(process.argv[3] || path.join(repo, "dist"));
const reports = path.join(repo, "reports");
fs.mkdirSync(reports, { recursive: true });
const port = Number(process.argv[2] || 8765);
const types = { ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript", ".json": "application/json",
  ".glb": "model/gltf-binary", ".png": "image/png", ".jpg": "image/jpeg", ".css": "text/css", ".svg": "image/svg+xml" };

http.createServer((req, res) => {
  const url = new URL(req.url, "http://x");
  if (req.method === "POST" && url.pathname === "/report") {
    let body = "";
    req.on("data", (c) => (body += c));
    req.on("end", () => {
      const name = (url.searchParams.get("name") || "report").replace(/[^\w-]/g, "");
      fs.writeFileSync(path.join(reports, name + ".json"), body);
      console.log("REPORT", name, body.slice(0, 400));
      res.end("ok");
    });
    return;
  }
  let p = path.join(dir, decodeURIComponent(url.pathname));
  if (!p.startsWith(dir)) { res.writeHead(403); return res.end(); }
  if (fs.existsSync(p) && fs.statSync(p).isDirectory()) p = path.join(p, "index.html");
  fs.readFile(p, (err, data) => {
    if (err) { res.writeHead(404); return res.end("not found"); }
    res.writeHead(200, { "Content-Type": types[path.extname(p)] || "application/octet-stream", "Cache-Control": "no-store" });
    res.end(data);
  });
}).listen(port, () => console.log(`viewer on http://localhost:${port}/`));
