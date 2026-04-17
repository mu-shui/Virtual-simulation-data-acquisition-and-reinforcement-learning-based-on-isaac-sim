"""Step 1: 启动 Kit，打开 USD，检查关键 prim 是否存在。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from isaacsim import SimulationApp

from scene_config import CUBE_CANDIDATES, DEFAULT_SCENE_USD, ROBOT_ROOT

simulation_app = SimulationApp({"headless": False})

import omni.usd
from pxr import Usd

USD_PATH = DEFAULT_SCENE_USD

omni.usd.get_context().open_stage(USD_PATH)

for _ in range(20):
    simulation_app.update()

stage = omni.usd.get_context().get_stage()

print("=" * 60)
print("USD:", USD_PATH)
print("场景是否加载成功：", stage is not None)
print("默认 Prim：", stage.GetDefaultPrim().GetPath() if stage.GetDefaultPrim() else "无")
print("=" * 60)

check_paths = [
    (ROBOT_ROOT, "机器人根"),
    *[(p, "方块") for p in CUBE_CANDIDATES],
]

for path, label in check_paths:
    prim = stage.GetPrimAtPath(path)
    print(f"{label} {path} -> 是否存在: {prim.IsValid()}")
    if prim.IsValid():
        print(f"  类型: {prim.GetTypeName()}")

print("=" * 60)
print("/World 顶层子节点：")
world = stage.GetPrimAtPath("/World")
if world and world.IsValid():
    for child in world.GetChildren():
        print(" -", child.GetPath(), "| type =", child.GetTypeName())
print("=" * 60)

for _ in range(120):
    simulation_app.update()

simulation_app.close()
