import { http, HttpResponse } from 'msw';

const API_BASE = 'http://localhost:8080/api';

export const handlers = [
  // Health check
  http.get(`${API_BASE}/health`, () => {
    return HttpResponse.json({
      status: 'healthy',
      timestamp: new Date().toISOString(),
      version: '1.0.0',
    });
  }),

  // Server status
  http.get(`${API_BASE}/status`, () => {
    return HttpResponse.json({
      running: true,
      status: 'Up 2 hours',
      timestamp: new Date().toISOString(),
    });
  }),

  // Server control
  http.post(`${API_BASE}/server/start`, () => {
    return HttpResponse.json({
      success: true,
      message: 'Server starting',
      output: 'Starting server...',
    });
  }),

  http.post(`${API_BASE}/server/stop`, () => {
    return HttpResponse.json({
      success: true,
      message: 'Server stopping',
      output: 'Stopping server...',
    });
  }),

  http.post(`${API_BASE}/server/restart`, () => {
    return HttpResponse.json({
      success: true,
      message: 'Server restarting',
      output: 'Restarting server...',
    });
  }),

  // Players
  http.get(`${API_BASE}/players`, () => {
    return HttpResponse.json({
      players: ['Player1', 'Player2'],
      count: 2,
    });
  }),

  // Metrics
  http.get(`${API_BASE}/metrics`, () => {
    return HttpResponse.json({
      metrics: {
        cpu_percent: '45.2',
        memory_usage: '1.2GiB / 2.0GiB',
        memory_percent: '60.0',
      },
      timestamp: new Date().toISOString(),
    });
  }),

  // Logs
  http.get(`${API_BASE}/logs`, () => {
    return HttpResponse.json({
      logs: [
        '[10:30:00] [Server thread/INFO] Starting minecraft server',
        '[10:30:01] [Server thread/INFO] Done!',
        '[10:30:02] [Server thread/ERROR] Test error message',
      ],
      lines: 3,
    });
  }),

  // Backups
  http.get(`${API_BASE}/backups`, () => {
    return HttpResponse.json({
      backups: [
        {
          name: 'minecraft_backup_20250115_103000.tar.gz',
          size: 104857600,
          created: '2025-01-15T10:30:00Z',
        },
      ],
      count: 1,
    });
  }),

  http.post(`${API_BASE}/backup`, () => {
    return HttpResponse.json({
      success: true,
      message: 'Backup created',
      output: 'Backup created successfully',
    });
  }),

  // Worlds
  http.get(`${API_BASE}/worlds`, () => {
    return HttpResponse.json({
      worlds: ['world', 'survival', 'creative'],
      count: 3,
    });
  }),

  // Plugins
  http.get(`${API_BASE}/plugins`, () => {
    return HttpResponse.json({
      plugins: ['EssentialsX', 'WorldEdit'],
      count: 2,
    });
  }),

  // Analytics
  http.post(`${API_BASE}/analytics/collect`, () => {
    return HttpResponse.json({
      success: true,
      message: 'Analytics data collected',
    });
  }),

  http.get(`${API_BASE}/analytics/report`, () => {
    return HttpResponse.json({
      report: {
        generated_at: new Date().toISOString(),
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
    });
  }),

  http.get(`${API_BASE}/analytics/trends`, () => {
    return HttpResponse.json({
      trends: {
        tps: {
          current: 20.0,
          average: 19.8,
          trend: { direction: 'stable', change_percent: 2.5 },
        },
        cpu: { current: 50.0, average: 48.0, trend: { direction: 'increasing' } },
        memory: { current: 1000, average: 950, trend: { direction: 'stable' } },
      },
      period_hours: 24,
    });
  }),

  http.get(`${API_BASE}/analytics/anomalies`, () => {
    return HttpResponse.json({
      anomalies: [],
      metric: 'tps',
      period_hours: 24,
    });
  }),

  http.get(`${API_BASE}/analytics/predictions`, () => {
    return HttpResponse.json({
      prediction: {
        predicted: 1200,
        confidence: 85.0,
        trend: 100.0,
      },
      metric: 'memory',
      hours_ahead: 1,
    });
  }),

  http.get(`${API_BASE}/analytics/player-behavior`, () => {
    return HttpResponse.json({
      behavior: {
        unique_players: 5,
        peak_hour: 20,
        hourly_distribution: { 20: 10, 21: 8, 22: 5 },
        total_events: 15,
      },
      period_hours: 24,
    });
  }),

  http.post(`${API_BASE}/analytics/custom-report`, () => {
    return HttpResponse.json({
      report: {
        generated_at: new Date().toISOString(),
        period_hours: 24,
        requested_metrics: ['performance', 'players'],
      },
      saved_as: 'custom_report_20240127_120000.json',
    });
  }),
];
