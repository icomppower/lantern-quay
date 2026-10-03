// Gate harness. Every gate drives the real game sim with fixed time steps (frame-rate independent) and
// writes its report to window.__report (and POSTs it to /report when served by tools/serve.mjs).
import { EYE_CROUCH } from "./sim/game.js";

const DT = 1 / 60;
const yieldUI = () => new Promise((r) => setTimeout(r, 0));

export function startTest(api, params) {
  const { game } = api;
  api.setTest({ step() {} });
  const kind = params.get("test") || "bench";
  const out = (name, data) => {
    window.__report = data;
    const pre = document.createElement("pre");
    pre.style.cssText = "position:fixed;top:8px;right:8px;z-index:99;max-width:46vw;max-height:90vh;overflow:auto;background:#000c;color:#fff;font:11px monospace;padding:8px;white-space:pre-wrap";
    pre.textContent = JSON.stringify(data, null, 1);
    if (!params.has("quiet")) document.body.appendChild(pre);
    fetch("/report?name=" + name, { method: "POST", body: JSON.stringify(data) }).catch(() => {});
  };
  const run = { v1, v2, v3, bench, shot }[kind];
  run(api, params, out).catch((e) => out("error", { error: String(e), stack: e.stack }));
}

// ------------------------------------------------------------------ helpers
function face(P, dir) { P.yaw = Math.atan2(-dir[0], -dir[2]); P.pitch = Math.asin(Math.max(-1, Math.min(1, dir[1]))); }

async function walkPath(game, pts, maxS = 240) {
  const P = game.player;
  let wi = 0, stuckT = 0, last = [...P.p], t = 0, metres = 0;
  while (t < maxS) {
    const w = pts[wi];
    const dx = w[0] - P.p[0], dz = w[1] - P.p[2];
    if (Math.hypot(dx, dz) < 0.3) { wi++; if (wi >= pts.length) return { ok: true, t: +t.toFixed(1), metres: +metres.toFixed(1) }; continue; }
    P.yaw = Math.atan2(-dx, -dz); P.pitch = 0;
    const before = [...P.p];
    game.tick(DT, { mf: 1, run: true });
    metres += Math.hypot(P.p[0] - before[0], P.p[2] - before[2]);
    t += DT;
    if (game.state !== "play") return { ok: false, why: "game over: " + JSON.stringify(game.result), at: P.p.map((v) => +v.toFixed(2)) };
    if (Math.hypot(P.p[0] - last[0], P.p[2] - last[2]) > 0.3) { last = [...P.p]; stuckT = 0; } else stuckT += DT;
    if (stuckT > 4) return { ok: false, why: "stuck", at: P.p.map((v) => +v.toFixed(2)), waypoint: wi };
    if (Math.round(t / DT) % 300 === 0) await yieldUI();
  }
  return { ok: false, why: "timeout" };
}

async function tickUntil(game, cond, maxS, input = () => ({})) {
  let t = 0;
  while (t < maxS) {
    if (cond()) return true;
    game.tick(DT, input());
    t += DT;
    if (game.state !== "play") return cond();
    if (Math.round(t / DT) % 300 === 0) await yieldUI();
  }
  return cond();
}

// Scripted marksman: crouch, scope 10x, aim at the holdover point for `pointFn()`, steady with held breath, fire.
async function shootAt(game, pointFn, { noHoldover = false } = {}) {
  const P = game.player;
  P.crouch = true; P.scoped = true; P.zoom = 10;
  const aimNow = () => {
    const p = pointFn();
    if (noHoldover) { const e = game.eye(); const d = [p[0] - e[0], p[1] - e[1], p[2] - e[2]]; const l = Math.hypot(...d); face(P, d.map((x) => x / l)); return null; }
    const h = game.holdoverAim(p); face(P, h.dir); return h;
  };
  let h = null;
  for (let i = 0; i < 40; i++) { h = aimNow(); game.tick(DT, { hold: true }); }
  const n0 = game.bullets.length;
  h = aimNow();
  game.tick(DT, { hold: true, fire: true });
  const b = game.bullets[n0];
  if (!b) return { fired: false };
  await tickUntil(game, () => !b.alive, 3, () => ({ hold: true }));
  return { fired: true, hit: b.hit ? b.hit.kind : "none", tof: +b.t.toFixed(3), holdover: h && { range: +h.range.toFixed(1), dropMil: +h.drop.toFixed(2), driftMil: +h.drift.toFixed(2), crossWind: +h.cross.toFixed(2) },
    impact: b.p.map((v) => +v.toFixed(3)) };
}

