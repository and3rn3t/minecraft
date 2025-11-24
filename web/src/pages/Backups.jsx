import { useCallback, useState } from 'react';
import { useToast } from '../components/ToastContainer';
import { useErrorHandler } from '../hooks/useErrorHandler';
import { usePolling } from '../hooks/usePolling';
import { api } from '../services/api';

const Backups = () => {
  const [creating, setCreating] = useState(false);
  const [restoring, setRestoring] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const { success: showSuccess, error: showError } = useToast();
  const handleError = useErrorHandler();

  // Poll backups list every 30 seconds
  const { data: backupsData, loading } = usePolling(
    useCallback(async () => {
      const data = await api.listBackups();
      return data.backups || [];
    }, []),
    30000
  );

  const backups = backupsData || [];

  const handleCreateBackup = useCallback(async () => {
    setCreating(true);
    try {
      const result = await api.createBackup();
      showSuccess(result.message || 'Backup created successfully!');
      // Data will refresh automatically via polling
    } catch (err) {
      handleError(err, 'Failed to create backup');
    } finally {
      setCreating(false);
    }
  }, [showSuccess, handleError]);

  const handleRestore = useCallback(
    async backupName => {
      if (
        !window.confirm(
          `Are you sure you want to restore backup "${backupName}"?\n\nThis will stop the server and restore the backup. The current state will be backed up first.`
        )
      ) {
        return;
      }

      setRestoring(backupName);
      try {
        const result = await api.restoreBackup(backupName);
        showSuccess(
          result.pre_restore_backup
            ? `Backup restored successfully! Current state backed up to: ${result.pre_restore_backup}`
            : 'Backup restored successfully!'
        );
        // Data will refresh automatically via polling
      } catch (err) {
        handleError(err, `Failed to restore backup: ${backupName}`);
      } finally {
        setRestoring(null);
      }
    },
    [showSuccess, handleError]
  );

  const handleDelete = useCallback(
    async backupName => {
      if (
        !window.confirm(
          `Are you sure you want to delete backup "${backupName}"?\n\nThis action cannot be undone.`
        )
      ) {
        return;
      }

      setDeleting(backupName);
      try {
        await api.deleteBackup(backupName);
        showSuccess(`Backup "${backupName}" deleted successfully`);
        // Data will refresh automatically via polling
      } catch (err) {
        handleError(err, `Failed to delete backup: ${backupName}`);
      } finally {
        setDeleting(null);
      }
    },
    [showSuccess, handleError]
  );

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
