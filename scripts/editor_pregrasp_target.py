"""
Run inside Isaac Sim Script Editor (Kit already running). No SimulationApp / close().

Computes a pre-grasp pose above the cube:
  - position: cube world translation + (0, 0, APPROACH_HEIGHT_M) in a Z-up world
  - orientation: tool +Z rotated to world -Z via 180 deg about world X (typical "reach from above")

Tune ORIENTATION_MODE / EXTRA_YAW_DEG if the hand frame does not match your asset.

Next step after this script: feed (target_pos, target_rot_matrix or quat) into your IK solver
(e.g. Isaac Lab Differential IK, Lula, or ArticulationKinematicsSolver + Lula config), then
apply_action / set_joint_position_targets on the arm DOFs only.
"""

from __future__ import annotations

import omni.usd
from pxr import Gf, Usd, UsdGeom

# ---- edit ----
CUBE_PRIM = "/World/Cube"
# Height above cube *center* along +world Z (meters). Increase if the gripper collides.
APPROACH_HEIGHT_M = 0.12
# "down": local +Z -> world -Z using Rx(180 deg). Use "identity" to debug position-only.
ORIENTATION_MODE = "down"  # "down" | "identity"
# Extra yaw about world +Z after base orientation (degrees). Often 0 for symmetric setups.
EXTRA_YAW_DEG = 0.0
# --------------


def _world_translation(prim: Usd.Prim) -> Gf.Vec3d:
    xf = UsdGeom.Xformable(prim)
    m = xf.ComputeLocalToWorldTransform(Usd.TimeCode.Default())
    t = m.ExtractTranslation()
    return Gf.Vec3d(float(t[0]), float(t[1]), float(t[2]))


def _quat_wxyz_from_rotation(rot: Gf.Rotation) -> tuple[float, float, float, float]:
    q = rot.GetQuat()
    imag = q.GetImaginary()
    return (float(q.GetReal()), float(imag[0]), float(imag[1]), float(imag[2]))


stage = omni.usd.get_context().get_stage()
cube = stage.GetPrimAtPath(CUBE_PRIM)
if not cube.IsValid():
    raise RuntimeError(f"Missing prim: {CUBE_PRIM}")

ct = _world_translation(cube)
target = Gf.Vec3d(ct[0], ct[1], ct[2] + APPROACH_HEIGHT_M)

if ORIENTATION_MODE == "identity":
    base = Gf.Rotation()
elif ORIENTATION_MODE == "down":
    # Maps +Z to -Z in world (Z-up): rotate 180 deg about world X
    base = Gf.Rotation(Gf.Vec3d(1.0, 0.0, 0.0), 180.0)
else:
    raise ValueError("ORIENTATION_MODE must be 'down' or 'identity'")

yaw = Gf.Rotation(Gf.Vec3d(0.0, 0.0, 1.0), EXTRA_YAW_DEG)
combined = yaw * base
wxyz = _quat_wxyz_from_rotation(combined)

print("=" * 60)
print("cube center (world, m):", f"{ct[0]:.6f}, {ct[1]:.6f}, {ct[2]:.6f}")
print("pregrasp target pos (world, m):", f"{target[0]:.6f}, {target[1]:.6f}, {target[2]:.6f}")
print("pregrasp quat wxyz:", f"{wxyz[0]:.6f}, {wxyz[1]:.6f}, {wxyz[2]:.6f}, {wxyz[3]:.6f}")
print("ORIENTATION_MODE:", ORIENTATION_MODE, "EXTRA_YAW_DEG:", EXTRA_YAW_DEG)
print("=" * 60)
print("Feed this pose to your IK / motion policy. Control only fr3_joint1..7 for arm;")
print("use finger joints separately for grasp.")
print("=" * 60)
