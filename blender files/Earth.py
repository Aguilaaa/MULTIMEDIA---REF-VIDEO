import bpy
import math

# Clear existing objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Create a UV sphere for Earth
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=64, ring_count=32)
earth = bpy.context.active_object
earth.name = "Earth"

# Add subdivision surface modifier
earth.modifiers.new(name="Subdivision", type='SUBSURF')
earth.modifiers["Subdivision"].levels = 2
earth.modifiers["Subdivision"].render_levels = 3

# Create material and assign texture
texture_path = r"D:\Solar System 3D Rendering Files\solarsystem_textures\2k_earth_daymap.jpg" # Update with your Earth texture path
mat = bpy.data.materials.new(name="Earth_Material")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get('Principled BSDF')
tex_image = mat.node_tree.nodes.new('ShaderNodeTexImage')
tex_image.image = bpy.data.images.load(texture_path)

# Connect nodes
mat.node_tree.links.new(bsdf.inputs['Base Color'], tex_image.outputs['Color'])

# Add Earth-specific material properties
if 'Metallic' in bsdf.inputs:
    bsdf.inputs['Metallic'].default_value = 0.0  # Earth is less metallic
if 'Roughness' in bsdf.inputs:
    bsdf.inputs['Roughness'].default_value = 0.5  # More roughness for natural surface
if 'Specular' in bsdf.inputs:
    bsdf.inputs['Specular'].default_value = 0.2  # Lower specularity
if 'IOR' in bsdf.inputs:
    bsdf.inputs['IOR'].default_value = 1.33  # Closer to water's IOR

# Assign material
if earth.data.materials:
    earth.data.materials[0] = mat
else:
    earth.data.materials.append(mat)

# Set up animation (10 seconds at 24 fps = 240 frames)
bpy.context.scene.frame_start = 0
bpy.context.scene.frame_end = 120
bpy.context.scene.render.fps = 24

# Earth rotates once every 24 hours - we'll show one full rotation in 10 seconds
earth.rotation_euler = (0, 0, 0)
earth.keyframe_insert(data_path="rotation_euler", frame=0)
earth.rotation_euler = (0, 0, math.pi * 2)
earth.keyframe_insert(data_path="rotation_euler", frame=240)

# Linear interpolation
if earth.animation_data and earth.animation_data.action:
    action = earth.animation_data.action
    try:
        for layer in action.layers:
            for strip in layer.strips:
                for channelbag in strip.channelbags:
                    for fcurve in channelbag.fcurves:
                        for kp in fcurve.keyframe_points:
                            kp.interpolation = 'LINEAR'
    except Exception as e:
        print(f"Interpolation skipped: {e}")

# Set up camera for full planet view
bpy.ops.object.camera_add(location=(0, -4, 0))
camera = bpy.context.active_object
camera.rotation_euler = (math.pi/2, 0, 0)
bpy.context.scene.camera = camera

# Adjust camera lens to fit entire planet in frame
camera.data.lens = 35

# Add lighting - sunlight
bpy.ops.object.light_add(type='SUN', location=(3, -3, 4))
sun = bpy.context.active_object
sun.data.energy = 3.0
sun.rotation_euler = (math.radians(45), math.radians(30), 0)

# Add fill light
bpy.ops.object.light_add(type='SUN', location=(-2, -2, -2))
fill_light = bpy.context.active_object
fill_light.data.energy = 1.0
fill_light.rotation_euler = (math.radians(-45), math.radians(-30), 0)

# Set background to simulate space
world = bpy.context.scene.world
if not world:
    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world

world.use_nodes = True
bg = world.node_tree.nodes.get('Background')
bg.inputs['Color'].default_value = (0.01, 0.01, 0.05, 1)  # Dark blue-black space
bg.inputs['Strength'].default_value = 0.1

# Add stars (optional)
try:
    stars_texture_path = r"D:\Solar System 3D Rendering Files\solarsystem_textures\2k_stars.jpg"  # Update path
    env_tex = world.node_tree.nodes.new('ShaderNodeTexEnvironment')
    env_tex.image = bpy.data.images.load(stars_texture_path)
    bg = world.node_tree.nodes.get('Background')
    world.node_tree.links.new(bg.inputs['Color'], env_tex.outputs['Color'])
except:
    print("Stars texture not found, using plain background")

# Set render settings
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.samples = 64
bpy.context.scene.render.resolution_x = 1280
bpy.context.scene.render.resolution_y = 720
bpy.context.scene.render.film_transparent = False

print("Earth planet animation setup complete!")