"""Export the finished scene to GLB for the three.js viewer.

  blender -b milestones/M4.blend --python scripts/export_glb.py
Writes viewer/canal_district.glb and viewer/scene_meta.json (paths, lights, sun, spawn).
glTF convention: +Y up. Blender (x, y, z) -> glTF (x, z, -y).
"""
import os
import sys
import json
import math
import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import layout as Lo  # noqa: E402
from lib import sky  # noqa: E402
from lib import lq_layout as Q  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "public", "world")
os.makedirs(OUT, exist_ok=True)
BAKED = os.path.join(ROOT, "materials", "textures", "baked")
os.makedirs(BAKED, exist_ok=True)


def to_gl(p):
    return [round(p[0], 4), round(p[2], 4), round(-p[1], 4)]


def srgb_to_lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(np.clip(c, 0, None), 1 / 2.4) - 0.055)


def bake_tint(img, tint, name):
    """glTF has no 'texture x constant' node: bake the TINT multiply into a texture copy."""
    path = os.path.join(BAKED, f"{name}_col.png")
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    rgb = lin_to_srgb(srgb_to_lin(px[..., :3]) * np.array(tint[:3], np.float32))
    px[..., :3] = np.clip(rgb, 0, 1)
    new = bpy.data.images.new(f"{name}_col.png", w, h, alpha=True)
    new.pixels[:] = px.ravel()
    new.filepath_raw = path
    new.file_format = "PNG"
    new.save()
    return new


def strip_render_only():
    """Rewire every material to the plain image -> Principled chain the glTF exporter reads."""
    report = []
    for m in bpy.data.materials:
        if not m.node_tree:
            continue
        nt = m.node_tree
        bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
        out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)
        if bsdf is None or out is None:
            continue
        base = nt.nodes.get("BASE_TEX")
        tint = nt.nodes.get("TINT")
        if base and tint:
            col = tint.inputs[7].default_value
            base.image = bake_tint(base.image, col, m.name)
            report.append(f"{m.name}: TINT baked into {m.name}_col.png")
        if base:
            nt.links.new(base.outputs["Color"], bsdf.inputs["Base Color"])
        keep = {"TEX_IMAGE", "NORMAL_MAP", "BSDF_PRINCIPLED", "OUTPUT_MATERIAL"}
        for n in list(nt.nodes):
            if n.type not in keep:
                nt.nodes.remove(n)
        nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
        if m.name == "water":
            bsdf.inputs["Transmission Weight"].default_value = 0.0
    return report


def lq_meta():
    """Gameplay layout for the game, in glTF coordinates (x, up, -y)."""
    def roof(rect, floors):
        return floors * Q.FLOOR_H

    def ladder(lad, rect, top):
        bx, by = lad["base"]
        x0, y0, x1, y1 = rect
        inward = {"w": (1.2, 0), "e": (-1.2, 0), "n": (0, -1.2), "s": (0, 1.2)}[lad["side"]]
        wall = {"w": (x0, by), "e": (x1, by), "n": (bx, y1), "s": (bx, y0)}[lad["side"]]
        return dict(base=to_gl((bx, by, 0.0)), wall=to_gl((wall[0], wall[1], 0.0)),
                    top=to_gl((wall[0] + inward[0], wall[1] + inward[1], top)), height=top, side=lad["side"])

    perches = []
    for p in Q.PERCHES:
        top = roof(p["rect"], p["floors"])
        perches.append(dict(id=p["id"], name=p["name"], spot=to_gl((*p["spot"], top)), roof=top,
                            rect=p["rect"], facing=p["facing"], ladder=ladder(p["ladder"], p["rect"], top)))
    t = Q.TOWER
    ttop = roof(t["rect"], t["floors"])
    tower = dict(name=t["name"], top=ttop, spot=to_gl((*t["spot"], ttop)), dive_to=to_gl((*t["dive_to"], Lo.WATER_Z)),
                 bell=to_gl(((t["rect"][0] + t["rect"][2]) / 2, (t["rect"][1] + t["rect"][3]) / 2, ttop + t["belfry_h"] - 1.1)),
                 ladder=ladder(t["ladder"], t["rect"], ttop), rect=t["rect"])
    zones = {k: dict(min=to_gl((r[0], r[3], 0)), max=to_gl((r[2], r[1], 0))) for k, r in Q.ZONES.items()}
    c = Q.CAFE
    cafe = dict(tables=[to_gl((x, y, 0)) for x, y in c["tables"]], counter=to_gl((*c["counter"], 0)),
                awning=dict(x=c["awning"]["x"], z0=-c["awning"]["y1"], z1=-c["awning"]["y0"],
                            top=c["awning"]["top"], bottom=c["awning"]["bottom"]))
    bx, by = Q.TOLL_BRIDGE["center"]
    guards = [dict(id=g["id"], a=to_gl((*g["a"], g["z"])), b=to_gl((*g["b"], g["z"]))) for g in Q.GUARDS]
    return dict(guards=guards, perches=perches, tower=tower, zones=zones, cafe=cafe, spawn=to_gl((*Q.SPAWN, 0.0)),
                toll_bridge=dict(center=to_gl((bx, by, 0)), south=to_gl((bx, Lo.CANAL_Y0 - 0.4, 0)),
                                 north=to_gl((bx, Lo.CANAL_Y1 + 0.4, 0))),
                water_y=Lo.WATER_Z, bounds=dict(min=to_gl((Q.X0, Q.Y1, 0)), max=to_gl((Q.X1, Q.Y0, 0))),
                canals=dict(main=dict(x0=40, x1=Q.X1 + 130, z0=-Lo.CANAL_Y1, z1=-Lo.CANAL_Y0),
                            side=dict(x0=Lo.CANAL_X0, x1=Lo.CANAL_X1, z0=-(Q.Y1 + 130), z1=-30.0)))


