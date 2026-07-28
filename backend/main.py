import asyncio
import json
import random
from dataclasses import dataclass
from enum import Enum

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware


class RobotConnectivity(Enum):
    ONLINE = "online"
    OFFLINE = "offline"


class RobotActivity(Enum):
    IDLE = "idle"
    MOVE = "moving"
    PICK = "picking"
    PLACE = "placing"


class RobotBatteryConsumption(Enum):
    IDLE = 0.0
    MOVE = 1.2
    PICK = 2.4
    PLACE = 1.8


# Cycle order and how many ticks each activity lasts
ACTIVITY_CYCLE: list[tuple[RobotActivity, int]] = [
    (RobotActivity.MOVE,  5),
    (RobotActivity.PICK,  4),
    (RobotActivity.PLACE, 3),
]


@dataclass
class Robot:
    id: str
    name: str
    connectivity: RobotConnectivity = RobotConnectivity.OFFLINE
    activity: RobotActivity = RobotActivity.IDLE
    battery_percentage: float = 100.0
    base_decay_rate: float = 0.5
    elapsed_cycles: int = 0

    def update_battery(self, activity: RobotActivity) -> None:
        """Linear drain with activity load and cycle wear, accelerates below 20% (Li-ion cliff)."""
        activity_load = RobotBatteryConsumption[activity.name].value
        cycle_wear = self.elapsed_cycles * 0.0005
        drain = self.base_decay_rate + activity_load + cycle_wear
        if self.battery_percentage < 20:
            drain *= 1.5
        self.battery_percentage = max(0.0, self.battery_percentage - drain)

    def move(self):
        self.elapsed_cycles += 1
        self.activity = RobotActivity.MOVE
        self.update_battery(self.activity)

    def pick(self):
        self.elapsed_cycles += 1
        self.activity = RobotActivity.PICK
        self.update_battery(self.activity)

    def place(self):
        self.elapsed_cycles += 1
        self.activity = RobotActivity.PLACE
        self.update_battery(self.activity)

    def start(self):
        self.connectivity = RobotConnectivity.ONLINE

    def stop(self):
        self.connectivity = RobotConnectivity.OFFLINE
        self.activity = RobotActivity.IDLE
        
    def is_battery_low(self):
        return self.battery_percentage <= 15.0;

    def to_dict(self) -> dict:
        alerts = []
        if self.is_battery_low():
            alerts.append("low_battery")
        if self.connectivity == RobotConnectivity.OFFLINE:
            alerts.append("disconnected")
        return {
            "id": self.id,
            "name": self.name,
            "connectivity": self.connectivity.value,
            "activity": self.activity.value,
            "battery_percentage": round(self.battery_percentage, 2),
            "elapsed_cycles": self.elapsed_cycles,
            "alerts": alerts,
        }


def make_fleet() -> list[Robot]:
    fleet = [
        Robot(id="robot-a", name="Robot A"),
        Robot(id="robot-b", name="Robot B"),
        Robot(id="robot-c", name="Robot C"),
        Robot(id="robot-d", name="Robot D"),
        Robot(id="robot-e", name="Robot E"),
    ]
    for robot in fleet:
        robot.start()
    return fleet


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws/robots_telemetry")
async def get_robots_telemetry(websocket: WebSocket):
    await websocket.accept()

    fleet = make_fleet()

    # Stagger each robot's starting position so they're not all in sync
    cycle_indices = [random.randint(0, len(ACTIVITY_CYCLE) - 1) for _ in fleet]
    tick_counters = [random.randint(1, ACTIVITY_CYCLE[cycle_indices[i]][1]) for i, _ in enumerate(fleet)]

    try:
        while True:
            for i, robot in enumerate(fleet):
                if robot.is_battery_low():
                    robot.stop()
                    continue

                tick_counters[i] -= 1
                if tick_counters[i] <= 0:
                    cycle_indices[i] = (cycle_indices[i] + 1) % len(ACTIVITY_CYCLE)
                    _, duration = ACTIVITY_CYCLE[cycle_indices[i]]
                    tick_counters[i] = duration

                activity = ACTIVITY_CYCLE[cycle_indices[i]][0]
                if activity == RobotActivity.MOVE:
                    robot.move()
                elif activity == RobotActivity.PICK:
                    robot.pick()
                elif activity == RobotActivity.PLACE:
                    robot.place()

            await websocket.send_text(json.dumps([r.to_dict() for r in fleet]))
            await asyncio.sleep(1.0)

    except WebSocketDisconnect:
        pass
