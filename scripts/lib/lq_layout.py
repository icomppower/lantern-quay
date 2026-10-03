"""Lantern Quay v1 sample: layout of the grown district (Blender Z-up metres, origin = Canal District SW corner).

The original 40 x 30 m Canal District sits unchanged at (0..40, 0..30). Its two canal reaches are extended:
the east reach (y 3.5..8.5) becomes the long main canal running east to x 142, the north reach
(x 27.5..32.5) becomes the side canal running north to y 86. World bounds about 150 x 100 m.
Everything gameplay needs (perches, ladders, tower, targets, zones) is exported to public/world/world.json.
"""
X0, X1 = -8.0, 142.0
Y0, Y1 = -14.0, 86.0
FLOOR_H = 3.2

# --------------------------------------------------------------- full buildings (arch.building)
# (name, rect x0,y0,x1,y1, floors, quay side, wall material)
SOUTH_FRONT = -1.5      # south row faces the main canal / plaza (side "n")
NORTH_FRONT = 11.0      # north row faces the main canal (side "s")

_walls = ["plaster_ochre", "ashlar", "plaster_rose", "plaster", "plaster_ochre", "ashlar", "plaster_rose"]


def _row(spans, y0, y1, face, floors_cycle, tag):
    out = []
    for i, (a, b) in enumerate(spans):
        out.append(dict(name=f"{tag}{i:02d}", rect=(a, y0, b, y1), floors=floors_cycle[i % len(floors_cycle)],
                        face=face, wall=_walls[(i * 3 + len(tag)) % len(_walls)]))
    return out


SOUTH_SPANS = [(-6, 4), (4, 12), (15, 24), (24, 33), (36, 45), (46, 56), (56, 64), (67, 76), (76, 85), (85, 94),
               (97, 106), (106, 115), (128, 138)]
NORTH_SPANS = [(48, 57), (57, 66), (69, 78), (78, 87), (87, 96), (99, 108), (108, 115), (130, 140)]
BUILDINGS = (
    _row(SOUTH_SPANS, -10.0, SOUTH_FRONT, "n", [3, 2, 4, 3, 2, 3, 4], "S")
    + _row(NORTH_SPANS, NORTH_FRONT, 19.0, "s", [3, 4, 2, 3, 3, 4, 2], "N")
    + _row([(33, 42), (42, 50), (53, 62), (62, 71), (74, 83)], None, None, "e", [3, 4, 3, 2, 4], "W")
    + _row([(33, 42), (45, 54), (57, 66), (66, 75)], None, None, "w", [4, 3, 3, 4], "E")
)
for b in BUILDINGS:  # side-canal rows run north-south: rect given as y spans
    if b["name"].startswith("W"):
        a, _, c, _ = b["rect"]; b["rect"] = (15.5, a, 25.0, c)
    elif b["name"].startswith("E"):
        a, _, c, _ = b["rect"]; b["rect"] = (35.0, a, 44.0, c)

# café: the south-row building at x 46..56 has the café terrace on the quay in front of it
CAFE_BUILDING = "S05"
DOMES = {"S02": 1.4, "N03": 1.5, "E01": 1.3, "W03": 1.2}
ROOF_GARDENS = ["S04", "N01", "N05", "W01", "E02", "S09"]

# --------------------------------------------------------------- perches (sniper roofs) + bell tower
PERCH_A = dict(id="A", name="東樓頂 East Loft", rect=(118.0, 10.5, 128.0, 18.5), floors=5, face="s", wall="ashlar",
               spot=(118.65, 11.1), facing=180.0, ladder=dict(base=(117.55, 15.5), side="w"))
PERCH_B = dict(id="B", name="南倉頂 South Warehouse", rect=(118.0, -10.0, 128.0, -0.8), floors=5, face="n",
               wall="plaster_ochre", spot=(118.65, -1.4), facing=180.0, ladder=dict(base=(117.55, -5.0), side="w"))
PERCHES = [PERCH_A, PERCH_B]
TOWER = dict(name="鐘樓 Bell Tower", rect=(41.5, 10.5, 46.5, 15.5), floors=5, belfry_h=3.4, dome_r=2.0,
             ladder=dict(base=(46.95, 13.0), side="e"), spot=(44.0, 11.2), dive_to=(44.0, 6.0))

# --------------------------------------------------------------- bridges
TOLL_BRIDGE = dict(center=(60.0, 6.0), rot=90.0)   # spans the main canal north-south
SIDE_BRIDGE = dict(center=(30.0, 56.0), rot=0.0)   # spans the side canal east-west

# --------------------------------------------------------------- crowd zones (convex rects, z = ground)
ZONES = {
    "plaza": (7.5, 1.0, 26.0, 11.0),
    "south_quay_w": (28.0, -0.6, 45.0, 2.9),
    "south_quay_cafe": (44.0, -0.6, 70.0, 2.9),
    "south_quay_e": (70.0, -0.6, 115.0, 2.9),
    "north_quay": (47.5, 9.1, 116.0, 10.7),
}
SPAWN = (16.0, 3.0)
CAFE = dict(tables=[(50.4, 1.0), (48.6, 0.2), (51.4, -0.5)], counter=(47.6, -0.9),
            awning=dict(x=53.2, y0=-1.3, y1=3.0, top=3.0, bottom=0.65))

# --------------------------------------------------------------- town fill (instanced scenery blocks)
FILL_AREAS = [
    (48.0, 23.5, 140.0, 31.0),   # behind the north row, south of the lane at y 22
    (46.0, 34.0, 140.0, 84.0),   # north-east quarter
    (-6.0, 33.0, 13.0, 84.0),    # north-west quarter behind the west row
    (-6.0, -17.5, 140.0, -10.8), # back of the south row
]

# --------------------------------------------------------------- rooftop watchmen (patrol between two roof points)
def _roof(name):
    for b in BUILDINGS:
        if b["name"] == name:
            return b["floors"] * FLOOR_H
    raise KeyError(name)


GUARDS = [
    dict(id="G1", roof="N05", a=(100.5, 12.3), b=(106.5, 17.6)),
    dict(id="G2", roof="S09", a=(86.2, -2.8), b=(92.8, -8.6)),
    dict(id="G3", roof="S12", a=(129.4, -2.6), b=(136.5, -8.6)),
]
for g in GUARDS:
    g["z"] = _roof(g["roof"])
