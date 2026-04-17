"""Isaac Lab: differential IK toward a pre-grasp pose (single env, FR3 in your USD).

Run from terminal (not Script Editor):
  cd /path/to/virtual_data_collection_rl/scripts
  conda activate isaaclab
  python lab_fr3_diff_ik_pregrasp.py

Requires your scene USD (default: repo/isaac_projects/isaac_scene/franka_2.usd, else franka_cube_scene_v1.usd;
override with ISAAC_SCENE_USD) with /World/fr3.

This script does NOT perform a grasp: it only drives the 7 arm joints toward one fixed pre-grasp
pose. Finger joints are initialized open (0.04) and are not commanded to close here.

Target pose defaults match editor_pregrasp_target.py (base frame = world if robot root is at origin).
Override with env: TARGET_XYZ, TARGET_QUAT_WXYZ (comma-separated).

Why motion can look "weird":
  - Differential IK is NOT a motion planner: each step greedily reduces pose error -> path is not a straight line in space.
  - Wrong Jacobian row vs EE link makes nonsensical twists (try EE_JACOBI_ROW_OFFSET 0 or -1).
  - Position+orientation together can cause large wrist motion; use DELTA_SCALE < 1 and/or higher IK_LAMBDA for smoother motion.
"""

from __future__ import annotations

import os
from pathlib import Path

# -----------------------------------------------------------------------------
# AppLauncher must run before other isaaclab/isaacsim imports
# -----------------------------------------------------------------------------
from isaaclab.app import AppLauncher

app_launcher = AppLauncher(headless=False)
simulation_app = app_launcher.app

import torch

import isaaclab.sim as sim_utils
from isaaclab.actuators import ImplicitActuatorCfg
from isaaclab.assets import Articulation
from isaaclab.assets.articulation import ArticulationCfg
from isaaclab.controllers import DifferentialIKController, DifferentialIKControllerCfg
from isaaclab.sim import SimulationCfg, SimulationContext
from isaaclab.utils.math import matrix_from_quat, quat_inv, subtract_frame_transforms

# --- scene ---
def _default_usd_path() -> str:
    repo = Path(__file__).resolve().parent.parent
    scene_dir = repo / "isaac_projects" / "isaac_scene"
    for name in ("franka_2.usd", "franka_cube_scene_v1.usd"):
        p = scene_dir / name
        if p.is_file():
            return str(p)
    return str(Path.home() / "isaac_projects" / "isaac_scene" / "franka_2.usd")


USD_PATH = os.environ.get("ISAAC_SCENE_USD", _default_usd_path())
ROBOT_PRIM = "/World/fr3"
EE_BODY_NAME = os.environ.get("EE_BODY_NAME", "fr3_hand")
# PhysX Jacobian row: often body_index-1 for the EE link (asset-dependent). Try 0 if motion is wrong.
EE_JACOBI_ROW_OFFSET = int(os.environ.get("EE_JACOBI_ROW_OFFSET", "-1"))
ARM_JOINT_PATTERN = "fr3_joint[1-7]"
# Scale each IK joint delta (0-1). Smaller = smoother, slower convergence.
DELTA_SCALE = float(os.environ.get("DELTA_SCALE", "0.35"))
# DLS damping: larger -> smoother near singularities, slower convergence.
IK_LAMBDA = float(os.environ.get("IK_LAMBDA", "0.06"))

# Default: pre-grasp above cube (same as your editor_pregrasp_target run). Base frame = world if /World/fr3 root is identity.
def _parse_floats(env_key: str, default: tuple[float, ...]) -> tuple[float, ...]:
    raw = os.environ.get(env_key)
    if not raw:
        return default
    return tuple(float(x.strip()) for x in raw.split(","))


TARGET_XYZ = _parse_floats("TARGET_XYZ", (0.518026, -0.151064, 0.170000))
TARGET_QUAT_WXYZ = _parse_floats("TARGET_QUAT_WXYZ", (0.0, 1.0, 0.0, 0.0))

SIM_DEVICE = os.environ.get("ISAAC_DEVICE", "cuda:0")
MAX_ITERS = int(os.environ.get("IK_ITERS", "800"))