def main():
    sc = bpy.context.scene
    # drop render-only objects
    for ob in list(bpy.data.objects):
        if ob.get("render_only") or ob.type in ("LIGHT", "CAMERA"):
            bpy.data.objects.remove(ob, do_unlink=True)
    # remove sway drivers (viewer re-creates sway in a vertex shader)
    for ob in bpy.data.objects:
        if ob.animation_data and ob.animation_data.drivers:
            for fc in list(ob.animation_data.drivers):
                ob.driver_remove(fc.data_path, fc.array_index)
    rep = strip_render_only()
    sc.frame_set(1)
    path = os.path.join(OUT, "world.glb")
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", export_yup=True, use_renderable=True,
        export_apply=False, export_texcoords=True, export_normals=True, export_tangents=False,
        export_materials="EXPORT", export_image_format="AUTO", export_extras=True,
        export_cameras=False, export_lights=False, export_animations=True,
        export_animation_mode="ACTIONS", export_frame_range=False, export_force_sampling=True,
        export_optimize_animation_size=True, export_def_bones=False,
    )
    # metadata for the viewer
    lamps = []
    for ob in bpy.data.objects:
        k = ob.get("instance_of")
        if k == "lantern":
            p = ob.matrix_world.translation
            lamps.append(to_gl((p.x, p.y, p.z + 0.3 * ob.scale.z)))
        elif k == "wall_lamp":
            p = ob.matrix_world @ __import__("mathutils").Vector((0, -0.38, 0.08))
            lamps.append(to_gl(p))
    s = sky.sun_dir()
    meta = dict(
        convention="glTF +Y up; Blender (x,y,z) -> (x, z, -y); metres",
        sun_dir=to_gl(s), paths={k: [to_gl((x, y, 0)) for x, y in v] for k, v in Lo.PATHS.items()},
        lamps=lamps, district=dict(w=Lo.W, d=Lo.D),
        spawn=dict(walk=to_gl((16.0, 2.0, 1.7)), orbit_target=to_gl((20.0, 15.0, 3.0)),
                   orbit_pos=to_gl((4.0, -22.0, 22.0))),
        cameras={k: dict(pos=to_gl(c["loc"]), target=to_gl(c["target"]), lens=c["lens"]) for k, c in Lo.CAMERAS.items()},
        airship_frames=1440, fps=24, export_report=rep,
    )
    meta["lq"] = lq_meta()
    with open(os.path.join(OUT, "world.json"), "w") as f:
        json.dump(meta, f, indent=1)
    print("EXPORTED", path, os.path.getsize(path) / 1e6, "MB")
    for r in rep:
        print("  ", r)


main()
