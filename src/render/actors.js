// Render layer for dynamic things: townsfolk/targets/watchmen (instanced), ladders, bell, café awning, tracers.
import * as THREE from "three";
import { SEATED_DROP } from "../sim/people.js";

const MAXP = 64;

function partMesh(geo, n, color = 0xffffff) {
  const mat = new THREE.MeshStandardMaterial({ color, roughness: 0.85 });
  const m = new THREE.InstancedMesh(geo, mat, n);
  m.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  m.setColorAt(0, new THREE.Color(1, 1, 1));
  m.castShadow = true; m.frustumCulled = false;
  m.count = 0;
  return m;
}

export class People {
  constructor(scene) {
    this.g = new THREE.Group();
    scene.add(this.g);
    const legs = new THREE.CylinderGeometry(0.15, 0.12, 0.8, 8).translate(0, 0.4, 0);
    const coat = new THREE.CylinderGeometry(0.19, 0.26, 0.82, 10).translate(0, 1.08, 0);
    const shoulders = new THREE.SphereGeometry(0.21, 10, 6).scale(1.15, 0.55, 0.8).translate(0, 1.47, 0);
    const head = new THREE.SphereGeometry(0.12, 12, 8).translate(0, 1.64, 0);
    this.parts = {
      legs: partMesh(legs, MAXP, 0x3a3128), coat: partMesh(coat, MAXP), shoulders: partMesh(shoulders, MAXP),
      head: partMesh(head, MAXP, 0xd9a882),
    };
    const hats = {
      cap: new THREE.CylinderGeometry(0.13, 0.13, 0.07, 12).translate(0, 1.75, 0.02),
      straw: new THREE.CylinderGeometry(0.26, 0.26, 0.02, 14).translate(0, 1.72, 0)
        .applyMatrix4(new THREE.Matrix4()).toNonIndexed(),
      tricorn: new THREE.ConeGeometry(0.3, 0.18, 3).translate(0, 1.8, 0),
      bonnet: new THREE.SphereGeometry(0.16, 12, 8, 0, Math.PI * 2, 0, Math.PI / 2).scale(1.1, 0.9, 1.25).translate(0, 1.68, 0),
      scarf: new THREE.TorusGeometry(0.12, 0.05, 6, 12).rotateX(Math.PI / 2).translate(0, 1.52, 0),
    };
    this.hats = {};
    for (const [k, g] of Object.entries(hats)) this.hats[k] = partMesh(g, MAXP);
    for (const m of [...Object.values(this.parts), ...Object.values(this.hats)]) this.g.add(m);
    this.m = new THREE.Matrix4(); this.q = new THREE.Quaternion(); this.e = new THREE.Euler(); this.c = new THREE.Color();
    this.alerts = [];
    const mk = (col) => {
      const c = document.createElement("canvas"); c.width = c.height = 64;
      const x = c.getContext("2d"); x.fillStyle = col; x.font = "bold 54px sans-serif"; x.textAlign = "center"; x.fillText("!", 32, 52);
      return new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), depthTest: false, transparent: true });
    };
    this.alertMats = [mk("#ffd25a"), mk("#ff4a3a")];
    for (let i = 0; i < 3; i++) { const s = new THREE.Sprite(this.alertMats[0]); s.scale.setScalar(0.8); s.visible = false; this.g.add(s); this.alerts.push(s); }
  }

  update(list, watch) {
    const counts = {};
    const put = (mesh, key, matrix, color) => {
      const i = counts[key] = (counts[key] ?? -1) + 1;
      mesh.setMatrixAt(i, matrix);
      if (color) mesh.setColorAt(i, this.c.set(color));
    };
    for (const pp of list) {
      const drop = pp.seated ? SEATED_DROP : 0;
      const bob = pp.down ? 0 : Math.abs(Math.sin(pp.walkPhase || 0)) * 0.04;
      this.e.set(-(pp.down || 0) * Math.PI / 2, pp.heading || 0, 0, "YXZ");
      this.q.setFromEuler(this.e);
      const h = pp.look?.height ?? 1;
      this.m.compose(new THREE.Vector3(pp.p[0], pp.p[1] - drop + bob + (pp.down ? 0.12 * pp.down : 0), pp.p[2]), this.q, new THREE.Vector3(1, h, 1));
      put(this.parts.legs, "legs", this.m, pp.legs || "#3a3128");
      put(this.parts.coat, "coat", this.m, pp.look.coat);
      put(this.parts.shoulders, "shoulders", this.m, pp.look.coat);
      put(this.parts.head, "head", this.m, "#d9a882");
      if (pp.look.hat) put(this.hats[pp.look.hat], pp.look.hat, this.m, pp.look.hatColor);
    }
    for (const [k, mesh] of Object.entries({ ...this.parts, ...this.hats })) {
      mesh.count = (counts[k] ?? -1) + 1;
      mesh.instanceMatrix.needsUpdate = true;
      if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    }
    watch.forEach((w, i) => {
      const s = this.alerts[i];
      s.visible = !w.dead && w.sees;
      s.material = this.alertMats[w.meterHot ? 1 : 0];
      s.position.set(w.p[0], w.p[1] + 2.4, w.p[2]);
    });
  }
}

