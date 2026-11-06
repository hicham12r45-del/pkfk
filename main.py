"""
Coralo - an ORIGINAL cartoon square sea-sponge character for Blender.

Run headless:
    blender -b -P coralo.py

Environment variables (all optional):
    OUT_DIR         output folder (default: "out")
    RENDER_PREVIEW  "1" to also render out/preview.png

Outputs:
    out/model.glb   the character (glTF binary)
    out/coralo.blend the full scene

Compatible with Blender 3.x and 4.x.
"""
import bpy
import math
import os
import random
import sys
import traceback

from mathutils import Vector, Quaternion


# =====================================================================
# CONFIGURATION
# =====================================================================
OUTPUT_DIR = os.environ.get("OUT_DIR", "out")
GLB_NAME = "model.glb"
BLEND_NAME = "coralo.blend"
PREVIEW_NAME = "preview.png"
RENDER_PNG = os.environ.get("RENDER_PREVIEW", "0") == "1"
SEED = 7

# Body dimensions (Blender units)
BODY_W = 2.0
BODY_D = 0.9
BODY_H = 2.2
BODY_BOTTOM = 0.9
BODY_CENTER_Z = BODY_BOTTOM + BODY_H / 2.0
BODY_TOP = BODY_BOTTOM + BODY_H
HALF_W = BODY_W / 2.0
HALF_D = BODY_D / 2.0
FRONT_Y = -HALF_D          # the face looks toward -Y

# Colour palette (RGBA, linear-ish values chosen for a flat cartoon look)
COL = {
    "body_a": (1.00, 0.42, 0.18, 1.0),
    "body_b": (1.00, 0.55, 0.22, 1.0),
    "limb": (0.95, 0.36, 0.15, 1.0),
    "pore": (0.62, 0.20, 0.08, 1.0),
    "spot": (0.55, 0.22, 0.70, 1.0),
    "eye_white": (0.98, 0.98, 1.00, 1.0),
    "iris": (0.30, 0.20, 0.85, 1.0),
    "pupil": (0.02, 0.02, 0.04, 1.0),
    "shine": (1.00, 1.00, 1.00, 1.0),
    "lash": (0.05, 0.03, 0.08, 1.0),
    "cheek": (1.00, 0.45, 0.55, 1.0),
    "freckle": (0.70, 0.25, 0.10, 1.0),
    "mouth": (0.20, 0.03, 0.05, 1.0),
    "teeth": (1.00, 0.98, 0.92, 1.0),
    "nose": (0.90, 0.30, 0.12, 1.0),
    "shorts": (0.10, 0.28, 0.45, 1.0),
    "belt": (0.12, 0.08, 0.06, 1.0),
    "buckle": (1.00, 0.78, 0.20, 1.0),
    "glove": (0.98, 0.95, 0.88, 1.0),
    "sock": (0.98, 0.96, 0.90, 1.0),
    "sock_stripe": (0.45, 0.25, 0.80, 1.0),
    "shoe": (0.95, 0.70, 0.12, 1.0),
    "sole": (0.20, 0.12, 0.08, 1.0),
    "stem": (0.20, 0.60, 0.25, 1.0),
    "leaf": (0.35, 0.78, 0.30, 1.0),
    "ground": (0.93, 0.85, 0.65, 1.0),
}

PARTS = []      # every character object is registered here
_MATS = {}      # material cache


# =====================================================================
# GENERIC HELPERS
# =====================================================================
def log(msg):
    print("[Coralo] " + msg)


def set_input(node, name, value):
    """Safely set a shader node input (names differ between versions)."""
    if node is not None and name in node.inputs:
        try:
            node.inputs[name].default_value = value
        except Exception:
            pass


