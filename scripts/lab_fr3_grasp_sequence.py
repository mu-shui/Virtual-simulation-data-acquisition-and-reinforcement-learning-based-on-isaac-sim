"""Isaac Lab: FR3 pick sequence — pre-grasp IK → grasp IK → close gripper → settle → lift.
Why the old result looked "twisted" / not top-down
  - Pose IK chases BOTH position and orientation. The quaternion (0,1,0,0) means "180° about X"
    in WORLD frame, but IK is applied to whatever body you name (fr3_hand vs fr3_hand_tcp).
    That body's LOCAL axes are not the same as "finger opening plane" or "approach normal" in
    your head — so the arm can look contorted while still matching the math target.
  - Default now: IK_COMMAND_TYPE=position — only reach the XYZ targets; orientation is FREE
    (redundant arm posture). This is usually the least twisted way to get above the cube.
  - Default EE_BODY_NAME=fr3_hand_tcp — Jacobian and target match the tool frame (closer to
    where contacts happen than fr3_hand).

Lift step (does the cube move up?)
  - After close, we hold POST_CLOSE_SETTLE_STEPS, then run a lift IK phase with fingers STILL
    commanded closed. Whether the cube sticks is PHYSICS: friction, contact, gripper force, and
    whether the grasp pose actually surrounds the cube. Tune materials / GRASP_Z_OFFSET_M / mass.

Run:
  cd .../virtual_data_collection_rl/scripts && conda activate isaaclab
  python lab_fr3_grasp_sequence.py

Env (see also inline defaults):
  ISAAC_SCENE_USD (default: repo isaac_projects/isaac_scene/franka_2.usd, else franka_cube_scene_v1.usd)
  CUBE_PRIM, CUBE_CENTER_MODE=xform|bbox (default bbox)
  IK_COMMAND_TYPE=position|pose   (position = less twist; pose = use ORIENTATION_MODE quat)
  EE_BODY_NAME (default fr3_hand_tcp), EE_JACOBI_ROW_OFFSET
  APPROACH_HEIGHT_M — pre-grasp: TCP target = cube center + world (0,0,+this) from center (default 0.12 m)
  CUBE_EXTENT_Z_M — cube height (m), default 0.03; used with GRASP_ABOVE_TOP_M if GRASP_Z_OFFSET_M unset
  GRASP_ABOVE_TOP_M — TCP world +Z above top face = center + extent_z/2 + this (default 0.003)
  GRASP_Z_OFFSET_M — override: TCP target = cube center + (0,0,+this); if unset, computed as half(extent_z)+above_top
  LIFT_Z_OFFSET_M (set 0 to skip lift)
  POST_CLOSE_SETTLE_STEPS — physics settle after close before lift
  IK_ITERS (default 500 per IK phase), IK_RENDER=0 — skip viewport draw during IK (much faster)
  CLOSE_HOLD_STEPS — steps while closing fingers
  KEEP_SIM_OPEN=1 — 跑完后不调用 simulation_app.close()，窗口保持可 Play / 选 prim 看 Property（需手动关窗口结束进程）
  PRE_GRASP_SETTLE_STEPS — 开局先跑这么多步物理（仅手指张开，不锁死手臂），让空中 Cube 落稳后再读坐标（默认 240 @60Hz≈4s）
"""

from __future__ import annotations

import os
from pathlib import Path

from isaaclab.app import AppLauncher

app_launcher = AppLauncher(headless=False)
simulation_app = app_launcher.app

# Module scope: helpers like get_cube_center_world_m use omni.usd (imports inside main() are local only).
import omni.usd

import torch

import isaaclab.sim as sim_utils
from isaaclab.actuators import ImplicitActuatorCfg
from isaaclab.assets import Articulation
from isaaclab.assets.articulation import ArticulationCfg
from isaaclab.controllers import DifferentialIKController, DifferentialIKControllerCfg
from isaaclab.sim import SimulationCfg, SimulationContext
from isaaclab.utils.math import matrix_from_quat, quat_inv, subtract_frame_transforms

