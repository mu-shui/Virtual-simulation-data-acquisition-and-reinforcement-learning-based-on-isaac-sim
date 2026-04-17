from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": False})

import omni.usd
from pxr import UsdGeom

USD_PATH = "/home/agiuser/isaac_projects/isaac_scene/franka_cube_scene_v1.usd"

# 打开场景
omni.usd.get_context().open_stage(USD_PATH)

# 等待场景加载稳定
for _ in range(60):
    simulation_app.update()

stage = omni.usd.get_context().get_stage()

def print_world_translation(prim_path: str):
    prim = stage.GetPrimAtPath(prim_path)
    if not prim.IsValid():
        print(f"{prim_path} 不存在")
        return

    xformable = UsdGeom.Xformable(prim)
    world_transform = xformable.ComputeLocalToWorldTransform(0)
    translation = world_transform.ExtractTranslation()

    print(f"{prim_path} 世界坐标:")
    print(f"  X = {translation[0]:.6f}")
    print(f"  Y = {translation[1]:.6f}")
    print(f"  Z = {translation[2]:.6f}")
    print("-" * 40)

print("=" * 60)
print_world_translation("/World/fr3")
print_world_translation("/World/Cube")
print_world_translation("/World/Camera_01")
print("=" * 60)

for _ in range(60):
    simulation_app.update()

simulation_app.close()
