import { useEffect, useState } from 'react';
import { api } from '../services/api';

const Backups = () => {
  const [backups, setBackups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [restoring, setRestoring] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    loadBackups();
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

  const loadBackups = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.listBackups();
      setBackups(data.backups || []);
    } catch (err) {
      setError('Failed to load backups');
      console.error('Failed to load backups:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateBackup = async () => {
    setCreating(true);
    setError(null);
    setSuccess(null);

    try {
      const result = await api.createBackup();
      setSuccess(result.message || 'Backup created successfully!');
      // Reload after creation (wait a bit for file system to sync)
      setTimeout(loadBackups, 2000);
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Failed to create backup');
      console.error('Failed to create backup:', err);
    } finally {
      setCreating(false);
    }
  };

  const handleRestore = async backupName => {
    if (
      !window.confirm(
        `Are you sure you want to restore backup "${backupName}"?\n\nThis will stop the server and restore the backup. The current state will be backed up first.`
      )
    ) {
      return;
    }

    setRestoring(backupName);
    setError(null);
    setSuccess(null);

    try {
      const result = await api.restoreBackup(backupName);
      setSuccess(
        result.pre_restore_backup
          ? `Backup restored successfully! Current state backed up to: ${result.pre_restore_backup}`
          : 'Backup restored successfully!'
      );
      // Reload backups after restore
      setTimeout(loadBackups, 1000);
    } catch (err) {
      setError(
        err.response?.data?.error || err.message || `Failed to restore backup: ${backupName}`
      );
      console.error('Failed to restore backup:', err);
    } finally {
      setRestoring(null);
    }
  };

  const handleDelete = async backupName => {
    if (
      !window.confirm(
        `Are you sure you want to delete backup "${backupName}"?\n\nThis action cannot be undone.`
      )
    ) {
      return;
    }

    setDeleting(backupName);
    setError(null);
    setSuccess(null);

    try {
      await api.deleteBackup(backupName);
      setSuccess(`Backup "${backupName}" deleted successfully`);
      // Reload backups after delete
      loadBackups();
    } catch (err) {
      setError(
        err.response?.data?.error || err.message || `Failed to delete backup: ${backupName}`
      );
      console.error('Failed to delete backup:', err);
    } finally {
      setDeleting(null);
    }
  };

  const formatSize = bytes => {
    if (!bytes) return 'Unknown';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
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

  const formatAge = dateString => {
    if (!dateString) return 'Unknown';
    try {
      const date = new Date(dateString);
      const now = new Date();
      const diffMs = now - date;
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMs / 3600000);
      const diffDays = Math.floor(diffMs / 86400000);

      if (diffMins < 1) return 'Just now';
      if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
      if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
      if (diffDays < 30) return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
      return `${Math.floor(diffDays / 30)} month${Math.floor(diffDays / 30) !== 1 ? 's' : ''} ago`;
    } catch {
      return 'Unknown';
    }
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-minecraft text-minecraft-grass-light leading-tight">
          BACKUPS
        </h1>
        <button
          onClick={handleCreateBackup}
          disabled={creating}
          className="btn-minecraft-primary text-[10px] disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {creating ? (
            <>
              <span>⏳</span>
              CREATING...
            </>
          ) : (
            <>
              <span>💾</span>
              CREATE BACKUP
            </>
          )}
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

      {/* Backups Table */}
      <div className="card-minecraft p-6">
        {loading ? (
          <div className="text-center py-8 text-[10px] font-minecraft text-minecraft-text-light">
            LOADING BACKUPS...
          </div>
        ) : backups.length === 0 ? (
          <div className="text-minecraft-text-dark text-center py-8">
            <p className="text-sm font-minecraft mb-2">NO BACKUPS FOUND</p>
            <p className="text-[10px] font-minecraft">CREATE A BACKUP TO GET STARTED</p>
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
                    SIZE
                  </th>
                  <th className="text-left py-3 px-4 text-[10px] font-minecraft text-minecraft-text-light uppercase">
                    CREATED
                  </th>
                  <th className="text-left py-3 px-4 text-[10px] font-minecraft text-minecraft-text-light uppercase">
                    AGE
                  </th>
                  <th className="text-left py-3 px-4 text-[10px] font-minecraft text-minecraft-text-light uppercase">
                    ACTIONS
                  </th>
                </tr>
              </thead>
              <tbody>
                {backups.map((backup, index) => (
                  <tr
                    key={backup.name || `backup-${index}`}
                    className="border-b-2 border-[#5D4037] hover:bg-minecraft-dirt-DEFAULT"
                  >
                    <td className="py-3 px-4 font-minecraft text-[10px] text-minecraft-text-light">
                      {backup.name}
                    </td>
                    <td className="py-3 px-4 font-minecraft text-[10px] text-minecraft-text-light">
                      {formatSize(backup.size)}
                    </td>
                    <td className="py-3 px-4 font-minecraft text-[10px] text-minecraft-text-light">
                      {formatDate(backup.created)}
                    </td>
                    <td className="py-3 px-4 font-minecraft text-[10px] text-minecraft-text-dark">
                      {formatAge(backup.created)}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleRestore(backup.name)}
                          disabled={restoring === backup.name || deleting === backup.name}
                          className="btn-minecraft text-[8px] disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {restoring === backup.name ? 'RESTORING...' : 'RESTORE'}
                        </button>
                        <button
                          onClick={() => handleDelete(backup.name)}
                          disabled={restoring === backup.name || deleting === backup.name}
                          className="btn-minecraft-danger text-[8px] disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {deleting === backup.name ? 'DELETING...' : 'DELETE'}
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
      {backups.length > 0 && (
        <div className="mt-4 bg-minecraft-water-DEFAULT/30 border-2 border-minecraft-water-dark p-3 text-[10px] font-minecraft text-minecraft-text-light">
          <strong>INFO:</strong> {backups.length} BACKUP{backups.length !== 1 ? 'S' : ''} AVAILABLE.
          RESTORING A BACKUP WILL STOP THE SERVER AND CREATE A BACKUP OF THE CURRENT STATE FIRST.
        </div>
      )}
    </div>
  );
};

export default Backups;
