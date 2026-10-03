"""Vegetation from low-poly foliage cards. Each clump/tree is a prototype instanced many times.
Canopy instances get a wind-sway driver (Blender); the viewer re-creates sway in a vertex shader."""
import math
import random
from mathutils import Vector, Matrix
from .core import MB, inst, register_proto, proto_coll, PROTOS

UVQ = [(0, 0), (1, 0), (1, 1), (0, 1)]


def _card(m, center, normal, size, mat, aspect=1.0, up=None, uv=UVQ):
    c = Vector(center)
    n = Vector(normal).normalized()
    up = Vector(up) if up is not None else Vector((0, 0, 1))
    if abs(n.dot(up)) > 0.95:
        up = Vector((1, 0, 0))
    r = up.cross(n).normalized()
    u = n.cross(r).normalized()
    hw, hh = size / 2, size * aspect / 2
    pts = [c - r * hw - u * hh, c + r * hw - u * hh, c + r * hw + u * hh, c - r * hw + u * hh]
    m.face([tuple(p) for p in pts], mat, uv=uv)


def _canopy(key, mat, n_cards, radii, center_z, card=1.2, seed=1, flat_bottom=0.35):
    if key in PROTOS:
        return
    rng = random.Random(seed)
    m = MB()
    rx, ry, rz = radii
    for i in range(n_cards):
        # points on/inside an ellipsoid, biased to the shell
        while True:
            d = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
            if 0.35 < d.length <= 1.0:
                break
        s = 0.75 + 0.25 * d.length
        if d.z < -flat_bottom:
            d.z = -flat_bottom - 0.1 * rng.random()
        p = Vector((d.x * rx * s, d.y * ry * s, center_z + d.z * rz * s))
        dn = d.normalized()
        nrm = Vector((dn.x + rng.uniform(-0.25, 0.25), dn.y + rng.uniform(-0.25, 0.25), dn.z * 0.6 + 0.35 + rng.uniform(-0.2, 0.2)))
        _card(m, p, nrm, card * rng.uniform(0.8, 1.2), mat)
    ob = m.to_object(key, proto_coll(), merge=False)
    register_proto(key, ob)


def _trunk(key, height, r0, r1, branches, seed, mat="bark", lean=0.12):
    if key in PROTOS:
        return
    rng = random.Random(seed)
    m = MB()
    pts, radii = [], []
    n = 8
    lx, ly = rng.uniform(-lean, lean), rng.uniform(-lean, lean)
    for i in range(n + 1):
        t = i / n
        pts.append((lx * t * t * height * 0.3 + 0.03 * math.sin(t * 7), ly * t * t * height * 0.3, height * t))
        radii.append(r0 + (r1 - r0) * t ** 0.7)
    m.tube(pts, 0, 7, mat, radii=radii)
    top = Vector(pts[-1])
    for b in range(branches):
        a = 2 * math.pi * b / branches + rng.uniform(-0.4, 0.4)
        L = rng.uniform(0.9, 1.5)
        base = Vector(pts[-3])
        tip = top + Vector((math.cos(a) * L, math.sin(a) * L, rng.uniform(0.4, 0.9)))
        mid = (base + tip) / 2 + Vector((0, 0, 0.2))
        m.tube([tuple(base), tuple(mid), tuple(tip)], 0, 5, mat, radii=[r1 * 0.9, r1 * 0.6, r1 * 0.25])
    ob = m.to_object(key, proto_coll(), merge=False)
    register_proto(key, ob)