def make_material(name, color, roughness=0.55, metallic=0.0,
                  subsurface=0.0, specular=0.4):
    """Create (or fetch) a Principled BSDF material."""
    if name in _MATS:
        return _MATS[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = color
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    set_input(bsdf, "Base Color", color)
    set_input(bsdf, "Roughness", roughness)
    set_input(bsdf, "Metallic", metallic)
    set_input(bsdf, "Subsurface", subsurface)          # Blender 3.x
    set_input(bsdf, "Subsurface Weight", subsurface)   # Blender 4.x
    set_input(bsdf, "Specular", specular)              # Blender 3.x
    set_input(bsdf, "Specular IOR Level", specular)    # Blender 4.x
    _MATS[name] = mat
    return mat


def make_sponge_material(name):
    """Body material: two-tone noise colour plus a fine bump for the sponge feel."""
    mat = make_material(name, COL["body_a"], roughness=0.7, subsurface=0.15)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    if bsdf is None:
        return mat
    try:
        big = nodes.new("ShaderNodeTexNoise")
        big.inputs["Scale"].default_value = 4.0
        big.inputs["Detail"].default_value = 3.0
        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = COL["body_a"]
        ramp.color_ramp.elements[1].color = COL["body_b"]
        links.new(big.outputs["Fac"], ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

        fine = nodes.new("ShaderNodeTexNoise")
        fine.inputs["Scale"].default_value = 70.0
        fine.inputs["Detail"].default_value = 6.0
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.18
        links.new(fine.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    except Exception as exc:
        log("procedural sponge nodes skipped: %s" % exc)
    return mat


def mat_for(key, roughness=0.55, metallic=0.0, specular=0.4):
    return make_material("M_" + key, COL[key], roughness, metallic,
                         0.0, specular)


def assign(obj, mat):
    if obj.type != 'MESH':
        return
    obj.data.materials.clear()
    obj.data.materials.append(mat)


def smooth(obj):
    if obj.type == 'MESH':
        for poly in obj.data.polygons:
            poly.use_smooth = True


def select_only(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def apply_scale(obj):
    select_only(obj)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)


def add_bevel(obj, width, segments=4):
    mod = obj.modifiers.new("Bevel", 'BEVEL')
    mod.width = width
    mod.segments = segments
    mod.limit_method = 'ANGLE'
    mod.angle_limit = math.radians(30.0)
    return mod


def finish(obj, name, mat, do_smooth=True):
    obj.name = name
    if obj.data is not None:
        obj.data.name = name + "_mesh"
    assign(obj, mat)
    if do_smooth:
        smooth(obj)
    PARTS.append(obj)
    return obj


# =====================================================================
# PRIMITIVE BUILDERS
# =====================================================================
def make_sphere(name, radius, loc, mat, scale=(1, 1, 1), rot=(0, 0, 0),
                segments=32, rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, segments=segments,
                                         ring_count=rings, location=loc)
    obj = bpy.context.active_object
    obj.scale = scale
    apply_scale(obj)
    obj.rotation_euler = rot
    return finish(obj, name, mat)


def make_cylinder(name, radius, depth, loc, mat, rot=(0, 0, 0), verts=32):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth,
                                        vertices=verts, location=loc,
                                        rotation=rot)
    obj = bpy.context.active_object
    return finish(obj, name, mat)


def make_box(name, size, loc, mat, rot=(0, 0, 0), bevel=0.03, segs=4):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    obj = bpy.context.active_object
    obj.scale = size
    apply_scale(obj)
    obj.rotation_euler = rot
    if bevel > 0.0:
        add_bevel(obj, bevel, segs)
    return finish(obj, name, mat)


def make_torus(name, major, minor, loc, mat, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor,
                                     major_segments=40, minor_segments=12,
                                     location=loc, rotation=rot)
    obj = bpy.context.active_object
    return finish(obj, name, mat)


def make_segment(name, p0, p1, r0, r1, mat, verts=24):
    """Tapered cylinder going from point p0 (radius r0) to p1 (radius r1)."""
    a = Vector(p0)
    b = Vector(p1)
    direction = b - a
    length = direction.length
    mid = (a + b) / 2.0
    bpy.ops.mesh.primitive_cone_add(radius1=r0, radius2=r1, depth=length,
                                    vertices=verts, location=mid)
    obj = bpy.context.active_object
    obj.rotation_mode = 'QUATERNION'
    unit = direction.normalized()
    if abs(unit.z) > 0.9999:
        if unit.z > 0:
            obj.rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))
        else:
            obj.rotation_quaternion = Quaternion((1.0, 0.0, 0.0), math.pi)
    else:
        obj.rotation_quaternion = unit.to_track_quat('Z', 'Y')
    return finish(obj, name, mat)