function perchEye(lq, id, crouch = true) {
  const p = lq.perches.find((k) => k.id === id) || { spot: lq.tower.spot };
  return [p.spot[0], p.spot[1] + (crouch ? EYE_CROUCH : 1.7), p.spot[2]];
}

function toPerch(game, lq, id) {
  const p = lq.perches.find((k) => k.id === id);
  game.placePlayer(p.spot[0], p.spot[2], p.roof + 1);
  game.player.crouch = true;
  game.player.eyeY = game.player.p[1] + EYE_CROUCH;
}

// ------------------------------------------------------------------ V1 reachability + sightlines
const ROUTES = {
  common: [[27, -1.8], [44, -1.8], [60, -1.6], [60, -9.8]],
  A: [[116.5, -9.8], [116.5, -15.5], [117.2, -15.5]],
  B_from_south: [[60, -1.6], [116.5, -1.8], [116.5, 5.0], [117.2, 5.0]],
  tower: [[47.25, -9.8], [47.25, -13.0]],
};

async function v1(api, params, out) {
  const { game, lq } = api;
  const res = { reach: {}, sightlines: {} };
  const legs = { A: [...ROUTES.common, ...ROUTES.A], B: ROUTES.B_from_south.slice(0), tower: [...ROUTES.common, ...ROUTES.tower] };
  legs.B = [[27, -1.8], [44, -1.8], ...ROUTES.B_from_south];
  for (const [id, pts] of Object.entries(legs)) {
    game.start(1);
    game.watch.forEach((w) => (w.dead = true)); // reachability only: watchmen are tested in V3
    const walk = await walkPath(game, pts);
    let climb = null;
    if (walk.ok) {
      const n = game.nearLadder();
      if (!n) climb = { ok: false, why: "no ladder in reach", at: game.player.p };
      else {
        game.tick(DT, { interact: true });
        await tickUntil(game, () => !game.player.anim, 20);
        const roof = id === "tower" ? lq.tower.top : lq.perches.find((k) => k.id === id).roof;
        const P = game.player;
        // then walk to the perch spot on the roof
        const spot = id === "tower" ? lq.tower.spot : lq.perches.find((k) => k.id === id).spot;
        const w2 = await walkPath(game, [[spot[0], spot[2]]], 30);
        climb = { ok: Math.abs(P.p[1] - roof) < 0.3 && w2.ok, roof, y: +P.p[1].toFixed(2), to_spot: w2 };
      }
    }
    res.reach[id] = { walk, climb, pass: !!(walk.ok && climb?.ok) };
  }
  // sightlines: simulate each contract's route for 2 loops; seconds the target chest is in clear view per loop
  for (const c of game.contracts) {
    game.start(c.id);
    const loop = c.route.reduce((s, r) => s + r.wait, 0) + 12;
    const seen = { A: 0, B: 0 };
    const eyes = { A: perchEye(lq, "A"), B: perchEye(lq, "B") };
    let t = 0;
    while (t < loop * 2) {
      game.mark.update(DT); game.awning.update(DT);
      const chest = game.mark.target.chest();
      for (const k of ["A", "B"]) if (game.losClear(eyes[k], chest)) seen[k] += DT;
      t += DT;
    }
    res.sightlines[c.id] = { loop_s: loop, A_s_per_loop: +(seen.A / 2).toFixed(1), B_s_per_loop: +(seen.B / 2).toFixed(1),
      pass: seen.A / 2 >= 3 && seen.B / 2 >= 3 };
  }
  res.pass = Object.values(res.reach).every((r) => r.pass) && Object.values(res.sightlines).every((r) => r.pass);
  out("v1", res);
}

