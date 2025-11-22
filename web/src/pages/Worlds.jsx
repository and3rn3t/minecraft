import { useState, useEffect } from 'react'
import { api } from '../services/api'

const Worlds = () => {
  const [worlds, setWorlds] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadWorlds()
  }, [])

  const loadWorlds = async () => {
    try {
      const data = await api.listWorlds()
      setWorlds(data.worlds || [])
    } catch (error) {
      console.error('Failed to load worlds:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-8">World Management</h1>

      <div className="bg-gray-800 rounded-lg p-6">
        {loading ? (
          <div className="text-center py-8">Loading worlds...</div>
        ) : worlds.length === 0 ? (
          <div className="text-gray-400 text-center py-8">No worlds found</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {worlds.map((world, index) => (
              <div key={index} className="bg-gray-700 rounded p-4">
                <h3 className="text-lg font-semibold mb-2">{world}</h3>
                <div className="flex gap-2 mt-4">
                  <button className="flex-1 px-3 py-2 bg-primary-600 hover:bg-primary-700 rounded text-sm">
                    Switch
                  </button>
                  <button className="flex-1 px-3 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm">
                    Backup
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default Worlds

