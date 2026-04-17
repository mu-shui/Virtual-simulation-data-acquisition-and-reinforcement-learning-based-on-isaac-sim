from isaacsim import SimulationApp

# 1) 先启动 Isaac Sim 应用
simulation_app = SimulationApp({"headless": False})

# 2) Omniverse/Isaac 相关导入必须放在 SimulationApp 之后
import omni.usd
from pxr import Usd

# 3) 你的场景路径
USD_PATH = "/home/agiuser/isaac_projects/isaac_scene/franka_cube_scene_v1.usd"

# 4) 打开场景
omni.usd.get_context().open_stage(USD_PATH)

# 5) 等几帧，确保场景加载完成
for _ in range(20):
    simulation_app.update()

# 6) 取得 stage
stage = omni.usd.get_context().get_stage()

print("=" * 60)
print("场景是否加载成功：", stage is not None)
print("默认 Prim：", stage.GetDefaultPrim().GetPath() if stage.GetDefaultPrim() else "无")
print("=" * 60)

# 7) 检查我们关心的几个对象
target_paths = [
    "/World/fr3",
    "/World/Cube",
    "/World/Camera_01",
]

for path in target_paths:
    prim = stage.GetPrimAtPath(path)
    print(f"{path} -> 是否存在: {prim.IsValid()}")
    if prim.IsValid():
        print(f"  类型: {prim.GetTypeName()}")

print("=" * 60)
print("场景中的顶层对象：")
world = stage.GetPrimAtPath("/World")
if world and world.IsValid():
    for child in world.GetChildren():
        print(" -", child.GetPath(), "| type =", child.GetTypeName())
print("=" * 60)

# 8) 为了看清加载结果，让程序保持一小会儿
for _ in range(120):
    simulation_app.update()

simulation_app.close()
