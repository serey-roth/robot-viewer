from ruckig import InputParameter, OutputParameter, Result, Ruckig


# Per-component kinematic limits (rad/s, rad/s², rad/s³).
# Chassis drive joints are wheels so limits are higher.
COMPONENT_LIMITS: dict[str, tuple[float, float, float]] = {
    "left_arm":      (1.5, 3.0,  8.0),
    "right_arm":     (1.5, 3.0,  8.0),
    "left_hand":     (2.0, 5.0, 15.0),
    "right_hand":    (2.0, 5.0, 15.0),
    "torso":         (0.5, 1.0,  3.0),
    "head":          (1.0, 2.0,  5.0),
    "chassis_steer": (1.0, 2.0,  5.0),
    "chassis_drive": (5.0, 10.0, 20.0),
}


class MotionPlanner:
    """Single-component online trajectory generator backed by Ruckig.

    Maintains its own internal state (position, velocity, acceleration) so
    the physics loop only needs to call set_target() when a new command
    arrives and step() on every tick to get the next drive target.
    """

    def __init__(self, dof: int, dt: float, max_vel: float, max_acc: float, max_jerk: float):
        self._otg = Ruckig(dof, dt)
        self._inp = InputParameter(dof)
        self._out = OutputParameter(dof)

        self._inp.max_velocity     = [max_vel]  * dof
        self._inp.max_acceleration = [max_acc]  * dof
        self._inp.max_jerk         = [max_jerk] * dof

        zeros = [0.0] * dof
        self._inp.current_position     = zeros[:]
        self._inp.current_velocity     = zeros[:]
        self._inp.current_acceleration = zeros[:]
        self._inp.target_position      = zeros[:]
        self._inp.target_velocity      = zeros[:]
        self._inp.target_acceleration  = zeros[:]

    def set_target(self, positions: list[float]) -> None:
        self._inp.target_position = [float(p) for p in positions]

    def step(self) -> list[float]:
        result = self._otg.update(self._inp, self._out)
        if result == Result.Finished:
            return list(self._inp.target_position)
        self._out.pass_to_input(self._inp)
        return list(self._out.new_position)


def build_planners(component_joints: dict[str, list[str]], dt: float) -> dict[str, MotionPlanner]:
    return {
        comp: MotionPlanner(len(joints), dt, *COMPONENT_LIMITS[comp])
        for comp, joints in component_joints.items()
    }
