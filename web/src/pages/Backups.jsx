import { useCallback, useEffect, useState } from 'react';
import { useToast } from '../components/ToastContainer';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { ErrorState } from '../components/ui/Alert';
import { PageHeader } from '../components/ui/PageHeader';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from '../components/ui/Table';
import { useErrorHandler } from '../hooks/useErrorHandler';
import { usePolling } from '../hooks/usePolling';
import { api } from '../services/api';

const Backups = () => {
  const [creating, setCreating] = useState(false);
  const [restoring, setRestoring] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const { success: showSuccess } = useToast();
  const handleError = useErrorHandler();

  // Poll backups list every 30 seconds
  const {
    data: backupsData,
    loading,
    error: pollingError,
    refetch,
  } = usePolling(
    useCallback(async signal => {
      const data = await api.listBackups(signal);
      return data.backups || [];
    }, []),
    30000
  );

  useEffect(() => {
    if (pollingError) {
      handleError(pollingError, 'Failed to load backups');
    }
  }, [pollingError, handleError]);

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
      <PageHeader
        title="BACKUPS"
        actions={
          <Button variant="primary" onClick={handleCreateBackup} disabled={creating}>
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
          </Button>
        }
      />

      {pollingError && <ErrorState message="Failed to load backups" onRetry={refetch} />}

      {/* Backups Table */}
      <Card padding="lg">
        {loading ? (
          <div className="text-center py-8 text-[10px] font-minecraft text-minecraft-text-light">
            LOADING BACKUPS...
          </div>
        ) : backups.length === 0 ? (
          <EmptyState icon="💾" title="No backups found" hint="Create a backup to get started" />
        ) : (
          <Table caption="Server backups">
            <TableHead>
              <TableRow>
                <TableHeaderCell>Name</TableHeaderCell>
                <TableHeaderCell>Size</TableHeaderCell>
                <TableHeaderCell>Created</TableHeaderCell>
                <TableHeaderCell>Age</TableHeaderCell>
                <TableHeaderCell>Actions</TableHeaderCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {backups.map((backup, index) => (
                <TableRow key={backup.name || `backup-${index}`} className="hover:bg-minecraft-dirt">
                  <TableCell>{backup.name}</TableCell>
                  <TableCell>{formatSize(backup.size)}</TableCell>
                  <TableCell>{formatDate(backup.created)}</TableCell>
                  <TableCell className="text-minecraft-text-dark">
                    {formatAge(backup.created)}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        onClick={() => handleRestore(backup.name)}
                        disabled={restoring === backup.name || deleting === backup.name}
                      >
                        {restoring === backup.name ? 'RESTORING...' : 'RESTORE'}
                      </Button>
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => handleDelete(backup.name)}
                        disabled={restoring === backup.name || deleting === backup.name}
                      >
                        {deleting === backup.name ? 'DELETING...' : 'DELETE'}
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
      {backups.length > 0 && (
        <div className="mt-4 border-2 border-minecraft-water-dark bg-minecraft-water/30 p-3 text-[10px] font-minecraft text-minecraft-text-light">
          <strong>INFO:</strong> {backups.length} backup{backups.length !== 1 ? 's' : ''} available.
          Restoring a backup will stop the server and create a backup of the current state first.
        </div>
      )}
    </div>
  );
};

export default Backups;