// ------------------------------------------------------------------ V2 ballistics
async function v2(api, params, out) {
  const { game, lq } = api;
  const res = { shots: [] };
  game.start(2); // strong crosswind contract
  game.watch.forEach((w) => (w.dead = true));
  toPerch(game, lq, "A");
  const e = game.eye();
  // targets floating over the main canal west of the perch, at exact slant ranges
  const dir = [-0.99, -0.06, 0.06];
  const dl = Math.hypot(...dir);
  for (const [R, noHold] of [[60, false], [120, false], [120, true]]) {
    const c = [e[0] + (dir[0] / dl) * R, e[1] + (dir[1] / dl) * R, e[2] + (dir[2] / dl) * R];
    const clear = game.losClear(e, c);
    game.testTargets = [{ c, r: 0.25 }];
    game.player.rounds = 5;
    game.player.bolt = 0;
    game.bellT = 15; // keep the shots masked so the crowd and target stay put
    const s = await shootAt(game, () => c, { noHoldover: noHold });
    const miss = s.impact ? +Math.hypot(s.impact[0] - c[0], s.impact[1] - c[1], s.impact[2] - c[2]).toFixed(3) : null;
    res.shots.push({ range: R, holdover: !noHold, los_clear: clear, result: s.hit, impact_offset_m: miss, ...s });
    game.player.bolt = 0;
  }
  game.testTargets = [];
  // awning: target = the Bookkeeper's chest at the café; awning forced down, then up
  const aw = game.awning;
  for (const mode of ["down", "up"]) {
    game.player.rounds = 5; game.player.bolt = 0;
    await tickUntil(game, () => game.mark.target.seated && game.mark.wait > 4, 60);
    aw.forced = mode === "down" ? 0 : 1.35;
    game.bellT = 15;
    const tgt = game.mark.target;
    const s = await shootAt(game, () => tgt.chest());
    res.shots.push({ awning: mode, result: s.hit, ...s });
    if (tgt.dead) { tgt.dead = false; tgt.down = 0; }
    aw.forced = null;
  }
  const by = (f) => res.shots.find(f);
  res.pass = by((s) => s.range === 60 && s.holdover).result === "testtarget"
    && by((s) => s.range === 120 && s.holdover).result === "testtarget"
    && by((s) => s.awning === "down").result === "awning"
    && by((s) => s.awning === "up").result === "target";
  res.note = "120 m without holdover is informational: it should miss low/downwind.";
  out("v2", res);
}

// ------------------------------------------------------------------ V3 contracts
async function v3(api, params, out) {
  const { game, lq } = api;
  const res = { contracts: {} };
  const perch = params.get("perch") || "A";
  for (const c of game.contracts) {
    game.start(c.id);
    toPerch(game, lq, perch);
    const P = game.player;
    const eye = () => game.eye();
    const t0 = game.time;
    let shots = [];
    // wait for a stationary, visible target during a bell ring (and the awning up for contract 2); up to 4 minutes
    for (let attempt = 0; attempt < 5 && !game.mark.target.dead && game.state === "play"; attempt++) {
      const ready = () => {
        const m = game.mark, t = m.target;
        if (m.wait < 1.2 || !game.ringing || game.bellPhase() > 6.5) return false;
        if (c.awning && game.awning.angle < 1.25) return false;
        if (!game.losClear(eye(), t.chest())) return false;
        const first = game.hitTest(eye(), t.chest()); // nobody else may stand in the line of fire
        return !!first && first.kind === "target";
      };
      P.crouch = true; P.scoped = true; P.zoom = 10;
      const ok = await tickUntil(game, ready, 240, () => ({ hold: false }));
      if (!ok) { shots.push({ waited: "no window" }); break; }
      const s = await shootAt(game, () => game.mark.target.chest());
      shots.push({ at_s: +(game.time - t0).toFixed(1), result: s.hit, masked: game.maskedShots, ...s.holdover });
    }
    // escape: dive from the perch's canal edge
    let dive = null;
    if (game.mark.target.dead && game.state === "play") {
      P.scoped = false; P.crouch = false;
      const n = game.nearDive();
      if (!n) dive = "not at a dive edge";
      else { game.tick(DT, { dive: true }); await tickUntil(game, () => game.state !== "play", 10); dive = "dove"; }
    }
    res.contracts[c.id] = { name: c.en, result: game.result, shots, dive, detect_peak: +game.detect.toFixed(2),
      pass: !!game.result?.ok };
  }
  // civilian hit must fail the contract
  game.start(1);
  toPerch(game, lq, perch);
  const civ = game.crowd.people.filter((p) => game.losClear(game.eye(), p.chest()))
    .sort((a, b) => Math.hypot(a.p[0] - 119, a.p[2] + 6) - Math.hypot(b.p[0] - 119, b.p[2] + 6))[0];
  let civRes = { found: !!civ };
  if (civ) {
    civ.wait = 99; civ.goal = null;
    const s = await shootAt(game, () => civ.chest());
    await tickUntil(game, () => game.state !== "play", 2);
    civRes = { ...civRes, hit: s.hit, result: game.result, pass: game.result?.reason === "civilian" };
  }
  res.civilian = civRes;
  res.pass = Object.values(res.contracts).every((r) => r.pass) && !!civRes.pass;
  out("v3" + (perch === "A" ? "" : "_" + perch), res);
}

