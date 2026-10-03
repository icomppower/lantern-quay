// The café wind awning: a canvas panel hinged along its top edge (a line along z at x = hingeX, y = top).
// angle 0 = hanging straight down (blocks shots from the east); gusts from the east lift it inward (-x) over the tables.
export class Awning {
  constructor({ x, z0, z1, top, bottom }, gusty = true, seed = 7) {
    Object.assign(this, { x, z0, z1, top, len: top - bottom });
    this.angle = 0; this.t = 0; this.gusty = gusty;
    this.seed = seed;
    this.cycle = 0;
  }

  // Gust cycle: down ~7 s, rise 0.8 s, up ~3 s, fall 0.8 s (period varies a little per cycle).
  update(dt) {
    this.t += dt;
    if (this.forced != null) { this.angle = this.forced; return; }
    if (!this.gusty) { this.angle = 0; return; }
    const P = 12, ph = this.t % P;
    const up = 1.35;
    let a;
    if (ph < 7) a = 0.05 * Math.sin(this.t * 2.1);
    else if (ph < 7.8) a = up * smooth((ph - 7) / 0.8);
    else if (ph < 10.8) a = up + 0.06 * Math.sin(this.t * 5);
    else if (ph < 11.6) a = up * (1 - smooth((ph - 10.8) / 0.8));
    else a = 0;
    this.angle = a;
  }

  get open() { return this.angle > 0.9; }
  secondsUntilOpen() { const ph = this.t % 12; return ph < 7.8 ? 7.8 - ph : 12 - ph + 7.8; }

  // panel corners: hinge line (x, top, z0..z1) plus the free edge swung out by `angle`
  edge() {
    return [this.x - Math.sin(this.angle) * this.len, this.top - Math.cos(this.angle) * this.len];
  }

  // segment a->b vs the panel; returns f in [0,1] or -1
  intersect(a, b) {
    const [ex, ey] = this.edge();
    // panel plane through the hinge (x, top) and edge (ex, ey), extruded along z. 2D line in the xy-plane.
    const hx = this.x, hy = this.top;
    const ux = ex - hx, uy = ey - hy;
    const nx = -uy, ny = ux; // normal in xy
    const da = (a[0] - hx) * nx + (a[1] - hy) * ny, db = (b[0] - hx) * nx + (b[1] - hy) * ny;
    if ((da > 0) === (db > 0)) return -1;
    const f = da / (da - db);
    const px = a[0] + (b[0] - a[0]) * f, py = a[1] + (b[1] - a[1]) * f, pz = a[2] + (b[2] - a[2]) * f;
    const s = ((px - hx) * ux + (py - hy) * uy) / (ux * ux + uy * uy);
    if (s < 0 || s > 1 || pz < this.z0 || pz > this.z1) return -1;
    return f;
  }
}

function smooth(x) { x = Math.max(0, Math.min(1, x)); return x * x * (3 - 2 * x); }