def make_tube(name, pts, radius, mat):
    """Smooth bezier tube through the given points (used for the smile)."""
    cu = bpy.data.curves.new(name + "_curve", 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = radius
    cu.bevel_resolution = 6
    cu.resolution_u = 24
    cu.use_fill_caps = True
    spline = cu.splines.new('BEZIER')
    spline.bezier_points.add(len(pts) - 1)
    for bp, p in zip(spline.bezier_points, pts):
        bp.co = p
        bp.handle_left_type = 'AUTO'
        bp.handle_right_type = 'AUTO'
    obj = bpy.data.objects.new(name, cu)
    bpy.context.collection.objects.link(obj)
    select_only(obj)
    bpy.ops.object.convert(target='MESH')
    obj = bpy.context.view_layer.objects.active
    return finish(obj, name, mat)


# =====================================================================
# SCENE SETUP
# =====================================================================
def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.curves,
                  bpy.data.lights, bpy.data.cameras):
        for item in list(block):
            if item.users == 0:
                block.remove(item)
    PARTS.clear()
    _MATS.clear()


def setup_world():
    scene = bpy.context.scene
    if scene.world is None:
        scene.world = bpy.data.worlds.new("CoraloWorld")
    world = scene.world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    set_input(bg, "Color", (0.62, 0.80, 0.92, 1.0))
    set_input(bg, "Strength", 0.9)


def setup_render():
    scene = bpy.context.scene
    for engine in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'CYCLES'):
        try:
            scene.render.engine = engine
            break
        except Exception:
            continue
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 1280
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    try:
        scene.view_settings.view_transform = 'Standard'
    except Exception:
        pass


# =====================================================================
# BODY
# =====================================================================
def build_body():
    log("building body")
    body_mat = make_sponge_material("M_body")
    bpy.ops.mesh.primitive_cube_add(size=1.0,
                                    location=(0, 0, BODY_CENTER_Z))
    body = bpy.context.active_object
    body.scale = (BODY_W, BODY_D, BODY_H)
    apply_scale(body)
    add_bevel(body, 0.14, 8)
    finish(body, "Body", body_mat)
    return body


def surface_point(face, u, v):
    """Return (position, normal axis letter) on a body face."""
    if face == "front":
        return Vector((u, -HALF_D, v)), 'y'
    if face == "back":
        return Vector((u, HALF_D, v)), 'y'
    if face == "left":
        return Vector((-HALF_W, u, v)), 'x'
    if face == "right":
        return Vector((HALF_W, u, v)), 'x'
    return Vector((u, v, BODY_TOP)), 'z'    # top


def flat_scale(axis, r, thickness):
    if axis == 'x':
        return (thickness, r, r)
    if axis == 'y':
        return (r, thickness, r)
    return (r, r, thickness)


def inside_face_area(face, u, v):
    """True when a front-face sample would land on the face / shorts."""
    if face != "front":
        return False
    return abs(u) < 0.80 and 1.40 < v < 2.90


def scatter_pores():
    log("scattering sponge pores")
    rng = random.Random(SEED)
    pore_mat = mat_for("pore", roughness=0.9)
    plan = [
        ("front", 16, (-0.92, 0.92), (1.45, 3.02)),
        ("back", 18, (-0.9, 0.9), (1.45, 3.0)),
        ("left", 10, (-0.38, 0.38), (1.45, 3.0)),
        ("right", 10, (-0.38, 0.38), (1.45, 3.0)),
        ("top", 8, (-0.85, 0.85), (-0.35, 0.35)),
    ]
    placed = []
    index = 0
    for face, count, urange, vrange in plan:
        made = 0
        attempts = 0
        while made < count and attempts < 400:
            attempts += 1
            u = rng.uniform(*urange)
            v = rng.uniform(*vrange)
            if inside_face_area(face, u, v):
                continue
            pos, axis = surface_point(face, u, v)
            if any((pos - q).length < 0.16 for q in placed):
                continue
            radius = rng.uniform(0.035, 0.075)
            normal = Vector({'x': (1, 0, 0), 'y': (0, 1, 0),
                             'z': (0, 0, 1)}[axis])
            sign = 1.0
            if face in ("front", "left"):
                sign = -1.0
            pos = pos - normal * sign * 0.012
            make_sphere("Pore_%02d" % index, radius, pos, pore_mat,
                        scale=flat_scale(axis, 1.0, 0.35),
                        segments=16, rings=8)
            placed.append(pos)
            made += 1
            index += 1
    log("pores placed: %d" % index)