// ------------------------------------------------------------------ V4 perf bench (real frames)
async function bench(api, params, out) {
  const { game, lq, playerCamera, syncVisuals, hud, drawScope, renderer } = api;
  const secs = Number(params.get("secs") || 20);
  api.begin(1);
  toPerch(game, lq, "A");
  game.watch.forEach((w) => (w.dead = false));
  const P = game.player;
  P.scoped = true; P.zoom = 10;
  const ft = [];
  let t = 0;
  api.setTest({
    step(dt) {
      t += dt;
      const tgt = game.mark.target.chest();
      const e = game.eye();
      const d = [tgt[0] - e[0], tgt[1] - e[1], tgt[2] - e[2]]; const l = Math.hypot(...d);
      face(P, d.map((x) => x / l));
      game.detect = 0;
      game.tick(dt, { hold: true });
      if (game.state !== "play") game.state = "play";
      playerCamera(P); syncVisuals(dt); hud(P); drawScope(P, game.rangeAtCrosshair());
      if (t > 2) ft.push(dt * 1000);
      if (t > secs + 2) {
        api.setTest({ step() {} });
        const s = [...ft].sort((a, b) => a - b);
        const avg = ft.reduce((a, b) => a + b, 0) / ft.length;
        out(params.get("name") || "bench", { ua: navigator.userAgent, frames: ft.length, avg_fps: +(1000 / avg).toFixed(1),
          p95_ms: +s[Math.floor(s.length * 0.95)].toFixed(2), p95_fps: +(1000 / s[Math.floor(s.length * 0.95)]).toFixed(1),
          min_fps: +(1000 / s[s.length - 1]).toFixed(1), load_s: +(api.firstFrameAt / 1000).toFixed(2), grid_ms: +api.gridMs.toFixed(0), collision_tris: api.tris,
          draw_calls: renderer.info.render.calls, tris: renderer.info.render.triangles, dpr: renderer.getPixelRatio(),
          viewport: [innerWidth, innerHeight], canvas: [renderer.domElement.width, renderer.domElement.height], scoped: P.zoom + "x" });
      }
    },
  });
}

// ------------------------------------------------------------------ V5 screenshots (Playwright captures when __ready)
async function shot(api, params, out) {
  const { game, lq, camera, playerCamera, syncVisuals, hud, drawScope } = api;
  const view = params.get("view");
  api.begin(1);
  document.getElementById("toast").style.display = "none";
  game.bellT = 18;
  for (let i = 0; i < 600; i++) game.tick(DT, {}); // let the crowd spread out and the target reach the bridge end
  const P = game.player;
  let t = 0;
  api.setTest({
    step(dt) {
      t += dt;
      if (view === "plaza") {
        game.placePlayer(15.5, 1.5); P.crouch = false; P.scoped = false;
        playerCamera(P);
        camera.position.set(15.5, 1.65, 1.5); camera.lookAt(17.5, 3.2, -14);
        document.getElementById("hud").classList.remove("on");
      } else if (view === "scope") {
        toPerch(game, lq, "A");
        const tgt = game.mark.target.chest(), e = game.eye();
        const d = [tgt[0] - e[0], tgt[1] - e[1], tgt[2] - e[2]]; const l = Math.hypot(...d);
        face(P, d.map((x) => x / l)); P.scoped = true; P.zoom = 10; P.swayT = 0;
        playerCamera(P); hud(P); drawScope(P, game.rangeAtCrosshair());
      } else if (view === "perch") {
        document.getElementById("hud").classList.remove("on");
        camera.fov = 50; camera.updateProjectionMatrix();
        camera.position.set(98, 30, 6); camera.lookAt(121, 12, -9);
      } else if (view === "title") {
        document.getElementById("hud").classList.remove("on");
        camera.position.set(150, 40, 18); camera.lookAt(70, 2, -14);
      }
      game.crowd.update(dt * 0); syncVisuals(dt);
      if (t > 1.5) window.__ready = true;
    },
  });
}
