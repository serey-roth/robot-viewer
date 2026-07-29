import { useEffect, useRef, useState } from "react"
import * as THREE from "three"
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js"
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js"
import URDFLoader from "urdf-loader"

type JointState = { pos: number; vel: number }
type RobotData = Record<string, JointState>

function RobotViewer({ joints }: { joints: Record<string, number> }) {
  const mountRef = useRef<HTMLDivElement>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const robotRef = useRef<any>(null)

  useEffect(() => {
    const el = mountRef.current!
    const w = el.clientWidth
    const h = el.clientHeight

    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(w, h)
    renderer.setPixelRatio(window.devicePixelRatio)
    renderer.shadowMap.enabled = true
    el.appendChild(renderer.domElement)

    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0xf8f9fa)

    const camera = new THREE.PerspectiveCamera(45, w / h, 0.01, 100)
    camera.position.set(2, 1.5, 2)

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.target.set(0, 0.8, 0)
    controls.update()

    scene.add(new THREE.AmbientLight(0xffffff, 0.6))
    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8)
    dirLight.position.set(2, 4, 2)
    scene.add(dirLight)

    const grid = new THREE.GridHelper(4, 20, 0xdddddd, 0xeeeeee)
    scene.add(grid)

    const manager = new THREE.LoadingManager()
    const gltfLoader = new GLTFLoader(manager)

    const loader = new URDFLoader(manager)
    loader.loadMeshCb = (path, _manager, _material, done) => {
      gltfLoader.load(
        path,
        (gltf) => done(gltf.scene),
        undefined,
        (err) => { console.error("mesh load error", path, err); done(new THREE.Object3D(), err as Error) },
      )
    }
    loader.load("/robots/humanoid/vega_1/vega_1_f5d6.urdf", (robot) => {
      robot.rotation.x = -Math.PI / 2
      scene.add(robot)
      robotRef.current = robot
    })

    let animId: number
    const animate = () => {
      animId = requestAnimationFrame(animate)
      controls.update()
      renderer.render(scene, camera)
    }
    animate()

    const onResize = () => {
      const w = el.clientWidth
      const h = el.clientHeight
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      renderer.setSize(w, h)
    }
    window.addEventListener("resize", onResize)

    return () => {
      cancelAnimationFrame(animId)
      window.removeEventListener("resize", onResize)
      renderer.dispose()
      el.removeChild(renderer.domElement)
    }
  }, [])

  useEffect(() => {
    const robot = robotRef.current
    if (!robot) return
    for (const [name, angle] of Object.entries(joints)) {
      robot.setJointValue(name, angle)
    }
  }, [joints])

  return <div ref={mountRef} className="w-full h-full" />
}

function useRobot() {
  const [joints, setJoints] = useState<Record<string, number>>({})
  const [status, setStatus] = useState<"connecting" | "connected" | "disconnected">("connecting")
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws/robot")
    ws.addEventListener("open", () => setStatus("connected"))
    ws.addEventListener("close", () => setStatus("disconnected"))
    ws.addEventListener("message", (e) => {
      const data: RobotData = JSON.parse(e.data)
      const next: Record<string, number> = {}
      for (const [k, v] of Object.entries(data)) {
        next[k] = v.pos
      }
      setJoints(next)
    })
    wsRef.current = ws
    return () => ws.close()
  }, [])

  function dispatchAction(action: string, payload?: Record<string, unknown>) {
    wsRef.current?.send(JSON.stringify({ action, ...payload }))
  }

  return { joints, status, dispatchAction }
}