from pxr import Gf, Usd, UsdGeom


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
CUBE_PRIM = os.environ.get("CUBE_PRIM", "/World/Cube")
CUBE_CENTER_MODE = os.environ.get("CUBE_CENTER_MODE", "bbox").strip().lower()
EE_BODY_NAME = os.environ.get("EE_BODY_NAME", "fr3_hand_tcp")
EE_JACOBI_ROW_OFFSET = int(os.environ.get("EE_JACOBI_ROW_OFFSET", "-1"))
# "position" = only reach XYZ (orientation free, usually less twisted). "pose" = also match ORIENTATION_MODE quat.
IK_COMMAND_TYPE = os.environ.get("IK_COMMAND_TYPE", "position")
ARM_JOINT_PATTERN = "fr3_joint[1-7]"
FINGER_JOINT_PATTERN = "fr3_finger_joint.*"

DELTA_SCALE = float(os.environ.get("DELTA_SCALE", "0.4"))
IK_LAMBDA = float(os.environ.get("IK_LAMBDA", "0.06"))
SIM_DEVICE = os.environ.get("ISAAC_DEVICE", "cuda:0")
IK_ITERS = int(os.environ.get("IK_ITERS", "500"))
# IK 内每步都 render=True 会非常慢。设 IK_RENDER=0 可只做物理步、大幅提速（画面会跳）。
IK_RENDER = os.environ.get("IK_RENDER", "1").strip().lower() not in ("0", "false", "no")

APPROACH_HEIGHT_M = float(os.environ.get("APPROACH_HEIGHT_M", "0.12"))
# Small cubes: +0.035m above center is usually too high. Default to top face + small margin.
CUBE_EXTENT_Z_M = float(os.environ.get("CUBE_EXTENT_Z_M", "0.03"))
GRASP_ABOVE_TOP_M = float(os.environ.get("GRASP_ABOVE_TOP_M", "0.003"))
_GRASP_Z_DEFAULT = 0.5 * CUBE_EXTENT_Z_M + GRASP_ABOVE_TOP_M
GRASP_Z_OFFSET_M = float(os.environ.get("GRASP_Z_OFFSET_M", str(_GRASP_Z_DEFAULT)))
LIFT_Z_OFFSET_M = float(os.environ.get("LIFT_Z_OFFSET_M", "0.22"))
EXTRA_YAW_DEG = float(os.environ.get("EXTRA_YAW_DEG", "0.0"))
ORIENTATION_MODE = os.environ.get("ORIENTATION_MODE", "down")

FINGER_OPEN = float(os.environ.get("FINGER_OPEN", "0.04"))
FINGER_CLOSED = float(os.environ.get("FINGER_CLOSED", "0.0"))
CLOSE_HOLD_STEPS = int(os.environ.get("CLOSE_HOLD_STEPS", "90"))
# Extra physics steps after close: contacts stabilize before lift (helps "carry cube").
POST_CLOSE_SETTLE_STEPS = int(os.environ.get("POST_CLOSE_SETTLE_STEPS", "120"))
LIFT_ITERS = int(os.environ.get("LIFT_ITERS", "400"))
# Cube 若在 USD 里悬空，需先让重力落稳再读 get_cube_center_world_m，否则 IK 目标仍是「空中」位置。
# 这里不再锁死手臂关节，避免“末端保持原样不动”的误解。
PRE_GRASP_SETTLE_STEPS = int(os.environ.get("PRE_GRASP_SETTLE_STEPS", "240"))
# 默认会 close()，Isaac 整体退出后左侧 Play、右侧 Property 会失效；设 KEEP_SIM_OPEN=1 保持 UI。
KEEP_SIM_OPEN = os.environ.get("KEEP_SIM_OPEN", "0").strip().lower() in ("1", "true", "yes")


