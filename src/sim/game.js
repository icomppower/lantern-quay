// Lantern Quay v1 game state: player movement, ladders, dive, rifle, bell, wind, detection, contract result.
// Framework-free. The world is a TriGrid (static triangles) plus the dynamic awning and people.
import { WALK, SHOT } from "./grid.js";
import { RIFLE, fire, advance, segSphere, solution } from "./ballistics.js";
import { Crowd, Mark, Watchman, DETECT } from "./people.js";
import { Awning } from "./awning.js";
import { contracts } from "./contracts.js";

export const EYE = 1.7, EYE_CROUCH = 1.25, RADIUS = 0.3, STEP = 0.45, DROP = 0.6;
export const BELL = { period: 45, ring: 6, first: 14 };
const HEIGHTS = [0.35, 0.9, 1.5];

export class Game {
  constructor(lq, grid) {
    this.lq = lq; this.grid = grid;
    this.contracts = contracts(lq);
    this.world = {
      groundAt: (x, y, z) => grid.groundAt(x, y, z, 1.0, 4.0),
      clear: (a, b) => this.losClear(a, b),
    };
    this.ladders = [
      ...lq.perches.map((p) => ({ ...p.ladder, name: p.name, id: "perch" + p.id })),
      { ...lq.tower.ladder, name: lq.tower.name, id: "tower" },
    ];
    const t = lq.tower, A = lq.perches[0], B = lq.perches[1];
    const rz = (r) => [-r[3], -r[1]]; // Blender rect y -> glTF z range
    this.diveEdges = [
      { name: "tower", x0: t.rect[0] + 0.2, x1: t.rect[2] - 0.2, z0: rz(t.rect)[1] - 1.6, z1: rz(t.rect)[1], y: t.top, to: -6.0, out: -9.7 },
      { name: "A", x0: A.rect[0] + 0.2, x1: A.rect[2] - 0.2, z0: rz(A.rect)[1] - 1.6, z1: rz(A.rect)[1], y: A.roof, to: -6.0, out: -9.7 },
      { name: "B", x0: B.rect[0] + 0.2, x1: B.rect[2] - 0.2, z0: rz(B.rect)[0], z1: rz(B.rect)[0] + 1.6, y: B.roof, to: -6.0, out: -1.9 },
    ];
  }

  // ------------------------------------------------------------------ contract lifecycle
  start(id, opts = {}) {
    const def = this.contracts.find((c) => c.id === id);
    this.def = def; this.time = 0; this.state = "play"; this.result = null; this.events = [];
    this.wind = [...def.wind];
    this.bellT = opts.bellPhase ?? 0;
    this.awning = new Awning(this.lq.cafe.awning, def.awning);
    if (!def.awning) this.awning.angle = 0;
    this.mark = new Mark(def, this.world);
    const avoid = this.lq.cafe.tables.map((t) => [t[0], t[2], 1.6]);
    this.crowd = new Crowd(this.lq.zones, { plaza: 12, south_quay_w: 6, south_quay_cafe: 10, south_quay_e: 8, north_quay: 8 },
      17 + id, this.world, avoid);
    this.watch = this.lq.guards.map((g, i) => new Watchman(g, i));
    const s = opts.spawn || this.lq.spawn;
    this.player = { p: [s[0], 0, s[2]], yaw: opts.yaw ?? -Math.PI / 2, pitch: 0, crouch: false, scoped: false, zoom: 4,
      breath: 1, holding: false, winded: 0, rounds: RIFLE.rounds, bolt: 0, eyeY: 0, moving: false, anim: null, inWater: false,
      head: [0, 0, 0], swayT: 0 };
    this.placePlayer(s[0], s[2], opts.spawnY);
    this.bullets = []; this.detect = 0; this.shots = 0; this.alerted = false; this.maskedShots = 0;
    this.targetDownAt = null;
  }

  placePlayer(x, z, y = null) {
    const P = this.player;
    const g = this.grid.groundAt(x, y ?? 40, z, 1.0, 80);
    P.p = [x, g ?? 0, z]; P.eyeY = P.p[1] + EYE;
  }

  get ringing() { return this.bellPhase() < BELL.ring; }
  bellPhase() { const t = this.bellT - BELL.first; return t < 0 ? 999 : t % BELL.period; }
  bellIn() { const t = this.bellT - BELL.first; return t < 0 ? -t : BELL.period - (t % BELL.period); }

  losClear(a, b) {
    if (!this.grid.clear(a, b, SHOT)) return false;
    if (this.awning && this.def?.awning && this.awning.intersect(a, b) >= 0) return false;
    return true;
  }

  // ------------------------------------------------------------------ player movement (ported from the Canal viewer)
  castH(x, y, z, dx, dz, far) { return this.grid.raycast(x, y, z, dx, 0, dz, far, WALK); }

