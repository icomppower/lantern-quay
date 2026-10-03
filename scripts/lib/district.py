"""Assembles the district from site, architecture, props and vegetation, per build stage."""
import math
import random
from .core import coll, inst
from . import layout as Lo
from . import site, arch, veg, sky
from . import assets as A


def _row(kind, us, z, w, h, arch_):
    return [dict(u=u, z=z, w=w, h=h, arch=arch_, kind=kind) for u in us]


def b1_plan():
    us = [1.4, 4.2, 7.0, 9.8, 12.6]
    F = arch.FLOOR_H
    g = _row("window", [1.4, 4.2, 9.8, 12.6], 0.85, 1.0, 1.75, True) + _row("door", [7.0], 0.0, 1.2, 2.55, True)
    f1 = _row("window", [1.4, 7.0, 12.6], F + 0.85, 0.95, 1.85, True) + _row("balcony", [4.2, 9.8], F + 0.05, 1.05, 2.35, True)
    f2 = _row("window", us, 2 * F + 0.9, 0.85, 1.4, False)
    return [g, f1, f2]


def b2_south():
    F = arch.FLOOR_H
    g = _row("door", [2.0], 0.0, 1.1, 2.4, True) + _row("window", [4.9], 0.85, 1.0, 1.7, True)
    f1 = _row("balcony", [3.5], F + 0.05, 1.05, 2.3, True)
    return [g, f1]


def section(C):
    """Stage 2: plaza front, grand stair, terrace, B1 + B2, the canal reach and footbridge."""
    D = coll("district")
    V = coll("vegetation")
    P = coll("props")
    Lt = coll("lights")
    site.ground(D)
    site.outer_ground(D)
    site.canal(D)
    site.terrace(D)
    site.raised_walk(D)
    site.grand_stair(D)
    site.railings(D)
    site.bridge(D)
    b1, a1 = arch.building(Lo.B1, D, seed=11, wall_mat="ashlar",
                           sides_cfg={"s": dict(openings=b1_plan()), "n": dict(ground_doors=0),
                                      "e": dict(ground_doors=1), "w": dict(ground_doors=1)},
                           awnings={("s", 4.2): "awning_blue", ("s", 9.8): "awning_red", ("s", 12.6): "awning_blue"})
    b2, a2 = arch.building(Lo.B2, D, seed=12, wall_mat="plaster", parapet="balustrade",
                           sides_cfg={"s": dict(openings=b2_south()), "w": dict(skip=True),
                                      "n": dict(ground_doors=0)},
                           awnings={("s", 4.9): "awning_ochre"})
    anchors = [a1, a2]
    # --- vegetation in the reference view
    veg.tree("orange", (10.3, 9.95, 0.0), V, rot=0.4, scale=1.05, pot="pot_terracotta", pot_scale=1.25)
    veg.tree("orange", (22.3, 10.3, 0.0), V, rot=2.1, scale=1.0, pot="pot_turquoise", pot_scale=1.15)
    veg.tree("orange", (3.4, 4.0, Lo.RAISED_Z), V, rot=1.2, scale=0.95, pot="pot_terracotta", pot_scale=1.2)
    veg.tree("olive", (11.6, 18.6, Lo.TERRACE_Z), V, rot=0.3, scale=1.0, pot="pot_terracotta", pot_scale=1.2)
    veg.tree("olive", (20.4, 18.6, Lo.TERRACE_Z), V, rot=1.9, scale=0.95, pot="pot_terracotta", pot_scale=1.2)
    veg.palm((3.0, 14.8, Lo.TERRACE_Z), V, rot=2.4)
    veg.palm((4.8, 1.6, Lo.RAISED_Z), V, rot=1.1, scale=0.85)
    for x in (13.6, 18.4):
        inst("pot_small", (x, 9.5, 0.0), 0, P, scale=1.4)
        veg.shrub((x, 9.5, 0.36), V, 0.9)
    inst("bench", (9.4, 12.3, 0.0), 0, P)
    inst("pot_terracotta", (12.4, 12.4, 0.0), 0.3, P, scale=0.7)
    veg.shrub((12.4, 12.4, 0.5), V, 1.0)
    # bougainvillea on B1, ivy over the terrace wall
    veg.wall_clump("bougainvillea", (9.0 + 5.6, 20.0, Lo.TERRACE_Z + 5.9), 0, V, 1.2)
    veg.wall_clump("bougainvillea", (9.0 + 0.4, 20.0, Lo.TERRACE_Z + 3.0), 0, V, 1.0)
    veg.wall_clump("bougainvillea", (7.0, 22.5, Lo.TERRACE_Z + 2.6), -math.pi / 2, V, 0.9)
    for x in (2.0, 8.5, 11.8, 19.5, 22.0):
        inst("ivy_hang", (x, 12.96, Lo.TERRACE_Z - 0.1), 0, V, scale=1.3)
    for (loc, rot, bw) in a1["balconies"] + a2["balconies"]:
        ox, oy = math.sin(rot), -math.cos(rot)
        for k in (-0.3, 0.35):
            inst("ivy_hang", (loc[0] + ox * 0.5 + math.cos(rot) * k * bw, loc[1] + oy * 0.5 + math.sin(rot) * k * bw,
                              loc[2] - 0.2), rot, V)
    for (loc, rot) in a1["window_boxes"] + a2["window_boxes"]:
        veg.shrub((loc[0], loc[1], loc[2] - 0.05), V, 0.55)
        inst("ivy_hang", (loc[0], loc[1] - 0.05, loc[2] - 0.15), rot, V, scale=0.8)
    # canal life
    inst("boat_a", (29.1, 15.5, Lo.WATER_Z - 0.12), math.pi / 2 + 0.05, P)
    inst("boat_b", (31.0, 26.6, Lo.WATER_Z - 0.12), -math.pi / 2 + 0.04, P)
    for y in (13.5, 17.5, 25.0):
        inst("mooring_post", (27.75, y, -0.02), 0, P)
    for y in (24.5, 28.0):
        inst("mooring_post", (32.25, y, -0.02), 0, P)
    for y in (20.0, 24.5, 28.0):  # on the terrace edge, clear of the 2.5 m quay path
        veg.cypress((24.15, y + 1.0, Lo.TERRACE_Z), V, 0.85)
    lanterns = [(x, y, z + 1.65) for x in (Lo.STAIR_X0 - 0.2, Lo.STAIR_X1 + 0.2)
                for (y, z) in ((9.3, 0.0), (13.15, Lo.TERRACE_Z))]
    lanterns += [(Lo.CANAL_X0 - 0.3, yy, 1.5) for yy in (20.87, 23.13)]
    lanterns += [(Lo.CANAL_X1 + 0.3, yy, 1.5) for yy in (20.87, 23.13)]
    sky.fill_lights(Lt, lanterns)
    return anchors


