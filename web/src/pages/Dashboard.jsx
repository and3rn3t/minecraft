import { useCallback, useEffect, useMemo, useState } from 'react';
import { StatusCardSkeleton } from '../components/LoadingSkeleton';
import MetricsChart from '../components/MetricsChart';
import StatusCard from '../components/StatusCard';
import { useToast } from '../components/ToastContainer';
import { useErrorHandler } from '../hooks/useErrorHandler';
import { usePolling } from '../hooks/usePolling';
import { api } from '../services/api';

const Dashboard = () => {
  const [actionLoading, setActionLoading] = useState(false);
  const { success } = useToast();
  const handleError = useErrorHandler();

  // Load dashboard data with polling
  const loadDashboardData = useCallback(async signal => {
    const [statusData, metricsData, playersData] = await Promise.all([
      api.getStatus(signal),
      api.getMetrics(signal),
      api.getPlayers(signal),
    ]);
    return {
      status: statusData,
      metrics: metricsData,
      players: playersData.players || [],
    };
  }, []);

  const {
    data: dashboardData,
    loading,
    error: pollingError,
    refetch,
  } = usePolling(loadDashboardData, 5000);

  useEffect(() => {
    if (pollingError) {
      handleError(pollingError, 'Failed to load dashboard data');
    }
  }, [pollingError, handleError]);

  const status = dashboardData?.status || null;
  const metrics = dashboardData?.metrics || null;
  const players = useMemo(() => dashboardData?.players || [], [dashboardData?.players]);

  const lastUpdated = useMemo(() => {
    if (!status?.timestamp) return null;
    const date = new Date(status.timestamp);
    return Number.isNaN(date.getTime()) ? null : date.toLocaleTimeString();
  }, [status?.timestamp]);

  const handleServerAction = useCallback(
    async action => {
      setActionLoading(true);
      try {
        if (action === 'start') {
          await api.startServer();
          success('Server started successfully');
        } else if (action === 'stop') {
          await api.stopServer();
          success('Server stopped successfully');
        } else if (action === 'restart') {
          await api.restartServer();
          success('Server restart initiated');
        }
        // Data will refresh automatically via polling
      } catch (err) {
        handleError(err, `Failed to ${action} server`);
      } finally {
        setActionLoading(false);
      }
    },
    [success, handleError]
  );

  const formatUptime = uptime => {
    if (!uptime || uptime === 'UNKNOWN') return 'UNKNOWN';
    // Simple uptime formatting (can be enhanced)
    return uptime;
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl lg:text-3xl font-minecraft text-minecraft-grass-light leading-tight drop-shadow-lg">
            DASHBOARD
          </h1>
          <p className="text-[8px] font-minecraft text-minecraft-text-dark mt-2">
            AUTO-REFRESHING EVERY 5S
          </p>
        </div>
        {status && (
          <div className="flex items-center gap-2 px-4 py-2 card-minecraft">
            <div
              className={`w-3 h-3 ${status?.running ? 'bg-minecraft-grass-light' : 'bg-[#C62828]'} animate-pulse`}
              style={{ imageRendering: 'pixelated' }}
            />
            <div>
              <span className="text-[10px] font-minecraft text-minecraft-text-light block">
                {status?.running ? 'LIVE' : 'OFFLINE'}
              </span>
              {lastUpdated && (
                <span className="text-[8px] font-minecraft text-minecraft-text-dark block mt-1">
                  SYNCED {lastUpdated}
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      {pollingError && (
        <div className="card-minecraft p-4 flex items-center justify-between gap-4">
          <p className="text-[10px] font-minecraft text-red-400 leading-relaxed">
            FAILED TO LOAD DASHBOARD DATA
          </p>
          <button onClick={refetch} className="btn-minecraft-danger text-[8px] shrink-0">
            RETRY
          </button>
        </div>
      )}

      {/* Server Status */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {loading ? (
          <>
            <StatusCardSkeleton />
            <StatusCardSkeleton />
            <StatusCardSkeleton />
          </>
        ) : (
          <>
            <StatusCard
              index={0}
              title="Server Status"
              value={status?.running ? 'ONLINE' : 'OFFLINE'}
              status={status?.running ? 'success' : 'error'}
              icon={status?.running ? '🟢' : '🔴'}
              subtitle={status?.running ? 'Server is running' : 'Server is offline'}
            />
            <StatusCard
              index={1}
              title="Players Online"
              value={`${players.length}`}
              status={players.length > 0 ? 'success' : 'info'}
              icon="👥"
              subtitle={`${players.length} / 10 players`}
            />
            <StatusCard
              index={2}
              title="Uptime"
              value={formatUptime(status?.status)}
              status="info"
              icon="⏱️"
              subtitle="Server runtime"
            />
          </>
        )}
      </div>

      {/* Server Controls */}
      <div className="card-minecraft p-6">
        <h2 className="text-sm font-minecraft text-minecraft-text-light mb-6 uppercase tracking-wide flex items-center gap-2">
          <span>⚙️</span>
          SERVER CONTROLS
        </h2>
        <div className="flex flex-wrap gap-4">
          <button
            onClick={() => handleServerAction('start')}
            disabled={status?.running || actionLoading}
            className="btn-minecraft-primary text-[10px] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
          >
            {actionLoading ? '⏳ PROCESSING...' : '▶️ START SERVER'}
          </button>
          <button
            onClick={() => handleServerAction('stop')}
            disabled={!status?.running || actionLoading}
            className="btn-minecraft-danger text-[10px] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
          >
            {actionLoading ? '⏳ PROCESSING...' : '⏹️ STOP SERVER'}
          </button>
          <button
            onClick={() => handleServerAction('restart')}
            disabled={!status?.running || actionLoading}
            className="btn-minecraft text-[10px] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
          >
            {actionLoading ? '⏳ PROCESSING...' : '🔄 RESTART SERVER'}
          </button>
        </div>
      </div>

      {/* Metrics */}
      {metrics && (
        <div className="card-minecraft p-6">
          <h2 className="text-sm font-minecraft text-minecraft-text-light mb-6 uppercase tracking-wide flex items-center gap-2">
            <span>📊</span>
            SERVER METRICS
          </h2>
          <MetricsChart metrics={metrics} />
        </div>
      )}

      {/* Online Players */}
      {!loading && (
        <div className="card-minecraft p-6">
          <h2 className="text-sm font-minecraft text-minecraft-text-light mb-6 uppercase tracking-wide flex items-center gap-2">
            <span>👥</span>
            ONLINE PLAYERS ({players.length})
          </h2>
          {players.length > 0 ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {players.map((player, index) => (
                <div
                  key={player}
                  style={{ animationDelay: `${index * 60}ms` }}
                  className="card-minecraft bg-minecraft-dirt-DEFAULT p-4 text-center text-[10px] font-minecraft text-minecraft-text-light hover:border-minecraft-grass-light hover:bg-minecraft-grass-DEFAULT hover:bg-opacity-20 transition-all duration-200 hover:scale-105 hover:shadow-lg"
                >
                  <div className="text-lg mb-1">🧑</div>
                  <div className="break-words">{player}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-10 text-minecraft-text-dark text-[10px] font-minecraft">
              <div className="text-3xl mb-3 opacity-50">💤</div>
              NO PLAYERS ONLINE
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Dashboard;
