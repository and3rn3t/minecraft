import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080/api';
const API_KEY = import.meta.env.VITE_API_KEY || localStorage.getItem('api_key');

// Create axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    ...(API_KEY && { 'X-API-Key': API_KEY }),
  },
});

// Request interceptor to add API key or auth token
apiClient.interceptors.request.use(config => {
  // Check for auth token first (JWT)
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
  }

  // Fallback to API key if no token
  const key = localStorage.getItem('api_key');
  if (key && !token) {
    config.headers['X-API-Key'] = key;
  }

  return config;
});

// Response interceptor to handle auth errors
apiClient.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      // Clear auth on 401
      localStorage.removeItem('auth_token');
    }
    return Promise.reject(error);
  }
);

export const api = {
  // Health check (no auth required)
  async getHealth() {
    const response = await apiClient.get('/health');
    return response.data;
  },

  // Server status
  async getStatus() {
    const response = await apiClient.get('/status');
    return response.data;
  },

  // Server control
  async startServer() {
    const response = await apiClient.post('/server/start');
    return response.data;
  },

  async stopServer() {
    const response = await apiClient.post('/server/stop');
    return response.data;
  },

  async restartServer() {
    const response = await apiClient.post('/server/restart');
    return response.data;
  },

  // Server commands
  async sendCommand(command) {
    const response = await apiClient.post('/server/command', { command });
    return response.data;
  },

  // Backups
  async createBackup() {
    const response = await apiClient.post('/backup');
    return response.data;
  },

  async listBackups() {
    const response = await apiClient.get('/backups');
    return response.data;
  },

  async restoreBackup(filename) {
    const response = await apiClient.post(`/backups/${filename}/restore`);
    return response.data;
  },

  async deleteBackup(filename) {
    const response = await apiClient.delete(`/backups/${filename}`);
    return response.data;
  },

  // Logs
  async getLogs(lines = 100) {
    const response = await apiClient.get(`/logs?lines=${lines}`);
    return response.data;
  },

  // Players
  async getPlayers() {
    const response = await apiClient.get('/players');
    return response.data;
  },

  // Metrics
  async getMetrics() {
    const response = await apiClient.get('/metrics');
    return response.data;
  },

  // Worlds
  async listWorlds() {
    const response = await apiClient.get('/worlds');
    return response.data;
  },

  // Plugins
  async listPlugins() {
    const response = await apiClient.get('/plugins');
    return response.data;
  },

  // Configuration files
  async listConfigFiles() {
    const response = await apiClient.get('/config/files');
    return response.data;
  },

  async getConfigFile(filename) {
    const response = await apiClient.get(`/config/files/${filename}`);
    return response.data;
  },

  async saveConfigFile(filename, content) {
    const response = await apiClient.post(`/config/files/${filename}`, {
      content,
    });
    return response.data;
  },

  async validateConfigFile(filename, content) {
    const response = await apiClient.post(`/config/files/${filename}/validate`, { content });
    return response.data;
  },

  // Authentication
  async register(username, password, email = '') {
    const response = await apiClient.post('/auth/register', {
      username,
      password,
      email,
    });
    return response.data;
  },

  async login(username, password) {
    const response = await apiClient.post('/auth/login', {
      username,
      password,
    });
    return response.data;
  },

  async logout() {
    const response = await apiClient.post('/auth/logout');
    return response.data;
  },

  async getCurrentUser() {
    const response = await apiClient.get('/auth/me');
    return response.data;
  },

  // OAuth
  async getOAuthUrl(provider, redirectUri) {
    const response = await apiClient.get(`/auth/oauth/${provider}/url`, {
      params: { redirect_uri: redirectUri },
    });
    return response.data;
  },

  async googleOAuthCallback(code, redirectUri) {
    const response = await apiClient.post('/auth/oauth/google/callback', {
      code,
      redirect_uri: redirectUri,
    });
    return response.data;
  },

  async appleOAuthCallback(code, redirectUri, idToken, userData) {
    const response = await apiClient.post('/auth/oauth/apple/callback', {
      code,
      redirect_uri: redirectUri,
      id_token: idToken,
      user: userData,
    });
    return response.data;
  },

  async linkOAuthAccount(provider, code, redirectUri, idToken = null, userData = null) {
    const response = await apiClient.post(`/auth/oauth/${provider}/link`, {
      code,
      redirect_uri: redirectUri,
      id_token: idToken,
      user: userData,
    });
    return response.data;
  },

  async unlinkOAuthAccount(provider) {
    const response = await apiClient.post(`/auth/oauth/${provider}/unlink`);
    return response.data;
  },

  // API Key Management
  async listApiKeys() {
    const response = await apiClient.get('/keys');
    return response.data;
  },

  async createApiKey(name, description = '') {
    const response = await apiClient.post('/keys', {
      name,
      description,
    });
    return response.data;
  },

  async deleteApiKey(keyId) {
    const response = await apiClient.delete(`/keys/${keyId}`);
    return response.data;
  },

  async enableApiKey(keyId) {
    const response = await apiClient.put(`/keys/${keyId}/enable`);
    return response.data;
  },

  async disableApiKey(keyId) {
    const response = await apiClient.put(`/keys/${keyId}/disable`);
    return response.data;
  },

  // User and Role Management
  async listUsers() {
    const response = await apiClient.get('/users');
    return response.data;
  },

  async updateUserRole(username, role) {
    const response = await apiClient.put(`/users/${username}/role`, { role });
    return response.data;
  },

  async deleteUser(username) {
    const response = await apiClient.delete(`/users/${username}`);
    return response.data;
  },

  async enableUser(username) {
    const response = await apiClient.put(`/users/${username}/enable`);
    return response.data;
  },

  async disableUser(username) {
    const response = await apiClient.put(`/users/${username}/disable`);
    return response.data;
  },

  async getPermissions() {
    const response = await apiClient.get('/permissions');
    return response.data;
  },

  async listRoles() {
    const response = await apiClient.get('/roles');
    return response.data;
  },

  // DDNS Management
  async getDdnsStatus() {
    const response = await apiClient.get('/ddns/status');
    return response.data;
  },

  async updateDdns() {
    const response = await apiClient.post('/ddns/update');
    return response.data;
  },

  async getDdnsConfig() {
    const response = await apiClient.get('/ddns/config');
    return response.data;
  },

  async saveDdnsConfig(content) {
    const response = await apiClient.post('/ddns/config', { content });
    return response.data;
  },
};

export default api;
