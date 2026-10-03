// Townsfolk, the contract target with bodyguards, and the rooftop watchmen. Framework-free.
// World access is injected: world.groundAt(x, y, z) -> y | null, world.clear(a, b) -> bool (line of sight).
export function rng(seed) {
  let s = seed >>> 0 || 1;
  return () => { s ^= s << 13; s ^= s >>> 17; s ^= s << 5; return (s >>> 0) / 4294967296; };
}

const COATS = ["#6f7f8c", "#8a6a48", "#4d6b5a", "#7a5a6e", "#a08a5c", "#5a6f93", "#8d7b6a", "#6b5446", "#9c7a54",
  "#4f5f6a", "#b09a78", "#7d8a6a", "#a3826e", "#5e5a72"];
const HATS = [null, null, null, "cap", "straw", null, "scarf"];

// hit spheres relative to the feet: legs, torso, head (radius)
export const BODY = [[0, 0.55, 0, 0.22], [0, 1.12, 0, 0.27], [0, 1.6, 0, 0.14]];
export const SEATED_DROP = 0.42;

export class Person {
  constructor(id, kind, p, look) {
    this.id = id; this.kind = kind; // civilian | target | bodyguard
    this.p = [...p]; this.goal = null; this.wait = 0; this.speed = 1.2; this.heading = 0;
    this.look = look; this.down = 0; this.dead = false; this.seated = false; this.panic = 0; this.walkPhase = 0;
  }
  spheres() {
    const out = [];
    const drop = this.seated ? SEATED_DROP : 0;
    for (const [dx, dy, dz, r] of BODY) {
      if (this.seated && dy < 0.7) continue;
      out.push([this.p[0] + dx, this.p[1] + dy - drop, this.p[2] + dz, r]);
    }
    return out;
  }
  head() { return [this.p[0], this.p[1] + 1.6 - (this.seated ? SEATED_DROP : 0), this.p[2]]; }
  chest() { return [this.p[0], this.p[1] + 1.15 - (this.seated ? SEATED_DROP : 0), this.p[2]]; }
}

function stepToward(pp, goal, speed, dt, world) {
  const dx = goal[0] - pp.p[0], dz = goal[2] - pp.p[2];
  const d = Math.hypot(dx, dz);
  if (d < 0.05) return true;
  const s = Math.min(d, speed * dt);
  pp.p[0] += (dx / d) * s; pp.p[2] += (dz / d) * s;
  pp.heading = Math.atan2(dx, dz);
  pp.walkPhase += s * 2.2;
  const g = world.groundAt(pp.p[0], pp.p[1] + 1.0, pp.p[2]);
  if (g !== null) pp.p[1] = g;
  return d - s < 0.05;
}

const randIn = (z, r) => [z.min[0] + (z.max[0] - z.min[0]) * r(), 0, z.min[2] + (z.max[2] - z.min[2]) * r()];

export class Crowd {
  constructor(zones, counts, seed, world, avoid = []) {
    this.r = rng(seed); this.world = world; this.zones = zones; this.people = [];
    let id = 0;
    for (const [zone, n] of Object.entries(counts)) {
      for (let i = 0; i < n; i++) {
        const z = zones[zone];
        const p = randIn(z, this.r);
        p[1] = world.groundAt(p[0], 2, p[2]) ?? 0;
        const look = { coat: COATS[Math.floor(this.r() * COATS.length)], hat: HATS[Math.floor(this.r() * HATS.length)],
          hatColor: COATS[Math.floor(this.r() * COATS.length)], height: 0.92 + this.r() * 0.14 };
        const pp = new Person(id++, "civilian", p, look);
        pp.zone = zone; pp.speed = 0.9 + this.r() * 0.6; pp.wait = this.r() * 4;
        this.people.push(pp);
      }
    }
    this.avoid = avoid; // [[x, z, r]] spots civilians keep clear of (the target's seat, etc.)
  }

  pick(pp) {
    for (let k = 0; k < 6; k++) {
      const g = randIn(this.zones[pp.zone], this.r);
      if (!this.avoid.some(([x, z, r]) => Math.hypot(g[0] - x, g[2] - z) < r)) return g;
    }
    return randIn(this.zones[pp.zone], this.r);
  }

  alert(at) {
    for (const pp of this.people) {
      if (pp.dead) continue;
      const d = Math.hypot(pp.p[0] - at[0], pp.p[2] - at[2]);
      if (d > 70) continue;
      pp.panic = 9; pp.wait = 0;
      // run to the far end of the zone, away from the shot
      const z = this.zones[pp.zone];
      const fx = pp.p[0] > at[0] ? z.max[0] : z.min[0];
      pp.goal = [fx - Math.sign(fx - at[0]) * this.r() * 3, 0, z.min[2] + (z.max[2] - z.min[2]) * this.r()];
    }
  }

  update(dt) {
    for (const pp of this.people) {
      if (pp.dead) { pp.down = Math.min(1, pp.down + dt * 2); continue; }
      if (pp.panic > 0) pp.panic -= dt;
      if (pp.wait > 0) { pp.wait -= dt; continue; }
      if (!pp.goal) pp.goal = this.pick(pp);
      if (stepToward(pp, pp.goal, pp.panic > 0 ? 3.6 : pp.speed, dt, this.world)) {
        pp.goal = null; pp.wait = pp.panic > 0 ? 0.5 : 1.5 + this.r() * 6;
      }
    }
  }
}

