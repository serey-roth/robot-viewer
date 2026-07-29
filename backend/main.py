import asyncio
import json
import os
import threading
from contextlib import asynccontextmanager

from dexcomm import ZenohConfig
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from zenoh_bridge import setup_zenoh_config
from robot_simulation import RobotSimulation
from robot_controller import RobotController


@asynccontextmanager
async def lifespan(_: FastAPI):
    robot_name = os.environ.setdefault("ROBOT_NAME", "vega_1")

    router_cfg, client_cfg = setup_zenoh_config()
    os.environ["ZENOH_CONFIG"] = str(client_cfg)

    sim = RobotSimulation(model_name=robot_name, config=ZenohConfig.from_file(router_cfg))

    sim_thread = threading.Thread(target=sim.start_simulation, daemon=True, name="sapien-sim")
    sim_thread.start()

    # Wait until the sim has published its first heartbeat before creating the
    # controller. This ensures the TCP route is warm and dexcontrol's heartbeat
    # monitor receives a message well within its 1-second window.
    sim._ready.wait(timeout=30.0)

    controller = RobotController(robot_name)

    app.state.robot_name = robot_name
    app.state.sim = sim
    app.state.controller = controller

    try:
        yield
    finally:
        controller.__exit__(None, None, None)
        sim.stop_simulation()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws/robot")
async def robot_session(websocket: WebSocket) -> None:
    await websocket.accept()

    sim: RobotSimulation = app.state.sim
    controller: RobotController = app.state.controller

    async def send_state() -> None:
        while True:
            await websocket.send_text(json.dumps(sim.state.to_dict()))
            await asyncio.sleep(1 / 30)

    async def receive_commands() -> None:
        while True:
            data = await websocket.receive_json()
            action = data.pop("action", None)
            if action is None:
                continue
            
            try:
                await asyncio.to_thread(controller.dispatch, action, **data)
            except Exception as e:
                await websocket.send_text(json.dumps({"error": str(e)}))
                
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(send_state())
            tg.create_task(receive_commands())
    except* (WebSocketDisconnect, asyncio.CancelledError):
        pass
    except* Exception as eg:
        for exc in eg.exceptions:
            print(f"WebSocket task failed: {exc!r}")