def _fr3_cfg() -> ArticulationCfg:
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
                "fr3_finger_joint.*": FINGER_OPEN,
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
                joint_names_expr=[FINGER_JOINT_PATTERN],
                effort_limit_sim=200.0,
                stiffness=2e3,
                damping=1e2,
            ),
        },
    )


def get_cube_center_world_m(cube_prim_path: str) -> tuple[float, float, float]:
    stage = omni.usd.get_context().get_stage()
    cube = stage.GetPrimAtPath(cube_prim_path)
    if not cube.IsValid():
        raise RuntimeError(f"Missing prim: {cube_prim_path}")
    if CUBE_CENTER_MODE not in ("xform", "bbox"):
        raise ValueError("CUBE_CENTER_MODE must be 'xform' or 'bbox'")

    if CUBE_CENTER_MODE == "bbox":
        bbox_cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_])
        world_bound = bbox_cache.ComputeWorldBound(cube)
        box = world_bound.ComputeAlignedBox()
        # Gf.Range3d has no GetCenter() in some USD builds; compute center via min/max.
        c = (box.GetMin() + box.GetMax()) * 0.5
        return float(c[0]), float(c[1]), float(c[2])

    xf = UsdGeom.Xformable(cube)
    m = xf.ComputeLocalToWorldTransform(Usd.TimeCode.Default())
    t = m.ExtractTranslation()
    return float(t[0]), float(t[1]), float(t[2])


def tool_quat_wxyz_world() -> tuple[float, float, float, float]:
    if ORIENTATION_MODE == "identity":
        base = Gf.Rotation()
    elif ORIENTATION_MODE == "down":
        base = Gf.Rotation(Gf.Vec3d(1.0, 0.0, 0.0), 180.0)
    else:
        raise ValueError("ORIENTATION_MODE must be 'down' or 'identity'")
    yaw = Gf.Rotation(Gf.Vec3d(0.0, 0.0, 1.0), EXTRA_YAW_DEG)
    combined = yaw * base
    q = combined.GetQuat()
    imag = q.GetImaginary()
    return (float(q.GetReal()), float(imag[0]), float(imag[1]), float(imag[2]))


def run_ik_phase(
    sim: SimulationContext,
    robot: Articulation,
    diff_ik: DifferentialIKController,
    ee_idx: int,
    ee_jacobi_idx: int,
    arm_joint_ids: torch.Tensor,
    target_pos_b: torch.Tensor,
    target_quat_b: torch.Tensor,
    max_iters: int,
    label: str,
    finger_joint_ids: torch.Tensor | None = None,
    finger_pos_cmd: torch.Tensor | None = None,
) -> None:
    sim_dt = sim.get_physics_dt()
    diff_ik.reset()
    robot.update(sim_dt)
    ee_pose_w = robot.data.body_pose_w[:, ee_idx]
    root_pose_w = robot.data.root_pose_w
    _ee_p, ee_quat_b_curr = subtract_frame_transforms(
        root_pose_w[:, 0:3],
        root_pose_w[:, 3:7],
        ee_pose_w[:, 0:3],
        ee_pose_w[:, 3:7],
    )
    if diff_ik.cfg.command_type == "position":
        diff_ik.set_command(target_pos_b[:, 0:3], ee_quat=ee_quat_b_curr)
    else:
        diff_ik.set_command(torch.cat([target_pos_b, target_quat_b], dim=-1))

    first = True
    for _ in range(max_iters):
        if first:
            first = False
            if finger_joint_ids is not None and finger_pos_cmd is not None:
                robot.set_joint_position_target(finger_pos_cmd, finger_joint_ids)
            sim.step(render=IK_RENDER)
            robot.update(sim.get_physics_dt())
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
        joint_pos_des = joint_pos + DELTA_SCALE * (joint_pos_des - joint_pos)

        robot.set_joint_position_target(joint_pos_des, arm_joint_ids)
        if finger_joint_ids is not None and finger_pos_cmd is not None:
            robot.set_joint_position_target(finger_pos_cmd, finger_joint_ids)
        robot.write_data_to_sim()
        sim.step(render=IK_RENDER)
        robot.update(sim_dt)

    print(f"[{label}] IK phase done ({max_iters} iters).")


