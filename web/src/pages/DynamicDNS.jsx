import { useEffect, useState } from 'react';
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
      <h1 className="text-2xl font-minecraft text-minecraft-grass-light mb-8 leading-tight">
        DYNAMIC DNS
      </h1>

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

      {/* Status Card */}
      <div className="card-minecraft p-6 mb-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-sm font-minecraft text-minecraft-text-light uppercase">
            DDNS STATUS
          </h2>
          <button
            onClick={handleUpdate}
            disabled={updating}
            className="btn-minecraft-primary text-[10px] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {updating ? 'UPDATING...' : 'UPDATE NOW'}
          </button>
        </div>
        {status && status.status && (
          <div className="font-minecraft text-[10px] text-minecraft-text-light whitespace-pre-line">
            {status.status}
          </div>
        )}
      </div>

      {/* Configuration Editor */}
      {config && (
        <div className="card-minecraft p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-sm font-minecraft text-minecraft-text-light uppercase">
              CONFIGURATION
            </h2>
            {config.is_example && (
              <span className="text-[8px] font-minecraft text-[#F57C00]">USING EXAMPLE CONFIG</span>
            )}
          </div>
          <textarea
            value={config.content || ''}
            onChange={e => setConfig({ ...config, content: e.target.value })}
            className="input-minecraft w-full h-96 font-mono text-[10px]"
            spellCheck={false}
          />
          <div className="mt-4 flex gap-2">
            <button
              onClick={handleSaveConfig}
              disabled={saving}
              className="btn-minecraft-primary text-[10px] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? 'SAVING...' : 'SAVE CONFIGURATION'}
            </button>
            <button onClick={loadData} className="btn-minecraft text-[10px]">
              RELOAD
            </button>
          </div>
        </div>
      )}

      {/* Info */}
      <div className="mt-4 bg-minecraft-water-DEFAULT/30 border-2 border-minecraft-water-dark p-3 text-[10px] font-minecraft text-minecraft-text-light">
        <strong>INFO:</strong> DYNAMIC DNS AUTOMATICALLY UPDATES YOUR DNS RECORDS WHEN YOUR PUBLIC
        IP ADDRESS CHANGES. CONFIGURE YOUR PROVIDER SETTINGS ABOVE AND ENABLE DDNS TO START
        AUTOMATIC UPDATES.
      </div>
    </div>
  );
};

export default DynamicDNS;
