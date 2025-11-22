import { useState, useEffect } from 'react'
import { api } from '../services/api'
import StatusCard from '../components/StatusCard'
import MetricsChart from '../components/MetricsChart'

const Dashboard = () => {
  const [status, setStatus] = useState(null)
  const [metrics, setMetrics] = useState(null)
  const [players, setPlayers] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 5000) // Update every 5 seconds
    return () => clearInterval(interval)
  }, [])

  const loadData = async () => {
    try {
      const [statusData, metricsData, playersData] = await Promise.all([
        api.getStatus(),
        api.getMetrics(),
        api.getPlayers(),
      ])
      setStatus(statusData)
      setMetrics(metricsData)
      setPlayers(playersData.players || [])
    } catch (error) {
      console.error('Failed to load dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleServerAction = async (action) => {
    try {
      if (action === 'start') {
        await api.startServer()
      } else if (action === 'stop') {
        await api.stopServer()
      } else if (action === 'restart') {
        await api.restartServer()
      }
      setTimeout(loadData, 2000) // Reload after action
    } catch (error) {
      console.error(`Failed to ${action} server:`, error)
      alert(`Failed to ${action} server: ${error.message}`)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-xl">Loading...</div>
      </div>
    )
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-8">Dashboard</h1>

      {/* Server Status */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <StatusCard
          title="Server Status"
          value={status?.running ? 'Online' : 'Offline'}
          status={status?.running ? 'success' : 'error'}
          icon="🟢"
        />
        <StatusCard
          title="Players Online"
          value={`${players.length} / 10`}
          status="info"
          icon="👥"
        />
        <StatusCard
          title="Uptime"
          value={status?.status || 'Unknown'}
          status="info"
          icon="⏱️"
        />
      </div>

      {/* Server Controls */}
      <div className="bg-gray-800 rounded-lg p-6 mb-8">
        <h2 className="text-xl font-semibold mb-4">Server Controls</h2>
        <div className="flex gap-4">
          <button
            onClick={() => handleServerAction('start')}
            disabled={status?.running}
            className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded transition-colors"
          >
            Start Server
          </button>
          <button
            onClick={() => handleServerAction('stop')}
            disabled={!status?.running}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded transition-colors"
          >
            Stop Server
          </button>
          <button
            onClick={() => handleServerAction('restart')}
            disabled={!status?.running}
            className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded transition-colors"
          >
            Restart Server
          </button>
        </div>
      </div>

      {/* Metrics */}
      {metrics && (
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Server Metrics</h2>
          <MetricsChart metrics={metrics} />
        </div>
      )}

      {/* Online Players */}
      {players.length > 0 && (
        <div className="bg-gray-800 rounded-lg p-6 mt-8">
          <h2 className="text-xl font-semibold mb-4">Online Players</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {players.map((player, index) => (
              <div key={index} className="bg-gray-700 rounded p-3 text-center">
                {player}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default Dashboard

