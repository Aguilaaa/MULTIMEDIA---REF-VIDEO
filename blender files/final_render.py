import bpy
import math
import os
import random
# ============================================================
# CONFIGURATION
# ============================================================
TEXTURE_DIR = r"C:\tex_img"
RENDER_ENGINE = "CYCLES"   # or "BLENDER_EEVEE"
RESOLUTION_X = 1920
RESOLUTION_Y = 1080
FRAME_START = 1
FRAME_END = 1500
USE_BLOOM = True
USE_MOTION_BLUR = False

def get_texture_path(filename):
    return os.path.join(TEXTURE_DIR, filename)

def planet_texture(pname):
    return get_texture_path(f"{pname.lower()}.jpg")

# ----- Satellite (ISS-style) config -----
SATELLITE_BLEND_PATH          = os.path.join(TEXTURE_DIR, "satelite.blend")
SATELLITE_INCLINATION_DEG     = 51.6
SATELLITE_ORBIT_RADIUS_MULT   = 1.4   # multiplier of earth_r — local to Earth object
# FIX: was 0.06 * earth_r = 0.018 units — completely invisible at camera distances.
# Camera Earth shots sit ~2.1 units from Earth; satellite needs to be at least 0.05+.
# 0.5 * earth_r = 0.15 units — clearly visible without being absurdly giant.
SATELLITE_SCALE_MULT          = 0.5
SATELLITE_ORBIT_PERIOD_FRAMES = 90

# ============================================================
# SECTION 1 - SCENE SETUP
# ============================================================
def initialize_scene():
    for obj in bpy.data.objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat, do_unlink=True)
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col)

    scene = bpy.context.scene
    scene.frame_start = FRAME_START
    scene.frame_end   = FRAME_END
    scene.render.engine = RENDER_ENGINE
    scene.render.resolution_x = RESOLUTION_X
    scene.render.resolution_y = RESOLUTION_Y
    scene.render.film_transparent = False

    if RENDER_ENGINE == "BLENDER_EEVEE":
        eevee = scene.eevee
        eevee.use_bloom = USE_BLOOM
        eevee.bloom_intensity = 0.5
        eevee.bloom_threshold = 0.8
        eevee.bloom_radius = 6.0
        eevee.use_ssr = True
        eevee.use_soft_shadows = True
        eevee.shadow_cube_size = '1024'
        eevee.taa_render_samples = 64
        if USE_MOTION_BLUR:
            eevee.use_motion_blur = True
    else:
        cycles = scene.cycles
        cycles.samples = 128
        if USE_MOTION_BLUR:
            scene.render.use_motion_blur = True
        if USE_BLOOM:
            scene.use_nodes = True
            tree = scene.node_tree
            tree.nodes.clear()
            rlayers = tree.nodes.new(type='CompositorNodeRLayers')
            rlayers.location = (0, 0)
            glare = tree.nodes.new(type='CompositorNodeGlare')
            glare.location = (300, 0)
            glare.glare_type = 'FOG_GLOW'
            glare.quality = 'HIGH'
            glare.threshold = 0.8
            glare.size = 9
            comp = tree.nodes.new(type='CompositorNodeComposite')
            comp.location = (600, 0)
            tree.links.new(rlayers.outputs['Image'], glare.inputs['Image'])
            tree.links.new(glare.outputs['Image'], comp.inputs['Image'])

    world = bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    wnt = world.node_tree
    wnt.nodes.clear()

    bg_node  = wnt.nodes.new("ShaderNodeBackground")
    out_node = wnt.nodes.new("ShaderNodeOutputWorld")
    out_node.location = (300, 0)

    noise = wnt.nodes.new("ShaderNodeTexNoise")
    noise.location = (-600, 200)
    noise.inputs["Scale"].default_value = 1.2
    noise.inputs["Detail"].default_value = 15.0
    noise.inputs["Roughness"].default_value = 0.55

    ramp = wnt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (-400, 200)
    ramp.color_ramp.elements[0].position = 0.4
    ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ramp.color_ramp.elements[1].position = 0.6
    ramp.color_ramp.elements[1].color = (0.05, 0.005, 0.01, 1.0)
    ramp.color_ramp.elements.new(0.85)
    ramp.color_ramp.elements[2].color = (0.15, 0.05, 0.01, 1.0)
    wnt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])

    stars_path = get_texture_path("stars.jpg")
    mix_node = wnt.nodes.new("ShaderNodeMixRGB")
    mix_node.blend_type = 'ADD'
    mix_node.inputs[0].default_value = 1.0
    mix_node.location = (-150, 0)

    if os.path.exists(stars_path):
        tex_coord = wnt.nodes.new("ShaderNodeTexCoord")
        mapping    = wnt.nodes.new("ShaderNodeMapping")
        img_node   = wnt.nodes.new("ShaderNodeTexEnvironment")
        tex_coord.location  = (-800, -200)
        mapping.location    = (-600, -200)
        img_node.location   = (-400, -200)
        try:
            img_node.image = bpy.data.images.load(stars_path)
        except Exception:
            pass
        wnt.links.new(tex_coord.outputs["Generated"], mapping.inputs["Vector"])
        wnt.links.new(mapping.outputs["Vector"],      img_node.inputs["Vector"])
        wnt.links.new(img_node.outputs["Color"], mix_node.inputs[1])
    else:
        mix_node.inputs[1].default_value = (0.0, 0.0, 0.0, 1.0)

    wnt.links.new(ramp.outputs["Color"], mix_node.inputs[2])
    wnt.links.new(mix_node.outputs["Color"], bg_node.inputs["Color"])
    bg_node.inputs["Strength"].default_value = 0.5
    wnt.links.new(bg_node.outputs["Background"], out_node.inputs["Surface"])
    return scene