def add_spots():
    log("adding colour spots")
    spot_mat = mat_for("spot", roughness=0.8)
    spots = [
        ("front", -0.78, 2.88, 0.20), ("front", 0.74, 2.80, 0.16),
        ("front", 0.82, 1.58, 0.13), ("front", -0.80, 1.56, 0.12),
        ("back", -0.4, 2.5, 0.28), ("back", 0.5, 1.9, 0.24),
        ("back", 0.2, 2.9, 0.15), ("left", 0.1, 2.6, 0.22),
        ("right", -0.1, 2.2, 0.2), ("top", 0.5, 0.1, 0.18),
        ("top", -0.6, -0.1, 0.14),
    ]
    for i, (face, u, v, r) in enumerate(spots):
        pos, axis = surface_point(face, u, v)
        make_sphere("Spot_%02d" % i, r, pos, spot_mat,
                    scale=flat_scale(axis, 1.0, 0.18),
                    segments=24, rings=12)


# =====================================================================
# FACE
# =====================================================================
def build_eyes():
    log("building eyes")
    white = mat_for("eye_white", roughness=0.15, specular=0.8)
    iris = mat_for("iris", roughness=0.2, specular=0.7)
    pupil = mat_for("pupil", roughness=0.1, specular=0.9)
    shine = mat_for("shine", roughness=0.0)
    lash = mat_for("lash", roughness=0.4)
    eye_z = 2.45
    for name, sx in (("L", -1.0), ("R", 1.0)):
        cx = sx * 0.42
        make_sphere("Eye_White_" + name, 0.34,
                    (cx, FRONT_Y - 0.03, eye_z), white,
                    scale=(1.0, 0.5, 1.12))
        make_sphere("Eye_Iris_" + name, 0.15,
                    (cx - sx * 0.04, FRONT_Y - 0.20, eye_z - 0.02), iris,
                    scale=(1.0, 0.35, 1.0))
        make_sphere("Eye_Pupil_" + name, 0.075,
                    (cx - sx * 0.04, FRONT_Y - 0.235, eye_z - 0.02), pupil,
                    scale=(1.0, 0.3, 1.0), segments=24, rings=12)
        make_sphere("Eye_Shine_" + name, 0.035,
                    (cx - sx * 0.01, FRONT_Y - 0.255, eye_z + 0.04), shine,
                    scale=(1.0, 0.3, 1.0), segments=16, rings=8)
        make_sphere("Eye_Shine_Small_" + name, 0.018,
                    (cx - sx * 0.08, FRONT_Y - 0.25, eye_z - 0.07), shine,
                    scale=(1.0, 0.3, 1.0), segments=12, rings=6)
        # three eyelashes fanning out from the top of the eye
        top = Vector((cx, FRONT_Y - 0.1, eye_z + 0.36))
        for i, angle in enumerate((-28.0, 0.0, 28.0)):
            a = math.radians(angle)
            length = 0.30 if i == 1 else 0.24
            direction = Vector((math.sin(a), 0.0, math.cos(a)))
            centre = top + direction * (length / 2.0)
            make_cylinder("Eyelash_%s_%d" % (name, i), 0.016, length,
                          centre, lash, rot=(0, a, 0), verts=12)


def build_nose_and_cheeks():
    log("building nose, cheeks and freckles")
    nose = mat_for("nose", roughness=0.5)
    cheek = mat_for("cheek", roughness=0.8)
    freckle = mat_for("freckle", roughness=0.9)
    make_sphere("Nose", 0.14, (0.0, FRONT_Y - 0.12, 2.08), nose,
                scale=(0.8, 1.0, 1.35))
    make_sphere("Nose_Tip", 0.07, (0.0, FRONT_Y - 0.24, 2.0), nose,
                scale=(1.0, 0.8, 0.9), segments=20, rings=10)
    for name, sx in (("L", -1.0), ("R", 1.0)):
        make_sphere("Cheek_" + name, 0.2, (sx * 0.66, FRONT_Y - 0.01, 1.86),
                    cheek, scale=(1.0, 0.18, 0.75))
        for i, (dx, dz) in enumerate(((-0.07, 0.07), (0.07, 0.09),
                                      (0.0, -0.05))):
            make_sphere("Freckle_%s_%d" % (name, i), 0.028,
                        (sx * 0.66 + dx, FRONT_Y - 0.035, 1.86 + dz),
                        freckle, scale=(1.0, 0.3, 1.0), segments=12, rings=6)


