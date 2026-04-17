##/home/agiuser/miniconda3/envs/isaaclab/lib/python3.11/site-packages/isaacsim/exts/isaacsim.examples.interactive/isaacsim/examples/interactive/hello_world/hello_world.py

# SPDX-FileCopyrightText: Copyright (c) 2020-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Isaac Sim 5.x: omni.isaac.* -> isaacsim.*
# See https://docs.isaacsim.omniverse.nvidia.com/latest/index.html

import numpy as np
from isaacsim.core.api.controllers.base_controller import BaseController
from isaacsim.core.api.objects import DynamicCuboid
from isaacsim.core.api.scenes.scene import Scene
from isaacsim.core.api.tasks import BaseTask
from isaacsim.core.utils.stage import get_stage_units
from isaacsim.core.utils.types import ArticulationAction
from isaacsim.examples.interactive.base_sample import BaseSample
from isaacsim.robot.manipulators.examples.franka import Franka
from isaacsim.robot.manipulators.examples.franka.controllers.pick_place_controller import PickPlaceController
from isaacsim.robot.manipulators.grippers.parallel_gripper import ParallelGripper


class FrankaPlaying(BaseTask):
    """Pick-and-place style task: ground plane, dynamic cube, and Franka."""

    def __init__(self, name: str) -> None:
        super().__init__(name=name, offset=None)
        self._goal_position = np.zeros(3)
        self._cube_size = np.array([0.05515, 0.05515, 0.05515]) / get_stage_units()
        self._cube_initial_position = np.array([0.3, 0.3, 0.3]) / get_stage_units()
        self._goal_position[0] = -0.3 / get_stage_units()
        self._goal_position[1] = -0.3 / get_stage_units()
        self._goal_position[2] = 0.05515 / 2.0 / get_stage_units()
        self._task_achieved = False
        self._cube = None
        self._franka = None

    def set_up_scene(self, scene: Scene) -> None:
        super().set_up_scene(scene)
        scene.add_default_ground_plane()
        self._cube = scene.add(
            DynamicCuboid(
                prim_path="/World/random_cube",
                name="fancy_cube",
                position=self._cube_initial_position,
                scale=self._cube_size,
                size=1.0,
                color=np.array([0.0, 0.0, 1.0]),
            )
        )
        self._task_objects[self._cube.name] = self._cube
        self._franka = scene.add(
            Franka(
                prim_path="/World/Fancy_Franka",
                name="fancy_franka",
            )
        )
        self._task_objects[self._franka.name] = self._franka
        self._move_task_objects_to_their_frame()
        return

    def get_observations(self) -> dict:
        cube_position, _ = self._cube.get_world_pose()
        joint_positions = self._franka.get_joint_positions()
        return {
            self._franka.name: {"joint_positions": joint_positions},
            self._cube.name: {"position": cube_position, "goal_position": self._goal_position},
        }

    def get_params(self) -> dict:
        return {
            "robot_name": {"value": self._franka.name, "modifiable": False},
            "cube_name": {"value": self._cube.name, "modifiable": False},
        }

    def calculate_metrics(self) -> dict:
        return {}

    def is_done(self) -> bool:
        return False

    def pre_step(self, time_step_index: int, simulation_time: float) -> None:
        super().pre_step(time_step_index=time_step_index, simulation_time=simulation_time)
        cube_position, _ = self._cube.get_world_pose()
        if not self._task_achieved and np.mean(np.abs(self._goal_position - cube_position)) < 0.02:
            self._cube.get_applied_visual_material().set_color(np.array([0.0, 1.0, 0.0]))
            self._task_achieved = True
        return

    def post_reset(self) -> None:
        if self._franka is not None and isinstance(self._franka.gripper, ParallelGripper):
            self._franka.gripper.set_joint_positions(self._franka.gripper.joint_opened_positions)
        if self._cube is not None:
            self._cube.get_applied_visual_material().set_color(np.array([0.0, 0.0, 1.0]))
        self._task_achieved = False
        return


class CoolController(BaseController):
    """Minimal custom controller; override `forward` with your control law."""

    def __init__(self) -> None:
        super().__init__(name="my_cool_controller")

    def forward(self, *args, **kwargs) -> ArticulationAction:
        return ArticulationAction()


class HelloWorld(BaseSample):
    def __init__(self) -> None:
        super().__init__()
        self._controller = None
        self._articulation_controller = None
        self._franka = None

    def setup_scene(self) -> None:
        world = self.get_world()
        world.add_task(FrankaPlaying(name="my_first_task"))
        return

    async def setup_post_load(self) -> None:
        self._world = self.get_world()
        self._franka = self._world.scene.get_object("fancy_franka")
        self._controller = PickPlaceController(
            name="pick_place_controller",
            gripper=self._franka.gripper,
            robot_articulation=self._franka,
        )
        self._articulation_controller = self._franka.get_articulation_controller()
        self._world.add_physics_callback("sim_step", self._pick_place_physics_step)
        await self._world.play_async()
        return

    def _pick_place_physics_step(self, step_size: float) -> None:
        observations = self._world.get_observations()
        actions = self._controller.forward(
            picking_position=observations["fancy_cube"]["position"],
            placing_position=observations["fancy_cube"]["goal_position"],
            current_joint_positions=observations["fancy_franka"]["joint_positions"],
        )
        if self._controller.is_done():
            self._world.pause()
        self._articulation_controller.apply_action(actions)
        return

    async def setup_pre_reset(self) -> None:
        world = self.get_world()
        if world.physics_callback_exists("sim_step"):
            world.remove_physics_callback("sim_step")
        if self._controller is not None:
            self._controller.reset()
        return

    async def setup_post_reset(self) -> None:
        self.get_world().add_physics_callback("sim_step", self._pick_place_physics_step)
        await self.get_world().play_async()
        return

    async def setup_post_clear(self) -> None:
        self._controller = None
        self._articulation_controller = None
        self._franka = None
        return

    def world_cleanup(self) -> None:
        world = self.get_world()
        if world is not None and world.physics_callback_exists("sim_step"):
            world.remove_physics_callback("sim_step")
        self._controller = None
        self._articulation_controller = None
        self._franka = None
        return
