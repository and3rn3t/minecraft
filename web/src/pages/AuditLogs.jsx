import { useCallback, useEffect, useState } from 'react';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { ErrorState } from '../components/ui/Alert';
import { EmptyState } from '../components/ui/EmptyState';
import { Input, Select } from '../components/ui/FormField';
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

const AuditLogs = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [limit, setLimit] = useState(100);
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const [actionFilter, setActionFilter] = useState('');
  const [usernameFilter, setUsernameFilter] = useState('');

  const loadLogs = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getAuditLogs(
        limit,
        offset,
        actionFilter || null,
        usernameFilter || null
      );
      if (data.success) {
        setLogs(data.logs || []);
        setTotal(data.total || 0);
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to load audit logs');
    } finally {
      setLoading(false);
    }
  }, [limit, offset, actionFilter, usernameFilter]);

  useEffect(() => {
    loadLogs();
  }, [loadLogs]);

  const formatTimestamp = timestamp => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleString();
    } catch {
      return timestamp;
    }
  };

  const getActionColor = action => {
    if (action.startsWith('server.')) return 'text-minecraft-water-light';
    if (action.startsWith('backup.')) return 'text-minecraft-grass-light';
    if (action.startsWith('player.')) return 'text-minecraft-warning-light';
    if (action.startsWith('user.')) return 'text-[#9C27B0]';
    if (action.startsWith('config.')) return 'text-minecraft-info';
    return 'text-minecraft-text-light';
  };

  const clearFilters = () => {
    setActionFilter('');
    setUsernameFilter('');
    setOffset(0);
  };

  return (
    <div>
      <PageHeader title="AUDIT LOGS" />

      {error && <ErrorState message={error} />}

      {/* Filters */}
      <Card padding="md" className="mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
          <Input
            label="ACTION FILTER"
            type="text"
            value={actionFilter}
            onChange={e => {
              setActionFilter(e.target.value);
              setOffset(0);
            }}
            placeholder="e.g. server.start"
          />
          <Input
            label="USERNAME FILTER"
            type="text"
            value={usernameFilter}
            onChange={e => {
              setUsernameFilter(e.target.value);
              setOffset(0);
            }}
            placeholder="Filter by username"
          />
          <Select
            label="LIMIT"
            value={limit}
            onChange={e => {
              setLimit(Number(e.target.value));
              setOffset(0);
            }}
          >
            <option value={50}>50</option>
            <option value={100}>100</option>
            <option value={200}>200</option>
            <option value={500}>500</option>
          </Select>
          <div className="flex items-end">
            <Button className="w-full" onClick={clearFilters}>
              CLEAR FILTERS
            </Button>
          </div>
        </div>
        <div className="text-[10px] font-minecraft text-minecraft-text-dark">
          TOTAL: {total} LOGS
        </div>
      </Card>

      {/* Logs Table */}
      <Card padding="md">
        {loading ? (
          <div className="text-center py-8 text-[10px] font-minecraft text-minecraft-text-light">
            LOADING...
          </div>
        ) : logs.length === 0 ? (
          <EmptyState icon="📋" title="No audit logs found" />
        ) : (
          <>
            <Table caption="Audit logs">
              <TableHead>
                <TableRow>
                  <TableHeaderCell>Timestamp</TableHeaderCell>
                  <TableHeaderCell>Username</TableHeaderCell>
                  <TableHeaderCell>Action</TableHeaderCell>
                  <TableHeaderCell>Details</TableHeaderCell>
                  <TableHeaderCell>IP Address</TableHeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {logs.map((log, index) => (
                  <TableRow key={index} className="hover:bg-minecraft-dirt">
                    <TableCell className="text-minecraft-text-dark">
                      {formatTimestamp(log.timestamp)}
                    </TableCell>
                    <TableCell>{log.username}</TableCell>
                    <TableCell className={getActionColor(log.action)}>{log.action}</TableCell>
                    <TableCell>
                      {log.details ? (
                        <pre className="text-[8px] whitespace-pre-wrap max-w-md overflow-auto">
                          {JSON.stringify(log.details, null, 2)}
                        </pre>
                      ) : (
                        '-'
                      )}
                    </TableCell>
                    <TableCell className="text-minecraft-text-dark text-[8px]">
                      {log.ip_address || '-'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            {/* Pagination */}
            {total > limit && (
              <div className="mt-4 flex items-center justify-between">
                <Button
                  onClick={() => setOffset(Math.max(0, offset - limit))}
                  disabled={offset === 0}
                >
                  PREVIOUS
                </Button>
                <span className="text-[10px] font-minecraft text-minecraft-text-dark">
                  SHOWING {offset + 1}-{Math.min(offset + limit, total)} OF {total}
                </span>
                <Button
                  onClick={() => setOffset(offset + limit)}
                  disabled={offset + limit >= total}
                >
                  NEXT
                </Button>
              </div>
            )}
          </>
        )}
      </Card>
    </div>
  );
};

export default AuditLogs;
