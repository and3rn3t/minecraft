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
        <h1 className="text-2xl font-minecraft text-minecraft-grass-light leading-tight">
          API KEYS
        </h1>
        <button
          onClick={() => setShowCreateForm(true)}
          className="btn-minecraft-primary text-[10px] flex items-center gap-2"
        >
          <span>🔑</span>
          CREATE API KEY
        </button>
      </div>

      {/* Error/Success messages */}
      {error && (
        <div className="bg-[#C62828] border-2 border-[#B71C1C] p-4 mb-6 text-white text-[10px] font-minecraft">
          {error}
        </div>
      )}

      {success && (
        <div className="bg-minecraft-grass-DEFAULT border-2 border-minecraft-grass-dark p-4 mb-6 text-white text-[10px] font-minecraft">
          {success}
        </div>
      )}

      {/* New Key Display Modal */}
      {newKeyValue && (
        <div className="bg-[#F57C00] border-2 border-[#E65100] p-6 mb-6 card-minecraft">
          <h3 className="text-sm font-minecraft mb-4 text-white leading-tight">
            ⚠️ NEW API KEY CREATED
          </h3>
          <p className="text-[10px] font-minecraft text-white mb-4">
            <strong>IMPORTANT:</strong> SAVE THIS API KEY SECURELY. IT WILL NOT BE SHOWN AGAIN.
          </p>
          <div className="bg-minecraft-background-dark border-2 border-[#5D4037] p-4 mb-4">
            <div className="flex items-center justify-between">
              <code className="text-xs font-minecraft text-white break-all">{newKeyValue}</code>
              <button
                onClick={() => copyToClipboard(newKeyValue)}
                className="ml-4 btn-minecraft text-[8px] whitespace-nowrap"
              >
                COPY
              </button>
            </div>
          </div>
          <button onClick={closeCreateForm} className="btn-minecraft-primary text-[10px]">
            I&apos;VE SAVED THE KEY
          </button>
        </div>
      )}

      {/* Create Form Modal */}
      {showCreateForm && !newKeyValue && (
        <div className="card-minecraft p-6 mb-6">
          <h2 className="text-sm font-minecraft text-minecraft-text-light mb-4 leading-tight">
            CREATE NEW API KEY
          </h2>
          <form onSubmit={handleCreateKey} className="space-y-4">
            <div>
              <label
                htmlFor="key-name"
                className="block text-[10px] font-minecraft text-minecraft-text-light mb-2"
              >
                KEY NAME <span className="text-[#C62828]">*</span>
              </label>
              <input
                id="key-name"
                type="text"
                value={newKeyName}
                onChange={e => setNewKeyName(e.target.value)}
                required
                className="input-minecraft w-full"
                placeholder="e.g., Webhook Integration"
              />
            </div>
            <div>
              <label
                htmlFor="key-description"
                className="block text-[10px] font-minecraft text-minecraft-text-light mb-2"
              >
                DESCRIPTION (OPTIONAL)
              </label>
              <textarea
                id="key-description"
                value={newKeyDescription}
                onChange={e => setNewKeyDescription(e.target.value)}
                rows={3}
                className="input-minecraft w-full"
                placeholder="Describe what this API key will be used for"
              />
            </div>
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={creating}
                className="btn-minecraft-primary text-[10px] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {creating ? 'CREATING...' : 'CREATE KEY'}
              </button>
              <button
                type="button"
                onClick={closeCreateForm}
                disabled={creating}
                className="btn-minecraft text-[10px] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                CANCEL
              </button>
            </div>
          </form>
        </div>
      )}

      {/* API Keys Table */}
      <div className="card-minecraft p-6">
        {loading ? (
          <div className="text-center py-8 text-[10px] font-minecraft text-minecraft-text-light">
            LOADING API KEYS...
          </div>
        ) : keys.length === 0 ? (
          <div className="text-minecraft-text-dark text-center py-8">
            <p className="text-sm font-minecraft mb-2">NO API KEYS FOUND</p>
            <p className="text-[10px] font-minecraft">CREATE AN API KEY TO GET STARTED</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b-2 border-[#5D4037]">
                  <th className="text-left py-3 px-4 text-[10px] font-minecraft text-minecraft-text-light uppercase">
                    NAME
                  </th>
                  <th className="text-left py-3 px-4 text-[10px] font-minecraft text-minecraft-text-light uppercase">
                    KEY ID
                  </th>
                  <th className="text-left py-3 px-4 text-[10px] font-minecraft text-minecraft-text-light uppercase">
                    DESCRIPTION
                  </th>
                  <th className="text-left py-3 px-4 text-[10px] font-minecraft text-minecraft-text-light uppercase">
                    STATUS
                  </th>
                  <th className="text-left py-3 px-4 text-[10px] font-minecraft text-minecraft-text-light uppercase">
                    CREATED
                  </th>
                  <th className="text-left py-3 px-4 text-[10px] font-minecraft text-minecraft-text-light uppercase">
                    ACTIONS
                  </th>
                </tr>
              </thead>
              <tbody>
                {keys.map((key, index) => (
                  <tr
                    key={key.id || `key-${index}`}
                    className="border-b-2 border-[#5D4037] hover:bg-minecraft-dirt-DEFAULT"
                  >
                    <td className="py-3 px-4 font-minecraft text-[10px] text-minecraft-text-light">
                      {key.name}
                    </td>
                    <td className="py-3 px-4">
                      <code className="text-[10px] font-minecraft text-minecraft-text-dark">
                        {key.id}
                      </code>
                    </td>
                    <td className="py-3 px-4 font-minecraft text-[10px] text-minecraft-text-dark">
                      {key.description || <span className="italic">NO DESCRIPTION</span>}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-1 text-[8px] font-minecraft ${
                          key.enabled
                            ? 'bg-minecraft-grass-DEFAULT text-white'
                            : 'bg-[#C62828] text-white'
                        }`}
                      >
                        {key.enabled ? '✓ ENABLED' : '✗ DISABLED'}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-minecraft text-[10px] text-minecraft-text-dark">
                      {formatDate(key.created)}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleToggle(key.id, key.enabled)}
                          disabled={toggling === key.id || deleting === key.id}
                          className={`btn-minecraft text-[8px] disabled:opacity-50 disabled:cursor-not-allowed ${
                            !key.enabled ? 'bg-minecraft-grass-DEFAULT' : ''
                          }`}
                        >
                          {toggling === key.id ? '...' : key.enabled ? 'DISABLE' : 'ENABLE'}
                        </button>
                        <button
                          onClick={() => handleDelete(key.id)}
                          disabled={toggling === key.id || deleting === key.id}
                          className="btn-minecraft-danger text-[8px] disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {deleting === key.id ? 'DELETING...' : 'DELETE'}
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
        <div className="mt-4 bg-minecraft-water-DEFAULT/30 border-2 border-minecraft-water-dark p-3 text-[10px] font-minecraft text-minecraft-text-light">
          <strong>INFO:</strong> {keys.length} API KEY{keys.length !== 1 ? 'S' : ''} AVAILABLE. API
          KEYS ALLOW PROGRAMMATIC ACCESS TO THE SERVER. KEEP THEM SECURE AND ROTATE THEM REGULARLY.
        </div>
      )}
    </div>
  );
};

export default ApiKeys;
