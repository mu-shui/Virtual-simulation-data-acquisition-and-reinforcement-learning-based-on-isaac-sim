"""
Run inside Isaac Sim Script Editor only (Kit already running). No SimulationApp / close().
Reads DOF positions, body_names, and COM pose for EE_BODY_NAME after a few physics steps.

If world.reset() is unwanted, comment out the reset() line (joint data may still work after PLAY).

If you see get_physics_dt / NoneType errors, this script calls initialize_simulation_context_async once
when physics context is missing (common in Script Editor).
"""

from __future__ import annotations

import numpy as np
from isaacsim.core.api import World
from isaacsim.core.prims import Articulation
from omni.kit.async_engine import run_coroutine

# ---- edit here ----
ROBOT_ROOT = "/World/fr3"
SCENE_ROBOT_NAME = "fr3_editor_articulation"
EE_BODY_NAME = "fr3_hand"
# -------------------

world = World(stage_units_in_meters=1.0)

# Script Editor often skips _init_stage; ensure PhysicsContext exists (see SimulationContext.__init__)
if world.get_physics_context() is None:

    async def _ensure_simulation_context():
        await world.initialize_simulation_context_async()

    run_coroutine(_ensure_simulation_context())

if world.scene.object_exists(SCENE_ROBOT_NAME):
    robot = world.scene.get_object(SCENE_ROBOT_NAME)
else:
    robot = Articulation(prim_paths_expr=ROBOT_ROOT, name=SCENE_ROBOT_NAME)
    world.scene.add(robot)

world.reset()
robot.initialize()

for _ in range(10):
    world.step(render=True)

print("=" * 60)
print("dof_names:", robot.dof_names)
jp = robot.get_joint_positions()
if jp is not None:
    arr = np.asarray(jp).reshape(-1)
    for name, val in zip(robot.dof_names, arr):
        print(f"  {name}: {float(val):.6f}")

print("-" * 60)
print("body_names (pick EE_BODY_NAME from this list):", robot.body_names)

names = robot.body_names
if names is None or EE_BODY_NAME not in names:
    print("EE_BODY_NAME not in body_names:", repr(EE_BODY_NAME))
    print("Set EE_BODY_NAME in this script to one of body_names above.")
    bi = None
else:
    bi = robot.get_body_index(EE_BODY_NAME)

if bi is not None:
    pos, ori = robot.get_body_coms(body_indices=np.array([bi], dtype=np.int32))
    p = np.asarray(pos).reshape(-1)
    o = np.asarray(ori).reshape(-1)
    print("ee_body", repr(EE_BODY_NAME), "COM pos (world, m):", f"{p[0]:.6f}, {p[1]:.6f}, {p[2]:.6f}")
    print("ee_body", repr(EE_BODY_NAME), "COM quat wxyz:", f"{o[0]:.6f}, {o[1]:.6f}, {o[2]:.6f}, {o[3]:.6f}")

print("=" * 60)