def _palm():
    if "palm_trunk" in PROTOS:
        return
    m = MB()
    pts, radii = [], []
    H = 6.2
    for i in range(13):
        t = i / 12
        pts.append((0.9 * t * t, 0.15 * math.sin(t * 3), H * t))
        radii.append(0.2 - 0.07 * t)
    m.tube(pts, 0, 8, "palm_bark", radii=radii)
    # trunk rings
    for i in range(1, 12):
        p = Vector(pts[i])
        m.lathe([(radii[i] + 0.025, -0.03), (radii[i] + 0.025, 0.03)], 8, "palm_bark", cap_top=False,
                center=tuple(p))
    ob = m.to_object("palm_trunk", proto_coll(), merge=False)
    register_proto("palm_trunk", ob)
    # crown of fronds: each frond is a 3-segment bent strip with fixed UVs
    m = MB()
    top = Vector(pts[-1])
    rng = random.Random(4)
    nf = 16
    for f in range(nf):
        a = 2 * math.pi * f / nf + rng.uniform(-0.15, 0.15)
        droop = rng.uniform(0.25, 0.9)
        L = rng.uniform(2.6, 3.2)
        dirv = Vector((math.cos(a), math.sin(a), 0))
        side = Vector((-math.sin(a), math.cos(a), 0))
        segs = 4
        prev = None
        for s in range(segs):
            t0, t1 = s / segs, (s + 1) / segs
            p0 = top + dirv * (L * t0) + Vector((0, 0, 0.5 * t0 - droop * t0 * t0 * 2.0))
            p1 = top + dirv * (L * t1) + Vector((0, 0, 0.5 * t1 - droop * t1 * t1 * 2.0))
            w0, w1 = 0.38, 0.38
            tilt = Vector((0, 0, 0.12))
            q = [p0 - side * w0 - tilt, p1 - side * w1 - tilt, p1 + side * w1 + tilt, p0 + side * w0 + tilt]
            uv = [(t0, 0), (t1, 0), (t1, 1), (t0, 1)]
            m.face([tuple(v) for v in q], "palm_frond", uv=uv)
    ob = m.to_object("palm_crown", proto_coll(), merge=False)
    register_proto("palm_crown", ob)


def _cypress():
    if "cypress" in PROTOS:
        return
    m = MB()
    prof = [(0.12, 0.0), (0.12, 0.5), (0.55, 0.8), (0.75, 2.0), (0.72, 3.5), (0.55, 5.0), (0.32, 6.3), (0.0, 7.2)]
    m.lathe(prof, 9, "cypress", cap_top=False)
    # ragged edge cards
    rng = random.Random(9)
    for i in range(46):
        z = rng.uniform(0.9, 6.6)
        r = 0.62 * math.sin(math.pi * min(1, z / 7.4)) + 0.05
        a = rng.uniform(0, 6.283)
        p = (r * math.cos(a), r * math.sin(a), z)
        _card(m, p, (math.cos(a), math.sin(a), rng.uniform(-0.1, 0.5)), rng.uniform(0.8, 1.1), "leaf_cypress", aspect=1.5)
    ob = m.to_object("cypress", proto_coll(), merge=False)
    register_proto("cypress", ob)
    # distant silhouette version (no cards)
    m = MB()
    m.lathe(prof, 6, "cypress", cap_top=False, smooth=True)
    ob = m.to_object("cypress_lo", proto_coll(), merge=False)
    register_proto("cypress_lo", ob)


def _wall_clump(key, mat, n, radius, seed, hang=0.0, card=1.0):
    """Clump hugging a wall at y=0 (outward is -y): bougainvillea / ivy masses."""
    if key in PROTOS:
        return
    rng = random.Random(seed)
    m = MB()
    for i in range(n):
        x = rng.uniform(-radius, radius)
        z = rng.uniform(-radius * 0.6 - hang, radius * 0.6)
        y = -rng.uniform(0.04, 0.32) * (1 - abs(x) / radius * 0.5)
        nrm = (rng.uniform(-0.5, 0.5), -1, rng.uniform(-0.2, 0.6))
        _card(m, (x, y, z), nrm, rng.uniform(0.7, 1.1) * card, mat)
    ob = m.to_object(key, proto_coll(), merge=False)
    register_proto(key, ob)


def _ivy_hang():
    if "ivy_hang" in PROTOS:
        return
    m = MB()
    for i, (x, rot) in enumerate([(-0.25, -0.2), (0.05, 0.1), (0.3, 0.25)]):
        n = Vector((math.sin(rot), -1, 0))
        _card(m, (x, -0.05, -0.55), n, 0.6, "leaf_ivy", aspect=2.0)
    ob = m.to_object("ivy_hang", proto_coll(), merge=False)
    register_proto("ivy_hang", ob)


