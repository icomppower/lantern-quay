"""Ground, canal, quays, terrace + retaining walls, grand stair, raised walk, humpback bridge."""
import math
from mathutils import Vector
from .core import MB, inst, arc_pts
from . import layout as Lo
from .arch import Side, band

EXT = 130.0  # how far the canal and outer ground run out past the district


def extrude_xz(m, profile, y0, y1, mat, cap_mat=None, caps=True):
    """Extrude a CCW (x,z) profile along +y from y0 to y1."""
    n = len(profile)
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(profile, profile[1:] + profile[:1]))
    if area < 0:
        profile = profile[::-1]
    for i in range(n):
        (ax, az), (bx, bz) = profile[i], profile[(i + 1) % n]
        nrm = (bz - az, 0, -(bx - ax))
        m.face([(ax, y0, az), (bx, y0, bz), (bx, y1, bz), (ax, y1, az)], mat, orient=nrm)
    if caps:
        m.face([(x, y0, z) for x, z in profile], cap_mat or mat, orient=(0, -1, 0))
        m.face([(x, y1, z) for x, z in profile], cap_mat or mat, orient=(0, 1, 0))


def extrude_yz(m, profile, x0, x1, mat, cap_mat=None):
    n = len(profile)
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(profile, profile[1:] + profile[:1]))
    if area < 0:
        profile = profile[::-1]
    for i in range(n):
        (ay, az), (by, bz) = profile[i], profile[(i + 1) % n]
        nrm = (0, bz - az, -(by - ay))
        m.face([(x0, ay, az), (x0, by, bz), (x1, by, bz), (x1, ay, az)], mat, orient=nrm)
    m.face([(x0, y, z) for y, z in profile], cap_mat or mat, orient=(-1, 0, 0))
    m.face([(x1, y, z) for y, z in profile], cap_mat or mat, orient=(1, 0, 0))


def _ext_west():
    pts = Lo.canal_west_edge()
    return [(Lo.CANAL_X0, Lo.D + EXT)] + pts + [(Lo.W + EXT, Lo.CANAL_Y0)]


def _ext_east():
    pts = Lo.canal_east_edge()
    return [(Lo.CANAL_X1, Lo.D + EXT)] + pts + [(Lo.W + EXT, Lo.CANAL_Y1)]


def ground(coll_):
    m = MB()
    west = Lo.canal_west_edge()
    poly = [(0, 0), (Lo.W, 0)] + list(reversed(west))[0:] + [(0, Lo.D)]
    # reversed west edge runs (40,3.5) -> arc -> (27.5,30)
    m.face([(x, y, 0.0) for x, y in poly], "flagstone", orient=(0, 0, 1))
    east = Lo.canal_east_edge()
    poly2 = list(east) + [(Lo.W, Lo.D)]
    m.face([(x, y, 0.0) for x, y in poly2], "flagstone", orient=(0, 0, 1))
    ob = m.to_object("ground_district", coll_)
    return ob


def outer_ground(coll_):
    """Plain fields around the district (z -0.02), with a corridor left open for the canal."""
    m = MB()
    E = EXT
    rects = [
        [(-E, 30), (27.5, 30), (27.5, 30 + E), (-E, 30 + E)],
        [(32.5, 30), (40 + E, 30), (40 + E, 30 + E), (32.5, 30 + E)],
        [(40, 8.5), (40 + E, 8.5), (40 + E, 30), (40, 30)],
        [(40, -E), (40 + E, -E), (40 + E, 3.5), (40, 3.5)],
        [(-E, -E), (40, -E), (40, 0), (-E, 0)],
        [(-E, 0), (0, 0), (0, 30), (-E, 30)],
    ]
    for r in rects:
        m.face([(x, y, -0.02) for x, y in r], "hill", orient=(0, 0, 1))
    return m.to_object("ground_outer", coll_)


