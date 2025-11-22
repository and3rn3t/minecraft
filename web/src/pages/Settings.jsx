import { useState } from 'react'

const Settings = () => {
  const [apiKey, setApiKey] = useState(localStorage.getItem('api_key') || '')

  const handleSaveApiKey = () => {
    if (apiKey) {
      localStorage.setItem('api_key', apiKey)
      alert('API key saved!')
    } else {
      localStorage.removeItem('api_key')
      alert('API key removed!')
    }
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-8">Settings</h1>

      <div className="bg-gray-800 rounded-lg p-6 max-w-2xl">
        <h2 className="text-xl font-semibold mb-4">API Configuration</h2>

        <div className="mb-4">
          <label className="block text-sm font-medium mb-2">
            API Key
          </label>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="Enter your API key"
            className="w-full bg-gray-700 text-white px-4 py-2 rounded border border-gray-600 focus:outline-none focus:border-primary-500"
          />
          <p className="text-sm text-gray-400 mt-2">
            Get your API key by running: ./scripts/api-key-manager.sh create
          </p>
        </div>

        <button
          onClick={handleSaveApiKey}
          className="px-4 py-2 bg-primary-600 hover:bg-primary-700 rounded transition-colors"
        >
          Save API Key
        </button>
      </div>
    </div>
  )
}

export default Settings

