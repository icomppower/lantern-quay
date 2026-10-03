// Runs the in-browser gates in Playwright Chromium against the built game (dist/), saves reports/ and shots/.
// Usage: node tests/gates.mjs [v1 v2 v3 shots]   (default: all)
import { chromium } from "playwright";
import { spawn } from "node:child_process";
import fs from "node:fs";

const PORT = 8790;
const which = process.argv.slice(2);
const want = (k) => !which.length || which.includes(k);
fs.mkdirSync("reports", { recursive: true });
fs.mkdirSync("shots", { recursive: true });
const srv = spawn("node", ["tools/serve.mjs", String(PORT)], { stdio: "ignore" });
await new Promise((r) => setTimeout(r, 600));
const browser = await chromium.launch({ args: ["--use-angle=metal", "--enable-gpu", "--ignore-gpu-blocklist"] });
const summary = {};
async function page(q, w = 1280, h = 720) {
  const p = await browser.newPage({ viewport: { width: w, height: h } });
  p.on("pageerror", (e) => console.log("PAGEERROR", e.message));
  p.on("console", (m) => { if (m.type() === "error") console.log("CONSOLE", m.text()); });
  await p.goto(`http://localhost:${PORT}/?${q}`);
  return p;
}
async function gate(name, q, timeout = 600000) {
  const t0 = Date.now();
  const p = await page(q + "&quiet");
  await p.waitForFunction(() => window.__report, null, { timeout, polling: 500 });
  const rep = await p.evaluate(() => window.__report);
  fs.writeFileSync(`reports/${name}.json`, JSON.stringify(rep, null, 1));
  summary[name] = { pass: rep.pass, secs: Math.round((Date.now() - t0) / 1000) };
  console.log(name, rep.pass ? "PASS" : "FAIL", JSON.stringify(rep).slice(0, 1500));
  await p.close();
}
try {
  if (want("v1")) await gate("v1", "test=v1");
  if (want("v2")) await gate("v2", "test=v2");
  if (want("v3")) await gate("v3", "test=v3");
  if (want("v3b")) await gate("v3_B", "test=v3&perch=B");
  if (want("shots")) {
    for (const [file, view] of [["plaza_street", "plaza"], ["scope_bridge", "scope"], ["perch_overview", "perch"], ["title", "title"]]) {
      const p = await page(`test=shot&view=${view}`, 1920, 1080);
      await p.waitForFunction(() => window.__ready, null, { timeout: 180000, polling: 300 });
      await p.screenshot({ path: `shots/${file}.png` });
      console.log("shot", file);
      await p.close();
    }
  }
} finally {
  fs.writeFileSync("reports/gates_summary.json", JSON.stringify(summary, null, 1));
  await browser.close();
  srv.kill();
}
