import { useEffect, useState } from 'react';
import { Alert, ErrorState } from '../components/ui/Alert';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Textarea } from '../components/ui/FormField';
import { PageHeader } from '../components/ui/PageHeader';
import { api } from '../services/api';

const DynamicDNS = () => {
  const [status, setStatus] = useState(null);
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [statusData, configData] = await Promise.all([
        api.getDdnsStatus().catch(() => ({ success: false, status: 'Unable to load status' })),
        api.getDdnsConfig().catch(() => ({ content: '', is_example: true })),
      ]);
      setStatus(statusData);
      setConfig(configData);
    } catch (err) {
      setError(`Failed to load DDNS data: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async () => {
    try {
      setUpdating(true);
      setError(null);
      setSuccess(null);
      const result = await api.updateDdns();
      if (result.success) {
        setSuccess('DDNS updated successfully!');
        await loadData();
      } else {
        setError(result.error || 'DDNS update failed');
      }
    } catch (err) {
      setError(`Failed to update DDNS: ${err.message}`);
    } finally {
      setUpdating(false);
    }
  };

  const handleSaveConfig = async () => {
    if (!config) return;

    try {
      setSaving(true);
      setError(null);
      setSuccess(null);
      const result = await api.saveDdnsConfig(config.content);
      if (result.success) {
        setSuccess('Configuration saved successfully!');
        await loadData();
      } else {
        setError(result.error || 'Failed to save configuration');
      }
    } catch (err) {
      setError(`Failed to save configuration: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-sm font-minecraft text-minecraft-text-light">LOADING...</div>
      </div>
    );
  }

  return (
    <div>
      <PageHeader title="DYNAMIC DNS" />

      {/* Error/Success messages */}
      {error && <ErrorState message={error} />}

      {success && (
        <Alert tone="success" autoDismiss={5000} onDismiss={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      {/* Status Card */}
      <Card padding="lg" className="mb-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-sm font-minecraft text-minecraft-text-light uppercase">
            DDNS STATUS
          </h2>
          <Button variant="primary" onClick={handleUpdate} disabled={updating}>
            {updating ? 'UPDATING...' : 'UPDATE NOW'}
          </Button>
        </div>
        {status?.status && (
          <div className="font-minecraft text-[10px] text-minecraft-text-light whitespace-pre-line">
            {status.status}
          </div>
        )}
      </Card>

      {/* Configuration Editor */}
      {config && (
        <Card padding="lg">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-sm font-minecraft text-minecraft-text-light uppercase">
              CONFIGURATION
            </h2>
            {config.is_example && (
              <span className="text-[8px] font-minecraft text-minecraft-warning">
                USING EXAMPLE CONFIG
              </span>
            )}
          </div>
          <Textarea
            aria-label="DDNS configuration"
            value={config.content || ''}
            onChange={e => setConfig({ ...config, content: e.target.value })}
            className="h-96 font-mono text-[10px]"
            spellCheck={false}
          />
          <div className="mt-4 flex gap-2">
            <Button variant="primary" onClick={handleSaveConfig} disabled={saving}>
              {saving ? 'SAVING...' : 'SAVE CONFIGURATION'}
            </Button>
            <Button onClick={loadData}>RELOAD</Button>
          </div>
        </Card>
      )}

      {/* Info */}
      <div className="mt-4 bg-minecraft-water/30 border-2 border-minecraft-water-dark p-3 text-[10px] font-minecraft text-minecraft-text-light">
        <strong>INFO:</strong> DYNAMIC DNS AUTOMATICALLY UPDATES YOUR DNS RECORDS WHEN YOUR PUBLIC
        IP ADDRESS CHANGES. CONFIGURE YOUR PROVIDER SETTINGS ABOVE AND ENABLE DDNS TO START
        AUTOMATIC UPDATES.
      </div>
    </div>
  );
};

export default DynamicDNS;