def build_mouth():
    log("building mouth")
    mouth = mat_for("mouth", roughness=0.4)
    teeth = mat_for("teeth", roughness=0.25, specular=0.6)
    y = FRONT_Y - 0.035
    make_tube("Smile", [(-0.62, y, 1.82), (0.0, y - 0.01, 1.52),
                        (0.62, y, 1.82)], 0.032, mouth)
    for name, sx in (("L", -1.0), ("R", 1.0)):
        make_tube("Dimple_" + name,
                  [(sx * 0.68, y, 1.90), (sx * 0.72, y, 1.82),
                   (sx * 0.66, y, 1.74)], 0.02, mouth)
    for name, sx in (("L", -1.0), ("R", 1.0)):
        make_box("Tooth_" + name, (0.17, 0.05, 0.24),
                 (sx * 0.095, y - 0.015, 1.40), teeth, bevel=0.025, segs=4)


# =====================================================================
# CLOTHES
# =====================================================================
def build_shorts():
    log("building shorts")
    shorts = mat_for("shorts", roughness=0.85)
    belt = mat_for("belt", roughness=0.5)
    buckle = mat_for("buckle", roughness=0.25, metallic=0.9, specular=0.8)
    glove = mat_for("glove", roughness=0.7)
    make_box("Shorts", (BODY_W + 0.1, BODY_D + 0.1, 0.46),
             (0, 0, BODY_BOTTOM + 0.23), shorts, bevel=0.07, segs=5)
    make_box("Belt", (BODY_W + 0.14, BODY_D + 0.14, 0.1),
             (0, 0, BODY_BOTTOM + 0.5), belt, bevel=0.03)
    make_box("Buckle", (0.26, 0.05, 0.14),
             (0, FRONT_Y - 0.1, BODY_BOTTOM + 0.5), buckle, bevel=0.015)
    make_box("Buckle_Inner", (0.14, 0.06, 0.07),
             (0, FRONT_Y - 0.105, BODY_BOTTOM + 0.5), belt, bevel=0.01)
    for name, sx in (("L", -1.0), ("R", 1.0)):
        make_cylinder("Button_" + name, 0.07, 0.04,
                      (sx * 0.55, FRONT_Y - 0.075, BODY_BOTTOM + 0.22),
                      glove, rot=(math.pi / 2.0, 0, 0), verts=24)
        make_torus("Button_Rim_" + name, 0.07, 0.012,
                   (sx * 0.55, FRONT_Y - 0.095, BODY_BOTTOM + 0.22), belt,
                   rot=(math.pi / 2.0, 0, 0))
        make_box("Pocket_" + name, (0.5, 0.03, 0.24),
                 (sx * 0.5, FRONT_Y - 0.065, BODY_BOTTOM + 0.2), shorts,
                 bevel=0.012, segs=2)


# =====================================================================
# LIMBS
# =====================================================================
def build_hand(prefix, wrist, direction, side):
    glove = mat_for("glove", roughness=0.6)
    d = Vector(direction).normalized()
    lateral = d.cross(Vector((0, 1, 0)))
    if lateral.length < 0.05:
        lateral = Vector((1, 0, 0))
    lateral.normalize()
    palm_c = Vector(wrist) + d * 0.12
    make_sphere(prefix + "_Palm", 0.15, palm_c, glove, scale=(1, 0.85, 1))
    for i, k in enumerate((-1.0, 0.0, 1.0)):
        base = palm_c + lateral * (k * 0.07) + d * 0.07
        tip = palm_c + lateral * (k * 0.085) + d * 0.34
        make_segment("%s_Finger_%d" % (prefix, i), base, tip,
                     0.04, 0.034, glove, verts=14)
        make_sphere("%s_Fingertip_%d" % (prefix, i), 0.036, tip, glove,
                    segments=14, rings=8)
    t_base = palm_c + lateral * (side * 0.1)
    t_tip = palm_c + lateral * (side * 0.22) + d * 0.14
    make_segment(prefix + "_Thumb", t_base, t_tip, 0.04, 0.034, glove,
                 verts=14)
    make_sphere(prefix + "_Thumb_Tip", 0.036, t_tip, glove,
                segments=14, rings=8)


