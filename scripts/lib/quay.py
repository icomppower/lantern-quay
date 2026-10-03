"""Lantern Quay v1 sample (stage 5): grows the Canal District into a ~150 x 100 m block by repeating
its building modules along the extended main and side canals, plus a bell tower, two perch roofs,
two more humpback bridges, quay furniture and instanced town fill. Reuses arch/site/assets/veg as-is."""
import math
import random
import bpy
from .core import MB, coll, inst
from . import layout as Lo
from . import lq_layout as Q
from . import site, arch, veg, sky


def _flag_rect(m, x0, y0, x1, y1, z=0.0, mat="flagstone"):
    m.face([(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)], mat, orient=(0, 0, 1))


def ground(C):
    """Paved streets inside the world bounds (canal corridors left open), fields outside."""
    old = bpy.data.objects.get("ground_outer")
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    m = MB()
    X0, X1, Y0, Y1 = Q.X0, Q.X1, Q.Y0, Q.Y1
    for r in ((X0, Y0, X1, 0.0), (X0, 0.0, 0.0, 30.0), (40.0, 0.0, X1, Lo.CANAL_Y0), (40.0, Lo.CANAL_Y1, X1, 30.0),
              (X0, 30.0, Lo.CANAL_X0, Y1), (Lo.CANAL_X1, 30.0, X1, Y1)):
        _flag_rect(m, *r)
    paved = m.to_object("ground_streets", C)
    E = 260.0
    h = MB()
    for r in ((X0 - E, Y0 - E, X0, Y1 + E), (X1, Y0 - E, X1 + E, Lo.CANAL_Y0), (X1, Lo.CANAL_Y1, X1 + E, Y1 + E),
              (X0, Y0 - E, X1, Y0), (X0, Y1, Lo.CANAL_X0, Y1 + E), (Lo.CANAL_X1, Y1, X1, Y1 + E)):
        _flag_rect(h, *r, z=-0.02, mat="hill")
    return paved, h.to_object("ground_outer", C)


def _bridge_at(center, rot_deg, D):
    """site.bridge() builds at Lo.BRIDGE_Y across Lo.CANAL_X0..X1; build it at the origin and move it."""
    saved = (Lo.CANAL_X0, Lo.CANAL_X1, Lo.BRIDGE_Y)
    Lo.CANAL_X0, Lo.CANAL_X1, Lo.BRIDGE_Y = -2.5, 2.5, 0.0
    tmp = coll("_bridge_tmp")
    site.bridge(tmp)
    Lo.CANAL_X0, Lo.CANAL_X1, Lo.BRIDGE_Y = saved
    a = math.radians(rot_deg)
    ca, sa = math.cos(a), math.sin(a)
    for ob in list(tmp.objects):
        x, y, z = ob.location
        ob.location = (center[0] + x * ca - y * sa, center[1] + x * sa + y * ca, z)
        ob.rotation_euler.z += a
        tmp.objects.unlink(ob)
        D.objects.link(ob)
    bpy.data.collections.remove(tmp)


def _awnings_for(L, floors, seed, count=2):
    """Pick ground-floor bays (same spacing as arch.default_openings) to carry awnings."""
    nb = max(1, int(L / 2.7))
    step = L / nb
    us = [round(step * (i + 0.5), 1) for i in range(nb)]
    rng = random.Random(seed)
    kinds = ["awning_blue", "awning_red", "awning_ochre"]
    return {u: rng.choice(kinds) for u in rng.sample(us, min(count, len(us)))}


