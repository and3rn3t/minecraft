import { useCallback, useState } from 'react';
import { useToast } from '../components/ToastContainer';
import { useErrorHandler } from '../hooks/useErrorHandler';
import { usePolling } from '../hooks/usePolling';
import { api } from '../services/api';

const Analytics = () => {
  const [period, setPeriod] = useState(24);
  const [activeTab, setActiveTab] = useState('overview');
  const { success, error } = useToast();
  const handleError = useErrorHandler();

  // Load analytics data with polling (every minute)
  const loadAnalytics = useCallback(async () => {
    const [reportData, trendsData, anomaliesData, predictionsData, behaviorData] =
      await Promise.all([
        api.getAnalyticsReport(period),
        api.getAnalyticsTrends(period, 'performance'),
        api.getAnalyticsAnomalies(period, 'tps'),
        api.getAnalyticsPredictions(1, 'memory'),
        api.getPlayerBehavior(period),
      ]);

    return {
      report: reportData.report,
      trends: trendsData.trends,
      anomalies: anomaliesData.anomalies || [],
      predictions: predictionsData.prediction,
      playerBehavior: behaviorData.behavior,
    };
  }, [period]);

  const { data: analyticsData, loading } = usePolling(loadAnalytics, 60000, [period]);

  const report = analyticsData?.report || null;
  const trends = analyticsData?.trends || null;
  const anomalies = analyticsData?.anomalies || [];
  const predictions = analyticsData?.predictions || null;
  const playerBehavior = analyticsData?.playerBehavior || null;

  const handleCollectData = useCallback(async () => {
    try {
      await api.collectAnalytics();
      success('Analytics data collected successfully');
      // Data will refresh automatically via polling
    } catch (err) {
      handleError(err, 'Failed to collect analytics data');
    }
  }, [success, handleError]);

  const handleGenerateReport = async () => {
    try {
      const config = {
        hours: period,
        metrics: ['performance', 'players'],
      };
      const result = await api.generateCustomReport(config);
      success(`Custom report generated: ${result.saved_as}`);
    } catch (err) {
      error('Failed to generate custom report');
    }
  };

  const formatNumber = num => {
    if (num === null || num === undefined) return 'N/A';
    return typeof num === 'number' ? num.toFixed(2) : num;
  };

  const getStatusColor = status => {
    switch (status) {
      case 'healthy':
        return 'text-green-500';
      case 'warning':
        return 'text-yellow-500';
      case 'critical':
        return 'text-red-500';
      default:
        return 'text-gray-500';
    }
  };

  const getTrendIcon = direction => {
    switch (direction) {
      case 'increasing':
        return '↗';
      case 'decreasing':
        return '↘';
      default:
        return '→';
    }
  };

  if (loading && !report) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-700 rounded w-1/4"></div>
          <div className="h-64 bg-gray-700 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Analytics Dashboard</h1>
          <p className="text-gray-400">Server performance insights and predictions</p>
        </div>
        <div className="flex gap-2">
          <select
            value={period}
            onChange={e => setPeriod(Number(e.target.value))}
            className="bg-gray-800 text-white px-4 py-2 rounded border border-gray-700"
          >
            <option value={1}>Last Hour</option>
            <option value={6}>Last 6 Hours</option>
            <option value={24}>Last 24 Hours</option>
            <option value={168}>Last Week</option>
          </select>
          <button
            onClick={handleCollectData}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
          >
            Collect Data
          </button>
          <button
            onClick={handleGenerateReport}
            className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded"
          >
            Generate Report
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-700">
        <nav className="flex space-x-8">
          {['overview', 'performance', 'players', 'anomalies', 'predictions'].map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-4 px-1 border-b-2 font-medium text-sm capitalize ${
                activeTab === tab
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-gray-400 hover:text-gray-300 hover:border-gray-300'
              }`}
            >
              {tab}
            </button>
          ))}
        </nav>
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && report && (
        <div className="space-y-6">
          {/* Summary */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-bold text-white mb-4">Summary</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-gray-900 rounded p-4">
                <div className="text-gray-400 text-sm">Status</div>
                <div className={`text-2xl font-bold ${getStatusColor(report.summary?.status)}`}>
                  {report.summary?.status?.toUpperCase() || 'UNKNOWN'}
                </div>
              </div>
              <div className="bg-gray-900 rounded p-4">
                <div className="text-gray-400 text-sm">Warnings</div>
                <div className="text-2xl font-bold text-white">
                  {report.summary?.warnings?.length || 0}
                </div>
              </div>
              <div className="bg-gray-900 rounded p-4">
                <div className="text-gray-400 text-sm">Recommendations</div>
                <div className="text-2xl font-bold text-white">
                  {report.summary?.recommendations?.length || 0}
                </div>
              </div>
            </div>

            {report.summary?.warnings && report.summary.warnings.length > 0 && (
              <div className="mt-4">
                <h3 className="text-lg font-semibold text-yellow-500 mb-2">Warnings</h3>
                <ul className="list-disc list-inside space-y-1 text-gray-300">
                  {report.summary.warnings.map((warning, idx) => (
                    <li key={idx}>{warning}</li>
                  ))}
                </ul>
              </div>
            )}

            {report.summary?.recommendations && report.summary.recommendations.length > 0 && (
              <div className="mt-4">
                <h3 className="text-lg font-semibold text-green-500 mb-2">Recommendations</h3>
                <ul className="list-disc list-inside space-y-1 text-gray-300">
                  {report.summary.recommendations.map((rec, idx) => (
                    <li key={idx}>{rec}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-gray-800 rounded-lg p-4">
              <div className="text-gray-400 text-sm">Current TPS</div>
              <div className="text-2xl font-bold text-white">
                {formatNumber(report.performance?.tps?.current || 0)}
              </div>
            </div>
            <div className="bg-gray-800 rounded-lg p-4">
              <div className="text-gray-400 text-sm">CPU Usage</div>
              <div className="text-2xl font-bold text-white">
                {formatNumber(report.performance?.cpu?.current || 0)}%
              </div>
            </div>
            <div className="bg-gray-800 rounded-lg p-4">
              <div className="text-gray-400 text-sm">Memory Usage</div>
              <div className="text-2xl font-bold text-white">
                {formatNumber(report.performance?.memory?.current || 0)} MB
              </div>
            </div>
            <div className="bg-gray-800 rounded-lg p-4">
              <div className="text-gray-400 text-sm">Unique Players</div>
              <div className="text-2xl font-bold text-white">
                {report.player_behavior?.unique_players || 0}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Performance Tab */}
      {activeTab === 'performance' && trends && (
        <div className="space-y-6">
          {trends.tps && (
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-xl font-bold text-white mb-4">TPS (Ticks Per Second)</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <div className="text-gray-400 text-sm">Current</div>
                  <div className="text-3xl font-bold text-white">
                    {formatNumber(trends.tps.current)}
                  </div>
                </div>
                <div>
                  <div className="text-gray-400 text-sm">Trend</div>
                  <div className="text-2xl font-bold text-white">
                    {getTrendIcon(trends.tps.trend?.direction)}{' '}
                    {trends.tps.trend?.direction || 'stable'}
                  </div>
                  <div className="text-gray-400 text-sm">
                    {trends.tps.trend?.change_percent > 0 ? '+' : ''}
                    {formatNumber(trends.tps.trend?.change_percent)}%
                  </div>
                </div>
              </div>
              {trends.tps.prediction && (
                <div className="mt-4 p-4 bg-gray-900 rounded">
                  <div className="text-gray-400 text-sm">Prediction (1 hour ahead)</div>
                  <div className="text-xl font-bold text-white">
                    {formatNumber(trends.tps.prediction.predicted)} (confidence:{' '}
                    {formatNumber(trends.tps.prediction.confidence)}%)
                  </div>
                </div>
              )}
            </div>
          )}

          {trends.memory && (
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-xl font-bold text-white mb-4">Memory Usage</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <div className="text-gray-400 text-sm">Current</div>
                  <div className="text-3xl font-bold text-white">
                    {formatNumber(trends.memory.current)} MB
                  </div>
                </div>
                <div>
                  <div className="text-gray-400 text-sm">Trend</div>
                  <div className="text-2xl font-bold text-white">
                    {getTrendIcon(trends.memory.trend?.direction)}{' '}
                    {trends.memory.trend?.direction || 'stable'}
                  </div>
                </div>
              </div>
            </div>
          )}

          {trends.cpu && (
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-xl font-bold text-white mb-4">CPU Usage</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <div className="text-gray-400 text-sm">Current</div>
                  <div className="text-3xl font-bold text-white">
                    {formatNumber(trends.cpu.current)}%
                  </div>
                </div>
                <div>
                  <div className="text-gray-400 text-sm">Average</div>
                  <div className="text-2xl font-bold text-white">
                    {formatNumber(trends.cpu.average)}%
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Players Tab */}
      {activeTab === 'players' && playerBehavior && (
        <div className="space-y-6">
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-bold text-white mb-4">Player Behavior</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <div className="text-gray-400 text-sm">Unique Players</div>
                <div className="text-3xl font-bold text-white">
                  {playerBehavior.unique_players || 0}
                </div>
              </div>
              <div>
                <div className="text-gray-400 text-sm">Peak Hour</div>
                <div className="text-3xl font-bold text-white">
                  {playerBehavior.peak_hour || 0}:00
                </div>
              </div>
              <div>
                <div className="text-gray-400 text-sm">Total Events</div>
                <div className="text-3xl font-bold text-white">
                  {playerBehavior.total_events || 0}
                </div>
              </div>
            </div>

            {playerBehavior.hourly_distribution && (
              <div className="mt-6">
                <h3 className="text-lg font-semibold text-white mb-4">
                  Hourly Activity Distribution
                </h3>
                <div className="grid grid-cols-12 gap-2">
                  {Object.entries(playerBehavior.hourly_distribution).map(([hour, count]) => (
                    <div key={hour} className="bg-gray-900 rounded p-2 text-center">
                      <div className="text-xs text-gray-400">{hour}:00</div>
                      <div className="text-sm font-bold text-white">{count}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Anomalies Tab */}
      {activeTab === 'anomalies' && (
        <div className="space-y-6">
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-bold text-white mb-4">Detected Anomalies</h2>
            {anomalies.length === 0 ? (
              <div className="text-gray-400 text-center py-8">No anomalies detected</div>
            ) : (
              <div className="space-y-4">
                {anomalies.map((anomaly, idx) => (
                  <div
                    key={idx}
                    className={`bg-gray-900 rounded p-4 border-l-4 ${
                      anomaly.severity === 'high' ? 'border-red-500' : 'border-yellow-500'
                    }`}
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="text-white font-semibold">
                          {anomaly.metric || 'Unknown'} Anomaly
                        </div>
                        <div className="text-gray-400 text-sm mt-1">
                          {anomaly.datetime || new Date(anomaly.timestamp * 1000).toLocaleString()}
                        </div>
                      </div>
                      <div className="text-right">
                        <div
                          className={`text-lg font-bold ${
                            anomaly.severity === 'high' ? 'text-red-500' : 'text-yellow-500'
                          }`}
                        >
                          {anomaly.severity?.toUpperCase()}
                        </div>
                        <div className="text-gray-400 text-sm">Z-Score: {anomaly.z_score}</div>
                      </div>
                    </div>
                    <div className="mt-2 text-gray-300">
                      Value: <span className="font-semibold">{formatNumber(anomaly.value)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Predictions Tab */}
      {activeTab === 'predictions' && predictions && (
        <div className="space-y-6">
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-bold text-white mb-4">Resource Usage Predictions</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-gray-900 rounded p-4">
                <div className="text-gray-400 text-sm">Predicted Value (1 hour ahead)</div>
                <div className="text-3xl font-bold text-white">
                  {formatNumber(predictions.predicted)}
                </div>
                <div className="text-gray-400 text-sm mt-2">
                  Confidence: {formatNumber(predictions.confidence)}%
                </div>
              </div>
              <div className="bg-gray-900 rounded p-4">
                <div className="text-gray-400 text-sm">Trend</div>
                <div className="text-2xl font-bold text-white">
                  {getTrendIcon(
                    predictions.trend > 0
                      ? 'increasing'
                      : predictions.trend < 0
                        ? 'decreasing'
                        : 'stable'
                  )}
                  {predictions.trend > 0
                    ? 'Increasing'
                    : predictions.trend < 0
                      ? 'Decreasing'
                      : 'Stable'}
                </div>
                <div className="text-gray-400 text-sm mt-2">
                  Rate: {formatNumber(predictions.trend)}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Analytics;