def build_arm(prefix, side, shoulder, elbow, wrist):
    limb = mat_for("limb", roughness=0.7)
    make_sphere(prefix + "_Shoulder", 0.1, shoulder, limb)
    make_segment(prefix + "_Upper", shoulder, elbow, 0.085, 0.07, limb)
    make_sphere(prefix + "_Elbow", 0.075, elbow, limb)
    make_segment(prefix + "_Fore", elbow, wrist, 0.07, 0.06, limb)
    build_hand(prefix + "_Hand", wrist, Vector(wrist) - Vector(elbow), side)


def build_arms():
    log("building arms")
    # left arm waves hello, right arm rests by the side
    build_arm("Arm_L", -1.0, (-1.0, 0.0, 2.15), (-1.55, -0.08, 2.60),
              (-1.72, -0.25, 3.15))
    build_arm("Arm_R", 1.0, (1.0, 0.0, 2.15), (1.50, -0.10, 1.72),
              (1.62, -0.26, 1.28))


def build_legs():
    log("building legs, socks and shoes")
    limb = mat_for("limb", roughness=0.7)
    sock = mat_for("sock", roughness=0.8)
    stripe = mat_for("sock_stripe", roughness=0.8)
    shoe = mat_for("shoe", roughness=0.45, specular=0.5)
    sole = mat_for("sole", roughness=0.9)
    for name, sx in (("L", -1.0), ("R", 1.0)):
        x = sx * 0.45
        make_segment("Leg_" + name, (x, 0, BODY_BOTTOM + 0.05),
                     (x, 0, 0.62), 0.075, 0.07, limb)
        make_segment("Sock_" + name, (x, 0, 0.64), (x, 0, 0.2),
                     0.105, 0.115, sock)
        for i, z in enumerate((0.55, 0.46)):
            make_torus("Sock_Stripe_%s_%d" % (name, i), 0.108, 0.022,
                       (x, 0, z), stripe)
        make_sphere("Shoe_" + name, 0.26, (x, -0.12, 0.145), shoe,
                    scale=(0.92, 1.45, 0.56))
        make_sphere("Sole_" + name, 0.27, (x, -0.12, 0.058), sole,
                    scale=(0.95, 1.5, 0.2))
        make_sphere("Shoe_Toe_" + name, 0.1, (x, -0.38, 0.16), shoe,
                    scale=(1.1, 0.8, 0.8), segments=20, rings=10)


def build_sprout():
    log("building sprout")
    stem = mat_for("stem", roughness=0.6)
    leaf = mat_for("leaf", roughness=0.5)
    base = Vector((0.0, 0.0, BODY_TOP - 0.02))
    tip = base + Vector((0.03, 0.0, 0.42))
    make_segment("Sprout_Stem", base, tip, 0.05, 0.035, stem)
    for name, sx in (("L", -1.0), ("R", 1.0)):
        make_sphere("Sprout_Leaf_" + name, 0.18,
                    tip + Vector((sx * 0.17, 0, 0.07)), leaf,
                    scale=(1.0, 0.22, 0.45),
                    rot=(0, sx * math.radians(-28.0), 0),
                    segments=24, rings=12)
    make_sphere("Sprout_Bud", 0.055, tip + Vector((0, 0, 0.06)), leaf,
                segments=16, rings=8)


# =====================================================================
# STAGE: GROUND, LIGHTS, CAMERA
# =====================================================================
def build_ground():
    sand = mat_for("ground", roughness=0.95)
    bpy.ops.mesh.primitive_cylinder_add(radius=4.5, depth=0.1, vertices=96,
                                        location=(0, 0, -0.05))
    ground = bpy.context.active_object
    ground.name = "Ground"
    assign(ground, sand)
    return ground


