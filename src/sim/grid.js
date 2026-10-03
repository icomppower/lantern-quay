// Static triangle grid for raycasts (walking collision, ground probes, bullets, line of sight).
// Triangles are bucketed into square XZ cells; a ray walks the cells in order (Amanatides-Woo).
// Framework-free: triangles come in as world-space Float32Array [ax,ay,az, bx,by,bz, cx,cy,cz]*.
export const WALK = 1, SHOT = 2;

export class TriGrid {
  constructor({ minX, minZ, maxX, maxZ }, cell = 4) {
    this.minX = minX; this.minZ = minZ; this.cell = cell;
    this.nx = Math.ceil((maxX - minX) / cell); this.nz = Math.ceil((maxZ - minZ) / cell);
  }

  build(tris, flags) {
    const n = tris.length / 9;
    this.n = n;
    // store v0, e1, e2 for Moller-Trumbore
    const T = (this.T = new Float32Array(n * 9));
    for (let i = 0; i < n; i++) {
      const o = i * 9;
      T[o] = tris[o]; T[o + 1] = tris[o + 1]; T[o + 2] = tris[o + 2];
      T[o + 3] = tris[o + 3] - tris[o]; T[o + 4] = tris[o + 4] - tris[o + 1]; T[o + 5] = tris[o + 5] - tris[o + 2];
      T[o + 6] = tris[o + 6] - tris[o]; T[o + 7] = tris[o + 7] - tris[o + 1]; T[o + 8] = tris[o + 8] - tris[o + 2];
    }
    this.flags = flags;
    const { nx, nz, cell, minX, minZ } = this;
    const counts = new Uint32Array(nx * nz + 1);
    const span = (i) => {
      const o = i * 9;
      const x0 = Math.min(tris[o], tris[o + 3], tris[o + 6]), x1 = Math.max(tris[o], tris[o + 3], tris[o + 6]);
      const z0 = Math.min(tris[o + 2], tris[o + 5], tris[o + 8]), z1 = Math.max(tris[o + 2], tris[o + 5], tris[o + 8]);
      const cx0 = Math.floor((x0 - minX) / cell), cx1 = Math.floor((x1 - minX) / cell);
      const cz0 = Math.floor((z0 - minZ) / cell), cz1 = Math.floor((z1 - minZ) / cell);
      if (cx1 < 0 || cz1 < 0 || cx0 >= nx || cz0 >= nz) return null;
      return [Math.max(0, cx0), Math.min(nx - 1, cx1), Math.max(0, cz0), Math.min(nz - 1, cz1)];
    };
    const spans = new Array(n);
    for (let i = 0; i < n; i++) {
      const s = (spans[i] = span(i));
      if (!s) continue;
      for (let z = s[2]; z <= s[3]; z++) for (let x = s[0]; x <= s[1]; x++) counts[z * nx + x + 1]++;
    }
    for (let c = 1; c <= nx * nz; c++) counts[c] += counts[c - 1];
    this.start = counts;
    const fill = counts.slice();
    this.items = new Uint32Array(counts[nx * nz]);
    for (let i = 0; i < n; i++) {
      const s = spans[i];
      if (!s) continue;
      for (let z = s[2]; z <= s[3]; z++) for (let x = s[0]; x <= s[1]; x++) this.items[fill[z * nx + x]++] = i;
    }
    this.stamp = new Uint32Array(n);
    this.q = 0;
    return this;
  }

  // Nearest hit along origin + t*dir (dir need not be unit; t is in units of |dir|) up to tMax.
  raycast(ox, oy, oz, dx, dy, dz, tMax, mask = WALK) {
    const { cell, minX, minZ, nx, nz, T, items, start, flags } = this;
    const q = ++this.q;
    let best = tMax, bi = -1;
    let cx = Math.floor((ox - minX) / cell), cz = Math.floor((oz - minZ) / cell);
    const stepX = dx > 0 ? 1 : -1, stepZ = dz > 0 ? 1 : -1;
    const tdx = dx !== 0 ? Math.abs(cell / dx) : Infinity, tdz = dz !== 0 ? Math.abs(cell / dz) : Infinity;
    let tmx = dx !== 0 ? ((minX + (cx + (dx > 0 ? 1 : 0)) * cell) - ox) / dx : Infinity;
    let tmz = dz !== 0 ? ((minZ + (cz + (dz > 0 ? 1 : 0)) * cell) - oz) / dz : Infinity;
    let tEnter = 0;
    for (let guard = 0; guard < 4096; guard++) {
      if (cx >= 0 && cz >= 0 && cx < nx && cz < nz) {
        const c = cz * nx + cx;
        for (let k = start[c], e = start[c + 1]; k < e; k++) {
          const i = items[k];
          if (this.stamp[i] === q || !(flags[i] & mask)) continue;
          this.stamp[i] = q;
          const o = i * 9;
          const e1x = T[o + 3], e1y = T[o + 4], e1z = T[o + 5], e2x = T[o + 6], e2y = T[o + 7], e2z = T[o + 8];
          const px = dy * e2z - dz * e2y, py = dz * e2x - dx * e2z, pz = dx * e2y - dy * e2x;
          const det = e1x * px + e1y * py + e1z * pz;
          if (det > -1e-12 && det < 1e-12) continue;
          const inv = 1 / det;
          const sx = ox - T[o], sy = oy - T[o + 1], sz = oz - T[o + 2];
          const u = (sx * px + sy * py + sz * pz) * inv;
          if (u < 0 || u > 1) continue;
          const qx = sy * e1z - sz * e1y, qy = sz * e1x - sx * e1z, qz = sx * e1y - sy * e1x;
          const v = (dx * qx + dy * qy + dz * qz) * inv;
          if (v < 0 || u + v > 1) continue;
          const t = (e2x * qx + e2y * qy + e2z * qz) * inv;
          if (t >= 0 && t < best) { best = t; bi = i; }
        }
      }
      const tExit = Math.min(tmx, tmz);
      if (bi >= 0 && best <= tExit) break;
      if (tExit > tMax || tExit === Infinity) break;
      if (tmx < tmz) { cx += stepX; tmx += tdx; } else { cz += stepZ; tmz += tdz; }
      tEnter = tExit;
      if ((cx < 0 && stepX < 0) || (cz < 0 && stepZ < 0) || (cx >= nx && stepX > 0) || (cz >= nz && stepZ > 0)) break;
    }
    if (bi < 0) return null;
    const o = bi * 9;
    let nxv = T[o + 4] * T[o + 8] - T[o + 5] * T[o + 7];
    let nyv = T[o + 5] * T[o + 6] - T[o + 3] * T[o + 8];
    let nzv = T[o + 3] * T[o + 7] - T[o + 4] * T[o + 6];
    const l = Math.hypot(nxv, nyv, nzv) || 1;
    nxv /= l; nyv /= l; nzv /= l;
    if (nxv * dx + nyv * dy + nzv * dz > 0) { nxv = -nxv; nyv = -nyv; nzv = -nzv; }
    return { t: best, tri: bi, nx: nxv, ny: nyv, nz: nzv };
  }

  groundAt(x, y, z, up = 1.0, down = 3.0) {
    const h = this.raycast(x, y + up, z, 0, -1, 0, up + down, WALK);
    return h ? y + up - h.t : null;
  }

  // true if the straight segment a->b is unobstructed for line of sight / bullets
  clear(a, b, mask = SHOT) {
    const dx = b[0] - a[0], dy = b[1] - a[1], dz = b[2] - a[2];
    return !this.raycast(a[0], a[1], a[2], dx, dy, dz, 1, mask);
  }
}