// Scripted lieutenant: loops a route of [point, waitSeconds, seated?] stops; two bodyguards follow.
export class Mark {
  constructor(def, world) {
    this.def = def; this.world = world;
    const p0 = def.route[0].p;
    this.target = new Person(1000, "target", [p0[0], world.groundAt(p0[0], 3, p0[2]) ?? 0, p0[2]], def.look);
    this.guards = def.bodyguards.map((g, i) => {
      const pp = new Person(1001 + i, "bodyguard", [p0[0] + g.off[0], 0, p0[2] + g.off[1]], def.guardLook);
      pp.p[1] = world.groundAt(pp.p[0], 3, pp.p[2]) ?? 0;
      pp.fixed = g.fixed || null;
      pp.off = g.off;
      return pp;
    });
    this.i = 0; this.wait = def.route[0].wait; this.target.seated = !!def.route[0].seated;
    this.fleeing = false; this.escaped = false; this.target.speed = def.speed || 1.0;
  }
  get people() { return [this.target, ...this.guards]; }

  flee() {
    if (this.target.dead || this.fleeing) return;
    this.fleeing = true; this.target.seated = false; this.target.speed = 3.2; this.wait = 0;
    const t = this.target.p;
    const e = [...this.def.exits].sort((a, b) => Math.hypot(a.via[0] - t[0], a.via[2] - t[2]) - Math.hypot(b.via[0] - t[0], b.via[2] - t[2]))[0];
    this.fleePath = [e.via, e.exit];
  }

  update(dt) {
    const t = this.target, w = this.world;
    if (t.dead) t.down = Math.min(1, t.down + dt * 1.6);
    else if (this.fleeing) {
      if (stepToward(t, this.fleePath[0], t.speed, dt, w)) {
        if (this.fleePath.length > 1) this.fleePath.shift(); else this.escaped = true;
      }
    } else if (this.wait > 0) {
      this.wait -= dt;
      if (this.wait <= 0) { this.i = (this.i + 1) % this.def.route.length; t.seated = false; }
    } else {
      const stop = this.def.route[this.i];
      if (stepToward(t, stop.p, t.speed, dt, w)) { this.wait = stop.wait; t.seated = !!stop.seated; if (stop.face !== undefined) t.heading = stop.face; }
    }
    for (const g of this.guards) {
      if (g.dead) { g.down = Math.min(1, g.down + dt * 1.6); continue; }
      const goal = g.fixed && !this.fleeing ? g.fixed : [t.p[0] + g.off[0], 0, t.p[2] + g.off[1]];
      const d = Math.hypot(goal[0] - g.p[0], goal[2] - g.p[2]);
      if (d > 0.3) stepToward(g, goal, Math.min(3.4, Math.max(t.speed, d * 1.5)), dt, w);
      else g.heading = Math.atan2(t.p[0] - g.p[0], t.p[2] - g.p[2]);
    }
  }
}

// Rooftop watchman: walks a -> b, pauses and scans, walks back. Detection meter fills while he can see the player.
export class Watchman {
  constructor(def, i) {
    this.def = def; this.p = [...def.a]; this.dir = 1; this.wait = 1 + i * 1.7; this.heading = 0; this.scan = 0;
    this.meter = 0; this.sees = false; this.dead = false; this.down = 0; this.walkPhase = 0; this.t = i * 0.37;
    const dx = def.b[0] - def.a[0], dz = def.b[2] - def.a[2];
    this.base = Math.atan2(dx, dz);
    this.heading = this.base;
  }
  eye() { return [this.p[0], this.p[1] + 1.65, this.p[2]]; }
  spheres() { return BODY.map(([dx, dy, dz, r]) => [this.p[0] + dx, this.p[1] + dy, this.p[2] + dz, r]); }
  head() { return [this.p[0], this.p[1] + 1.6, this.p[2]]; }

  update(dt, player, world, cfg) {
    if (this.dead) { this.down = Math.min(1, this.down + dt * 1.6); this.sees = false; return 0; }
    this.t += dt;
    const goal = this.dir > 0 ? this.def.b : this.def.a;
    if (this.wait > 0) {
      this.wait -= dt;
      this.scan += dt;
      // pauses to watch the main canal (z = -6), sweeping slowly across it
      const face = this.p[2] > -6 ? Math.PI : 0;
      this.heading = face + Math.sin(this.scan * 0.7) * 1.4;
      if (this.wait <= 0) this.dir *= -1;
    } else {
      const dx = goal[0] - this.p[0], dz = goal[2] - this.p[2];
      const d = Math.hypot(dx, dz);
      const s = Math.min(d, 1.1 * dt);
      this.p[0] += (dx / d) * s; this.p[2] += (dz / d) * s; this.walkPhase += s * 2.2;
      this.heading = Math.atan2(dx, dz);
      if (d - s < 0.05) { this.wait = 7; this.scan = 0; }
    }
    // vision
    const e = this.eye();
    const tgt = player.head;
    const vx = tgt[0] - e[0], vy = tgt[1] - e[1], vz = tgt[2] - e[2];
    const dist = Math.hypot(vx, vy, vz);
    let rate = 0;
    this.sees = false;
    if (dist < cfg.range) {
      const ang = Math.atan2(vx, vz) - this.heading;
      const a = Math.abs(Math.atan2(Math.sin(ang), Math.cos(ang)));
      if (a < cfg.fov / 2 && world.clear(e, tgt)) {
        this.sees = true;
        rate = cfg.rate * Math.pow(1 - dist / cfg.range, 0.7) * (player.crouch ? cfg.crouchMul : 1) * (player.moving ? cfg.moveMul : 1);
        if (dist < 6) rate *= 2.5;
      }
    }
    return rate;
  }
}

export const DETECT = { range: 60, fov: (100 * Math.PI) / 180, rate: 1.3, crouchMul: 0.35, moveMul: 1.4, decay: 0.12 };
