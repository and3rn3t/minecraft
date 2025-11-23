import { useEffect, useState } from 'react';
import { api } from '../services/api';

const ApiKeys = () => {
  const [keys, setKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [newKeyDescription, setNewKeyDescription] = useState('');
  const [newKeyValue, setNewKeyValue] = useState(null);
  const [toggling, setToggling] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    loadKeys();
  }, []);

  // Clear messages after 5 seconds
  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => setSuccess(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [success]);

  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [error]);

  const loadKeys = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.listApiKeys();
      setKeys(data.keys || []);
    } catch (err) {
      setError('Failed to load API keys');
      console.error('Failed to load API keys:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateKey = async e => {
    e.preventDefault();
    if (!newKeyName.trim()) {
      setError('Key name is required');
      return;
    }

    setCreating(true);
    setError(null);
    setSuccess(null);

    try {
      const result = await api.createApiKey(newKeyName.trim(), newKeyDescription.trim());
      setNewKeyValue(result.key);
      setSuccess(result.message || 'API key created successfully!');
      setNewKeyName('');
      setNewKeyDescription('');
      // Reload keys after creation
      setTimeout(loadKeys, 1000);
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Failed to create API key');
      console.error('Failed to create API key:', err);
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async keyId => {
    if (
      !window.confirm(
        `Are you sure you want to delete this API key?\n\nThis action cannot be undone.`
      )
    ) {
      return;
    }

    setDeleting(keyId);
    setError(null);
    setSuccess(null);

    try {
      const result = await api.deleteApiKey(keyId);
      setSuccess(result.message || 'API key deleted successfully');
      // Reload keys after delete
      loadKeys();
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Failed to delete API key');
      console.error('Failed to delete API key:', err);
    } finally {
      setDeleting(null);
    }
  };

  const handleToggle = async (keyId, enabled) => {
    setToggling(keyId);
    setError(null);
    setSuccess(null);

    try {
      const result = enabled ? await api.disableApiKey(keyId) : await api.enableApiKey(keyId);
      setSuccess(result.message || `API key ${enabled ? 'disabled' : 'enabled'} successfully`);
      // Reload keys after toggle
      loadKeys();
    } catch (err) {
      setError(
        err.response?.data?.error ||
          err.message ||
          `Failed to ${enabled ? 'disable' : 'enable'} API key`
      );
      console.error('Failed to toggle API key:', err);
    } finally {
      setToggling(null);
    }
  };

  const formatDate = dateString => {
    if (!dateString) return 'Unknown';
    try {
      const date = new Date(dateString);
      return date.toLocaleString();
    } catch {
      return dateString;
    }
  };

  const copyToClipboard = text => {
    navigator.clipboard.writeText(text).then(
      () => {
        setSuccess('API key copied to clipboard!');
      },
      () => {
        setError('Failed to copy to clipboard');
      }
    );
  };

  const closeCreateForm = () => {
    setShowCreateForm(false);
    setNewKeyName('');
    setNewKeyDescription('');
    setNewKeyValue(null);
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">API Keys</h1>
        <button
          onClick={() => setShowCreateForm(true)}
          className="px-4 py-2 bg-primary-600 hover:bg-primary-700 rounded transition-colors flex items-center gap-2"
        >
          <span>🔑</span>
          Create API Key
        </button>
      </div>

      {/* Error/Success messages */}
      {error && (
        <div className="bg-red-900/50 border border-red-700 rounded p-4 mb-6 text-red-300">
          {error}
        </div>
      )}

      {success && (
        <div className="bg-green-900/50 border border-green-700 rounded p-4 mb-6 text-green-300">
          {success}
        </div>
      )}

      {/* New Key Display Modal */}
      {newKeyValue && (
        <div className="bg-yellow-900/50 border-2 border-yellow-600 rounded p-6 mb-6">
          <h3 className="text-xl font-bold mb-4 text-yellow-300">⚠️ New API Key Created</h3>
          <p className="text-yellow-200 mb-4">
            <strong>Important:</strong> Save this API key securely. It will not be shown again.
          </p>
          <div className="bg-gray-900 rounded p-4 mb-4">
            <div className="flex items-center justify-between">
              <code className="text-lg font-mono text-white break-all">{newKeyValue}</code>
              <button
                onClick={() => copyToClipboard(newKeyValue)}
                className="ml-4 px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded text-sm whitespace-nowrap"
              >
                Copy
              </button>
            </div>
          </div>
          <button
            onClick={closeCreateForm}
            className="px-4 py-2 bg-primary-600 hover:bg-primary-700 rounded transition-colors"
          >
            I&apos;ve Saved the Key
          </button>
        </div>
      )}

      {/* Create Form Modal */}
      {showCreateForm && !newKeyValue && (
        <div className="bg-gray-800 rounded-lg p-6 mb-6 border border-gray-700">
          <h2 className="text-2xl font-semibold mb-4">Create New API Key</h2>
          <form onSubmit={handleCreateKey} className="space-y-4">
            <div>
              <label htmlFor="key-name" className="block text-sm font-medium mb-2">
                Key Name <span className="text-red-400">*</span>
              </label>
              <input
                id="key-name"
                type="text"
                value={newKeyName}
                onChange={e => setNewKeyName(e.target.value)}
                required
                className="w-full bg-gray-700 text-white px-4 py-2 rounded border border-gray-600 focus:outline-none focus:border-primary-500"
                placeholder="e.g., Webhook Integration"
              />
            </div>
            <div>
              <label htmlFor="key-description" className="block text-sm font-medium mb-2">
                Description (optional)
              </label>
              <textarea
                id="key-description"
                value={newKeyDescription}
                onChange={e => setNewKeyDescription(e.target.value)}
                rows={3}
                className="w-full bg-gray-700 text-white px-4 py-2 rounded border border-gray-600 focus:outline-none focus:border-primary-500"
                placeholder="Describe what this API key will be used for"
              />
            </div>
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={creating}
                className="px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded transition-colors"
              >
                {creating ? 'Creating...' : 'Create Key'}
              </button>
              <button
                type="button"
                onClick={closeCreateForm}
                disabled={creating}
                className="px-4 py-2 bg-gray-600 hover:bg-gray-700 disabled:bg-gray-500 disabled:cursor-not-allowed rounded transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* API Keys Table */}
      <div className="bg-gray-800 rounded-lg p-6">
        {loading ? (
          <div className="text-center py-8">Loading API keys...</div>
        ) : keys.length === 0 ? (
          <div className="text-gray-400 text-center py-8">
            <p className="text-lg mb-2">No API keys found</p>
            <p className="text-sm">Create an API key to get started</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left py-3 px-4">Name</th>
                  <th className="text-left py-3 px-4">Key ID</th>
                  <th className="text-left py-3 px-4">Description</th>
                  <th className="text-left py-3 px-4">Status</th>
                  <th className="text-left py-3 px-4">Created</th>
                  <th className="text-left py-3 px-4">Actions</th>
                </tr>
              </thead>
              <tbody>
                {keys.map((key, index) => (
                  <tr
                    key={key.id || `key-${index}`}
                    className="border-b border-gray-700 hover:bg-gray-700 transition-colors"
                  >
                    <td className="py-3 px-4 font-medium">{key.name}</td>
                    <td className="py-3 px-4">
                      <code className="text-sm font-mono text-gray-300">{key.id}</code>
                    </td>
                    <td className="py-3 px-4 text-gray-400 text-sm">
                      {key.description || <span className="italic">No description</span>}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${
                          key.enabled
                            ? 'bg-green-900/50 text-green-300'
                            : 'bg-red-900/50 text-red-300'
                        }`}
                      >
                        {key.enabled ? '✓ Enabled' : '✗ Disabled'}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-gray-400 text-sm">{formatDate(key.created)}</td>
                    <td className="py-3 px-4">
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleToggle(key.id, key.enabled)}
                          disabled={toggling === key.id || deleting === key.id}
                          className={`px-3 py-1 rounded text-sm transition-colors disabled:bg-gray-600 disabled:cursor-not-allowed ${
                            key.enabled
                              ? 'bg-yellow-600 hover:bg-yellow-700'
                              : 'bg-green-600 hover:bg-green-700'
                          }`}
                        >
                          {toggling === key.id ? '...' : key.enabled ? 'Disable' : 'Enable'}
                        </button>
                        <button
                          onClick={() => handleDelete(key.id)}
                          disabled={toggling === key.id || deleting === key.id}
                          className="px-3 py-1 bg-red-600 hover:bg-red-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded text-sm transition-colors"
                        >
                          {deleting === key.id ? 'Deleting...' : 'Delete'}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Info */}
      {keys.length > 0 && (
        <div className="mt-4 bg-blue-900/30 border border-blue-700 rounded p-3 text-blue-300 text-sm">
          <strong>Info:</strong> {keys.length} API key{keys.length !== 1 ? 's' : ''} available. API
          keys allow programmatic access to the server. Keep them secure and rotate them regularly.
        </div>
      )}
    </div>
  );
};

export default ApiKeys;
