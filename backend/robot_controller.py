import time
import numpy as np
from typing import Literal

from dexbot_utils.configs.registry import get_robot_config
from dexcontrol.robot import Robot

Action = Literal[
    "open_right_hand",
    "open_left_hand",
    "open_both_hands",
    "close_right_hand",
    "close_left_hand",
    "close_both_hands",
    "move_arm",
    "move_torso",
    "move_head",
    "move_chassis"
]

# RobotControls methods are adapted from the dexcontrol basic examples:
# https://github.com/dexmate-ai/dexcontrol/tree/main/examples/basic_examples/control
class RobotControls:
    def __init__(self, robot: Robot):
        self._robot = robot

    def open_right_hand(self) -> None:
        self._robot.right_hand.open_hand()

    def open_left_hand(self) -> None:
        self._robot.left_hand.open_hand()

    def open_both_hands(self) -> None:
        self.open_right_hand()
        self.open_left_hand()

    def close_right_hand(self) -> None:
        self._robot.right_hand.close_hand()

    def close_left_hand(self) -> None:
        self._robot.left_hand.close_hand()

    def close_both_hands(self) -> None:
        self.close_right_hand()
        self.close_left_hand()

    def move_arm(self, side: Literal["right", "left"] = "right", step_size: float = 0.2) -> None:
        """Executes a sequence of arm movements to demonstrate joint control.

        Args:
            side: Which arm to move ("right" or "left").
            step_size: Magnitude of joint movement in radians.
        """
        arm = self._robot.left_arm if side == "left" else self._robot.right_arm

        arm.set_joint_pos(np.zeros(7))
        time.sleep(1.5)

        for joint_idx in range(7):
            target_pos = np.zeros(7)
            target_pos[joint_idx] = step_size
            arm.set_joint_pos(target_pos)
            time.sleep(1.5)

            arm.set_joint_pos(np.zeros(7))
            time.sleep(1.5)

    def _move_head_joint_sequence(
        self,
        joint_idx: int,
        step_size: float,
        motion_timeout: float = 2.0,
    ) -> None:
        """Executes movement sequence for a single head joint.

        Args:
            joint_idx: Index of joint to move.
            step_size: Size of joint movement in radians.
            motion_timeout: Seconds to wait for each motion.
        """
        head = self._robot.head

        positive_pos = np.zeros(3)
        negative_pos = np.zeros(3)
        positive_pos[joint_idx] = step_size
        negative_pos[joint_idx] = -step_size

        head.set_joint_pos(positive_pos)
        time.sleep(1.5)

        head.set_joint_pos(negative_pos)
        time.sleep(1.5)

        head.set_joint_pos(np.zeros(3))
        time.sleep(1.5)

    def move_head(self, step_size: float = 0.5, motion_timeout: float = 2.0) -> None:
        """Moves the head to an initial position then exercises each joint.

        Args:
            step_size: Size of joint movement in radians.
            motion_timeout: Seconds to wait for each motion.
        """
        head = self._robot.head

        initial_pos = np.array([-np.pi / 6, 0.0, 0.0])
        head.set_joint_pos(initial_pos)
        time.sleep(1.5)

        for joint_idx in range(3):
            self._move_head_joint_sequence(joint_idx, step_size, motion_timeout)

        head.set_joint_pos(np.zeros(3))


    def move_chassis(self, speed: float = 0.1, duration: float = 4.0) -> None:
        """Executes a sequence of chassis movements.

        Args:
            speed: Linear velocity (m/s) or angular velocity (rad/s).
            duration: Time to maintain each movement in seconds.
        """
        chassis = self._robot.chassis

        chassis.move_straight(speed, wait_time=duration)
        chassis.move_straight(-speed, wait_time=duration)

        chassis.move_sideways(speed, wait_time=duration)
        chassis.move_sideways(-speed, wait_time=duration)

        chassis.turn(speed, wait_time=duration)
        chassis.turn(-speed, wait_time=duration)


    def move_torso(self) -> None:
        """Moves the torso through a sequence of named poses and custom positions."""
        POSE_SEQUENCE: list[tuple[str, float]] = [
            ("home",            3.0),
            ("crouch20_low",    3.0),
            ("crouch20_medium", 3.0),
            ("crouch20_high",   3.0),
            ("crouch45_high",   3.0),
            ("crouch45_medium", 3.0),
            ("crouch45_low",    3.0),
            ("crouch90_low",    4.0),
            ("crouch90_medium", 4.0),
            ("crouch90_high",   4.0),
            ("crouch45_medium", 3.0),
            ("home",            4.0),
        ]

        torso = self._robot.torso
        for pose_name, _ in POSE_SEQUENCE:
            print(f"  → {pose_name}")
            pose = torso.get_predefined_pose(pose_name)
            torso.set_joint_pos(pose)
            time.sleep(2.0)

        print("  → custom: lean forward (j1=45°, j2=90°, j3=−45°)")
        torso.set_joint_pos(np.deg2rad([45, 90, -45]))
        time.sleep(2.0)

        print("  → custom: side tilt (j1=30°, j2=60°, j3=15°)")
        torso.set_joint_pos(np.deg2rad([30, 60, 15]))
        time.sleep(2.0)

        print("  → home")
        torso.set_joint_pos(np.zeros(3))
        time.sleep(2.0)

class RobotController:
    def __init__(self, model_name: str = "vega_1"):
        config = get_robot_config(model_name)
        self._robot = Robot(configs=config)
        self._controls = RobotControls(self._robot)
        self._components = set(config.components.keys())

    def _has(self, component: str) -> bool:
        return component in self._components

    def dispatch(self, action: str, **kwargs) -> None:
        if action == "open_right_hand":
            if not self._has("right_hand"):
                raise ValueError("This robot does not have a right hand.")
            self._controls.open_right_hand()

        elif action == "open_left_hand":
            if not self._has("left_hand"):
                raise ValueError("This robot does not have a left hand.")
            self._controls.open_left_hand()

        elif action == "open_both_hands":
            if not self._has("left_hand"):
                raise ValueError("This robot does not have a left hand.")
            if not self._has("right_hand"):
                raise ValueError("This robot does not have a right hand.")
            self._controls.open_both_hands()

        elif action == "close_right_hand":
            if not self._has("right_hand"):
                raise ValueError("This robot does not have a right hand.")
            self._controls.close_right_hand()

        elif action == "close_left_hand":
            if not self._has("left_hand"):
                raise ValueError("This robot does not have a left hand.")
            self._controls.close_left_hand()

        elif action == "close_both_hands":
            if not self._has("left_hand"):
                raise ValueError("This robot does not have a left hand.")
            if not self._has("right_hand"):
                raise ValueError("This robot does not have a right hand.")
            self._controls.close_both_hands()

        elif action == "move_arm":
            self._controls.move_arm(**kwargs)

        elif action == "move_head":
            self._controls.move_head(**kwargs)

        elif action == "move_chassis":
            if not self._has("chassis_steer"):
                raise ValueError("This robot does not have a chassis.")
            self._controls.move_chassis(**kwargs)

        elif action == "move_torso":
            if not self._has("torso"):
                raise ValueError("This robot does not have a torso.")
            self._controls.move_torso(**kwargs)

        else:
            raise ValueError(f"Unknown action: '{action}'.")

    def __enter__(self) -> "RobotController":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._robot.__exit__(exc_type, exc_val, exc_tb)
