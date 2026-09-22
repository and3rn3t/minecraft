import { useCallback, useEffect, useMemo, useState } from 'react';
import { StatusCardSkeleton } from '../components/LoadingSkeleton';
import MetricsChart from '../components/MetricsChart';
import StatusCard from '../components/StatusCard';
import { useToast } from '../components/ToastContainer';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { ErrorState } from '../components/ui/Alert';
import { PageHeader } from '../components/ui/PageHeader';
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
    <div className="animate-fadeIn space-y-6">
      <PageHeader
        title="DASHBOARD"
        subtitle="AUTO-REFRESHING EVERY 5S"
        actions={
          status && (
            <Card padding="sm" className="flex items-center gap-2 px-4 py-2">
              <div
                className={`h-3 w-3 ${status?.running ? 'bg-minecraft-grass-light' : 'bg-minecraft-danger'} animate-pulse`}
                style={{ imageRendering: 'pixelated' }}
              />
              <div>
                <span className="block text-[10px] font-minecraft text-minecraft-text-light">
                  {status?.running ? 'LIVE' : 'OFFLINE'}
                </span>
                {lastUpdated && (
                  <span className="mt-1 block text-[8px] font-minecraft text-minecraft-text-dark">
                    SYNCED {lastUpdated}
                  </span>
                )}
              </div>
            </Card>
          )
        }
      />

      {pollingError && <ErrorState message="Failed to load dashboard data" onRetry={refetch} />}

      {/* Server Status */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
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
      <Card padding="lg">
        <h2 className="mb-6 flex items-center gap-2 text-sm font-minecraft uppercase tracking-wide text-minecraft-text-light">
          <span>⚙️</span>
          SERVER CONTROLS
        </h2>
        <div className="flex flex-wrap gap-4">
          <Button
            variant="primary"
            onClick={() => handleServerAction('start')}
            disabled={status?.running || actionLoading}
          >
            {actionLoading ? '⏳ PROCESSING...' : '▶️ START SERVER'}
          </Button>
          <Button
            variant="danger"
            onClick={() => handleServerAction('stop')}
            disabled={!status?.running || actionLoading}
          >
            {actionLoading ? '⏳ PROCESSING...' : '⏹️ STOP SERVER'}
          </Button>
          <Button
            variant="secondary"
            onClick={() => handleServerAction('restart')}
            disabled={!status?.running || actionLoading}
          >
            {actionLoading ? '⏳ PROCESSING...' : '🔄 RESTART SERVER'}
          </Button>
        </div>
      </Card>

      {/* Metrics */}
      {metrics && (
        <Card padding="lg">
          <h2 className="mb-6 flex items-center gap-2 text-sm font-minecraft uppercase tracking-wide text-minecraft-text-light">
            <span>📊</span>
            SERVER METRICS
          </h2>
          <MetricsChart metrics={metrics} />
        </Card>
      )}

      {/* Online Players */}
      {!loading && (
        <Card padding="lg">
          <h2 className="mb-6 flex items-center gap-2 text-sm font-minecraft uppercase tracking-wide text-minecraft-text-light">
            <span>👥</span>
            ONLINE PLAYERS ({players.length})
          </h2>
          {players.length > 0 ? (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
              {players.map((player, index) => (
                <Card
                  key={player}
                  padding="md"
                  style={{ animationDelay: `${index * 60}ms` }}
                  className="bg-minecraft-dirt text-center text-[10px] font-minecraft text-minecraft-text-light transition-all duration-200 hover:scale-105 hover:border-minecraft-grass-light hover:bg-minecraft-grass hover:bg-opacity-20 hover:shadow-lg"
                >
                  <div className="mb-1 text-lg">🧑</div>
                  <div className="break-words">{player}</div>
                </Card>
              ))}
            </div>
          ) : (
            <div className="py-10 text-center text-[10px] font-minecraft text-minecraft-text-dark">
              <div className="mb-3 text-3xl opacity-50">💤</div>
              NO PLAYERS ONLINE
            </div>
          )}
        </Card>
      )}
    </div>
  );
};

export default Dashboard;
