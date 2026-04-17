"""Step 2: 读取机器人根、末端 prim、方块、相机在世界坐标系下的位姿。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from isaacsim import SimulationApp

from scene_config import (
    CAMERA_PRIM,
    CUBE_CANDIDATES,
    DEFAULT_SCENE_USD,
    EE_PRIM_PATH,
    ROBOT_ROOT,
)
from pose_utils import print_pose

simulation_app = SimulationApp({"headless": False})

import omni.usd

USD_PATH = DEFAULT_SCENE_USD
omni.usd.get_context().open_stage(USD_PATH)

for _ in range(60):
    simulation_app.update()

stage = omni.usd.get_context().get_stage()

print("=" * 60)
print("USD:", USD_PATH)

print_pose("机器人根 (非 TCP，仅基座/装配根)", ROBOT_ROOT, stage.GetPrimAtPath(ROBOT_ROOT))

cube_ok = False
for p in CUBE_CANDIDATES:
    if print_pose("方块", p, stage.GetPrimAtPath(p)):
        cube_ok = True
        break
if not cube_ok:
    print("方块: 以下路径均无效 —", CUBE_CANDIDATES)

# 相机可能在 /World 或 /World/fr3 下
for cam in [CAMERA_PRIM, "/World/Camera_01", "/World/fr3/Camera_01"]:
    if print_pose("相机", cam, stage.GetPrimAtPath(cam)):
        break

print_pose("末端 EE prim (默认 fr3_hand，可用 EE_PRIM_PATH 覆盖)", EE_PRIM_PATH, stage.GetPrimAtPath(EE_PRIM_PATH))

print("=" * 60)

for _ in range(60):
    simulation_app.update()

simulation_app.close()
