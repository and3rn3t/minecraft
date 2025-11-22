import { useState, useEffect, useRef } from 'react'
import { api } from '../services/api'

const Logs = () => {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [autoScroll, setAutoScroll] = useState(true)
  const [filter, setFilter] = useState('')
  const logEndRef = useRef(null)

  useEffect(() => {
    loadLogs()
    const interval = setInterval(loadLogs, 2000) // Update every 2 seconds
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (autoScroll && logEndRef.current && logEndRef.current.scrollIntoView) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs, autoScroll])

  const loadLogs = async () => {
    try {
      const data = await api.getLogs(200)
      setLogs(data.logs || [])
    } catch (error) {
      console.error('Failed to load logs:', error)
    } finally {
      setLoading(false)
    }
  }

  const filteredLogs = logs.filter((log) =>
    log.toLowerCase().includes(filter.toLowerCase())
  )

  return (
    <div>
      <h1 className="text-3xl font-bold mb-8">Server Logs</h1>

      {/* Controls */}
      <div className="bg-gray-800 rounded-lg p-4 mb-6 flex gap-4 items-center">
        <input
          type="text"
          placeholder="Filter logs..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="flex-1 bg-gray-700 text-white px-4 py-2 rounded border border-gray-600 focus:outline-none focus:border-primary-500"
        />
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={autoScroll}
            onChange={(e) => setAutoScroll(e.target.checked)}
            className="w-4 h-4"
          />
          <span>Auto-scroll</span>
        </label>
        <button
          onClick={loadLogs}
          className="px-4 py-2 bg-primary-600 hover:bg-primary-700 rounded transition-colors"
        >
          Refresh
        </button>
      </div>

      {/* Log Display */}
      <div className="bg-gray-800 rounded-lg p-4">
        {loading ? (
          <div className="text-center py-8">Loading logs...</div>
        ) : (
          <div className="font-mono text-sm overflow-auto max-h-[600px]">
            {filteredLogs.length === 0 ? (
              <div className="text-gray-400 text-center py-8">No logs found</div>
            ) : (
              filteredLogs.map((log, index) => (
                <div
                  key={index}
                  className={`py-1 px-2 hover:bg-gray-700 ${
                    log.includes('ERROR') || log.includes('WARN')
                      ? 'text-red-400'
                      : log.includes('INFO')
                      ? 'text-blue-400'
                      : 'text-gray-300'
                  }`}
                >
                  {log}
                </div>
              ))
            )}
            <div ref={logEndRef} />
          </div>
        )}
      </div>
    </div>
  )
}

export default Logs

