"""Facade + building generator: real wall thickness, recessed (arched) openings with reveals,
architraves, string courses, cornice tile band, parapet, quoins. Repeated parts are instanced."""
import math
import random
from mathutils import Vector
from .core import MB, inst, materials
from . import assets as A
from .assets import _outline

FLOOR_H = 3.2
WALL_T = 0.40


def _area(poly):
    a = 0
    for (x0, z0), (x1, z1) in zip(poly, poly[1:] + poly[:1]):
        a += x0 * z1 - x1 * z0
    return a / 2


class Side:
    """One straight wall: origin (x, y), direction angle a, length L. Inside is to the left."""

    def __init__(self, x, y, a, L):
        self.o = Vector((x, y, 0))
        self.t = Vector((math.cos(a), math.sin(a), 0))
        self.n_in = Vector((-math.sin(a), math.cos(a), 0))
        self.a = a
        self.L = L

    def w(self, u, v, z, base=0.0):
        p = self.o + self.t * u + self.n_in * v
        return (p.x, p.y, base + z)


def facade(m, side, base_z, height, openings, wall_mat, trim_mat="stone_trim", thick=WALL_T,
           architrave=True):
    """openings: list of dict(u, z, w, h, arch, kind). Adds wall faces (outer plane v=0), reveals."""
    L = side.L
    xs = {0.0, L}
    zs = {0.0, height}
    boxes = []
    for o in openings:
        x0, x1 = o["u"] - o["w"] / 2, o["u"] + o["w"] / 2
        z0, z1 = o["z"], o["z"] + o["h"]
        boxes.append((x0, x1, z0, z1, o))
        xs |= {x0, x1}
        zs |= {z0, z1}
    xs, zs = sorted(xs), sorted(zs)

    def W(u, z, v=0.0):
        return side.w(u, v, z, base_z)

    def quad_uz(pts, v=0.0, mat=wall_mat):
        if _area(pts) < 0:
            pts = pts[::-1]
        m.face([W(u, z, v) for u, z in pts], mat)

    for i in range(len(xs) - 1):
        for j in range(len(zs) - 1):
            uc, zc = (xs[i] + xs[i + 1]) / 2, (zs[j] + zs[j + 1]) / 2
            if any(b[0] < uc < b[1] and b[2] < zc < b[3] for b in boxes):
                continue
            quad_uz([(xs[i], zs[j]), (xs[i + 1], zs[j]), (xs[i + 1], zs[j + 1]), (xs[i], zs[j + 1])])
    for x0, x1, z0, z1, o in boxes:
        w, h, arch = o["w"], o["h"], o["arch"]
        uc = o["u"]
        if arch:
            r = w / 2
            spring = z0 + h - r
            n = 10
            left = [(x0, z1)] + [(uc + r * math.cos(math.pi / 2 + (math.pi / 2) * k / (n // 2)),
                                  spring + r * math.sin(math.pi / 2 + (math.pi / 2) * k / (n // 2)))
                                 for k in range(n // 2 + 1)]
            right = [(x1, z1)] + [(uc + r * math.cos(math.pi / 2 - (math.pi / 2) * k / (n // 2)),
                                   spring + r * math.sin(math.pi / 2 - (math.pi / 2) * k / (n // 2)))
                                  for k in range(n // 2 + 1)]
            quad_uz(left)
            quad_uz(right)
        outline = [(uc + x, z0 + z) for x, z in _outline(w, h, arch)]
        # reveals (inward-facing), toward opening centre
        cen = Vector(W(uc, z0 + h * 0.5, thick * 0.5))
        for p, q in zip(outline, outline[1:] + outline[:1]):
            f = [W(p[0], p[1], 0), W(q[0], q[1], 0), W(q[0], q[1], thick), W(p[0], p[1], thick)]
            mid = sum((Vector(c) for c in f), Vector()) / 4
            nrm = (Vector(f[1]) - Vector(f[0])).cross(Vector(f[2]) - Vector(f[1]))
            if nrm.dot(cen - mid) < 0:
                f = f[::-1]
            m.face(f, trim_mat)
        if architrave and o["kind"] != "none":
            e = 0.13
            outer = [(uc + x, z0 + z) for x, z in _outline(w + 2 * e, h + e, arch)]
            vv = -0.045
            segs = list(zip(range(len(outline)), range(1, len(outline) + 1)))
            for a_, b_ in segs[1:]:  # skip bottom
                b_ %= len(outline)
                pi, qi = outline[a_], outline[b_]
                po, qo = outer[a_], outer[b_]
                # front ring face
                fr = [W(pi[0], pi[1], vv), W(qi[0], qi[1], vv), W(qo[0], qo[1], vv), W(po[0], po[1], vv)]
                nrm = (Vector(fr[1]) - Vector(fr[0])).cross(Vector(fr[2]) - Vector(fr[1]))
                if nrm.dot(-side.n_in) < 0:
                    fr = fr[::-1]
                m.face(fr, trim_mat)
                # outer edge strip
                st = [W(po[0], po[1], 0), W(qo[0], qo[1], 0), W(qo[0], qo[1], vv), W(po[0], po[1], vv)]
                mid = sum((Vector(c) for c in st), Vector()) / 4
                nrm = (Vector(st[1]) - Vector(st[0])).cross(Vector(st[2]) - Vector(st[1]))
                if nrm.dot(mid - cen) < 0:
                    st = st[::-1]
                m.face(st, trim_mat)
                # inner lip strip
                st = [W(pi[0], pi[1], 0), W(qi[0], qi[1], 0), W(qi[0], qi[1], vv), W(pi[0], pi[1], vv)]
                mid = sum((Vector(c) for c in st), Vector()) / 4
                nrm = (Vector(st[1]) - Vector(st[0])).cross(Vector(st[2]) - Vector(st[1]))
                if nrm.dot(cen - mid) < 0:
                    st = st[::-1]
                m.face(st, trim_mat)


def band(m, side, base_z, z0, z1, out, mat, ext=0.0):
    """Horizontal strip proud of the wall by `out` (string course / cornice)."""
    u0, u1 = -out - ext, side.L + out + ext
    P = lambda u, v, z: side.w(u, v, z, base_z)
    outw = -side.n_in
    m.face([P(u0, -out, z0), P(u1, -out, z0), P(u1, -out, z1), P(u0, -out, z1)], mat, orient=outw)
    m.face([P(u0, 0.0, z1), P(u0, -out, z1), P(u1, -out, z1), P(u1, 0.0, z1)], mat, orient=(0, 0, 1))
    m.face([P(u0, 0.0, z0), P(u1, 0.0, z0), P(u1, -out, z0), P(u0, -out, z0)], mat, orient=(0, 0, -1))
    m.face([P(u0, 0, z0), P(u0, -out, z0), P(u0, -out, z1), P(u0, 0, z1)], mat, orient=-side.t)
    m.face([P(u1, -out, z0), P(u1, 0, z0), P(u1, 0, z1), P(u1, -out, z1)], mat, orient=side.t)


# ------------------------------------------------------------------ building
def default_openings(L, floors, rng, door_at=None, style="arch", ground_doors=1, balcony_floor=1,
                     bay=2.7):
    nb = max(1, int(L / bay))
    step = L / nb
    us = [step * (i + 0.5) for i in range(nb)]
    plan = []
    if door_at is None:
        door_at = [us[len(us) // 2]] if ground_doors else []
    for f in range(floors):
        row = []
        for u in us:
            if f == 0:
                if any(abs(u - d) < step * 0.5 for d in door_at):
                    row.append(dict(u=u, z=0.0, w=1.15, h=2.5, arch=True, kind="door"))
                else:
                    row.append(dict(u=u, z=0.85, w=1.0, h=1.75, arch=(style == "arch"), kind="window"))
            elif f == balcony_floor and rng.random() < 0.45:
                row.append(dict(u=u, z=f * FLOOR_H + 0.05, w=1.05, h=2.35, arch=True, kind="balcony"))
            else:
                arch = (style == "arch") and f < floors - 1 or rng.random() < 0.2
                hh = 1.75 if f < floors - 1 else 1.4
                row.append(dict(u=u, z=f * FLOOR_H + 0.9, w=0.95 if f < floors - 1 else 0.85,
                                h=hh, arch=arch, kind="window"))
        plan.append(row)
    return plan


def building(spec, coll_, seed=1, wall_mat="ashlar", plinth_mat="ashlar_dark", sides_cfg=None,
             parapet="solid", lit_prob=0.18, awnings=None, lamps=True):
    """spec: dict(name, rect=(x0,y0,x1,y1), z, floors). sides_cfg: per side key 's','e','n','w'
    → dict(openings=..., skip=False, door_at=[u...]) . Returns anchors for vegetation."""
    rng = random.Random(seed)
    x0, y0, x1, y1 = spec["rect"]
    bz = spec["z"]
    floors = spec["floors"]
    top = floors * FLOOR_H
    par_h = 0.95 if parapet == "solid" else 0.0
    H = top + par_h
    sides = {
        "s": Side(x0, y0, 0.0, x1 - x0),
        "e": Side(x1, y0, math.pi / 2, y1 - y0),
        "n": Side(x1, y1, math.pi, x1 - x0),
        "w": Side(x0, y1, -math.pi / 2, y1 - y0),
    }
    sides_cfg = sides_cfg or {}
    anchors = dict(window_boxes=[], balconies=[], doors=[], walls=[], roof=(x0, y0, x1, y1, bz + top))
    m = MB()
    awnings = awnings or {}
    for key, sd in sides.items():
        cfg = sides_cfg.get(key, {})
        if cfg.get("skip"):
            # blind wall (party wall / back), still solid
            facade(m, sd, bz, H, [], wall_mat)
            continue
        plan = cfg.get("openings") or default_openings(
            sd.L, floors, rng, door_at=cfg.get("door_at"), style=cfg.get("style", "arch"),
            ground_doors=cfg.get("ground_doors", 1))
        flat_ops = [o for row in plan for o in row if o["kind"] != "none"]
        facade(m, sd, bz, H, flat_ops, wall_mat)
        anchors["walls"].append((key, sd))
        for o in flat_ops:
            u, z, w, h, arch = o["u"], o["z"], o["w"], o["h"], o["arch"]
            loc = sd.w(u, 0, z, bz)
            if o["kind"] == "door":
                inst(A.door_unit(w, h, arch), loc, sd.a, coll_)
                anchors["doors"].append((loc, sd.a))
                if lamps:
                    for s in (-1, 1):
                        inst("wall_lamp", sd.w(u + s * (w / 2 + 0.45), 0, 2.0, bz), sd.a, coll_)
                kind = awnings.get((key, round(u, 1)))
                if kind:
                    inst(A.awning(w + 0.9, kind), sd.w(u, -0.0, z + h + 0.45, bz), sd.a, coll_)
            elif o["kind"] == "balcony":
                inst(A.door_unit(w, h, arch), loc, sd.a, coll_)
                bw = w + 1.0
                inst(A.balcony(bw), loc, sd.a, coll_)
                for s in (-1, 1):
                    inst("corbel", sd.w(u + s * (bw / 2 - 0.2), 0, z - 0.22, bz), sd.a, coll_)
                # railing: front + sides
                n = 2
                for i in range(n):
                    uu = u - bw / 2 + bw * (i + 0.5) / n
                    inst("railing_iron", sd.w(uu, -0.96, z, bz), sd.a, coll_, scale=(bw / n, 1, 1))
                for s in (-1, 1):
                    inst("railing_iron", sd.w(u + s * (bw / 2 - 0.03), -0.5, z, bz), sd.a + math.pi / 2,
                         coll_, scale=(0.94, 1, 1))
                anchors["balconies"].append((sd.w(u, -0.5, z, bz), sd.a, bw))
            else:
                lit = rng.random() < lit_prob
                inst(A.window_unit(w, h, arch, lit), loc, sd.a, coll_)
                inst(A.sill(w), sd.w(u, 0, z, bz), sd.a, coll_)
                if not arch:
                    inst(A.shutter_pair(w, h), loc, sd.a, coll_)
                kind = awnings.get((key, round(u, 1)))
                if kind:
                    inst(A.awning(w + 0.5, kind), sd.w(u, 0, z + h + 0.35, bz), sd.a, coll_)
                elif z > 1 and rng.random() < 0.35:
                    inst("window_box", sd.w(u, -0.1, z - 0.02, bz), sd.a, coll_)
                    anchors["window_boxes"].append((sd.w(u, -0.2, z + 0.15, bz), sd.a))
        # horizontal articulation
        band(m, sd, bz, 0.0, 0.55, 0.06, plinth_mat)
        for f in range(1, floors):
            band(m, sd, bz, f * FLOOR_H - 0.08, f * FLOOR_H + 0.1, 0.07, "stone_trim")
        band(m, sd, bz, top - 0.42, top - 0.12, 0.02, "tile")
        band(m, sd, bz, top - 0.12, top + 0.08, 0.16, "stone_trim")
        if parapet == "solid":
            band(m, sd, bz, H - 0.02, H + 0.08, 0.06, "stone_trim")
    # parapet inner faces + roof deck
    inset = 0.25
    if parapet == "solid":
        ip = [(x0 + inset, y0 + inset), (x1 - inset, y0 + inset), (x1 - inset, y1 - inset), (x0 + inset, y1 - inset)]
        for (ax, ay), (bx_, by_) in zip(ip, ip[1:] + ip[:1]):
            cxm, cym = (x0 + x1) / 2 - (ax + bx_) / 2, (y0 + y1) / 2 - (ay + by_) / 2
            m.face([(ax, ay, bz + top), (ax, ay, bz + H + 0.08), (bx_, by_, bz + H + 0.08), (bx_, by_, bz + top)],
                   wall_mat, orient=(cxm, cym, 0))
        # parapet top cap
        op = [(x0 - 0.06, y0 - 0.06), (x1 + 0.06, y0 - 0.06), (x1 + 0.06, y1 + 0.06), (x0 - 0.06, y1 + 0.06)]
        for (a, b), (c, d) in zip(zip(op, ip), zip(op[1:] + op[:1], ip[1:] + ip[:1])):
            m.face([(a[0], a[1], bz + H + 0.08), (c[0], c[1], bz + H + 0.08), (d[0], d[1], bz + H + 0.08),
                    (b[0], b[1], bz + H + 0.08)], "stone_trim")
        m.face([(x, y, bz + top) for x, y in ip], "flagstone")
    else:
        m.face([(x0, y0, bz + top + 0.08), (x1, y0, bz + top + 0.08), (x1, y1, bz + top + 0.08),
                (x0, y1, bz + top + 0.08)], "flagstone")
        # balustrade round the roof edge
        pts = [(x0 + 0.2, y0 + 0.2), (x1 - 0.2, y0 + 0.2), (x1 - 0.2, y1 - 0.2), (x0 + 0.2, y1 - 0.2), (x0 + 0.2, y0 + 0.2)]
        for (ax, ay), (bx_, by_) in zip(pts[:-1], pts[1:]):
            L = math.hypot(bx_ - ax, by_ - ay)
            n = max(1, round(L / 1.2))
            ang = math.atan2(by_ - ay, bx_ - ax)
            for i in range(n):
                t = (i + 0.5) / n
                inst("balustrade", (ax + (bx_ - ax) * t, ay + (by_ - ay) * t, bz + top + 0.08), ang, coll_,
                     scale=(L / n / 1.2, 1, 1))
    ob = m.to_object(spec["name"], coll_, bevel=0.025)
    # quoins
    corners = [((x0, y0), 0), ((x1, y0), math.pi / 2), ((x1, y1), math.pi), ((x0, y1), -math.pi / 2)]
    for (cx, cy), r in corners:
        k = 0
        z = 0.55
        while z < top - 0.5:
            inst("quoin_a" if k % 2 == 0 else "quoin_b", (cx, cy, bz + z), r, coll_)
            z += 0.32
            k += 1
    return ob, anchors


def dome(center, base_z, radius, coll_, name="dome"):
    """Octagonal drum + copper dome + lantern finial."""
    cx, cy = center
    m = MB()
    m.lathe([(radius * 1.05, 0.0), (radius * 1.05, 0.25)], 8, "stone_trim", center=(cx, cy, base_z), cap_top=True)
    m.lathe([(radius, 0.25), (radius, 1.6)], 8, "plaster", center=(cx, cy, base_z), cap_top=False, smooth=False)
    m.lathe([(radius * 1.08, 1.6), (radius * 1.08, 1.8)], 8, "tile", center=(cx, cy, base_z), cap_top=False, smooth=False)
    prof = [(radius * 1.12, 1.8), (radius * 1.12, 1.9)]
    for k in range(1, 11):
        a = (math.pi / 2) * k / 10
        prof.append((radius * 1.05 * math.cos(a) + 0.001, 1.9 + radius * 1.15 * math.sin(a)))
    m.lathe(prof, 16, "copper", center=(cx, cy, base_z), cap_top=False)
    top = base_z + 1.9 + radius * 1.15
    m.lathe([(0.25, 0), (0.25, 0.6), (0.32, 0.65), (0.0, 1.05)], 8, "copper", center=(cx, cy, top))
    m.lathe([(0.05, 1.0), (0.05, 1.5), (0.12, 1.55), (0.0, 1.7)], 6, "brass", center=(cx, cy, top))
    # drum openings: dark slits
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8
        r = radius * math.cos(math.pi / 8) + 0.01
        px, py = cx + r * math.cos(a), cy + r * math.sin(a)
        tx, ty = -math.sin(a) * 0.22, math.cos(a) * 0.22
        m.face([(px - tx, py - ty, base_z + 0.5), (px + tx, py + ty, base_z + 0.5),
                (px + tx, py + ty, base_z + 1.35), (px - tx, py - ty, base_z + 1.35)], "interior_lit")
    return m.to_object(name, coll_, merge=False)