  walkStep(mx, mz) {
    const P = this.player;
    let len = Math.hypot(mx, mz);
    if (len < 1e-6) return true;
    for (let iter = 0; iter < 3; iter++) {
      len = Math.hypot(mx, mz);
      if (len < 1e-5) return false;
      const dx = mx / len, dz = mz / len;
      let hit = null;
      for (const h of HEIGHTS) {
        const r = this.castH(P.p[0], P.p[1] + h, P.p[2], dx, dz, RADIUS + len);
        if (r && (!hit || r.t < hit.t)) hit = r;
      }
      if (!hit) break;
      let nx = hit.nx, nz = hit.nz;
      const nl = Math.hypot(nx, nz);
      if (nl < 1e-6) return false;
      nx /= nl; nz /= nl;
      if (nx * dx + nz * dz > 0) { nx = -nx; nz = -nz; }
      const d = mx * nx + mz * nz;
      mx -= nx * d; mz -= nz * d;
    }
    const nx = P.p[0] + mx, nz = P.p[2] + mz;
    const g = this.grid.groundAt(nx, P.p[1], nz, STEP + 0.05, 3.0);
    if (g === null || g > P.p[1] + STEP || g < P.p[1] - DROP) return false;
    P.p = [nx, g, nz];
    return true;
  }

  nearLadder() {
    const P = this.player;
    for (const l of this.ladders) {
      if (P.p[1] < 1.2 && Math.hypot(P.p[0] - l.base[0], P.p[2] - l.base[2]) < 1.4) return { l, dir: 1 };
      if (Math.abs(P.p[1] - l.height) < 1.2 && Math.hypot(P.p[0] - l.top[0], P.p[2] - l.top[2]) < 1.7) return { l, dir: -1 };
    }
    return null;
  }

  nearDive() {
    const P = this.player;
    return this.diveEdges.find((e) => P.p[0] > e.x0 && P.p[0] < e.x1 && P.p[2] > e.z0 && P.p[2] < e.z1 && Math.abs(P.p[1] - e.y) < 1.5) || null;
  }

  // ------------------------------------------------------------------ main tick
  // input: {mf, ms, run, look:[dyaw,dpitch], crouch, scope, zoom, fire, hold, interact, dive}
  tick(dt, input = {}) {
    if (this.state !== "play") return;
    this.time += dt; this.bellT += dt;
    const P = this.player;
    this.events.length = 0;
    // bell
    const ph = this.bellPhase();
    if (ph < dt + 1e-9 && this.bellT >= BELL.first) this.events.push("bell");
    this.awning.update(dt);
    // look
    if (input.look) {
      const s = P.scoped ? 1 / P.zoom : 1;
      P.yaw -= input.look[0] * s; P.pitch = Math.max(-1.35, Math.min(1.35, P.pitch - input.look[1] * s));
    }
    if (input.crouch) P.crouch = !P.crouch;
    if (input.scope) P.scoped = !P.scoped;
    if (input.zoom) P.zoom = P.zoom === 4 ? 10 : 4;
    // ladders / dive animation
    if (P.anim) this.animate(dt);
    else {
      if (input.interact) {
        const n = this.nearLadder();
        if (n) this.startLadder(n.l, n.dir);
      }
      if (input.dive && !P.anim) {
        const e = this.nearDive();
        if (e) this.startDive(e);
      }
    }
    if (!P.anim) {
      const mf = input.mf || 0, ms = input.ms || 0;
      P.moving = !!(mf || ms);
      if (P.moving) {
        const speed = P.scoped ? 0.9 : P.crouch ? 1.3 : input.run ? 5.0 : 2.2;
        const fx = -Math.sin(P.yaw), fz = -Math.cos(P.yaw);
        const rx = -fz, rz = fx;
        let mx = fx * mf + rx * ms, mz = fz * mf + rz * ms;
        const l = Math.hypot(mx, mz);
        const st = speed * Math.min(dt, 0.05);
        mx = (mx / l) * st; mz = (mz / l) * st;
        this.walkStep(mx, mz);
      }
    }
    const eyeH = P.crouch ? EYE_CROUCH : EYE;
    const target = P.p[1] + eyeH;
    P.eyeY = P.anim ? target : P.eyeY + (target - P.eyeY) * Math.min(1, dt * 12);
    P.head = [P.p[0], P.p[1] + eyeH, P.p[2]];
    // breathing / sway
    P.holding = !!(input.hold && P.scoped && P.breath > 0 && P.winded <= 0);
    if (P.holding) { P.breath -= dt / 5; if (P.breath <= 0) { P.breath = 0; P.winded = 3; } }
    else { P.breath = Math.min(1, P.breath + dt / 4); if (P.winded > 0) P.winded -= dt; }
    P.swayT += dt;
    // rifle
    if (P.bolt > 0) P.bolt -= dt;
    if (input.fire && P.scoped && P.rounds > 0 && P.bolt <= 0 && !P.anim) this.shoot(input.aimOverride);
    // bullets
    for (const b of this.bullets) if (b.alive) this.flyBullet(b, dt);
    // people
    this.crowd.update(dt);
    this.mark.update(dt);
    let rate = 0;
    const pl = { head: [P.p[0], P.eyeY - 0.1, P.p[2]], crouch: P.crouch, moving: P.moving };
    for (const w of this.watch) rate = Math.max(rate, w.update(dt, pl, this.world, DETECT));
    // a figure walking the streets blends into the crowd: watchmen only react to someone on a roof or ladder
    if (P.anim?.kind === "dive" || P.inWater || (P.p[1] < 3 && !P.scoped)) rate = 0;
    this.detect = rate > 0 ? Math.min(1, this.detect + rate * dt) : Math.max(0, this.detect - DETECT.decay * dt);
    // outcomes
    if (this.detect >= 1) return this.end(false, "spotted");
    if (this.mark.escaped) return this.end(false, "escaped");
    if (this.mark.target.dead && P.inWater) return this.end(true, "dove");
    if (!this.mark.target.dead && P.rounds === 0 && !this.bullets.some((b) => b.alive) && P.bolt <= 0) return this.end(false, "ammo");
  }

