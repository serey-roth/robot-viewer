from dataclasses import dataclass, field, fields

import math
import threading
import time

import numpy as np
import sapien
import sapien.physx
import dexmate_urdf
from dexcomm import Publisher, Subscriber, ZenohConfig, serve
from dexcomm.codecs import (
    JointStateCodec, JointCmdCodec,
    DictDataCodec, BMSStateCodec, EStopStateCodec, BasicDataCodec,
)

from motion_planner import MotionPlanner, build_planners

COMPONENT_JOINTS: dict[str, list[str]] = {
    "left_arm":        [f"L_arm_j{i}" for i in range(1, 8)],
    "right_arm":       [f"R_arm_j{i}" for i in range(1, 8)],
    "left_hand":       ["L_th_j1", "L_ff_j1", "L_mf_j1", "L_rf_j1", "L_lf_j1", "L_th_j0"],
    "right_hand":      ["R_th_j1", "R_ff_j1", "R_mf_j1", "R_rf_j1", "R_lf_j1", "R_th_j0"],
    "torso":           ["torso_j1", "torso_j2", "torso_j3"],
    "head":            ["head_j1", "head_j2", "head_j3"],
    "chassis_steer":   ["L_wheel_j1", "R_wheel_j1"],
    "chassis_drive":   ["L_wheel_j2", "R_wheel_j2"],
}

STATE_TOPICS = {
    "left_arm":      "state/arm/left",
    "right_arm":     "state/arm/right",
    "left_hand":     "state/hand/left",
    "right_hand":    "state/hand/right",
    "torso":         "state/torso",
    "head":          "state/head",
    "chassis_steer": "state/chassis/steer",
    "chassis_drive": "state/chassis/drive",
}

CMD_TOPICS = {
    "left_arm":      "control/arm/left",
    "right_arm":     "control/arm/right",
    "left_hand":     "control/hand/left",
    "right_hand":    "control/hand/right",
    "torso":         "control/torso",
    "head":          "control/head",
    "chassis_steer": "control/chassis/steer",
    "chassis_drive": "control/chassis/drive",
}

@dataclass
class Battery:
    timestamp_ns: int
    voltage: float
    current: float
    temperature: float
    percentage: float
    
@dataclass
class EStop:
    timestamp_ns: int
    left_base_estop_enabled: bool = False
    right_base_estop_enabled: bool = False
    torso_estop_enabled: bool = False
    remote_estop_enabled: bool = False
    software_estop_enabled: bool = False

@dataclass
class Joint:
    pos: float = 0.0
    vel: float = 0.0
    torque: float = 0.0
    cur: float = 0.0
    timestamp_ns: int = 0

def _joint() -> Joint:
    return field(default_factory=Joint)

@dataclass
class LeftArmJoints:
    L_arm_j1: Joint = _joint()
    L_arm_j2: Joint = _joint()
    L_arm_j3: Joint = _joint()
    L_arm_j4: Joint = _joint()
    L_arm_j5: Joint = _joint()
    L_arm_j6: Joint = _joint()
    L_arm_j7: Joint = _joint()

@dataclass
class RightArmJoints:
    R_arm_j1: Joint = _joint()
    R_arm_j2: Joint = _joint()
    R_arm_j3: Joint = _joint()
    R_arm_j4: Joint = _joint()
    R_arm_j5: Joint = _joint()
    R_arm_j6: Joint = _joint()
    R_arm_j7: Joint = _joint()

@dataclass
class LeftHandJoints:
    L_th_j1: Joint = _joint()
    L_ff_j1: Joint = _joint()
    L_mf_j1: Joint = _joint()
    L_rf_j1: Joint = _joint()
    L_lf_j1: Joint = _joint()
    L_th_j0: Joint = _joint()

