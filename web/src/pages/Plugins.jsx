import { useState, useEffect } from 'react'
import { api } from '../services/api'

const Plugins = () => {
  const [plugins, setPlugins] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadPlugins()
  }, [])

  const loadPlugins = async () => {
    try {
      const data = await api.listPlugins()
      setPlugins(data.plugins || [])
    } catch (error) {
      console.error('Failed to load plugins:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-8">Plugin Management</h1>

      <div className="bg-gray-800 rounded-lg p-6">
        {loading ? (
          <div className="text-center py-8">Loading plugins...</div>
        ) : plugins.length === 0 ? (
          <div className="text-gray-400 text-center py-8">No plugins installed</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {plugins.map((plugin) => (
              <div key={plugin} className="bg-gray-700 rounded p-4">
                <h3 className="text-lg font-semibold mb-2">{plugin}</h3>
                <div className="flex gap-2 mt-4">
                  <button className="flex-1 px-3 py-2 bg-green-600 hover:bg-green-700 rounded text-sm">
                    Enable
                  </button>
                  <button className="flex-1 px-3 py-2 bg-red-600 hover:bg-red-700 rounded text-sm">
                    Disable
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

export default Plugins