def canal(coll_, extended=True):
    west = _ext_west() if extended else Lo.canal_west_edge()
    east = _ext_east() if extended else Lo.canal_east_edge()
    m = MB()
    # walls: from coping down to bed, facing the water
    for pts, side in ((west, 1), (east, -1)):
        for (ax, ay), (bx, by) in zip(pts[:-1], pts[1:]):
            d = Vector((bx - ax, by - ay, 0))
            left = Vector((-d.y, d.x, 0)) * side
            # dry ashlar above the water line, darker wet stone below
            m.face([(ax, ay, 0.0), (bx, by, 0.0), (bx, by, Lo.WATER_Z + 0.25), (ax, ay, Lo.WATER_Z + 0.25)],
                   "ashlar", orient=left)
            m.face([(ax, ay, Lo.WATER_Z + 0.25), (bx, by, Lo.WATER_Z + 0.25), (bx, by, Lo.BED_Z), (ax, ay, Lo.BED_Z)],
                   "canal_bed", orient=left)
            # coping: 0.42 wide, 0.07 proud, overhangs water 0.06
            out = left.normalized() * 0.06
            inn = -left.normalized() * 0.36
            a0, b0 = Vector((ax, ay, 0)), Vector((bx, by, 0))
            q = [a0 + out, b0 + out, b0 + inn, a0 + inn]
            m.face([(p.x, p.y, 0.07) for p in q], "stone_trim", orient=(0, 0, 1))
            m.face([(q[0].x, q[0].y, -0.05), (q[1].x, q[1].y, -0.05), (q[1].x, q[1].y, 0.07), (q[0].x, q[0].y, 0.07)],
                   "stone_trim", orient=left)
            m.face([(q[3].x, q[3].y, 0.0), (q[2].x, q[2].y, 0.0), (q[2].x, q[2].y, 0.07), (q[3].x, q[3].y, 0.07)],
                   "stone_trim", orient=-left)
    bed = west + list(reversed(east))
    m.face([(x, y, Lo.BED_Z) for x, y in bed], "canal_bed", orient=(0, 0, 1))
    walls = m.to_object("canal_walls", coll_, bevel=0.0)
    w = MB()
    w.face([(x, y, Lo.WATER_Z) for x, y in bed], "water", orient=(0, 0, 1))
    water = w.to_object("water", coll_)
    return walls, water


def terrace(coll_):
    """Upper terrace (z 1.8) with rounded SE corner, retaining walls, tile band, coping."""
    T = Lo.TERRACE_Z
    arc = arc_pts(23.0, 15.0, 2.0, -math.pi / 2, 0.0, 8)
    poly = [(0.0, 13.0)] + arc + [(25.0, 30.0), (0.0, 30.0)]
    m = MB()
    m.prism(poly, 0.0, T, "flagstone", "ashlar")
    # tile band + coping along the exposed edges (front, arc, east, north)
    edges = list(zip(poly, poly[1:] + poly[:1]))
    for (ax, ay), (bx, by) in edges:
        if ax == 0.0 and bx == 0.0:
            continue
        L = math.hypot(bx - ax, by - ay)
        sd = Side(ax, ay, math.atan2(by - ay, bx - ax) + math.pi, L)
        # Side expects inside on its left; edges run CCW so inside is left of (a->b).
        sd = Side(ax, ay, math.atan2(by - ay, bx - ax), L)
        band(m, sd, 0.0, T - 0.5, T - 0.2, 0.015, "tile")
        band(m, sd, 0.0, T - 0.2, T + 0.08, 0.10, "stone_trim")
        band(m, sd, 0.0, 0.0, 0.35, 0.05, "ashlar_dark")
    ob = m.to_object("terrace", coll_, bevel=0.02)
    return ob, poly


def raised_walk(coll_):
    x0, y0, x1, y1 = Lo.RAISED
    m = MB()
    m.prism([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], 0.0, Lo.RAISED_Z, "flagstone", "stone_trim")
    # intermediate step along part of the east edge
    m.prism([(x1, 3.0), (x1 + 0.38, 3.0), (x1 + 0.38, 9.0), (x1, 9.0)], 0.0, 0.15, "stone_trim", "stone_trim")
    return m.to_object("raised_walk", coll_, bevel=0.03)


