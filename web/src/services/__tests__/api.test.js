import { beforeEach, describe, expect, it, vi } from 'vitest';

// Hoist mock instance to avoid initialization issues
const mockAxiosInstance = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  delete: vi.fn(),
  put: vi.fn(),
  interceptors: {
    request: {
      use: vi.fn(),
    },
    response: {
      use: vi.fn(),
    },
  },
}));

// Mock axios before importing api
vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => mockAxiosInstance),
  },
}));

// Import api after mocking
import { api } from '../api';

describe('API Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  describe('getHealth', () => {
    it('calls health endpoint', async () => {
      mockAxiosInstance.get.mockResolvedValue({ data: { status: 'healthy' } });

      const result = await api.getHealth();
      expect(result.status).toBe('healthy');
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/health');
    });
  });

  describe('getStatus', () => {
    it('calls status endpoint with API key', async () => {
      mockAxiosInstance.get.mockResolvedValue({
        data: { running: true },
      });

      localStorage.setItem('api_key', 'test-key');
      await api.getStatus();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/status');
    });
  });

  describe('server control', () => {
    it('startServer calls correct endpoint', async () => {
      mockAxiosInstance.post.mockResolvedValue({
        data: { success: true },
      });

      await api.startServer();
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/server/start');
    });

    it('stopServer calls correct endpoint', async () => {
      mockAxiosInstance.post.mockResolvedValue({
        data: { success: true },
      });

      await api.stopServer();
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/server/stop');
    });

    it('restartServer calls correct endpoint', async () => {
      mockAxiosInstance.post.mockResolvedValue({
        data: { success: true },
      });

      await api.restartServer();
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/server/restart');
    });
  });

  describe('sendCommand', () => {
    it('sends command with correct payload', async () => {
      mockAxiosInstance.post.mockResolvedValue({
        data: { response: 'OK' },
      });

      await api.sendCommand('list');
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/server/command', {
        command: 'list',
      });
    });
  });

  describe('backups', () => {
    it('createBackup calls correct endpoint', async () => {
      mockAxiosInstance.post.mockResolvedValue({
        data: { success: true },
      });

      await api.createBackup();
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/backup');
    });

    it('listBackups calls correct endpoint', async () => {
      mockAxiosInstance.get.mockResolvedValue({
        data: { backups: [] },
      });

      await api.listBackups();
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/backups');
    });
  });

  describe('getLogs', () => {
    it('calls logs endpoint with lines parameter', async () => {
      mockAxiosInstance.get.mockResolvedValue({
        data: { logs: [] },
      });

      await api.getLogs(100);
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/logs?lines=100');
    });
  });

  describe('getPlayers', () => {
    it('calls players endpoint', async () => {
      mockAxiosInstance.get.mockResolvedValue({
        data: { players: ['Player1'], count: 1 },
      });

      const result = await api.getPlayers();
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/players');
      expect(result.players).toEqual(['Player1']);
    });
  });

  describe('getMetrics', () => {
    it('calls metrics endpoint', async () => {
      mockAxiosInstance.get.mockResolvedValue({
        data: { metrics: { cpu_percent: '50' } },
      });

      const result = await api.getMetrics();
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/metrics');
      expect(result.metrics.cpu_percent).toBe('50');
    });
  });

  describe('listWorlds', () => {
    it('calls worlds endpoint', async () => {
      mockAxiosInstance.get.mockResolvedValue({
        data: { worlds: ['world'], count: 1 },
      });

      const result = await api.listWorlds();
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/worlds');
      expect(result.worlds).toEqual(['world']);
    });
  });

  describe('listPlugins', () => {
    it('calls plugins endpoint', async () => {
      mockAxiosInstance.get.mockResolvedValue({
        data: { plugins: ['Plugin1'], count: 1 },
      });

      const result = await api.listPlugins();
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/plugins');
      expect(result.plugins).toEqual(['Plugin1']);
    });
  });

  describe('config files', () => {
    it('listConfigFiles calls correct endpoint', async () => {
      mockAxiosInstance.get.mockResolvedValue({
        data: { files: [{ name: 'server.properties' }] },
      });

      const result = await api.listConfigFiles();
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/config/files');
      expect(result.files).toHaveLength(1);
    });

    it('getConfigFile calls correct endpoint', async () => {
      mockAxiosInstance.get.mockResolvedValue({
        data: { name: 'server.properties', content: '# config' },
      });

      const result = await api.getConfigFile('server.properties');
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/config/files/server.properties');
      expect(result.content).toBe('# config');
    });

    it('saveConfigFile calls correct endpoint with content', async () => {
      mockAxiosInstance.post.mockResolvedValue({
        data: { success: true },
      });

      await api.saveConfigFile('server.properties', '# new config');
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/config/files/server.properties', {
        content: '# new config',
      });
    });

    it('validateConfigFile calls correct endpoint', async () => {
      mockAxiosInstance.post.mockResolvedValue({
        data: { valid: true, errors: [] },
      });

      const result = await api.validateConfigFile('server.properties', '# config');
      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        '/config/files/server.properties/validate',
        { content: '# config' }
      );
      expect(result.valid).toBe(true);
    });
  });

  describe('backup management', () => {
    it('restoreBackup calls correct endpoint', async () => {
      mockAxiosInstance.post.mockResolvedValue({
        data: { success: true },
      });

      await api.restoreBackup('backup.tar.gz');
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/backups/backup.tar.gz/restore');
    });

    it('deleteBackup calls correct endpoint', async () => {
      mockAxiosInstance.delete.mockResolvedValue({
        data: { success: true },
      });

      await api.deleteBackup('backup.tar.gz');
      expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/backups/backup.tar.gz');
    });
  });

  describe('authentication', () => {
    it('register calls correct endpoint', async () => {
      mockAxiosInstance.post.mockResolvedValue({
        data: { success: true, user: { username: 'testuser' }, token: 'token123' },
      });

      const result = await api.register('testuser', 'password123', 'test@example.com');
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/auth/register', {
        username: 'testuser',
        password: 'password123',
        email: 'test@example.com',
      });
      expect(result.success).toBe(true);
    });

    it('login calls correct endpoint', async () => {
      mockAxiosInstance.post.mockResolvedValue({
        data: { success: true, user: { username: 'testuser' }, token: 'token123' },
      });

      const result = await api.login('testuser', 'password123');
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/auth/login', {
        username: 'testuser',
        password: 'password123',
        totp_token: null,
      });
      expect(result.success).toBe(true);
    });

    it('logout calls correct endpoint', async () => {
      mockAxiosInstance.post.mockResolvedValue({
        data: { success: true },
      });

      await api.logout();
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/auth/logout');
    });

    it('getCurrentUser calls correct endpoint', async () => {
      mockAxiosInstance.get.mockResolvedValue({
        data: { username: 'testuser', role: 'admin' },
      });

      const result = await api.getCurrentUser();
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/auth/me');
      expect(result.username).toBe('testuser');
    });
  });

  describe('OAuth', () => {
    it('getOAuthUrl calls correct endpoint', async () => {
      mockAxiosInstance.get.mockResolvedValue({
        data: { url: 'https://accounts.google.com/oauth2/auth' },
      });

      const result = await api.getOAuthUrl('google', 'http://localhost/oauth/callback');
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/auth/oauth/google/url', {
        params: { redirect_uri: 'http://localhost/oauth/callback' },
      });
      expect(result.url).toContain('google.com');
    });

    it('linkOAuthAccount calls correct endpoint', async () => {
      mockAxiosInstance.post.mockResolvedValue({
        data: { success: true },
      });

      await api.linkOAuthAccount('google', 'code123', 'http://localhost/oauth/callback');
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/auth/oauth/google/link', {
        code: 'code123',
        redirect_uri: 'http://localhost/oauth/callback',
        id_token: null,
        user: null,
      });
    });

    it('unlinkOAuthAccount calls correct endpoint', async () => {
      mockAxiosInstance.post.mockResolvedValue({
        data: { success: true },
      });

      await api.unlinkOAuthAccount('google');
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/auth/oauth/google/unlink');
    });
  });
});
