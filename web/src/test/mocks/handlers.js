import { http, HttpResponse } from 'msw'

const API_BASE = 'http://localhost:8080/api'

export const handlers = [
  // Health check
  http.get(`${API_BASE}/health`, () => {
    return HttpResponse.json({
      status: 'healthy',
      timestamp: new Date().toISOString(),
      version: '1.0.0',
    })
  }),

  // Server status
  http.get(`${API_BASE}/status`, () => {
    return HttpResponse.json({
      running: true,
      status: 'Up 2 hours',
      timestamp: new Date().toISOString(),
    })
  }),

  // Server control
  http.post(`${API_BASE}/server/start`, () => {
    return HttpResponse.json({
      success: true,
      message: 'Server starting',
      output: 'Starting server...',
    })
  }),

  http.post(`${API_BASE}/server/stop`, () => {
    return HttpResponse.json({
      success: true,
      message: 'Server stopping',
      output: 'Stopping server...',
    })
  }),

  http.post(`${API_BASE}/server/restart`, () => {
    return HttpResponse.json({
      success: true,
      message: 'Server restarting',
      output: 'Restarting server...',
    })
  }),

  // Players
  http.get(`${API_BASE}/players`, () => {
    return HttpResponse.json({
      players: ['Player1', 'Player2'],
      count: 2,
    })
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
    })
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
    })
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
    })
  }),

  http.post(`${API_BASE}/backup`, () => {
    return HttpResponse.json({
      success: true,
      message: 'Backup created',
      output: 'Backup created successfully',
    })
  }),

  // Worlds
  http.get(`${API_BASE}/worlds`, () => {
    return HttpResponse.json({
      worlds: ['world', 'survival', 'creative'],
      count: 3,
    })
  }),

  // Plugins
  http.get(`${API_BASE}/plugins`, () => {
    return HttpResponse.json({
      plugins: ['EssentialsX', 'WorldEdit'],
      count: 2,
    })
  }),
]

