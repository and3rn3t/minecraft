import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import Analytics from '../../pages/Analytics';
import * as api from '../../services/api';
import { renderWithRouter } from '../utils';

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

describe('Analytics Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
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

  it('loads and displays complete analytics data', async () => {
    api.api.getAnalyticsReport.mockResolvedValue(mockReport);
    api.api.getAnalyticsTrends.mockResolvedValue({
      trends: mockReport.report.performance,
      period_hours: 24,
    });
    api.api.getAnalyticsAnomalies.mockResolvedValue({ anomalies: [] });
    api.api.getAnalyticsPredictions.mockResolvedValue({
      prediction: { predicted: 1200, confidence: 85.0, trend: 100.0 },
      metric: 'memory',
      hours_ahead: 1,
    });
    api.api.getPlayerBehavior.mockResolvedValue({
      behavior: mockReport.report.player_behavior,
      period_hours: 24,
    });

    renderWithRouter(<Analytics />);

    // Wait for all data to load
    await waitFor(() => {
      expect(screen.getByText('Analytics Dashboard')).toBeInTheDocument();
    });

    // Verify all sections are present
    await waitFor(
      () => {
        expect(screen.getByText('Summary')).toBeInTheDocument();
        expect(screen.getByText('Current TPS')).toBeInTheDocument();
        expect(screen.getByText('CPU Usage')).toBeInTheDocument();
        expect(screen.getByText('Memory Usage')).toBeInTheDocument();
        expect(screen.getByText('Unique Players')).toBeInTheDocument();
      },
      { timeout: 3000 }
    );
  });

  it('handles complete analytics workflow: collect → view → generate', async () => {
    api.api.getAnalyticsReport.mockResolvedValue(mockReport);
    api.api.getAnalyticsTrends.mockResolvedValue({
      trends: mockReport.report.performance,
      period_hours: 24,
    });
    api.api.getAnalyticsAnomalies.mockResolvedValue({ anomalies: [] });
    api.api.getAnalyticsPredictions.mockResolvedValue({
      prediction: { predicted: 1200, confidence: 85.0, trend: 100.0 },
    });
    api.api.getPlayerBehavior.mockResolvedValue({
      behavior: mockReport.report.player_behavior,
      period_hours: 24,
    });
    api.api.collectAnalytics.mockResolvedValue({ success: true, message: 'Data collected' });
    api.api.generateCustomReport.mockResolvedValue({
      report: mockReport.report,
      saved_as: 'custom_report_20240127_120000.json',
    });

    const user = userEvent.setup({ delay: null });
    renderWithRouter(<Analytics />);

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('Summary')).toBeInTheDocument();
    });

    // Step 1: Collect data
    const collectButton = screen.getByRole('button', { name: /collect data/i });
    await user.click(collectButton);

    await waitFor(() => {
      expect(api.api.collectAnalytics).toHaveBeenCalled();
    });

    // Step 2: Navigate through tabs
    const performanceTab = screen.getByRole('button', { name: /performance/i });
    await user.click(performanceTab);

    await waitFor(() => {
      expect(screen.getByText('TPS (Ticks Per Second)')).toBeInTheDocument();
    });

    const playersTab = screen.getByRole('button', { name: /players/i });
    await user.click(playersTab);

    await waitFor(() => {
      expect(screen.getByText('Player Behavior')).toBeInTheDocument();
    });

    // Step 3: Generate custom report
    const generateButton = screen.getByRole('button', { name: /generate report/i });
    await user.click(generateButton);

    await waitFor(() => {
      expect(api.api.generateCustomReport).toHaveBeenCalled();
    });
  });

  it('handles period change and data refresh', async () => {
    api.api.getAnalyticsReport.mockResolvedValue(mockReport);
    api.api.getAnalyticsTrends.mockResolvedValue({
      trends: mockReport.report.performance,
      period_hours: 24,
    });
    api.api.getAnalyticsAnomalies.mockResolvedValue({ anomalies: [] });
    api.api.getAnalyticsPredictions.mockResolvedValue({
      prediction: { predicted: 1200, confidence: 85.0 },
    });
    api.api.getPlayerBehavior.mockResolvedValue({
      behavior: mockReport.report.player_behavior,
      period_hours: 24,
    });

    const user = userEvent.setup({ delay: null });
    renderWithRouter(<Analytics />);

    await waitFor(() => {
      expect(screen.getByText('Summary')).toBeInTheDocument();
    });

    // Change period to 6 hours
    const periodSelect = screen.getByDisplayValue('Last 24 Hours');
    await user.selectOptions(periodSelect, '6');

    // Verify API was called with new period
    await waitFor(() => {
      expect(api.api.getAnalyticsReport).toHaveBeenCalledWith(6);
      expect(api.api.getAnalyticsTrends).toHaveBeenCalledWith(6, 'performance');
      expect(api.api.getAnalyticsAnomalies).toHaveBeenCalledWith(6, 'tps');
      expect(api.api.getPlayerBehavior).toHaveBeenCalledWith(6);
    });
  });

  it('displays anomalies when detected', async () => {
    const reportWithAnomalies = {
      ...mockReport,
      report: {
        ...mockReport.report,
        performance: {
          ...mockReport.report.performance,
          tps: {
            ...mockReport.report.performance.tps,
            anomalies: [
              {
                timestamp: 1706374800,
                datetime: '2024-01-27 13:00:00',
                value: 5.0,
                severity: 'high',
                z_score: 3.5,
              },
            ],
          },
        },
      },
    };

    api.api.getAnalyticsReport.mockResolvedValue(reportWithAnomalies);
    api.api.getAnalyticsTrends.mockResolvedValue({
      trends: reportWithAnomalies.report.performance,
      period_hours: 24,
    });
    api.api.getAnalyticsAnomalies.mockResolvedValue({
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
    });
    api.api.getAnalyticsPredictions.mockResolvedValue({
      prediction: { predicted: 1200, confidence: 85.0 },
    });
    api.api.getPlayerBehavior.mockResolvedValue({
      behavior: mockReport.report.player_behavior,
      period_hours: 24,
    });

    const user = userEvent.setup({ delay: null });
    renderWithRouter(<Analytics />);

    await waitFor(() => {
      expect(screen.getByText('Summary')).toBeInTheDocument();
    });

    // Navigate to anomalies tab
    const anomaliesTab = screen.getByRole('button', { name: /anomalies/i });
    await user.click(anomaliesTab);

    await waitFor(() => {
      expect(screen.getByText('Detected Anomalies')).toBeInTheDocument();
      expect(screen.getByText('HIGH')).toBeInTheDocument();
      expect(screen.getByText('5.00')).toBeInTheDocument(); // anomaly value
    });
  });
});
