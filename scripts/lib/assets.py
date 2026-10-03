"""Prototype meshes. Every repeated element is built once here and instanced via core.inst()."""
import math
from .core import MB, register_proto, proto_coll, PROTOS


def _done(key, mb, bevel=0.0, segs=2):
    if key in PROTOS:
        return PROTOS[key]
    ob = mb.to_object(key, proto_coll(), bevel=bevel, bevel_segs=segs)
    return register_proto(key, ob)


# ------------------------------------------------------------- railings
def railing_iron():
    """1 m wrought-iron railing segment centred on x=0, along +X, height 1.0 m."""
    if "railing_iron" in PROTOS:
        return
    m = MB()
    t = 0.022
    m.box((-0.5, -0.02, 0.06), (0.5, 0.02, 0.10), "iron")       # bottom rail
    m.box((-0.5, -0.03, 0.94), (0.5, 0.03, 1.00), "iron")       # top rail
    m.box((-0.5, -0.015, 0.80), (0.5, 0.015, 0.83), "iron")     # upper band
    m.box((-0.52, -0.03, 0.0), (-0.47, 0.03, 1.04), "iron")     # post
    for i in range(10):
        x = -0.45 + i * 0.1
        m.box((x - t / 2, -t / 2, 0.08), (x + t / 2, t / 2, 0.96), "iron")
    for i in range(5):  # scroll rings between bands
        x = -0.4 + i * 0.2
        m.lathe([(0.04, 0.0), (0.045, 0.005)], 8, "iron", cap_top=False, center=(x, 0, 0.86))
    _done("railing_iron", m)


def balustrade():
    """1.2 m stone balustrade segment centred on x=0, height 0.95 m."""
    if "balustrade" in PROTOS:
        return
    m = MB()
    m.box((-0.6, -0.16, 0.0), (0.6, 0.16, 0.16), "stone_trim")
    m.box((-0.6, -0.14, 0.82), (0.6, 0.14, 0.95), "stone_trim")
    m.box((-0.6, -0.16, 0.0), (-0.48, 0.16, 0.95), "stone_trim")
    prof = [(0.05, 0.16), (0.07, 0.20), (0.05, 0.26), (0.085, 0.42), (0.10, 0.52), (0.07, 0.62),
            (0.045, 0.70), (0.06, 0.76), (0.075, 0.82)]
    for i in range(4):
        x = -0.33 + i * 0.22
        m.lathe(prof, 10, "stone_trim", cap_top=True, center=(x, 0, 0))
    _done("balustrade", m, bevel=0.012)


# ------------------------------------------------------------- pillar & lantern
def pillar():
    if "pillar" in PROTOS:
        return
    m = MB()
    m.box((-0.3, -0.3, 0.0), (0.3, 0.3, 0.18), "stone_trim")
    m.box((-0.26, -0.26, 0.18), (0.26, 0.26, 1.20), "ashlar")
    for ang in range(4):
        c, s = math.cos(ang * math.pi / 2), math.sin(ang * math.pi / 2)
        # proud tile panel on each face
        d = 0.275
        pts = []
        for (u, z) in [(-0.18, 0.48), (0.18, 0.48), (0.18, 0.92), (-0.18, 0.92)]:
            x, y = c * (-d) - s * u, s * (-d) + c * u
            pts.append((x, y, z))
        # face orientation: outward normal is (-c, -s)
        m.face(list(reversed(pts)) if True else pts, "tile")
    m.box((-0.34, -0.34, 1.20), (0.34, 0.34, 1.32), "stone_trim")
    m.box((-0.28, -0.28, 1.32), (0.28, 0.28, 1.38), "stone_trim")
    _done("pillar", m, bevel=0.02)


def lantern():
    if "lantern" in PROTOS:
        return
    m = MB()
    m.box((-0.17, -0.17, 0.0), (0.17, 0.17, 0.05), "iron")
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.box((sx * 0.15 - 0.018, sy * 0.15 - 0.018, 0.05), (sx * 0.15 + 0.018, sy * 0.15 + 0.018, 0.52), "iron")
    m.box((-0.13, -0.13, 0.07), (0.13, 0.13, 0.50), "lamp_glow")
    m.lathe([(0.24, 0.52), (0.24, 0.56), (0.03, 0.74), (0.0, 0.75)], 4, "copper", cap_top=False)
    m.lathe([(0.03, 0.74), (0.035, 0.80), (0.05, 0.84), (0.0, 0.90)], 8, "brass", cap_top=False)
    _done("lantern", m)


