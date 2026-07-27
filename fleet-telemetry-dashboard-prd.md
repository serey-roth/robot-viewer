# PRD: Fleet Telemetry Dashboard

## 1. Problem

Operators managing a fleet of physical robots need to answer, at a glance:

- Which robots are online and healthy?
- Which need attention right now (low battery, sensor fault, disconnected)?
- What is a given robot doing, and how is it performing over time?

Raw telemetry (battery %, joint torque, force/torque readings, task state) is not directly usable under time pressure. The dashboard compresses that stream into fast, correct decisions.

---

## 2. Goals

- Real-time, multi-robot monitoring UI in React + TypeScript
- Backend schema matches Dexmate's real `dexcontrol` structure, not an invented one
- Honest boundary between what is real (schema, joint structure) and what is simulated (values, no hardware)

---

## 3. Non-Goals

- No auth, multi-tenancy, or persistence layer
- No claim of live hardware or private API access
- No ROS bridge or real sensor drivers
- No full 36-DOF fidelity in any 3D visualization

---

## 4. Scope

### 4.1 Fleet Overview (must-have)

- Grid of 4–6 simulated robots
- Per-robot card: name/ID, connectivity, battery %, current task, health indicator
- Live updates via WebSocket — no page refresh
- Click-through to robot detail view

### 4.2 Robot Detail View (must-have)

- Live telemetry charts: battery over time, joint torque/force readings
- Current task + task history
- Alert states: low battery, sensor fault, disconnected

### 4.3 Mock Telemetry Backend

- Python + FastAPI with WebSocket streaming
- Schema mirrors `dexcontrol` (verified via `pip install dexcontrol`):
  - Component-based: `Arm`, `Chassis`, `Hand`, `Head`, `Torso`, and sensor modules (camera/IMU/lidar/ultrasonic); internally Zenoh pub/sub + protobuf
  - **Battery:** `percentage`, `temperature`, `current`, `voltage`, `power` (= current × voltage)
  - **Joint state:** `pos` (rad, or m for prismatic), `vel` — per-joint via `get_joint_pos_dict()` / `get_joint_vel_dict()`
  - **Arm wrench:** 6-axis `wrench` (force + torque) + two wrist button states
- Joint names/hierarchy sourced from `dexmate-urdf` (real, not invented)
- Values simulated via bounded random walk per field — see Section 6
- No live hardware or private API access; `dexcontrol` only talks to physical units over Zenoh

### 4.4 Out of Scope: Camera/Video

Dexmate's `rtc_stream_viewer.html` example shows camera feeds use WebRTC for video transport (WebSocket only for SDP signaling) — a different problem from telemetry streaming. Excluded to protect the 2-day budget. Natural Phase 2.

### 4.5 3D Joint Visualizer (stretch)

- Simplified articulated model — joint subset, not full 36-DOF
- Live joint angles from the mocked stream
- Attempted only after 4.1–4.3 are complete

### 4.6 Documentation

- README: clearly states what is real (schema, joint structure) vs. simulated (values, no hardware)
- Optional: 30–60s demo recording

---

## 5. Stack

| Layer | Choice |
|---|---|
| Frontend | React + TypeScript, Vite |
| Charts | Recharts or ECharts |
| Realtime | Native WebSocket API |
| Styling | Tailwind CSS |
| Backend | Python + FastAPI |
| State schema | Mirrors verified `dexcontrol` fields (battery, joint pos/vel, wrench) |
| Joint reference | `dexmate-urdf` (pip) |
| 3D (stretch) | Three.js |

---

## 6. Data Simulation Strategy

- **Bounded random walk** per field — each value drifts from its previous value within a clamped, physically plausible range; not uniform random per tick
- **Battery:** slow monotonic decrease + small noise; optional charge cycle
- **Joint positions:** smooth oscillation (sine + noise) within real joint limits from `dexmate-urdf`
- **Wrench:** near-zero at idle, spikes correlated to task state
- **Robot fixtures** — each simulated robot has a distinct scenario to exercise every UI state:
  - Robot A: healthy, normal operation
  - Robot B: low battery, draining
  - Robot C: intermittent connectivity
  - Robot D: idle / charging
  - Robot E (optional): sensor fault
- **Task state machine:** idle → moving → picking → placing → idle, with plausible durations; feeds task history
- **Non-uniform tick rates:** joints update faster than battery, matching real telemetry patterns
- **Seeded initial state** per robot for reproducible demo behavior

---

## 7. Timeline

### Day 1
- Scaffold frontend and backend projects
- Mock server: state schema, per-field random walk, multi-robot WebSocket broadcast
- Fleet overview: static layout → wired to live data
- Validate end-to-end data flow early (highest-risk integration point)

### Day 2
- Robot detail view + live telemetry charts
- Alert states, connection-loss handling, UI polish
- Stretch: Three.js joint visualizer (only if ahead of schedule)
- README + optional demo recording

---

## 8. Risks

| Risk | Mitigation |
|---|---|
| Three.js eats the time budget | Stretch only — attempted last |
| Mock data reads as fake/static | Bounded random walk + async per-robot updates |
| Scope creep into a second feature | Single feature enforced; backend kept thin |
| Overclaiming hardware/API access | README states simulation boundary explicitly |
