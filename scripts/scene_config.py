"""场景路径与常用 prim 名：可用环境变量覆盖，避免写死机器路径。"""

from __future__ import annotations

import os
from pathlib import Path

# 本文件在 repo/scripts/ → 默认场景在 repo/isaac_projects/isaac_scene/（你当前实际位置）
def _default_scene_usd() -> str:
    repo = Path(__file__).resolve().parent.parent
    in_repo = repo / "isaac_projects" / "isaac_scene" / "franka_cube_scene_v1.usd"
    if in_repo.is_file():
        return str(in_repo)
    home = Path.home() / "isaac_projects" / "isaac_scene" / "franka_cube_scene_v1.usd"
    return str(home)


# 优先环境变量 ISAAC_SCENE_USD
DEFAULT_SCENE_USD = os.environ.get("ISAAC_SCENE_USD", _default_scene_usd())

ROBOT_ROOT = os.environ.get("ROBOT_ROOT", "/World/fr3")

# 方块可能在 /World/Cube 或误挂在 /World/fr3/Cube 下，脚本会依次尝试
CUBE_CANDIDATES = [
    p.strip()
    for p in os.environ.get("CUBE_PRIM_PATHS", "/World/Cube,/World/fr3/Cube").split(",")
    if p.strip()
]

CAMERA_PRIM = os.environ.get("CAMERA_PRIM", "/World/Camera_01")

# 末端：USD 里用于读位姿的 Xform（常见为手掌/法兰附近）
EE_PRIM_PATH = os.environ.get("EE_PRIM_PATH", "/World/fr3/fr3_hand")

# 物理刚体名（Articulation.get_body_index），与 USD link 名一致；不对时看 step3 打印的 body_names
EE_BODY_NAME = os.environ.get("EE_BODY_NAME", "fr3_hand")
