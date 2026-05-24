import bpy
import math

# Clear existing objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Create UV sphere for the sun
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0, 0))
sun = bpy.context.active_object
sun.name = "Sun"

# Add subdivision surface modifier
sun.modifiers.new(name="Subdivision", type='SUBSURF')
sun.modifiers["Subdivision"].levels = 2
sun.modifiers["Subdivision"].render_levels = 2

# Create material
mat = bpy.data.materials.new(name="Dark_Sun_Material")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links
nodes.clear()

# Create nodes
tex_coord = nodes.new(type='ShaderNodeTexCoord')
mapping = nodes.new(type='ShaderNodeMapping')
texture = nodes.new(type='ShaderNodeTexImage')

try:
    texture.image = bpy.data.images.load(r"D:\Solar System 3D Rendering Files\solarsystem_textures\2k_sun.jpg")
except:
    texture.image = bpy.data.images.new("Fallback", 1024, 1024, alpha=True)
    texture.image.generated_color = (0.8, 0.4, 0.1, 1)

rgb_curves = nodes.new(type='ShaderNodeRGBCurve')
color_mix = nodes.new(type='ShaderNodeMixRGB')
emission = nodes.new(type='ShaderNodeEmission')
output = nodes.new(type='ShaderNodeOutputMaterial')

emission.inputs['Strength'].default_value = 3.0

curve = rgb_curves.mapping.curves[3]
curve.points.new(0.25, 0.15)
curve.points.new(0.75, 0.65)
rgb_curves.mapping.update()

color_mix.blend_type = 'MULTIPLY'
color_mix.inputs['Color2'].default_value = (0.9, 0.7, 0.5, 1)

links.new(tex_coord.outputs['UV'], mapping.inputs['Vector'])
links.new(mapping.outputs['Vector'], texture.inputs['Vector'])
links.new(texture.outputs['Color'], rgb_curves.inputs['Color'])
links.new(rgb_curves.outputs['Color'], color_mix.inputs['Color1'])
links.new(color_mix.outputs['Color'], emission.inputs['Color'])
links.new(emission.outputs['Emission'], output.inputs['Surface'])

sun.data.materials.append(mat)

# World background
world = bpy.data.worlds['World']
world.use_nodes = True
bg = world.node_tree.nodes['Background']
bg.inputs['Color'].default_value = (0.02, 0.02, 0.02, 1)
bg.inputs['Strength'].default_value = 0.1

# Camera
bpy.ops.object.camera_add(location=(0, -4.5, 0.5))
camera = bpy.context.active_object
camera.name = "Sun_Camera"
camera.data.lens = 45

constraint = camera.constraints.new(type='TRACK_TO')
constraint.target = sun
constraint.track_axis = 'TRACK_NEGATIVE_Z'
constraint.up_axis = 'UP_Y'
bpy.context.scene.camera = camera

# Animation setup
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 120
bpy.context.scene.render.fps = 24

sun.animation_data_clear()
sun.rotation_mode = 'XYZ'

sun.rotation_euler = (0, 0, 0)
sun.keyframe_insert(data_path="rotation_euler", frame=1)
sun.rotation_euler = (0, 0, math.pi * 2)
sun.keyframe_insert(data_path="rotation_euler", frame=120)

# Blender 5.x: set linear interpolation via channelbag
if sun.animation_data and sun.animation_data.action:
    action = sun.animation_data.action
    action.name = "SunRotation"
    try:
        for layer in action.layers:
            for strip in layer.strips:
                for channelbag in strip.channelbags:
                    for fcurve in channelbag.fcurves:
                        for kp in fcurve.keyframe_points:
                            kp.interpolation = 'LINEAR'
    except Exception as e:
        print(f"Interpolation skipped: {e}")

# Render settings
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.samples = 256
# === FASTER RENDER SETTINGS ===
bpy.context.scene.cycles.samples = 64          # was 256 — 4x faster
bpy.context.scene.cycles.use_adaptive_sampling = True
bpy.context.scene.cycles.adaptive_threshold = 0.1
bpy.context.scene.cycles.use_denoising = True
bpy.context.scene.cycles.denoiser = 'OPENIMAGEDENOISE'  # works on any GPU/CPU

# Lower bounces (emission-only sun doesn't need many)
bpy.context.scene.cycles.max_bounces = 2
bpy.context.scene.cycles.diffuse_bounces = 1
bpy.context.scene.cycles.glossy_bounces = 1
bpy.context.scene.cycles.transparent_max_bounces = 2

# Use GPU
bpy.context.scene.cycles.device = 'GPU'
bpy.context.scene.render.use_persistent_data = True

# Lower resolution (optional, remove if you want 1080p)
bpy.context.scene.render.resolution_x = 1280
bpy.context.scene.render.resolution_y = 720

# Lower subdivision at render time

if hasattr(bpy.context.scene.view_settings, 'look'):
    try:
        bpy.context.scene.view_settings.look = 'AgX - High Contrast'
    except:
        pass

bpy.ops.view3d.camera_to_view_selected()