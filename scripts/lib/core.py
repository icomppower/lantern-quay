"""Core helpers: scene reset, collections, materials, mesh builder, instancing."""
import math
import os
import bpy
import bmesh
from mathutils import Vector, Matrix

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TEX = os.path.join(ROOT, "materials", "textures")

# metres covered by one texture repeat, per material
TILE = {
    "flagstone": 4.0, "ashlar": 2.0, "ashlar_dark": 2.0, "plaster": 3.0, "plaster_ochre": 3.0,
    "plaster_rose": 3.0, "tile": 0.9, "timber": 1.2, "copper": 2.0, "terracotta": 1.0,
    "awning_blue": 1.0, "awning_red": 1.0, "awning_ochre": 1.0, "patchwork": 3.0,
    "canal_bed": 2.0, "stone_trim": 1.5,
}


# ------------------------------------------------------------------ scene
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    return sc


def coll(name, parent=None, hidden=False):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(c)
    if hidden:
        c.hide_render = True
        c.hide_viewport = True
    return c


# ------------------------------------------------------------------ materials
_mats = {}


def _img(name, noncolor=False):
    path = os.path.join(TEX, name)
    im = bpy.data.images.get(name) or bpy.data.images.load(path, check_existing=True)
    if noncolor:
        im.colorspace_settings.name = "Non-Color"
    return im