def wall_lamp():
    if "wall_lamp" in PROTOS:
        return
    m = MB()
    m.box((-0.06, 0.0, 0.0), (0.06, 0.04, 0.35), "iron")
    m.box((-0.02, -0.38, 0.30), (0.02, 0.0, 0.33), "iron")
    m.box((-0.09, -0.47, -0.05), (0.09, -0.29, 0.22), "lamp_glow")
    m.lathe([(0.15, 0.22), (0.02, 0.36), (0.0, 0.37)], 4, "copper", cap_top=False, center=(0, -0.38, 0))
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.box((sx * 0.09 - 0.01, -0.38 + sy * 0.09 - 0.01, -0.07), (sx * 0.09 + 0.01, -0.38 + sy * 0.09 + 0.01, 0.23), "iron")
    _done("wall_lamp", m)


# ------------------------------------------------------------- pots, planters, furniture
def pots():
    if "pot_terracotta" not in PROTOS:
        m = MB()
        prof = [(0.22, 0.0), (0.30, 0.10), (0.38, 0.32), (0.40, 0.48), (0.36, 0.60), (0.30, 0.66),
                (0.34, 0.70), (0.33, 0.74), (0.28, 0.74)]
        m.lathe(prof, 16, "terracotta", cap_top=False, cap_bottom=True)
        m.lathe([(0.29, 0.70)], 16, "soil", cap_top=True)
        _done("pot_terracotta", m)
    if "pot_turquoise" not in PROTOS:
        m = MB()
        prof = [(0.20, 0.0), (0.32, 0.12), (0.42, 0.40), (0.42, 0.62), (0.34, 0.82), (0.26, 0.92),
                (0.30, 0.98), (0.28, 1.0), (0.24, 1.0)]
        m.lathe(prof, 18, "blue_ceramic", cap_top=False, cap_bottom=True)
        m.lathe([(0.25, 0.95)], 18, "soil", cap_top=True)
        _done("pot_turquoise", m)
    if "pot_small" not in PROTOS:
        m = MB()
        m.lathe([(0.12, 0.0), (0.16, 0.05), (0.19, 0.24), (0.21, 0.28), (0.17, 0.28)], 12,
                "terracotta", cap_top=False, cap_bottom=True)
        m.lathe([(0.17, 0.26)], 12, "soil")
        _done("pot_small", m)


def planter_box(length=1.0, key="planter_box"):
    if key in PROTOS:
        return
    m = MB()
    m.box((-length / 2, -0.22, 0.0), (length / 2, 0.22, 0.42), "stone_trim", skip=("+z",))
    m.box((-length / 2 + 0.05, -0.17, 0.0), (length / 2 - 0.05, 0.17, 0.36), "soil", skip=("-z",))
    m.box((-length / 2 - 0.03, -0.25, 0.42), (length / 2 + 0.03, 0.25, 0.47), "tile")
    _done(key, m, bevel=0.015)


def window_box():
    if "window_box" in PROTOS:
        return
    m = MB()
    m.box((-0.45, -0.2, 0.0), (0.45, 0.0, 0.2), "terracotta")
    m.box((-0.42, -0.18, 0.18), (0.42, -0.02, 0.19), "soil")
    for sx in (-0.35, 0.35):
        m.box((sx - 0.02, -0.06, -0.15), (sx + 0.02, 0.0, 0.02), "iron")
    _done("window_box", m)


def bench():
    if "bench" in PROTOS:
        return
    m = MB()
    for x in (-0.65, 0.65):
        m.box((x - 0.08, -0.22, 0.0), (x + 0.08, 0.22, 0.40), "stone_trim")
    m.box((-0.85, -0.25, 0.40), (0.85, 0.25, 0.46), "stone_trim")
    for i in range(4):
        y = -0.18 + i * 0.12
        m.box((-0.82, y - 0.045, 0.46), (0.82, y + 0.045, 0.49), "timber")
    _done("bench", m, bevel=0.01)


