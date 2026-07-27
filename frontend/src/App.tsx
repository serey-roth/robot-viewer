type RobotStatus = "online" | "offline";

type Robot = {
  id: string;
  name: string;
  battery: number;
  task: string;
  status: RobotStatus;
};

const MOCK_ROBOTS: Robot[] = [
  {
    id: "robot-a",
    name: "Robot A",
    battery: 85,
    task: "moving",
    status: "online",
  },
  {
    id: "robot-b",
    name: "Robot B",
    battery: 12,
    task: "idle",
    status: "online",
  },
  {
    id: "robot-c",
    name: "Robot C",
    battery: 60,
    task: "moving",
    status: "offline",
  },
  {
    id: "robot-d",
    name: "Robot D",
    battery: 40,
    task: "idle",
    status: "online",
  },
  {
    id: "robot-e",
    name: "Robot E",
    battery: 70,
    task: "picking",
    status: "online",
  },
];

function RobotCard({ robot }: { robot: Robot }) {
  return (
    <div
      className="flex flex-col gap-3 p-4 rounded-lg bg-gray-50 border border-gray-200 shadow-sm"
    >
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-2">
          <span
            className={`w-4 h-4 border-2 border-gray-200 rounded-full ${robot.status === "online" ? "bg-green-500" : "bg-red-500"}`}
          />
          <span className="text-base font-semibold text-gray-900">
            {robot.name}
          </span>
        </div>
        <span className="text-xs text-gray-400">{robot.status}</span>
      </div>
      <div className="flex flex-col gap-2 text-sm">
        <p>
          <span className="text-gray-500">
            {robot.task === "idle" ? "No task" : "Task"}
          </span>
          {robot.task !== "idle" && (
            <>
              <span className="mx-1.5 text-gray-300">·</span>
              <span className="text-gray-800">{robot.task}</span>
            </>
          )}
        </p>
        <div className="flex items-center gap-2">
          <div className="flex-1 h-1.5 bg-gray-200 rounded-full">
            <div
              className={`h-1.5 rounded-full bg-blue-400`}
              style={{ width: `${robot.battery}%` }}
            />
          </div>
          <span className="text-xs text-gray-500 w-8 text-right">
            {robot.battery}%
          </span>
        </div>
      </div>
    </div>
  )
}
function App() {
  const robots = MOCK_ROBOTS;

  return (
    <div className="w-screen min-h-screen p-8">
      <div className="block mx-auto sm:max-w-3xl">
        <div className="grid grid-cols-2 gap-3">
          {robots.map((robot) => (
            <RobotCard key={robot.id} robot={robot} />
          ))}
        </div>
      </div>
    </div>
  );
}

export default App;
