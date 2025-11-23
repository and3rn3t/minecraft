import { useEffect, useState } from 'react';
import MetricsChart from '../components/MetricsChart';
import StatusCard from '../components/StatusCard';
import { api } from '../services/api';

const Dashboard = () => {
  const [status, setStatus] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [players, setPlayers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000); // Update every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const [statusData, metricsData, playersData] = await Promise.all([
        api.getStatus(),
        api.getMetrics(),
        api.getPlayers(),
      ]);
      setStatus(statusData);
      setMetrics(metricsData);
      setPlayers(playersData.players || []);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleServerAction = async action => {
    try {
      if (action === 'start') {
        await api.startServer();
      } else if (action === 'stop') {
        await api.stopServer();
      } else if (action === 'restart') {
        await api.restartServer();
      }
      setTimeout(loadData, 2000); // Reload after action
    } catch (error) {
      console.error(`Failed to ${action} server:`, error);
      alert(`Failed to ${action} server: ${error.message}`);
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
        DASHBOARD
      </h1>

      {/* Server Status */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <StatusCard
          title="Server Status"
          value={status?.running ? 'ONLINE' : 'OFFLINE'}
          status={status?.running ? 'success' : 'error'}
          icon="🟢"
        />
        <StatusCard
          title="Players Online"
          value={`${players.length} / 10`}
          status="info"
          icon="👥"
        />
        <StatusCard title="Uptime" value={status?.status || 'UNKNOWN'} status="info" icon="⏱️" />
      </div>

      {/* Server Controls */}
      <div className="card-minecraft p-6 mb-8">
        <h2 className="text-sm font-minecraft text-minecraft-text-light mb-4 uppercase">
          SERVER CONTROLS
        </h2>
        <div className="flex gap-4">
          <button
            onClick={() => handleServerAction('start')}
            disabled={status?.running}
            className="btn-minecraft-primary text-[10px] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            START SERVER
          </button>
          <button
            onClick={() => handleServerAction('stop')}
            disabled={!status?.running}
            className="btn-minecraft-danger text-[10px] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            STOP SERVER
          </button>
          <button
            onClick={() => handleServerAction('restart')}
            disabled={!status?.running}
            className="btn-minecraft text-[10px] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            RESTART SERVER
          </button>
        </div>
      </div>

      {/* Metrics */}
      {metrics && (
        <div className="card-minecraft p-6">
          <h2 className="text-sm font-minecraft text-minecraft-text-light mb-4 uppercase">
            SERVER METRICS
          </h2>
          <MetricsChart metrics={metrics} />
        </div>
      )}

      {/* Online Players */}
      {players.length > 0 && (
        <div className="card-minecraft p-6 mt-8">
          <h2 className="text-sm font-minecraft text-minecraft-text-light mb-4 uppercase">
            ONLINE PLAYERS
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {players.map((player, index) => (
              <div
                key={index}
                className="bg-minecraft-dirt-DEFAULT border-2 border-[#5D4037] p-3 text-center text-[10px] font-minecraft text-minecraft-text-light"
              >
                {player}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
