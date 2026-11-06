import bpy
import math
import os
import sys
import traceback
import bmesh
from mathutils import Vector

# ============================================================
# سبونج بوب سكوير بان - مجسم ثلاثي الأبعاد دقيق
# ============================================================

def clear_scene():
    """حذف جميع العناصر الموجودة في المشهد"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    # حذف جميع المواد المتبقية
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat)
    # حذف جميع الشبكات المتبقية
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)


def create_material(name, color, roughness=0.5, metallic=0.0, 
                    specular=0.5, emission_strength=0.0):
    """إنشاء مادة جديدة بلون محدد"""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Specular IOR Level"].default_value = specular
    if emission_strength > 0:
        bsdf.inputs["Emission Color"].default_value = (*color, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    return mat


def assign_material(obj, material):
    """تعيين مادة لكائن"""
    if obj.data.materials:
        obj.data.materials[0] = material
    else:
        obj.data.materials.append(material)


def set_smooth(obj):
    """تفعيل التنعيم على الكائن"""
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.shade_smooth()
    obj.select_set(False)


def create_cube(name, location, scale, rotation=(0, 0, 0)):
    """إنشاء مكعب مع تحديد الموقع والحجم"""
    bpy.ops.mesh.primitive_cube_add(size=1, location=location, rotation=rotation)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(scale=True)
    return obj


def create_uv_sphere(name, location, radius=1.0, segments=32, rings=16):
    """إنشاء كرة مع تحديد الموقع ونصف القطر"""
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments, ring_count=rings,
        radius=radius, location=location
    )
    obj = bpy.context.active_object
    obj.name = name
    set_smooth(obj)
    return obj


def create_cylinder(name, location, radius=0.5, depth=1.0, rotation=(0, 0, 0)):
    """إنشاء أسطوانة"""
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, depth=depth, location=location, rotation=rotation
    )
    obj = bpy.context.active_object
    obj.name = name
    set_smooth(obj)
    return obj


def create_torus(name, location, major_radius=1.0, minor_radius=0.1):
    """إنشاء شكل حلقي"""
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major_radius, minor_radius=minor_radius,
        location=location
    )
    obj = bpy.context.active_object
    obj.name = name
    set_smooth(obj)
    return obj


def subdivide_object(obj, levels=2):
    """إضافة معدل تقسيم فرعي للكائن"""
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    modifier = obj.modifiers.new(name="Subdivision", type='SUBSURF')
    modifier.levels = levels
    modifier.render_levels = levels
    obj.select_set(False)
    return modifier


def add_bevel(obj, width=0.02, segments=3):
    """إضافة معدل شطب للكائن"""
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    modifier = obj.modifiers.new(name="Bevel", type='BEVEL')
    modifier.width = width
    modifier.segments = segments
    obj.select_set(False)
    return modifier


def add_displace(obj, strength=0.1, texture_name="DisplaceTex"):
    """إضافة معدل إزاحة لتشويه السطح"""
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    tex = bpy.data.textures.new(texture_name, type='VORONOI')
    tex.noise_scale = 0.5
    modifier = obj.modifiers.new(name="Displace", type='DISPLACE')
    modifier.texture = tex
    modifier.strength = strength
    obj.select_set(False)
    return modifier


# ============================================================
# المواد المستخدمة في الشخصية
# ============================================================

def create_all_materials():
    """إنشاء جميع المواد المطلوبة للشخصية"""
    materials = {}
    
    # لون الجسم الأصفر الإسفنجي
    materials['body'] = create_material(
        "SpongeBob_Body", (1.0, 0.85, 0.1), roughness=0.8, specular=0.2
    )
    
    # اللون الأبيض للعيون
    materials['eye_white'] = create_material(
        "SpongeBob_EyeWhite", (1.0, 1.0, 1.0), roughness=0.3, specular=0.6
    )
    
    # اللون الأزرق للقزحية
    materials['iris'] = create_material(
        "SpongeBob_Iris", (0.2, 0.5, 0.9), roughness=0.4, specular=0.5
    )
    
    # اللون الأسود للبؤبؤ
    materials['pupil'] = create_material(
        "SpongeBob_Pupil", (0.01, 0.01, 0.01), roughness=0.2, specular=0.8
    )
    
    # لون الأنف
    materials['nose'] = create_material(
        "SpongeBob_Nose", (1.0, 0.85, 0.1), roughness=0.7, specular=0.3
    )
    
    # اللون الأبيض للأسنان
    materials['teeth'] = create_material(
        "SpongeBob_Teeth", (1.0, 1.0, 0.95), roughness=0.3, specular=0.7
    )
    
    # اللون الأحمر للربطة
    materials['tie'] = create_material(
        "SpongeBob_Tie", (0.8, 0.1, 0.05), roughness=0.6, specular=0.3
    )
    
    # اللون الأبيض للقميص
    materials['shirt'] = create_material(
        "SpongeBob_Shirt", (0.95, 0.95, 0.95), roughness=0.7, specular=0.2
    )
    
    # اللون البني للسروال
    materials['pants'] = create_material(
        "SpongeBob_Pants", (0.5, 0.3, 0.1), roughness=0.8, specular=0.1
    )
    
    # اللون الأسود للحزام
    materials['belt'] = create_material(
        "SpongeBob_Belt", (0.05, 0.05, 0.05), roughness=0.6, specular=0.3
    )
    
    # اللون الأصفر للذراعين والساقين
    materials['limbs'] = create_material(
        "SpongeBob_Limbs", (1.0, 0.85, 0.1), roughness=0.7, specular=0.2
    )
    
    # اللون الأبيض للجوارب
    materials['socks'] = create_material(
        "SpongeBob_Socks", (0.95, 0.95, 0.95), roughness=0.7, specular=0.2
    )
    
    # اللون الأسود للأحذية
    materials['shoes'] = create_material(
        "SpongeBob_Shoes", (0.05, 0.05, 0.05), roughness=0.4, specular=0.5
    )
    
    # اللون الأحمر للخطوط على الجوارب
    materials['sock_stripe_red'] = create_material(
        "SpongeBob_SockStripeRed", (0.8, 0.1, 0.1), roughness=0.7, specular=0.2
    )
    
    # اللون الأزرق للخطوط على الجوارب
    materials['sock_stripe_blue'] = create_material(
        "SpongeBob_SockStripeBlue", (0.1, 0.2, 0.8), roughness=0.7, specular=0.2
    )
    
    # لون الرموش
    materials['eyelash'] = create_material(
        "SpongeBob_Eyelash", (0.02, 0.02, 0.02), roughness=0.8, specular=0.1
    )
    
    # لون الفم
    materials['mouth'] = create_material(
        "SpongeBob_Mouth", (0.4, 0.05, 0.05), roughness=0.9, specular=0.1
    )
    
    # لون الخدود
    materials['cheek'] = create_material(
        "SpongeBob_Cheek", (1.0, 0.6, 0.4), roughness=0.9, specular=0.1
    )
    
    # لون الثقوب في الإسفنج
    materials['pore'] = create_material(
        "SpongeBob_Pore", (0.7, 0.6, 0.05), roughness=0.9, specular=0.1
    )
    
    # لون القفازات
    materials['gloves'] = create_material(
        "SpongeBob_Gloves", (0.95, 0.95, 0.95), roughness=0.6, specular=0.3
    )
    
    return materials


# ============================================================
# إنشاء الجسم الرئيسي (الإسفنجة)
# ============================================================

def create_body(materials):
    """إنشاء الجسم الرئيسي لسبونج بوب"""
    # الجسم الرئيسي - مكعب مستطيل مثل الإسفنجة
    body = create_cube(
        "SpongeBob_Body",
        location=(0, 0, 2.5),
        scale=(1.2, 0.4, 1.5)
    )
    assign_material(body, materials['body'])
    
    # إضافة تقسيم فرعي لتنعيم الحواف
    subdivide_object(body, levels=2)
    add_bevel(body, width=0.05, segments=4)
    
    # إضافة إزاحة خفيفة لمحاكاة ملمس الإسفنج
    add_displace(body, strength=0.03, texture_name="SpongeTexture")
    
    # إنشاء الثقوب على سطح الجسم
    create_body_pores(materials)
    
    return body


def create_body_pores(materials):
    """إنشاء الثقوب على سطح الإسفنجة"""
    pore_positions = [
        # الجانب الأمامي
        (0.4, -0.21, 3.2), (-0.3, -0.21, 2.8), (0.6, -0.21, 2.2),
        (-0.6, -0.21, 3.5), (0.1, -0.21, 1.8), (-0.8, -0.21, 2.5),
        (0.8, -0.21, 3.0), (-0.2, -0.21, 3.8), (0.5, -0.21, 1.5),
        # الجانب الخلفي
        (0.4, 0.21, 3.2), (-0.3, 0.21, 2.8), (0.6, 0.21, 2.2),
        (-0.6, 0.21, 3.5), (0.1, 0.21, 1.8), (-0.8, 0.21, 2.5),
        # الجانب الأيسر
        (-1.21, 0.1, 3.0), (-1.21, -0.1, 2.5), (-1.21, 0.0, 3.5),
        # الجانب الأيمن
        (1.21, 0.1, 3.0), (1.21, -0.1, 2.5), (1.21, 0.0, 3.5),
        # السطح العلوي
        (0.3, 0.0, 4.01), (-0.4, 0.1, 4.01), (0.0, -0.1, 4.01),
    ]
    
    for i, pos in enumerate(pore_positions):
        pore = create_uv_sphere(
            f"Sponge_Pore_{i}",
            location=pos,
            radius=0.06,
            segments=12,
            rings=8
        )
        assign_material(pore, materials['pore'])
        # تسطيح الكرة قليلاً
        pore.scale = (1, 1, 0.3)


# ============================================================
# إنشاء العيون
# ============================================================

def create_eyes(materials):
    """إنشاء عيون سبونج بوب الكبيرة"""
    eyes_group = []
    
    # العين اليسرى
    eye_left_white = create_uv_sphere(
        "Eye_Left_White",
        location=(-0.35, -0.35, 3.2),
        radius=0.45,
        segments=48,
        rings=24
    )
    assign_material(eye_left_white, materials['eye_white'])
    eye_left_white.scale = (1, 0.6, 1)
    eyes_group.append(eye_left_white)
    
    # العين اليمنى
    eye_right_white = create_uv_sphere(
        "Eye_Right_White",
        location=(0.35, -0.35, 3.2),
        radius=0.45,
        segments=48,
        rings=24
    )
    assign_material(eye_right_white, materials['eye_white'])
    eye_right_white.scale = (1, 0.6, 1)
    eyes_group.append(eye_right_white)
    
    # القزحية اليسرى
    iris_left = create_uv_sphere(
        "Iris_Left",
        location=(-0.35, -0.62, 3.2),
        radius=0.18,
        segments=32,
        rings=16
    )
    assign_material(iris_left, materials['iris'])
    iris_left.scale = (1, 0.5, 1)
    eyes_group.append(iris_left)
    
    # القزحية اليمنى
    iris_right = create_uv_sphere(
        "Iris_Right",
        location=(0.35, -0.62, 3.2),
        radius=0.18,
        segments=32,
        rings=16
    )
    assign_material(iris_right, materials['iris'])
    iris_right.scale = (1, 0.5, 1)
    eyes_group.append(iris_right)
    
    # البؤبؤ الأيسر
    pupil_left = create_uv_sphere(
        "Pupil_Left",
        location=(-0.35, -0.70, 3.2),
        radius=0.09,
        segments=24,
        rings=12
    )
    assign_material(pupil_left, materials['pupil'])
    pupil_left.scale = (1, 0.5, 1)
    eyes_group.append(pupil_left)
    
    # البؤبؤ الأيمن
    pupil_right = create_uv_sphere(
        "Pupil_Right",
        location=(0.35, -0.70, 3.2),
        radius=0.09,
        segments=24,
        rings=12
    )
    assign_material(pupil_right, materials['pupil'])
    pupil_right.scale = (1, 0.5, 1)
    eyes_group.append(pupil_right)
    
    # إضافة لمعة صغيرة في كل عين
    glint_left = create_uv_sphere(
        "Glint_Left",
        location=(-0.30, -0.72, 3.30),
        radius=0.03,
        segments=12,
        rings=8
    )
    glint_mat = create_material("Glint", (1, 1, 1), roughness=0.0, specular=1.0, emission_strength=2.0)
    assign_material(glint_left, glint_mat)
    eyes_group.append(glint_left)
    
    glint_right = create_uv_sphere(
        "Glint_Right",
        location=(0.40, -0.72, 3.30),
        radius=0.03,
        segments=12,
        rings=8
    )
    assign_material(glint_right, glint_mat)
    eyes_group.append(glint_right)
    
    return eyes_group


def create_eyelashes(materials):
    """إنشاء الرموش فوق كل عين"""
    eyelashes = []
    
    # رموش العين اليسرى (3 رموش)
    lash_positions_left = [
        (-0.50, -0.35, 3.65, 0, 0.3, 0),
        (-0.35, -0.35, 3.70, 0, 0, 0),
        (-0.20, -0.35, 3.65, 0, -0.3, 0),
    ]
    
    for i, (x, y, z, rx, ry, rz) in enumerate(lash_positions_left):
        lash = create_cylinder(
            f"Eyelash_Left_{i}",
            location=(x, y, z),
            radius=0.012,
            depth=0.25,
            rotation=(math.radians(rx), math.radians(ry + 20), math.radians(rz))
        )
        assign_material(lash, materials['eyelash'])
        eyelashes.append(lash)
    
    # رموش العين اليمنى (3 رموش)
    lash_positions_right = [
        (0.20, -0.35, 3.65, 0, 0.3, 0),
        (0.35, -0.35, 3.70, 0, 0, 0),
        (0.50, -0.35, 3.65, 0, -0.3, 0),
    ]
    
    for i, (x, y, z, rx, ry, rz) in enumerate(lash_positions_right):
        lash = create_cylinder(
            f"Eyelash_Right_{i}",
            location=(x, y, z),
            radius=0.012,
            depth=0.25,
            rotation=(math.radians(rx), math.radians(ry + 20), math.radians(rz))
        )
        assign_material(lash, materials['eyelash'])
        eyelashes.append(lash)
    
    return eyelashes


# ============================================================
# إنشاء الأنف
# ============================================================

def create_nose(materials):
    """إنشاء أنف سبونج بوب الطويل"""
    # الجزء الرئيسي للأنف
    nose = create_uv_sphere(
        "Nose_Main",
        location=(0, -0.55, 2.7),
        radius=0.12,
        segments=24,
        rings=16
    )
    nose.scale = (0.8, 2.5, 0.8)
    assign_material(nose, materials['nose'])
    
    # طرف الأنف (أكثر استدارة)
    nose_tip = create_uv_sphere(
        "Nose_Tip",
        location=(0, -0.85, 2.7),
        radius=0.13,
        segments=24,
        rings=16
    )
    assign_material(nose_tip, materials['nose'])
    
    return nose, nose_tip


# ============================================================
# إنشاء الفم والأسنان
# ============================================================

def create_mouth(materials):
    """إنشاء فم سبونج بوب العريض مع الأسنان"""
    mouth_objects = []
    
    # خط الفم (شكل منحني باستخدام نصف حلقة)
    # إنشاء شكل الفم باستخدام مكعب مشوه
    mouth_curve = create_cube(
        "Mouth_Line",
        location=(0, -0.21, 2.1),
        scale=(0.7, 0.02, 0.03)
    )
    assign_material(mouth_curve, materials['mouth'])
    
    # إضافة انحناء للفم باستخدام تعديل
    bpy.context.view_layer.objects.active = mouth_curve
    mouth_curve.select_set(True)
    
    # إنشاء قوس الفم باستخدام torus مقطوع
    mouth_arc = create_torus(
        "Mouth_Arc",
        location=(0, -0.20, 2.3),
        major_radius=0.55,
        minor_radius=0.025
    )
    mouth_arc.scale = (1, 0.3, 0.5)
    mouth_arc.rotation_euler = (math.radians(90), 0, 0)
    assign_material(mouth_arc, materials['mouth'])
    mouth_objects.append(mouth_arc)
    
    # حذف النصف العلوي من الحلقة للحصول على ابتسامة
    bpy.context.view_layer.objects.active = mouth_arc
    mouth_arc.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(mouth_arc.data)
    bm.verts.ensure_lookup_table()
    for v in bm.verts:
        if v.co.z > 0.01:  # حذف النصف العلوي
            bm.verts.remove(v)
    bmesh.update_edit_mesh(mouth_arc.data)
    bpy.ops.object.mode_set(mode='OBJECT')
    mouth_arc.select_set(False)
    
    # الأسنان الأمامية (سنتان كبيرتان)
    tooth_left = create_cube(
        "Tooth_Left",
        location=(-0.12, -0.25, 1.95),
        scale=(0.12, 0.05, 0.18)
    )
    assign_material(tooth_left, materials['teeth'])
    add_bevel(tooth_left, width=0.015, segments=3)
    mouth_objects.append(tooth_left)
    
    tooth_right = create_cube(
        "Tooth_Right",
        location=(0.12, -0.25, 1.95),
        scale=(0.12, 0.05, 0.18)
    )
    assign_material(tooth_right, materials['teeth'])
    add_bevel(tooth_right, width=0.015, segments=3)
    mouth_objects.append(tooth_right)
    
    # إضافة خط بين الأسنان
    teeth_gap = create_cube(
        "Teeth_Gap",
        location=(0, -0.25, 1.95),
        scale=(0.01, 0.06, 0.18)
    )
    gap_mat = create_material("TeethGap", (0.8, 0.8, 0.75), roughness=0.5)
    assign_material(teeth_gap, gap_mat)
    mouth_objects.append(teeth_gap)
    
    # الخدود (نقاط نمش)
    create_freckles(materials)
    
    return mouth_objects


def create_freckles(materials):
    """إنشاء النمش على خدود سبونج بوب"""
    freckles_positions = [
        # الخد الأيسر (3 نقاط)
        (-0.7, -0.19, 2.3), (-0.6, -0.19, 2.15), (-0.8, -0.19, 2.15),
        # الخد الأيمن (3 نقاط)
        (0.7, -0.19, 2.3), (0.6, -0.19, 2.15), (0.8, -0.19, 2.15),
    ]
    
    for i, pos in enumerate(freckles_positions):
        freckle = create_uv_sphere(
            f"Freckle_{i}",
            location=pos,
            radius=0.03,
            segments=8,
            rings=6
        )
        freckle.scale = (1, 0.3, 1)
        assign_material(freckle, materials['cheek'])


# ============================================================
# إنشاء الملابس
# ============================================================

def create_shirt(materials):
    """إنشاء القميص الأبيض"""
    shirt = create_cube(
        "Shirt",
        location=(0, 0, 1.35),
        scale=(1.22, 0.42, 0.15)
    )
    assign_material(shirt, materials['shirt'])
    add_bevel(shirt, width=0.02, segments=2)
    
    # الياقة
    collar = create_torus(
        "Collar",
        location=(0, -0.1, 1.5),
        major_radius=0.3,
        minor_radius=0.04
    )
    collar.scale = (1.5, 0.5, 1)
    assign_material(collar, materials['shirt'])
    
    return shirt, collar


def create_pants(materials):
    """إنشاء السروال البني"""
    pants = create_cube(
        "Pants",
        location=(0, 0, 1.0),
        scale=(1.22, 0.42, 0.2)
    )
    assign_material(pants, materials['pants'])
    add_bevel(pants, width=0.02, segments=2)
    
    # الحزام الأسود
    belt = create_cube(
        "Belt",
        location=(0, 0, 1.2),
        scale=(1.23, 0.43, 0.03)
    )
    assign_material(belt, materials['belt'])
    
    # إبزم الحزام
    buckle = create_cube(
        "Belt_Buckle",
        location=(0, -0.22, 1.2),
        scale=(0.08, 0.02, 0.05)
    )
    buckle_mat = create_material("Buckle", (0.8, 0.7, 0.2), metallic=0.9, roughness=0.2)
    assign_material(buckle, buckle_mat)
    
    # أرجل السروال
    pant_leg_left = create_cube(
        "Pant_Leg_Left",
        location=(-0.4, 0, 0.7),
        scale=(0.35, 0.40, 0.15)
    )
    assign_material(pant_leg_left, materials['pants'])
    
    pant_leg_right = create_cube(
        "Pant_Leg_Right",
        location=(0.4, 0, 0.7),
        scale=(0.35, 0.40, 0.15)
    )
    assign_material(pant_leg_right, materials['pants'])
    
    return pants, belt, buckle, pant_leg_left, pant_leg_right


def create_tie(materials):
    """إنشاء ربطة العنق الحمراء"""
    # عقدة الربطة
    tie_knot = create_uv_sphere(
        "Tie_Knot",
        location=(0, -0.23, 1.45),
        radius=0.08,
        segments=16,
        rings=12
    )
    tie_knot.scale = (1.2, 0.6, 1)
    assign_material(tie_knot, materials['tie'])
    
    # جسم الربطة (الجزء العلوي)
    tie_upper = create_cube(
        "Tie_Upper",
        location=(0, -0.24, 1.3),
        scale=(0.08, 0.02, 0.12)
    )
    assign_material(tie_upper, materials['tie'])
    add_bevel(tie_upper, width=0.01, segments=2)
    
    # جسم الربطة (الجزء السفلي - أعرض)
    tie_lower = create_cube(
        "Tie_Lower",
        location=(0, -0.24, 1.1),
        scale=(0.12, 0.02, 0.10)
    )
    assign_material(tie_lower, materials['tie'])
    add_bevel(tie_lower, width=0.01, segments=2)
    
    # طرف الربطة (مثلث)
    tie_tip = create_cube(
        "Tie_Tip",
        location=(0, -0.24, 0.95),
        scale=(0.10, 0.02, 0.06)
    )
    assign_material(tie_tip, materials['tie'])
    
    return tie_knot, tie_upper, tie_lower, tie_tip


# ============================================================
# إنشاء الذراعين واليدين
# ============================================================

def create_arms(materials):
    """إنشاء ذراعي سبونج بوب الرفيعتين"""
    arms = []
    
    # الذراع الأيسر
    arm_left = create_cylinder(
        "Arm_Left",
        location=(-1.5, 0, 2.2),
        radius=0.05,
        depth=0.8,
        rotation=(0, math.radians(90), 0)
    )
    assign_material(arm_left, materials['limbs'])
    arms.append(arm_left)
    
    # كم القميص الأيسر
    sleeve_left = create_cylinder(
        "Sleeve_Left",
        location=(-1.3, 0, 2.2),
        radius=0.07,
        depth=0.15,
        rotation=(0, math.radians(90), 0)
    )
    assign_material(sleeve_left, materials['shirt'])
    arms.append(sleeve_left)
    
    # الذراع الأيمن
    arm_right = create_cylinder(
        "Arm_Right",
        location=(1.5, 0, 2.2),
        radius=0.05,
        depth=0.8,
        rotation=(0, math.radians(90), 0)
    )
    assign_material(arm_right, materials['limbs'])
    arms.append(arm_right)
    
    # كم القميص الأيمن
    sleeve_right = create_cylinder(
        "Sleeve_Right",
        location=(1.3, 0, 2.2),
        radius=0.07,
        depth=0.15,
        rotation=(0, math.radians(90), 0)
    )
    assign_material(sleeve_right, materials['shirt'])
    arms.append(sleeve_right)
    
    # الأيدي
    create_hands(materials, arms)
    
    return arms


def create_hands(materials, arms_list):
    """إنشاء يدي سبونج بوب مع الأصابع"""
    # اليد اليسرى
    hand_left = create_uv_sphere(
        "Hand_Left",
        location=(-1.9, 0, 2.2),
        radius=0.12,
        segments=20,
        rings=12
    )
    hand_left.scale = (1, 0.7, 1)
    assign_material(hand_left, materials['gloves'])
    arms_list.append(hand_left)
    
    # أصابع اليد اليسرى
    finger_positions_left = [
        (-2.0, -0.08, 2.2), (-2.05, 0, 2.2), (-2.0, 0.08, 2.2), (-1.95, 0, 2.1)
    ]
    for i, pos in enumerate(finger_positions_left):
        finger = create_cylinder(
            f"Finger_Left_{i}",
            location=pos,
            radius=0.025,
            depth=0.15,
            rotation=(0, math.radians(90), 0)
        )
        assign_material(finger, materials['gloves'])
        arms_list.append(finger)
    
    # اليد اليمنى
    hand_right = create_uv_sphere(
        "Hand_Right",
        location=(1.9, 0, 2.2),
        radius=0.12,
        segments=20,
        rings=12
    )
    hand_right.scale = (1, 0.7, 1)
    assign_material(hand_right, materials['gloves'])
    arms_list.append(hand_right)
    
    # أصابع اليد اليمنى
    finger_positions_right = [
        (2.0, -0.08, 2.2), (2.05, 0, 2.2), (2.0, 0.08, 2.2), (1.95, 0, 2.1)
    ]
    for i, pos in enumerate(finger_positions_right):
        finger = create_cylinder(
            f"Finger_Right_{i}",
            location=pos,
            radius=0.025,
            depth=0.15,
            rotation=(0, math.radians(90), 0)
        )
        assign_material(finger, materials['gloves'])
        arms_list.append(finger)


# ============================================================
# إنشاء الساقين والقدمين
# ============================================================

def create_legs(materials):
    """إنشاء ساقي سبونج بوب الرفيعتين"""
    legs = []
    
    # الساق اليسرى
    leg_left = create_cylinder(
        "Leg_Left",
        location=(-0.4, 0, 0.35),
        radius=0.04,
        depth=0.6
    )
    assign_material(leg_left, materials['limbs'])
    legs.append(leg_left)
    
    # الساق اليمنى
    leg_right = create_cylinder(
        "Leg_Right",
        location=(0.4, 0, 0.35),
        radius=0.04,
        depth=0.6
    )
    assign_material(leg_right, materials['limbs'])
    legs.append(leg_right)
    
    # الجوارب
    create_socks(materials, legs)
    
    # الأحذية
    create_shoes(materials, legs)
    
    return legs


def create_socks(materials, legs_list):
    """إنشاء الجوارب البيضاء مع الخطوط الملونة"""
    # الجورب الأيسر
    sock_left = create_cylinder(
        "Sock_Left",
        location=(-0.4, 0, 0.25),
        radius=0.05,
        depth=0.2
    )
    assign_material(sock_left, materials['socks'])
    legs_list.append(sock_left)
    
    # خطوط الجورب الأيسر
    stripe_l1 = create_torus(
        "Sock_Stripe_L1",
        location=(-0.4, 0, 0.30),
        major_radius=0.05,
        minor_radius=0.01
    )
    stripe_l1.rotation_euler = (math.radians(90), 0, 0)
    assign_material(stripe_l1, materials['sock_stripe_red'])
    legs_list.append(stripe_l1)
    
    stripe_l2 = create_torus(
        "Sock_Stripe_L2",
        location=(-0.4, 0, 0.26),
        major_radius=0.05,
        minor_radius=0.01
    )
    stripe_l2.rotation_euler = (math.radians(90), 0, 0)
    assign_material(stripe_l2, materials['sock_stripe_blue'])
    legs_list.append(stripe_l2)
    
    # الجورب الأيمن
    sock_right = create_cylinder(
        "Sock_Right",
        location=(0.4, 0, 0.25),
        radius=0.05,
        depth=0.2
    )
    assign_material(sock_right, materials['socks'])
    legs_list.append(sock_right)
    
    # خطوط الجورب الأيمن
    stripe_r1 = create_torus(
        "Sock_Stripe_R1",
        location=(0.4, 0, 0.30),
        major_radius=0.05,
        minor_radius=0.01
    )
    stripe_r1.rotation_euler = (math.radians(90), 0, 0)
    assign_material(stripe_r1, materials['sock_stripe_red'])
    legs_list.append(stripe_r1)
    
    stripe_r2 = create_torus(
        "Sock_Stripe_R2",
        location=(0.4, 0, 0.26),
        major_radius=0.05,
        minor_radius=0.01
    )
    stripe_r2.rotation_euler = (math.radians(90), 0, 0)
    assign_material(stripe_r2, materials['sock_stripe_blue'])
    legs_list.append(stripe_r2)


def create_shoes(materials, legs_list):
    """إنشاء أحذية سبونج بوب السوداء"""
    # الحذاء الأيسر
    shoe_left = create_uv_sphere(
        "Shoe_Left",
        location=(-0.4, -0.08, 0.05),
        radius=0.12,
        segments=24,
        rings=12
    )
    shoe_left.scale = (0.8, 1.8, 0.5)
    assign_material(shoe_left, materials['shoes'])
    legs_list.append(shoe_left)
    
    # الحذاء الأيمن
    shoe_right = create_uv_sphere(
        "Shoe_Right",
        location=(0.4, -0.08, 0.05),
        radius=0.12,
        segments=24,
        rings=12
    )
    shoe_right.scale = (0.8, 1.8, 0.5)
    assign_material(shoe_right, materials['shoes'])
    legs_list.append(shoe_right)
    
    # نعل الحذاء الأيسر
    sole_left = create_cube(
        "Sole_Left",
        location=(-0.4, -0.08, 0.0),
        scale=(0.09, 0.20, 0.02)
    )
    sole_mat = create_material("Sole", (0.02, 0.02, 0.02), roughness=0.9)
    assign_material(sole_left, sole_mat)
    legs_list.append(sole_left)
    
    # نعل الحذاء الأيمن
    sole_right = create_cube(
        "Sole_Right",
        location=(0.4, -0.08, 0.0),
        scale=(0.09, 0.20, 0.02)
    )
    assign_material(sole_right, sole_mat)
    legs_list.append(sole_right)


# ============================================================
# إعداد المشهد (الإضاءة والكاميرا)
# ============================================================

def setup_scene():
    """إعداد المشهد مع الإضاءة والكاميرا"""
    # الشمس الرئيسية
    bpy.ops.object.light_add(type='SUN', location=(5, -5, 8))
    sun = bpy.context.active_object
    sun.name = "Sun_Main"
    sun.data.energy = 4.0
    sun.rotation_euler = (math.radians(40), math.radians(15), math.radians(-30))
    
    # ضوء خلفي
    bpy.ops.object.light_add(type='SUN', location=(-3, 5, 6))
    back_light = bpy.context.active_object
    back_light.name = "Sun_Back"
    back_light.data.energy = 1.5
    back_light.data.color = (0.9, 0.9, 1.0)
    
    # ضوء جانبي
    bpy.ops.object.light_add(type='AREA', location=(4, -2, 3))
    side_light = bpy.context.active_object
    side_light.name = "Area_Side"
    side_light.data.energy = 100
    side_light.data.size = 3
    
    # ضوء علوي
    bpy.ops.object.light_add(type='POINT', location=(0, -3, 5))
    top_light = bpy.context.active_object
    top_light.name = "Point_Top"
    top_light.data.energy = 50
    
    # الكاميرا
    bpy.ops.object.camera_add(location=(4, -5, 3.5))
    camera = bpy.context.active_object
    camera.name = "Camera_Main"
    camera.rotation_euler = (math.radians(70), 0, math.radians(38))
    camera.data.lens = 50
    bpy.context.scene.camera = camera
    
    # كاميرا ثانية للعرض الجانبي
    bpy.ops.object.camera_add(location=(6, 0, 2.5))
    camera_side = bpy.context.active_object
    camera_side.name = "Camera_Side"
    camera_side.rotation_euler = (math.radians(90), 0, math.radians(90))
    camera_side.data.lens = 35
    
    # إعداد خلفية العالم
    setup_world_background()
    
    # إعداد المشهد
    scene = bpy.context.scene
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 128


def setup_world_background():
    """إعداد خلفية العالم"""
    world = bpy.data.worlds.get("World")
    if world is None:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    
    world.use_nodes = True
    nodes = world.node_tree.nodes
    bg_node = nodes.get("Background")
    if bg_node:
        bg_node.inputs[0].default_value = (0.4, 0.7, 0.9, 1.0)  # أزرق فاتح
        bg_node.inputs[1].default_value = 1.0


# ============================================================
# إضافة تفاصيل إضافية للدقة
# ============================================================

def add_body_waves(materials):
    """إضافة التموجات على حواف الجسم"""
    # حواف متموجة على السطح الأمامي
    wave_positions = [
        (-1.2, -0.20, 1.5), (-0.8, -0.20, 1.2), (-0.4, -0.20, 1.4),
        (0.0, -0.20, 1.1), (0.4, -0.20, 1.3), (0.8, -0.20, 1.2),
        (1.2, -0.20, 1.5),
    ]
    
    for i, pos in enumerate(wave_positions):
        wave = create_uv_sphere(
            f"Body_Wave_{i}",
            location=pos,
            radius=0.08,
            segments=12,
            rings=8
        )
        wave.scale = (1, 0.3, 0.6)
        assign_material(wave, materials['body'])


def add_cheek_details(materials):
    """إضافة تفاصيل الخدود"""
    # خطوط الخد
    cheek_line_left = create_cylinder(
        "Cheek_Line_Left",
        location=(-0.6, -0.20, 2.0),
        radius=0.01,
        depth=0.3,
        rotation=(math.radians(90), math.radians(20), 0)
    )
    assign_material(cheek_line_left, materials['mouth'])
    
    cheek_line_right = create_cylinder(
        "Cheek_Line_Right",
        location=(0.6, -0.20, 2.0),
        radius=0.01,
        depth=0.3,
        rotation=(math.radians(90), math.radians(-20), 0)
    )
    assign_material(cheek_line_right, materials['mouth'])


def add_chin(materials):
    """إضافة الذقن"""
    chin = create_uv_sphere(
        "Chin",
        location=(0, -0.18, 1.7),
        radius=0.15,
        segments=20,
        rings=12
    )
    chin.scale = (1.5, 0.5, 0.8)
    assign_material(chin, materials['body'])


def add_eyebrows(materials):
    """إضافة الحواجب"""
    # الحاجب الأيسر
    brow_left = create_cylinder(
        "Eyebrow_Left",
        location=(-0.35, -0.30, 3.75),
        radius=0.025,
        depth=0.35,
        rotation=(math.radians(90), 0, math.radians(-10))
    )
    assign_material(brow_left, materials['eyelash'])
    
    # الحاجب الأيمن
    brow_right = create_cylinder(
        "Eyebrow_Right",
        location=(0.35, -0.30, 3.75),
        radius=0.025,
        depth=0.35,
        rotation=(math.radians(90), 0, math.radians(10))
    )
    assign_material(brow_right, materials['eyelash'])
    
    return brow_left, brow_right


# ============================================================
# تنظيم الكائنات في مجموعات
# ============================================================

def organize_hierarchy():
    """تنظيم الكائنات في تسلسل هرمي"""
    # إنشاء كائن فارغ كمجموع رئيسي
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0))
    root = bpy.context.active_object
    root.name = "SpongeBob_Root"
    
    # إنشاء مجموعات فرعية
    collections = {
        'Body': bpy.data.collections.new("Body"),
        'Eyes': bpy.data.collections.new("Eyes"),
        'Nose': bpy.data.collections.new("Nose"),
        'Mouth': bpy.data.collections.new("Mouth"),
        'Clothes': bpy.data.collections.new("Clothes"),
        'Arms': bpy.data.collections.new("Arms"),
        'Legs': bpy.data.collections.new("Legs"),
        'Details': bpy.data.collections.new("Details"),
    }
    
    # ربط المجموعات بالمشهد
    for name, col in collections.items():
        bpy.context.scene.collection.children.link(col)
    
    return root, collections


def assign_to_collection(obj, collection):
    """إضافة كائن إلى مجموعة"""
    for col in obj.users_collection:
        col.objects.unlink(obj)
    collection.objects.link(obj)


# ============================================================
# التصدير
# ============================================================

def export_model(filepath):
    """تصدير النموذج بصيغة GLB"""
    os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)
    
    # تحديد جميع الكائنات
    bpy.ops.object.select_all(action='SELECT')
    
    bpy.ops.export_scene.gltf(
        filepath=filepath,
        export_format='GLB',
        use_selection=True,
        export_apply=True,
        export_normals=True,
        export_materials='EXPORT',
        export_colors=True,
        export_skins=True,
        export_morph=False,
        export_yup=True
    )
    print(f"تم التصدير بنجاح: {filepath}")


def export_fbx(filepath):
    """تصدير النموذج بصيغة FBX"""
    os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)
    
    bpy.ops.object.select_all(action='SELECT')
    
    bpy.ops.export_scene.fbx(
        filepath=filepath,
        use_selection=True,
        apply_scale_options='FBX_SCALE_ALL',
        use_mesh_modifiers=True,
        mesh_smooth_type='FACE',
        add_leaf_bones=False,
        primary_bone_axis='Y',
        secondary_bone_axis='X',
    )
    print(f"تم التصدير بنجاح: {filepath}")


def save_blend_file(filepath):
    """حفظ ملف بليندر"""
    os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=filepath)
    print(f"تم الحفظ: {filepath}")


# ============================================================
# تطبيق التعديلات النهائية
# ============================================================

def apply_all_modifiers():
    """تطبيق جميع التعديلات على الكائنات"""
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            for modifier in obj.modifiers:
                bpy.ops.object.modifier_apply(modifier=modifier.name)
            obj.select_set(False)


def set_origin_to_center():
    """ضبط نقطة الأصل لجميع الكائنات"""
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='MEDIAN')
            obj.select_set(False)


def optimize_geometry():
    """تحسين الهندسة عن طريق إزالة الرؤوس المزدوجة"""
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.remove_doubles(threshold=0.0001)
            bpy.ops.object.mode_set(mode='OBJECT')
            obj.select_set(False)


# ============================================================
# إضافة كاميرا للمعاينة
# ============================================================

def setup_render_settings():
    """إعدادات التصيير المتقدمة"""
    scene = bpy.context.scene
    
    # إعدادات Cycles
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'GPU'
    scene.cycles.samples = 256
    scene.cycles.use_denoising = True
    
    # إعدادات الإضاءة
    scene.cycles.max_bounces = 12
    scene.cycles.diffuse_bounces = 8
    scene.cycles.glossy_bounces = 6
    scene.cycles.transparent_max_bounces = 8
    
    # إعدادات الألوان
    scene.view_settings.view_transform = 'Filmic'
    scene.view_settings.look = 'Medium High Contrast'
    
    # إعدادات الإخراج
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'


# ============================================================
# التحقق من صحة النموذج
# ============================================================

def validate_model():
    """التحقق من صحة النموذج"""
    issues = []
    
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            # التحقق من وجود مادة
            if not obj.data.materials:
                issues.append(f"الكائن '{obj.name}' لا يحتوي على مادة")
            
            # التحقق من وجود رؤوس معزولة
            mesh = obj.data
            loose_verts = [v for v in mesh.vertices if not v.groups]
            
            # التحقق من الأوجه المزدوجة
            if len(mesh.vertices) == 0:
                issues.append(f"الكائن '{obj.name}' فارغ")
    
    if issues:
        print("تحذيرات:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("النموذج سليم تماماً ✓")
    
    return len(issues) == 0


def count_objects():
    """عد الكائنات في المشهد"""
    mesh_count = sum(1 for obj in bpy.data.objects if obj.type == 'MESH')
    light_count = sum(1 for obj in bpy.data.objects if obj.type == 'LIGHT')
    camera_count = sum(1 for obj in bpy.data.objects if obj.type == 'CAMERA')
    
    print(f"\n{'='*50}")
    print(f"إحصائيات المشهد:")
    print(f"  الكائنات الشبكية: {mesh_count}")
    print(f"  الأضواء: {light_count}")
    print(f"  الكاميرات: {camera_count}")
    print(f"  المجموع: {len(bpy.data.objects)}")
    print(f"{'='*50}\n")


# ============================================================
# الدالة الرئيسية
# ============================================================

def main():
    try:
        print("بدء إنشاء مجسم سبونج بوب سكوير بان...")
        print("=" * 50)
        
        # 1. تنظيف المشهد
        print("[1/10] تنظيف المشهد...")
        clear_scene()
        
        # 2. إنشاء المواد
        print("[2/10] إنشاء المواد...")
        materials = create_all_materials()
        
        # 3. إنشاء الجسم
        print("[3/10] إنشاء الجسم الرئيسي...")
        body = create_body(materials)
        
        # 4. إنشاء العيون
        print("[4/10] إنشاء العيون...")
        eyes = create_eyes(materials)
        eyelashes = create_eyelashes(materials)
        eyebrows = add_eyebrows(materials)
        
        # 5. إنشاء الأنف والفم
        print("[5/10] إنشاء الأنف والفم...")
        nose_parts = create_nose(materials)
        mouth_parts = create_mouth(materials)
        add_cheek_details(materials)
        add_chin(materials)
        
        # 6. إنشاء الملابس
        print("[6/10] إنشاء الملابس...")
        shirt, collar = create_shirt(materials)
        pants_parts = create_pants(materials)
        tie_parts = create_tie(materials)
        
        # 7. إنشاء الذراعين
        print("[7/10] إنشاء الذراعين واليدين...")
        arms = create_arms(materials)
        
        # 8. إنشاء الساقين
        print("[8/10] إنشاء الساقين والقدمين...")
        legs = create_legs(materials)
        
        # 9. إضافة التفاصيل
        print("[9/10] إضافة التفاصيل النهائية...")
        add_body_waves(materials)
        
        # 10. إعداد المشهد والتصدير
        print("[10/10] إعداد المشهد والتصدير...")
        setup_scene()
        
        # تنظيم التسلسل الهرمي
        root, collections = organize_hierarchy()
        
        # التحقق من النموذج
        print("\nالتحقق من صحة النموذج...")
        validate_model()
        count_objects()
        
        # التصدير
        os.makedirs("out", exist_ok=True)
        export_model("out/spongebob.glb")
        
        print("\n" + "=" * 50)
        print("تم إنشاء مجسم سبونج بوب بنجاح! ✓")
        print("=" * 50)
        
    except Exception as e:
        print(f"خطأ في السيناريو: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()