@dataclass
class RightHandJoints:
    R_th_j1: Joint = _joint()
    R_ff_j1: Joint = _joint()
    R_mf_j1: Joint = _joint()
    R_rf_j1: Joint = _joint()
    R_lf_j1: Joint = _joint()
    R_th_j0: Joint = _joint()

@dataclass
class TorsoJoints:
    torso_j1: Joint = _joint()
    torso_j2: Joint = _joint()
    torso_j3: Joint = _joint()

@dataclass
class HeadJoints:
    head_j1: Joint = _joint()
    head_j2: Joint = _joint()
    head_j3: Joint = _joint()

@dataclass
class ChassisSteerJoints:
    L_wheel_j1: Joint = _joint()
    R_wheel_j1: Joint = _joint()

@dataclass
class ChassisDriveJoints:
    L_wheel_j2: Joint = _joint()
    R_wheel_j2: Joint = _joint()

class RobotState:
    def __init__(self, model_name = "vega_1"):
        self.robot_name = model_name
        
        self.left_arm = LeftArmJoints()
        self.right_arm = RightArmJoints()
        self.left_hand = LeftHandJoints()
        self.right_hand = RightHandJoints()
        self.torso = TorsoJoints()
        self.head = HeadJoints()
        self.chassis_steer = ChassisSteerJoints()
        self.chassis_drive = ChassisDriveJoints()
        
        timestamp_ns = time.time_ns()

        # Mock battery and estop to prevent failed robot system initialization
        self.battery = Battery(
            timestamp_ns,
            voltage=48.0,
            current=0.0,
            temperature=25.0,
            percentage=100,
        )
        self.estop = EStop(timestamp_ns)

    def to_dict(self) -> dict[str, dict[str, float]]:
        result: dict[str, dict[str, float]] = {}
        for comp, joint_names in COMPONENT_JOINTS.items():
            component = getattr(self, comp, None)
            if component is None:
                continue
            for f, name in zip(fields(component), joint_names):
                joint = getattr(component, f.name)
                result[name] = {"pos": float(joint.pos), "vel": float(joint.vel)}
        return result

    def update_component(
        self,
        comp: str,
        pos: np.ndarray,
        vel: np.ndarray,
        torque: np.ndarray,
        cur: np.ndarray,
        timestamp_ns: int,
    ) -> None:
        component = getattr(self, comp)
        for f, p, v, t, c in zip(fields(component), pos, vel, torque, cur):
            joint = getattr(component, f.name)
            joint.pos = float(p)
            joint.vel = float(v)
            joint.torque = float(t)
            joint.cur = float(c)
            joint.timestamp_ns = timestamp_ns


def get_robot_urdf_path(model_name="vega_1"):
    _urdf_dir = next(
    p.parent for p in dexmate_urdf.get_urdf_paths("humanoid", "vega_1")
    if p.name == "vega_1_f5d6.urdf"
    )
    return str(_urdf_dir / "vega_1_f5d6.urdf")