def table_chairs():
    if "cafe_set" in PROTOS:
        return
    m = MB()
    m.lathe([(0.25, 0.0), (0.04, 0.03), (0.03, 0.70), (0.33, 0.72), (0.33, 0.75), (0.0, 0.75)], 14, "iron")
    for a in (0.3, 0.3 + math.pi):
        cx, cy = math.cos(a) * 0.65, math.sin(a) * 0.65
        for dx in (-0.18, 0.18):
            for dy in (-0.18, 0.18):
                m.box((cx + dx - 0.015, cy + dy - 0.015, 0), (cx + dx + 0.015, cy + dy + 0.015, 0.45), "iron")
        m.box((cx - 0.21, cy - 0.21, 0.45), (cx + 0.21, cy + 0.21, 0.49), "timber")
        ox, oy = math.cos(a) * 0.2, math.sin(a) * 0.2
        m.box((cx + ox - 0.2 * abs(math.sin(a)) - 0.02, cy + oy - 0.2 * abs(math.cos(a)) - 0.02, 0.49),
              (cx + ox + 0.2 * abs(math.sin(a)) + 0.02, cy + oy + 0.2 * abs(math.cos(a)) + 0.02, 0.9), "timber")
    _done("cafe_set", m)


def crate_barrel():
    if "crate" not in PROTOS:
        m = MB()
        m.box((-0.3, -0.3, 0), (0.3, 0.3, 0.55), "timber")
        _done("crate", m, bevel=0.015)
    if "barrel" not in PROTOS:
        m = MB()
        m.lathe([(0.24, 0.0), (0.28, 0.2), (0.30, 0.42), (0.28, 0.64), (0.24, 0.84)], 14, "timber", cap_bottom=True)
        for z in (0.1, 0.74):
            m.lathe([(0.265, z), (0.265, z + 0.04)], 14, "iron", cap_top=False)
        _done("barrel", m)


def mooring_post():
    if "mooring_post" in PROTOS:
        return
    m = MB()
    m.lathe([(0.12, -1.6), (0.12, 0.9), (0.10, 1.0), (0.0, 1.05)], 10, "timber")
    m.lathe([(0.125, 0.55), (0.125, 0.7)], 10, "teal_paint", cap_top=False)
    _done("mooring_post", m)


# ------------------------------------------------------------- facade parts
def quoins():
    for key, (a, b) in {"quoin_a": (0.55, 0.32), "quoin_b": (0.32, 0.55)}.items():
        if key in PROTOS:
            continue
        m = MB()
        # sits on an outer corner at origin; walls run along +X (face y<0) and +Y (face x<0)
        m.box((-0.04, -0.04, 0), (a, 0.0, 0.30), "stone_trim", skip=("+y",))
        m.box((-0.04, -0.04, 0), (0.0, b, 0.30), "stone_trim", skip=("+x",))
        _done(key, m, bevel=0.012)


def corbel():
    if "corbel" in PROTOS:
        return
    m = MB()
    # stepped stone bracket, wall at y=0, projecting to -y
    m.box((-0.12, -0.55, -0.12), (0.12, 0.0, 0.0), "stone_trim")
    m.box((-0.11, -0.38, -0.30), (0.11, 0.0, -0.12), "stone_trim")
    m.box((-0.10, -0.20, -0.48), (0.10, 0.0, -0.30), "stone_trim")
    _done("corbel", m, bevel=0.015)


def sill(w):
    key = f"sill_{w:.2f}"
    if key not in PROTOS:
        m = MB()
        m.box((-w / 2 - 0.08, -0.10, -0.08), (w / 2 + 0.08, 0.05, 0.0), "stone_trim")
        _done(key, m, bevel=0.012)
    return key