def _fr3_cfg() -> ArticulationCfg:
    # Do not use fr3_joint.* -> 0.0: FR3 USD limits exclude 0 for some joints (e.g. joint4, joint6).
    # Values below are inside typical FR3 limits; align with your scene if needed.
    return ArticulationCfg(
        prim_path=ROBOT_PRIM,
        spawn=None,
        init_state=ArticulationCfg.InitialStateCfg(
            joint_pos={
                "fr3_joint1": 0.0,
                "fr3_joint2": 0.0,
                "fr3_joint3": 0.0,
                "fr3_joint4": -0.25,
                "fr3_joint5": 0.0,
                "fr3_joint6": 0.6,
                "fr3_joint7": 0.0,
                "fr3_finger_joint.*": 0.04,
            },
        ),
        actuators={
            "arm": ImplicitActuatorCfg(
                joint_names_expr=[ARM_JOINT_PATTERN],
                effort_limit_sim=100.0,
                stiffness=400.0,
                damping=80.0,
            ),
            "gripper": ImplicitActuatorCfg(
                joint_names_expr=["fr3_finger_joint.*"],
                effort_limit_sim=200.0,
                stiffness=2e3,
                damping=1e2,
            ),
        },
    )


def main() -> None:
    if not sim_utils.open_stage(USD_PATH):
        raise RuntimeError(f"Failed to open USD: {USD_PATH}")

    for _ in range(20):
        simulation_app.update()

    sim_cfg = SimulationCfg(dt=1.0 / 60.0, device=SIM_DEVICE)
    sim = SimulationContext(sim_cfg)

    robot_cfg = _fr3_cfg()
    robot = Articulation(cfg=robot_cfg)

    diff_ik_cfg = DifferentialIKControllerCfg(
        command_type="pose",
        use_relative_mode=False,
        ik_method="dls",
        ik_params={"lambda_val": IK_LAMBDA},
    )
    diff_ik = DifferentialIKController(diff_ik_cfg, num_envs=1, device=sim.device)

    sim_dt = sim.get_physics_dt()
    sim.reset()
    robot.reset()

    ee_idx = robot.find_bodies(EE_BODY_NAME)[0][0]
    ee_jacobi_idx = ee_idx + EE_JACOBI_ROW_OFFSET
    arm_joint_ids = robot.find_joints([ARM_JOINT_PATTERN])[0]

    robot.update(sim_dt)
    print(
        "[IK] EE body",
        EE_BODY_NAME,
        "body_idx",
        ee_idx,
        "jacobian_row",
        ee_jacobi_idx,
        "DELTA_SCALE",
        DELTA_SCALE,
        "IK_LAMBDA",
        IK_LAMBDA,
    )

    ee_pose_b_des = torch.zeros(1, 7, device=sim.device)
    ee_pose_b_des[0, 0:3] = torch.tensor(TARGET_XYZ, device=sim.device, dtype=torch.float32)
    ee_pose_b_des[0, 3:7] = torch.tensor(TARGET_QUAT_WXYZ, device=sim.device, dtype=torch.float32)

    diff_ik.reset()
    diff_ik.set_command(ee_pose_b_des)

    # Match test_differential_ik: first step after command uses stale jacobians; skip one physics step.
    first = True
    for _ in range(MAX_ITERS):
        if first:
            first = False
            sim.step(render=True)
            robot.update(sim_dt)
            continue

        jacobian = robot.root_physx_view.get_jacobians()[:, ee_jacobi_idx, :, arm_joint_ids]
        ee_pose_w = robot.data.body_pose_w[:, ee_idx]
        root_pose_w = robot.data.root_pose_w
        base_rot = root_pose_w[:, 3:7]
        base_rot_matrix = matrix_from_quat(quat_inv(base_rot))
        jacobian[:, :3, :] = torch.bmm(base_rot_matrix, jacobian[:, :3, :])
        jacobian[:, 3:, :] = torch.bmm(base_rot_matrix, jacobian[:, 3:, :])

        joint_pos = robot.data.joint_pos[:, arm_joint_ids]
        ee_pos_b, ee_quat_b = subtract_frame_transforms(
            root_pose_w[:, 0:3],
            root_pose_w[:, 3:7],
            ee_pose_w[:, 0:3],
            ee_pose_w[:, 3:7],
        )
        joint_pos_des = diff_ik.compute(ee_pos_b, ee_quat_b, jacobian, joint_pos)
        # Smaller per-step changes -> smoother-looking trajectory (still not a Cartesian straight line).
        joint_pos_des = joint_pos + DELTA_SCALE * (joint_pos_des - joint_pos)

        robot.set_joint_position_target(joint_pos_des, arm_joint_ids)
        robot.write_data_to_sim()
        sim.step(render=True)
        robot.update(sim_dt)

    print("Done IK loop. Check viewport for end pose near pre-grasp target.")
    print("Target xyz (base frame):", TARGET_XYZ)
    print("Target quat wxyz:", TARGET_QUAT_WXYZ)

    # Keep window open briefly
    for _ in range(120):
        sim.step(render=True)
        robot.update(sim_dt)

    simulation_app.close()


if __name__ == "__main__":
    main()
