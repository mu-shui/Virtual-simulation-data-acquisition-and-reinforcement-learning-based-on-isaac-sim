"""Isaac Lab 最小物理自检：空场景 + 地面 + 一个受重力下落的刚体方块。

用途：区分「Kit/驱动/显示卡住」与「大脚本逻辑问题」。若本脚本能持续打印方块 Z
坐标下降并最终接近地面高度，说明 PhysX 与 SimulationContext 基本正常。

运行（在 conda isaaclab 环境中）:
  cd .../virtual_data_collection_rl/scripts
  conda activate isaaclab
  python lab_falling_cube_smoke.py

环境变量:
  ISAAC_DEVICE   默认 cuda:0，可改为 cpu 做对照
  HEADLESS=1       无界面（远程/无 DISPLAY 时可试）
  KEEP_SIM_OPEN=1  跑完后不调用 simulation_app.close()，便于在窗口里手动 Play/看 Stage
  DROP_HEIGHT_M    方块初始中心高度（米），默认 2.0
  STEP_COUNT       物理步数，默认 360（约 60Hz 下 6 秒）
  PRINT_EVERY      每隔多少步打印一次 Z，默认 30
"""

from __future__ import annotations

import os
import sys

# -----------------------------------------------------------------------------
# AppLauncher 必须在其它 isaaclab / isaacsim 导入之前
# -----------------------------------------------------------------------------
from isaaclab.app import AppLauncher

_HEADLESS = os.environ.get("HEADLESS", "0").strip().lower() in ("1", "true", "yes")
app_launcher = AppLauncher(headless=_HEADLESS)
simulation_app = app_launcher.app

import torch

import isaaclab.sim as sim_utils
from isaaclab.assets import RigidObject, RigidObjectCfg
from isaaclab.sim import SimulationCfg, SimulationContext
from isaaclab.sim.spawners import DomeLightCfg, GroundPlaneCfg

SIM_DEVICE = os.environ.get("ISAAC_DEVICE", "cuda:0")
DROP_HEIGHT_M = float(os.environ.get("DROP_HEIGHT_M", "2.0"))
STEP_COUNT = int(os.environ.get("STEP_COUNT", "360"))
PRINT_EVERY = int(os.environ.get("PRINT_EVERY", "30"))
KEEP_SIM_OPEN = os.environ.get("KEEP_SIM_OPEN", "0").strip().lower() in ("1", "true", "yes")
SIM_DT = 1.0 / 60.0


def main() -> None:
    print("[falling_cube_smoke] Python OK, starting Kit / stage...", flush=True)

    sim_utils.create_new_stage()
    for _ in range(20):
        simulation_app.update()

    sim_cfg = SimulationCfg(dt=SIM_DT, device=SIM_DEVICE)
    sim_cfg.gravity = (0.0, 0.0, -9.81)
    sim = SimulationContext(sim_cfg)

    gp_cfg = GroundPlaneCfg()
    gp_cfg.func("/World/defaultGroundPlane", gp_cfg)

    dome_cfg = DomeLightCfg(
        color=(0.1, 0.1, 0.1),
        enable_color_temperature=True,
        color_temperature=5500,
        intensity=10000,
    )
    dome_cfg.func(prim_path="/World/defaultDomeLight", cfg=dome_cfg, translation=(0.0, 0.0, 10.0))

    # 程序化生成刚体方块（不依赖 Nucleus 里的 dex_cube USD）
    spawn = sim_utils.CuboidCfg(
        size=(0.1, 0.1, 0.1),
        collision_props=sim_utils.CollisionPropertiesCfg(),
        rigid_props=sim_utils.RigidBodyPropertiesCfg(),
        mass_props=sim_utils.MassPropertiesCfg(mass=1.0),
    )
    cube_cfg = RigidObjectCfg(
        prim_path="/World/FallingCube",
        spawn=spawn,
        init_state=RigidObjectCfg.InitialStateCfg(pos=(0.0, 0.0, DROP_HEIGHT_M)),
    )
    cube = RigidObject(cfg=cube_cfg)

    print(
        "[falling_cube_smoke] scene ready | device",
        SIM_DEVICE,
        "| dt",
        SIM_DT,
        "| drop Z",
        DROP_HEIGHT_M,
        "| steps",
        STEP_COUNT,
        flush=True,
    )

    sim.reset()
    cube.reset()

    z_prev = float("nan")
    for step in range(STEP_COUNT):
        sim.step(render=not _HEADLESS)
        cube.update(sim.cfg.dt)
        z = float(cube.data.root_pos_w[0, 2].item())
        if step == 0 or step % PRINT_EVERY == 0 or step == STEP_COUNT - 1:
            dz = z - z_prev if step > 0 else 0.0
            print(f"  step {step:4d}  cube_z={z:.4f} m  dZ={dz:+.5f}", flush=True)
            z_prev = z
        else:
            z_prev = z

    print(
        "[falling_cube_smoke] finished. If cube_z decreased toward ~0.05 (half extent on ground), physics works.",
        flush=True,
    )

    if KEEP_SIM_OPEN:
        print("[falling_cube_smoke] KEEP_SIM_OPEN=1 — close the Kit window to exit.", flush=True)
        try:
            while simulation_app.is_running():
                simulation_app.update()
        except KeyboardInterrupt:
            pass
    else:
        simulation_app.close()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("[falling_cube_smoke] ERROR:", file=sys.stderr, flush=True)
        raise
