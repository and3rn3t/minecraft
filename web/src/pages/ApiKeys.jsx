import { useEffect, useState } from 'react';
import { Alert, ErrorState } from '../components/ui/Alert';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { Input, Select, Textarea } from '../components/ui/FormField';
import { Modal } from '../components/ui/Modal';
import { PageHeader } from '../components/ui/PageHeader';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from '../components/ui/Table';
import { api } from '../services/api';

const ApiKeys = () => {
  const [keys, setKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [newKeyDescription, setNewKeyDescription] = useState('');
  const [newKeyRole, setNewKeyRole] = useState('user');
  const [newKeyValue, setNewKeyValue] = useState(null);
  const [toggling, setToggling] = useState(null);
  const [rescoping, setRescoping] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    loadKeys();
  }, []);

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
      const result = await api.createApiKey(
        newKeyName.trim(),
        newKeyDescription.trim(),
        newKeyRole
      );
      setNewKeyValue(result.key);
      setSuccess(result.message || 'API key created successfully!');
      setNewKeyName('');
      setNewKeyDescription('');
      setNewKeyRole('user');
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

  const handleRescope = async (keyId, role) => {
    setRescoping(keyId);
    setError(null);
    setSuccess(null);

    try {
      const result = await api.updateApiKeyScope(keyId, role);
      setSuccess(result.message || 'API key scope updated');
      loadKeys();
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Failed to update API key scope');
      console.error('Failed to update API key scope:', err);
    } finally {
      setRescoping(null);
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
    setNewKeyRole('user');
    setNewKeyValue(null);
  };

  return (
    <div>
      <PageHeader
        title="API KEYS"
        actions={
          <Button variant="primary" onClick={() => setShowCreateForm(true)} icon="🔑">
            CREATE API KEY
          </Button>
        }
      />

      {/* Error/Success messages */}
      {error && <ErrorState message={error} />}

      {success && (
        <Alert tone="success" autoDismiss={5000} onDismiss={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      {/* New Key Display */}
      <Modal open={!!newKeyValue} onClose={closeCreateForm} title="⚠️ NEW API KEY CREATED">
        <p className="text-[10px] font-minecraft text-minecraft-text-light mb-4">
          <strong>Important:</strong> save this API key securely. It will not be shown again.
        </p>
        <Card padding="md" className="bg-minecraft-background-dark mb-4">
          <div className="flex items-center justify-between">
            <code className="text-xs font-minecraft text-minecraft-text-light break-all">
              {newKeyValue}
            </code>
            <Button size="sm" className="ml-4 whitespace-nowrap" onClick={() => copyToClipboard(newKeyValue)}>
              COPY
            </Button>
          </div>
        </Card>
        <Button variant="primary" onClick={closeCreateForm}>
          I&apos;VE SAVED THE KEY
        </Button>
      </Modal>

      {/* Create Form */}
      <Modal
        open={showCreateForm && !newKeyValue}
        onClose={closeCreateForm}
        title="CREATE NEW API KEY"
      >
        <form onSubmit={handleCreateKey} className="space-y-4">
          <Input
            label="KEY NAME"
            type="text"
            value={newKeyName}
            onChange={e => setNewKeyName(e.target.value)}
            required
            placeholder="e.g., Webhook Integration"
          />
          <Textarea
            label="DESCRIPTION (OPTIONAL)"
            value={newKeyDescription}
            onChange={e => setNewKeyDescription(e.target.value)}
            rows={3}
            placeholder="Describe what this API key will be used for"
          />
          <Select
            label="ACCESS LEVEL"
            value={newKeyRole}
            onChange={e => setNewKeyRole(e.target.value)}
            hint="A key on a phone or in a browser should be the smallest level that works."
          >
            <option value="user">USER — READ ONLY</option>
            <option value="operator">OPERATOR — CONTROL THE SERVER</option>
            <option value="admin">ADMIN — EVERYTHING, INCLUDING USERS AND KEYS</option>
          </Select>
          <div className="flex gap-2">
            <Button type="submit" variant="primary" disabled={creating}>
              {creating ? 'CREATING...' : 'CREATE KEY'}
            </Button>
            <Button type="button" onClick={closeCreateForm} disabled={creating}>
              CANCEL
            </Button>
          </div>
        </form>
      </Modal>

      {/* API Keys Table */}
      <Card padding="lg">
        {loading ? (
          <div className="text-center py-8 text-[10px] font-minecraft text-minecraft-text-light">
            LOADING API KEYS...
          </div>
        ) : keys.length === 0 ? (
          <EmptyState icon="🔑" title="No API keys found" hint="Create an API key to get started" />
        ) : (
          <Table caption="API keys">
            <TableHead>
              <TableRow>
                <TableHeaderCell>Name</TableHeaderCell>
                <TableHeaderCell>Key ID</TableHeaderCell>
                <TableHeaderCell>Description</TableHeaderCell>
                <TableHeaderCell>Access</TableHeaderCell>
                <TableHeaderCell>Status</TableHeaderCell>
                <TableHeaderCell>Created</TableHeaderCell>
                <TableHeaderCell>Actions</TableHeaderCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {keys.map((key, index) => (
                <TableRow key={key.id || `key-${index}`} className="hover:bg-minecraft-dirt">
                  <TableCell>{key.name}</TableCell>
                  <TableCell>
                    <code className="text-[10px] font-minecraft text-minecraft-text-dark">
                      {key.id}
                    </code>
                  </TableCell>
                  <TableCell className="text-minecraft-text-dark">
                    {key.description || <span className="italic">NO DESCRIPTION</span>}
                  </TableCell>
                  <TableCell>
                    <select
                      value={key.role || 'user'}
                      onChange={e => handleRescope(key.id, e.target.value)}
                      disabled={rescoping === key.id || deleting === key.id}
                      aria-label={`Access level for ${key.name}`}
                      className="input-minecraft text-[8px] disabled:opacity-50"
                    >
                      <option value="user">USER</option>
                      <option value="operator">OPERATOR</option>
                      <option value="admin">ADMIN</option>
                    </select>
                  </TableCell>
                  <TableCell>
                    <Badge status={key.enabled ? 'success' : 'danger'}>
                      {key.enabled ? '✓ ENABLED' : '✗ DISABLED'}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-minecraft-text-dark">
                    {formatDate(key.created)}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        onClick={() => handleToggle(key.id, key.enabled)}
                        disabled={toggling === key.id || deleting === key.id}
                      >
                        {toggling === key.id ? '...' : key.enabled ? 'DISABLE' : 'ENABLE'}
                      </Button>
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => handleDelete(key.id)}
                        disabled={toggling === key.id || deleting === key.id}
                      >
                        {deleting === key.id ? 'DELETING...' : 'DELETE'}
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Card>

      {/* Info */}
      {keys.length > 0 && (
        <div className="mt-4 bg-minecraft-water/30 border-2 border-minecraft-water-dark p-3 text-[10px] font-minecraft text-minecraft-text-light">
          <strong>INFO:</strong> {keys.length} API KEY{keys.length !== 1 ? 'S' : ''} AVAILABLE. API
          KEYS ALLOW PROGRAMMATIC ACCESS TO THE SERVER. KEEP THEM SECURE AND ROTATE THEM REGULARLY.
        </div>
      )}
    </div>
  );
};

export default ApiKeys;
