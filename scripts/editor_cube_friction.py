"""
Run in Isaac Sim Script Editor (Kit already running). No SimulationApp / close().

Creates a rigid-body physics material (static/dynamic friction, restitution) and binds it to
your Cube collider. Low friction makes the cube slip when lifted; raising friction helps
grasp + carry (together with gripper force and contact geometry).

Steps:
  1) File → Open your scene USD (e.g. franka_cube_scene_v1.usd).
  2) Window → Script Editor → paste/run this file (or File → Open this script).
  3) File → Save (Ctrl+S) to persist material binding into the USD.

Env (optional, set before Kit if you use a launcher that passes env):
  CUBE_PRIM=/World/Cube
  CUBE_PHYSICS_MAT=/World/Materials/CubeHighFriction
  STATIC_FRICTION=1.2
  DYNAMIC_FRICTION=1.0
  RESTITUTION=0.0

Note: Contact uses *both* surfaces. If the cube still slips, also raise friction on gripper
finger collision meshes (their prim paths in Stage) with the same material or another high-friction mat.
"""

from __future__ import annotations

import os

CUBE_PRIM = os.environ.get("CUBE_PRIM", "/World/Cube")
MATERIAL_PRIM = os.environ.get("CUBE_PHYSICS_MAT", "/World/Materials/CubeHighFriction")
STATIC_FRICTION = float(os.environ.get("STATIC_FRICTION", "1.2"))
DYNAMIC_FRICTION = float(os.environ.get("DYNAMIC_FRICTION", "1.0"))
RESTITUTION = float(os.environ.get("RESTITUTION", "0.0"))

from isaaclab.sim.spawners.materials.physics_materials import spawn_rigid_body_material
from isaaclab.sim.spawners.materials.physics_materials_cfg import RigidBodyMaterialCfg
from isaaclab.sim.utils import bind_physics_material

cfg = RigidBodyMaterialCfg(
    static_friction=STATIC_FRICTION,
    dynamic_friction=DYNAMIC_FRICTION,
    restitution=RESTITUTION,
    # When cube meets gripper, "max" uses the higher of the two coefficients (often helps grip).
    friction_combine_mode="max",
    restitution_combine_mode="average",
)

spawn_rigid_body_material(MATERIAL_PRIM, cfg)
bind_physics_material(CUBE_PRIM, MATERIAL_PRIM)

print("=" * 60)
print("Physics material prim:", MATERIAL_PRIM)
print(
    f"  static_friction={STATIC_FRICTION}  dynamic_friction={DYNAMIC_FRICTION}  restitution={RESTITUTION}"
)
print("Bind attempted on:", CUBE_PRIM, "(and descendants until a collider accepts the bind).")
print("If you see a warning, select Cube in Stage → find the child Mesh with Collision API and set")
print("  CUBE_PRIM to that path, then run again.")
print("Save the USD (Ctrl+S) to keep this binding.")
print("=" * 60)
