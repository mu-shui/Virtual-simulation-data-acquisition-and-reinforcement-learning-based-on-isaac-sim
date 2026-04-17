"""
Run inside Isaac Sim Script Editor only (Kit already running). No SimulationApp / close().
Edit prim paths below if needed.

Related: editor_check_scene.py, editor_read_pose.py, editor_joint_states.py,
         editor_pregrasp_target.py (pre-grasp pose above cube for IK).
"""

from __future__ import annotations

import omni.usd
from pxr import Gf, Usd, UsdGeom

# ---- edit prim paths here ----
CUBE_PATHS = ["/World/Cube", "/World/fr3/Cube"]
EE_PATH = "/World/fr3/fr3_hand"
ROBOT_ROOT = "/World/fr3"
CAMERA_PATHS = ["/World/Camera_01", "/World/fr3/Camera_01"]
# ------------------------------


def _pose(prim: Usd.Prim) -> tuple[tuple[float, float, float], tuple[float, float, float, float]]:
    xformable = UsdGeom.Xformable(prim)
    m = xformable.ComputeLocalToWorldTransform(Usd.TimeCode.Default())
    t = m.ExtractTranslation()
    # Gf.Rotation has no Matrix3d ctor; decompose rotation from Matrix4d via Gf.Transform
    xf = Gf.Transform()
    xf.SetMatrix(m)
    q = xf.GetRotation().GetQuat()
    imag = q.GetImaginary()
    pos = (float(t[0]), float(t[1]), float(t[2]))
    wxyz = (float(q.GetReal()), float(imag[0]), float(imag[1]), float(imag[2]))
    return pos, wxyz


def _print_one(label: str, path: str) -> bool:
    stage = omni.usd.get_context().get_stage()
    p = stage.GetPrimAtPath(path)
    if not p.IsValid():
        print(f"{label} {path} -> missing")
        return False
    pos, wxyz = _pose(p)
    print(f"{label} ({path})")
    print(f"  pos (m): {pos[0]:.6f}, {pos[1]:.6f}, {pos[2]:.6f}")
    print(f"  quat wxyz: {wxyz[0]:.6f}, {wxyz[1]:.6f}, {wxyz[2]:.6f}, {wxyz[3]:.6f}")
    return True


print("=" * 60)
_print_one("robot_root", ROBOT_ROOT)
for cp in CUBE_PATHS:
    if _print_one("cube", cp):
        break
for cam in CAMERA_PATHS:
    if _print_one("camera", cam):
        break
_print_one("ee_prim", EE_PATH)
print("=" * 60)