def _new_mat(name):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (600, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (300, 0)
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    return m, nt, bsdf, out


def _mix_rgb(nt, blend="MULTIPLY"):
    n = nt.nodes.new("ShaderNodeMix")
    n.data_type = "RGBA"
    n.blend_type = blend
    return n  # inputs: 0 factor, 6 A, 7 B ; outputs: 2 result


def pbr(name, col_img, nrm_img=None, rough=0.8, metal=0.0, tint=None, nrm_strength=1.0,
        variation=0.25, rough_img=None, specular=0.5):
    """Image-based PBR material. A RENDER_ONLY noise multiply adds large-scale colour
    variation in Cycles; export.py rewires it away so glTF sees image -> Base Color."""
    if name in _mats:
        return _mats[name]
    m, nt, bsdf, out = _new_mat(name)
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = _img(col_img)
    tex.location = (-500, 100)
    tex.name = "BASE_TEX"
    src = tex.outputs[0]
    if tint is not None:
        mt = _mix_rgb(nt, "MULTIPLY")
        mt.inputs[0].default_value = 1.0
        mt.inputs[7].default_value = (*tint, 1)
        nt.links.new(src, mt.inputs[6])
        mt.name = "TINT"  # exported: baked into a tinted texture copy by export.py
        src = mt.outputs[2]
    if variation > 0:
        tc = nt.nodes.new("ShaderNodeTexCoord")
        tc.location = (-900, -200)
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.location = (-700, -200)
        nz.inputs["Scale"].default_value = 0.35
        nz.inputs["Detail"].default_value = 3
        nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
        ramp = nt.nodes.new("ShaderNodeMapRange")
        ramp.inputs[1].default_value = 0.3
        ramp.inputs[2].default_value = 0.7
        ramp.inputs[3].default_value = 1 - variation
        ramp.inputs[4].default_value = 1 + variation * 0.4
        nt.links.new(nz.outputs[0], ramp.inputs[0])
        mv = _mix_rgb(nt, "MULTIPLY")
        mv.name = "RENDER_ONLY"
        mv.inputs[0].default_value = 1.0
        nt.links.new(src, mv.inputs[6])
        cr = nt.nodes.new("ShaderNodeCombineColor")
        for i in range(3):
            nt.links.new(ramp.outputs[0], cr.inputs[i])
        nt.links.new(cr.outputs[0], mv.inputs[7])
        src = mv.outputs[2]
    nt.links.new(src, bsdf.inputs["Base Color"])
    if nrm_img:
        nt_ = nt.nodes.new("ShaderNodeTexImage")
        nt_.image = _img(nrm_img, True)
        nt_.location = (-500, -300)
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = nrm_strength
        nt.links.new(nt_.outputs[0], nm.inputs["Color"])
        nt.links.new(nm.outputs[0], bsdf.inputs["Normal"])
    if rough_img:
        rt = nt.nodes.new("ShaderNodeTexImage")
        rt.image = _img(rough_img, True)
        nt.links.new(rt.outputs[0], bsdf.inputs["Roughness"])
    else:
        bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    _mats[name] = m
    return m


def flat(name, color, rough=0.6, metal=0.0, emit=None, emit_strength=0.0, alpha=1.0,
         transmission=0.0):
    if name in _mats:
        return _mats[name]
    m, nt, bsdf, out = _new_mat(name)
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emit:
        bsdf.inputs["Emission Color"].default_value = (*emit, 1)
        bsdf.inputs["Emission Strength"].default_value = emit_strength
    if transmission:
        bsdf.inputs["Transmission Weight"].default_value = transmission
    if alpha < 1:
        bsdf.inputs["Alpha"].default_value = alpha
    m.diffuse_color = (*color, 1)
    _mats[name] = m
    return m


def foliage(name, img, translucency=0.12, tint=(1, 1, 1)):
    """Alpha-tested card material. Translucent backlight is RENDER_ONLY."""
    if name in _mats:
        return _mats[name]
    m, nt, bsdf, out = _new_mat(name)
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = _img(img)
    tex.name = "BASE_TEX"
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    bsdf.inputs["Roughness"].default_value = 0.9
    bsdf.inputs["Specular IOR Level"].default_value = 0.0
    # backlit translucency (render only)
    tr = nt.nodes.new("ShaderNodeBsdfTranslucent")
    tr.name = "RENDER_ONLY_TRANSLUCENT"
    hue = _mix_rgb(nt, "MULTIPLY")
    hue.inputs[0].default_value = 1
    hue.inputs[7].default_value = (0.55, 0.75, 0.25, 1)
    nt.links.new(tex.outputs["Color"], hue.inputs[6])
    nt.links.new(hue.outputs[2], tr.inputs["Color"])
    tp = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix1 = nt.nodes.new("ShaderNodeMixShader")
    mix1.inputs[0].default_value = translucency
    nt.links.new(bsdf.outputs[0], mix1.inputs[1])
    nt.links.new(tr.outputs[0], mix1.inputs[2])
    mix2 = nt.nodes.new("ShaderNodeMixShader")
    mix2.name = "RENDER_ONLY_ALPHA"
    nt.links.new(tex.outputs["Alpha"], mix2.inputs[0])
    nt.links.new(tp.outputs[0], mix2.inputs[1])
    nt.links.new(mix1.outputs[0], mix2.inputs[2])
    nt.links.new(mix2.outputs[0], out.inputs[0])
    try:
        m.surface_render_method = "DITHERED"
    except Exception:
        pass
    m.use_backface_culling = False
    m["alpha_test"] = 0.5
    _mats[name] = m
    return m


def water_mat():
    if "water" in _mats:
        return _mats["water"]
    m, nt, bsdf, out = _new_mat("water")
    bsdf.inputs["Base Color"].default_value = (0.20, 0.52, 0.50, 1)
    bsdf.inputs["Roughness"].default_value = 0.04
    bsdf.inputs["Transmission Weight"].default_value = 0.85
    bsdf.inputs["IOR"].default_value = 1.33
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.name = "RENDER_ONLY_WAVES"
    nz.noise_dimensions = "4D"
    nz.inputs["Scale"].default_value = 1.6
    nz.inputs["Detail"].default_value = 6
    nz.inputs["Roughness"].default_value = 0.55
    # animated: W follows the frame (driver), the water drifts and shimmers
    fc = nz.inputs["W"].driver_add("default_value")
    fc.driver.expression = "frame/48.0"
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.0, 2.2, 1.0)
    fc2 = mp.inputs["Location"].driver_add("default_value", 1)
    fc2.driver.expression = "frame/120.0"
    nt.links.new(tc.outputs["Object"], mp.inputs[0])
    nt.links.new(mp.outputs[0], nz.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.22
    bump.inputs["Distance"].default_value = 0.05
    nt.links.new(nz.outputs[0], bump.inputs["Height"])
    nt.links.new(bump.outputs[0], bsdf.inputs["Normal"])
    m.diffuse_color = (0.2, 0.52, 0.5, 1)
    _mats["water"] = m
    return m


def materials():
    """Return the shared material palette (created once)."""
    return {
        "flagstone": pbr("flagstone", "flagstone_col.png", "flagstone_nrm.png", 0.85, nrm_strength=1.2),
        "ashlar": pbr("ashlar", "ashlar_col.png", "ashlar_nrm.png", 0.85, nrm_strength=1.3),
        "ashlar_dark": pbr("ashlar_dark", "ashlar_col.png", "ashlar_nrm.png", 0.9,
                           tint=(0.62, 0.55, 0.48), nrm_strength=1.3),
        "stone_trim": pbr("stone_trim", "ashlar_col.png", "plaster_nrm.png", 0.75,
                          tint=(1.08, 1.04, 0.98), variation=0.1),
        "plaster": pbr("plaster", "plaster_col.png", "plaster_nrm.png", 0.9),
        "plaster_ochre": pbr("plaster_ochre", "plaster_col.png", "plaster_nrm.png", 0.9,
                             tint=(1.0, 0.82, 0.55)),
        "plaster_rose": pbr("plaster_rose", "plaster_col.png", "plaster_nrm.png", 0.9,
                            tint=(1.0, 0.80, 0.70)),
        "tile": pbr("tile", "tile_col.png", "tile_nrm.png", 0.18, variation=0.05, nrm_strength=0.8),
        "timber": pbr("timber", "timber_col.png", "timber_nrm.png", 0.7, variation=0.1),
        "copper": pbr("copper", "copper_col.png", "copper_nrm.png", 0.5, metal=0.55,
                      rough_img="copper_rgh.png", variation=0.1),
        "terracotta": pbr("terracotta", "terracotta_col.png", "terracotta_nrm.png", 0.75, variation=0.15),
        "awning_blue": pbr("awning_blue", "awning_blue_col.png", None, 0.9, variation=0.05),
        "awning_red": pbr("awning_red", "awning_red_col.png", None, 0.9, variation=0.05),
        "awning_ochre": pbr("awning_ochre", "awning_ochre_col.png", None, 0.9, variation=0.05),
        "patchwork": pbr("patchwork", "patchwork_col.png", "patchwork_nrm.png", 0.85, variation=0.08),
        "canal_bed": pbr("canal_bed", "ashlar_col.png", "ashlar_nrm.png", 0.95, tint=(0.28, 0.33, 0.26)),
        "iron": flat("iron", (0.035, 0.035, 0.035), 0.45, 0.8),
        "glass": flat("glass", (0.025, 0.035, 0.04), 0.18, 0.0),
        "interior": flat("interior", (0.035, 0.028, 0.022), 0.9),
        "interior_lit": flat("interior_lit", (0.05, 0.03, 0.02), 0.9, emit=(1.0, 0.62, 0.30), emit_strength=1.4),
        "lamp_glow": flat("lamp_glow", (1.0, 0.8, 0.5), 0.3, emit=(1.0, 0.60, 0.26), emit_strength=7.0),
        "teal_paint": flat("teal_paint", (0.05, 0.30, 0.30), 0.55),
        "green_paint": flat("green_paint", (0.10, 0.24, 0.16), 0.55),
        "blue_ceramic": flat("blue_ceramic", (0.02, 0.32, 0.40), 0.15),
        "soil": flat("soil", (0.12, 0.08, 0.05), 1.0),
        "rope": flat("rope", (0.45, 0.36, 0.24), 0.9),
        "bark": flat("bark", (0.17, 0.12, 0.08), 0.95),
        "palm_bark": flat("palm_bark", (0.33, 0.27, 0.19), 0.95),
        "brass": flat("brass", (0.62, 0.45, 0.20), 0.35, 0.9),
        "cushion": flat("cushion", (0.55, 0.20, 0.12), 0.9),
        "water": water_mat(),
        "leaf_orange": foliage("leaf_orange", "leaf_orange.png"),
        "leaf_olive": foliage("leaf_olive", "leaf_olive.png"),
        "leaf_bougainvillea": foliage("leaf_bougainvillea", "leaf_bougainvillea.png"),
        "leaf_shrub": foliage("leaf_shrub", "leaf_shrub.png"),
        "leaf_ivy": foliage("leaf_ivy", "leaf_ivy.png"),
        "palm_frond": foliage("palm_frond", "palm_frond.png"),
        "grass": foliage("grass", "grass.png"),
        "leaf_cypress": foliage("leaf_cypress", "leaf_cypress.png"),
        "cypress": flat("cypress", (0.035, 0.075, 0.03), 0.9),
        "hill": flat("hill", (0.36, 0.33, 0.20), 1.0),
        "hill_far": flat("hill_far", (0.40, 0.36, 0.28), 1.0),
        "distant_stone_lit": flat("distant_stone_lit", (0.80, 0.66, 0.50), 0.9),
        "copper_far": flat("copper_far", (0.22, 0.48, 0.42), 0.6, 0.3),
        "distant_stone": flat("distant_stone", (0.72, 0.58, 0.44), 0.9),
    }


# ------------------------------------------------------------------ mesh builder
class MB:
    """Accumulates geometry in local space with per-face material names."""

    def __init__(self):
        self.bm = bmesh.new()
        self.mat_names = []
        self.face_mat = {}

    def mi(self, mat):
        if mat not in self.mat_names:
            self.mat_names.append(mat)
        return self.mat_names.index(mat)

    def v(self, p):
        return self.bm.verts.new(p)

    def face(self, pts, mat, uv=None, orient=None):
        if orient is not None:
            n = Vector((0, 0, 0))
            for a, b in zip(pts, list(pts[1:]) + [pts[0]]):
                n.x += (a[1] - b[1]) * (a[2] + b[2])
                n.y += (a[2] - b[2]) * (a[0] + b[0])
                n.z += (a[0] - b[0]) * (a[1] + b[1])
            if n.dot(Vector(orient)) < 0:
                pts = list(reversed(pts))
                if uv is not None:
                    uv = list(reversed(uv))
        vs = [self.bm.verts.new(p) for p in pts]
        try:
            f = self.bm.faces.new(vs)
        except ValueError:
            return None
        f.material_index = self.mi(mat)
        if uv is not None:
            self._fixed_uv = getattr(self, "_fixed_uv", {})
            self._fixed_uv[f] = uv
        return f

    def box(self, mn, mx, mat, skip=()):
        x0, y0, z0 = mn
        x1, y1, z1 = mx
        P = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
             (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        F = {"-z": (0, 3, 2, 1), "+z": (4, 5, 6, 7), "-y": (0, 1, 5, 4), "+y": (2, 3, 7, 6),
             "-x": (3, 0, 4, 7), "+x": (1, 2, 6, 5)}
        for k, idx in F.items():
            if k in skip:
                continue
            self.face([P[i] for i in idx], mat)

    def prism(self, poly, z0, z1, mat_top, mat_side, bottom=False, mat_bottom=None):
        """Extrude CCW 2D polygon from z0 to z1."""
        n = len(poly)
        self.face([(x, y, z1) for x, y in poly], mat_top)
        if bottom:
            self.face([(x, y, z0) for x, y in reversed(poly)], mat_bottom or mat_side)
        for i in range(n):
            a, b = poly[i], poly[(i + 1) % n]
            self.face([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)], mat_side)

    def lathe(self, profile, segs, mat, cap_top=True, cap_bottom=False, center=(0, 0, 0), smooth=True):
        """profile: list of (r, z) bottom->top. Revolve around Z."""
        cx, cy, cz = center
        rings = []
        for r, z in profile:
            ring = []
            for s in range(segs):
                a = 2 * math.pi * s / segs
                ring.append(self.bm.verts.new((cx + r * math.cos(a), cy + r * math.sin(a), cz + z)))
            rings.append(ring)
        mi = self.mi(mat)
        for j in range(len(rings) - 1):
            for s in range(segs):
                a, b = rings[j][s], rings[j][(s + 1) % segs]
                c, d = rings[j + 1][(s + 1) % segs], rings[j + 1][s]
                try:
                    f = self.bm.faces.new((a, b, c, d))
                    f.material_index = mi
                    f.smooth = smooth
                except ValueError:
                    pass
        if cap_top and profile[-1][0] > 1e-4:
            f = self.bm.faces.new(rings[-1])
            f.material_index = mi
        if cap_bottom and profile[0][0] > 1e-4:
            f = self.bm.faces.new(list(reversed(rings[0])))
            f.material_index = mi

    def tube(self, pts, radius, segs, mat, smooth=True, radii=None):
        """Sweep a circle along a polyline (for trunks, rails, ropes)."""
        rings = []
        for i, p in enumerate(pts):
            p = Vector(p)
            if i == 0:
                t = Vector(pts[1]) - p
            elif i == len(pts) - 1:
                t = p - Vector(pts[i - 1])
            else:
                t = Vector(pts[i + 1]) - Vector(pts[i - 1])
            t.normalize()
            up = Vector((0, 0, 1)) if abs(t.z) < 0.95 else Vector((1, 0, 0))
            u = t.cross(up).normalized()
            w = t.cross(u).normalized()
            r = radii[i] if radii else radius
            ring = [self.bm.verts.new(p + (u * math.cos(2 * math.pi * s / segs) +
                                          w * math.sin(2 * math.pi * s / segs)) * r) for s in range(segs)]
            rings.append(ring)
        mi = self.mi(mat)
        for j in range(len(rings) - 1):
            for s in range(segs):
                try:
                    f = self.bm.faces.new((rings[j][s], rings[j][(s + 1) % segs],
                                           rings[j + 1][(s + 1) % segs], rings[j + 1][s]))
                    f.material_index = mi
                    f.smooth = smooth
                except ValueError:
                    pass

    def merge(self, dist=1e-4):
        bmesh.ops.remove_doubles(self.bm, verts=self.bm.verts, dist=dist)

    def to_object(self, name, collection, bevel=0.0, bevel_segs=2, uv_world_offset=(0, 0, 0),
                  merge=True, smooth_all=False):
        mats = materials()
        if merge:
            self.merge()
        bm = self.bm
        bm.normal_update()
        uvl = bm.loops.layers.uv.verify()
        fixed = getattr(self, "_fixed_uv", {})
        ox, oy, oz = uv_world_offset
        for f in bm.faces:
            mname = self.mat_names[f.material_index]
            t = TILE.get(mname, 1.0)
            if f in fixed:
                for l, uv in zip(f.loops, fixed[f]):
                    l[uvl].uv = uv
                continue
            n = f.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            for l in f.loops:
                co = l.vert.co
                x, y, z = co.x + ox, co.y + oy, co.z + oz
                if ax == 2:
                    u, v = x, y
                elif ax == 1:
                    u, v = (x if n.y < 0 else -x), z
                else:
                    u, v = (y if n.x > 0 else -y), z
                l[uvl].uv = (u / t, v / t)
            if smooth_all:
                f.smooth = True
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        for mn in self.mat_names:
            me.materials.append(mats[mn])
        ob = bpy.data.objects.new(name, me)
        collection.objects.link(ob)
        if bevel > 0:
            bake_bevel(ob, bevel, bevel_segs)
        return ob


def bake_bevel(ob, width, segs=2, angle=40):
    """Bake an angle-limited bevel into the mesh. Falls back to a smaller bevel, then none,
    if the modifier produces spikes (vertices outside the original bounds)."""
    me0 = ob.data
    lo = [min(v.co[i] for v in me0.vertices) for i in range(3)]
    hi = [max(v.co[i] for v in me0.vertices) for i in range(3)]
    for w in (width, width * 0.5):
        mod = ob.modifiers.new("bevel", "BEVEL")
        mod.width = w
        mod.segments = segs
        mod.limit_method = "ANGLE"
        mod.angle_limit = math.radians(angle)
        mod.use_clamp_overlap = True
        dg = bpy.context.evaluated_depsgraph_get()
        ev = ob.evaluated_get(dg)
        new = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
        ob.modifiers.clear()
        ok = all(lo[i] - 0.05 <= v.co[i] <= hi[i] + 0.05 for v in new.vertices for i in range(3))
        if ok:
            ob.data = new
            new.name = me0.name
            bpy.data.meshes.remove(me0)
            return True
        bpy.data.meshes.remove(new)
    print("WARN bevel spikes, kept unbevelled:", ob.name)
    return False


# ------------------------------------------------------------------ instancing
PROTOS = {}


def proto_coll():
    return coll("_prototypes", hidden=True)


def register_proto(key, ob):
    """Move a freshly built object into the hidden prototype collection."""
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    proto_coll().objects.link(ob)
    PROTOS[key] = ob
    ob["proto"] = key
    return ob


def inst(key, loc, rot_z=0.0, collection=None, scale=1.0, rot=None, name=None):
    """Linked duplicate of a prototype: shares mesh data (no geometry copy)."""
    src = PROTOS[key]
    ob = bpy.data.objects.new(name or f"{key}.i", src.data)
    ob.location = loc
    if rot is not None:
        ob.rotation_euler = rot
    else:
        ob.rotation_euler = (0, 0, rot_z)
    if isinstance(scale, (int, float)):
        ob.scale = (scale, scale, scale)
    else:
        ob.scale = scale
    ob["instance_of"] = key
    (collection or bpy.context.scene.collection).objects.link(ob)
    return ob


def along(points, spacing):
    """Yield (pos, angle) every `spacing` metres along a 2D polyline (centre of each span)."""
    out = []
    for a, b in zip(points[:-1], points[1:]):
        a, b = Vector((*a, 0)), Vector((*b, 0))
        d = b - a
        L = d.length
        n = max(1, round(L / spacing))
        ang = math.atan2(d.y, d.x)
        for i in range(n):
            p = a + d * ((i + 0.5) / n)
            out.append(((p.x, p.y), ang, L / n))
    return out


def arc_pts(cx, cy, r, a0, a1, n):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cy + r * math.sin(a0 + (a1 - a0) * i / n))
            for i in range(n + 1)]