class RobotSimulation:
    def __init__(self, model_name: str = "vega_1", config: ZenohConfig | None = None):
        self._topic_prefix = f"{model_name}/"
        self._config = config
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._timestep = 1/240.0

        self._load_scene()
        self._load_robot(model_name)
        self._planners: dict[str, MotionPlanner] = build_planners(COMPONENT_JOINTS, self._timestep)
        self._setup_comms()

        self._heartbeat_thread = threading.Thread(
            target=self._setup_heartbeat, daemon=True, name="heartbeat"
        )
        self._heartbeat_thread.start()
        
    @property
    def state(self) -> RobotState:
        return self._state

    def start_simulation(self):
        self._stop.clear()
        self.run()
        
    def stop_simulation(self):
        self._stop.set()

    def run(self):
        dt = self._timestep
        step = 0
        next_t = time.perf_counter() + dt

        while not self._stop.is_set():
            self._apply_joint_targets()
            self._scene.step()
            step += 1

            if step % 8 == 0:  # ~30 Hz publish rate
                self._publish_states()

            # Sleep if we're ahead; if we're behind, snap the clock forward
            # instead of accumulating debt. sleep(0.0) still yields the GIL, so
            # Zenoh callbacks and the asyncio loop always get scheduled.
            next_t += dt
            now = time.perf_counter()
            time.sleep(max(0.0, next_t - now))
            next_t = max(next_t, now)

    def _load_scene(self):
        sapien.physx.set_scene_config(gravity=np.array([0, 0, 0], dtype=np.float32))
        self._physx_system = sapien.physx.PhysxCpuSystem()
        self._scene = sapien.Scene([self._physx_system])
        self._scene.set_timestep(self._timestep)

    def _load_robot(self, model_name: str = "vega_1"):
        loader = self._scene.create_urdf_loader()
        loader.fix_root_link = True
        builder = loader.load_file_as_articulation_builder(get_robot_urdf_path(model_name))
        for lb in builder.link_builders:
            lb.visual_records.clear()

        self._robot = builder.build()
        self._robot.set_pose(sapien.Pose([0, 0, 0.05]))

        n_dof = len(self._robot.get_active_joints())
        self._robot.set_qpos(np.zeros(n_dof))
        self._robot.set_qvel(np.zeros(n_dof))

        self._joints = {j.name: j for j in self._robot.get_active_joints()}
        self._joint_index = {j.name: i for i, j in enumerate(self._robot.get_active_joints())}
        for j in self._joints.values():
            j.set_drive_properties(stiffness=1000, damping=50)

        self._state = RobotState(model_name)
        
    def _hand_type_handler(self, _):
        return {"left": "HandF5D6_V2", "right": "HandF5D6_V2"}

    def _versions_handler(self, _):
        return {"version": "0.0.0", "firmware_version": {}, "min_client_version": "0.0.0"}

    def _arm_mode_handler(self, _):
        return {"success": True, "mode": [1, 1, 1, 1, 1, 1, 1]}

    def _head_mode_handler(self, _):
        return {"success": True, "mode": [1, 1, 1]}

    def _torso_mode_handler(self, _):
        return {"success": True, "mode": [1, 1, 1]}

    def _estop_service_handler(self, _):
        return {"success": True}

    def _register_services(self):
        p = self._topic_prefix
        cfg = self._config
        self._services = [
            serve(f"{p}info/hand_type",  handler=self._hand_type_handler,    response_encoder=DictDataCodec.encode, config=cfg),
            serve(f"{p}info/versions",   handler=self._versions_handler,      response_encoder=DictDataCodec.encode, config=cfg),
            serve(f"{p}mode/arm/left",   handler=self._arm_mode_handler,      response_encoder=DictDataCodec.encode, config=cfg),
            serve(f"{p}mode/arm/right",  handler=self._arm_mode_handler,      response_encoder=DictDataCodec.encode, config=cfg),
            serve(f"{p}mode/head",       handler=self._head_mode_handler,     response_encoder=DictDataCodec.encode, config=cfg),
            serve(f"{p}mode/torso",      handler=self._torso_mode_handler,    response_encoder=DictDataCodec.encode, config=cfg),
            serve(f"{p}system/estop",    handler=self._estop_service_handler, response_encoder=DictDataCodec.encode, config=cfg),
        ]
        
    def _setup_comms(self):
        p = self._topic_prefix
        cfg = self._config

        self._pubs = {
            comp: Publisher(f"{p}{topic}", encoder=JointStateCodec.encode, config=cfg)
            for comp, topic in STATE_TOPICS.items()
        }
        self._battery_pub = Publisher(f"{p}state/bms", encoder=BMSStateCodec.encode, config=cfg)
        self._estop_pub = Publisher(f"{p}state/estop", encoder=EStopStateCodec.encode, config=cfg)
        self._heartbeat_pub = Publisher(f"{p}heartbeat", encoder=BasicDataCodec.encode_u64, config=cfg)

        self._subs = [
            Subscriber(f"{p}{topic}", callback=self._make_cmd_handler(comp), decoder=JointCmdCodec.decode, config=cfg)
            for comp, topic in CMD_TOPICS.items()
        ]

        self._register_services()

    def _make_cmd_handler(self, comp: str):
        def on_cmd(cmd: dict):
            pos = cmd.get("pos", [])
            with self._lock:
                self._planners[comp].set_target(pos)
        return on_cmd

    def _apply_joint_targets(self):
        with self._lock:
            for comp, planner in self._planners.items():
                next_pos = planner.step()
                for name, pos in zip(COMPONENT_JOINTS[comp], next_pos):
                    if name in self._joints:
                        self._joints[name].set_drive_target(pos)

    def _update_component(
        self,
        comp: str,
        joint_names: list[str],
        qpos: np.ndarray,
        qvel: np.ndarray,
        ts: int,
    ) -> None:
        planner_pos = self._planners[comp]._inp.current_position
        n = len(joint_names)
        pos_arr = np.zeros(n, dtype=np.float32)
        vel_arr = np.zeros(n, dtype=np.float32)
        for i, name in enumerate(joint_names):
            idx = self._joint_index.get(name)
            if idx is not None and idx < len(qpos):
                val = float(qpos[idx])
                pos_arr[i] = val if not math.isnan(val) else planner_pos[i]
                v = float(qvel[idx]) if idx < len(qvel) else 0.0
                vel_arr[i] = 0.0 if math.isnan(v) else v
            else:
                pos_arr[i] = planner_pos[i]
        self._state.update_component(comp, pos_arr, vel_arr, np.zeros(n, dtype=np.float32), np.zeros(n, dtype=np.float32), ts)

    def _publish_component(self, comp: str) -> None:
        component = getattr(self._state, comp)
        joint_fields = fields(component)
        
        self._pubs[comp].publish({
            "pos": [float(getattr(component, f.name).pos) for f in joint_fields],
            "vel": [float(getattr(component, f.name).vel) for f in joint_fields],
            "torque": [float(getattr(component, f.name).torque) for f in joint_fields],
            "cur": [float(getattr(component, f.name).cur) for f in joint_fields],
            "timestamp_ns": int(getattr(component, joint_fields[0].name).timestamp_ns) if joint_fields else 0,
        })

    def _publish_battery(self) -> None:
        batt = self._state.battery
        self._battery_pub.publish({
            "timestamp_ns": batt.timestamp_ns,
            "voltage": batt.voltage,
            "current": batt.current,
            "temperature": batt.temperature,
            "percentage": batt.percentage,
        })

    def _publish_estop(self) -> None:
        es = self._state.estop
        self._estop_pub.publish({
            "timestamp_ns": es.timestamp_ns,
            "left_base_estop_enabled": es.left_base_estop_enabled,
            "right_base_estop_enabled": es.right_base_estop_enabled,
            "torso_estop_enabled": es.torso_estop_enabled,
            "remote_estop_enabled": es.remote_estop_enabled,
            "software_estop_enabled": es.software_estop_enabled,
        })

    def _publish_states(self):
        ts = time.time_ns()
        qpos = self._robot.get_qpos()
        qvel = self._robot.get_qvel()

        for comp, joint_names in COMPONENT_JOINTS.items():
            self._update_component(comp, joint_names, qpos, qvel, ts)
            self._publish_component(comp)

        self._publish_battery()
        self._publish_estop()

    def _setup_heartbeat(self) -> None:
        """
        Guarantees a stable heartbeat rate regardless of SAPIEN physics load.
        We need to do this separately otherwise watchdog will shutdown system
        if heartbeat rate is too slow.
        """
        while True:
            try:
                self._heartbeat_pub.publish(time.time_ns())
                self._ready.set()
            except Exception:
                pass
            time.sleep(0.02)  # 50 Hz
    