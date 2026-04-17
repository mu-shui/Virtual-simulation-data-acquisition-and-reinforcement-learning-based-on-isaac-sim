"""Step 3: 物理步进后读取关节角、刚体名，并从 Articulation 读末端 link 的 COM 位姿。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from isaacsim import SimulationApp

from scene_config import DEFAULT_SCENE_USD, EE_BODY_NAME, ROBOT_ROOT

simulation_app = SimulationApp({"headless": False})

import omni.usd
from isaacsim.core.api import World
from isaacsim.core.prims import Articulation

USD_PATH = DEFAULT_SCENE_USD
omni.usd.get_context().open_stage(USD_PATH)

world = World(stage_units_in_meters=1.0)
robot = Articulation(prim_paths_expr=ROBOT_ROOT, name="fr3")
world.scene.add(robot)

for _ in range(60):
    simulation_app.update()

world.reset()
robot.initialize()

for _ in range(10):
    world.step(render=True)

print("=" * 60)
print("DOF 名称:", robot.dof_names)
jp = robot.get_joint_positions()
if jp is not None:
    arr = np.asarray(jp).reshape(-1)
    for name, val in zip(robot.dof_names, arr):
        print(f"  {name}: {float(val):.6f}")

print("-" * 60)
print("刚体 link 名称 (用于 EE_BODY_NAME):", robot.body_names)

names = robot.body_names
if names is None or EE_BODY_NAME not in names:
    print(f"未找到刚体名 EE_BODY_NAME={EE_BODY_NAME!r}，请从上面「刚体 link 名称」中选一个并设置环境变量 EE_BODY_NAME")
    bi = None
else:
    bi = robot.get_body_index(EE_BODY_NAME)

if bi is not None:
    pos, ori = robot.get_body_coms(body_indices=np.array([bi], dtype=np.int32))
    # shape (1,1,3) (1,1,4) wxyz
    p = np.asarray(pos).reshape(-1)
    o = np.asarray(ori).reshape(-1)
    print(f"末端刚体 {EE_BODY_NAME!r} COM 位置 (world, m): {p[0]:.6f}, {p[1]:.6f}, {p[2]:.6f}")
    print(f"末端刚体 {EE_BODY_NAME!r} COM 姿态 (四元数 wxyz): {o[0]:.6f}, {o[1]:.6f}, {o[2]:.6f}, {o[3]:.6f}")

print("=" * 60)

for _ in range(60):
    simulation_app.update()

simulation_app.close()
