import { useState, useEffect } from 'react'
import { api } from '../services/api'

const Backups = () => {
  const [backups, setBackups] = useState([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    loadBackups()
  }, [])

  const loadBackups = async () => {
    try {
      const data = await api.listBackups()
      setBackups(data.backups || [])
    } catch (error) {
      console.error('Failed to load backups:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateBackup = async () => {
    setCreating(true)
    try {
      await api.createBackup()
      setTimeout(loadBackups, 2000) // Reload after creation
      alert('Backup created successfully!')
    } catch (error) {
      console.error('Failed to create backup:', error)
      alert(`Failed to create backup: ${error.message}`)
    } finally {
      setCreating(false)
    }
  }

  const formatSize = (bytes) => {
    if (!bytes) return 'Unknown'
    const mb = bytes / (1024 * 1024)
    return `${mb.toFixed(2)} MB`
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown'
    return new Date(dateString).toLocaleString()
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">Backups</h1>
        <button
          onClick={handleCreateBackup}
          disabled={creating}
          className="px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded transition-colors"
        >
          {creating ? 'Creating...' : 'Create Backup'}
        </button>
      </div>

      <div className="bg-gray-800 rounded-lg p-6">
        {loading ? (
          <div className="text-center py-8">Loading backups...</div>
        ) : backups.length === 0 ? (
          <div className="text-gray-400 text-center py-8">No backups found</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left py-3 px-4">Name</th>
                  <th className="text-left py-3 px-4">Size</th>
                  <th className="text-left py-3 px-4">Created</th>
                  <th className="text-left py-3 px-4">Actions</th>
                </tr>
              </thead>
              <tbody>
                {backups.map((backup, index) => (
                  <tr key={index} className="border-b border-gray-700 hover:bg-gray-700">
                    <td className="py-3 px-4">{backup.name}</td>
                    <td className="py-3 px-4">{formatSize(backup.size)}</td>
                    <td className="py-3 px-4">{formatDate(backup.created)}</td>
                    <td className="py-3 px-4">
                      <button className="px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-sm mr-2">
                        Restore
                      </button>
                      <button className="px-3 py-1 bg-red-600 hover:bg-red-700 rounded text-sm">
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

export default Backups