def grand_stair(coll_):
    m = MB()
    x0, x1 = Lo.STAIR_X0, Lo.STAIR_X1
    rise = Lo.TERRACE_Z / Lo.STAIR_RISERS
    for i in range(Lo.STAIR_RISERS):
        yf = Lo.STAIR_Y0 + i * Lo.STAIR_TREAD
        m2 = MB()
        m.box((x0, yf, i * rise), (x1, 13.05, (i + 1) * rise), "stone_trim",
              skip=("-z",) if i == 0 else ("-z",))
    # cheek walls with sloped tops
    top_y = Lo.STAIR_Y0 + Lo.STAIR_RISERS * Lo.STAIR_TREAD
    prof = [(9.0, 0.0), (13.0, 0.0), (13.0, 2.25), (12.6, 2.25), (9.9, 0.8), (9.0, 0.8)]
    for cx0, cx1 in ((x0 - 0.4, x0), (x1, x1 + 0.4)):
        extrude_yz(m, prof, cx0, cx1, "ashlar")
        # coping on the cheek
        cp = [(9.0, 0.8), (9.9, 0.8), (12.6, 2.25), (13.0, 2.25), (13.0, 2.33), (12.6, 2.33), (9.9, 0.88), (9.0, 0.88)]
        extrude_yz(m, cp, cx0 - 0.05, cx1 + 0.05, "stone_trim")
    ob = m.to_object("grand_stair", coll_, bevel=0.02)
    # pillars + lanterns: bottom pair and top pair
    for x in (x0 - 0.2, x1 + 0.2):
        inst("pillar", (x, 9.3, 0.0), 0, coll_)
        inst("lantern", (x, 9.3, 1.38), 0, coll_)
        inst("pillar", (x, 13.15, Lo.TERRACE_Z), 0, coll_)
        inst("lantern", (x, 13.15, Lo.TERRACE_Z + 1.38), 0, coll_)
    return ob


