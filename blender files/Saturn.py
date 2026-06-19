import bpy
import math

# Clear existing objects safely without using operators
def clear_scene():
    # Get all objects to delete
    objects_to_delete = []
    for obj in bpy.context.scene.objects:
        if obj.type in ['MESH', 'LIGHT', 'CAMERA']:
            objects_to_delete.append(obj)
    
    # Delete objects directly
    for obj in objects_to_delete:
        bpy.data.objects.remove(obj, do_unlink=True)

# Clear the scene
clear_scene()
# Create a UV sphere for Saturn
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=64, ring_count=32)
saturn = bpy.context.active_object
saturn.name = "Saturn"
# Add subdivision surface modifier
saturn.modifiers.new(name="Subdivision", type='SUBSURF')
saturn.modifiers["Subdivision"].levels = 2
saturn.modifiers["Subdivision"].render_levels = 3
# Create material and assign texture for Saturn
texture_path = r"D:\Solar System 3D Rendering Files\solarsystem_textures\2k_saturn.jpg"
mat = bpy.data.materials.new(name="Saturn_Material")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get('Principled BSDF')
tex_image = mat.node_tree.nodes.new('ShaderNodeTexImage')
tex_image.image = bpy.data.images.load(texture_path)
# Connect nodes
mat.node_tree.links.new(bsdf.inputs['Base Color'], tex_image.outputs['Color'])
# Add Saturn-specific material properties (gas giant appearance)
if 'Metallic' in bsdf.inputs:
    bsdf.inputs['Metallic'].default_value = 0.0  # Non-metallic gas giant
if 'Roughness' in bsdf.inputs:
    bsdf.inputs['Roughness'].default_value = 0.3  # Smooth gaseous surface
# Using IOR for gas giant atmosphere
if 'IOR' in bsdf.inputs:
    bsdf.inputs['IOR'].default_value = 1.2  # IOR for hydrogen/helium atmosphere
# Assign material
if saturn.data.materials:
    saturn.data.materials[0] = mat
else:
    saturn.data.materials.append(mat)

# Create Saturn's rings using a cylinder with proper mesh operations
bpy.ops.mesh.primitive_cylinder_add(radius=3.0, depth=0.02, location=(0, 0, 0))
rings_outer = bpy.context.active_object
rings_outer.name = "Saturn_Rings_Outer"

# Create inner cylinder to subtract (create ring hole)
bpy.ops.mesh.primitive_cylinder_add(radius=1.3, depth=0.03, location=(0, 0, 0))
rings_inner = bpy.context.active_object
rings_inner.name = "Saturn_Rings_Inner"

# Make sure we're in object mode
bpy.ops.object.mode_set(mode='OBJECT')

# Select outer ring and make it active
bpy.context.view_layer.objects.active = rings_outer
bpy.ops.object.select_all(action='DESELECT')
rings_outer.select_set(True)

# Add boolean modifier to create ring shape
bool_mod = rings_outer.modifiers.new(name="Boolean", type='BOOLEAN')
bool_mod.operation = 'DIFFERENCE'
bool_mod.object = rings_inner
bool_mod.solver = 'EXACT'

# Apply the boolean modifier
bpy.ops.object.modifier_apply(modifier="Boolean")

# Delete the inner cylinder (no longer needed)
bpy.data.objects.remove(rings_inner, do_unlink=True)

# Rename the final rings object
rings = rings_outer
rings.name = "Saturn_Rings"

# Create rings material
rings_texture_path = r"D:\Solar System 3D Rendering Files\solarsystem_textures\2k_saturn_ring_alpha.png"
rings_mat = bpy.data.materials.new(name="Saturn_Rings_Material")
rings_mat.use_nodes = True
rings_mat.blend_method = 'BLEND'  # Enable transparency
rings_bsdf = rings_mat.node_tree.nodes.get('Principled BSDF')
rings_tex_image = rings_mat.node_tree.nodes.new('ShaderNodeTexImage')
rings_tex_image.image = bpy.data.images.load(rings_texture_path)
# Connect texture to both color and alpha
rings_mat.node_tree.links.new(rings_bsdf.inputs['Base Color'], rings_tex_image.outputs['Color'])
rings_mat.node_tree.links.new(rings_bsdf.inputs['Alpha'], rings_tex_image.outputs['Alpha'])
# Set material properties for rings
if 'Metallic' in rings_bsdf.inputs:
    rings_bsdf.inputs['Metallic'].default_value = 0.1  # Slight metallic for ice particles