def _house(b, D, V, seed, lights, extra_skip=()):
    x0, y0, x1, y1 = b["rect"]
    face = b["face"]
    L = (x1 - x0) if face in ("n", "s") else (y1 - y0)
    aw = _awnings_for(L, b["floors"], seed, 2 if b["floors"] > 2 else 1)
    cfg = {k: dict(ground_doors=1 if k == face else 0) for k in "nesw"}
    for k in extra_skip:
        cfg[k] = dict(skip=True)
    cfg[face] = dict(ground_doors=1)
    spec = dict(name=b["name"], rect=b["rect"], z=0.0, floors=b["floors"])
    ob, anc = arch.building(spec, D, seed=seed, wall_mat=b["wall"],
                            parapet="balustrade" if seed % 5 == 0 else "solid", sides_cfg=cfg,
                            awnings={(face, u): k for u, k in aw.items()}, lamps=True)
    top = b["floors"] * Q.FLOOR_H
    rng = random.Random(seed * 7)
    if b["name"] in Q.DOMES:
        arch.dome(((x0 + x1) / 2, (y0 + y1) / 2), top, Q.DOMES[b["name"]], D, name=b["name"] + "_dome")
    elif b["name"] in Q.ROOF_GARDENS:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        for k in range(3):
            px = cx + (k - 1) * min(2.4, (x1 - x0) / 4)
            inst("planter_box", (px, cy, top), 0, D, scale=(1.1, 1.6, 1))
            veg.tree("orchard", (px, cy, top + 0.36), V, rot=k + seed, scale=0.95)
    for (loc, rot) in anc["window_boxes"]:
        if rng.random() < 0.6:
            veg.shrub((loc[0], loc[1], loc[2] - 0.05), V, 0.55)
    for (loc, rot, bw) in anc["balconies"]:
        ox, oy = math.sin(rot), -math.cos(rot)
        inst("ivy_hang", (loc[0] + ox * 0.5, loc[1] + oy * 0.5, loc[2] - 0.2), rot, V)
    if rng.random() < 0.5:  # bougainvillea over the quay face
        sd = dict(anc["walls"])[face]
        p = sd.w(L * rng.uniform(0.2, 0.8), 0, rng.uniform(2.6, 4.2), 0.0)
        veg.wall_clump("bougainvillea", p, sd.a, V, rng.uniform(0.8, 1.1))
    for loc, rot in anc["doors"][:1]:
        ox, oy = math.sin(rot), -math.cos(rot)
        lights.append((loc[0] + ox * 0.5, loc[1] + oy * 0.5, loc[2] + 2.0))
    return ob, anc


def bell_tower(D, lights):
    t = Q.TOWER
    x0, y0, x1, y1 = t["rect"]
    spec = dict(name="bell_tower", rect=t["rect"], z=0.0, floors=t["floors"])
    arch.building(spec, D, seed=21, wall_mat="ashlar",
                  sides_cfg={"s": dict(ground_doors=1), "n": dict(ground_doors=0), "e": dict(ground_doors=0),
                             "w": dict(skip=True)})
    top = t["floors"] * Q.FLOOR_H
    bh = t["belfry_h"]
    m = MB()
    # four corner piers of the open belfry, a slab, then the copper dome on top
    for cx, cy in ((x0 + 0.45, y0 + 0.45), (x1 - 0.45, y0 + 0.45), (x1 - 0.45, y1 - 0.45), (x0 + 0.45, y1 - 0.45)):
        m.box((cx - 0.45, cy - 0.45, top + 0.95), (cx + 0.45, cy + 0.45, top + bh), "ashlar")
    m.box((x0 - 0.15, y0 - 0.15, top + bh), (x1 + 0.15, y1 + 0.15, top + bh + 0.35), "stone_trim")
    m.box((x0 - 0.05, y0 - 0.05, top + bh - 0.35), (x1 + 0.05, y1 + 0.05, top + bh), "tile")
    m.to_object("belfry", D, bevel=0.02)
    arch.dome(((x0 + x1) / 2, (y0 + y1) / 2), top + bh + 0.35, t["dome_r"], D, name="tower_dome")
    lights.append(((x0 + x1) / 2, y0 - 0.6, 2.4))
    return top


