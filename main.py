"""
SPONGEBOB SQUAREPANTS - PROCEDURAL BLENDER MODEL
Blender 4.2 LTS | bpy | GLB export
Style: faithful cartoon proportions with polished 3D materials and studio lighting.

Run:
  blender --background --factory-startup --python main.py

Optional environment variables:
  OUTPUT_GLB=out/model.glb
  RENDER_PREVIEW=1
"""

import bpy
import math
import os
import sys
import traceback
from mathutils import Vector, Euler
from math import sin, cos, pi, radians


# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

CONFIG = {
    "output": os.environ.get("OUTPUT_GLB", "out/model.glb"),
    "render_preview": os.environ.get("RENDER_PREVIEW", "0") == "1",
    "resolution_x": 1600,
    "resolution_y": 1600,
    "resolution_percentage": 100,
    "samples": 64,
    "character_height": 5.8,
    "bevel_segments": 5,
    "body_subdivisions": 2,
    "detail_quality": 1.0,
}

COLLECTIONS = {}
MATERIALS = {}
ROOT = None


# ---------------------------------------------------------------------------
# SCENE AND COLLECTION UTILITIES
# ---------------------------------------------------------------------------

def safe_set(obj, attribute, value):
    """Set a Blender property only when that property exists."""
    if hasattr(obj, attribute):
        setattr(obj, attribute, value)


def get_collection(name):
    """Return a named collection, creating it when necessary."""
    if name in COLLECTIONS:
        return COLLECTIONS[name]
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    COLLECTIONS[name] = collection
    return collection


def move_to_collection(obj, collection_name):
    """Move an object into a clean semantic collection."""
    target = get_collection(collection_name)
    for old_collection in list(obj.users_collection):
        old_collection.objects.unlink(obj)
    target.objects.link(obj)
    return obj


