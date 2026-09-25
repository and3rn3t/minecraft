import { useEffect, useState } from 'react';
import { Alert, ErrorState } from '../components/ui/Alert';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { Input, Select } from '../components/ui/FormField';
import { PageHeader } from '../components/ui/PageHeader';
import { api } from '../services/api';

const Datapacks = () => {
  const [datapacks, setDatapacks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [installing, setInstalling] = useState(false);
  const [busyName, setBusyName] = useState(null);
  const [formData, setFormData] = useState({ name: '', source: 'url', url: '', file: null });

  useEffect(() => {
    loadDatapacks();
  }, []);

  const loadDatapacks = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.listDatapacks();
      setDatapacks(data.datapacks || []);
    } catch (err) {
      setError(err.response?.data?.error || 'Could not load datapacks.');
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({ name: '', source: 'url', url: '', file: null });
  };

  const handleInstall = async e => {
    e.preventDefault();
    try {
      setInstalling(true);
      setError(null);
      setMessage(null);
      const data = await api.installDatapack(formData);
      if (data.success) {
        setMessage(`Datapack "${formData.name}" installed and enabled`);
        setShowForm(false);
        resetForm();
        loadDatapacks();
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to install datapack');
    } finally {
      setInstalling(false);
    }
  };

  const handleEnable = async name => {
    try {
      setBusyName(name);
      setError(null);
      const data = await api.enableDatapack(name);
      if (data.success) {
        setMessage(`Datapack "${name}" enabled`);
        loadDatapacks();
      }
    } catch (err) {
      setError(err.response?.data?.error || `Failed to enable ${name}`);
    } finally {
      setBusyName(null);
    }
  };

  const handleDisable = async name => {
    try {
      setBusyName(name);
      setError(null);
      const data = await api.disableDatapack(name);
      if (data.success) {
        setMessage(`Datapack "${name}" disabled`);
        loadDatapacks();
      }
    } catch (err) {
      setError(err.response?.data?.error || `Failed to disable ${name}`);
    } finally {
      setBusyName(null);
    }
  };

  const handleDelete = async name => {
    if (!confirm(`Delete "${name}"? Its tracked source will be backed up first, but this removes it from git.`)) {
      return;
    }
    try {
      setBusyName(name);
      setError(null);
      const data = await api.deleteDatapack(name);
      if (data.success) {
        setMessage(`Datapack "${name}" deleted`);
        loadDatapacks();
      }
    } catch (err) {
      setError(err.response?.data?.error || `Failed to delete ${name}`);
    } finally {
      setBusyName(null);
    }
  };

  return (
    <div>
      <PageHeader
        title="DATAPACKS"
        subtitle="Vanilla datapacks — advancements, recipes, loot tables and functions, no plugin required"
        actions={
          <Button
            variant="primary"
            onClick={() => {
              resetForm();
              setShowForm(show => !show);
            }}
          >
            + INSTALL DATAPACK
          </Button>
        }
      />

      {message && <Alert tone="success" autoDismiss={4000} onDismiss={() => setMessage(null)}>{message}</Alert>}

      {error && <ErrorState message={error} onRetry={loadDatapacks} />}

      {showForm && (
        <Card padding="lg" className="mb-6">
          <h2 className="text-sm font-minecraft text-minecraft-text-light mb-4 uppercase">
            INSTALL DATAPACK
          </h2>
          <form onSubmit={handleInstall} className="space-y-4">
            <Input
              label="NAME"
              type="text"
              value={formData.name}
              onChange={e => setFormData({ ...formData, name: e.target.value })}
              required
              placeholder="e.g. family"
              hint="Letters, numbers and underscores only"
            />

            <Select
              label="SOURCE"
              value={formData.source}
              onChange={e => setFormData({ ...formData, source: e.target.value })}
            >
              <option value="url">Zip URL</option>
              <option value="file">Upload a zip file</option>
            </Select>

            {formData.source === 'url' ? (
              <Input
                label="ZIP URL"
                type="url"
                value={formData.url}
                onChange={e => setFormData({ ...formData, url: e.target.value })}
                required
                placeholder="https://example.com/datapack.zip"
              />
            ) : (
              <Input
                label="ZIP FILE"
                type="file"
                accept=".zip"
                onChange={e => setFormData({ ...formData, file: e.target.files?.[0] || null })}
                required
              />
            )}

            <div className="flex gap-2">
              <Button type="submit" variant="primary" loading={installing}>
                INSTALL &amp; ENABLE
              </Button>
              <Button
                type="button"
                onClick={() => {
                  setShowForm(false);
                  resetForm();
                }}
              >
                CANCEL
              </Button>
            </div>
          </form>
        </Card>
      )}

      <Card padding="lg">
        {loading ? (
          <div className="text-center py-8 text-[10px] font-minecraft text-minecraft-text-light">
            LOADING DATAPACKS...
          </div>
        ) : error && !datapacks.length ? null : datapacks.length === 0 ? (
          <EmptyState
            icon="📦"
            title="NO DATAPACKS YET"
            hint="Install one from a zip, or scaffold one with scripts/datapack-manager.sh create"
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {datapacks.map(pack => (
              <Card key={pack.name} padding="md">
                <h3 className="text-sm font-minecraft text-minecraft-text-light mb-1 leading-tight">
                  {pack.name}
                </h3>
                <p className="text-[10px] font-minecraft text-minecraft-text-dark mb-2">
                  <Badge status={pack.enabled ? 'success' : 'neutral'}>
                    {pack.enabled ? 'ENABLED' : 'AVAILABLE'}
                  </Badge>
                  {pack.world && <span className="ml-2">world: {pack.world}</span>}
                </p>
                <div className="flex gap-2 mt-4">
                  {pack.enabled ? (
                    <Button
                      variant="danger"
                      size="sm"
                      className="flex-1"
                      loading={busyName === pack.name}
                      onClick={() => handleDisable(pack.name)}
                    >
                      DISABLE
                    </Button>
                  ) : (
                    <Button
                      variant="primary"
                      size="sm"
                      className="flex-1"
                      loading={busyName === pack.name}
                      onClick={() => handleEnable(pack.name)}
                    >
                      ENABLE
                    </Button>
                  )}
                  <Button
                    size="sm"
                    className="flex-1"
                    loading={busyName === pack.name}
                    onClick={() => handleDelete(pack.name)}
                  >
                    DELETE
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
};

export default Datapacks;
