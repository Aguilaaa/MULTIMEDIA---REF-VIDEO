import bpy
import math

# Clear existing objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Create a UV sphere for Mars
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=64, ring_count=32)
mars = bpy.context.active_object
mars.name = "Mars"

# Add subdivision surface modifier
mars.modifiers.new(name="Subdivision", type='SUBSURF')
mars.modifiers["Subdivision"].levels = 2
mars.modifiers["Subdivision"].render_levels = 3

# Create material and assign texture
texture_path = r"D:\Solar System 3D Rendering Files\solarsystem_textures\2k_mars.jpg"  # Update with your Mars texture path
mat = bpy.data.materials.new(name="Mars_Material")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get('Principled BSDF')
tex_image = mat.node_tree.nodes.new('ShaderNodeTexImage')
tex_image.image = bpy.data.images.load(texture_path)

# Connect nodes
mat.node_tree.links.new(bsdf.inputs['Base Color'], tex_image.outputs['Color'])

# Add Mars-specific material properties (rusty, dusty surface)
if 'Metallic' in bsdf.inputs:
    bsdf.inputs['Metallic'].default_value = 0.05  # Slight metallic for mineral content
if 'Roughness' in bsdf.inputs:
    bsdf.inputs['Roughness'].default_value = 0.7  # Very rough surface
if 'Specular' in bsdf.inputs:
    bsdf.inputs['Specular'].default_value = 0.1  # Low specularity
if 'IOR' in bsdf.inputs:
    bsdf.inputs['IOR'].default_value = 1.5  # Similar to dry soil/rock

# Add bump/normal map for surface detail (optional)
try:
    normal_path = r"D:\Solar System 3D Rendering Files\solarsystem_textures\2k_mars_normal.jpg"  # Update path
    normal_map = mat.node_tree.nodes.new('ShaderNodeTexImage')
    normal_map.image = bpy.data.images.load(normal_path)
    
    normal_node = mat.node_tree.nodes.new('ShaderNodeNormalMap')
    mat.node_tree.links.new(normal_node.inputs['Color'], normal_map.outputs['Color'])
    mat.node_tree.links.new(bsdf.inputs['Normal'], normal_node.outputs['Normal'])
except:
    print("Normal map not found, proceeding without surface details")

# Assign material
if mars.data.materials:
    mars.data.materials[0] = mat
else:
    mars.data.materials.append(mat)

# Set up animation (10 seconds at 24 fps = 240 frames)
bpy.context.scene.frame_start = 0
bpy.context.scene.frame_end = 120
bpy.context.scene.render.fps = 24

# Mars rotates once every 24.6 hours - slightly slower than Earth
mars.rotation_euler = (0, 0, 0)
mars.keyframe_insert(data_path="rotation_euler", frame=0)
mars.rotation_euler = (0, 0, math.pi * 2)
mars.keyframe_insert(data_path="rotation_euler", frame=250)  # Slightly longer for Mars day

# Linear interpolation - Blender 5.x compatible
if mars.animation_data and mars.animation_data.action:
    action = mars.animation_data.action
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

# Add lighting - sunlight (Mars receives less sunlight than Earth)
bpy.ops.object.light_add(type='SUN', location=(3, -3, 4))
sun = bpy.context.active_object
sun.data.energy = 2.5  # Slightly dimmer than Earth's sun
sun.rotation_euler = (math.radians(45), math.radians(30), 0)

# Add fill light to show surface details
bpy.ops.object.light_add(type='SUN', location=(-2, -2, -2))
fill_light = bpy.context.active_object
fill_light.data.energy = 0.8  # Softer fill light
fill_light.rotation_euler = (math.radians(-45), math.radians(-30), 0)

# Set background to simulate Martian sky (dusty reddish)
world = bpy.context.scene.world
if not world:
    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world

world.use_nodes = True
bg = world.node_tree.nodes.get('Background')
bg.inputs['Color'].default_value = (0.1, 0.05, 0.03, 1)  # Dusty reddish
bg.inputs['Strength'].default_value = 0.1

# Set render settings for Martian atmosphere effect
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.samples = 64
bpy.context.scene.render.resolution_x = 1280
bpy.context.scene.render.resolution_y = 720
bpy.context.scene.render.film_transparent = False

print("Mars planet animation setup complete!")