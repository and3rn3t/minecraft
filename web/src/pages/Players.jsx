import { useState, useEffect } from 'react'
import { api } from '../services/api'

const Players = () => {
  const [players, setPlayers] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadPlayers()
    const interval = setInterval(loadPlayers, 5000)
    return () => clearInterval(interval)
  }, [])

  const loadPlayers = async () => {
    try {
      const data = await api.getPlayers()
      setPlayers(data.players || [])
    } catch (error) {
      console.error('Failed to load players:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-8">Player Management</h1>

      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-semibold mb-4">
          Online Players ({players.length})
        </h2>
        {loading ? (
          <div className="text-center py-8">Loading...</div>
        ) : players.length === 0 ? (
          <div className="text-gray-400 text-center py-8">No players online</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {players.map((player, index) => (
              <div
                key={index}
                className="bg-gray-700 rounded p-4 flex items-center justify-between"
              >
                <span className="text-lg">{player}</span>
                <button className="px-3 py-1 bg-red-600 hover:bg-red-700 rounded text-sm">
                  Kick
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default Players

