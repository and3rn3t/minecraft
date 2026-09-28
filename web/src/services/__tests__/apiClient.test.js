import { beforeEach, describe, expect, it, vi } from 'vitest';

// The axios instance api.js builds, and what it registers on it. api.test.js
// covers each endpoint; this file covers the machinery every endpoint shares.
const mockAxiosInstance = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  delete: vi.fn(),
  put: vi.fn(),
  interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
}));
const create = vi.hoisted(() => vi.fn(() => mockAxiosInstance));

vi.mock('axios', () => ({ default: { create } }));

import { clearAllCache } from '../../utils/apiCache';
import { api } from '../api';

// Captured once: beforeEach's clearAllMocks would wipe the calls
const clientConfig = create.mock.calls[0][0];
const addAuth = mockAxiosInstance.interceptors.request.use.mock.calls[0][0];
const [passResponse, handleError] = mockAxiosInstance.interceptors.response.use.mock.calls[0];

describe('api client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    clearAllCache();
  });

  it('sends cookies, so the OAuth state survives a cross-origin dev setup', () => {
    expect(clientConfig).toMatchObject({ withCredentials: true, timeout: 15000 });
    expect(clientConfig.headers['Content-Type']).toBe('application/json');
  });

  describe('request interceptor', () => {
    it('sends the signed-in token as a Bearer credential', () => {
      localStorage.setItem('auth_token', 'jwt');
      localStorage.setItem('api_key', 'key');

      const config = addAuth({ headers: {} });

      expect(config.headers).toEqual({ Authorization: 'Bearer jwt' });
    });

    it('falls back to a saved API key', () => {
      localStorage.setItem('api_key', 'key');

      expect(addAuth({ headers: {} }).headers).toEqual({ 'X-API-Key': 'key' });
    });

    it('adds nothing when signed out', () => {
      expect(addAuth({ headers: {} }).headers).toEqual({});
    });
  });

  describe('response interceptor', () => {
    it('passes successful responses through', () => {
      const response = { data: 1 };
      expect(passResponse(response)).toBe(response);
    });

    it('drops the stored token on a 401', async () => {
      localStorage.setItem('auth_token', 'expired');
      const error = { response: { status: 401 } };

      await expect(handleError(error)).rejects.toBe(error);
      expect(localStorage.getItem('auth_token')).toBeNull();
    });

    it('keeps the token for other failures', async () => {
      localStorage.setItem('auth_token', 'fine');

      await expect(handleError({ response: { status: 500 } })).rejects.toBeTruthy();
      await expect(handleError(new Error('Network Error'))).rejects.toBeTruthy();
      expect(localStorage.getItem('auth_token')).toBe('fine');
    });
  });

  describe('cached reads', () => {
    it('serve a repeat call from cache', async () => {
      mockAxiosInstance.get.mockResolvedValue({ data: { running: true } });

      expect(await api.getStatus()).toEqual({ running: true });
      expect(await api.getStatus()).toEqual({ running: true });

      expect(mockAxiosInstance.get).toHaveBeenCalledTimes(1);
    });

    it('share one request between concurrent callers', async () => {
      let resolve;
      mockAxiosInstance.get.mockReturnValue(new Promise(r => (resolve = r)));

      const first = api.getStatus();
      const second = api.getStatus();
      resolve({ data: 'shared' });

      expect(await Promise.all([first, second])).toEqual(['shared', 'shared']);
      expect(mockAxiosInstance.get).toHaveBeenCalledTimes(1);
    });

    it('are refetched after a change to the server', async () => {
      mockAxiosInstance.get.mockResolvedValue({ data: { running: false } });
      mockAxiosInstance.post.mockResolvedValue({ data: { success: true } });

      await api.getStatus();
      await api.startServer();
      await api.getStatus();

      expect(mockAxiosInstance.get).toHaveBeenCalledTimes(2);
    });

    it("one caller giving up doesn't cancel the request for the others", async () => {
      let resolve;
      mockAxiosInstance.get.mockReturnValue(new Promise(r => (resolve = r)));
      const leaving = new AbortController();

      const abandoned = api.getStatus(leaving.signal);
      const staying = api.getStatus();
      leaving.abort();

      // Checked while the request is in flight; once it settles the last
      // subscriber releases it, which aborts the (by then finished) controller.
      const { signal } = mockAxiosInstance.get.mock.calls[0][1];
      expect(signal.aborted).toBe(false);

      resolve({ data: 'still here' });
      await expect(abandoned).rejects.toBeTruthy();
      expect(await staying).toBe('still here');
    });

    it('cancel the request once every caller has given up', async () => {
      mockAxiosInstance.get.mockReturnValue(new Promise(() => {}));
      const a = new AbortController();
      const b = new AbortController();

      const first = api.getStatus(a.signal);
      const second = api.getStatus(b.signal);
      a.abort();
      b.abort();

      await expect(first).rejects.toBeTruthy();
      await expect(second).rejects.toBeTruthy();
      expect(mockAxiosInstance.get.mock.calls[0][1].signal.aborted).toBe(true);
    });

    it('do not cache a failure', async () => {
      mockAxiosInstance.get.mockRejectedValueOnce(new Error('down')).mockResolvedValueOnce({ data: 'up' });

      await expect(api.getStatus()).rejects.toThrow('down');
      expect(await api.getStatus()).toBe('up');
    });
  });
});