  // ------------------------------------------------------------------ shooting
  swayOffset() {
    const P = this.player;
    const base = (P.crouch ? 0.8 : 1.5) / 1000; // radians
    const k = P.holding ? 0.1 : P.winded > 0 ? 2.0 : 1.0;
    const t = P.swayT;
    return [base * k * (Math.sin(t * 0.83) + 0.45 * Math.sin(t * 2.1 + 1.3)), base * k * (Math.sin(t * 1.27 + 0.4) * 0.8 + 0.3 * Math.sin(t * 3.1))];
  }

  aimDir() {
    const P = this.player;
    const [sy, sp] = P.scoped ? this.swayOffset() : [0, 0];
    const yaw = P.yaw + sy, pitch = P.pitch + sp;
    return [-Math.sin(yaw) * Math.cos(pitch), Math.sin(pitch), -Math.cos(yaw) * Math.cos(pitch)];
  }

  eye() { const P = this.player; return [P.p[0], P.eyeY, P.p[2]]; }

  shoot(aimOverride) {
    const P = this.player;
    P.rounds--; P.bolt = RIFLE.rebolt; this.shots++;
    const b = fire(this.eye(), aimOverride || this.aimDir());
    this.bullets.push(b);
    const masked = this.ringing;
    if (masked) this.maskedShots++;
    this.events.push(masked ? "shot_masked" : "shot");
    if (!masked) this.alarm(this.eye());
    return b;
  }

  alarm(at) {
    this.alerted = true;
    this.crowd.alert(this.mark.target.p);
    this.mark.flee();
    this.detect = Math.min(0.95, this.detect + 0.25);
  }

  hitTest(a, b) {
    const dx = b[0] - a[0], dy = b[1] - a[1], dz = b[2] - a[2];
    let best = null;
    const w = this.grid.raycast(a[0], a[1], a[2], dx, dy, dz, 1, SHOT);
    if (w) best = { f: w.t, kind: "world" };
    if (this.def.awning) {
      const f = this.awning.intersect(a, b);
      if (f >= 0 && (!best || f < best.f)) best = { f, kind: "awning" };
    }
    const all = [...this.crowd.people, ...this.mark.people];
    for (const pp of all) {
      if (pp.dead) continue;
      if (Math.abs(pp.p[0] - a[0]) > 60 + Math.abs(dx) && Math.abs(pp.p[2] - a[2]) > 60 + Math.abs(dz)) continue;
      for (const s of pp.spheres()) {
        const f = segSphere(a, b, s, s[3]);
        if (f >= 0 && (!best || f < best.f)) best = { f, kind: pp.kind, person: pp };
      }
    }
    for (const t of this.testTargets || []) {
      const f = segSphere(a, b, t.c, t.r);
      if (f >= 0 && (!best || f < best.f)) best = { f, kind: "testtarget", tt: t };
    }
    for (const wm of this.watch) {
      if (wm.dead) continue;
      for (const s of wm.spheres()) {
        const f = segSphere(a, b, s, s[3]);
        if (f >= 0 && (!best || f < best.f)) best = { f, kind: "watchman", person: wm };
      }
    }
    return best;
  }

