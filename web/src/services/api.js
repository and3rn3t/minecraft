import axios from 'axios';
import {
  clearAllCache,
  getCachedResponse,
  setCachedResponse,
  setPendingRequest,
  subscribeToPendingRequest,
} from '../utils/apiCache';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080/api';
const API_KEY = import.meta.env.VITE_API_KEY || localStorage.getItem('api_key');

// Create axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  // The OAuth login flow depends on the Flask session cookie surviving
  // between GET /auth/oauth/<provider>/url (which mints a one-time `state`
  // into the session) and the callback POST that verifies it -- same-origin
  // requests carry cookies automatically, but the documented dev setup
  // (Vite on :5173 calling the API on :8080) is cross-origin, where axios
  // drops cookies unless told otherwise. The API's CORS config already
  // allows credentials (see ALLOWED_ORIGINS in api/server.py), so this is
  // the other half of that.
  withCredentials: true,
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

// Helper function to make cached GET requests. `signal` lets this specific
// call stop waiting early, but never cancels the underlying network request
// on behalf of any other caller sharing it (see subscribeToPendingRequest) —
// two components polling the same endpoint can't have one's unmount cancel
// the fetch the other is still waiting on.
async function cachedGet(url, params = {}, cacheTTL = 5000, signal) {
  // Check cache first
  const cached = getCachedResponse(url, 'GET', params);
  if (cached) {
    return cached;
  }

  // Join an already in-flight request for this key, if there is one
  const joined = subscribeToPendingRequest(url, 'GET', params, signal);
  if (joined) {
    return joined;
  }

  // Nothing pending: issue the request ourselves, behind our own internal
  // controller (never an external caller's signal directly).
  const controller = new AbortController();
  const requestPromise = apiClient.get(url, { params, signal: controller.signal }).then(response => {
    // Cache successful responses
    setCachedResponse(url, 'GET', params, response.data, cacheTTL);
    return response.data;
  });

  // Track pending request, then subscribe to our own request the same way
  // any joiner would — so our own `signal` behaves consistently whether or
  // not someone else joins in before this settles.
  setPendingRequest(url, 'GET', params, requestPromise, controller);
  return subscribeToPendingRequest(url, 'GET', params, signal);
}

// Helper function to clear cache after mutations.
// Clears everything; per-pattern invalidation can be added if it's ever needed.
function invalidateCache() {
  clearAllCache();
}