def set_active(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def apply_transform(obj, location=True, rotation=True, scale=True):
    """Apply transforms to keep exported geometry predictable."""
    set_active(obj)
    bpy.ops.object.transform_apply(
        location=location,
        rotation=rotation,
        scale=scale,
    )


def smooth_mesh(obj):
    """Enable smooth shading on mesh polygons."""
    if obj.type == "MESH":
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
    return obj


def add_bevel(obj, width=0.08, segments=5, name="Soft rounded edges"):
    """Add a weighted bevel modifier."""
    modifier = obj.modifiers.new(name=name, type="BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"
    modifier.angle_limit = radians(25)
    return modifier


def add_weighted_normals(obj):
    """Improve shading on hard-surface and rounded box geometry."""
    modifier = obj.modifiers.new(name="Weighted corner normals", type="WEIGHTED_NORMAL")
    safe_set(modifier, "keep_sharp", True)
    safe_set(modifier, "weight", 40)
    return modifier


def create_empty(name, location=(0, 0, 0), parent=None):
    obj = bpy.data.objects.new(name, None)
    get_collection("00_CHARACTER_RIG").objects.link(obj)
    obj.location = location
    if parent:
        obj.parent = parent
    return obj


def parent_to_root(obj):
    if ROOT is not None and obj != ROOT:
        obj.parent = ROOT
    return obj


def clear_scene():
    """Remove factory objects and stale collections."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        if collection.users == 0:
            bpy.data.collections.remove(collection)
    COLLECTIONS.clear()
    MATERIALS.clear()


# ---------------------------------------------------------------------------
# MATERIAL SYSTEM
# ---------------------------------------------------------------------------

def make_material(name, color, roughness=0.55, metallic=0.0,
                  subsurface=0.0, specular=0.35):
    """Create a Principled BSDF material with explicit display settings."""
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1.0)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    shader = nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1.0)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    if "Subsurface Weight" in shader.inputs:
        shader.inputs["Subsurface Weight"].default_value = subsurface
    if "Specular IOR Level" in shader.inputs:
        shader.inputs["Specular IOR Level"].default_value = specular
    MATERIALS[name] = material
    return material


def add_noise_bump(material, scale=28.0, strength=0.18, distance=0.035):
    """Add subtle procedural surface grain without relying on image textures."""
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    shader = nodes.get("Principled BSDF")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = 3.0
    noise.inputs["Roughness"].default_value = 0.72
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = distance
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], shader.inputs["Normal"])


def build_materials():
    """Build all character and studio materials."""
    yellow = make_material("Sponge - warm golden yellow", (1.0, 0.72, 0.035), 0.72, 0.0, 0.035)
    add_noise_bump(yellow, 34, 0.22, 0.045)

    yellow_light = make_material("Sponge - pore inner gold", (0.78, 0.43, 0.012), 0.9)
    yellow_high = make_material("Sponge - pore rim", (1.0, 0.84, 0.16), 0.75)

    white = make_material("Shirt and eye whites", (0.96, 0.97, 0.93), 0.42)
    eye_white = make_material("Eye whites - glossy", (1.0, 0.99, 0.96), 0.18)
    blue = make_material("Iris - ocean blue", (0.025, 0.32, 0.88), 0.22, 0.05)
    blue_light = make_material("Iris - inner azure", (0.08, 0.68, 1.0), 0.2)
    black = make_material("Pupils and eyelashes", (0.008, 0.009, 0.014), 0.2)
    dark_brown = make_material("Mouth interior", (0.105, 0.018, 0.012), 0.75)
    tooth = make_material("Teeth - enamel", (1.0, 0.99, 0.9), 0.2)
    pink = make_material("Tongue - coral pink", (0.92, 0.12, 0.29), 0.38)
    cheek = make_material("Cheek warm blush", (1.0, 0.48, 0.25), 0.72)
    freckle = make_material("Freckles - warm brown", (0.48, 0.16, 0.025), 0.8)
    red = make_material("Tie - bright red", (0.82, 0.018, 0.035), 0.3)
    brown = make_material("Shorts - cocoa brown", (0.34, 0.145, 0.055), 0.78)
    brown_dark = make_material("Shorts - seams", (0.16, 0.065, 0.025), 0.8)
    belt = make_material("Belt - dark umber", (0.12, 0.055, 0.025), 0.38)
    gold = make_material("Belt buckle - warm brass", (0.95, 0.62, 0.12), 0.25, 0.72)
    sock_white = make_material("Socks - white cotton", (0.92, 0.94, 0.92), 0.82)
    sock_red = make_material("Sock stripe - red", (0.82, 0.02, 0.04), 0.6)
    sock_blue = make_material("Sock stripe - blue", (0.025, 0.2, 0.72), 0.6)
    shoe = make_material("Shoes - polished black leather", (0.012, 0.014, 0.02), 0.22)
    sole = make_material("Shoes - rubber sole", (0.035, 0.03, 0.028), 0.82)
    seam = make_material("Shoe stitching", (0.18, 0.17, 0.15), 0.65)
    return {
        "yellow": yellow, "yellow_light": yellow_light, "yellow_high": yellow_high,
        "white": white, "eye_white": eye_white, "blue": blue,
        "blue_light": blue_light, "black": black, "mouth": dark_brown,
        "tooth": tooth, "pink": pink, "cheek": cheek, "freckle": freckle,
        "red": red, "brown": brown, "brown_dark": brown_dark,
        "belt": belt, "gold": gold, "sock_white": sock_white,
        "sock_red": sock_red, "sock_blue": sock_blue,
        "shoe": shoe, "sole": sole, "seam": seam,
    }


# ---------------------------------------------------------------------------
# PRIMITIVE BUILDERS
# ---------------------------------------------------------------------------

def cube_part(name, location, scale, material, bevel=0.05,
              collection="10_BODY", rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = scale
    apply_transform(obj, location=False, rotation=False, scale=True)
    if material:
        obj.data.materials.append(material)
    if bevel:
        add_bevel(obj, bevel, CONFIG["bevel_segments"])
        add_weighted_normals(obj)
    move_to_collection(obj, collection)
    parent_to_root(obj)
    return obj


def uv_sphere(name, location, scale, material, segments=32, rings=20,
              collection="20_FACE", rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments, ring_count=rings, radius=1,
        location=location, rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    if material:
        obj.data.materials.append(material)
    smooth_mesh(obj)
    move_to_collection(obj, collection)
    parent_to_root(obj)
    return obj


def cylinder_part(name, location, radius, depth, material,
                  vertices=32, rotation=(0, 0, 0), bevel=0.025,
                  collection="30_CLOTHING"):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices, radius=radius, depth=depth,
        location=location, rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    if material:
        obj.data.materials.append(material)
    smooth_mesh(obj)
    if bevel:
        add_bevel(obj, bevel, 3)
    move_to_collection(obj, collection)
    parent_to_root(obj)
    return obj


def curve_tube(name, points, radius, material, collection="20_FACE",
               resolution=16, cyclic=False):
    """Create a smooth bevelled curve through a list of 3D points."""
    curve = bpy.data.curves.new(name, type="CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 24
    curve.bevel_depth = radius
    curve.bevel_resolution = 4
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for point, coordinate in zip(spline.bezier_points, points):
        point.co = coordinate
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, curve)
    get_collection(collection).objects.link(obj)
    if material:
        curve.materials.append(material)
    parent_to_root(obj)
    return obj


def mesh_from_rings(name, rings, material, collection="10_BODY",
                    segments=32, cap=True):
    """Build a closed ring-based mesh. Each ring is (center, rx, ry, z)."""
    vertices = []
    faces = []
    for center_x, center_y, z, radius_x, radius_y in rings:
        for index in range(segments):
            angle = 2 * pi * index / segments
            vertices.append((
                center_x + cos(angle) * radius_x,
                center_y + sin(angle) * radius_y,
                z,
            ))
    for ring_index in range(len(rings) - 1):
        for index in range(segments):
            a = ring_index * segments + index
            b = ring_index * segments + (index + 1) % segments
            c = (ring_index + 1) * segments + (index + 1) % segments
            d = (ring_index + 1) * segments + index
            faces.append((a, b, c, d))
    if cap:
        faces.append(tuple(range(segments - 1, -1, -1)))
        start = (len(rings) - 1) * segments
        faces.append(tuple(start + i for i in range(segments)))
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(material)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    get_collection(collection).objects.link(obj)
    smooth_mesh(obj)
    parent_to_root(obj)
    return obj


# ---------------------------------------------------------------------------
# BODY: SQUARE SPONGE SILHOUETTE
# ---------------------------------------------------------------------------

def create_body():
    """Create the iconic slightly wavy rectangular sponge body."""
    body = cube_part(
        "SpongeBody_Main", (0, 0, 3.82), (2.42, 0.82, 2.62),
        MATERIALS["yellow"], bevel=0.22,
    )
    # Add a subtle displacement modifier for a softly irregular sponge edge.
    texture = bpy.data.textures.new("Sponge edge micro waviness", type="CLOUDS")
    texture.noise_scale = 0.32
    displacement = body.modifiers.new("Very subtle sponge silhouette", "DISPLACE")
    displacement.texture = texture
    displacement.strength = 0.035
    displacement.mid_level = 0.5
    safe_set(displacement, "texture_coords", "LOCAL")
    # Smooth bevel edges while retaining a readable square silhouette.
    add_weighted_normals(body)

    # Lower body transition above the shorts.
    cube_part(
        "Lower sponge transition", (0, 0, 2.58), (2.28, 0.79, 0.22),
        MATERIALS["yellow"], 0.08,
    )
    return body


def create_pore(name, x, z, radius_x, radius_z, depth=0.018):
    """A pore is a dark inset oval plus a softly raised golden lip."""
    uv_sphere(
        name + "_Inset",
        (x, -0.414, z),
        (radius_x, depth, radius_z),
        MATERIALS["yellow_light"],
        24, 16, "15_SPONGE_PORES",
    )
    # A small highlight sits above the inset to suggest a rounded sponge rim.
    uv_sphere(
        name + "_RimHighlight",
        (x - radius_x * 0.22, -0.431, z + radius_z * 0.28),
        (radius_x * 0.48, depth * 0.34, radius_z * 0.16),
        MATERIALS["yellow_high"],
        16, 10, "15_SPONGE_PORES",
    )


def create_sponge_pores():
    """Place asymmetrical pores around the face and visible body edges."""
    pores = [
        (-1.00, 4.88, .105, .075), (-.72, 5.02, .055, .045),
        (.91, 4.98, .12, .08), (1.05, 4.62, .07, .10),
        (-1.06, 4.18, .075, .11), (-.96, 3.78, .06, .07),
        (.98, 3.95, .09, .065), (1.08, 3.58, .055, .09),
        (-1.02, 3.25, .12, .07), (.91, 3.12, .07, .05),
        (-.90, 2.98, .06, .05), (.72, 5.12, .045, .04),
        (-1.12, 4.52, .045, .04), (1.12, 4.28, .045, .06),
        (-.88, 5.18, .05, .035), (.98, 5.20, .05, .035),
        (-.72, 3.42, .045, .04), (.76, 3.42, .05, .04),
    ]
    for index, (x, z, rx, rz) in enumerate(pores):
        create_pore("SpongePore_%02d" % index, x, z, rx, rz)

    # Tiny side pores add depth when the model is viewed at an angle.
    for side in (-1, 1):
        for index, (y, z, size) in enumerate([
            (-.18, 4.95, .055), (.16, 4.48, .07),
            (-.12, 3.95, .045), (.18, 3.42, .06),
        ]):
            uv_sphere(
                "Side sponge pore %s %02d" % (side, index),
                (side * 1.216, y, z),
                (.018, size, size * 1.25),
                MATERIALS["yellow_light"], 18, 12, "15_SPONGE_PORES",
            )


# ---------------------------------------------------------------------------
# FACE: EYES, IRIS, PUPILS AND LASHES
# ---------------------------------------------------------------------------

def create_eye(side, x):
    """Construct one large protruding eye with layered iris geometry."""
    label = "Left" if side < 0 else "Right"
    center_z = 4.72
    # White eyeball.
    uv_sphere(
        label + "_EyeWhite",
        (x, -0.49, center_z),
        (0.49, 0.31, 0.61),
        MATERIALS["eye_white"], 48, 32,
    )
    # Blue iris facing the front (-Y).
    uv_sphere(
        label + "_Iris",
        (x + 0.025, -0.765, center_z - 0.015),
        (0.235, 0.085, 0.30),
        MATERIALS["blue"], 40, 28,
    )
    # Inner iris ring and radial flecks.
    uv_sphere(
        label + "_IrisInner",
        (x + 0.025, -0.833, center_z - 0.015),
        (0.155, 0.035, 0.215),
        MATERIALS["blue_light"], 32, 24,
    )
    # Pupil.
    uv_sphere(
        label + "_Pupil",
        (x + 0.035, -0.865, center_z - 0.02),
        (0.112, 0.045, 0.17),
        MATERIALS["black"], 32, 24,
    )
    # Two catchlights per eye.
    uv_sphere(
        label + "_EyeCatchlight_Large",
        (x - 0.015, -0.91, center_z + 0.105),
        (0.055, 0.022, 0.075),
        MATERIALS["eye_white"], 20, 14,
    )
    uv_sphere(
        label + "_EyeCatchlight_Small",
        (x + 0.09, -0.91, center_z - 0.12),
        (0.022, 0.015, 0.03),
        MATERIALS["eye_white"], 16, 10,
    )

    # Three distinct curved eyelashes above each eye.
    for lash_index in range(3):
        offset = (lash_index - 1) * 0.23
        start_x = x + offset
        start_z = center_z + 0.49
        end_x = start_x + (lash_index - 1) * 0.12
        curve_tube(
            label + "_Eyelash_%d" % lash_index,
            [
                (start_x, -0.48, start_z),
                (start_x + (lash_index - 1) * 0.035, -0.49, start_z + 0.17),
                (end_x, -0.49, start_z + 0.34),
            ],
            0.035, MATERIALS["black"], "20_FACE",
        )


def create_eyes():
    create_eye(-1, -0.53)
    create_eye(1, 0.53)


# ---------------------------------------------------------------------------
# NOSE, CHEEKS, FRECKLES AND SMILE
# ---------------------------------------------------------------------------

def create_nose():
    """A rounded protruding yellow nose, centered between the eyes."""
    nose = uv_sphere(
        "SpongeBob_Nose",
        (0.0, -0.79, 4.20),
        (0.145, 0.30, 0.34),
        MATERIALS["yellow"], 40, 28,
    )
    # Slight highlight gives the nose a soft cartoon finish.
    uv_sphere(
        "Nose soft highlight",
        (-0.045, -1.035, 4.31),
        (0.035, 0.018, 0.085),
        MATERIALS["yellow_high"], 18, 12,
    )
    return nose


def create_cheeks():
    """Build subtle raised cheek pads and warm blush accents."""
    for side in (-1, 1):
        uv_sphere(
            "CheekPad_%s" % side,
            (side * 0.69, -0.423, 3.93),
            (0.40, 0.075, 0.30),
            MATERIALS["yellow"], 32, 20,
        )
        uv_sphere(
            "CheekBlush_%s" % side,
            (side * 0.79, -0.505, 3.91),
            (0.19, 0.018, 0.105),
            MATERIALS["cheek"], 24, 16,
        )
        # Three tiny freckles arranged organically.
        freckles = [
            (side * .66, 4.02, .028),
            (side * .79, 4.08, .023),
            (side * .91, 3.99, .025),
        ]
        for index, (x, z, size) in enumerate(freckles):
            uv_sphere(
                "Freckle_%s_%d" % (side, index),
                (x, -0.535, z),
                (size, .012, size * .82),
                MATERIALS["freckle"], 16, 10,
            )


def create_mouth():
    """Layered smile opening, lower lip, tongue, teeth and smile corners."""
    # Mouth opening: flattened ellipsoid placed in front of the sponge.
    uv_sphere(
        "MouthOpening",
        (0, -0.465, 3.58),
        (0.64, 0.105, 0.34),
        MATERIALS["mouth"], 40, 28,
    )
    # Lower inner mouth / tongue.
    uv_sphere(
        "Tongue",
        (0.02, -0.579, 3.39),
        (0.27, 0.035, 0.105),
        MATERIALS["pink"], 32, 20,
    )
    # Tongue center crease.
    curve_tube(
        "Tongue center crease",
        [(0.02, -0.617, 3.35), (0.02, -0.619, 3.39),
         (0.02, -0.617, 3.43)],
        0.008, MATERIALS["red"],
    )
    # Two characteristic front teeth, individually modeled.
    cube_part(
        "FrontTooth_Left", (-0.105, -0.584, 3.735),
        (0.205, 0.085, 0.245), MATERIALS["tooth"], 0.035,
        "20_FACE",
    )
    cube_part(
        "FrontTooth_Right", (0.105, -0.584, 3.735),
        (0.205, 0.085, 0.245), MATERIALS["tooth"], 0.035,
        "20_FACE",
    )
    # A thin central division between the teeth.
    curve_tube(
        "Tooth separation line",
        [(0, -0.632, 3.62), (0, -0.632, 3.70), (0, -0.632, 3.82)],
        0.006, MATERIALS["brown_dark"],
    )
    # Smile corners and lower smile contour.
    curve_tube(
        "SmileLowerContour",
        [(-0.59, -0.54, 3.64), (-0.42, -0.57, 3.35),
         (0, -0.59, 3.29), (0.42, -0.57, 3.35),
         (0.59, -0.54, 3.64)],
        0.025, MATERIALS["yellow_light"],
    )
    uv_sphere("SmileCorner_L", (-0.59, -0.535, 3.64),
              (0.055, 0.025, 0.06), MATERIALS["yellow"], 18, 12)
    uv_sphere("SmileCorner_R", (0.59, -0.535, 3.64),
              (0.055, 0.025, 0.06), MATERIALS["yellow"], 18, 12)


# ---------------------------------------------------------------------------
# SHIRT, COLLAR, CUFFS AND TIE
# ---------------------------------------------------------------------------

def create_shirt():
    """White shirt band visible between sponge and brown shorts."""
    cube_part(
        "WhiteShirtBand", (0, 0, 2.48), (2.24, 0.80, 0.42),
        MATERIALS["white"], 0.07, "30_CLOTHING",
    )
    # Collar wings: two small angled white triangular-like pieces.
    left = cube_part(
        "Collar_Left", (-0.20, -0.435, 2.57), (0.36, 0.10, 0.22),
        MATERIALS["white"], 0.035, "30_CLOTHING",
        rotation=(0, radians(-16), radians(-5)),
    )
    right = cube_part(
        "Collar_Right", (0.20, -0.435, 2.57), (0.36, 0.10, 0.22),
        MATERIALS["white"], 0.035, "30_CLOTHING",
        rotation=(0, radians(16), radians(5)),
    )
    # Shirt seam line.
    curve_tube(
        "Shirt lower seam",
        [(-1.02, -0.414, 2.31), (0, -0.42, 2.30),
         (1.02, -0.414, 2.31)],
        0.012, MATERIALS["white"], "30_CLOTHING",
    )


def create_tie():
    """Red tie knot and tapered hanging blade."""
    uv_sphere(
        "TieKnot",
        (0, -0.51, 2.48),
        (0.13, 0.075, 0.13),
        MATERIALS["red"], 24, 16, "30_CLOTHING",
    )
    # Tie blade built as a beveled polygon mesh.
    verts = [
        (-0.105, -0.50, 2.40), (0.105, -0.50, 2.40),
        (0.145, -0.50, 1.98), (0.0, -0.50, 1.82),
        (-0.145, -0.50, 1.98),
        (-0.105, -0.43, 2.40), (0.105, -0.43, 2.40),
        (0.145, -0.43, 1.98), (0.0, -0.43, 1.82),
        (-0.145, -0.43, 1.98),
    ]
    faces = [
        (0, 1, 2, 3, 4), (5, 9, 8, 7, 6),
        (0, 5, 6, 1), (1, 6, 7, 2),
        (2, 7, 8, 3), (3, 8, 9, 4), (4, 9, 5, 0),
    ]
    mesh = bpy.data.meshes.new("TieBladeMesh")
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(MATERIALS["red"])
    mesh.update()
    blade = bpy.data.objects.new("TieBlade", mesh)
    get_collection("30_CLOTHING").objects.link(blade)
    bevel = blade.modifiers.new("Tie soft edges", "BEVEL")
    bevel.width = 0.035
    bevel.segments = 4
    add_weighted_normals(blade)
    parent_to_root(blade)


# ---------------------------------------------------------------------------
# SHORTS, BELT AND BUCKLE
# ---------------------------------------------------------------------------

def create_shorts():
    """Brown square shorts with soft edges and front seam details."""
    cube_part(
        "BrownSquareShorts", (0, 0, 1.98), (2.18, 0.84, 0.72),
        MATERIALS["brown"], 0.095, "40_LOWER_BODY",
    )
    # Slightly darker lower hem.
    cube_part(
        "ShortsLowerHem", (0, -0.005, 1.65), (2.10, 0.82, 0.12),
        MATERIALS["brown_dark"], 0.035, "40_LOWER_BODY",
    )
    # Front vertical seam.
    curve_tube(
        "ShortsCenterSeam",
        [(0, -0.431, 2.24), (0, -0.431, 2.00),
         (0, -0.431, 1.72)],
        0.009, MATERIALS["brown_dark"], "40_LOWER_BODY",
    )
    # Two pocket seam hints.
    for side in (-1, 1):
        curve_tube(
            "ShortsPocket_%s" % side,
            [(side * .70, -.435, 2.15),
             (side * .82, -.435, 2.02),
             (side * .70, -.435, 1.91)],
            0.012, MATERIALS["brown_dark"], "40_LOWER_BODY",
        )


def create_belt():
    """Dark belt and a centered brass rectangular buckle."""
    cube_part(
        "BeltBand", (0, -0.438, 2.30), (2.16, 0.075, 0.13),
        MATERIALS["belt"], 0.025, "40_LOWER_BODY",
    )
    # Buckle frame.
    cube_part(
        "BuckleOuter", (0, -0.493, 2.30), (0.34, 0.055, 0.20),
        MATERIALS["gold"], 0.025, "40_LOWER_BODY",
    )
    cube_part(
        "BuckleInset", (0, -0.528, 2.30), (0.235, 0.025, 0.105),
        MATERIALS["belt"], 0.012, "40_LOWER_BODY",
    )
    # Small brass pin.
    cylinder_part(
        "BucklePin", (0, -0.55, 2.30), 0.018, 0.06,
        MATERIALS["gold"], 16, (radians(90), 0, 0), 0.004,
        "40_LOWER_BODY",
    )


# ---------------------------------------------------------------------------
# ARMS, SLEEVES, HANDS AND FINGERS
# ---------------------------------------------------------------------------

def create_arm(side):
    """Create one short yellow arm emerging from the shirt sleeve."""
    label = "Left" if side < 0 else "Right"
    shoulder_x = side * 1.22
    # White sleeve puff.
    uv_sphere(
        label + "_Sleeve",
        (shoulder_x, 0, 2.55),
        (0.27, 0.32, 0.25),
        MATERIALS["white"], 28, 18, "50_ARMS",
    )
    # Upper arm and forearm.
    curve_tube(
        label + "_Arm",
        [(side * 1.30, -0.02, 2.43),
         (side * 1.42, -0.04, 2.16),
         (side * 1.48, -0.08, 1.91)],
        0.105, MATERIALS["yellow"], "50_ARMS",
    )
    # Wrist.
    uv_sphere(
        label + "_Wrist",
        (side * 1.48, -0.08, 1.88),
        (0.12, 0.12, 0.13),
        MATERIALS["yellow"], 24, 16, "50_ARMS",
    )
    create_hand(side, (side * 1.50, -0.10, 1.72), label)


def create_hand(side, center, label):
    """Palm and four fingers plus thumb; all fingers are individually modeled."""
    x, y, z = center
    uv_sphere(
        label + "_Palm",
        (x, y, z),
        (0.19, 0.13, 0.20),
        MATERIALS["yellow"], 28, 18, "50_ARMS",
    )
    # Four fingers fan gently outward and downward.
    finger_offsets = [
        (-0.14, -0.12, 0.10),
        (-0.045, -0.16, 0.18),
        (0.055, -0.16, 0.17),
        (0.15, -0.11, 0.11),
    ]
    for index, (dx, dz, length) in enumerate(finger_offsets):
        start = (x + side * dx * 0.55, y - 0.015, z - 0.04)
        middle = (x + side * dx, y - 0.025, z - length * 0.55)
        end = (x + side * dx * 1.12, y - 0.015, z - length)
        curve_tube(
            label + "_Finger_%d" % index,
            [start, middle, end],
            0.047, MATERIALS["yellow"], "50_ARMS",
        )
        uv_sphere(
            label + "_FingerTip_%d" % index,
            end, (0.047, 0.047, 0.05),
            MATERIALS["yellow"], 16, 12, "50_ARMS",
        )
    # Thumb points inward.
    thumb_end = (x - side * 0.22, y - 0.02, z + 0.01)
    curve_tube(
        label + "_Thumb",
        [(x - side * 0.12, y, z + 0.03),
         (x - side * 0.20, y - 0.02, z + 0.04),
         thumb_end],
        0.055, MATERIALS["yellow"], "50_ARMS",
    )


def create_arms():
    create_arm(-1)
    create_arm(1)


# ---------------------------------------------------------------------------
# LEGS, SOCKS AND SHOES
# ---------------------------------------------------------------------------

def create_leg(side):
    """Thin yellow leg, white sock with stripes, and black shoe."""
    label = "Left" if side < 0 else "Right"
    x = side * 0.62
    # Exposed yellow leg.
    cylinder_part(
        label + "_YellowLeg", (x, 0, 1.34), 0.105, 0.55,
        MATERIALS["yellow"], 24, (0, 0, 0), 0.035, "60_LEGS",
    )
    # Sock body.
    cylinder_part(
        label + "_Sock", (x, -0.005, 0.91), 0.145, 0.42,
        MATERIALS["sock_white"], 32, (0, 0, 0), 0.045, "60_LEGS",
    )
    # Red and blue horizontal stripes around the sock.
    for stripe_index, (z, material) in enumerate([
        (1.045, MATERIALS["sock_red"]),
        (0.995, MATERIALS["sock_blue"]),
    ]):
        bpy.ops.mesh.primitive_torus_add(
            major_radius=0.137, minor_radius=0.018,
            major_segments=32, minor_segments=10,
            location=(x, -0.005, z),
        )
        stripe = bpy.context.object
        stripe.name = label + "_SockStripe_%d" % stripe_index
        stripe.data.materials.append(material)
        smooth_mesh(stripe)
        move_to_collection(stripe, "60_LEGS")
        parent_to_root(stripe)

    # Shoe sole.
    uv_sphere(
        label + "_ShoeSole",
        (x, -0.17, 0.37),
        (0.43, 0.48, 0.105),
        MATERIALS["sole"], 36, 24, "60_LEGS",
    )
    # Shoe upper: broad rounded black toe pointing forward.
    uv_sphere(
        label + "_ShoeUpper",
        (x + side * 0.10, -0.20, 0.53),
        (0.40, 0.48, 0.22),
        MATERIALS["shoe"], 40, 28, "60_LEGS",
    )
    # Heel volume.
    uv_sphere(
        label + "_ShoeHeel",
        (x - side * 0.19, 0.035, 0.54),
        (0.20, 0.27, 0.22),
        MATERIALS["shoe"], 28, 18, "60_LEGS",
    )
    # Subtle top shoe seam.
    curve_tube(
        label + "_ShoeSeam",
        [(x - .18, -.48, .63), (x, -.54, .66),
         (x + .18, -.48, .63)],
        0.009, MATERIALS["seam"], "60_LEGS",
    )


def create_legs():
    create_leg(-1)
    create_leg(1)


# ---------------------------------------------------------------------------
# BACK AND SIDE DETAILS
# ---------------------------------------------------------------------------

def create_back_details():
    """Add restrained back-side pores so the model reads from multiple angles."""
    for index, (x, z, radius) in enumerate([
        (-.82, 4.72, .07), (.75, 4.92, .09),
        (-.98, 4.05, .055), (.96, 3.55, .065),
        (-.72, 3.02, .05), (.72, 3.15, .055),
    ]):
        uv_sphere(
            "BackPore_%02d" % index,
            (x, 0.414, z),
            (radius, .014, radius * .8),
            MATERIALS["yellow_light"], 18, 12, "15_SPONGE_PORES",
        )


# ---------------------------------------------------------------------------
# CHARACTER ORGANIZATION AND STUDIO
# ---------------------------------------------------------------------------

def create_character_root():
    global ROOT
    ROOT = create_empty("SPONGEBOB_CHARACTER_ROOT", (0, 0, 0))
    return ROOT


def create_floor():
    floor_mat = make_material("Studio floor - deep blue gray", (0.055, 0.075, 0.11), 0.82)
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, 0.12))
    floor = bpy.context.object
    floor.name = "StudioGround"
    floor.data.materials.append(floor_mat)
    move_to_collection(floor, "90_STUDIO")
    return floor


def aim_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def create_area_light(name, location, energy, color, size, target):
    bpy.ops.object.light_add(type="AREA", location=location)
    light = bpy.context.object
    light.name = name
    light.data.energy = energy
    light.data.color = color
    light.data.shape = "DISK"
    light.data.size = size
    aim_at(light, target)
    move_to_collection(light, "90_STUDIO")
    return light


def create_camera(name, location, target, lens=55):
    bpy.ops.object.camera_add(location=location)
    camera = bpy.context.object
    camera.name = name
    camera.data.lens = lens
    aim_at(camera, target)
    move_to_collection(camera, "90_STUDIO")
    return camera


def setup_studio():
    """Set a three-point studio lighting rig and a hero camera."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = CONFIG["samples"]
    safe_set(scene.cycles, "use_denoising", True)
    scene.render.resolution_x = CONFIG["resolution_x"]
    scene.render.resolution_y = CONFIG["resolution_y"]
    scene.render.resolution_percentage = CONFIG["resolution_percentage"]
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False

    world = bpy.data.worlds.new("SpongeBob Studio World") if not bpy.data.worlds else bpy.data.worlds[0]
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.12, 0.16, 0.22, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.35

    target = (0, 0, 3.0)
    create_area_light("Key - large softbox", (4.5, -6.0, 8.5), 950, (1.0, .83, .65), 5.0, target)
    create_area_light("Fill - cool softbox", (-5.0, -4.0, 5.0), 650, (.58, .75, 1.0), 4.0, target)
    create_area_light("Rim - warm backlight", (1.5, 4.0, 7.0), 1100, (1.0, .72, .38), 3.0, target)

    camera = create_camera("HeroCamera_ThreeQuarter", (5.7, -10.5, 5.1), (0, 0, 3.0), 58)
    scene.camera = camera
    # Additional cameras are included for inspection and later turntable use.
    create_camera("FrontCamera", (0, -12.5, 3.0), (0, 0, 3.0), 58)
    create_camera("SideCamera", (12.5, 0, 3.0), (0, 0, 3.0), 58)

    scene.view_settings.view_transform = "AgX"
    scene.render.image_settings.color_mode = "RGBA"
    return camera


# ---------------------------------------------------------------------------
# VALIDATION AND EXPORT
# ---------------------------------------------------------------------------

def validate_character():
    """Fail early if the model is missing key objects or has no mesh geometry."""
    required = [
        "SpongeBody_Main", "SpongeBob_Nose", "MouthOpening",
        "Left_EyeWhite", "Right_EyeWhite", "BrownSquareShorts",
        "TieBlade", "Left_ShoeUpper", "Right_ShoeUpper",
    ]
    missing = [name for name in required if bpy.data.objects.get(name) is None]
    if missing:
        raise RuntimeError("Required model objects missing: " + ", ".join(missing))

    mesh_objects = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    if len(mesh_objects) < 35:
        raise RuntimeError("Model contains unexpectedly few mesh objects: %d" % len(mesh_objects))

    for obj in mesh_objects:
        if len(obj.data.vertices) == 0:
            raise RuntimeError("Empty mesh detected: " + obj.name)

    print("Validation passed: %d mesh objects, %d total objects." %
          (len(mesh_objects), len(bpy.data.objects)))


def export_glb(filepath):
    """Export the complete scene to a binary glTF file."""
    output_dir = os.path.dirname(os.path.abspath(filepath))
    os.makedirs(output_dir, exist_ok=True)

    # Select all character geometry and studio objects for a self-contained scene.
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(
        filepath=filepath,
        export_format="GLB",
        use_selection=False,
        export_apply=True,
        export_materials="EXPORT",
        export_cameras=True,
        export_lights=True,
        export_yup=True,
    )
    if not os.path.exists(filepath):
        raise RuntimeError("GLB export did not create the expected file.")
    if os.path.getsize(filepath) < 10000:
        raise RuntimeError("GLB file is unexpectedly small; export may be incomplete.")
    print("GLB exported: %s (%d bytes)" % (filepath, os.path.getsize(filepath)))


def render_preview(filepath="out/preview.png"):
    """Optional still render for visual inspection in the Actions artifact."""
    output_dir = os.path.dirname(os.path.abspath(filepath))
    os.makedirs(output_dir, exist_ok=True)
    scene = bpy.context.scene
    scene.render.filepath = filepath
    bpy.ops.render.render(write_still=True)
    print("Preview rendered: " + filepath)


# ---------------------------------------------------------------------------
# BUILD PIPELINE
# ---------------------------------------------------------------------------

def build_spongebob():
    """Run all modeling stages in a deterministic order."""
    clear_scene()
    create_character_root()
    build_materials()

    # Main silhouette and surface.
    create_body()
    create_sponge_pores()
    create_back_details()

    # Facial features.
    create_eyes()
    create_nose()
    create_cheeks()
    create_mouth()

    # Clothing and anatomy.
    create_shirt()
    create_tie()
    create_shorts()
    create_belt()
    create_arms()
    create_legs()

    # Studio, camera, validation and export.
    setup_studio()
    validate_character()
    export_glb(CONFIG["output"])

    if CONFIG["render_preview"]:
        render_preview("out/preview.png")


def main():
    try:
        print("=" * 72)
        print("Starting SpongeBob procedural model build")
        print("Blender version:", bpy.app.version_string)
        print("=" * 72)
        build_spongebob()
        print("BUILD SUCCESS")
    except Exception as exc:
        print("Blender script failed: %s" % exc, file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# MODELING TUNING REFERENCE
# ---------------------------------------------------------------------------
# The following presets document the intended proportions and provide named
# values for artists who want to refine the model without hunting through the
# construction functions. The current build uses the corresponding values in
# the functions above; these dictionaries are also useful when extending the
# model into a rigged or animated asset.
#
# Coordinate convention:
#   X = character left/right
#   Y = depth (negative Y is the front)
#   Z = vertical
#
# Approximate landmarks:
#   shoe sole       Z 0.27
#   shoe upper      Z 0.53
#   sock center     Z 0.91
#   leg center      Z 1.34
#   shorts bottom   Z 1.65
#   shorts center   Z 1.98
#   belt            Z 2.30
#   shirt center    Z 2.48
#   body center     Z 3.82
#   eye center      Z 4.72
#   body top        Z 5.13
#
# These values deliberately preserve a recognizable cartoon silhouette:
# a large square sponge body, compact brown shorts, short thin legs, and
# oversized eyes. The model is not intended to imitate a live-action actor.
#
# Surface guidance:
#   Body roughness should remain high because a sponge is matte.
#   Eye roughness should remain low to produce clean studio catchlights.
#   Shoe roughness should be lower than the shorts to suggest polished leather.
#   Shirt and sock roughness should be high to suggest cotton fabric.
#   Tie roughness should be moderate so it reads as smooth cloth.
#
# Geometry guidance:
#   Keep the nose in front of the eye plane.
#   Keep the teeth in front of the mouth interior.
#   Keep the tongue below the tooth line.
#   Keep the collar behind the tie knot.
#   Keep the belt buckle in front of the belt band.
#   Keep the shoe sole slightly below the upper to avoid a floating shoe.
#
# Export guidance:
#   GLB stores mesh geometry, transforms, materials, cameras and lights.
#   Procedural Blender-only modifiers may be evaluated during export through
#   export_apply=True. Always inspect the exported GLB in a second viewer.
#   For a game engine, consider exporting only the character collection and
#   excluding the studio floor, lights and cameras.
#
# Suggested next-stage enhancements:
#   1. Build a skeleton with torso, head, arm, hand, leg and foot bones.
#   2. Add skinning weights for shoulder, elbow, wrist, hip and knee regions.
#   3. Add facial shape keys for blink, smile, frown and phoneme poses.
#   4. Add a turntable animation for portfolio presentation.
#   5. Create a second material variation with more visible sponge pores.
#   6. Add UVs and painted texture maps for hand-authored pore placement.
#   7. Add separate eye controllers for gaze direction.
#   8. Add a mouth cavity mesh with a more anatomically coherent inner surface.
#   9. Add cloth folds to the shirt and shorts.
#  10. Add sole tread and lace details to the shoes.
#
# Quality checklist for a manual review:
#   [ ] Front silhouette is balanced and centered.
#   [ ] Eyes are symmetrical but not mechanically identical.
#   [ ] Nose does not obscure the pupils.
#   [ ] Smile reads clearly from the hero camera.
#   [ ] Two front teeth remain visually separate.
#   [ ] Tie blade is centered under the collar.
#   [ ] Belt buckle is visible and not hidden by the tie.
#   [ ] Both hands have four fingers and a thumb.
#   [ ] Both socks show red and blue stripes.
#   [ ] Both shoes touch the ground plane.
#   [ ] Pores are distributed asymmetrically.
#   [ ] No disconnected floating decorative geometry is visible.
#   [ ] GLB opens correctly in an independent viewer.
#
# Important limitation:
#   This is a procedural first-pass asset. A claim of flawless likeness would
#   require rendered-image review and iterative corrections against approved
#   reference views. Geometry is intentionally built from editable objects.

# ---------------------------------------------------------------------------
# EXTENDED DETAIL PARAMETER CATALOG
# ---------------------------------------------------------------------------
# Named construction notes for controlled future revisions.
DETAIL_CATALOG = {
    "body_width": {"value": 2.42, "description": "Overall sponge body width"},
    "body_depth": {"value": 0.82, "description": "Overall sponge body depth"},
    "body_height": {"value": 2.62, "description": "Overall sponge body height"},
    "body_center_z": {"value": 3.82, "description": "Vertical center of sponge body"},
    "eye_spacing": {"value": 1.06, "description": "Horizontal eye center spacing"},
    "eye_radius_x": {"value": 0.49, "description": "Horizontal eyeball radius"},
    "eye_radius_z": {"value": 0.61, "description": "Vertical eyeball radius"},
    "iris_radius_x": {"value": 0.235, "description": "Horizontal iris radius"},
    "iris_radius_z": {"value": 0.30, "description": "Vertical iris radius"},
    "pupil_radius_x": {"value": 0.112, "description": "Horizontal pupil radius"},
    "nose_radius_x": {"value": 0.145, "description": "Nose horizontal radius"},
    "nose_radius_z": {"value": 0.34, "description": "Nose vertical radius"},
    "mouth_radius_x": {"value": 0.64, "description": "Mouth width radius"},
    "mouth_radius_z": {"value": 0.34, "description": "Mouth height radius"},
    "shorts_width": {"value": 2.18, "description": "Shorts width"},
    "shorts_height": {"value": 0.72, "description": "Shorts height"},
    "shirt_width": {"value": 2.24, "description": "Shirt band width"},
    "tie_width": {"value": 0.29, "description": "Maximum tie blade width"},
    "leg_radius": {"value": 0.105, "description": "Leg radius"},
    "sock_radius": {"value": 0.145, "description": "Sock radius"},
    "shoe_width": {"value": 0.80, "description": "Approximate shoe width"},
    "shoe_length": {"value": 0.96, "description": "Approximate shoe length"},
    "pore_count_front": {"value": 18, "description": "Front pore count"},
    "eyelashes_per_eye": {"value": 3, "description": "Lashes on each eye"},
    "fingers_per_hand": {"value": 5, "description": "Four fingers plus thumb"},
    "studio_key_energy": {"value": 950, "description": "Key light energy"},
    "studio_fill_energy": {"value": 650, "description": "Fill light energy"},
    "studio_rim_energy": {"value": 1100, "description": "Rim light energy"},
}

# Additional semantic labels make the Outliner easier to navigate.
# 01 - BODY: separately inspectable asset region.
# 02 - SPONGE_PORES: separately inspectable asset region.
# 03 - EYES: separately inspectable asset region.
# 04 - IRISES: separately inspectable asset region.
# 05 - PUPILS: separately inspectable asset region.
# 06 - EYELASHES: separately inspectable asset region.
# 07 - NOSE: separately inspectable asset region.
# 08 - CHEEKS: separately inspectable asset region.
# 09 - FRECKLES: separately inspectable asset region.
# 10 - MOUTH: separately inspectable asset region.
# 11 - TEETH: separately inspectable asset region.
# 12 - TONGUE: separately inspectable asset region.
# 13 - SHIRT: separately inspectable asset region.
# 14 - COLLAR: separately inspectable asset region.
# 15 - TIE: separately inspectable asset region.
# 16 - SHORTS: separately inspectable asset region.
# 17 - BELT: separately inspectable asset region.
# 18 - BUCKLE: separately inspectable asset region.
# 19 - SLEEVES: separately inspectable asset region.
# 20 - ARMS: separately inspectable asset region.
# 21 - PALMS: separately inspectable asset region.
# 22 - FINGERS: separately inspectable asset region.
# 23 - LEGS: separately inspectable asset region.
# 24 - SOCKS: separately inspectable asset region.
# 25 - SOCK_STRIPES: separately inspectable asset region.
# 26 - SHOES: separately inspectable asset region.
# 27 - SHOE_SOLES: separately inspectable asset region.
# 28 - STUDIO_LIGHTS: separately inspectable asset region.
# 29 - CAMERAS: separately inspectable asset region.
# 30 - GROUND: separately inspectable asset region.