def window_unit(w, h, arch, lit=False):
    """Frame + glass + mullions sitting in an opening of width w, height h (arch: semicircular top).
    Origin = bottom centre of the opening on the outer wall plane; window plane at y=+0.22."""
    key = f"win_{w:.2f}_{h:.2f}_{int(arch)}_{int(lit)}"
    if key in PROTOS:
        return key
    m = MB()
    y = 0.22
    outline = _outline(w, h, arch)
    glass = "interior_lit" if lit else "glass"
    # back interior plate (deeper) + glass in front
    m.face([(x, y + 0.25, z) for x, z in outline], "interior_lit" if lit else "interior")
    m.face([(x, y + 0.01, z) for x, z in outline], glass)
    fr = 0.06
    # frame as boxes along the outline segments
    for (x0, z0), (x1, z1) in zip(outline, outline[1:] + outline[:1]):
        cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
        L = math.hypot(x1 - x0, z1 - z0)
        ang = math.atan2(z1 - z0, x1 - x0)
        _rot_box(m, (cx, y - 0.03, cz), L + fr * 0.6, 0.06, fr, ang, "timber")
    # mullions
    top = h - (w / 2 if arch else 0)
    _rot_box(m, (0, y - 0.02, top / 2 + 0.02), 0.04, 0.04, top, math.pi / 2, "timber", vertical=True)
    _rot_box(m, (0, y - 0.02, top * 0.62), w, 0.04, 0.04, 0, "timber")
    if not arch:
        _rot_box(m, (0, y - 0.02, top * 0.31), w, 0.04, 0.04, 0, "timber")
    ob = m.to_object(key, proto_coll(), merge=False)
    register_proto(key, ob)
    return key


def door_unit(w, h, arch):
    key = f"door_{w:.2f}_{h:.2f}_{int(arch)}"
    if key in PROTOS:
        return key
    m = MB()
    y = 0.26
    outline = _outline(w, h, arch)
    m.face([(x, y, z) for x, z in outline], "timber")
    # planks / studs
    for i in range(1, 5):
        x = -w / 2 + i * w / 5
        _rot_box(m, (x, y - 0.015, (h - (w / 2 if arch else 0)) / 2), 0.03, 0.03,
                 h - (w / 2 if arch else 0) - 0.05, math.pi / 2, "timber", vertical=True)
    for z in (0.35, 1.2):
        _rot_box(m, (0, y - 0.03, z), w - 0.05, 0.03, 0.08, 0, "iron")
    m.lathe([(0.05, 0), (0.05, 0.02)], 8, "brass", center=(w * 0.32, y - 0.04, 1.05))
    ob = m.to_object(key, proto_coll(), merge=False)
    register_proto(key, ob)
    return key


def shutter_pair(w, h):
    """Open louvred shutters folded back against the facade either side of a w x h opening."""
    key = f"shutters_{w:.2f}_{h:.2f}"
    if key in PROTOS:
        return key
    m = MB()
    sw = w / 2
    for side in (-1, 1):
        x0 = side * (w / 2 + 0.06)
        x1 = side * (w / 2 + 0.06 + sw)
        a, b = min(x0, x1), max(x0, x1)
        m.box((a, -0.07, 0.02), (b, -0.035, h - 0.02), "teal_paint")
        n = int(h / 0.12)
        for i in range(1, n):
            z = i * h / n
            m.box((a + 0.04, -0.09, z - 0.012), (b - 0.04, -0.07, z + 0.012), "teal_paint")
    _done(key, m)
    return key


def awning(w, kind="awning_blue"):
    key = f"awning_{kind}_{w:.2f}"
    if key in PROTOS:
        return key
    m = MB()
    proj, drop = 1.1, 0.55
    # sloped canvas: wall line at y=0 z=0, front edge y=-proj z=-drop
    m.face([(-w / 2, 0, 0), (-w / 2, -proj, -drop), (w / 2, -proj, -drop), (w / 2, 0, 0)], kind)
    # scalloped valance
    n = max(3, int(w / 0.3))
    for i in range(n):
        x0 = -w / 2 + i * w / n
        x1 = x0 + w / n
        pts = [(x0, -proj, -drop), (x1, -proj, -drop), (x1, -proj, -drop - 0.18)]
        for k in range(1, 6):
            t = k / 6
            pts.append((x1 - (x1 - x0) * t, -proj, -drop - 0.18 - 0.08 * math.sin(math.pi * t)))
        pts.append((x0, -proj, -drop - 0.18))
        m.face(pts, kind)
    # side cheeks
    for sx in (-w / 2, w / 2):
        m.face([(sx, 0, 0), (sx, -proj, -drop), (sx, -proj, -drop - 0.18), (sx, 0, -0.18)], kind)
    # iron arms
    for sx in (-w / 2 + 0.05, w / 2 - 0.05):
        m.tube([(sx, 0, -0.9), (sx, -proj, -drop - 0.02)], 0.015, 6, "iron")
    m.box((-w / 2 - 0.05, -0.06, -0.06), (w / 2 + 0.05, 0.0, 0.06), "copper")
    ob = m.to_object(key, proto_coll(), merge=False)
    # double-sided fabric: no culling
    for s in ob.data.materials:
        s.use_backface_culling = False
    register_proto(key, ob)
    return key


