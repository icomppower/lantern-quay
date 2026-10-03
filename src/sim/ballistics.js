// Bolt-action rifle ballistics: point-mass bullet with quadratic drag in moving air (so wind drift comes
// from drag lag, as in reality) and gravity. Framework-free; vectors are [x, y, z] arrays, +y up.
export const G = 9.81;
export const RIFLE = {
  v0: 330,          // m/s muzzle velocity (subsonic carbine: gives readable drop and drift at 60-140 m)
  k: 0.003,         // 1/m quadratic drag coefficient (v falls ~e^(-k x))
  zeroRange: 60,    // scope zeroed at 60 m
  rounds: 5,
  rebolt: 1.4,      // s
  dt: 1 / 960,      // integration substep
  maxTime: 2.5,     // s
};

export function stepBullet(b, wind, dt, k = RIFLE.k) {
  const rx = b.v[0] - wind[0], ry = b.v[1] - wind[1], rz = b.v[2] - wind[2];
  const sp = Math.hypot(rx, ry, rz);
  b.v[0] += -k * sp * rx * dt;
  b.v[1] += (-k * sp * ry - G) * dt;
  b.v[2] += -k * sp * rz * dt;
  b.p[0] += b.v[0] * dt; b.p[1] += b.v[1] * dt; b.p[2] += b.v[2] * dt;
  b.t += dt;
}

// Fly a shot along +x from the origin at elevation `elev` (rad) with a crosswind blowing toward +z.
// Returns {y, z, t} where the bullet crosses x = range.
function flatShot(range, elev, crossWind = 0) {
  const b = { p: [0, 0, 0], v: [RIFLE.v0 * Math.cos(elev), RIFLE.v0 * Math.sin(elev), 0], t: 0 };
  const w = [0, 0, crossWind];
  let prev = [...b.p];
  while (b.p[0] < range && b.t < RIFLE.maxTime) { prev = [...b.p]; stepBullet(b, w, RIFLE.dt); }
  const f = (range - prev[0]) / Math.max(1e-9, b.p[0] - prev[0]);
  return { y: prev[1] + (b.p[1] - prev[1]) * f, z: prev[2] + (b.p[2] - prev[2]) * f, t: b.t - RIFLE.dt * (1 - f) };
}

let _zero = null;
export function zeroAngle() {
  if (_zero !== null) return _zero;
  let lo = 0, hi = 0.05;
  for (let i = 0; i < 40; i++) { const m = (lo + hi) / 2; if (flatShot(RIFLE.zeroRange, m).y < 0) lo = m; else hi = m; }
  return (_zero = (lo + hi) / 2);
}

// Holdover for a target `range` m away with `crossWind` m/s blowing left-to-right across the line of fire.
// dropMil > 0: aim that many mils above the target. driftMil > 0: the bullet drifts right; aim left.
export function solution(range, crossWind = 0) {
  const s = flatShot(range, zeroAngle(), crossWind);
  return { dropMil: (-s.y / range) * 1000, driftMil: (s.z / range) * 1000, tof: s.t };
}

// Range card shown in the dossier / scope legend.
export function rangeCard(ranges = [40, 60, 80, 100, 120, 140], wind = 1) {
  return ranges.map((r) => { const s = solution(r, wind); return { r, drop: +s.dropMil.toFixed(1), driftPerMs: +s.driftMil.toFixed(2), tof: +s.tof.toFixed(2) }; });
}

// Start a bullet from `origin` along the sight line `aim` (unit). The bore is tilted up by the zero angle.
export function fire(origin, aim) {
  const za = zeroAngle();
  // world-up component perpendicular to the aim direction
  let ux = -aim[0] * aim[1], uy = 1 - aim[1] * aim[1], uz = -aim[2] * aim[1];
  const ul = Math.hypot(ux, uy, uz) || 1;
  ux /= ul; uy /= ul; uz /= ul;
  const c = Math.cos(za), s = Math.sin(za);
  const d = [aim[0] * c + ux * s, aim[1] * c + uy * s, aim[2] * c + uz * s];
  return { p: [...origin], v: d.map((x) => x * RIFLE.v0), t: 0, alive: true, trail: [[...origin]], hit: null };
}

// Advance a bullet by dt seconds; hitTest(a, b) -> {f (0..1 along a->b), ...info} | null for the nearest hit.
export function advance(b, wind, dt, hitTest) {
  if (!b.alive) return null;
  let remaining = dt;
  while (remaining > 1e-9 && b.alive) {
    const a = [...b.p];
    const n = 4;
    for (let i = 0; i < n && remaining > 1e-9; i++) {
      const h = Math.min(RIFLE.dt, remaining);
      stepBullet(b, wind, h);
      remaining -= h;
    }
    const hit = hitTest(a, b.p);
    if (hit) {
      b.alive = false;
      b.p = [a[0] + (b.p[0] - a[0]) * hit.f, a[1] + (b.p[1] - a[1]) * hit.f, a[2] + (b.p[2] - a[2]) * hit.f];
      b.hit = hit;
      b.trail.push([...b.p]);
      return hit;
    }
    b.trail.push([...b.p]);
    if (b.t > RIFLE.maxTime || b.p[1] < -5) { b.alive = false; return null; }
  }
  return null;
}

// Segment vs sphere: returns f in [0,1] of first contact or -1.
export function segSphere(a, b, c, r) {
  const dx = b[0] - a[0], dy = b[1] - a[1], dz = b[2] - a[2];
  const fx = a[0] - c[0], fy = a[1] - c[1], fz = a[2] - c[2];
  const A = dx * dx + dy * dy + dz * dz;
  const B = 2 * (fx * dx + fy * dy + fz * dz);
  const C = fx * fx + fy * fy + fz * fz - r * r;
  if (C <= 0) return 0;
  const disc = B * B - 4 * A * C;
  if (disc < 0 || A < 1e-12) return -1;
  const t = (-B - Math.sqrt(disc)) / (2 * A);
  return t >= 0 && t <= 1 ? t : -1;
}
