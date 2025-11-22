import { describe, it, expect, vi, beforeEach } from 'vitest'

// Hoist mock instance to avoid initialization issues
const mockAxiosInstance = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  interceptors: {
    request: {
      use: vi.fn(),
    },
  },
}))

// Mock axios before importing api
vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => mockAxiosInstance),
  },
}))

// Import api after mocking
import { api } from '../api'

describe('API Service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  describe('getHealth', () => {
    it('calls health endpoint', async () => {
      mockAxiosInstance.get.mockResolvedValue({ data: { status: 'healthy' } })

      const result = await api.getHealth()
      expect(result.status).toBe('healthy')
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/health')
    })
  })

  describe('getStatus', () => {
    it('calls status endpoint with API key', async () => {
      mockAxiosInstance.get.mockResolvedValue({
        data: { running: true },
      })

      localStorage.setItem('api_key', 'test-key')
      await api.getStatus()

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/status')
    })
  })

  describe('server control', () => {
    it('startServer calls correct endpoint', async () => {
      mockAxiosInstance.post.mockResolvedValue({
        data: { success: true },
      })

      await api.startServer()
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/server/start')
    })

    it('stopServer calls correct endpoint', async () => {
      mockAxiosInstance.post.mockResolvedValue({
        data: { success: true },
      })

      await api.stopServer()
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/server/stop')
    })

    it('restartServer calls correct endpoint', async () => {
      mockAxiosInstance.post.mockResolvedValue({
        data: { success: true },
      })

      await api.restartServer()
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/server/restart')
    })
  })

  describe('sendCommand', () => {
    it('sends command with correct payload', async () => {
      mockAxiosInstance.post.mockResolvedValue({
        data: { response: 'OK' },
      })

      await api.sendCommand('list')
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/server/command', {
        command: 'list',
      })
    })
  })

  describe('backups', () => {
    it('createBackup calls correct endpoint', async () => {
      mockAxiosInstance.post.mockResolvedValue({
        data: { success: true },
      })

      await api.createBackup()
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/backup')
    })

    it('listBackups calls correct endpoint', async () => {
      mockAxiosInstance.get.mockResolvedValue({
        data: { backups: [] },
      })

      await api.listBackups()
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/backups')
    })
  })

  describe('getLogs', () => {
    it('calls logs endpoint with lines parameter', async () => {
      mockAxiosInstance.get.mockResolvedValue({
        data: { logs: [] },
      })

      await api.getLogs(100)
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/logs?lines=100')
    })
  })

  describe('getPlayers', () => {
    it('calls players endpoint', async () => {
      mockAxiosInstance.get.mockResolvedValue({
        data: { players: ['Player1'], count: 1 },
      })

      const result = await api.getPlayers()
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/players')
      expect(result.players).toEqual(['Player1'])
    })
  })

  describe('getMetrics', () => {
    it('calls metrics endpoint', async () => {
      mockAxiosInstance.get.mockResolvedValue({
        data: { metrics: { cpu_percent: '50' } },
      })

      const result = await api.getMetrics()
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/metrics')
      expect(result.metrics.cpu_percent).toBe('50')
    })
  })

  describe('listWorlds', () => {
    it('calls worlds endpoint', async () => {
      mockAxiosInstance.get.mockResolvedValue({
        data: { worlds: ['world'], count: 1 },
      })

      const result = await api.listWorlds()
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/worlds')
      expect(result.worlds).toEqual(['world'])
    })
  })

  describe('listPlugins', () => {
    it('calls plugins endpoint', async () => {
      mockAxiosInstance.get.mockResolvedValue({
        data: { plugins: ['Plugin1'], count: 1 },
      })

      const result = await api.listPlugins()
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/plugins')
      expect(result.plugins).toEqual(['Plugin1'])
    })
  })
})