def balcony(w):
    key = f"balcony_{w:.2f}"
    if key in PROTOS:
        return key
    m = MB()
    d = 1.0
    m.box((-w / 2, -d, -0.16), (w / 2, 0, 0.0), "stone_trim")
    m.box((-w / 2 - 0.04, -d - 0.04, -0.22), (w / 2 + 0.04, 0.0, -0.16), "stone_trim")
    m.box((-w / 2 + 0.02, -d + 0.02, -0.25), (w / 2 - 0.02, -0.02, -0.22), "tile")
    ob = m.to_object(key, proto_coll(), bevel=0.015)
    register_proto(key, ob)
    return key


def roof_course(length=2.0):
    """One course of barrel roof tiles along +X, 0.25 m wide, for pitched roofs."""
    key = "roof_course"
    if key in PROTOS:
        return key
    m = MB()
    n = int(length / 0.22)
    for i in range(n):
        x = -length / 2 + (i + 0.5) * length / n
        pts = []
        for k in range(7):
            a = math.pi * k / 6
            pts.append((x + 0.1 * math.cos(a), 0.0, 0.045 * math.sin(a)))
        # extrude along -y (down the slope) 0.32
        prev = None
        for k in range(6):
            a0, a1 = pts[k], pts[k + 1]
            m.face([(a0[0], 0.04, a0[2] + 0.02), (a0[0], -0.30, a0[2]), (a1[0], -0.30, a1[2]),
                    (a1[0], 0.04, a1[2] + 0.02)], "terracotta")
    _done(key, m)
    return key


def _outline(w, h, arch, n=10):
    """Opening outline (x, z), CCW seen from outside (looking +y)."""
    if not arch:
        return [(-w / 2, 0), (w / 2, 0), (w / 2, h), (-w / 2, h)]
    r = w / 2
    spring = h - r
    pts = [(-w / 2, 0), (w / 2, 0), (w / 2, spring)]
    for k in range(1, n):
        a = math.pi * k / n
        pts.append((r * math.cos(a), spring + r * math.sin(a)))
    pts.append((-w / 2, spring))
    return pts


def _rot_box(m, c, L, D, H, ang, mat, vertical=False):
    """Box of length L along direction ang in the XZ plane (D depth along y, H thickness)."""
    cx, cy, cz = c
    if vertical:
        m.box((cx - L / 2, cy - D / 2, cz - H / 2), (cx + L / 2, cy + D / 2, cz + H / 2), mat)
        return
    ca, sa = math.cos(ang), math.sin(ang)
    corners = []
    for dx, dz in [(-L / 2, -H / 2), (L / 2, -H / 2), (L / 2, H / 2), (-L / 2, H / 2)]:
        corners.append((cx + dx * ca - dz * sa, cz + dx * sa + dz * ca))
    f = [(x, cy - D / 2, z) for x, z in corners]
    b = [(x, cy + D / 2, z) for x, z in corners]
    m.face(f, mat)
    m.face(b[::-1], mat)
    for i in range(4):
        j = (i + 1) % 4
        m.face([f[j], f[i], b[i], b[j]], mat)