def add_area_light(name, loc, energy, size, target, color=(1, 1, 1)):
    bpy.ops.object.light_add(type='AREA', location=loc)
    light = bpy.context.active_object
    light.name = name
    light.data.energy = energy
    light.data.size = size
    light.data.color = color
    con = light.constraints.new('TRACK_TO')
    con.target = target
    con.track_axis = 'TRACK_NEGATIVE_Z'
    con.up_axis = 'UP_Y'
    return light


def build_stage():
    log("building stage")
    build_ground()
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 1.7))
    target = bpy.context.active_object
    target.name = "FocusTarget"
    add_area_light("KeyLight", (4.0, -5.0, 6.0), 900, 4.0, target,
                   (1.0, 0.96, 0.9))
    add_area_light("FillLight", (-5.0, -4.0, 3.0), 350, 5.0, target,
                   (0.85, 0.92, 1.0))
    add_area_light("RimLight", (0.0, 6.0, 5.0), 500, 3.0, target)
    bpy.ops.object.camera_add(location=(5.2, -8.2, 3.7))
    cam = bpy.context.active_object
    cam.name = "Camera"
    cam.data.lens = 55
    con = cam.constraints.new('TRACK_TO')
    con.target = target
    con.track_axis = 'TRACK_NEGATIVE_Z'
    con.up_axis = 'UP_Y'
    bpy.context.scene.camera = cam
    return cam


# =====================================================================
# ASSEMBLY, VERIFICATION, EXPORT
# =====================================================================
def parent_all():
    root = bpy.data.objects.new("Coralo", None)
    root.empty_display_type = 'PLAIN_AXES'
    bpy.context.collection.objects.link(root)
    for obj in PARTS:
        obj.parent = root
    log("parented %d parts under 'Coralo'" % len(PARTS))
    return root


def verify_model():
    """Sanity checks so a broken build fails loudly instead of silently."""
    problems = []
    verts = 0
    for obj in PARTS:
        if obj.type != 'MESH':
            problems.append("%s is not a mesh" % obj.name)
            continue
        if len(obj.data.vertices) == 0:
            problems.append("%s has no vertices" % obj.name)
        if len(obj.data.materials) == 0:
            problems.append("%s has no material" % obj.name)
        verts += len(obj.data.vertices)
    low = min((obj.matrix_world @ Vector(c)).z
              for obj in PARTS for c in obj.bound_box)
    high = max((obj.matrix_world @ Vector(c)).z
               for obj in PARTS for c in obj.bound_box)
    log("parts: %d | vertices: %d | height: %.2f" %
        (len(PARTS), verts, high - low))
    if low < -0.05:
        problems.append("model sinks below ground (z=%.3f)" % low)
    if problems:
        raise RuntimeError("verification failed: " + "; ".join(problems))
    log("verification passed")


def export_all():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    glb_path = os.path.join(OUTPUT_DIR, GLB_NAME)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in PARTS:
        obj.select_set(True)
    try:
        bpy.ops.export_scene.gltf(filepath=glb_path, export_format='GLB',
                                  use_selection=True, export_apply=True)
    except TypeError:
        bpy.ops.export_scene.gltf(filepath=glb_path, export_format='GLB',
                                  use_selection=True)
    log("exported " + glb_path)
    blend_path = os.path.join(OUTPUT_DIR, BLEND_NAME)
    bpy.ops.wm.save_as_mainfile(filepath=blend_path, compress=True)
    log("saved " + blend_path)
    if RENDER_PNG:
        png_path = os.path.join(OUTPUT_DIR, PREVIEW_NAME)
        bpy.context.scene.render.filepath = png_path
        bpy.ops.render.render(write_still=True)
        log("rendered " + png_path)


def build_character():
    build_body()
    scatter_pores()
    add_spots()
    build_eyes()
    build_nose_and_cheeks()
    build_mouth()
    build_shorts()
    build_arms()
    build_legs()
    build_sprout()


def main():
    try:
        clear_scene()
        setup_world()
        setup_render()
        build_character()
        verify_model()
        parent_all()
        build_stage()
        export_all()
        log("done")
    except Exception as exc:
        print("Blender script failed: %s" % exc, file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
