import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080/api'
const API_KEY = import.meta.env.VITE_API_KEY || localStorage.getItem('api_key')

// Create axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    ...(API_KEY && { 'X-API-Key': API_KEY }),
  },
})

// Request interceptor to add API key
apiClient.interceptors.request.use((config) => {
  const key = localStorage.getItem('api_key')
  if (key) {
    config.headers['X-API-Key'] = key
  }
  return config
})

export const api = {
  // Health check (no auth required)
  async getHealth() {
    const response = await apiClient.get('/health')
    return response.data
  },

  // Server status
  async getStatus() {
    const response = await apiClient.get('/status')
    return response.data
  },

  // Server control
  async startServer() {
    const response = await apiClient.post('/server/start')
    return response.data
  },

  async stopServer() {
    const response = await apiClient.post('/server/stop')
    return response.data
  },

  async restartServer() {
    const response = await apiClient.post('/server/restart')
    return response.data
  },

  // Server commands
  async sendCommand(command) {
    const response = await apiClient.post('/server/command', { command })
    return response.data
  },

  // Backups
  async createBackup() {
    const response = await apiClient.post('/backup')
    return response.data
  },

  async listBackups() {
    const response = await apiClient.get('/backups')
    return response.data
  },

  // Logs
  async getLogs(lines = 100) {
    const response = await apiClient.get(`/logs?lines=${lines}`)
    return response.data
  },

  // Players
  async getPlayers() {
    const response = await apiClient.get('/players')
    return response.data
  },

  // Metrics
  async getMetrics() {
    const response = await apiClient.get('/metrics')
    return response.data
  },

  // Worlds
  async listWorlds() {
    const response = await apiClient.get('/worlds')
    return response.data
  },

  // Plugins
  async listPlugins() {
    const response = await apiClient.get('/plugins')
    return response.data
  },
}

export default api

