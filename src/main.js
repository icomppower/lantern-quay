import * as THREE from "three";
import { setupScene, loadWorld, buildGrid, uTime } from "./render/world.js";
import { People, ladderMeshes, bellMesh, awningMesh, Tracers } from "./render/actors.js";
import { Game } from "./sim/game.js";
import { rangeCard } from "./sim/ballistics.js";
import { Sfx } from "./audio.js";
import { startTest } from "./tests.js";

const params = new URLSearchParams(location.search);
const $ = (id) => document.getElementById(id);
const show = (id) => { for (const s of document.querySelectorAll(".screen")) s.classList.toggle("on", s.id === id); };

// ------------------------------------------------------------------ renderer + world
const canvas = $("gl");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: "high-performance" });
renderer.setPixelRatio(Math.min(devicePixelRatio, params.has("dpr") ? Number(params.get("dpr")) : 1.5));
renderer.setSize(innerWidth, innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.AgXToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;
const BASE_FOV = 65;
const camera = new THREE.PerspectiveCamera(BASE_FOV, innerWidth / innerHeight, 0.05, 2000);

const meta = await (await fetch("world/world.json")).json();
const lq = meta.lq;
const { scene, sky, followSun } = setupScene(renderer, meta);
$("loadTxt").textContent = "Loading the city… 載入城市";
const world = await loadWorld("world/world.glb", scene, (f) => { $("loadBar").style.width = (f * 100).toFixed(0) + "%"; });
$("loadTxt").textContent = "Charting rooftops… 測量屋頂";
await new Promise((r) => setTimeout(r, 0));
const tg0 = performance.now();
const b = lq.bounds;
const { grid, tris } = buildGrid(world, { minX: b.min[0] - 6, minZ: b.min[2] - 6, maxX: b.max[0] + 6, maxZ: b.max[2] + 6 });
const gridMs = performance.now() - tg0;

const game = new Game(lq, grid);
const people = new People(scene);
ladderMeshes(scene, game.ladders);
const bell = bellMesh(scene, lq.tower.bell);
const awning = awningMesh(scene, lq.cafe.awning);
awning.visible = false;
const tracers = new Tracers(scene);
const sfx = new Sfx();

// ------------------------------------------------------------------ input
const keys = new Set();
const pend = { crouch: false, scope: false, zoom: false, fire: false, interact: false, dive: false };
let look = [0, 0];
let mode = "title"; // title | board | dossier | play | pause | result
let current = 1;
const done = new Set();
addEventListener("keydown", (e) => {
  keys.add(e.code);
  if (mode !== "play") return;
  if (e.code === "KeyC" || e.code === "ControlLeft") pend.crouch = true;
  if (e.code === "KeyZ") pend.scope = true;
  if (e.code === "KeyQ") pend.zoom = true;
  if (e.code === "KeyE") pend.interact = true;
  if (e.code === "KeyF") pend.dive = true;
  if (e.code === "Space") pend.fire = true;
  if (e.code === "KeyP") pause();
});
addEventListener("keyup", (e) => keys.delete(e.code));
canvas.addEventListener("contextmenu", (e) => e.preventDefault());
canvas.addEventListener("mousedown", (e) => {
  if (mode !== "play") return;
  if (document.pointerLockElement !== canvas) { canvas.requestPointerLock?.(); return; }
  if (e.button === 0) pend.fire = true;
  if (e.button === 2) pend.scope = true;
});
addEventListener("wheel", (e) => { if (mode === "play" && game.player?.scoped) pend.zoom = true; }, { passive: true });
addEventListener("mousemove", (e) => {
  if (mode !== "play" || document.pointerLockElement !== canvas) return;
  look[0] += e.movementX * 0.0022; look[1] += e.movementY * 0.0022;
});
document.addEventListener("pointerlockchange", () => {
  if (!document.pointerLockElement && mode === "play" && !params.has("test") && !params.has("bench")) pause();
});
function pause() { mode = "pause"; show("pause"); if (document.pointerLockElement) document.exitPointerLock(); }

// ------------------------------------------------------------------ screens
function board() {
  mode = "board"; show("board");
  const list = $("contractList");
  list.innerHTML = "";
  for (const c of game.contracts) {
    const d = document.createElement("div");
    d.className = "contract";
    d.innerHTML = `<div class="n">CONTRACT ${c.id} 委託</div><div class="t">${c.zh} · ${c.en}</div><div class="sub" style="margin:4px 0 0">${c.brief[0]}</div>${done.has(c.id) ? '<div class="done">✓ completed 已完成</div>' : ""}`;
    d.onclick = () => dossier(c.id);
    list.appendChild(d);
  }
}
function drawPortrait(c) {
  const x = $("portrait").getContext("2d");
  x.fillStyle = "#2a221a"; x.fillRect(0, 0, 84, 104);
  x.fillStyle = c.look.coat; x.beginPath(); x.moveTo(14, 104); x.lineTo(22, 62); x.quadraticCurveTo(42, 52, 62, 62); x.lineTo(70, 104); x.fill();
  x.fillStyle = "#d9a882"; x.beginPath(); x.arc(42, 44, 14, 0, 7); x.fill();
  x.fillStyle = c.look.hatColor;
  if (c.look.hat === "tricorn") { x.beginPath(); x.moveTo(18, 36); x.lineTo(66, 36); x.lineTo(42, 18); x.fill(); }
  else { x.beginPath(); x.ellipse(42, 34, 18, 11, 0, Math.PI, 0); x.fill(); }
  x.fillStyle = "#3e4650"; x.fillRect(2, 70, 10, 34); x.fillRect(72, 70, 10, 34);
}
function dossier(id) {
  current = id;
  const c = game.contracts.find((k) => k.id === id);
  mode = "dossier"; show("dossier");
  $("dN").textContent = `CONTRACT ${c.id} · 檔案 DOSSIER`;
  $("dT").textContent = `${c.zh} · ${c.en}`;
  $("dB").innerHTML = `${c.brief.join(" ")}<br>${c.briefZh}`;
  $("dC").innerHTML = c.clues.map(([k, v]) => `<tr><td>${k}</td><td>${v}</td></tr>`).join("");
  const card = rangeCard([60, 80, 100, 120], 1).map((r) => `${r.r} m: ${r.drop} mil up, ${r.driftPerMs} mil per m/s wind`).join(" · ");
  $("dTips").innerHTML = `Perches 狙擊點: East Loft 東樓頂 and South Warehouse 南倉頂, ladders on their west walls. The bell tower rings every 45 s: shots fired while it rings don't alert the crowd.<br>Range card 彈道表 (zeroed 60 m): ${card}.`;
  drawPortrait(c);
}
function begin() {
  game.start(current);
  awning.visible = game.def.awning;
  mode = "play"; show(null);
  $("hud").classList.add("on");
  sfx.unlock();
  if (!params.has("test")) canvas.requestPointerLock?.();
  toast(`${game.def.zh} · ${game.def.en}`, 2.5);
}
function finish() {
  const r = game.result;
  mode = "result"; show("result");
  $("hud").classList.remove("on");
  if (document.pointerLockElement) document.exitPointerLock();
  const why = { dove: "目標倒下，你躍入運河脫身。Target down; you escaped into the canal.",
    spotted: "被守望者發現。A watchman spotted you.", civilian: "誤傷平民。A civilian was hit.",
    escaped: "目標逃脫。The target escaped after an unmasked shot.", ammo: "子彈用盡。Out of rounds." }[r.reason];
  $("rT").textContent = r.ok ? "委託完成 Contract complete" : "任務失敗 Mission failed";
  $("rT").style.color = r.ok ? "var(--good)" : "var(--bad)";
  $("rS").innerHTML = `${why}<br>${r.time}s · ${r.shots} shot${r.shots === 1 ? "" : "s"} · ${r.masked} masked by the bell${r.alerted ? " · crowd alerted" : ""}`;
  if (r.ok) done.add(current);
}
$("bPlay").onclick = () => { sfx.unlock(); board(); };
$("bGo").onclick = begin;
$("bBack").onclick = board;
$("bRetry").onclick = begin;
$("bBoard").onclick = board;
$("bResume").onclick = () => { mode = "play"; show(null); canvas.requestPointerLock?.(); };
$("bRestart").onclick = begin;
$("bQuit").onclick = () => { $("hud").classList.remove("on"); board(); };

let toastT = 0;
function toast(t, s = 2) { $("toast").innerHTML = t; $("toast").style.opacity = 1; toastT = s; }

// ------------------------------------------------------------------ scope overlay
const sc = $("scope"), sx = sc.getContext("2d");
function drawScope(P, range) {
  const w = (sc.width = innerWidth), h = (sc.height = innerHeight);
  const r = Math.min(w, h) * 0.46, cx = w / 2, cy = h / 2;
  sx.fillStyle = "#050403";
  sx.beginPath(); sx.rect(0, 0, w, h); sx.arc(cx, cy, r, 0, Math.PI * 2, true); sx.fill();
  const g = sx.createRadialGradient(cx, cy, r * 0.82, cx, cy, r);
  g.addColorStop(0, "rgba(0,0,0,0)"); g.addColorStop(1, "rgba(0,0,0,0.75)");
  sx.fillStyle = g; sx.beginPath(); sx.arc(cx, cy, r, 0, Math.PI * 2); sx.fill();
  const pxMil = (h / 2) / Math.tan((camera.fov * Math.PI) / 360) * 0.001;
  sx.strokeStyle = "rgba(10,10,10,0.95)"; sx.fillStyle = "rgba(10,10,10,0.95)"; sx.lineWidth = 1.4;
  sx.beginPath(); sx.moveTo(cx - r, cy); sx.lineTo(cx - 4, cy); sx.moveTo(cx + 4, cy); sx.lineTo(cx + r, cy);
  sx.moveTo(cx, cy - r); sx.lineTo(cx, cy - 4); sx.moveTo(cx, cy + 4); sx.lineTo(cx, cy + r); sx.stroke();
  sx.font = "11px ui-monospace, monospace"; sx.textAlign = "left";
  for (let m = 1; m <= 10; m++) {
    const d = m * pxMil;
    if (d > r * 0.95) break;
    const big = m % 2 === 0 ? 3.2 : 2.2;
    for (const [px, py] of [[cx + d, cy], [cx - d, cy], [cx, cy + d], [cx, cy - d]]) { sx.beginPath(); sx.arc(px, py, big, 0, 7); sx.fill(); }
    if (m % 2 === 0) { sx.fillText(m, cx + 7, cy + d + 4); sx.fillText(m, cx + d - 4, cy - 8); }
  }
  sx.fillStyle = "rgba(246,234,216,0.9)"; sx.textAlign = "center"; sx.font = "13px ui-monospace, monospace";
  sx.fillText(`${P.zoom}×   ${range ? range.toFixed(0) + " m" : "– m"}   ${game.ringing ? "🔔 MASKED" : ""}`, cx, cy + r - 18);
}

// ------------------------------------------------------------------ HUD
function hud(P) {
  $("ammo").textContent = P.rounds;
  $("bolt").textContent = P.bolt > 0 ? "· rebolt 上膛" : "";
  const ws = Math.hypot(game.wind[0], game.wind[2]);
  $("wind").textContent = ws.toFixed(1);
  const fx = -Math.sin(P.yaw), fz = -Math.cos(P.yaw), rx = -fz, rz = fx;
  const wf = game.wind[0] * fx + game.wind[2] * fz, wr = game.wind[0] * rx + game.wind[2] * rz;
  $("windArrow").style.transform = `rotate(${(Math.atan2(wr, wf) * 180) / Math.PI}deg)`;
  $("bell").textContent = game.ringing ? "RINGING 鳴響" : `${Math.ceil(game.bellIn())} s`;
  $("bell").style.color = game.ringing ? "var(--good)" : "";
  $("zoomRow").style.display = P.scoped ? "" : "none";
  $("breathRow").style.display = P.scoped ? "" : "none";
  $("zoom").textContent = P.zoom + "×";
  $("breath").textContent = P.winded > 0 ? "winded 喘" : Math.round(P.breath * 100) + "%";
  $("detBar").style.width = (game.detect * 100).toFixed(0) + "%";
  $("detBar").style.background = game.detect > 0.66 ? "var(--bad)" : "var(--warn)";
  $("detTxt").textContent = game.watch.some((w) => w.sees) ? "· seen 被看見" : "";
  const c = game.def, t = game.mark.target;
  if (!t.dead) {
    $("objT").textContent = `目標 ${c.zh} · ${c.en}`;
    $("objS").textContent = `${c.clues[0][1]} coat, ${c.clues[1][1]}. Climb a perch, scope in, fire while the bell rings.`;
  } else {
    $("objT").textContent = "目標倒下 Target down";
    $("objS").textContent = "Escape: dive into the canal from a canal-side roof edge (F). 從臨河屋頂邊跳水脫身。";
  }
  let pr = "";
  const n = !P.anim && game.nearLadder();
  if (n) pr = n.dir > 0 ? "E 爬梯 Climb the ladder" : "E 落梯 Climb down";
  if (!P.anim && game.nearDive()) pr = "F 跳水 Dive into the canal" + (t.dead ? "" : " (target still alive)");
  $("prompt").style.display = pr ? "block" : "none";
  $("prompt").textContent = pr;
  $("cross").style.display = P.scoped ? "none" : "";
  sc.style.display = P.scoped ? "block" : "none";
  for (const w of game.watch) w.meterHot = game.detect > 0.66;
}

// ------------------------------------------------------------------ frame
const timer = new THREE.Timer();
let firstFrameAt = null;
const v3 = new THREE.Vector3();
let test = null;
let titleT = 0;

function playerCamera(P) {
  const [sy, sp] = P.scoped ? game.swayOffset() : [0, 0];
  camera.position.set(P.p[0], P.eyeY, P.p[2]);
  camera.rotation.set(P.pitch + sp, P.yaw + sy, 0, "YXZ");
  const fov = P.scoped ? BASE_FOV / P.zoom : BASE_FOV;
  if (camera.fov !== fov) { camera.fov = fov; camera.updateProjectionMatrix(); }
}

function syncVisuals(dt) {
  const all = [...game.crowd.people, ...game.mark.people, ...game.watch.map((w) => Object.assign(w, { look: w.look || { coat: "#2c3138", hat: "cap", hatColor: "#7a1f1f", height: 1.06 } }))];
  people.update(all, game.watch);
  awning.rotation.z = -game.awning.angle;
  const ph = game.bellPhase();
  bell.rotation.x = ph < 6 ? Math.sin(ph * 5.5) * 0.45 * (1 - ph / 6) : 0;
  tracers.sync(game.bullets);
  tracers.update(dt);
  for (const e of game.events) {
    if (e === "bell") { sfx.bell(); toast("鐘聲響起 The bell rings: shots are masked", 2.5); }
    else if (e === "shot" || e === "shot_masked") sfx.shot(e === "shot");
    else if (e === "impact:target") toast("目標倒下 Target down: now dive into the canal (F)", 3);
    else if (e === "impact:awning") toast("遮篷擋住了 The awning took the shot", 1.8);
    else if (e === "splash") sfx.splash();
  }
}

function frame() {
  timer.update();
  const dt = Math.min(timer.getDelta(), 0.1);
  uTime.value += dt;
  world.mixer.update(dt);
  if (test) test.step(dt);
  else if (mode === "play") {
    const P = game.player;
    const input = {
      mf: (keys.has("KeyW") || keys.has("ArrowUp") ? 1 : 0) - (keys.has("KeyS") || keys.has("ArrowDown") ? 1 : 0),
      ms: (keys.has("KeyD") || keys.has("ArrowRight") ? 1 : 0) - (keys.has("KeyA") || keys.has("ArrowLeft") ? 1 : 0),
      run: keys.has("ShiftLeft") || keys.has("ShiftRight"), hold: keys.has("ShiftLeft") || keys.has("ShiftRight"),
      look, ...pend,
    };
    look = [0, 0];
    for (const k in pend) pend[k] = false;
    game.tick(dt, input);
    playerCamera(P);
    syncVisuals(dt);
    hud(P);
    if (P.scoped) drawScope(P, game.rangeAtCrosshair());
    if (game.state === "over") setTimeout(finish, 900), (mode = "ending");
  } else if (mode === "ending") {
    game.mark.update(dt); game.crowd.update(dt); syncVisuals(dt);
  } else if (mode !== "pause") {
    titleT += dt;
    const a = titleT * 0.03 + 0.6;
    camera.position.set(70 + Math.cos(a) * 95, 42, -28 + Math.sin(a) * 70);
    camera.lookAt(62, 4, -24);
    if (camera.fov !== BASE_FOV) { camera.fov = BASE_FOV; camera.updateProjectionMatrix(); }
    if (game.crowd) { game.crowd.update(dt); game.mark.update(dt); syncVisuals(dt); }
  }
  if (toastT > 0) { toastT -= dt; if (toastT <= 0) $("toast").style.opacity = 0; }
  camera.getWorldDirection(v3);
  followSun(v3.multiplyScalar(game.player?.scoped ? 40 : 20).add(camera.position).setY(0));
  sky.position.copy(camera.position);
  renderer.render(scene, camera);
  if (firstFrameAt === null) {
    firstFrameAt = performance.now();
    if (!params.has("test") && !params.has("bench")) { show("title"); }
  }
  requestAnimationFrame(frame);
}
addEventListener("resize", () => { camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth, innerHeight); });

// a crowd behind the title card
game.start(1);
mode = "title";
requestAnimationFrame(frame);

const api = { THREE, game, grid, camera, renderer, scene, world, meta, lq, tris, gridMs, playerCamera, syncVisuals, hud, drawScope,
  begin: (id) => { current = id; begin(); }, show, get firstFrameAt() { return firstFrameAt; }, setTest: (t) => (test = t) };
window.__lq = api;
if (params.has("test") || params.has("bench")) startTest(api, params);
