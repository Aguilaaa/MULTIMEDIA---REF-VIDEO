import bpy
import math

# Clear existing objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Create a UV sphere for Pluto
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=64, ring_count=32)
pluto = bpy.context.active_object
pluto.name = "Pluto"

# Add subdivision surface modifier
pluto.modifiers.new(name="Subdivision", type='SUBSURF')
pluto.modifiers["Subdivision"].levels = 2
pluto.modifiers["Subdivision"].render_levels = 3

# Create material and assign texture
texture_path = r"D:\Solar System 3D Rendering Files\solarsystem_textures\2k_pluto.webp"
mat = bpy.data.materials.new(name="Pluto_Material")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get('Principled BSDF')
tex_image = mat.node_tree.nodes.new('ShaderNodeTexImage')
tex_image.image = bpy.data.images.load(texture_path)

# Connect nodes
mat.node_tree.links.new(bsdf.inputs['Base Color'], tex_image.outputs['Color'])

# Add Pluto-specific material properties (rocky dwarf planet)
if 'Metallic' in bsdf.inputs:
    bsdf.inputs['Metallic'].default_value = 0.0  # Non-metallic rocky surface
if 'Roughness' in bsdf.inputs:
    bsdf.inputs['Roughness'].default_value = 0.8  # Rough rocky surface
# Using standard IOR for rocky material
if 'IOR' in bsdf.inputs:
    bsdf.inputs['IOR'].default_value = 1.5  # IOR for rocky material

# Assign material
if pluto.data.materials:
    pluto.data.materials[0] = mat
else:
    pluto.data.materials.append(mat)

# Set up animation (5 seconds at 24 fps = 120 frames)
bpy.context.scene.frame_start = 0
bpy.context.scene.frame_end = 120
bpy.context.scene.render.fps = 24

# Pluto rotates very slowly (about 153 hours or 6.4 Earth days per rotation)
# About 0.19 full rotations during the 5-second animation
pluto.rotation_euler = (0, 0, 0)
pluto.keyframe_insert(data_path="rotation_euler", frame=0)
pluto.rotation_euler = (0, 0, math.pi * 0.38)  # 0.19 full rotations (0.38π radians)
pluto.keyframe_insert(data_path="rotation_euler", frame=120)

# Linear interpolation
if pluto.animation_data and pluto.animation_data.action:
    action = pluto.animation_data.action
    try:
        for layer in action.layers:
            for strip in layer.strips:
                for channelbag in strip.channelbags:
                    for fcurve in channelbag.fcurves:
                        for kp in fcurve.keyframe_points:
                            kp.interpolation = 'LINEAR'
    except Exception as e:
        print(f"Interpolation skipped: {e}")

# Set up camera for full planet view - FIXED POSITIONING
bpy.ops.object.camera_add(location=(0, -4, 0))
camera = bpy.context.active_object
# Point camera directly at the planet center (no rotation needed when positioned on negative Y-axis)
camera.rotation_euler = (math.pi/2, 0, 0)
bpy.context.scene.camera = camera

# Adjust camera lens to fit entire planet in frame
camera.data.lens = 35  # Wider lens to capture full planet

# Add lighting - improved positioning
bpy.ops.object.light_add(type='SUN', location=(3, -3, 4))
sun = bpy.context.active_object
sun.data.energy = 3.0  # Increased energy for better illumination
sun.rotation_euler = (math.radians(45), math.radians(30), 0)  # Angle the light

# Add fill light to illuminate the lower half
bpy.ops.object.light_add(type='SUN', location=(-2, -2, -2))
fill_light = bpy.context.active_object
fill_light.data.energy = 1.0  # Softer fill light
fill_light.rotation_euler = (math.radians(-45), math.radians(-30), 0)

# Set black background with minimal ambient light
world = bpy.context.scene.world
if not world:
    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world

world.use_nodes = True
bg = world.node_tree.nodes.get('Background')
bg.inputs['Color'].default_value = (0, 0, 0, 1)  # Black background
bg.inputs['Strength'].default_value = 0.2  # Slightly more ambient light to see planet details

# Set render settings for better quality
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.samples = 64
bpy.context.scene.render.resolution_x = 1280
bpy.context.scene.render.resolution_y = 720
bpy.context.scene.render.film_transparent = False

print("Pluto planet animation setup complete!")