export const api = {
  // Health check (no auth required, no cache)
  async getHealth() {
    const response = await apiClient.get('/health');
    return response.data;
  },

  // Server status (cached for 2 seconds)
  async getStatus(signal) {
    return cachedGet('/status', {}, 2000, signal);
  },

  // Server control (invalidate cache on state changes)
  async startServer() {
    const response = await apiClient.post('/server/start');
    invalidateCache();
    return response.data;
  },

  async stopServer() {
    const response = await apiClient.post('/server/stop');
    invalidateCache();
    return response.data;
  },

  async restartServer() {
    const response = await apiClient.post('/server/restart');
    invalidateCache();
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
    invalidateCache(); // Clear cache after creating backup
    return response.data;
  },

  async listBackups(signal) {
    return cachedGet('/backups', {}, 10000, signal); // Cache for 10 seconds
  },

  async restoreBackup(filename) {
    const response = await apiClient.post(`/backups/${filename}/restore`);
    invalidateCache(); // Clear cache after restore
    return response.data;
  },

  async deleteBackup(filename) {
    const response = await apiClient.delete(`/backups/${filename}`);
    invalidateCache(); // Clear cache after delete
    return response.data;
  },

  // Logs (cached briefly so a fast polling loop doesn't refetch identical lines)
  async getLogs(lines = 100, signal) {
    return cachedGet('/logs', { lines }, 1500, signal);
  },

  // Game events (chat, joins, deaths, advancements) parsed from the server log
  async getEvents({ limit = 100, type = null, player = null } = {}) {
    const params = { limit };
    if (type) params.type = type;
    if (player) params.player = player;
    const response = await apiClient.get('/events', { params });
    return response.data;
  },

  async getEventTypes() {
    return cachedGet('/events/types', {}, 300000);
  },

  // Bedtime mode: the countdown and its controls (cached briefly for the 15s poll)
  async getBedtime(signal) {
    return cachedGet('/bedtime', {}, 10000, signal);
  },

  async extendBedtime() {
    const response = await apiClient.post('/bedtime/extend');
    invalidateCache(); // Bedtime moved, so cached reads are stale
    return response.data;
  },

  async skipBedtime() {
    const response = await apiClient.post('/bedtime/skip');
    invalidateCache(); // Bedtime moved, so cached reads are stale
    return response.data;
  },

  async startBedtimeNow() {
    const response = await apiClient.post('/bedtime/now');
    invalidateCache(); // This can stop the server, so /status is stale too
    return response.data;
  },

  // Hall of Deaths: epitaphs, stats and the leaderboard
  async getDeaths({ limit = 50, player = null, category = null } = {}) {
    const params = { limit };
    if (player) params.player = player;
    if (category) params.category = category;
    const response = await apiClient.get('/deaths', { params });
    return response.data;
  },

  async getDeathsLeaderboard(limit = 10) {
    return cachedGet('/deaths/leaderboard', { limit }, 15000);
  },

  // Players (cached for 3 seconds)
  async getPlayers(signal) {
    return cachedGet('/players', {}, 3000, signal);
  },

  async opPlayer(player, level = 4) {
    const response = await apiClient.post('/players/op', { player, level });
    return response.data;
  },

  async deopPlayer(player) {
    const response = await apiClient.delete(`/players/op/${encodeURIComponent(player)}`);
    return response.data;
  },

  // Ops list (cached briefly so it shares the 5s poll's cadence with getPlayers)
  async getOps(signal) {
    return cachedGet('/players/ops', {}, 3000, signal);
  },

  // Metrics (cached for 2 seconds)
  async getMetrics(signal) {
    return cachedGet('/metrics', {}, 2000, signal);
  },

  // Analytics (cached for longer periods - analytics don't change frequently)
  async collectAnalytics() {
    const response = await apiClient.post('/analytics/collect');
    invalidateCache(); // Clear analytics cache after collection
    return response.data;
  },

  async getAnalyticsReport(hours = 24, signal) {
    return cachedGet('/analytics/report', { hours }, 60000, signal); // Cache for 60 seconds
  },

  async getAnalyticsTrends(hours = 24, type = 'performance', signal) {
    return cachedGet('/analytics/trends', { hours, type }, 60000, signal); // Cache for 60 seconds
  },

  async getAnalyticsAnomalies(hours = 24, metric = 'tps', signal) {
    return cachedGet('/analytics/anomalies', { hours, metric }, 60000, signal); // Cache for 60 seconds
  },

  async getAnalyticsPredictions(hoursAhead = 1, metric = 'memory', signal) {
    return cachedGet(
      '/analytics/predictions',
      { hours_ahead: hoursAhead, metric },
      60000,
      signal
    ); // Cache for 60 seconds
  },

  async getPlayerBehavior(hours = 24, signal) {
    return cachedGet('/analytics/player-behavior', { hours }, 60000, signal); // Cache for 60 seconds
  },

  async generateCustomReport(config) {
    const response = await apiClient.post('/analytics/custom-report', config);
    invalidateCache(); // Clear cache after generating report
    return response.data;
  },

  // Worlds (cached for 30 seconds - rarely changes)
  async listWorlds() {
    return cachedGet('/worlds', {}, 30000);
  },

  // Plugins (cached for 30 seconds - rarely changes)
  async listPlugins() {
    return cachedGet('/plugins', {}, 30000);
  },

  // Datapacks
  async listDatapacks() {
    return cachedGet('/datapacks', {}, 10000);
  },

  async installDatapack({ name, url, file }) {
    const formData = new FormData();
    formData.append('name', name);
    if (file) {
      formData.append('file', file);
    } else {
      formData.append('url', url);
    }
    const response = await apiClient.post('/datapacks/install', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    invalidateCache();
    return response.data;
  },

  async enableDatapack(name) {
    const response = await apiClient.put(`/datapacks/${name}/enable`);
    invalidateCache();
    return response.data;
  },

  async disableDatapack(name) {
    const response = await apiClient.put(`/datapacks/${name}/disable`);
    invalidateCache();
    return response.data;
  },

  async deleteDatapack(name) {
    const response = await apiClient.delete(`/datapacks/${name}`);
    invalidateCache();
    return response.data;
  },

  // Configuration files (cached for 30 seconds - rarely changes)
  async listConfigFiles() {
    return cachedGet('/config/files', {}, 30000);
  },

  async getConfigFile(filename) {
    return cachedGet(`/config/files/${filename}`, {}, 30000);
  },

  async saveConfigFile(filename, content) {
    const response = await apiClient.post(`/config/files/${filename}`, {
      content,
    });
    invalidateCache(); // Clear cache after saving config
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

  async login(username, password, totpToken = null) {
    const response = await apiClient.post('/auth/login', {
      username,
      password,
      totp_token: totpToken,
    });
    return response.data;
  },

  // Two-Factor Authentication
  async setup2FA() {
    const response = await apiClient.post('/auth/2fa/setup');
    return response.data;
  },

  async verify2FASetup(token) {
    const response = await apiClient.post('/auth/2fa/verify', { token });
    return response.data;
  },

  async disable2FA(password) {
    const response = await apiClient.post('/auth/2fa/disable', { password });
    return response.data;
  },

  async get2FAStatus() {
    const response = await apiClient.get('/auth/2fa/status');
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

  async googleOAuthCallback(code, redirectUri, state = null) {
    const response = await apiClient.post('/auth/oauth/google/callback', {
      code,
      redirect_uri: redirectUri,
      state,
    });
    return response.data;
  },

  async appleOAuthCallback(code, redirectUri, idToken, userData, state = null) {
    const response = await apiClient.post('/auth/oauth/apple/callback', {
      code,
      redirect_uri: redirectUri,
      id_token: idToken,
      user: userData,
      state,
    });
    return response.data;
  },

  async linkOAuthAccount(provider, code, redirectUri, idToken = null, userData = null, state = null) {
    const response = await apiClient.post(`/auth/oauth/${provider}/link`, {
      code,
      redirect_uri: redirectUri,
      id_token: idToken,
      user: userData,
      state,
    });
    return response.data;
  },

  async unlinkOAuthAccount(provider) {
    const response = await apiClient.post(`/auth/oauth/${provider}/unlink`);
    return response.data;
  },

  // API Key Management
  async listApiKeys() {
    return cachedGet('/keys', {}, 15000); // Cache for 15 seconds
  },

  async createApiKey(name, description = '', role = 'user') {
    const response = await apiClient.post('/keys', {
      name,
      description,
      role,
    });
    invalidateCache(); // Clear cache after creating key
    return response.data;
  },

  async updateApiKeyScope(keyId, role) {
    const response = await apiClient.put(`/keys/${keyId}`, { role });
    invalidateCache(); // Clear cache after re-scoping a key
    return response.data;
  },

  async deleteApiKey(keyId) {
    const response = await apiClient.delete(`/keys/${keyId}`);
    invalidateCache(); // Clear cache after deleting key
    return response.data;
  },

  async enableApiKey(keyId) {
    const response = await apiClient.put(`/keys/${keyId}/enable`);
    invalidateCache(); // Clear cache after enabling key
    return response.data;
  },

  async disableApiKey(keyId) {
    const response = await apiClient.put(`/keys/${keyId}/disable`);
    invalidateCache(); // Clear cache after disabling key
    return response.data;
  },

  // User and Role Management
  async listUsers() {
    return cachedGet('/users', {}, 15000); // Cache for 15 seconds
  },

  async updateUserRole(username, role) {
    const response = await apiClient.put(`/users/${username}/role`, { role });
    invalidateCache(); // Clear cache after role update
    return response.data;
  },

  async deleteUser(username) {
    const response = await apiClient.delete(`/users/${username}`);
    invalidateCache(); // Clear cache after deleting user
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

  // File Browser
  async listFiles(path = '') {
    const response = await apiClient.get('/files/list', {
      params: { path },
    });
    return response.data;
  },

  async readFile(path) {
    const response = await apiClient.get('/files/read', {
      params: { path },
    });
    return response.data;
  },

  async writeFile(path, content) {
    const response = await apiClient.post('/files/write', {
      path,
      content,
    });
    return response.data;
  },

  async deleteFile(path) {
    const response = await apiClient.delete('/files/delete', {
      params: { path },
    });
    return response.data;
  },

  async uploadFile(path, file) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('path', path);
    const response = await apiClient.post('/files/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  async downloadFile(path) {
    const response = await apiClient.get('/files/download', {
      params: { path },
      responseType: 'blob',
    });
    return response.data;
  },

  // Audit Logs
  async getAuditLogs(limit = 100, offset = 0, action = null, username = null) {
    const params = { limit, offset };
    if (action) params.action = action;
    if (username) params.username = username;
    const response = await apiClient.get('/audit/logs', { params });
    return response.data;
  },

  // Command Scheduler
  async listSchedules() {
    const response = await apiClient.get('/scheduler/schedules');
    return response.data;
  },

  async createSchedule(schedule) {
    const response = await apiClient.post('/scheduler/schedules', schedule);
    return response.data;
  },

  async updateSchedule(scheduleId, schedule) {
    const response = await apiClient.put(`/scheduler/schedules/${scheduleId}`, schedule);
    return response.data;
  },

  async enableSchedule(scheduleId) {
    const response = await apiClient.put(`/scheduler/schedules/${scheduleId}/enable`);
    invalidateCache();
    return response.data;
  },

  async disableSchedule(scheduleId) {
    const response = await apiClient.put(`/scheduler/schedules/${scheduleId}/disable`);
    invalidateCache();
    return response.data;
  },

  async deleteSchedule(scheduleId) {
    const response = await apiClient.delete(`/scheduler/schedules/${scheduleId}`);
    return response.data;
  },
};

export default api;
