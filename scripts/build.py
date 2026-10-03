"""Regenerate the canal district from scratch.

  blender -b --python scripts/build.py -- --stage 2 --render ref,bridge --out milestones/M2
  stage 2 = canal/bridge/stair section, 3 = full district, 4 = + animation, scenery, final light
  --hero renders CAM_HERO at 1920x1080; --samples overrides preview samples (64).
"""
import os
import sys
import time
import argparse
import importlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402

from lib import core, layout, assets, arch, site, veg, sky, district, airship, scenery, lq_layout, quay  # noqa: E402
for mod in (core, layout, lq_layout, assets, arch, site, veg, sky, district, airship, scenery, quay):
    importlib.reload(mod)


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=int, default=5)
    ap.add_argument("--render", default="")
    ap.add_argument("--out", default=os.path.join(core.ROOT, "milestones", "scene"))
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--hero", action="store_true")
    ap.add_argument("--hero-samples", type=int, default=256)
    ap.add_argument("--frame", type=int, default=1)
    ap.add_argument("--no-save", action="store_true")
    return ap.parse_args(argv)


def stats():
    tris = 0
    seen = set()
    inst_tris = 0
    objs = 0
    for ob in bpy.data.objects:
        if ob.type != "MESH" or ob.users_collection[0].name == "_prototypes":
            continue
        objs += 1
        me = ob.data
        t = sum(len(p.vertices) - 2 for p in me.polygons)
        inst_tris += t
        if me.name not in seen:
            seen.add(me.name)
            tris += t
    return dict(objects=objs, unique_meshes=len(seen), unique_tris=tris, drawn_tris=inst_tris)


def main():
    a = parse()
    t0 = time.time()
    core.reset_scene()
    core.materials()
    assets.build_all_basic()
    veg.make_protos()
    sky.render_settings(960, 540, a.samples)
    sky.world()
    sky.sun()
    cams = sky.cameras()
    district.section(None)
    if a.stage >= 3:
        district.expand()
    if a.stage >= 4:
        district.finish()
    if a.stage >= 5:
        quay.build()
    atm = sky.atmosphere(core.coll("atmosphere"))
    sc = bpy.context.scene
    sc.frame_set(a.frame)
    st = stats()
    print("STATS", st, "build_s=%.1f" % (time.time() - t0))
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    if not a.no_save:
        bpy.ops.wm.save_as_mainfile(filepath=a.out + ".blend", compress=True)
    for name in [r for r in a.render.split(",") if r]:
        cam = cams["CAM_" + name.upper()]
        sc.camera = cam
        t1 = time.time()
        sc.render.filepath = f"{a.out}_{name}.png"
        bpy.ops.render.render(write_still=True)
        print("RENDER", name, "%.1fs" % (time.time() - t1))
    if a.hero:
        sc.camera = cams["CAM_HERO"]
        if a.stage >= 4:
            hf = district.hero_frame(cams["CAM_HERO"])
            sc.frame_set(hf)
            print("HERO_FRAME", hf)
        sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
        sc.cycles.samples = a.hero_samples
        sc.render.filepath = f"{a.out}_hero.png"
        t1 = time.time()
        bpy.ops.render.render(write_still=True)
        print("RENDER hero %.1fs" % (time.time() - t1))


main()
