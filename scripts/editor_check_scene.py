"""
Run inside Isaac Sim Script Editor only (Kit already running). No SimulationApp / close().
Checks that key prims exist on the *current* stage (load your USD in the GUI first).
"""

from __future__ import annotations

import omni.usd

# ---- edit prim paths here ----
ROBOT_ROOT = "/World/fr3"
CUBE_PATHS = ["/World/Cube", "/World/fr3/Cube"]
# ------------------------------

stage = omni.usd.get_context().get_stage()

print("=" * 60)
print("stage valid:", stage is not None)
if stage is None:
    raise RuntimeError("No stage loaded. Open your USD in Isaac Sim first.")
dp = stage.GetDefaultPrim()
print("defaultPrim:", dp.GetPath() if dp and dp.IsValid() else "(none)")
print("=" * 60)

print("robot_root", ROBOT_ROOT, "-> valid:", stage.GetPrimAtPath(ROBOT_ROOT).IsValid())
for p in CUBE_PATHS:
    ok = stage.GetPrimAtPath(p).IsValid()
    print("cube", p, "-> valid:", ok)
    if ok:
        print("  type:", stage.GetPrimAtPath(p).GetTypeName())

print("=" * 60)
print("/World top-level children:")
world = stage.GetPrimAtPath("/World")
if world.IsValid():
    for child in world.GetChildren():
        print(" -", child.GetPath(), "| type =", child.GetTypeName())
else:
    print("(no /World)")
print("=" * 60)
