import { useCallback, useEffect, useState } from 'react';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { ErrorState } from '../components/ui/Alert';
import { EmptyState } from '../components/ui/EmptyState';
import { PageHeader } from '../components/ui/PageHeader';
import { Select } from '../components/ui/FormField';
import { useToast } from '../components/ToastContainer';
import { useErrorHandler } from '../hooks/useErrorHandler';
import { usePolling } from '../hooks/usePolling';
import { api } from '../services/api';

const TABS = ['overview', 'performance', 'players', 'anomalies', 'predictions'];

const Analytics = () => {
  const [period, setPeriod] = useState(24);
  const [activeTab, setActiveTab] = useState('overview');
  const { success, error } = useToast();
  const handleError = useErrorHandler();

  // Load analytics data with polling (every minute)
  const loadAnalytics = useCallback(
    async signal => {
      const [reportData, trendsData, anomaliesData, predictionsData, behaviorData] =
        await Promise.all([
          api.getAnalyticsReport(period, signal),
          api.getAnalyticsTrends(period, 'performance', signal),
          api.getAnalyticsAnomalies(period, 'tps', signal),
          api.getAnalyticsPredictions(1, 'memory', signal),
          api.getPlayerBehavior(period, signal),
        ]);

      return {
        report: reportData.report,
        trends: trendsData.trends,
        anomalies: anomaliesData.anomalies || [],
        predictions: predictionsData.prediction,
        playerBehavior: behaviorData.behavior,
      };
    },
    [period]
  );

  const {
    data: analyticsData,
    loading,
    error: pollingError,
    refetch,
  } = usePolling(loadAnalytics, 60000, [period]);

  useEffect(() => {
    if (pollingError) {
      handleError(pollingError, 'Failed to load analytics data');
    }
  }, [pollingError, handleError]);

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

  const getStatusBadge = status => {
    switch (status) {
      case 'healthy':
        return 'success';
      case 'warning':
        return 'warning';
      case 'critical':
        return 'danger';
      default:
        return 'neutral';
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
      <div>
        <div className="skeleton mb-8 h-8 w-1/4" />
        <div className="skeleton h-64" />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="ANALYTICS DASHBOARD"
        subtitle="SERVER PERFORMANCE INSIGHTS AND PREDICTIONS"
        actions={
          <>
            <Select
              aria-label="Time period"
              value={period}
              onChange={e => setPeriod(Number(e.target.value))}
              className="w-auto"
            >
              <option value={1}>Last Hour</option>
              <option value={6}>Last 6 Hours</option>
              <option value={24}>Last 24 Hours</option>
              <option value={168}>Last Week</option>
            </Select>
            <Button variant="secondary" size="sm" onClick={handleCollectData}>
              COLLECT DATA
            </Button>
            <Button variant="primary" size="sm" onClick={handleGenerateReport}>
              GENERATE REPORT
            </Button>
          </>
        }
      />

      {pollingError && (
        <ErrorState
          message={
            pollingError?.response?.data?.error
              ? `Failed to load analytics data: ${pollingError.response.data.error}`
              : 'Failed to load analytics data.'
          }
          onRetry={refetch}
        />
      )}

      {/* Tabs */}
      <div className="mb-6 flex gap-2 border-b-2 border-minecraft-stone-dark pb-2">
        {TABS.map(tab => (
          <Button
            key={tab}
            variant={activeTab === tab ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setActiveTab(tab)}
          >
            {tab.toUpperCase()}
          </Button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && report && (
        <div className="space-y-6">
          <Card padding="lg">
            <h2 className="mb-4 text-sm font-minecraft uppercase text-minecraft-text-light">
              Summary
            </h2>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <Card padding="md">
                <div className="text-[10px] font-minecraft uppercase text-minecraft-text-dark">Status</div>
                <div className="mt-1">
                  <Badge status={getStatusBadge(report.summary?.status)}>
                    {report.summary?.status?.toUpperCase() || 'UNKNOWN'}
                  </Badge>
                </div>
              </Card>
              <Card padding="md">
                <div className="text-[10px] font-minecraft uppercase text-minecraft-text-dark">
                  Warnings
                </div>
                <div className="text-2xl font-minecraft text-minecraft-text-light">
                  {report.summary?.warnings?.length || 0}
                </div>
              </Card>
              <Card padding="md">
                <div className="text-[10px] font-minecraft uppercase text-minecraft-text-dark">
                  Recommendations
                </div>
                <div className="text-2xl font-minecraft text-minecraft-text-light">
                  {report.summary?.recommendations?.length || 0}
                </div>
              </Card>
            </div>

            {report.summary?.warnings && report.summary.warnings.length > 0 && (
              <div className="mt-4">
                <h3 className="mb-2 text-[10px] font-minecraft uppercase text-minecraft-warning-light">
                  Warnings
                </h3>
                <ul className="list-inside list-disc space-y-1 text-[10px] font-minecraft text-minecraft-text-light">
                  {report.summary.warnings.map((warning, idx) => (
                    <li key={idx}>{warning}</li>
                  ))}
                </ul>
              </div>
            )}

            {report.summary?.recommendations && report.summary.recommendations.length > 0 && (
              <div className="mt-4">
                <h3 className="mb-2 text-[10px] font-minecraft uppercase text-minecraft-success-light">
                  Recommendations
                </h3>
                <ul className="list-inside list-disc space-y-1 text-[10px] font-minecraft text-minecraft-text-light">
                  {report.summary.recommendations.map((rec, idx) => (
                    <li key={idx}>{rec}</li>
                  ))}
                </ul>
              </div>
            )}
          </Card>

          {/* Quick Stats */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
            <Card padding="md">
              <div className="text-[10px] font-minecraft uppercase text-minecraft-text-dark">
                Current TPS
              </div>
              <div className="text-2xl font-minecraft text-minecraft-text-light">
                {formatNumber(report.performance?.tps?.current || 0)}
              </div>
            </Card>
            <Card padding="md">
              <div className="text-[10px] font-minecraft uppercase text-minecraft-text-dark">CPU Usage</div>
              <div className="text-2xl font-minecraft text-minecraft-text-light">
                {formatNumber(report.performance?.cpu?.current || 0)}%
              </div>
            </Card>
            <Card padding="md">
              <div className="text-[10px] font-minecraft uppercase text-minecraft-text-dark">
                Memory Usage
              </div>
              <div className="text-2xl font-minecraft text-minecraft-text-light">
                {formatNumber(report.performance?.memory?.current || 0)} MB
              </div>
            </Card>
            <Card padding="md">
              <div className="text-[10px] font-minecraft uppercase text-minecraft-text-dark">
                Unique Players
              </div>
              <div className="text-2xl font-minecraft text-minecraft-text-light">
                {report.player_behavior?.unique_players || 0}
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* Performance Tab */}
      {activeTab === 'performance' && trends && (
        <div className="space-y-6">
          {trends.tps && (
            <Card padding="lg">
              <h2 className="mb-4 text-sm font-minecraft uppercase text-minecraft-text-light">
                TPS (Ticks Per Second)
              </h2>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div>
                  <div className="text-[10px] font-minecraft uppercase text-minecraft-text-dark">
                    Current
                  </div>
                  <div className="text-2xl font-minecraft text-minecraft-text-light">
                    {formatNumber(trends.tps.current)}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] font-minecraft uppercase text-minecraft-text-dark">Trend</div>
                  <div className="text-[10px] font-minecraft text-minecraft-text-light">
                    {getTrendIcon(trends.tps.trend?.direction)}{' '}
                    {trends.tps.trend?.direction || 'stable'}
                  </div>
                  <div className="text-[10px] font-minecraft uppercase text-minecraft-text-dark">
                    {trends.tps.trend?.change_percent > 0 ? '+' : ''}
                    {formatNumber(trends.tps.trend?.change_percent)}%
                  </div>
                </div>
              </div>
              {trends.tps.prediction && (
                <Card padding="md" className="mt-4">
                  <div className="text-[10px] font-minecraft uppercase text-minecraft-text-dark">
                    Prediction (1 hour ahead)
                  </div>
                  <div className="text-[10px] font-minecraft text-minecraft-text-light">
                    {formatNumber(trends.tps.prediction.predicted)} (confidence:{' '}
                    {formatNumber(trends.tps.prediction.confidence)}%)
                  </div>
                </Card>
              )}
            </Card>
          )}

          {trends.memory && (
            <Card padding="lg">
              <h2 className="mb-4 text-sm font-minecraft uppercase text-minecraft-text-light">
                Memory Usage
              </h2>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div>
                  <div className="text-[10px] font-minecraft uppercase text-minecraft-text-dark">
                    Current
                  </div>
                  <div className="text-2xl font-minecraft text-minecraft-text-light">
                    {formatNumber(trends.memory.current)} MB
                  </div>
                </div>
                <div>
                  <div className="text-[10px] font-minecraft uppercase text-minecraft-text-dark">Trend</div>
                  <div className="text-[10px] font-minecraft text-minecraft-text-light">
                    {getTrendIcon(trends.memory.trend?.direction)}{' '}
                    {trends.memory.trend?.direction || 'stable'}
                  </div>
                </div>
              </div>
            </Card>
          )}

          {trends.cpu && (
            <Card padding="lg">
              <h2 className="mb-4 text-sm font-minecraft uppercase text-minecraft-text-light">
                CPU Usage
              </h2>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div>
                  <div className="text-[10px] font-minecraft uppercase text-minecraft-text-dark">
                    Current
                  </div>
                  <div className="text-2xl font-minecraft text-minecraft-text-light">
                    {formatNumber(trends.cpu.current)}%
                  </div>
                </div>
                <div>
                  <div className="text-[10px] font-minecraft uppercase text-minecraft-text-dark">
                    Average
                  </div>
                  <div className="text-[10px] font-minecraft text-minecraft-text-light">
                    {formatNumber(trends.cpu.average)}%
                  </div>
                </div>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* Players Tab */}
      {activeTab === 'players' && playerBehavior && (
        <div className="space-y-6">
          <Card padding="lg">
            <h2 className="mb-4 text-sm font-minecraft uppercase text-minecraft-text-light">
              Player Behavior
            </h2>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div>
                <div className="text-[10px] font-minecraft uppercase text-minecraft-text-dark">
                  Unique Players
                </div>
                <div className="text-2xl font-minecraft text-minecraft-text-light">
                  {playerBehavior.unique_players || 0}
                </div>
              </div>
              <div>
                <div className="text-[10px] font-minecraft uppercase text-minecraft-text-dark">
                  Peak Hour
                </div>
                <div className="text-2xl font-minecraft text-minecraft-text-light">
                  {playerBehavior.peak_hour || 0}:00
                </div>
              </div>
              <div>
                <div className="text-[10px] font-minecraft uppercase text-minecraft-text-dark">
                  Total Events
                </div>
                <div className="text-2xl font-minecraft text-minecraft-text-light">
                  {playerBehavior.total_events || 0}
                </div>
              </div>
            </div>

            {playerBehavior.hourly_distribution && (
              <div className="mt-6">
                <h3 className="mb-4 text-[10px] font-minecraft uppercase text-minecraft-text-light">
                  Hourly Activity Distribution
                </h3>
                <div className="grid grid-cols-6 gap-2 sm:grid-cols-12">
                  {Object.entries(playerBehavior.hourly_distribution).map(([hour, count]) => (
                    <Card key={hour} padding="sm" className="text-center">
                      <div className="text-[8px] font-minecraft text-minecraft-text-dark">
                        {hour}:00
                      </div>
                      <div className="text-[10px] font-minecraft text-minecraft-text-light">
                        {count}
                      </div>
                    </Card>
                  ))}
                </div>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Anomalies Tab */}
      {activeTab === 'anomalies' && (
        <div className="space-y-6">
          <Card padding="lg">
            <h2 className="mb-4 text-sm font-minecraft uppercase text-minecraft-text-light">
              Detected Anomalies
            </h2>
            {anomalies.length === 0 ? (
              <EmptyState icon="✅" title="No anomalies detected" />
            ) : (
              <div className="space-y-4">
                {anomalies.map((anomaly, idx) => (
                  <Card
                    key={idx}
                    padding="md"
                    accent={anomaly.severity === 'high' ? 'bg-minecraft-danger' : 'bg-minecraft-warning'}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="text-[10px] font-minecraft text-minecraft-text-light">
                          {anomaly.metric || 'Unknown'} Anomaly
                        </div>
                        <div className="mt-1 text-[8px] font-minecraft text-minecraft-text-dark">
                          {anomaly.datetime || new Date(anomaly.timestamp * 1000).toLocaleString()}
                        </div>
                      </div>
                      <div className="text-right">
                        <Badge status={anomaly.severity === 'high' ? 'danger' : 'warning'}>
                          {anomaly.severity?.toUpperCase()}
                        </Badge>
                        <div className="mt-1 text-[8px] font-minecraft text-minecraft-text-dark">
                          Z-Score: {anomaly.z_score}
                        </div>
                      </div>
                    </div>
                    <div className="mt-2 text-[10px] font-minecraft text-minecraft-text-light">
                      Value: <span className="font-bold">{formatNumber(anomaly.value)}</span>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Predictions Tab */}
      {activeTab === 'predictions' && predictions && (
        <div className="space-y-6">
          <Card padding="lg">
            <h2 className="mb-4 text-sm font-minecraft uppercase text-minecraft-text-light">
              Resource Usage Predictions
            </h2>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <Card padding="md">
                <div className="text-[10px] font-minecraft uppercase text-minecraft-text-dark">
                  Predicted Value (1 hour ahead)
                </div>
                <div className="text-2xl font-minecraft text-minecraft-text-light">
                  {formatNumber(predictions.predicted)}
                </div>
                <div className="mt-2 text-[10px] font-minecraft uppercase text-minecraft-text-dark">
                  Confidence: {formatNumber(predictions.confidence)}%
                </div>
              </Card>
              <Card padding="md">
                <div className="text-[10px] font-minecraft uppercase text-minecraft-text-dark">Trend</div>
                <div className="text-[10px] font-minecraft text-minecraft-text-light">
                  {getTrendIcon(
                    predictions.trend > 0
                      ? 'increasing'
                      : predictions.trend < 0
                        ? 'decreasing'
                        : 'stable'
                  )}{' '}
                  {predictions.trend > 0
                    ? 'Increasing'
                    : predictions.trend < 0
                      ? 'Decreasing'
                      : 'Stable'}
                </div>
                <div className="mt-2 text-[10px] font-minecraft uppercase text-minecraft-text-dark">
                  Rate: {formatNumber(predictions.trend)}
                </div>
              </Card>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};

export default Analytics;
