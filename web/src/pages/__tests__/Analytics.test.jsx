import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from '../../services/api';
import { renderWithRouter } from '../../test/utils';
import Analytics from '../Analytics';

// Mock the API service
vi.mock('../../services/api', () => ({
  api: {
    collectAnalytics: vi.fn(),
    getAnalyticsReport: vi.fn(),
    getAnalyticsTrends: vi.fn(),
    getAnalyticsAnomalies: vi.fn(),
    getAnalyticsPredictions: vi.fn(),
    getPlayerBehavior: vi.fn(),
    generateCustomReport: vi.fn(),
  },
}));

describe('Analytics', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  const mockReport = {
    report: {
      generated_at: '2024-01-27T12:00:00',
      period_hours: 24,
      player_behavior: {
        unique_players: 5,
        peak_hour: 20,
        hourly_distribution: { 20: 10, 21: 8, 22: 5 },
        total_events: 15,
      },
      performance: {
        tps: {
          current: 20.0,
          average: 19.8,
          trend: { direction: 'stable', change_percent: 2.5 },
          prediction: { predicted: 20.1, confidence: 85.0 },
        },
        cpu: { current: 50.0, average: 48.0, trend: { direction: 'increasing' } },
        memory: { current: 1000, average: 950, trend: { direction: 'stable' } },
      },
      summary: {
        status: 'healthy',
        warnings: [],
        recommendations: [],
      },
    },
  };

  const mockTrends = {
    trends: {
      tps: {
        current: 20.0,
        average: 19.8,
        trend: { direction: 'stable', change_percent: 2.5 },
        prediction: { predicted: 20.1, confidence: 85.0 },
      },
      cpu: { current: 50.0, average: 48.0, trend: { direction: 'increasing' } },
      memory: { current: 1000, average: 950, trend: { direction: 'stable' } },
    },
    period_hours: 24,
  };

  const mockAnomalies = {
    anomalies: [
      {
        timestamp: 1706374800,
        datetime: '2024-01-27 13:00:00',
        value: 5.0,
        severity: 'high',
        z_score: 3.5,
        metric: 'tps',
      },
    ],
    metric: 'tps',
    period_hours: 24,
  };

  const mockPredictions = {
    prediction: {
      predicted: 1200,
      confidence: 85.0,
      trend: 100.0,
    },
    metric: 'memory',
    hours_ahead: 1,
  };

  const mockPlayerBehavior = {
    behavior: {
      unique_players: 5,
      peak_hour: 20,
      hourly_distribution: { 20: 10, 21: 8, 22: 5 },
      total_events: 15,
    },
    period_hours: 24,
  };

  it('renders analytics dashboard title', async () => {
    api.api.getAnalyticsReport.mockResolvedValue(mockReport);
    api.api.getAnalyticsTrends.mockResolvedValue(mockTrends);
    api.api.getAnalyticsAnomalies.mockResolvedValue({ anomalies: [] });
    api.api.getAnalyticsPredictions.mockResolvedValue(mockPredictions);
    api.api.getPlayerBehavior.mockResolvedValue(mockPlayerBehavior);

    renderWithRouter(<Analytics />);

    await waitFor(() => {
      expect(screen.getByText('Analytics Dashboard')).toBeInTheDocument();
    });
  });

  it('displays loading state initially', () => {
    api.api.getAnalyticsReport.mockImplementation(() => new Promise(() => {}));
    api.api.getAnalyticsTrends.mockImplementation(() => new Promise(() => {}));
    api.api.getAnalyticsAnomalies.mockImplementation(() => new Promise(() => {}));
    api.api.getAnalyticsPredictions.mockImplementation(() => new Promise(() => {}));
    api.api.getPlayerBehavior.mockImplementation(() => new Promise(() => {}));

    renderWithRouter(<Analytics />);

    // Check for loading indicators (may be in skeleton or spinner)
    const loadingElements = screen.queryAllByText(/loading/i);
    expect(loadingElements.length).toBeGreaterThan(0);
  });

  it('displays overview tab by default', async () => {
    api.api.getAnalyticsReport.mockResolvedValue(mockReport);
    api.api.getAnalyticsTrends.mockResolvedValue(mockTrends);
    api.api.getAnalyticsAnomalies.mockResolvedValue({ anomalies: [] });
    api.api.getAnalyticsPredictions.mockResolvedValue(mockPredictions);
    api.api.getPlayerBehavior.mockResolvedValue(mockPlayerBehavior);

    renderWithRouter(<Analytics />);

    await waitFor(() => {
      expect(screen.getByText('Summary')).toBeInTheDocument();
      expect(screen.getByText('HEALTHY')).toBeInTheDocument();
    });
  });

  it('displays performance metrics in overview', async () => {
    api.api.getAnalyticsReport.mockResolvedValue(mockReport);
    api.api.getAnalyticsTrends.mockResolvedValue(mockTrends);
    api.api.getAnalyticsAnomalies.mockResolvedValue({ anomalies: [] });
    api.api.getAnalyticsPredictions.mockResolvedValue(mockPredictions);
    api.api.getPlayerBehavior.mockResolvedValue(mockPlayerBehavior);

    renderWithRouter(<Analytics />);

    await waitFor(() => {
      expect(screen.getByText('Current TPS')).toBeInTheDocument();
      expect(screen.getByText('20.00')).toBeInTheDocument();
    });
  });

  it('switches to performance tab', async () => {
    api.api.getAnalyticsReport.mockResolvedValue(mockReport);
    api.api.getAnalyticsTrends.mockResolvedValue(mockTrends);
    api.api.getAnalyticsAnomalies.mockResolvedValue({ anomalies: [] });
    api.api.getAnalyticsPredictions.mockResolvedValue(mockPredictions);
    api.api.getPlayerBehavior.mockResolvedValue(mockPlayerBehavior);

    const user = userEvent.setup({ delay: null });
    renderWithRouter(<Analytics />);

    await waitFor(() => {
      expect(screen.getByText('Summary')).toBeInTheDocument();
    });

    const performanceTab = screen.getByRole('button', { name: /performance/i });
    await user.click(performanceTab);

    await waitFor(() => {
      expect(screen.getByText('TPS (Ticks Per Second)')).toBeInTheDocument();
    });
  });

  it('switches to players tab', async () => {
    api.api.getAnalyticsReport.mockResolvedValue(mockReport);
    api.api.getAnalyticsTrends.mockResolvedValue(mockTrends);
    api.api.getAnalyticsAnomalies.mockResolvedValue({ anomalies: [] });
    api.api.getAnalyticsPredictions.mockResolvedValue(mockPredictions);
    api.api.getPlayerBehavior.mockResolvedValue(mockPlayerBehavior);

    const user = userEvent.setup({ delay: null });
    renderWithRouter(<Analytics />);

    await waitFor(() => {
      expect(screen.getByText('Summary')).toBeInTheDocument();
    });

    const playersTab = screen.getByRole('button', { name: /players/i });
    await user.click(playersTab);

    await waitFor(() => {
      expect(screen.getByText('Player Behavior')).toBeInTheDocument();
      expect(screen.getByText('5')).toBeInTheDocument(); // unique_players
    });
  });

  it('switches to anomalies tab', async () => {
    api.api.getAnalyticsReport.mockResolvedValue(mockReport);
    api.api.getAnalyticsTrends.mockResolvedValue(mockTrends);
    api.api.getAnalyticsAnomalies.mockResolvedValue(mockAnomalies);
    api.api.getAnalyticsPredictions.mockResolvedValue(mockPredictions);
    api.api.getPlayerBehavior.mockResolvedValue(mockPlayerBehavior);

    const user = userEvent.setup({ delay: null });
    renderWithRouter(<Analytics />);

    await waitFor(() => {
      expect(screen.getByText('Summary')).toBeInTheDocument();
    });

    const anomaliesTab = screen.getByRole('button', { name: /anomalies/i });
    await user.click(anomaliesTab);

    await waitFor(() => {
      expect(screen.getByText('Detected Anomalies')).toBeInTheDocument();
      expect(screen.getByText('HIGH')).toBeInTheDocument();
    });
  });

  it('displays no anomalies message when none detected', async () => {
    api.api.getAnalyticsReport.mockResolvedValue(mockReport);
    api.api.getAnalyticsTrends.mockResolvedValue(mockTrends);
    api.api.getAnalyticsAnomalies.mockResolvedValue({ anomalies: [] });
    api.api.getAnalyticsPredictions.mockResolvedValue(mockPredictions);
    api.api.getPlayerBehavior.mockResolvedValue(mockPlayerBehavior);

    const user = userEvent.setup({ delay: null });
    renderWithRouter(<Analytics />);

    await waitFor(() => {
      expect(screen.getByText('Summary')).toBeInTheDocument();
    });

    const anomaliesTab = screen.getByRole('button', { name: /anomalies/i });
    await user.click(anomaliesTab);

    await waitFor(() => {
      expect(screen.getByText('No anomalies detected')).toBeInTheDocument();
    });
  });

  it('switches to predictions tab', async () => {
    api.api.getAnalyticsReport.mockResolvedValue(mockReport);
    api.api.getAnalyticsTrends.mockResolvedValue(mockTrends);
    api.api.getAnalyticsAnomalies.mockResolvedValue({ anomalies: [] });
    api.api.getAnalyticsPredictions.mockResolvedValue(mockPredictions);
    api.api.getPlayerBehavior.mockResolvedValue(mockPlayerBehavior);

    const user = userEvent.setup({ delay: null });
    renderWithRouter(<Analytics />);

    await waitFor(() => {
      expect(screen.getByText('Summary')).toBeInTheDocument();
    });

    const predictionsTab = screen.getByRole('button', { name: /predictions/i });
    await user.click(predictionsTab);

    await waitFor(() => {
      expect(screen.getByText('Resource Usage Predictions')).toBeInTheDocument();
      expect(screen.getByText('1200')).toBeInTheDocument(); // predicted value
    });
  });

  it('changes time period', async () => {
    api.api.getAnalyticsReport.mockResolvedValue(mockReport);
    api.api.getAnalyticsTrends.mockResolvedValue(mockTrends);
    api.api.getAnalyticsAnomalies.mockResolvedValue({ anomalies: [] });
    api.api.getAnalyticsPredictions.mockResolvedValue(mockPredictions);
    api.api.getPlayerBehavior.mockResolvedValue(mockPlayerBehavior);

    const user = userEvent.setup({ delay: null });
    renderWithRouter(<Analytics />);

    await waitFor(() => {
      expect(screen.getByText('Summary')).toBeInTheDocument();
    });

    const periodSelect = screen.getByDisplayValue('Last 24 Hours');
    await user.selectOptions(periodSelect, '6');

    await waitFor(() => {
      expect(api.api.getAnalyticsReport).toHaveBeenCalledWith(6);
    });
  });

  it('triggers data collection', async () => {
    api.api.getAnalyticsReport.mockResolvedValue(mockReport);
    api.api.getAnalyticsTrends.mockResolvedValue(mockTrends);
    api.api.getAnalyticsAnomalies.mockResolvedValue({ anomalies: [] });
    api.api.getAnalyticsPredictions.mockResolvedValue(mockPredictions);
    api.api.getPlayerBehavior.mockResolvedValue(mockPlayerBehavior);
    api.api.collectAnalytics.mockResolvedValue({ success: true, message: 'Data collected' });

    const user = userEvent.setup({ delay: null });
    renderWithRouter(<Analytics />);

    await waitFor(() => {
      expect(screen.getByText('Summary')).toBeInTheDocument();
    });

    const collectButton = screen.getByRole('button', { name: /collect data/i });
    await user.click(collectButton);

    await waitFor(() => {
      expect(api.api.collectAnalytics).toHaveBeenCalled();
    });
  });

  it('generates custom report', async () => {
    api.api.getAnalyticsReport.mockResolvedValue(mockReport);
    api.api.getAnalyticsTrends.mockResolvedValue(mockTrends);
    api.api.getAnalyticsAnomalies.mockResolvedValue({ anomalies: [] });
    api.api.getAnalyticsPredictions.mockResolvedValue(mockPredictions);
    api.api.getPlayerBehavior.mockResolvedValue(mockPlayerBehavior);
    api.api.generateCustomReport.mockResolvedValue({
      report: mockReport.report,
      saved_as: 'custom_report_20240127_120000.json',
    });

    const user = userEvent.setup({ delay: null });
    renderWithRouter(<Analytics />);

    await waitFor(() => {
      expect(screen.getByText('Summary')).toBeInTheDocument();
    });

    const generateButton = screen.getByRole('button', { name: /generate report/i });
    await user.click(generateButton);

    await waitFor(() => {
      expect(api.api.generateCustomReport).toHaveBeenCalledWith({
        hours: 24,
        metrics: ['performance', 'players'],
      });
    });
  });

  it('displays warnings when present', async () => {
    const reportWithWarnings = {
      ...mockReport,
      report: {
        ...mockReport.report,
        summary: {
          status: 'warning',
          warnings: ['Low TPS detected', 'High memory usage'],
          recommendations: ['Reduce view distance'],
        },
      },
    };

    api.api.getAnalyticsReport.mockResolvedValue(reportWithWarnings);
    api.api.getAnalyticsTrends.mockResolvedValue(mockTrends);
    api.api.getAnalyticsAnomalies.mockResolvedValue({ anomalies: [] });
    api.api.getAnalyticsPredictions.mockResolvedValue(mockPredictions);
    api.api.getPlayerBehavior.mockResolvedValue(mockPlayerBehavior);

    renderWithRouter(<Analytics />);

    await waitFor(() => {
      expect(screen.getByText('Warnings')).toBeInTheDocument();
      expect(screen.getByText('Low TPS detected')).toBeInTheDocument();
      expect(screen.getByText('High memory usage')).toBeInTheDocument();
    });
  });

  it('displays recommendations when present', async () => {
    const reportWithRecommendations = {
      ...mockReport,
      report: {
        ...mockReport.report,
        summary: {
          status: 'healthy',
          warnings: [],
          recommendations: ['Consider reducing view distance', 'Monitor memory usage'],
        },
      },
    };

    api.api.getAnalyticsReport.mockResolvedValue(reportWithRecommendations);
    api.api.getAnalyticsTrends.mockResolvedValue(mockTrends);
    api.api.getAnalyticsAnomalies.mockResolvedValue({ anomalies: [] });
    api.api.getAnalyticsPredictions.mockResolvedValue(mockPredictions);
    api.api.getPlayerBehavior.mockResolvedValue(mockPlayerBehavior);

    renderWithRouter(<Analytics />);

    await waitFor(() => {
      expect(screen.getByText('Recommendations')).toBeInTheDocument();
      expect(screen.getByText('Consider reducing view distance')).toBeInTheDocument();
    });
  });

  it('handles API errors gracefully', async () => {
    api.api.getAnalyticsReport.mockRejectedValue(new Error('API Error'));
    api.api.getAnalyticsTrends.mockRejectedValue(new Error('API Error'));
    api.api.getAnalyticsAnomalies.mockRejectedValue(new Error('API Error'));
    api.api.getAnalyticsPredictions.mockRejectedValue(new Error('API Error'));
    api.api.getPlayerBehavior.mockRejectedValue(new Error('API Error'));

    renderWithRouter(<Analytics />);

    // Component should still render, even with errors
    await waitFor(() => {
      expect(screen.getByText('Analytics Dashboard')).toBeInTheDocument();
    });
  });

  it('updates data periodically', async () => {
    api.api.getAnalyticsReport.mockResolvedValue(mockReport);
    api.api.getAnalyticsTrends.mockResolvedValue(mockTrends);
    api.api.getAnalyticsAnomalies.mockResolvedValue({ anomalies: [] });
    api.api.getAnalyticsPredictions.mockResolvedValue(mockPredictions);
    api.api.getPlayerBehavior.mockResolvedValue(mockPlayerBehavior);

    renderWithRouter(<Analytics />);

    await waitFor(() => {
      expect(screen.getByText('Summary')).toBeInTheDocument();
    });

    // Fast-forward time to trigger interval
    vi.advanceTimersByTime(60000);

    await waitFor(() => {
      // Should have been called multiple times (initial + interval)
      expect(api.api.getAnalyticsReport.mock.calls.length).toBeGreaterThan(1);
    });
  });
});