def _shrub():
    if "shrub" in PROTOS:
        return
    rng = random.Random(21)
    m = MB()
    for i in range(12):
        a = rng.uniform(0, 6.283)
        r = rng.uniform(0, 0.25)
        _card(m, (r * math.cos(a), r * math.sin(a), rng.uniform(0.2, 0.45)),
              (math.cos(a), math.sin(a), rng.uniform(0.2, 1.0)), rng.uniform(0.5, 0.7), "leaf_shrub")
    ob = m.to_object("shrub", proto_coll(), merge=False)
    register_proto("shrub", ob)
    m = MB()
    for i in range(3):
        a = math.pi * i / 3
        _card(m, (0, 0, 0.12), (math.cos(a), math.sin(a), 0), 0.5, "grass", aspect=0.5)
    ob = m.to_object("grass_tuft", proto_coll(), merge=False)
    register_proto("grass_tuft", ob)


def make_protos():
    _trunk("orange_trunk", 3.0, 0.12, 0.07, 5, seed=3)
    _canopy("orange_canopy", "leaf_orange", 95, (2.0, 2.0, 1.45), 4.1, card=1.35, seed=5)
    _trunk("olive_trunk", 2.0, 0.16, 0.08, 4, seed=7, lean=0.3)
    _canopy("olive_canopy", "leaf_olive", 60, (1.5, 1.5, 1.0), 2.9, card=1.1, seed=8)
    _trunk("orchard_trunk", 1.3, 0.07, 0.045, 4, seed=11)
    _canopy("orchard_canopy", "leaf_orange", 34, (1.0, 1.0, 0.8), 2.0, card=0.9, seed=12)
    _palm()
    _cypress()
    _wall_clump("bougainvillea", "leaf_bougainvillea", 26, 1.2, seed=31, hang=0.6)
    _wall_clump("ivy_mass", "leaf_shrub", 48, 1.0, seed=32, hang=0.5, card=0.55)
    _ivy_hang()
    _shrub()


_phase = [0]


def _sway(ob, amp=0.012, speed=0.06):
    _phase[0] += 1
    ph = (_phase[0] * 1.618) % 6.283
    for axis, k in ((0, 1.0), (1, 0.7)):
        fc = ob.driver_add("rotation_euler", axis)
        base = ob.rotation_euler[axis]
        fc.driver.expression = f"{base:.4f}+sin(frame*{speed * k:.4f}+{ph + axis:.3f})*{amp:.4f}"
    ob["sway"] = amp


def tree(kind, loc, coll_, rot=0.0, scale=1.0, pot=None, pot_scale=1.0):
    x, y, z = loc
    rz = z
    if pot:
        inst(pot, (x, y, z), rot, coll_, scale=pot_scale)
        rz = z + (0.7 if pot == "pot_terracotta" else 0.95) * pot_scale
    t = inst(f"{kind}_trunk", (x, y, rz), rot, coll_, scale=scale)
    c = inst(f"{kind}_canopy", (x, y, rz), rot, coll_, scale=scale)
    _sway(c, 0.010 / scale)
    return t, c


def palm(loc, coll_, rot=0.0, scale=1.0):
    inst("palm_trunk", loc, rot, coll_, scale=scale)
    c = inst("palm_crown", loc, rot, coll_, scale=scale)
    _sway(c, 0.008, 0.05)


def cypress(loc, coll_, scale=1.0, lo=False):
    inst("cypress_lo" if lo else "cypress", loc, random.uniform(0, 6.28), coll_,
         scale=(scale * random.uniform(0.85, 1.1), scale * random.uniform(0.85, 1.1), scale))


def wall_clump(kind, loc, rot, coll_, scale=1.0):
    c = inst(kind, loc, rot, coll_, scale=scale)
    _sway(c, 0.006, 0.08)
    return c


def shrub(loc, coll_, scale=1.0):
    c = inst("shrub", loc, random.uniform(0, 6.28), coll_, scale=scale)
    return c
