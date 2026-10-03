"""Patchwork airship (~12.5 m) with timber/copper gondola, fins, rigging and propellers,
keyframed along a smooth closed route above the district."""
import math
import bpy
from mathutils import Vector
from .core import MB, coll

LENGTH = 12.5
RADIUS = 2.05
ROUTE_C = (67.0, 36.0)
ROUTE_R = (64.0, 44.0)
ROUTE_Z = 38.0
FRAMES = 1440  # 60 s at 24 fps


def _envelope(m):
    """Body of revolution along +X with fixed UVs (u along length, v around)."""
    rings, segs = 18, 20
    prof = []
    for i in range(rings + 1):
        t = i / rings
        x = -LENGTH / 2 + LENGTH * t
        # blunt nose, long tapering tail
        r = RADIUS * (math.sin(math.pi * t ** 0.85) ** 0.75)
        prof.append((x, max(r, 0.02)))
    for i in range(rings):
        (x0, r0), (x1, r1) = prof[i], prof[i + 1]
        for s in range(segs):
            a0, a1 = 2 * math.pi * s / segs, 2 * math.pi * (s + 1) / segs
            p = [(x0, r0 * math.cos(a0), r0 * math.sin(a0)), (x1, r1 * math.cos(a0), r1 * math.sin(a0)),
                 (x1, r1 * math.cos(a1), r1 * math.sin(a1)), (x0, r0 * math.cos(a1), r0 * math.sin(a1))]
            uv = [(i / rings * 1.6, s / segs), ((i + 1) / rings * 1.6, s / segs),
                  ((i + 1) / rings * 1.6, (s + 1) / segs), (i / rings * 1.6, (s + 1) / segs)]
            # outward normal is radial
            m.face(p, "patchwork", uv=uv, orient=(0, math.cos((a0 + a1) / 2), math.sin((a0 + a1) / 2)))
    return prof


def _ring(m, x, r, w, mat):
    n = 20
    for s in range(n):
        a0, a1 = 2 * math.pi * s / n, 2 * math.pi * (s + 1) / n
        rr = r + 0.03
        m.face([(x - w, rr * math.cos(a0), rr * math.sin(a0)), (x + w, rr * math.cos(a0), rr * math.sin(a0)),
                (x + w, rr * math.cos(a1), rr * math.sin(a1)), (x - w, rr * math.cos(a1), rr * math.sin(a1))],
               mat, orient=(0, math.cos(a0), math.sin(a0)))


