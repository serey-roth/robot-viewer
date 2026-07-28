import { useEffect, useState } from "react"

type RobotConnectivity = "online" | "offline"
type RobotActivity = "idle" | "moving" | "picking" | "placing"

type Robot = {
  id: string
  name: string
  battery_percentage: number
  alerts: string[]
  activity: RobotActivity
  connectivity: RobotConnectivity
}

type WsStatus = "connecting" | "connected" | "disconnected"

function batteryColor(pct: number) {
  if (pct < 20) return "bg-red-500"
  if (pct < 40) return "bg-yellow-400"
  return "bg-green-500"
}

function RobotCardSkeleton() {
  return (
    <div className="flex flex-col gap-3 p-4 rounded-lg bg-gray-50 border border-gray-200 shadow-sm animate-pulse">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full bg-gray-200" />
          <div className="h-4 w-24 rounded bg-gray-200" />
        </div>
        <div className="h-3 w-12 rounded bg-gray-200" />
      </div>
      <div className="flex flex-col gap-2">
        <div className="h-3 w-32 rounded bg-gray-200" />
        <div className="flex items-center gap-2">
          <div className="flex-1 h-1.5 rounded-full bg-gray-200" />
          <div className="h-3 w-8 rounded bg-gray-200" />
        </div>
      </div>
    </div>
  )
}

function RobotCard({ robot }: { robot: Robot }) {
  return (
    <div className="flex flex-col gap-3 p-4 rounded-lg bg-gray-50 border border-gray-200 shadow-sm">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-2">
          <span className={`w-4 h-4 border-2 border-gray-200 rounded-full ${robot.connectivity === "online" ? "bg-green-500" : "bg-red-500"}`} />
          <span className="text-base font-semibold text-gray-900">{robot.name}</span>
        </div>
        <span className="text-xs text-gray-400">{robot.connectivity}</span>
      </div>
      <div className="flex flex-col gap-2 text-sm">
        <p>
          <span className="text-gray-500">{robot.activity === "idle" ? "No activity" : "Activity"}</span>
          {robot.activity !== "idle" && (
            <>
              <span className="mx-1.5 text-gray-300">·</span>
              <span className="text-gray-800">{robot.activity}</span>
            </>
          )}
        </p>
        <div className="flex items-center gap-2">
          <div className="flex-1 h-1.5 bg-gray-200 rounded-full">
            <div
              className={`h-1.5 rounded-full ${batteryColor(robot.battery_percentage)}`}
              style={{ width: `${robot.battery_percentage}%` }}
            />
          </div>
          <span className="text-xs text-gray-500 w-8 text-right">
            {robot.battery_percentage.toFixed(0)}%
          </span>
        </div>
        {robot.alerts.length > 0 && (
          <div className="flex flex-wrap gap-1 pt-1">
            {robot.alerts.map((alert) => (
              <span key={alert} className="text-xs px-2 py-px rounded-full bg-red-100 text-red-600">
                {alert.replace("_", " ")}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function useTelemetry() {
  const [robots, setRobots] = useState<Robot[]>([])
  const [wsStatus, setWsStatus] = useState<WsStatus>("connecting")

  useEffect(() => {
    const websocket = new WebSocket("ws://localhost:8000/ws/robots_telemetry")

    websocket.addEventListener("open", () => setWsStatus("connected"))
    websocket.addEventListener("message", (e) => setRobots(JSON.parse(e.data)))
    websocket.addEventListener("close", () => setWsStatus("disconnected"))

    return () => websocket.close()
  }, [])

  return { robots, wsStatus }
}

const SKELETON_COUNT = 5

function App() {
  const { robots, wsStatus } = useTelemetry()
  const isLoading = robots.length === 0

  return (
    <div className="w-screen min-h-screen p-8">
      <div className="block mx-auto sm:max-w-3xl space-y-4">

        {wsStatus === "disconnected" && (
          <div className="text-sm text-center text-red-500 bg-red-50 border border-red-200 rounded-lg px-4 py-2">
            Connection lost — attempting to reconnect…
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          {isLoading
            ? Array.from({ length: SKELETON_COUNT }).map((_, i) => (
                <RobotCardSkeleton key={i} />
              ))
            : robots.map((robot) => (
                <RobotCard key={robot.id} robot={robot} />
              ))}
        </div>

      </div>
    </div>
  )
}

export default App