export default function App() {
  const { joints, status, dispatchAction } = useRobot()

  const isRobotEnabled = status === "connected"

  return (
    <div className="w-screen h-screen flex flex-col bg-white">
      <header className="flex items-center justify-between px-5 py-3 border-b border-gray-100 shrink-0">
        <h1 className="text-sm font-semibold text-gray-900 tracking-tight">Dexmate Robot Control</h1>
        <div className="flex items-center gap-1.5">
          <span className={`w-2 h-2 rounded-full ${status === "connected" ? "bg-green-400" : "bg-gray-300"}`} />
          <span className="text-xs text-gray-400 capitalize">{status}</span>
        </div>
      </header>
      <div className="flex flex-1 overflow-hidden relative">
        <div className="flex-1">
          <RobotViewer joints={joints} />
        </div>
        <aside className="w-64 shrink-0 border-l border-gray-100 flex flex-col overflow-y-auto">
          <div className="p-4 flex flex-col gap-2">
            <div className="flex flex-col gap-2">
              <p className="text-xs font-semibold uppercase tracking-widest text-gray-400">Hands</p>
              <div className="flex gap-2 items-center">
                <button disabled={!isRobotEnabled} className="flex-1 text-sm font-medium px-3 py-1.5 rounded-lg transition-colors cursor-pointer select-none bg-gray-100 hover:bg-gray-200 text-gray-800 disabled:opacity-50" onClick={() => dispatchAction("open_left_hand")}>Open L</button>
                <button disabled={!isRobotEnabled} className="flex-1 text-sm font-medium px-3 py-1.5 rounded-lg transition-colors cursor-pointer select-none bg-gray-100 hover:bg-gray-200 text-gray-800 disabled:opacity-50" onClick={() => dispatchAction("open_right_hand")}>Open R</button>
              </div>
              <div className="flex gap-2">
                <button disabled={!isRobotEnabled} className="flex-1 text-sm font-medium px-3 py-1.5 rounded-lg transition-colors cursor-pointer select-none bg-gray-100 hover:bg-gray-200 text-gray-800 disabled:opacity-50" onClick={() => dispatchAction("close_left_hand")}>Close L</button>
                <button disabled={!isRobotEnabled} className="flex-1 text-sm font-medium px-3 py-1.5 rounded-lg transition-colors cursor-pointer select-none bg-gray-100 hover:bg-gray-200 text-gray-800 disabled:opacity-50" onClick={() => dispatchAction("close_right_hand")}>Close R</button>
              </div>
              <div className="flex gap-2">
                <button disabled={!isRobotEnabled} className="flex-1 text-sm font-medium px-3 py-1.5 rounded-lg transition-colors cursor-pointer select-none bg-gray-100 hover:bg-gray-200 text-gray-800 disabled:opacity-50" onClick={() => dispatchAction("open_both_hands")}>Open Both</button>
              </div> 
              <div className="flex gap-2">
                <button disabled={!isRobotEnabled} className="flex-1 text-sm font-medium px-3 py-1.5 rounded-lg transition-colors cursor-pointer select-none bg-gray-100 hover:bg-gray-200 text-gray-800 disabled:opacity-50" onClick={() => dispatchAction("close_both_hands")}>Close Both</button>
              </div>
            </div>

            <div className="bg-gray-50 w-full h-0.5 space-y-1"/>

            <div className="flex flex-col gap-2">
              <p className="text-xs font-semibold uppercase tracking-widest text-gray-400">Arms</p>
              <div className="flex gap-2 items-center">
                <button disabled={!isRobotEnabled} className="flex-1 text-sm font-medium px-3 py-1.5 rounded-lg transition-colors cursor-pointer select-none bg-gray-100 hover:bg-gray-200 text-gray-800 disabled:opacity-50" onClick={() => dispatchAction("move_arm", { side: "left" })}>Move L</button>
                <button disabled={!isRobotEnabled} className="flex-1 text-sm font-medium px-3 py-1.5 rounded-lg transition-colors cursor-pointer select-none bg-gray-100 hover:bg-gray-200 text-gray-800 disabled:opacity-50" onClick={() => dispatchAction("move_arm", { side: "right" })}>Move R</button>
              </div>
            </div>

            <div className="bg-gray-50 w-full h-0.5 space-y-1"/>

            <div className="flex flex-col gap-2">
              <p className="text-xs font-semibold uppercase tracking-widest text-gray-400">Torso</p>
              <div className="flex gap-2 items-center">
                <button disabled={!isRobotEnabled} className="flex-1 text-sm font-medium px-3 py-1.5 rounded-lg transition-colors cursor-pointer select-none bg-gray-100 hover:bg-gray-200 text-gray-800 disabled:opacity-50" onClick={() => dispatchAction("move_torso")}>Move</button>
              </div>
            </div>

            <div className="bg-gray-50 w-full h-0.5 space-y-1"/>

            <div className="flex flex-col gap-2">
              <p className="text-xs font-semibold uppercase tracking-widest text-gray-400">Head</p>
              <div className="flex gap-2 items-center">
                <button disabled={!isRobotEnabled} className="flex-1 text-sm font-medium px-3 py-1.5 rounded-lg transition-colors cursor-pointer select-none bg-gray-100 hover:bg-gray-200 text-gray-800 disabled:opacity-50" onClick={() => dispatchAction("move_head")}>Move</button>
              </div>
            </div>

            <div className="bg-gray-50 w-full h-0.5 space-y-1"/>

            <div className="flex flex-col gap-2">
              <p className="text-xs font-semibold uppercase tracking-widest text-gray-400">Chassis</p>
              <div className="flex gap-2 items-center">
                <button disabled={!isRobotEnabled} className="flex-1 text-sm font-medium px-3 py-1.5 rounded-lg transition-colors cursor-pointer select-none bg-gray-100 hover:bg-gray-200 text-gray-800 disabled:opacity-50" onClick={() => dispatchAction("move_chassis")}>Move Wheels</button>
              </div>
            </div>
          </div>
        </aside>

        {status === "connecting" && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/60 backdrop-blur-sm">
            <div className="flex flex-col items-center gap-3 px-8 py-6 bg-white rounded-2xl shadow-lg">
              <div className="w-7 h-7 rounded-full border-2 border-gray-200 border-t-gray-700 animate-spin" />
              <span className="text-sm text-gray-500 tracking-tight">Setting up robot…</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
