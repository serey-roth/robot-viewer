# Vega 1 Robot Viewer

Interactive 3D viewer for the Dexmate Vega 1 F5D6 humanoid robot. A physics simulation (SAPIEN) runs in-process and streams joint state over WebSocket to a React frontend, which renders a live URDF model and control panel for triggering actions.

Demo: [vimeo.com/1214035369](https://vimeo.com/1214035369?share=copy&fl=sv&fe=ci)

## Stack

- **Backend**: FastAPI + SAPIEN physics, `dexcontrol` robot API, Zenoh pub/sub
- **Frontend**: React + TypeScript, Three.js / URDF Loader, Tailwind CSS

## How it works

1. On startup, `RobotSimulation` loads the Vega 1 F5D6 URDF into SAPIEN and begins publishing joint states over Zenoh at ~30 Hz.
2. `RobotController` connects to the simulation via `dexcontrol` (same Zenoh transport as real hardware).
3. The FastAPI WebSocket endpoint (`/ws/robot`) bridges the browser: it streams joint state to the frontend to animate the 3D model, and dispatches control actions from the frontend to the controller.

## Running locally

### Backend

```bash
cd backend
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Actions

Actions are drawn from the basic `dexcontrol` usage examples and dispatched over WebSocket to `RobotController`:

| Action | Description |
| ------ | ----------- |
| `open_left_hand` / `open_right_hand` / `open_both_hands` | Open gripper(s) |
| `close_left_hand` / `close_right_hand` / `close_both_hands` | Close gripper(s) |
| `move_arm` | Run arm joint sequence (`side`: `"left"` or `"right"`) |
| `move_head` | Run head joint sequence |
| `move_torso` | Run torso pose sequence |
| `move_chassis` | Run chassis movement sequence (straight, sideways, turn) |
