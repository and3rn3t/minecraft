import { useEffect, useState } from 'react';
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

  useEffect(() => {
    loadLogs();
  }, [limit, offset, actionFilter, usernameFilter]);

  const loadLogs = async () => {
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
  };

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
    if (action.startsWith('player.')) return 'text-[#FF9800]';
    if (action.startsWith('user.')) return 'text-[#9C27B0]';
    if (action.startsWith('config.')) return 'text-[#2196F3]';
    return 'text-minecraft-text-light';
  };

  const clearFilters = () => {
    setActionFilter('');
    setUsernameFilter('');
    setOffset(0);
  };

  return (
    <div>
      <h1 className="text-2xl font-minecraft text-minecraft-grass-light mb-8 leading-tight">
        AUDIT LOGS
      </h1>

      {error && (
        <div className="card-minecraft p-4 mb-6 bg-[#C62828] text-white">
          <div className="text-[10px] font-minecraft">{error}</div>
        </div>
      )}

      {/* Filters */}
      <div className="card-minecraft p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
          <div>
            <label className="block text-[10px] font-minecraft text-minecraft-text-light mb-2">
              ACTION FILTER
            </label>
            <input
              type="text"
              value={actionFilter}
              onChange={e => {
                setActionFilter(e.target.value);
                setOffset(0);
              }}
              placeholder="e.g. server.start"
              className="input-minecraft w-full text-[10px]"
            />
          </div>
          <div>
            <label className="block text-[10px] font-minecraft text-minecraft-text-light mb-2">
              USERNAME FILTER
            </label>
            <input
              type="text"
              value={usernameFilter}
              onChange={e => {
                setUsernameFilter(e.target.value);
                setOffset(0);
              }}
              placeholder="Filter by username"
              className="input-minecraft w-full text-[10px]"
            />
          </div>
          <div>
            <label className="block text-[10px] font-minecraft text-minecraft-text-light mb-2">
              LIMIT
            </label>
            <select
              value={limit}
              onChange={e => {
                setLimit(Number(e.target.value));
                setOffset(0);
              }}
              className="input-minecraft w-full text-[10px]"
            >
              <option value={50}>50</option>
              <option value={100}>100</option>
              <option value={200}>200</option>
              <option value={500}>500</option>
            </select>
          </div>
          <div className="flex items-end">
            <button onClick={clearFilters} className="btn-minecraft text-[10px] w-full">
              CLEAR FILTERS
            </button>
          </div>
        </div>
        <div className="text-[10px] font-minecraft text-minecraft-text-dark">
          TOTAL: {total} LOGS
        </div>
      </div>

      {/* Logs Table */}
      <div className="card-minecraft p-4">
        {loading ? (
          <div className="text-center py-8 text-[10px] font-minecraft text-minecraft-text-light">
            LOADING...
          </div>
        ) : logs.length === 0 ? (
          <div className="text-center py-8 text-minecraft-text-dark text-[10px] font-minecraft">
            NO AUDIT LOGS FOUND
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full font-minecraft text-[10px]">
                <thead>
                  <tr className="border-b-2 border-minecraft-stone-DEFAULT">
                    <th className="text-left p-2 text-minecraft-text-light">TIMESTAMP</th>
                    <th className="text-left p-2 text-minecraft-text-light">USERNAME</th>
                    <th className="text-left p-2 text-minecraft-text-light">ACTION</th>
                    <th className="text-left p-2 text-minecraft-text-light">DETAILS</th>
                    <th className="text-left p-2 text-minecraft-text-light">IP ADDRESS</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log, index) => (
                    <tr
                      key={index}
                      className="border-b border-minecraft-dirt-DEFAULT hover:bg-minecraft-dirt-DEFAULT"
                    >
                      <td className="p-2 text-minecraft-text-dark">
                        {formatTimestamp(log.timestamp)}
                      </td>
                      <td className="p-2 text-minecraft-text-light">{log.username}</td>
                      <td className={`p-2 ${getActionColor(log.action)}`}>{log.action}</td>
                      <td className="p-2 text-minecraft-text-light">
                        {log.details ? (
                          <pre className="text-[8px] whitespace-pre-wrap max-w-md overflow-auto">
                            {JSON.stringify(log.details, null, 2)}
                          </pre>
                        ) : (
                          '-'
                        )}
                      </td>
                      <td className="p-2 text-minecraft-text-dark text-[8px]">
                        {log.ip_address || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {total > limit && (
              <div className="mt-4 flex items-center justify-between">
                <button
                  onClick={() => setOffset(Math.max(0, offset - limit))}
                  disabled={offset === 0}
                  className="btn-minecraft text-[10px] disabled:opacity-50"
                >
                  PREVIOUS
                </button>
                <span className="text-[10px] font-minecraft text-minecraft-text-dark">
                  SHOWING {offset + 1}-{Math.min(offset + limit, total)} OF {total}
                </span>
                <button
                  onClick={() => setOffset(offset + limit)}
                  disabled={offset + limit >= total}
                  className="btn-minecraft text-[10px] disabled:opacity-50"
                >
                  NEXT
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default AuditLogs;