def quay_furniture(P, V, Lt):
    rng = random.Random(404)
    lamps = []
    # lantern pillars along both main-canal quays, clear of the crowd lanes (on the coping line)
    for x in range(44, 141, 12):
        if abs(x - Q.TOLL_BRIDGE["center"][0]) < 4 or 116 < x < 129:
            continue
        for y in (Lo.CANAL_Y0 - 0.45, Lo.CANAL_Y1 + 0.45):
            inst("pillar", (x, y, 0.0), 0, P, scale=0.85)
            inst("lantern", (x, y, 1.38 * 0.85), 0, P, scale=0.8)
            lamps.append((x, y, 1.6))
    for y in range(36, 84, 10):  # side-canal quays
        for x in (Lo.CANAL_X0 - 0.45, Lo.CANAL_X1 + 0.45):
            inst("pillar", (x, y, 0.0), 0, P, scale=0.85)
            inst("lantern", (x, y, 1.38 * 0.85), 0, P, scale=0.8)
    for x in range(46, 140, 7):
        if abs(x + 0.5 - Q.TOLL_BRIDGE["center"][0]) < 3:
            continue
        inst("mooring_post", (x + 0.5, Lo.CANAL_Y0 - 0.25, -0.02), 0, P)
    # boats moored along the canals (static in v1)
    for (x, y, k, r) in ((52.0, 4.6, "boat_a", 0.02), (71.0, 7.4, "boat_b", 3.16), (88.0, 4.6, "boat_a", 3.1),
                         (104.0, 7.4, "boat_b", 0.04), (136.0, 4.7, "boat_a", 0.0), (29.0, 44.0, "boat_b", 1.6),
                         (31.0, 66.0, "boat_a", -1.55), (29.1, 78.0, "boat_a", 1.57)):
        inst(k, (x, y, Lo.WATER_Z - 0.12), r, P)
    # cargo and benches against the building fronts (outside the crowd lanes)
    for x in (66.0, 95.5, 111.5):
        for dx, k in ((0.0, "crate"), (0.7, "crate"), (1.4, "barrel")):
            inst(k, (x + dx, -1.15, 0.0), rng.uniform(0, 0.5), P)
    for x in (80.0, 102.0):
        inst("bench", (x, 10.75, 0.0), math.pi, P)
    # café terrace in front of the café building
    for (x, y) in Q.CAFE["tables"]:
        inst("cafe_set", (x, y, 0.0), x, P)
    for x in (45.0, 57.5):
        inst("pot_terracotta", (x, -1.0, 0.0), x, P, scale=0.7)
        veg.shrub((x, -1.0, 0.5), V, 0.9)
    # trees on the wider quay corners and plazas of the side canal
    for (x, y, k) in ((36.5, 31.5, "olive"), (23.5, 31.5, "orange"), (47.0, 21.0, "olive"), (97.5, 21.0, "orange"),
                      (68.0, 21.0, "olive"), (13.8, 44.0, "olive"), (45.5, 44.0, "orange")):
        veg.tree(k, (x, y, 0.0), V, rot=x, scale=1.0, pot="pot_terracotta", pot_scale=1.2)
    for y in (40.0, 52.0, 64.0, 76.0):
        veg.cypress((45.2, y, 0.0), V, 0.9)
    sky.fill_lights(Lt, lamps[:6])


def town_fill(C):
    from . import scenery
    scenery._block_protos()
    rng = random.Random(909)
    keys = ["town_block_a", "town_block_b", "town_block_c"]
    for (x0, y0, x1, y1) in Q.FILL_AREAS:
        rows = max(1, int((y1 - y0) / 8.5))
        for r in range(rows):
            y = y0 + (y1 - y0) * (r + 0.5) / rows
            x = x0 + 4
            while x < x1 - 3:
                if rng.random() < 0.82:
                    inst(rng.choice(keys), (x, y, 0.0), rng.choice((0, math.pi)), C,
                         scale=(rng.uniform(0.95, 1.3), 1.0, rng.uniform(0.8, 1.25)))
                x += rng.uniform(8.5, 11)


def build():
    D = coll("district")
    V = coll("vegetation")
    P = coll("props")
    Lt = coll("lights")
    F = coll("town_fill")
    ground(D)
    _bridge_at(Q.TOLL_BRIDGE["center"], Q.TOLL_BRIDGE["rot"], D)
    _bridge_at(Q.SIDE_BRIDGE["center"], Q.SIDE_BRIDGE["rot"], D)
    lights = []
    for i, b in enumerate(Q.BUILDINGS):
        _house(b, D, V, 100 + i, lights)
    for i, p in enumerate(Q.PERCHES):
        _house(dict(p, name="perch_" + p["id"]), D, V, 61 + i, lights)
    bell_tower(D, lights)
    quay_furniture(P, V, Lt)
    town_fill(F)
    sky.fill_lights(Lt, lights[:10])
