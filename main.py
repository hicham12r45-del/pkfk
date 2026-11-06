import bpy
import math
import os
import sys
import traceback

def main():
    try:
        # Clear the default scene
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()

        # Hero cube
        bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 1))
        cube = bpy.context.active_object
        cube.name = "HeroCube"

        # Sun light
        bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))
        sun = bpy.context.active_object
        sun.data.energy = 3.0

        # Camera
        bpy.ops.object.camera_add(location=(6, -6, 4))
        camera = bpy.context.active_object
        camera.rotation_euler = (math.radians(65), 0, math.radians(45))
        bpy.context.scene.camera = camera

        # Export GLB
        os.makedirs("out", exist_ok=True)
        bpy.ops.export_scene.gltf(
            filepath="out/model.glb",
            export_format='GLB',
            use_selection=False
        )
        print("Exported out/model.glb")

    except Exception as e:
        print(f"Blender script failed: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()