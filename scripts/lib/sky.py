"""World sky, sun, atmosphere volume, cameras, Cycles/Metal render settings."""
import math
import bpy
from mathutils import Vector
from . import layout as Lo

# sun: low, east-north-east, so the south facades sit in cool shadow and long tree shadows
# fall toward the reference camera (as in the reference frame).
SUN_ELEV = math.radians(24.0)
SUN_AZ = math.radians(38.0)  # measured from +X toward +Y (Blender), i.e. ENE


def sun_dir():
    return Vector((math.cos(SUN_ELEV) * math.cos(SUN_AZ), math.cos(SUN_ELEV) * math.sin(SUN_AZ), math.sin(SUN_ELEV)))


def world(strength=1.0):
    w = bpy.data.worlds.new("sky")
    bpy.context.scene.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "MULTIPLE_SCATTERING"
    sky.sun_disc = False
    sky.sun_elevation = SUN_ELEV
    # Blender sky rotation: 0 = sun toward +Y? sun_rotation is measured from +Y clockwise; map from our az
    sky.sun_rotation = math.pi / 2 - SUN_AZ
    sky.altitude = 50
    sky.air_density = 1.2
    sky.aerosol_density = 3.0
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 0.13 * strength
    # warm the sky slightly toward the reference's hazy apricot horizon
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs[0].default_value = 1.0
    mix.inputs[7].default_value = (1.0, 0.80, 0.62, 1)
    nt.links.new(sky.outputs[0], mix.inputs[6])
    nt.links.new(mix.outputs[2], bg.inputs["Color"])
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    return w


def sun(strength=5.0):
    d = bpy.data.lights.new("Sun", "SUN")
    d.energy = strength
    d.color = (1.0, 0.70, 0.44)
    d.angle = math.radians(1.2)
    ob = bpy.data.objects.new("Sun", d)
    bpy.context.scene.collection.objects.link(ob)
    s = sun_dir()
    ob.rotation_euler = s.to_track_quat("Z", "Y").to_euler()
    return ob


def fill_lights(coll_, positions):
    """Small warm point lights inside the lanterns."""
    for i, p in enumerate(positions):
        l = bpy.data.lights.new(f"lantern_light_{i}", "POINT")
        l.energy = 40
        l.color = (1.0, 0.66, 0.34)
        l.shadow_soft_size = 0.12
        ob = bpy.data.objects.new(l.name, l)
        ob.location = p
        coll_.objects.link(ob)


def atmosphere(coll_, density=0.0011):
    """Thin warm haze volume for aerial perspective and restrained light shafts."""
    me = bpy.data.meshes.new("haze")
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("atmosphere_volume", me)
    ob.location = (20, 30, 18)
    ob.scale = (360, 360, 40)
    coll_.objects.link(ob)
    m = bpy.data.materials.new("haze")
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Color"].default_value = (1.0, 0.86, 0.70, 1)
    vol.inputs["Density"].default_value = density
    vol.inputs["Anisotropy"].default_value = 0.55
    nt.links.new(vol.outputs[0], out.inputs["Volume"])
    me.materials.append(m)
    ob.visible_shadow = False
    ob["render_only"] = True
    return ob


def camera(name, loc, target, lens):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.sensor_width = 36
    cd.clip_start = 0.05
    cd.clip_end = 1500
    ob = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


def cameras():
    obs = {}
    for k, c in Lo.CAMERAS.items():
        obs[k] = camera(k, c["loc"], c["target"], c["lens"])
    bpy.context.scene.camera = obs["CAM_REF"]
    return obs


def render_settings(w=960, h=540, samples=64):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "METAL"
    # session-only: specialised-kernel background compiles hung Cycles once on this machine
    prefs.kernel_optimization_level = "OFF"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = d.type == "METAL"
    sc.cycles.device = "GPU"
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    sc.cycles.max_bounces = 6
    sc.cycles.diffuse_bounces = 3
    sc.cycles.glossy_bounces = 3
    sc.cycles.transmission_bounces = 6
    sc.cycles.volume_bounces = 0
    sc.cycles.transparent_max_bounces = 16
    sc.cycles.volume_step_rate = 4.0
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.cycles.blur_glossy = 1.0
    sc.render.resolution_x = w
    sc.render.resolution_y = h
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    sc.view_settings.exposure = 0.0
    sc.render.image_settings.file_format = "PNG"
    sc.frame_start = 1
    sc.frame_end = 720
    sc.render.fps = 24