if 'Roughness' in rings_bsdf.inputs:
    rings_bsdf.inputs['Roughness'].default_value = 0.8  # Rough particle surface
# Assign rings material
if rings.data.materials:
    rings.data.materials[0] = rings_mat
else:
    rings.data.materials.append(rings_mat)

# Set up animation (5 seconds at 24 fps = 120 frames)
bpy.context.scene.frame_start = 0
bpy.context.scene.frame_end = 120
bpy.context.scene.render.fps = 24
# Saturn rotates every 10.7 hours (fast rotation for a gas giant)
# About 2.8 full rotations during the 5-second animation
saturn.rotation_euler = (0, 0, 0)
saturn.keyframe_insert(data_path="rotation_euler", frame=0)
saturn.rotation_euler = (0, 0, math.pi * 5.6)  # 2.8 full rotations (5.6π radians)
saturn.keyframe_insert(data_path="rotation_euler", frame=120)

# Linear interpolation
if saturn.animation_data and saturn.animation_data.action:
    action = saturn.animation_data.action
    try:
        for layer in action.layers:
            for strip in layer.strips:
                for channelbag in strip.channelbags:
                    for fcurve in channelbag.fcurves:
                        for kp in fcurve.keyframe_points:
                            kp.interpolation = 'LINEAR'
    except Exception as e:
        print(f"Interpolation skipped: {e}")

# Animate rings (slower rotation than planet)
rings.rotation_euler = (0, 0, 0)
rings.keyframe_insert(data_path="rotation_euler", frame=0)
rings.rotation_euler = (0, 0, math.pi * 1.4)  # Slower ring rotation
rings.keyframe_insert(data_path="rotation_euler", frame=120) 

# Linear interpolation
if rings.animation_data and rings.animation_data.action:
    action = rings.animation_data.action
    try:
        for layer in action.layers:
            for strip in layer.strips:
                for channelbag in strip.channelbags:
                    for fcurve in channelbag.fcurves:
                        for kp in fcurve.keyframe_points:
                            kp.interpolation = 'LINEAR'
    except Exception as e:
        print(f"Interpolation skipped: {e}")

# Set up camera for full planet view - positioned to show complete rings
bpy.ops.object.camera_add(location=(0, -8, 2))  # Further back and higher to capture full rings
camera = bpy.context.active_object
# Point camera at planet center with slight downward angle
camera.rotation_euler = (math.radians(75), 0, 0)  # Better angle to see rings and planet
bpy.context.scene.camera = camera
# Adjust camera lens to fit entire planet and rings in frame
camera.data.lens = 24  # Even wider lens to capture full ring system
# Add realistic lighting setup for Saturn
bpy.ops.object.light_add(type='SUN', location=(5, -5, 3))
sun = bpy.context.active_object
sun.data.energy = 5.0  # Stronger main light
sun.data.angle = math.radians(0.5)  # Sharp shadows like sunlight
sun.rotation_euler = (math.radians(35), math.radians(45), 0)

# Add rim light to enhance planet edges
bpy.ops.object.light_add(type='SUN', location=(-4, -6, 2))
rim_light = bpy.context.active_object
rim_light.data.energy = 2.0
rim_light.data.color = (0.8, 0.9, 1.0)  # Slightly blue rim light
rim_light.rotation_euler = (math.radians(60), math.radians(-30), 0)

# Add subtle fill light for ring details
bpy.ops.object.light_add(type='AREA', location=(0, -3, -4))
fill_light = bpy.context.active_object
fill_light.data.energy = 1.5
fill_light.data.size = 2.0
fill_light.rotation_euler = (math.radians(180), 0, 0)
# Set pure black background
world = bpy.context.scene.world
if not world:
    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get('Background')
bg.inputs['Color'].default_value = (0, 0, 0, 1)  # Pure black background
bg.inputs['Strength'].default_value = 0.0  # No ambient light for deep space look
# Set render settings for realistic quality
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.samples = 64  # Higher samples for better quality
bpy.context.scene.render.resolution_x = 1280
bpy.context.scene.render.resolution_y = 720
bpy.context.scene.render.film_transparent = False
# Enable motion blur for more realistic rotation
bpy.context.scene.render.motion_blur_shutter = 0.5
# Set color management for more realistic colors
bpy.context.scene.view_settings.view_transform = 'Filmic'
bpy.context.scene.view_settings.look = 'Medium High Contrast'
print("Saturn planet animation with rings setup complete!")