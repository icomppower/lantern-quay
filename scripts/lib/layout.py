"""Single source of truth for the district layout (metres, Blender Z-up, origin SW corner)."""
import math

W, D = 40.0, 30.0
PLAZA_Z = 0.0
TERRACE_Z = 1.80
RAISED_Z = 0.30
WATER_Z = -0.90
BED_Z = -1.80

# canal: N-S reach x 27.5..32.5 from y=30 to y=11, quarter bend centred (35,11), E-W reach y 3.5..8.5
CANAL_W = 5.0
CANAL_X0, CANAL_X1 = 27.5, 32.5
BEND_C = (35.0, 11.0)
BEND_RI, BEND_RO = 2.5, 7.5
CANAL_Y0, CANAL_Y1 = 3.5, 8.5  # east reach


def canal_west_edge(n=16):
    """Outer (west/south) bank edge, from north end to east end."""
    pts = [(CANAL_X0, D)]
    for i in range(n + 1):
        a = math.pi + (math.pi / 2) * i / n  # 180 -> 270 deg
        pts.append((BEND_C[0] + BEND_RO * math.cos(a), BEND_C[1] + BEND_RO * math.sin(a)))
    pts.append((W, CANAL_Y0))
    return pts


def canal_east_edge(n=10):
    """Inner (east/north) bank edge, from north end to east end."""
    pts = [(CANAL_X1, D)]
    for i in range(n + 1):
        a = math.pi + (math.pi / 2) * i / n
        pts.append((BEND_C[0] + BEND_RI * math.cos(a), BEND_C[1] + BEND_RI * math.sin(a)))
    pts.append((W, CANAL_Y1))
    return pts


def canal_centerline(n=12):
    pts = [(30.0, D)]
    for i in range(n + 1):
        a = math.pi + (math.pi / 2) * i / n
        pts.append((BEND_C[0] + 5.0 * math.cos(a), BEND_C[1] + 5.0 * math.sin(a)))
    pts.append((W, 6.0))
    return pts


# terrace (z 1.8): main block with rounded SE corner near the canal
TERRACE_Y0 = 13.0
TERRACE_X1 = 25.0
STAIR_X0, STAIR_X1 = 14.75, 17.25
STAIR_Y0 = 9.6  # bottom step front edge
STAIR_RISERS = 10
STAIR_TREAD = 0.34
RAISED = (0.0, 0.0, 6.0, 12.6)  # raised walk x0,y0,x1,y1

# buildings (footprint x0,y0,x1,y1, base z, floors)
B1 = dict(name="B1_terrace_house", rect=(9.0, 20.0, 23.0, 28.0), z=TERRACE_Z, floors=3)
B2 = dict(name="B2_west_house", rect=(0.0, 17.0, 7.0, 28.0), z=TERRACE_Z, floors=2)
B3 = dict(name="B3_orchard_house", rect=(34.5, 10.0, 40.0, 20.5), z=PLAZA_Z, floors=2)
B4 = dict(name="B4_dome_house", rect=(34.5, 23.5, 40.0, 30.0), z=PLAZA_Z, floors=3)
FLOOR_H = 3.2

BRIDGE_Y = 22.0
BRIDGE_W = 2.0  # walkable width between parapets
BRIDGE_RISE = 0.9

# walk-test polylines (x, y) — the walker follows these at eye height 1.7 m
PATHS = {
    "raised_walk_to_south_quay": [(1.5, 1.0), (1.5, 11.5), (4.5, 11.5), (7.5, 6.0), (16.0, 4.5),
                                  (24.0, 4.0), (28.0, 2.0), (39.5, 1.6)],
    "plaza_stair_terrace": [(16.0, 4.0), (16.0, 9.2), (16.0, 13.4), (16.0, 16.5), (16.0, 19.55)],
    "terrace_west": [(16.0, 16.5), (8.0, 16.0), (8.0, 29.3)],
    "terrace_east": [(16.0, 16.5), (23.6, 16.5), (24.0, 19.0)],
    "west_quay": [(24.0, 9.5), (26.2, 12.0), (26.2, 29.5)],
    "bridge_and_east_quay": [(26.2, 22.0), (33.6, 22.0), (33.6, 29.5)],
    "east_quay_south": [(33.6, 22.0), (33.6, 9.5)],
    "east_lane": [(33.6, 22.0), (39.6, 22.0)],
}

CAMERAS = {
    "CAM_REF": dict(loc=(16.2, 1.0, 1.7), target=(16.6, 20.0, -0.3), lens=18),
    "CAM_HERO": dict(loc=(15.2, -0.8, 1.75), target=(19.2, 20.0, 5.6), lens=18),
    "CAM_BRIDGE": dict(loc=(25.0, 8.6, 1.7), target=(30.5, 22.0, 2.6), lens=22),
    "CAM_EAST": dict(loc=(23.6, 15.5, 3.5), target=(37.0, 19.0, 4.5), lens=20),
    "CAM_TOP": dict(loc=(20.0, -16.0, 30.0), target=(21.0, 14.0, 0.0), lens=30),
}
