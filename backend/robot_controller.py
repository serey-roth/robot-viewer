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
    "close_both_hands"
]

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

        else:
            raise ValueError(f"Unknown action: '{action}'.")

    def __enter__(self) -> "RobotController":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._robot.__exit__(exc_type, exc_val, exc_tb)