export function ladderMeshes(scene, ladders) {
  const mat = new THREE.MeshStandardMaterial({ color: 0x4a3524, roughness: 0.8 });
  const g = new THREE.Group();
  for (const l of ladders) {
    const out = new THREE.Vector2(l.base[0] - l.wall[0], l.base[2] - l.wall[2]).normalize();
    const along = new THREE.Vector2(-out.y, out.x);
    const H = l.height + 1.1;
    const cx = l.wall[0] + out.x * 0.18, cz = l.wall[2] + out.y * 0.18;
    for (const s of [-0.28, 0.28]) {
      const rail = new THREE.Mesh(new THREE.BoxGeometry(0.06, H, 0.06), mat);
      rail.position.set(cx + along.x * s, H / 2, cz + along.y * s);
      g.add(rail);
    }
    const rung = new THREE.BoxGeometry(0.56, 0.035, 0.035);
    const n = Math.floor(H / 0.3);
    const im = new THREE.InstancedMesh(rung, mat, n);
    const m = new THREE.Matrix4();
    const rot = new THREE.Matrix4().makeRotationY(Math.atan2(-along.y, along.x));
    for (let i = 0; i < n; i++) { m.copy(rot).setPosition(cx, 0.25 + i * 0.3, cz); im.setMatrixAt(i, m); }
    g.add(im);
  }
  g.traverse((o) => { o.castShadow = true; });
  scene.add(g);
  return g;
}

export function bellMesh(scene, at) {
  const pts = [[0.0, 0.0], [0.62, 0.0], [0.58, 0.12], [0.46, 0.35], [0.38, 0.75], [0.36, 0.95], [0.22, 1.05], [0.0, 1.07]]
    .map(([r, y]) => new THREE.Vector2(r, y));
  const geo = new THREE.LatheGeometry(pts, 20).translate(0, -1.07, 0);
  const bell = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color: 0xa8792c, metalness: 0.9, roughness: 0.35, side: THREE.DoubleSide }));
  const pivot = new THREE.Group();
  pivot.position.set(at[0], at[1] + 1.07, at[2]);
  pivot.add(bell);
  scene.add(pivot);
  return pivot;
}

export function awningMesh(scene, aw) {
  const c = document.createElement("canvas"); c.width = 128; c.height = 32;
  const x = c.getContext("2d");
  for (let i = 0; i < 8; i++) { x.fillStyle = i % 2 ? "#efe3cc" : "#b8352a"; x.fillRect(i * 16, 0, 16, 32); }
  const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace;
  const len = aw.top - aw.bottom, w = aw.z1 - aw.z0;
  const geo = new THREE.PlaneGeometry(w, len).rotateY(Math.PI / 2).translate(0, -len / 2, 0);
  const mesh = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ map: tex, side: THREE.DoubleSide, roughness: 0.9 }));
  mesh.castShadow = true;
  const hinge = new THREE.Group();
  hinge.position.set(aw.x, aw.top, (aw.z0 + aw.z1) / 2);
  hinge.add(mesh);
  // frame: two posts and a top bar
  const fm = new THREE.MeshStandardMaterial({ color: 0x2b2420, roughness: 0.6 });
  for (const z of [aw.z0, aw.z1]) {
    const p = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, aw.top, 6), fm);
    p.position.set(aw.x, aw.top / 2, z); scene.add(p);
  }
  const bar = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, w, 6).rotateX(Math.PI / 2), fm);
  bar.position.set(aw.x, aw.top, (aw.z0 + aw.z1) / 2);
  scene.add(bar, hinge);
  return hinge;
}

export class Tracers {
  constructor(scene) { this.scene = scene; this.list = []; this.mat = new THREE.LineBasicMaterial({ color: 0xfff1c0, transparent: true, opacity: 0.9, fog: false }); }
  sync(bullets) {
    for (const b of bullets) {
      if (!b._line) {
        b._line = new THREE.Line(new THREE.BufferGeometry(), this.mat.clone());
        b._line.frustumCulled = false;
        this.scene.add(b._line); this.list.push(b);
        b._age = 0;
      }
      const pts = b.trail.slice(-6).map((p) => new THREE.Vector3(...p));
      b._line.geometry.setFromPoints(pts);
    }
  }
  update(dt) {
    for (const b of this.list) {
      if (!b.alive) { b._age += dt; b._line.material.opacity = Math.max(0, 0.9 - b._age * 1.5); }
      if (b._age > 0.7 && b._line.parent) this.scene.remove(b._line);
    }
  }
}