# ------------------------------------------------------------- boats
def boats():
    for key, paint, canopy in (("boat_a", "teal_paint", False), ("boat_b", "green_paint", True)):
        if key in PROTOS:
            continue
        m = MB()
        L, B, Dp = 4.2, 1.35, 0.55
        secs = 11
        rings = []
        for i in range(secs):
            t = i / (secs - 1)
            x = -L / 2 + L * t
            wfac = math.sin(math.pi * (0.06 + 0.88 * t)) ** 0.7
            hb = B / 2 * wfac
            sheer = Dp + 0.18 * (2 * t - 1) ** 2
            ring = []
            for k in range(7):
                a = math.pi * k / 6  # 0..pi : starboard top -> keel -> port top
                yy = hb * math.cos(a)
                zz = sheer - (sheer) * math.sin(a) * (0.65 + 0.35 * wfac)
                ring.append((x, yy, zz))
            rings.append(ring)
        for i in range(secs - 1):
            for k in range(6):
                a, b = rings[i][k], rings[i][k + 1]
                c, d = rings[i + 1][k + 1], rings[i + 1][k]
                mat = paint if k in (0, 5) else "timber"
                m.face([a, b, c, d], mat)
        # gunwale rails, thwarts
        for side in (0, 6):
            m.tube([rings[i][side] for i in range(secs)], 0.03, 5, "timber")
        for x in (-0.9, 0.2, 1.2):
            m.box((x - 0.12, -0.55, 0.28), (x + 0.12, 0.55, 0.32), "timber")
        m.box((-1.9, -0.45, 0.06), (1.9, 0.45, 0.08), "timber")
        if canopy:
            for sx in (-0.4, 0.8):
                for sy in (-0.5, 0.5):
                    m.box((sx - 0.02, sy - 0.02, 0.3), (sx + 0.02, sy + 0.02, 1.35), "iron")
            m.face([(-0.5, -0.62, 1.32), (0.9, -0.62, 1.32), (0.9, 0.0, 1.45), (-0.5, 0.0, 1.45)], "awning_ochre")
            m.face([(-0.5, 0.0, 1.45), (0.9, 0.0, 1.45), (0.9, 0.62, 1.32), (-0.5, 0.62, 1.32)], "awning_ochre")
        else:
            m.tube([(-0.3, -0.5, 0.35), (1.6, -0.75, 0.05)], 0.025, 5, "timber")
            m.box((1.55, -0.85, 0.0), (1.85, -0.68, 0.06), "timber")
        ob = m.to_object(key, proto_coll(), merge=False)
        for s in ob.data.materials:
            s.use_backface_culling = False
        register_proto(key, ob)


def parasol():
    if "parasol" in PROTOS:
        return
    m = MB()
    m.box((-0.25, -0.25, 0.0), (0.25, 0.25, 0.1), "stone_trim")
    m.lathe([(0.025, 0.1), (0.025, 2.45), (0.0, 2.6)], 6, "timber")
    n = 8
    R = 1.35
    for i in range(n):
        a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
        p0 = (R * math.cos(a0), R * math.sin(a0), 2.05)
        p1 = (R * math.cos(a1), R * math.sin(a1), 2.05)
        m.face([(0, 0, 2.5), p0, p1], "awning_red", uv=[(0.5, 1), (0, 0), (1, 0)])
        m.face([p0, p1, (p1[0], p1[1], 1.93), (p0[0], p0[1], 1.93)], "awning_red", uv=[(0, 1), (1, 1), (1, 0.8), (0, 0.8)])
    ob = m.to_object("parasol", proto_coll(), merge=False)
    register_proto("parasol", ob)


def pergola():
    if "pergola" in PROTOS:
        return
    m = MB()
    W, D, H = 3.2, 2.6, 2.4
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.box((sx * W / 2 - 0.08, sy * D / 2 - 0.08, 0), (sx * W / 2 + 0.08, sy * D / 2 + 0.08, H), "timber")
    for sy in (-1, 1):
        m.box((-W / 2 - 0.3, sy * D / 2 - 0.07, H), (W / 2 + 0.3, sy * D / 2 + 0.07, H + 0.18), "timber")
    for i in range(9):
        x = -W / 2 - 0.1 + i * (W + 0.2) / 8
        m.box((x - 0.04, -D / 2 - 0.35, H + 0.18), (x + 0.04, D / 2 + 0.35, H + 0.3), "timber")
    _done("pergola", m, bevel=0.01)


def build_all_basic():
    railing_iron(); balustrade(); pillar(); lantern(); wall_lamp(); pots(); planter_box()
    planter_box(2.0, "planter_long"); window_box(); bench(); table_chairs(); crate_barrel()
    mooring_post(); quoins(); corbel(); roof_course(); boats()