# ============================================================
# SECTION 2 - MATERIAL HELPERS
# ============================================================
def create_textured_material(name, texture_path, emission_color=None,
                               emission_strength=0.0, roughness=0.8,
                               metallic=0.0, alpha=1.0, blend_mode=None, bump_path=None):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out   = nodes.new("ShaderNodeOutputMaterial"); out.location = (600, 0)
    bsdf  = nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (200, 0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value  = metallic

    if texture_path and os.path.exists(texture_path):
        coord = nodes.new("ShaderNodeTexCoord"); coord.location = (-600, 0)
        uvmap = nodes.new("ShaderNodeMapping");  uvmap.location = (-400, 0)
        img   = nodes.new("ShaderNodeTexImage"); img.location   = (-150, 50)
        try:
            img.image = bpy.data.images.load(texture_path, check_existing=True)
        except Exception:
            pass
        links.new(coord.outputs["UV"],     uvmap.inputs["Vector"])
        links.new(uvmap.outputs["Vector"], img.inputs["Vector"])
        links.new(img.outputs["Color"],    bsdf.inputs["Base Color"])
        if alpha < 1.0:
            links.new(img.outputs["Alpha"], bsdf.inputs["Alpha"])
            mat.blend_method  = blend_mode or "BLEND"
            mat.shadow_method = "CLIP"

    if bump_path and os.path.exists(bump_path):
        if 'coord' not in dir():
            coord = nodes.new("ShaderNodeTexCoord"); coord.location = (-600, 0)
            uvmap = nodes.new("ShaderNodeMapping");  uvmap.location = (-400, 0)
        bump_img  = nodes.new("ShaderNodeTexImage"); bump_img.location  = (-150, -250)
        bump_node = nodes.new("ShaderNodeBump");     bump_node.location = (50, -250)
        try:
            bump_img.image = bpy.data.images.load(bump_path, check_existing=True)
            bump_img.image.colorspace_settings.name = 'Non-Color'
        except Exception:
            pass
        links.new(uvmap.outputs["Vector"],    bump_img.inputs["Vector"])
        links.new(bump_img.outputs["Color"],  bump_node.inputs["Height"])
        links.new(bump_node.outputs["Normal"],bsdf.inputs["Normal"])
        bump_node.inputs["Distance"].default_value = 0.2

    if emission_color and emission_strength > 0:
        bsdf.inputs["Emission Color"].default_value    = (*emission_color, 1)
        bsdf.inputs["Emission Strength"].default_value = emission_strength

    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat

def create_sun_material():
    mat   = bpy.data.materials.new(name="Sun_Mat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out  = nodes.new("ShaderNodeOutputMaterial"); out.location  = (600, 0)
    emit = nodes.new("ShaderNodeEmission");        emit.location = (200, 0)
    emit.inputs["Strength"].default_value = 15.0
    emit.inputs["Color"].default_value    = (1.0, 0.35, 0.02, 1.0)
    tex_path = get_texture_path("sun.jpg")
    if os.path.exists(tex_path):
        coord = nodes.new("ShaderNodeTexCoord"); coord.location = (-600, 0)
        uvmap = nodes.new("ShaderNodeMapping");  uvmap.location = (-400, 0)
        img   = nodes.new("ShaderNodeTexImage"); img.location   = (-150, 0)
        try:
            img.image = bpy.data.images.load(tex_path, check_existing=True)
        except Exception:
            pass
        mix = nodes.new("ShaderNodeMixRGB"); mix.location = (-10, 100)
        mix.blend_type = 'MULTIPLY'
        mix.inputs["Fac"].default_value = 0.6
        mix.inputs["Color2"].default_value = (1.0, 0.75, 0.2, 1.0)
        links.new(coord.outputs["UV"],     uvmap.inputs["Vector"])
        links.new(uvmap.outputs["Vector"], img.inputs["Vector"])
        links.new(img.outputs["Color"],    mix.inputs["Color1"])
        links.new(mix.outputs["Color"],    emit.inputs["Color"])
    links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat

def create_atmosphere_material():
    mat   = bpy.data.materials.new(name="Earth_Atmo")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out   = nodes.new("ShaderNodeOutputMaterial"); out.location  = (600, 0)
    trans = nodes.new("ShaderNodeBsdfTransparent"); trans.location = (-100, 100)
    emit  = nodes.new("ShaderNodeEmission");         emit.location  = (-100, -50)
    emit.inputs["Color"].default_value    = (0.2, 0.5, 1.0, 1.0)
    emit.inputs["Strength"].default_value = 0.3
    fac = nodes.new("ShaderNodeLayerWeight"); fac.location = (-300, 0)
    fac.inputs["Blend"].default_value = 0.45
    mix = nodes.new("ShaderNodeMixShader"); mix.location = (400, 0)
    links.new(fac.outputs["Facing"],    mix.inputs["Fac"])
    links.new(trans.outputs["BSDF"],    mix.inputs[1])
    links.new(emit.outputs["Emission"], mix.inputs[2])
    links.new(mix.outputs["Shader"],    out.inputs["Surface"])
    mat.blend_method  = "BLEND"
    mat.shadow_method = "NONE"
    return mat

def create_ring_material(ring_texture=None):
    mat   = bpy.data.materials.new(name="Ring_Mat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out  = nodes.new("ShaderNodeOutputMaterial"); out.location  = (600, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (200, 0)
    bsdf.inputs["Roughness"].default_value = 0.9
    bsdf.inputs["Alpha"].default_value     = 0.55
    mat.blend_method  = "BLEND"
    mat.shadow_method = "NONE"
    if ring_texture and os.path.exists(ring_texture):
        coord = nodes.new("ShaderNodeTexCoord"); coord.location = (-600, 0)
        img   = nodes.new("ShaderNodeTexImage"); img.location   = (-150, 50)
        bw    = nodes.new("ShaderNodeRGBToBW");  bw.location    = (50, -50)
        try:
            img.image = bpy.data.images.load(ring_texture, check_existing=True)
        except Exception:
            pass
        links.new(coord.outputs["UV"],  img.inputs["Vector"])
        links.new(img.outputs["Color"], bsdf.inputs["Base Color"])
        links.new(img.outputs["Color"], bw.inputs["Color"])
        links.new(bw.outputs["Val"],    bsdf.inputs["Alpha"])
    else:
        bsdf.inputs["Base Color"].default_value = (0.85, 0.78, 0.65, 1.0)
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat

# ============================================================
# SECTION 3 - OBJECT HELPERS
# ============================================================
def create_sphere(name, radius, location=(0, 0, 0), segments=64, rings=32):
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=radius, location=location, segments=segments, ring_count=rings)
    obj = bpy.context.active_object
    obj.name = name
    bpy.ops.object.shade_smooth()
    return obj

def create_disc(name, radius, location=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=128, radius=radius, depth=0.001,
        location=location, rotation=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = name
    bpy.ops.object.shade_smooth()
    return obj

def spawn_empty(name, location=(0, 0, 0)):
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=location)
    obj = bpy.context.active_object
    obj.name = name
    return obj

def create_point_light(name, location, energy, radius=0.5, color=(1, 0.9, 0.7)):
    bpy.ops.object.light_add(type='POINT', location=location)
    light = bpy.context.active_object
    light.name = name
    light.data.energy           = energy
    light.data.color            = color
    light.data.shadow_soft_size = radius
    return light

def apply_material(obj, mat):
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

# ============================================================
# SECTION 4 - PLANET DEFINITIONS
# ============================================================
PLANET_DATA = [
    ("Mercury", 0.11,  12,     88,   58,  0.03,  (0.6, 0.5, 0.45, 1)),
    ("Venus",   0.28,  18,    225,  243,  177.4, (0.9, 0.8, 0.5,  1)),
    ("Earth",   0.30,  25,    365,    1,   23.4, (0.2, 0.5, 0.9,  1)),
    ("Mars",    0.16,  34,    687,   1.03, 25.2, (0.8, 0.4, 0.2,  1)),
    ("Jupiter", 3.36,  55,   4333,   0.41, 3.1,  (0.8, 0.7, 0.55, 1)),
    ("Saturn",  2.83,  80,  10759,   0.45, 26.7, (0.9, 0.85, 0.6, 1)),
    ("Uranus",  1.20, 105,  30688,   0.72, 97.8, (0.5, 0.85, 0.9, 1)),
    ("Neptune", 1.16, 125,  60182,   0.67, 28.3, (0.2, 0.4, 0.9,  1)),
    ("Pluto",   0.05, 150,  90560,   6.39, 122.5, (0.6, 0.5, 0.4,  1)),
]

SUN_RADIUS = 8.0
SPEED_SCALE = 1.5

# ============================================================
# SECTION 5 - BUILD SOLAR SYSTEM
# ============================================================
def construct_solar_system():
    planets = {}

    sun_obj = create_sphere("Sun", SUN_RADIUS)
    sun_mat = create_sun_material()
    apply_material(sun_obj, sun_mat)
    sun_obj.visible_shadow = False

    sun_light = create_point_light("SunLight", (0, 0, 0), energy=150000,
                                   radius=SUN_RADIUS, color=(1.0, 0.95, 0.9))
    sun_light.data.use_shadow = False
    sun_light.data.use_custom_distance = True
    sun_light.data.cutoff_distance     = 600.0

    bpy.ops.object.light_add(type='SUN', rotation=(math.radians(45), math.radians(45), 0))
    fill = bpy.context.active_object
    fill.name = "AmbientFill"
    fill.data.energy = 0.01
    fill.data.color  = (0.3, 0.35, 0.5)
    fill.data.use_shadow = False

    bpy.ops.object.light_add(type='SUN', rotation=(math.radians(-45), math.radians(-135), 0))
    fill2 = bpy.context.active_object
    fill2.name = "AmbientFill2"
    fill2.data.energy = 0.03
    fill2.data.color  = (0.7, 0.8, 1.0)
    fill2.data.use_shadow = False

    for (pname, prad, orbit_r, orb_period, rot_period, axial_tilt, base_color) in PLANET_DATA:
        pivot  = spawn_empty(f"{pname}_Pivot")
        planet = create_sphere(pname, prad, location=(orbit_r, 0, 0))
        planet.parent = pivot
        planet.rotation_euler.x = math.radians(axial_tilt)

        tpath = planet_texture(pname)
        bpath = get_texture_path("pluto_bump.jpg") if pname == "Pluto" else None
        mat = create_textured_material(f"{pname}_Mat", tpath,
                                       roughness=0.85, metallic=0.0, bump_path=bpath)
        if not os.path.exists(tpath):
            mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = base_color
        apply_material(planet, mat)

        planets[pname] = {"pivot": pivot, "planet": planet, "orbit_r": orbit_r, "radius": prad}

    # Saturn rings
    saturn_info = planets["Saturn"]
    sat_obj = saturn_info["planet"]
    sat_r   = saturn_info["radius"]
    ring_tex_path = get_texture_path("saturn_ring.jpg")
    ring = create_disc("Saturn_Ring", radius=sat_r * 2.2, location=(0, 0, 0))
    ring.parent = sat_obj
    ring_mat = create_ring_material(ring_tex_path if os.path.exists(ring_tex_path) else None)
    apply_material(ring, ring_mat)

    # Earth moon
    earth_info = planets["Earth"]
    earth_obj  = earth_info["planet"]
    earth_r    = earth_info["radius"]
    moon_obj = create_sphere("Moon", earth_r * 0.27, location=(earth_r * 3.0, 0, 0))
    moon_obj.parent = earth_obj
    moon_mat = create_textured_material("Moon_Mat", get_texture_path("moon.jpg"),
                                        roughness=0.9, metallic=0.0)
    apply_material(moon_obj, moon_mat)

    # Jupiter moons
    jup_obj = planets["Jupiter"]["planet"]
    jup_r   = planets["Jupiter"]["radius"]
    for i, (m_name, m_rad, m_dist, m_tex) in enumerate([
        ("Io",       jup_r * 0.025, jup_r * 1.5, "io.jpg"),
        ("Europa",   jup_r * 0.020, jup_r * 2.0, "europa.jpg"),
        ("Ganymede", jup_r * 0.035, jup_r * 2.6, "ganymede.jpg"),
        ("Callisto", jup_r * 0.032, jup_r * 3.3, "callisto.jpg"),
    ]):
        angle = i * (math.pi / 2)
        m_obj = create_sphere(m_name, m_rad,
                              location=(m_dist * math.cos(angle), m_dist * math.sin(angle), 0))
        m_obj.parent = jup_obj
        m_mat = create_textured_material(f"{m_name}_Mat", get_texture_path(m_tex),
                                         roughness=0.9, metallic=0.0)
        apply_material(m_obj, m_mat)

    return planets

# ============================================================
# SECTION 5b - ORBIT LINES
# ============================================================
def draw_orbit_paths():
    mat = bpy.data.materials.new("Orbit_Line_Mat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out  = nodes.new("ShaderNodeOutputMaterial"); out.location  = (400, 0)
    emit = nodes.new("ShaderNodeEmission");        emit.location = (100, 0)
    emit.inputs["Color"].default_value    = (0.4, 0.6, 1.0, 1.0)
    emit.inputs["Strength"].default_value = 0.7
    trans = nodes.new("ShaderNodeBsdfTransparent"); trans.location = (100, 100)
    mix   = nodes.new("ShaderNodeMixShader");        mix.location   = (250, 50)
    mix.inputs[0].default_value = 1.0
    links.new(trans.outputs["BSDF"],      mix.inputs[1])
    links.new(emit.outputs["Emission"],   mix.inputs[2])
    links.new(mix.outputs["Shader"],      out.inputs["Surface"])
    mat.blend_method  = "BLEND"
    mat.shadow_method = "NONE"

    for (pname, prad, orbit_r, *_rest) in PLANET_DATA:
        ORBIT_SEGMENTS = 256
        curve_data = bpy.data.curves.new(name=f"Orbit_{pname}", type='CURVE')
        curve_data.dimensions          = '3D'
        curve_data.resolution_u        = 12
        curve_data.render_resolution_u = 24
        curve_data.bevel_depth         = 0.014
        curve_data.use_fill_caps       = True
        spline = curve_data.splines.new('POLY')
        spline.use_cyclic_u = True
        spline.points.add(ORBIT_SEGMENTS - 1)
        for i, pt in enumerate(spline.points):
            angle = (2 * math.pi * i) / ORBIT_SEGMENTS
            pt.co = (orbit_r * math.cos(angle), orbit_r * math.sin(angle), 0.0, 1.0)
        orbit_obj = bpy.data.objects.new(f"Orbit_{pname}", curve_data)
        bpy.context.collection.objects.link(orbit_obj)
        orbit_obj.data.materials.append(mat)

# ============================================================
# SECTION 5c - SCATTERED ASTEROIDS
# ============================================================
def scatter_asteroids():
    field_root = spawn_empty("AsteroidField_Root")
    ast_mat = bpy.data.materials.new("Asteroid_Mat")
    ast_mat.use_nodes = True
    nodes = ast_mat.node_tree.nodes
    links = ast_mat.node_tree.links
    nodes.clear()
    out  = nodes.new("ShaderNodeOutputMaterial"); out.location  = (600, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (200, 0)
    bsdf.inputs["Roughness"].default_value = 0.97
    bsdf.inputs["Metallic"].default_value  = 0.0
    ast_tex_path = get_texture_path("asteroid.jpg")
    if os.path.exists(ast_tex_path):
        coord = nodes.new("ShaderNodeTexCoord"); coord.location = (-600, 0)
        uvmap = nodes.new("ShaderNodeMapping");  uvmap.location = (-400, 0)
        img   = nodes.new("ShaderNodeTexImage"); img.location   = (-150, 50)
        try:
            img.image = bpy.data.images.load(ast_tex_path, check_existing=True)
        except Exception:
            pass
        noise = nodes.new("ShaderNodeTexNoise"); noise.location = (-600, -250)
        noise.inputs["Scale"].default_value = 8.0
        tint_ramp = nodes.new("ShaderNodeValToRGB"); tint_ramp.location = (-400, -250)
        tint_ramp.color_ramp.elements[0].color = (0.75, 0.75, 0.75, 1.0)
        tint_ramp.color_ramp.elements[1].color = (1.1,  1.05, 1.0,  1.0)
        tint_mix = nodes.new("ShaderNodeMixRGB"); tint_mix.location = (-150, -150)
        tint_mix.blend_type = 'MULTIPLY'
        tint_mix.inputs["Fac"].default_value = 0.8
        links.new(coord.outputs["UV"],           uvmap.inputs["Vector"])
        links.new(uvmap.outputs["Vector"],        img.inputs["Vector"])
        links.new(noise.outputs["Fac"],           tint_ramp.inputs["Fac"])
        links.new(img.outputs["Color"],           tint_mix.inputs["Color1"])
        links.new(tint_ramp.outputs["Color"],     tint_mix.inputs["Color2"])
        links.new(tint_mix.outputs["Color"],      bsdf.inputs["Base Color"])
    else:
        bsdf.inputs["Base Color"].default_value = (0.30, 0.27, 0.24, 1.0)
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    asteroids = []
    for i in range(60):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.7)
        ast = bpy.context.active_object
        ast.name = f"Asteroid_{i:02d}"
        ast.scale = (random.uniform(0.5, 1.6), random.uniform(0.5, 1.6), random.uniform(0.4, 1.3))
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        for v in ast.data.vertices:
            j = 1.0 + random.uniform(-0.35, 0.35)
            v.co.x *= j; v.co.y *= j
            v.co.z *= j * (1.0 + random.uniform(-0.2, 0.2))
        bpy.ops.object.shade_flat()
        apply_material(ast, ast_mat)
        r  = random.uniform(20.0, 170.0)
        a  = random.uniform(0, 2 * math.pi)
        h  = random.uniform(-25.0, 25.0)
        ast.location = (r * math.cos(a), r * math.sin(a), h)
        s = random.uniform(0.6, 2.4)
        ast.scale = (s, s, s)
        ast.rotation_euler = (random.uniform(0, math.pi*2),
                              random.uniform(0, math.pi*2),
                              random.uniform(0, math.pi*2))
        ast.parent = field_root
        asteroids.append(ast)

    for ast in asteroids:
        start_rot = tuple(ast.rotation_euler)
        ast.keyframe_insert(data_path="rotation_euler", frame=1)
        end_rot = list(start_rot)
        axis_idx = {'x':0,'y':1,'z':2}[random.choice(['x','y','z'])]
        end_rot[axis_idx] += math.radians(random.uniform(40, 160))
        ast.rotation_euler = tuple(end_rot)
        ast.keyframe_insert(data_path="rotation_euler", frame=FRAME_END)
        start_loc = tuple(ast.location)
        ast.keyframe_insert(data_path="location", frame=1)
        ast.location = (start_loc[0] + random.uniform(-6,6),
                        start_loc[1] + random.uniform(-6,6),
                        start_loc[2] + random.uniform(-3,3))
        ast.keyframe_insert(data_path="location", frame=FRAME_END)
        if ast.animation_data and ast.animation_data.action:
            for fc in ast.animation_data.action.fcurves:
                for kf in fc.keyframe_points:
                    kf.interpolation = 'LINEAR'

    print(f"  -> Scattered 60 asteroids")
    return field_root

# ============================================================
# SECTION 5d - EARTH SATELLITE (ISS-style)  *** FULLY REWRITTEN ***
# ============================================================
def add_earth_satellite(planets):
    """
    Correct parent chain:
      Earth_Pivot  (solar orbit Z animation)
        -> Earth   (planet mesh, spin animation)
           -> Satellite_OrbitPivot  (static X inclination, animated Z revolution)
              -> Satellite_Root     (local location = (orbit_radius,0,0), local scale)

    WHY THIS FIXES VISIBILITY:
    Bug 1 — Wrong parent: old code parented orbit_pivot to earth_pivot (the
      Sun-orbit empty). Earth_Pivot sits at the Sun's origin. The satellite
      was circling (0,0,0) in Sun-space, which is deep inside the Sun — invisible.
      FIX: parent orbit_pivot to earth_obj (the planet mesh itself), so the
      satellite orbits Earth's actual position as Earth travels around the Sun.

    Bug 2 — Microscopic scale: SATELLITE_SCALE_MULT 0.06 * earth_r 0.30 = 0.018
      Blender units. Camera Earth shots sit ~2.1 units from Earth — the satellite
      was sub-pixel sized.
      FIX: SATELLITE_SCALE_MULT raised to 0.5 → scale = 0.15 units. Clearly visible.

    Bug 3 — Wrong location strategy: old code set sat_root.location in world
      space before parenting. With earth_obj at world position (25,0,0) at frame 1
      and orbit_radius=0.42, the resulting local position was nearly (0,0,0).
      FIX: set location AFTER parenting so it is in local space relative to
      orbit_pivot, which is itself local to Earth. (orbit_radius, 0, 0) in that
      local frame places the satellite correctly in Earth orbit.

    Bug 4 — matrix_parent_inverse.identity() (in the original): wiped the parent
      inverse, snapping the satellite to the pivot origin inside Earth.
      FIX: never call .identity() on parent_inverse after parenting.
    """
    if not os.path.exists(SATELLITE_BLEND_PATH):
        print(f"  -> [Satellite] SKIPPED — not found: {SATELLITE_BLEND_PATH}")
        return None

    earth_obj = planets["Earth"]["planet"]
    earth_r   = planets["Earth"]["radius"]

    orbit_radius = earth_r * SATELLITE_ORBIT_RADIUS_MULT   # local to Earth: ~0.42
    sat_scale    = earth_r * SATELLITE_SCALE_MULT           # 0.15 — visible

    # ------------------------------------------------------------------
    # 1. Append objects from satelite.blend
    # ------------------------------------------------------------------
    with bpy.data.libraries.load(SATELLITE_BLEND_PATH, link=False) as (data_from, data_to):
        data_to.objects = list(data_from.objects)
        print(f"  -> [Satellite] objects in .blend: {list(data_from.objects)}")

    imported = [o for o in data_to.objects if o is not None]
    if not imported:
        print("  -> [Satellite] No objects found in .blend — aborting")
        return None

    # Link all into scene, force every object visible
    for obj in imported:
        if obj.name not in bpy.context.scene.collection.objects:
            bpy.context.scene.collection.objects.link(obj)
        obj.hide_viewport = False
        obj.hide_render   = False
        try:
            obj.hide_set(False)
        except RuntimeError:
            pass

    # ------------------------------------------------------------------
    # 2. Find the root of the imported hierarchy
    # ------------------------------------------------------------------
    imported_names = {o.name for o in imported}
    roots = [o for o in imported
             if o.parent is None or o.parent.name not in imported_names]
    sat_root = (roots or imported)[0]
    sat_root.name = "Satellite_Root"
    print(f"  -> [Satellite] root='{sat_root.name}'  "
          f"children={[c.name for c in sat_root.children]}")

    # ------------------------------------------------------------------
    # 3. Build orbit rig — pivot parented to earth_obj (the planet mesh)
    #    FIX: was earth_pivot; must be earth_obj so it follows Earth's position
    # ------------------------------------------------------------------
    orbit_pivot = spawn_empty("Satellite_OrbitPivot")
    orbit_pivot.parent   = earth_obj          # <-- KEY FIX: earth_obj not earth_pivot
    orbit_pivot.location = (0.0, 0.0, 0.0)   # local to Earth: sit at Earth's centre

    # Static inclination on X — set once, never keyframed
    orbit_pivot.rotation_euler = (math.radians(SATELLITE_INCLINATION_DEG), 0.0, 0.0)

    # ------------------------------------------------------------------
    # 4. Parent satellite to orbit_pivot FIRST, then set local transforms
    #    FIX: location set AFTER parenting = local space relative to orbit_pivot
    #    Do NOT call matrix_parent_inverse.identity() — that breaks the offset
    # ------------------------------------------------------------------
    sat_root.parent = orbit_pivot
    # Now set in LOCAL space (relative to orbit_pivot / Earth):
    sat_root.location = (orbit_radius, 0.0, 0.0)
    sat_root.scale    = (sat_scale, sat_scale, sat_scale)

    # ------------------------------------------------------------------
    # 5. Animate only the Z (revolution) channel on orbit_pivot
    # ------------------------------------------------------------------
    orbit_pivot.rotation_euler.z = 0.0
    orbit_pivot.keyframe_insert(data_path="rotation_euler", frame=1, index=2)

    n_orbits = (FRAME_END - 1) / SATELLITE_ORBIT_PERIOD_FRAMES
    orbit_pivot.rotation_euler.z = math.radians(360.0 * n_orbits)
    orbit_pivot.keyframe_insert(data_path="rotation_euler", frame=FRAME_END, index=2)

    if orbit_pivot.animation_data and orbit_pivot.animation_data.action:
        for fc in orbit_pivot.animation_data.action.fcurves:
            for kf in fc.keyframe_points:
                kf.interpolation = 'LINEAR'

    # ------------------------------------------------------------------
    # 6. Debug report
    # ------------------------------------------------------------------
    bpy.context.view_layer.update()
    wp = sat_root.matrix_world.translation
    print(f"  -> [Satellite] orbit_radius(local)={orbit_radius:.3f}  "
          f"scale={sat_scale:.4f}  inclination={SATELLITE_INCLINATION_DEG}°")
    print(f"  -> [Satellite] world_pos at frame1=({wp.x:.2f},{wp.y:.2f},{wp.z:.2f})  "
          f"dims={tuple(round(d,3) for d in sat_root.dimensions)}")
    return sat_root

# ============================================================
# SECTION 6 - ANIMATION
# ============================================================
def animate_orbits_and_spins(planets):
    bpy.context.scene.frame_set(1)

    for (pname, prad, orbit_r, orb_period, rot_period, axial_tilt, base_color) in PLANET_DATA:
        pivot  = planets[pname]["pivot"]
        planet = planets[pname]["planet"]

        deg_per_frame = 360.0 / (orb_period / SPEED_SCALE)
        pivot.rotation_euler = (0, 0, 0)
        pivot.keyframe_insert(data_path="rotation_euler", frame=1)
        pivot.rotation_euler.z = math.radians(deg_per_frame * FRAME_END)
        pivot.keyframe_insert(data_path="rotation_euler", frame=FRAME_END)
        for fc in pivot.animation_data.action.fcurves:
            for kf in fc.keyframe_points:
                kf.interpolation = 'LINEAR'

        planet.rotation_euler = (math.radians(axial_tilt), 0, 0)
        planet.keyframe_insert(data_path="rotation_euler", frame=1)
        planet.rotation_euler = (math.radians(axial_tilt), 0,
                                 math.radians(0.5 * FRAME_END))
        planet.keyframe_insert(data_path="rotation_euler", frame=FRAME_END)
        for fc in planet.animation_data.action.fcurves:
            for kf in fc.keyframe_points:
                kf.interpolation = 'LINEAR'

    sun = bpy.data.objects.get("Sun")
    if sun:
        sun.rotation_euler.z = 0
        sun.keyframe_insert(data_path="rotation_euler", frame=1)
        sun.rotation_euler.z = math.radians(360 * 2)
        sun.keyframe_insert(data_path="rotation_euler", frame=FRAME_END)
        for fc in sun.animation_data.action.fcurves:
            for kf in fc.keyframe_points:
                kf.interpolation = 'LINEAR'

# ============================================================
# SECTION 7 - PLANET LABELS
# ============================================================
def create_planet_labels(planets, cam_obj, blocks):
    label_objects = {}
    for (pname, prad, orbit_r, orb_period, rot_period, axial_tilt, base_color) in PLANET_DATA:
        planet = planets[pname]["planet"]
        pivot = planets[pname]["pivot"]

        label_prad = prad * 2.5 if pname == "Saturn" else prad

        billboard_rig = spawn_empty(f"LabelRig_{pname}", location=(orbit_r, 0, 0))
        billboard_rig.parent = pivot

        c_track = billboard_rig.constraints.new(type='TRACK_TO')
        c_track.target = cam_obj
        c_track.track_axis = 'TRACK_Z'
        c_track.up_axis = 'UP_Y'

        bpy.ops.object.text_add(location=(0, 0, 0))
        txt_obj = bpy.context.active_object
        txt_obj.name = f"Label_{pname}"
        txt_obj.parent = billboard_rig
        txt_obj.data.body = pname.upper()
        txt_obj.data.size = label_prad * 0.30
        txt_obj.data.align_x = 'CENTER'
        txt_obj.data.space_character = 1.8   # wide-tracked all-caps spacing
        txt_obj.data.space_word = 1.2
        txt_obj.location = (0, label_prad * 1.6, 0)

        # Font priority: sci-fi / geometric sans → clean condensed → system fallback
        font_candidates = [
            # Installed custom fonts
            "C:\\Windows\\Fonts\\Nasalization.ttf",
            "C:\\Windows\\Fonts\\nasalization-rg.ttf",
            "C:\\Windows\\Fonts\\Furore.otf",
            "C:\\Windows\\Fonts\\furore.otf",
            "C:\\Windows\\Fonts\\Rajdhani-Bold.ttf",
            "C:\\Windows\\Fonts\\rajdhanibold.ttf",
            # Common Windows system fonts (geometric / clean)
            "C:\\Windows\\Fonts\\censcbk.ttf",   # Century Gothic
            "C:\\Windows\\Fonts\\gothic.ttf",
            "C:\\Windows\\Fonts\\micross.ttf",   # Microsoft Sans Serif
            "C:\\Windows\\Fonts\\bahnschrift.ttf",  # Bahnschrift — best built-in geometric
            "C:\\Windows\\Fonts\\calibrib.ttf",
            "C:\\Windows\\Fonts\\trebucbd.ttf",
        ]
        font_path = None
        for candidate in font_candidates:
            if os.path.exists(candidate):
                font_path = candidate
                break

        if font_path:
            try:
                fnt = bpy.data.fonts.load(font_path)
                txt_obj.data.font = fnt
            except Exception:
                pass

        lmat = bpy.data.materials.new(f"Label_{pname}_Mat")
        lmat.use_nodes = True
        lmat.blend_method = 'BLEND'
        lmat.show_transparent_back = False
        ln = lmat.node_tree.nodes
        ll = lmat.node_tree.links
        ln.clear()

        lout = ln.new("ShaderNodeOutputMaterial")
        lout.location = (400, 0)

        lemit = ln.new("ShaderNodeEmission")
        lemit.location = (0, 0)
        lemit.inputs["Color"].default_value = (0.85, 0.92, 1.0, 1.0)
        lemit.inputs["Strength"].default_value = 3.0
        ltrans = ln.new("ShaderNodeBsdfTransparent")
        ltrans.location = (0, 100)

        lmix = ln.new("ShaderNodeMixShader")
        lmix.location = (200, 50)
        lmix.inputs[0].default_value = 0.0

        ll.new(ltrans.outputs["BSDF"], lmix.inputs[1])
        ll.new(lemit.outputs["Emission"], lmix.inputs[2])
        ll.new(lmix.outputs["Shader"], lout.inputs["Surface"])

        txt_obj.data.materials.append(lmat)
        label_objects[pname] = {"obj": txt_obj, "mix_node": lmix}

    for idx, (pname, b_start, b_end) in enumerate(blocks):
        trans_end = b_start if idx == 0 else b_start + 40
        showcase_start = trans_end
        showcase_end = b_end

        fade_in_start = showcase_start
        fade_in_end = showcase_start + 20
        fade_out_start = showcase_end - 20
        fade_out_end = showcase_end

        mix_node = label_objects[pname]["mix_node"]

        mix_node.inputs[0].default_value = 0.0
        mix_node.inputs[0].keyframe_insert(data_path="default_value", frame=1)
        mix_node.inputs[0].keyframe_insert(data_path="default_value", frame=fade_in_start)

        mix_node.inputs[0].default_value = 1.0
        mix_node.inputs[0].keyframe_insert(data_path="default_value", frame=fade_in_end)
        mix_node.inputs[0].keyframe_insert(data_path="default_value", frame=fade_out_start)

        mix_node.inputs[0].default_value = 0.0
        mix_node.inputs[0].keyframe_insert(data_path="default_value", frame=fade_out_end)

        if mix_node.id_data.animation_data and mix_node.id_data.animation_data.action:
            for fcurve in mix_node.id_data.animation_data.action.fcurves:
                for kf in fcurve.keyframe_points:
                    kf.interpolation = 'BEZIER'

    return label_objects

# ============================================================
# SECTION 8 - CAMERA SYSTEM
# ============================================================
def setup_cinematic_camera(planets):
    cam_target = spawn_empty("CameraTarget")
    cam_pivot  = spawn_empty("CameraPivot")

    bpy.ops.object.camera_add(location=(0, -300, 30))
    cam_obj = bpy.context.active_object
    cam_obj.name = "MainCamera"
    bpy.context.scene.camera = cam_obj
    cam_obj.parent = cam_pivot

    track = cam_obj.constraints.new(type='TRACK_TO')
    track.target     = cam_target
    track.track_axis = 'TRACK_NEGATIVE_Z'
    track.up_axis    = 'UP_Y'

    cam_obj.data.lens       = 35
    cam_obj.data.clip_start = 0.01
    cam_obj.data.clip_end   = 3000
    cam_obj.data.dof.use_dof = False
    cam_obj.rotation_euler.y = math.radians(2)

    sun_obj = bpy.data.objects.get("Sun")
    for obj in [cam_pivot, cam_target]:
        c = obj.constraints.new(type='COPY_LOCATION')
        c.target = sun_obj; c.name = "Copy_Sun"

    targets = ["Sun"] + [p[0] for p in PLANET_DATA]
    for t_name in targets:
        tgt = sun_obj if t_name == "Sun" else planets[t_name]["planet"]
        for obj in [cam_pivot, cam_target]:
            c = obj.constraints.new(type='COPY_LOCATION')
            c.target = tgt; c.name = f"Copy_{t_name}"; c.influence = 0.0

    def keyframe_lock(target_name, frame, influence):
        for obj in [cam_pivot, cam_target]:
            c = obj.constraints.get(f"Copy_{target_name}")
            if c:
                c.influence = influence
                c.keyframe_insert(data_path="influence", frame=frame)

    keyframe_lock("Sun", 1, 1.0)
    for p_name in [p[0] for p in PLANET_DATA]:
        keyframe_lock(p_name, 1, 0.0)

    cam_obj.location = (380, -250, 20);  cam_obj.keyframe_insert(data_path="location", frame=1)
    cam_obj.location = (120, -180,  5);  cam_obj.keyframe_insert(data_path="location", frame=80)
    cam_obj.location = (-160, -90, 35);  cam_obj.keyframe_insert(data_path="location", frame=200)
    cam_obj.location = (70, -230,  75);  cam_obj.keyframe_insert(data_path="location", frame=300)
    keyframe_lock("Sun", 300, 1.0); keyframe_lock("Sun", 301, 0.0)

    blocks = [
        ("Mercury", 300,  390),
        ("Venus",   390,  490),
        ("Earth",   490,  620),
        ("Mars",    620,  720),
        ("Jupiter", 720,  880),
        ("Saturn",  880, 1060),
        ("Uranus", 1060, 1160),
        ("Neptune",1160, 1270),
        ("Pluto",  1270, 1370),
    ]
    prev_target = "Sun"; prev_end = 300

    for idx, (pname, b_start, b_end) in enumerate(blocks):
        trans_end = b_start + 30; showcase_start = trans_end; showcase_end = b_end
        keyframe_lock(prev_target, trans_end,     1.0)
        keyframe_lock(prev_target, trans_end + 1, 0.0)
        keyframe_lock(pname, prev_end,        0.0)
        keyframe_lock(pname, trans_end,       1.0)
        keyframe_lock(pname, showcase_end,    1.0)

        prad = planets[pname]["radius"]
        r    = prad * 2.5 if pname == "Saturn" else prad

        paths = {
            "Mercury": ((r*2.31, -r*6.15, r*6.15),  (r*2.45, -r*7.36, r*1.96),  (-r*3.89, -r*2.33, r*7.77)),
            "Venus":   ((r*7.63, -r*2.86, -r*3.82), (0,      -r*5.12, r*6.15),  (-r*5.82, -r*6.66, r*1.66)),
            "Earth":   ((r*0.77, -r*7.69, r*4.61),  (r*6.28, -r*4.71, -r*1.57), (-r*2.73, -r*7.27, -r*4.55)),
            "Mars":    ((r*5.39, -r*7.19, r*0.45),  (-r*2.52,-r*7.56, r*0.76),  (r*2.29,  -r*6.87, r*5.34)),
            "Jupiter": ((-r*5.66,-r*6.79, r*1.7),   (r*2.14, -r*6.41, -r*4.28), (r*4.32,  -r*6.17, r*4.93)),
            "Saturn":  ((r*3.23, -r*6.45, -r*5.38), (r*1.94, -r*7.76, r*0.19),  (-r*2.8,  -r*7.01, r*4.9)),
            "Uranus":  ((r*8.58, -r*2.57, r*0.86),  (r*1.93, -r*6.74, -r*3.85), (-r*5.48, -r*4.57, r*5.48)),
            "Neptune": ((0,      -r*7.63, r*4.77),   (r*4.78, -r*6.37, r*0.8),   (-r*6.13, -r*5.36, r*3.83)),
            "Pluto":   ((-r*5.32,-r*6.96, r*2.05),  (r*4.04, -r*6.46, r*2.42),  (r*5.43,  -r*6.9, -r*1.97)),
        }
        p1, p2, p3 = paths.get(pname, ((-r*5,-r*8,r*4),(r*2,-r*3,r*1),(r*4,-r*6,r*2)))
        mid = (showcase_start + showcase_end) // 2
        cam_obj.location = p1; cam_obj.keyframe_insert(data_path="location", frame=showcase_start)
        cam_obj.location = p2; cam_obj.keyframe_insert(data_path="location", frame=mid)
        cam_obj.location = p3; cam_obj.keyframe_insert(data_path="location", frame=showcase_end)
        prev_target = pname; prev_end = showcase_end

    keyframe_lock(prev_target, 1400,     1.0)
    keyframe_lock(prev_target, 1401,     0.0)
    keyframe_lock("Sun", 1370, 0.0)
    keyframe_lock("Sun", 1400, 1.0)
    keyframe_lock("Sun", 1500, 1.0)
    cam_obj.location = (80,  -100,  60); cam_obj.keyframe_insert(data_path="location", frame=1400)
    cam_obj.location = (200, -280, 180); cam_obj.keyframe_insert(data_path="location", frame=1500)

    for obj in [cam_pivot, cam_target, cam_obj]:
        if obj.animation_data and obj.animation_data.action:
            for fc in obj.animation_data.action.fcurves:
                for kf in fc.keyframe_points:
                    kf.interpolation = 'BEZIER'

    if cam_obj.animation_data and cam_obj.animation_data.action:
        for fc in cam_obj.animation_data.action.fcurves:
            if fc.data_path == "location":
                mod = fc.modifiers.new(type='NOISE')
                mod.scale = 80.0; mod.strength = 0.15

    return cam_obj, blocks

# ============================================================
# MAIN
# ============================================================
def generate_animation():
    print("=== Solar System Generator ===")
    print("[1/5] Scene setup...")
    initialize_scene()
    print("[2/5] Planets + materials...")
    planets = construct_solar_system()
    print("[2b/5] Orbit lines...")
    draw_orbit_paths()
    print("[2c/5] Asteroids...")
    scatter_asteroids()
    print("[2d/5] Satellite...")
    add_earth_satellite(planets)
    print("[3/5] Orbit + spin animation...")
    animate_orbits_and_spins(planets)
    print("[4/5] Camera animation...")
    cam_obj, blocks = setup_cinematic_camera(planets)
    print("[5/5] Planet labels...")
    create_planet_labels(planets, cam_obj, blocks)
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    print("=== Done! ===")

generate_animation()