def bridge(coll_):
    """Humpback stone footbridge at y=22: stepped deck, segmental arch on buttress piers,
    solid parapets with coping, end pillars with lanterns."""
    y = Lo.BRIDGE_Y
    hw = Lo.BRIDGE_W / 2
    ya, yb = y - hw - 0.25, y + hw + 0.25
    xa, xb = Lo.CANAL_X0, Lo.CANAL_X1
    span = xb - xa
    rise = 0.15
    n_steps = 6
    tread = 0.36
    top = []
    x = xa
    z = 0.0
    top.append((xa - 0.6, 0.0))
    for k in range(n_steps):
        top.append((xa + k * tread, z))
        z = (k + 1) * rise
        top.append((xa + k * tread, z))
    mid0 = xa + n_steps * tread
    mid1 = xb - n_steps * tread
    top.append((mid0, z))
    top.append((mid1, z))
    for k in range(n_steps):
        top.append((mid1 + k * tread, z))
        z = (n_steps - k - 1) * rise
        top.append((mid1 + k * tread, z))
    top.append((xb + 0.6, 0.0))
    # clean duplicates
    clean = []
    for p in top:
        if not clean or (abs(clean[-1][0] - p[0]) > 1e-6 or abs(clean[-1][1] - p[1]) > 1e-6):
            clean.append(p)
    top = clean
    pier = 0.35
    s0, s1 = xa + pier, xb - pier
    spring_z = -0.55
    crown_z = 0.38
    soffit = []
    nseg = 14
    for k in range(nseg + 1):
        t = k / nseg
        xx = s1 - (s1 - s0) * t
        soffit.append((xx, spring_z + (crown_z - spring_z) * math.sin(math.pi * t)))
    prof = top + [(xb + 0.6, -0.25), (xb, -0.25), (xb, spring_z), (s1, spring_z)] + soffit[1:-1] + \
        [(s0, spring_z), (xa, spring_z), (xa, -0.25), (xa - 0.6, -0.25)]
    m = MB()
    extrude_xz(m, prof, ya, yb, "ashlar", cap_mat="ashlar")
    # piers down to the bed
    for px0, px1 in ((xa, s0), (s1, xb)):
        m.box((px0, ya - 0.1, -1.8), (px1, yb + 0.1, spring_z), "ashlar_dark")
        m.box((px0 - 0.0, ya - 0.18, spring_z - 0.12), (px1 + 0.0, yb + 0.18, spring_z), "stone_trim")
    # voussoir ring: stone trim band around the arch on both faces
    for yy, sgn in ((ya, -1), (yb, 1)):
        for (ax, az), (bx, bz) in zip(soffit[:-1], soffit[1:]):
            q = [(ax, yy + sgn * 0.03, az), (bx, yy + sgn * 0.03, bz), (bx, yy + sgn * 0.03, bz + 0.28),
                 (ax, yy + sgn * 0.03, az + 0.28)]
            m.face(q, "stone_trim", orient=(0, sgn, 0))
    # parapets following a smooth curve over the steps
    def deck(xx):
        if xx <= xa or xx >= xb:
            return 0.0
        t = (xx - xa) / span
        return min(n_steps * rise, n_steps * rise * math.sin(math.pi * t) * 1.18)
    for p0, p1 in ((ya, ya + 0.25), (yb - 0.25, yb)):
        pts = []
        N = 24
        xs = [xa - 0.6 + (span + 1.2) * k / N for k in range(N + 1)]
        upper = [(xx, deck(xx) + 0.95) for xx in xs]
        lower = [(xx, deck(xx) - 0.05 if xa < xx < xb else -0.02) for xx in reversed(xs)]
        prof2 = upper + lower
        extrude_xz(m, prof2, p0, p1, "ashlar")
        cop = [(xx, deck(xx) + 0.95) for xx in xs] + [(xx, deck(xx) + 1.03) for xx in reversed(xs)]
        extrude_xz(m, cop, p0 - 0.05, p1 + 0.05, "stone_trim")
        # tile inlay strip on the outer face
        sgn = -1 if p0 == ya else 1
        yy = (p0 if sgn < 0 else p1) + sgn * 0.004
        for (ax, az), (bx, bz) in zip(upper[:-1], upper[1:]):
            m.face([(ax, yy, az - 0.32), (bx, yy, bz - 0.32), (bx, yy, bz - 0.14), (ax, yy, az - 0.14)], "tile",
                   orient=(0, sgn, 0))
    ob = m.to_object("bridge", coll_, bevel=0.02)
    for x in (xa - 0.3, xb + 0.3):
        for yy in (ya + 0.12, yb - 0.12):
            inst("pillar", (x, yy, 0.0), 0, coll_, scale=(0.85, 0.85, 0.85))
            inst("lantern", (x, yy, 1.38 * 0.85), 0, coll_, scale=0.8)
    return ob


def railings(coll_):
    """Iron railing along terrace edge (with stair gap), balustrade in front of B2."""
    T = Lo.TERRACE_Z
    runs_iron = [
        [(7.2, 13.18), (Lo.STAIR_X0 - 0.5, 13.18)],
        [(Lo.STAIR_X1 + 0.5, 13.18), (23.0, 13.18)] ,
        arc_pts(23.0, 15.0, 1.82, -math.pi / 2, 0.0, 4),
        [(24.82, 15.0), (24.82, 29.82), (0.2, 29.82)],
    ]
    from .core import along
    for run in runs_iron:
        for (p, ang, seg) in along(run, 1.0):
            inst("railing_iron", (p[0], p[1], T), ang, coll_, scale=(seg, 1, 1))
    for (p, ang, seg) in along([(0.3, 13.2), (7.0, 13.2)], 1.2):
        inst("balustrade", (p[0], p[1], T + 0.08), ang, coll_, scale=(seg / 1.2, 1, 1))