  flyBullet(b, dt) {
    const hit = advance(b, this.wind, dt, (a, c) => this.hitTest(a, c));
    if (!hit) return;
    this.events.push("impact:" + hit.kind);
    if (hit.person) {
      hit.person.dead = true;
      if (hit.kind === "civilian") return this.end(false, "civilian");
      if (hit.kind === "target") this.targetDownAt = this.time;
      if (hit.kind === "watchman" || hit.kind === "bodyguard") this.detect = Math.min(0.95, this.detect + 0.15);
    }
  }

  // ------------------------------------------------------------------ ladder + dive animation
  startLadder(l, dir) {
    const P = this.player;
    P.scoped = false; P.crouch = false;
    const from = dir > 0 ? [l.base[0], 0, l.base[2]] : [...P.p];
    const wallOut = [l.base[0] - l.wall[0], l.base[2] - l.wall[2]];
    const n = Math.hypot(...wallOut) || 1;
    const onWall = [l.wall[0] + (wallOut[0] / n) * 0.45, l.wall[2] + (wallOut[1] / n) * 0.45];
    P.anim = { kind: "ladder", l, dir, t: 0, from, onWall, dur: 0.5 + l.height / 4.0 };
    P.yaw = Math.atan2(wallOut[0], wallOut[1]);
  }

  startDive(e) {
    const P = this.player;
    P.scoped = false; P.crouch = false;
    const from = [...P.p];
    const to = [P.p[0], this.lq.water_y - 0.6, e.to];
    P.anim = { kind: "dive", t: 0, from, to, out: e.out, dur: 0.6 + Math.sqrt((from[1] - to[1]) / 4.9) };
    this.events.push("dive");
  }

  animate(dt) {
    const P = this.player, A = P.anim;
    A.t += dt;
    const u = Math.min(1, A.t / A.dur);
    if (A.kind === "ladder") {
      const l = A.l;
      const h = l.height;
      if (A.dir > 0) {
        const y = Math.min(h, Math.max(0, (A.t - 0.25) / (A.dur - 0.5)) * h);
        P.p = [A.onWall[0], y, A.onWall[1]];
        if (u >= 1) { P.p = [l.top[0], h, l.top[2]]; P.anim = null; this.placePlayer(l.top[0], l.top[2], h + 0.5); }
      } else {
        const y = h * (1 - Math.min(1, Math.max(0, (A.t - 0.25) / (A.dur - 0.5))));
        P.p = [A.onWall[0], y, A.onWall[1]];
        if (u >= 1) { P.anim = null; this.placePlayer(l.base[0], l.base[2], 1.0); }
      }
    } else if (A.kind === "dive") {
      const y = A.from[1] + (A.to[1] - A.from[1]) * u * u + Math.sin(u * Math.PI) * 1.2;
      P.p = [A.from[0], y, A.from[2] + (A.to[2] - A.from[2]) * u];
      P.pitch = -0.4 - u * 0.6;
      if (u >= 1) {
        P.anim = null; P.inWater = true; this.events.push("splash");
        if (!this.mark.target.dead) { // no kill yet: climb out on the quay and carry on
          P.inWater = false;
          this.placePlayer(P.p[0], A.out, 0.5);
          P.pitch = 0;
        }
      }
    }
  }

  end(ok, reason) {
    this.state = "over";
    this.result = { ok, reason, time: +this.time.toFixed(1), shots: this.shots, masked: this.maskedShots, alerted: this.alerted };
    this.events.push(ok ? "success" : "fail");
  }

  // ------------------------------------------------------------------ helpers for the scripted shooter + HUD
  // Aim direction that puts the reticle at the holdover point for `point` (drop and wind from the range card).
  holdoverAim(point, crossOverride = null) {
    const e = this.eye();
    const dx = point[0] - e[0], dy = point[1] - e[1], dz = point[2] - e[2];
    const R = Math.hypot(dx, dy, dz);
    const hz = Math.hypot(dx, dz);
    const fx = dx / hz, fz = dz / hz;
    const right = [-fz, 0, fx];
    const cross = crossOverride ?? (this.wind[0] * right[0] + this.wind[2] * right[2]);
    const s = solution(R, cross);
    const cosA = hz / R; // rifleman's rule: drop acts on the horizontal component
    const up = (s.dropMil / 1000) * R * cosA, left = (s.driftMil / 1000) * R;
    const aim = [point[0] - right[0] * left, point[1] + up, point[2] - right[2] * left];
    const ax = aim[0] - e[0], ay = aim[1] - e[1], az = aim[2] - e[2];
    const al = Math.hypot(ax, ay, az);
    return { dir: [ax / al, ay / al, az / al], range: R, drop: s.dropMil, drift: s.driftMil, cross };
  }

  // range to whatever the sight line hits (shown in the scope)
  rangeAtCrosshair() {
    const e = this.eye(), d = this.aimDir();
    const h = this.grid.raycast(e[0], e[1], e[2], d[0], d[1], d[2], 400, SHOT);
    return h ? h.t : null;
  }
}