def expand():
    """Stage 3: east bank houses, roof gardens, cafe, boats, props, foreground trees."""
    D = coll("district")
    V = coll("vegetation")
    P = coll("props")
    Lt = coll("lights")
    A.parasol(); A.pergola()
    b3, a3 = arch.building(Lo.B3, D, seed=13, wall_mat="plaster_ochre",
                           sides_cfg={"e": dict(skip=True), "w": dict(door_at=[2.6, 7.9]),
                                      "n": dict(ground_doors=1), "s": dict(ground_doors=0)},
                           awnings={("w", 5.2): "awning_red", ("w", 2.6): "awning_blue"})
    b4, a4 = arch.building(Lo.B4, D, seed=14, wall_mat="plaster_rose",
                           sides_cfg={"e": dict(skip=True), "n": dict(skip=True),
                                      "w": dict(ground_doors=1), "s": dict(ground_doors=1)},
                           awnings={("s", 1.4): "awning_ochre"})
    x0, y0, x1, y1 = Lo.B4["rect"]
    top4 = Lo.B4["z"] + Lo.B4["floors"] * arch.FLOOR_H
    arch.dome(((x0 + x1) / 2, (y0 + y1) / 2), top4, 1.55, D, name="B4_dome")
    # --- roof gardens
    top1 = Lo.B1["z"] + Lo.B1["floors"] * arch.FLOOR_H
    inst("pergola", (13.0, 24.0, top1), 0, D)
    veg.wall_clump("ivy_mass", (13.0, 24.0, top1 + 2.55), 0, V, 1.3)
    veg.wall_clump("bougainvillea", (14.2, 22.8, top1 + 2.5), math.pi, V, 1.0)
    for x in (17.5, 19.5, 21.5):
        inst("planter_long", (x, 21.0, top1), 0, D, scale=(0.9, 1, 1))
        veg.tree("orchard", (x, 21.0, top1 + 0.36), V, rot=x, scale=0.9)
    top3 = Lo.B3["z"] + Lo.B3["floors"] * arch.FLOOR_H
    for i, y in enumerate((11.4, 13.6, 15.8, 18.0)):
        for x in (35.6, 38.6):
            inst("planter_box", (x, y, top3), 0, D, scale=(1.1, 1.6, 1))
            veg.tree("orchard", (x, y, top3 + 0.36), V, rot=i + x, scale=1.0 + 0.1 * ((i + int(x)) % 2))
    inst("pergola", (37.2, 19.6, top3), math.pi / 2, D, scale=(0.8, 0.9, 0.95))
    veg.wall_clump("bougainvillea", (37.2, 19.6, top3 + 2.4), 0, V, 0.9)
    # --- climbing plants on the east bank
    veg.wall_clump("bougainvillea", (34.5, 14.0, 3.2), -math.pi / 2, V, 1.2)
    veg.wall_clump("bougainvillea", (36.0, 23.5, 2.9), 0, V, 1.0)
    veg.wall_clump("ivy_mass", (34.5, 18.6, 1.4), -math.pi / 2, V, 1.1)
    veg.wall_clump("ivy_mass", (40.0 - 0.6, 10.0, 4.0), 0, V, 1.0)
    for (loc, rot, bw) in a3["balconies"] + a4["balconies"]:
        ox, oy = math.sin(rot), -math.cos(rot)
        inst("ivy_hang", (loc[0] + ox * 0.5, loc[1] + oy * 0.5, loc[2] - 0.2), rot, V)
    for (loc, rot) in a3["window_boxes"] + a4["window_boxes"]:
        veg.shrub((loc[0], loc[1], loc[2] - 0.05), V, 0.55)
        inst("ivy_hang", (loc[0], loc[1], loc[2] - 0.15), rot, V, scale=0.8)
    # --- plaza: cafe under parasols, planters along the terrace wall, foreground trees
    for (x, y) in ((7.9, 1.7), (10.6, 2.4)):
        inst("cafe_set", (x, y, 0.0), x, P)
        inst("parasol", (x, y, 0.0), 0.3 * x, P)
    for x in (8.0, 20.0, 24.0):
        inst("planter_box", (x, 12.45, 0.0), 0, P, scale=(1.6, 1, 1))
        for dx in (-0.4, 0.4):
            veg.shrub((x + dx, 12.45, 0.36), V, 0.8)
    veg.tree("orange", (7.0, 0.6, 0.0), V, rot=2.8, scale=1.1, pot="pot_terracotta", pot_scale=1.3)
    veg.tree("orange", (25.4, 0.7, 0.0), V, rot=0.9, scale=1.05, pot="pot_turquoise", pot_scale=1.2)
    veg.tree("olive", (3.3, 9.6, Lo.RAISED_Z), V, rot=1.7, scale=1.0, pot="pot_terracotta", pot_scale=1.1)
    # canal-corner trees: their shadows dapple the plaza foreground (low NE sun)
    veg.tree("orange", (26.0, 5.5, 0.0), V, rot=0.4, scale=1.1, pot="pot_terracotta", pot_scale=1.25)
    inst("bench", (3.6, 6.8, Lo.RAISED_Z), math.pi / 2, P)
    for (x, y, k) in ((5.0, 12.4, "pot_small"), (5.6, 12.5, "pot_small"), (23.4, 12.0, "pot_small")):
        inst(k, (x, y, Lo.RAISED_Z if x < 6 else 0.0), x, P, scale=1.2)
        veg.shrub((x, y, (Lo.RAISED_Z if x < 6 else 0.0) + 0.3), V, 0.6)
    # --- south quay + east reach: boats, mooring, cargo
    inst("boat_a", (37.0, 6.0, Lo.WATER_Z - 0.12), 0.06, P)
    inst("boat_b", (31.4, 4.7, Lo.WATER_Z - 0.12), 0.5, P)
    for x in (30.0, 34.0, 38.0):
        inst("mooring_post", (x, 3.25, -0.02), 0, P)
    for (x, y, k, r) in ((35.2, 0.5, "crate", 0.1), (35.9, 0.5, "crate", 0.5), (35.5, 0.55, "crate", 0.2),
                         (36.8, 0.55, "barrel", 0), (37.4, 0.6, "barrel", 0), (29.5, 0.5, "barrel", 0)):
        inst(k, (x, y, 0.55 if (k == "crate" and x == 35.5) else 0.0), r, P)
    inst("bench", (32.0, 0.45, 0.0), 0, P)
    # --- east quay: planters against B3/B4 and a bench
    for y in (11.5, 16.8, 25.5):
        inst("pot_terracotta", (34.15, y, 0.0), y, P, scale=0.7)
        veg.shrub((34.15, y, 0.5), V, 0.9)
    # lights in the bridge-side wall lamps and doors of the east bank
    lights = []
    for loc, rot in a3["doors"] + a4["doors"]:
        ox, oy = math.sin(rot), -math.cos(rot)
        lights.append((loc[0] + ox * 0.5, loc[1] + oy * 0.5, loc[2] + 2.0))
    sky.fill_lights(Lt, lights)


def finish():
    """Stage 4: airship on its looping route, distant scenery."""
    from . import airship, scenery
    airship.build()
    scenery.build()


def hero_frame(cam, target=(0.70, 0.80)):
    """Frame where the airship sits in the open sky over the canal gap in the hero camera."""
    import bpy
    from bpy_extras.object_utils import world_to_camera_view
    from . import airship
    sc = bpy.context.scene
    best, bf = 9, 1
    for f in range(1, airship.FRAMES, 4):
        p, _ = airship.route((f - 1) / airship.FRAMES)
        v = world_to_camera_view(sc, cam, p)
        if v.z <= 0:
            continue
        d = (v.x - target[0]) ** 2 + (v.y - target[1]) ** 2
        if d < best:
            best, bf = d, f
    return bf
