import bpy
import math

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=64, ring_count=32)
obj = bpy.context.active_object
obj.name = "Neptune"

sub = obj.modifiers.new(name="Subsurf", type='SUBSURF')
sub.levels = 2
sub.render_levels = 3

tex_path = r"D:\Solar System 3D Rendering Files\solarsystem_textures\2k_neptune.jpg"

mat = bpy.data.materials.new(name="Mat_Neptune")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links

bsdf = nodes.get("Principled BSDF")
tex = nodes.new("ShaderNodeTexImage")

try:
    tex.image = bpy.data.images.load(tex_path)
except:
    print("Texture load failed")

links.new(bsdf.inputs["Base Color"], tex.outputs["Color"])

if "Metallic" in bsdf.inputs:
    bsdf.inputs["Metallic"].default_value = 0.0
if "Roughness" in bsdf.inputs:
    bsdf.inputs["Roughness"].default_value = 0.5
if "IOR" in bsdf.inputs:
    bsdf.inputs["IOR"].default_value = 1.3

if obj.data.materials:
    obj.data.materials[0] = mat
else:
    obj.data.materials.append(mat)

scn = bpy.context.scene
scn.frame_start = 0
scn.frame_end = 120
scn.render.fps = 24

obj.rotation_euler = (0, 0, 0)
obj.keyframe_insert(data_path="rotation_euler", frame=0)
obj.rotation_euler = (0, 0, math.pi * 3.72)
obj.keyframe_insert(data_path="rotation_euler", frame=120)

if obj.animation_data and obj.animation_data.action:
    act = obj.animation_data.action
    try:
        for layer in act.layers:
            for strip in layer.strips:
                for ch in strip.channelbags:
                    for fc in ch.fcurves:
                        for kp in fc.keyframe_points:
                            kp.interpolation = 'LINEAR'
    except:
        pass

bpy.ops.object.camera_add(location=(0, -4, 0))
cam = bpy.context.active_object
cam.rotation_euler = (math.pi/2, 0, 0)
scn.camera = cam
cam.data.lens = 35

bpy.ops.object.light_add(type='SUN', location=(3, -3, 4))
sun = bpy.context.active_object
sun.data.energy = 3.0
sun.rotation_euler = (math.radians(45), math.radians(30), 0)

bpy.ops.object.light_add(type='SUN', location=(-2, -2, -2))
fill = bpy.context.active_object
fill.data.energy = 1.0
fill.rotation_euler = (math.radians(-45), math.radians(-30), 0)

world = scn.world or bpy.data.worlds.new("World")
scn.world = world
world.use_nodes = True

bg = world.node_tree.nodes.get("Background")
bg.inputs["Color"].default_value = (0, 0, 0, 1)
bg.inputs["Strength"].default_value = 0.2

scn.render.engine = 'CYCLES'
scn.cycles.samples = 64
scn.render.resolution_x = 1280
scn.render.resolution_y = 720
scn.render.film_transparent = False

print("Done")