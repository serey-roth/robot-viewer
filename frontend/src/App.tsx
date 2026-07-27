import { useEffect, useState } from 'react'

interface Data {
  message: string;
  status: string;
}

function App() {
  const [data, setData] = useState<Data | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      try {
        const response = await fetch('http://localhost:8000/api/data', {
          method: "GET"
        })
        
        if (!response.ok) {
          throw new Error("Something went wrong during fetch")
        }
  
        const data = await response.json();
        setData(data)
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Something went wrong during fetch")
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  return (
    <div className="p-8 font-sans">
      {loading && <p>Loading data...</p>}
      {data && !loading && (
        <div className="border border-gray-300 p-4 rounded-lg">
          <p>{data.message}</p>
        </div>
      )}
      {!data && !loading && <p>No data found.</p>}
      {error && <p className="text-red-500">{error}</p>}
    </div>
  )
}

export default App
