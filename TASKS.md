# Tasks: Fleet Telemetry Dashboard

Tasks are ordered by the 2-day timeline. Complete them top to bottom. Stretch tasks are clearly marked.

---

## Day 1

### 1. Install backend dependencies

In `backend/`, activate your virtual environment and install:

```bash
source venv/bin/activate
pip install fastapi uvicorn websockets dexmate-urdf
pip freeze > requirements.txt
```

Run the server to confirm it starts:

```bash
uvicorn main:app --reload
```

---

### 2. Define the telemetry state schema

In `backend/main.py`, define Python dataclasses (or dicts) that mirror the `dexcontrol` structure:

- `BatteryState`: `percentage` (float), `temperature` (float), `voltage` (float), `current` (float), `power` (float, derived)
- `JointState`: `pos` (float, radians), `vel` (float)
- `WrenchState`: `force` (x, y, z floats), `torque` (x, y, z floats)
- `RobotState`: `id` (str), `name` (str), `connectivity` (`"online"` | `"offline"` | `"intermittent"`), `task` (str), `battery` (BatteryState), `joints` (dict of joint name → JointState), `wrench` (WrenchState), `alerts` (list of str)

Use real joint names from `dexmate-urdf`. Run `python -c "import dexmate_urdf; print(dir(dexmate_urdf))"` to explore the package and extract the joint name list.

---

### 3. Implement the bounded random walk simulator

In `backend/`, create `simulator.py`. For each robot, maintain its previous state and update it each tick:

- **Battery:** decrease `percentage` by 0.01–0.05 per tick with small noise; clamp to `[0, 100]`; `power = current * voltage`
- **Joints:** update each `pos` with `pos += sin(t) * 0.01 + random.gauss(0, 0.002)`; clamp to joint limits
- **Wrench:** near-zero at idle; spike force values when task is `"picking"` or `"placing"`
- **Task state machine:** cycle `idle → moving → picking → placing → idle`; each state lasts a random plausible duration (e.g. idle: 3–8s, moving: 2–5s, picking: 1–3s, placing: 1–2s)

Define 4–5 robot fixtures with seeded initial states:

| Robot | Scenario |
|---|---|
| `robot-a` | Healthy, full battery |
| `robot-b` | Low battery (starts at 12%, draining) |
| `robot-c` | Intermittent connectivity (randomly drops offline) |
| `robot-d` | Idle / charging (battery slowly increasing) |
| `robot-e` | Sensor fault (wrench readings spike erratically) |

---

### 4. Add a WebSocket endpoint that streams all robots

In `backend/main.py`, add a `/ws/telemetry` WebSocket endpoint:

- On connect, start a loop that calls the simulator, serializes all robot states to JSON, and sends the payload every **100ms** for joints and **1s** for battery (or send a combined packet every 100ms and let the frontend handle display rate)
- Handle client disconnect cleanly so the loop exits
- Test it manually with a WebSocket client (e.g. `websocat ws://localhost:8000/ws/telemetry`) before moving to the frontend

---

### 5. Build the Fleet Overview layout (static first)

In `frontend/src/`, create `components/FleetGrid.tsx` and `components/RobotCard.tsx`.

`RobotCard` should display:
- Robot name and ID
- Connectivity status dot (green / yellow / red)
- Battery % with a simple bar
- Current task label
- Health indicator (alerts summary)

Wire it with hardcoded mock data first — confirm the layout looks correct before connecting to the WebSocket.

---

### 6. Connect the Fleet Overview to the WebSocket

In `frontend/src/`, create `hooks/useTelemetry.ts`. This hook should:

- Open a `WebSocket` connection to `ws://localhost:8000/ws/telemetry` on mount
- Parse incoming JSON and update a `robots` state map keyed by robot ID
- Close the connection on unmount
- Expose `robots`, `connected` (bool), and `lastUpdated`

Import `useTelemetry` in `App.tsx` and pass `robots` down to `FleetGrid`.

---

### 7. Validate end-to-end data flow

With both servers running (`uvicorn` + `vite`), open the browser and confirm:

- All robot cards render with live-updating data
- Battery values are visibly changing
- Task labels cycle through states
- Connectivity status reflects robot fixtures (robot-c should flicker)
- No console errors

Fix any issues before moving to Day 2.

---

## Day 2

### 8. Build the Robot Detail View

Create `frontend/src/pages/RobotDetail.tsx` (or `components/RobotDetail.tsx`).

Add routing — install React Router if not already present:

```bash
npm install react-router-dom
```

- Route `/` → Fleet Overview
- Route `/robot/:id` → Robot Detail View

Make each `RobotCard` a link to `/robot/:id`.

---

### 9. Add live telemetry charts

Install your chart library:

```bash
npm install recharts        # or: npm install echarts echarts-for-react
```

In `RobotDetail.tsx`, add:

- **Battery chart:** line chart of `percentage` over the last 60 seconds; update every second
- **Joint torque chart:** line chart of 2–3 key joint `pos` values over the last 30 seconds; update every 100ms
- **Wrench chart:** bar or line chart of force x/y/z over time

Buffer incoming telemetry in the hook (keep a rolling window of the last N samples per robot) so charts always have history to render.

---

### 10. Implement alert states

In `RobotDetail.tsx` and `RobotCard.tsx`, render visible alerts when:

- `battery.percentage < 15` → show "Low Battery" warning
- `connectivity === "offline"` → show "Disconnected" banner; pause chart updates gracefully
- `connectivity === "intermittent"` → show "Unstable Connection" warning
- Any alert in `robot.alerts` → render them as a list with severity color coding

In the backend simulator, set `alerts` on the robot state when thresholds are crossed.

---

### 11. Handle connection loss on the frontend

In `useTelemetry.ts`:

- If the WebSocket closes unexpectedly, attempt reconnection with exponential backoff (start at 1s, cap at 10s)
- While disconnected, mark all robots as `"offline"` in state
- Show a global "Reconnecting…" banner in the UI

---

### 12. Polish the UI

- Make the layout responsive (fleet grid wraps on smaller screens)
- Add loading state for initial connection
- Ensure chart axes have proper labels and units (%, rad, N, Nm)
- Confirm robot-b and robot-e clearly look different from robot-a at a glance
- Clean up any console warnings

---

### 13. Write the README

Create `README.md` at the project root. Include:

- What this project is (1 paragraph)
- **What is real:** the `dexcontrol` schema, `dexmate-urdf` joint names/hierarchy
- **What is simulated:** all telemetry values, no hardware, no live API
- How to run locally (backend + frontend commands)
- Screenshot or GIF of the dashboard (add after recording)

---

## Stretch (only if Day 1–2 tasks are complete)

### 14. Add a 3D joint visualizer

Install Three.js:

```bash
npm install three @types/three
```

Create `components/JointVisualizer.tsx`:

- Render a simplified articulated arm model (3–5 joints, not full 36-DOF)
- Map live `pos` values from the telemetry stream to joint rotations
- Use `useFrame` or `requestAnimationFrame` to update smoothly
- Add it as a panel in `RobotDetail.tsx`

---

### 15. Record a demo

- Run both servers and open the dashboard
- Record a 30–60s screen capture showing: fleet overview live updates, clicking into a robot, charts updating, an alert state visible
- Add the recording or a GIF to the README