def build():
    C = coll("airship")
    root = bpy.data.objects.new("Airship", None)
    root.empty_display_type = "ARROWS"
    C.objects.link(root)
    m = MB()
    prof = _envelope(m)

    def r_at(x):
        for (xa, ra), (xb, rb) in zip(prof[:-1], prof[1:]):
            if xa <= x <= xb:
                return ra + (rb - ra) * (x - xa) / (xb - xa)
        return 0.0
    for x in (-3.0, 0.5, 3.6):
        _ring(m, x, r_at(x), 0.06, "rope")
    _ring(m, LENGTH / 2 - 0.9, r_at(LENGTH / 2 - 0.9), 0.12, "copper")
    # fins: four, cross-shaped at the tail, fabric over timber spars
    fx0, fx1 = -LENGTH / 2 + 0.25, -LENGTH / 2 + 2.6
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        ca, sa = math.cos(a), math.sin(a)
        r0a, r0b = r_at(fx0) * 0.9, r_at(fx1) * 0.9
        out = 1.35
        pts = [(fx0, ca * r0a, sa * r0a), (fx1, ca * r0b, sa * r0b),
               (fx0 + 0.6, ca * (r0a + out), sa * (r0a + out)), (fx0 - 0.15, ca * (r0a + out * 0.85), sa * (r0a + out * 0.85))]
        nrm = (0, -sa, ca)
        m.face(pts, "patchwork", uv=[(0, 0), (1, 0), (1, 1), (0, 1)], orient=nrm)
        m.face(pts, "patchwork", uv=[(0, 0), (1, 0), (1, 1), (0, 1)], orient=(0, sa, -ca))
        m.tube([pts[2], pts[3]], 0.035, 5, "timber")
        m.tube([pts[1], pts[2]], 0.03, 5, "timber")
    env = m.to_object("airship_envelope", C, merge=False)
    for s_ in env.data.materials:
        s_.use_backface_culling = False
    env.parent = root

    # gondola: timber hull with copper roof, glowing windows, railing, rigging
    g = MB()
    gz = -RADIUS - 1.55
    L, Wd = 4.2, 1.3
    hull = [(-L / 2, 0.0), (-L / 2 + 0.4, -0.45), (L / 2 - 0.6, -0.45), (L / 2, 0.0)]
    from .site import extrude_xz
    extrude_xz(g, [(x, z + gz) for x, z in hull], -Wd / 2, Wd / 2, "timber")
    g.box((-L / 2 + 0.3, -Wd / 2 + 0.05, gz), (L / 2 - 0.45, Wd / 2 - 0.05, gz + 0.95), "timber")
    for i in range(5):
        x = -L / 2 + 0.6 + i * 0.68
        for s in (-1, 1):
            g.face([(x - 0.22, s * (Wd / 2 - 0.04), gz + 0.35), (x + 0.22, s * (Wd / 2 - 0.04), gz + 0.35),
                    (x + 0.22, s * (Wd / 2 - 0.04), gz + 0.75), (x - 0.22, s * (Wd / 2 - 0.04), gz + 0.75)],
                   "interior_lit", orient=(0, s, 0))
    g.box((-L / 2 + 0.15, -Wd / 2 - 0.12, gz + 0.95), (L / 2 - 0.3, Wd / 2 + 0.12, gz + 1.05), "copper")
    g.lathe([(0.32, 0.0), (0.3, 0.2), (0.0, 0.35)], 8, "copper", center=(L / 2 - 0.2, 0, gz + 0.1))
    # rigging lines from the envelope belly to the gondola roof corners
    for xa, xb in ((-1.9, -1.5), (1.6, 1.3), (-3.5, -1.8), (3.2, 1.6)):
        for s in (-1, 1):
            top = (xa, s * 0.9, -math.sqrt(max(0.0, r_at(xa) ** 2 - 0.81)) + 0.05)
            g.tube([top, (xb, s * (Wd / 2), gz + 1.05)], 0.018, 4, "rope", smooth=False)
    # engine pods with propellers mounted on outriggers
    for s in (-1, 1):
        g.tube([(-0.6, s * Wd / 2, gz + 0.6), (-0.9, s * (Wd / 2 + 1.0), gz + 0.75)], 0.05, 6, "iron")
    gond = g.to_object("airship_gondola", C, merge=False)
    gond.parent = root
    pods = []
    for s in (-1, 1):
        pm = MB()
        prof2 = [(0.02, -0.5), (0.16, -0.35), (0.2, 0.0), (0.17, 0.3), (0.02, 0.42)]
        pm.lathe([(r, z) for r, z in prof2], 10, "copper")
        pod = pm.to_object(f"airship_pod_{'L' if s > 0 else 'R'}", C, merge=False)
        pod.parent = root
        pod.location = (-0.9, s * (Wd / 2 + 1.0), gz + 0.75)
        pod.rotation_euler = (0, math.pi / 2, 0)  # lathe axis Z -> ship X
        pm = MB()
        for b in range(3):
            a = 2 * math.pi * b / 3
            d = Vector((0, math.cos(a), math.sin(a)))
            n = Vector((0, -math.sin(a), math.cos(a)))
            p0 = d * 0.1
            p1 = d * 0.85
            pts = [p0 - n * 0.05, p1 - n * 0.09, p1 + n * 0.09, p0 + n * 0.05]
            pm.face([tuple(p + Vector((-0.02 * i, 0, 0))) for i, p in enumerate(pts)], "timber", orient=(-1, 0, 0))
            pm.face([tuple(p + Vector((0.02 - 0.02 * i, 0, 0))) for i, p in enumerate(pts)], "timber", orient=(1, 0, 0))
        prop = pm.to_object(f"airship_prop_{'L' if s > 0 else 'R'}", C, merge=False)
        prop.parent = root
        prop.location = (-1.45, s * (Wd / 2 + 1.0), gz + 0.75)
        prop["spin"] = True
        pods.append(prop)
    # pennant
    pn = MB()
    pn.face([(-LENGTH / 2 - 0.2, 0, 0.2), (-LENGTH / 2 - 1.6, 0, 0.0), (-LENGTH / 2 - 0.2, 0, -0.25)], "awning_red",
            uv=[(0, 1), (1, 0.5), (0, 0)], orient=(0, -1, 0))
    pen = pn.to_object("airship_pennant", C, merge=False)
    pen.parent = root
    for s_ in pen.data.materials:
        s_.use_backface_culling = False
    animate(root, pods)
    return root


def route(t):
    """Closed smooth route, t in [0,1). Returns position (Vector) and heading (rad)."""
    a = 2 * math.pi * t
    cx, cy = ROUTE_C
    rx, ry = ROUTE_R
    x = cx + rx * math.cos(a) + 3.0 * math.cos(2 * a)
    y = cy + ry * math.sin(a)
    z = ROUTE_Z + 1.6 * math.sin(2 * a + 0.7)
    dx = -rx * math.sin(a) - 6.0 * math.sin(2 * a)
    dy = ry * math.cos(a)
    return Vector((x, y, z)), math.atan2(dy, dx)


def animate(root, props, step=8):
    sc = bpy.context.scene
    sc.frame_end = FRAMES
    prev_h = None
    for f in range(0, FRAMES + 1, step):
        t = f / FRAMES
        p, h = route(t)
        if prev_h is not None:
            while h - prev_h > math.pi:
                h -= 2 * math.pi
            while h - prev_h < -math.pi:
                h += 2 * math.pi
        # bank into the turn and pitch with the climb
        _, h2 = route(t + 0.01)
        turn = (h2 - h + math.pi) % (2 * math.pi) - math.pi
        root.location = p
        root.rotation_euler = (-turn * 0.6, 0.03 * math.sin(4 * math.pi * t), h)
        root.keyframe_insert("location", frame=f + 1)
        root.keyframe_insert("rotation_euler", frame=f + 1)
        prev_h = h
    for pr in props:
        for f, ang in ((1, 0.0), (FRAMES + 1, 2 * math.pi * 300)):
            pr.rotation_euler = (ang, 0, 0)
            pr.keyframe_insert("rotation_euler", index=0, frame=f)
    for ob in [root] + props:
        ad = ob.animation_data
        if ad and ad.action:
            _linearize(ad.action, ob in props)


def _linearize(action, linear):
    """Blender 5 layered actions: iterate all channelbags' fcurves."""
    curves = []
    try:
        for layer in action.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    curves.extend(cb.fcurves)
    except AttributeError:
        curves = list(action.fcurves)
    for fc in curves:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR" if linear else "BEZIER"
            if not linear:
                kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"