def main() -> None:
    if IK_COMMAND_TYPE not in ("position", "pose"):
        raise ValueError("IK_COMMAND_TYPE must be 'position' or 'pose'")

    if not sim_utils.open_stage(USD_PATH):
        raise RuntimeError(f"Failed to open USD: {USD_PATH}")

    for _ in range(20):
        simulation_app.update()

    sim_cfg = SimulationCfg(dt=1.0 / 60.0, device=SIM_DEVICE)
    sim = SimulationContext(sim_cfg)

    robot_cfg = _fr3_cfg()
    robot = Articulation(cfg=robot_cfg)

    diff_ik_cfg = DifferentialIKControllerCfg(
        command_type=IK_COMMAND_TYPE,
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
    finger_joint_ids = robot.find_joints([FINGER_JOINT_PATTERN])[0]
    n_f = int(finger_joint_ids.shape[0]) if hasattr(finger_joint_ids, "shape") else len(finger_joint_ids)
    fingers_open_cmd = torch.full((1, n_f), FINGER_OPEN, device=sim.device, dtype=torch.float32)

    robot.update(sim_dt)

    if PRE_GRASP_SETTLE_STEPS > 0:
        print(
            f"[pre-grasp settle] {PRE_GRASP_SETTLE_STEPS} physics steps: fingers open, "
            "let cube settle (e.g. drop onto disk) before reading target."
        )
        for _ in range(PRE_GRASP_SETTLE_STEPS):
            robot.set_joint_position_target(fingers_open_cmd, finger_joint_ids)
            robot.write_data_to_sim()
            sim.step(render=True)
            robot.update(sim_dt)

    def read_cube_center_world() -> tuple[float, float, float]:
        return get_cube_center_world_m(CUBE_PRIM)

    cx, cy, cz = get_cube_center_world_m(CUBE_PRIM)
    qw, qx, qy, qz = tool_quat_wxyz_world()
    print(
        "[grasp] cube center (world m):",
        f"{cx:.6f}, {cy:.6f}, {cz:.6f}",
        "| tool quat wxyz (world):",
        f"{qw:.4f}, {qx:.4f}, {qy:.4f}, {qz:.4f}",
    )
    print(
        "[grasp] center mode",
        CUBE_CENTER_MODE,
        "| CUBE_EXTENT_Z_M",
        CUBE_EXTENT_Z_M,
        "| GRASP_ABOVE_TOP_M",
        GRASP_ABOVE_TOP_M,
        "=> GRASP_Z_OFFSET_M",
        GRASP_Z_OFFSET_M,
    )
    print(
        "[IK] command_type",
        IK_COMMAND_TYPE,
        "| EE",
        EE_BODY_NAME,
        "body_idx",
        ee_idx,
        "jacobian_row",
        ee_jacobi_idx,
        "| DELTA_SCALE",
        DELTA_SCALE,
        "IK_LAMBDA",
        IK_LAMBDA,
    )

    device = sim.device
    cube_w = torch.tensor([[cx, cy, cz]], device=device, dtype=torch.float32)
    quat_w = torch.tensor([[qw, qx, qy, qz]], device=device, dtype=torch.float32)

    def pose_w_to_b(pos_w: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        root_pose_w = robot.data.root_pose_w
        return subtract_frame_transforms(
            root_pose_w[:, 0:3],
            root_pose_w[:, 3:7],
            pos_w,
            quat_w,
        )

    # --- Phase 1: pre-grasp (keep fingers open) ---
    robot.set_joint_position_target(fingers_open_cmd, finger_joint_ids)
    robot.write_data_to_sim()
    pre_w = cube_w + torch.tensor([[0.0, 0.0, APPROACH_HEIGHT_M]], device=device)
    pos_b, quat_b = pose_w_to_b(pre_w)
    run_ik_phase(
        sim,
        robot,
        diff_ik,
        ee_idx,
        ee_jacobi_idx,
        arm_joint_ids,
        pos_b,
        quat_b,
        IK_ITERS,
        "pre-grasp",
        finger_joint_ids=finger_joint_ids,
        finger_pos_cmd=fingers_open_cmd,
    )

    # Re-read cube center after pre-grasp: object may drift/bounce during approach.
    cx2, cy2, cz2 = read_cube_center_world()
    cube_w = torch.tensor([[cx2, cy2, cz2]], device=device, dtype=torch.float32)
    print(
        "[re-target] cube center before grasp approach (world m):",
        f"{cx2:.6f}, {cy2:.6f}, {cz2:.6f}",
    )

    # --- Phase 2: lower toward grasp (fingers still open) ---
    robot.set_joint_position_target(fingers_open_cmd, finger_joint_ids)
    robot.write_data_to_sim()
    grasp_w = cube_w + torch.tensor([[0.0, 0.0, GRASP_Z_OFFSET_M]], device=device)
    pos_b, quat_b = pose_w_to_b(grasp_w)
    run_ik_phase(
        sim,
        robot,
        diff_ik,
        ee_idx,
        ee_jacobi_idx,
        arm_joint_ids,
        pos_b,
        quat_b,
        IK_ITERS,
        "grasp approach",
        finger_joint_ids=finger_joint_ids,
        finger_pos_cmd=fingers_open_cmd,
    )

    # --- Close gripper ---
    closed = torch.full((1, n_f), FINGER_CLOSED, device=device, dtype=torch.float32)
    robot.set_joint_position_target(closed, finger_joint_ids)
    robot.write_data_to_sim()
    print(f"[close] finger target = {FINGER_CLOSED} for {CLOSE_HOLD_STEPS} steps.")
    for _ in range(CLOSE_HOLD_STEPS):
        sim.step(render=True)
        robot.update(sim_dt)

    print(
        f"[settle] {POST_CLOSE_SETTLE_STEPS} steps: freeze arm at current joints + keep fingers closed before lift."
    )
    for _ in range(POST_CLOSE_SETTLE_STEPS):
        arm_hold = robot.data.joint_pos[:, arm_joint_ids]
        robot.set_joint_position_target(arm_hold, arm_joint_ids)
        robot.set_joint_position_target(closed, finger_joint_ids)
        robot.write_data_to_sim()
        sim.step(render=True)
        robot.update(sim_dt)

    # --- Phase 3: lift (optional) ---
    if LIFT_Z_OFFSET_M > 1e-6:
        lift_w = cube_w + torch.tensor([[0.0, 0.0, LIFT_Z_OFFSET_M]], device=device, dtype=torch.float32)
        pos_b, quat_b = pose_w_to_b(lift_w)
        run_ik_phase(
            sim,
            robot,
            diff_ik,
            ee_idx,
            ee_jacobi_idx,
            arm_joint_ids,
            pos_b,
            quat_b,
            LIFT_ITERS,
            "lift",
            finger_joint_ids=finger_joint_ids,
            finger_pos_cmd=closed,
        )

    print(
        "Done grasp sequence. If the cube did not lift with the arm: increase friction on cube/gripper, "
        "tune GRASP_Z_OFFSET_M / FINGER_CLOSED, or hold longer (POST_CLOSE_SETTLE_STEPS)."
    )

    for _ in range(120):
        sim.step(render=True)
        robot.update(sim_dt)

    if KEEP_SIM_OPEN:
        print(
            "[ui] KEEP_SIM_OPEN=1: 不关闭 Isaac。关闭视窗或 Ctrl+C 结束进程。"
        )
        while simulation_app.is_running():
            simulation_app.update()
    else:
        simulation_app.close()


if __name__ == "__main__":
    main()
