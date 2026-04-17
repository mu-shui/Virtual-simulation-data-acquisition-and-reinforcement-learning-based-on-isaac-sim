"""从 USD prim 读取世界系位姿（平移 + 四元数 wxyz）。"""

from __future__ import annotations

from pxr import Gf, Usd, UsdGeom


def world_pose_from_prim(prim: Usd.Prim, time: Usd.TimeCode | None = None) -> tuple[Gf.Vec3d, tuple[float, float, float, float]]:
    """返回 (translation, (w, x, y, z))。"""
    if not prim.IsValid():
        raise ValueError("prim 无效")
    tcode = time if time is not None else Usd.TimeCode.Default()
    xformable = UsdGeom.Xformable(prim)
    m = xformable.ComputeLocalToWorldTransform(tcode)
    trans = m.ExtractTranslation()
    xf = Gf.Transform()
    xf.SetMatrix(m)
    q = xf.GetRotation().GetQuat()
    imag = q.GetImaginary()
    wxyz = (float(q.GetReal()), float(imag[0]), float(imag[1]), float(imag[2]))
    return Gf.Vec3d(trans[0], trans[1], trans[2]), wxyz


def print_pose(label: str, prim_path: str, prim: Usd.Prim) -> bool:
    if not prim.IsValid():
        print(f"{label} ({prim_path}) -> 不存在")
        return False
    trans, wxyz = world_pose_from_prim(prim)
    print(f"{label} ({prim_path})")
    print(f"  位置 (world, m): x={trans[0]:.6f}, y={trans[1]:.6f}, z={trans[2]:.6f}")
    print(f"  姿态 (四元数 wxyz): w={wxyz[0]:.6f}, x={wxyz[1]:.6f}, y={wxyz[2]:.6f}, z={wxyz[3]:.6f}")
    return True
