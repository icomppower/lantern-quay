"""Lightweight distant scenery: low-poly hill ring, cypress rows, a hill town of instanced
blocks and domes, an aqueduct. All silhouettes, kept cheap (shared meshes)."""
import math
import random
from .core import MB, coll, inst, register_proto, proto_coll, PROTOS
from . import veg


def _hills(C):
    rng = random.Random(5)
    m = MB()
    rings, segs = 4, 72
    radii = [135, 195, 265, 345, 430]
    cx, cy = 67, 36
    hts = []
    for j, r in enumerate(radii):
        row = []
        for s in range(segs):
            a = 2 * math.pi * s / segs
            base = (math.sin(a * 3 + 1.1) * 0.5 + math.sin(a * 7 + 0.3) * 0.3 + math.sin(a * 13) * 0.2)
            h = (6 + 26 * j / (len(radii) - 1)) * (0.75 + 0.35 * base) + rng.uniform(-2, 2)
            if j == 0:
                h = rng.uniform(0, 3)
            # keep the south (behind reference camera) and east low so the sun reads
            row.append((cx + r * math.cos(a), cy + r * math.sin(a), max(-0.02, h)))
        hts.append(row)
    for j in range(len(radii) - 1):
        for s in range(segs):
            a, b = hts[j][s], hts[j][(s + 1) % segs]
            c, d = hts[j + 1][(s + 1) % segs], hts[j + 1][s]
            mat = "hill" if j < 2 else "hill_far"
            m.face([a, b, c, d], mat, orient=(0, 0, 1))
    ob = m.to_object("distant_hills", C, merge=True)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def _block_protos():
    if "town_block_a" in PROTOS:
        return
    for key, (w, d, h) in {"town_block_a": (6, 5, 8), "town_block_b": (4, 6, 11), "town_block_c": (8, 5, 6)}.items():
        m = MB()
        m.box((-w / 2, -d / 2, 0), (w / 2, d / 2, h), "distant_stone")
        m.box((-w / 2 - 0.2, -d / 2 - 0.2, h), (w / 2 + 0.2, d / 2 + 0.2, h + 0.4), "distant_stone_lit")
        for i in range(int(w / 1.8)):
            x = -w / 2 + 1.0 + i * 1.8
            for z in range(1, int(h / 3) + 1):
                m.box((x - 0.3, -d / 2 - 0.02, z * 3 - 1.6), (x + 0.3, -d / 2, z * 3 - 0.5), "interior")
        register_proto(key, m.to_object(key, proto_coll(), merge=False))
    m = MB()
    m.lathe([(2.2, 0), (2.2, 1.5)], 10, "distant_stone", cap_top=False)
    prof = [(2.3, 1.5)] + [(2.2 * math.cos(math.pi / 2 * k / 6) + 0.001, 1.5 + 2.4 * math.sin(math.pi / 2 * k / 6)) for k in range(1, 7)]
    m.lathe(prof, 12, "copper_far", cap_top=False)
    register_proto("town_dome", m.to_object("town_dome", proto_coll(), merge=False))
    m = MB()
    m.box((-1.2, -1.2, 0), (1.2, 1.2, 16), "distant_stone")
    m.lathe([(1.5, 16), (0.0, 19)], 4, "copper_far")
    register_proto("town_tower", m.to_object("town_tower", proto_coll(), merge=False))
    # aqueduct module: one arch bay 8 m
    m = MB()
    m.box((-4, -1.2, 9), (4, 1.2, 11), "distant_stone")
    for sx in (-4, 4):
        m.box((sx - 0.9, -1.2, 0), (sx + 0.9, 1.2, 9), "distant_stone")
    n = 8
    for k in range(n):
        a0, a1 = math.pi * k / n, math.pi * (k + 1) / n
        p0 = (3.1 * math.cos(a0), 6.0 + 3.0 * math.sin(a0))
        p1 = (3.1 * math.cos(a1), 6.0 + 3.0 * math.sin(a1))
        for y, o in ((-1.2, (0, -1, 0)), (1.2, (0, 1, 0))):
            m.face([(p0[0], y, p0[1]), (p1[0], y, p1[1]), (p1[0], y, 9.0), (p0[0], y, 9.0)], "distant_stone", orient=o)
    register_proto("aqueduct_bay", m.to_object("aqueduct_bay", proto_coll(), merge=False))


def build():
    C = coll("scenery")
    _hills(C)
    _block_protos()
    rng = random.Random(77)
    # hill town to the north-east, climbing a slope, seen over the canal gap
    for i in range(46):
        a = math.radians(rng.uniform(28, 72))
        r = rng.uniform(150, 200)
        x, y = 67 + r * math.cos(a), 36 + r * math.sin(a)
        z = (r - 135) * 0.22
        k = rng.choice(["town_block_a", "town_block_b", "town_block_c"])
        inst(k, (x, y, z), rng.uniform(-0.3, 0.3) + a + math.pi / 2, C, scale=rng.uniform(0.9, 1.3))
    for (a, r) in ((45, 185), (58, 175), (36, 195)):
        x, y = 67 + r * math.cos(math.radians(a)), 36 + r * math.sin(math.radians(a))
        inst("town_dome", (x, y, (r - 135) * 0.22 + 9), 0, C, scale=1.4)
    for (a, r) in ((52, 183), (40, 170)):
        x, y = 67 + r * math.cos(math.radians(a)), 36 + r * math.sin(math.radians(a))
        inst("town_tower", (x, y, (r - 135) * 0.22), 0.4, C)
    # aqueduct crossing the northern fields
    for i in range(14):
        inst("aqueduct_bay", (-60 + i * 8, 112, -0.5), 0, C)
    # cypress rows (low-poly silhouettes) along field lines, like the reference skyline
    for i in range(22):
        veg.cypress((-4 + i * 3.4, -24 + rng.uniform(-0.5, 0.5), 0), C, scale=rng.uniform(1.1, 1.5), lo=True)
    for i in range(18):
        veg.cypress((-30 + i * 3.6, 96 + rng.uniform(-0.5, 0.5), 0), C, scale=rng.uniform(1.0, 1.4), lo=True)
    for i in range(16):
        veg.cypress((152 + rng.uniform(-0.5, 0.5), 14 + i * 3.8, 0), C, scale=rng.uniform(1.1, 1.5), lo=True)
    for i in range(10):
        veg.cypress((-12 + rng.uniform(-0.4, 0.4), 4 + i * 3.4, 0), C, scale=rng.uniform(1.0, 1.3), lo=True)
    # olive groves (shared canopy mesh) in the near fields
    for gx in range(6):
        for gy in range(3):
            veg.tree("olive", (154 + gx * 6.5 + rng.uniform(-1, 1), -30 + gy * 6.5, 0), C, rot=rng.uniform(0, 6),
                     scale=rng.uniform(0.8, 1.1))
    for gx in range(5):
        for gy in range(2):
            veg.tree("olive", (-36 + gx * 6.5, 40 + gy * 6.5, 0), C, rot=rng.uniform(0, 6), scale=rng.uniform(0.8, 1.0))
