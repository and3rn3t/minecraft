import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  clearAllCache,
  clearCache,
  getCachedResponse,
  getPendingRequest,
  setCachedResponse,
  setPendingRequest,
} from '../apiCache';

describe('apiCache', () => {
  beforeEach(() => {
    clearAllCache();
  });

  describe('response cache', () => {
    it('returns a cached response within its TTL', () => {
      setCachedResponse('/status', 'GET', {}, { running: true }, 2000);
      expect(getCachedResponse('/status', 'GET', {})).toEqual({ running: true });
    });

    it('expires a cached response once its own TTL has passed', () => {
      const now = Date.now();
      vi.spyOn(Date, 'now').mockReturnValue(now);
      setCachedResponse('/status', 'GET', {}, { running: true }, 2000);

      vi.spyOn(Date, 'now').mockReturnValue(now + 2001);
      expect(getCachedResponse('/status', 'GET', {})).toBeNull();

      vi.restoreAllMocks();
    });

    it('honors each entry\'s own TTL, not a shared default', () => {
      // getStatus (2s) and listBackups (10s) used to always fall back to the
      // module's 30s default because isCacheValid() was called without
      // entry.ttl — every endpoint was silently cached for 30 seconds
      // regardless of what it asked for.
      const now = Date.now();
      vi.spyOn(Date, 'now').mockReturnValue(now);
      setCachedResponse('/status', 'GET', {}, { running: true }, 2000);
      setCachedResponse('/backups', 'GET', {}, { backups: [] }, 10000);

      vi.spyOn(Date, 'now').mockReturnValue(now + 3000);
      expect(getCachedResponse('/status', 'GET', {})).toBeNull();
      expect(getCachedResponse('/backups', 'GET', {})).toEqual({ backups: [] });

      vi.restoreAllMocks();
    });

    it('clearCache removes a single entry without affecting others', () => {
      setCachedResponse('/status', 'GET', {}, { running: true });
      setCachedResponse('/players', 'GET', {}, { players: [] });

      clearCache('/status', 'GET', {});

      expect(getCachedResponse('/status', 'GET', {})).toBeNull();
      expect(getCachedResponse('/players', 'GET', {})).toEqual({ players: [] });
    });
  });

  describe('pending-request dedup', () => {
    it('shares one in-flight promise across concurrent callers', () => {
      const promise = new Promise(() => {});
      setPendingRequest('/status', 'GET', {}, promise);
      expect(getPendingRequest('/status', 'GET', {})).toBe(promise);
    });

    it('unregisters itself once the promise resolves', async () => {
      const promise = Promise.resolve({ running: true });
      setPendingRequest('/status', 'GET', {}, promise);
      await promise;
      // The cleanup runs in a microtask queued by .then(); flush it.
      await Promise.resolve();
      expect(getPendingRequest('/status', 'GET', {})).toBeUndefined();
    });

    it('unregisters itself once the promise rejects', async () => {
      const promise = Promise.reject(new Error('network error'));
      setPendingRequest('/status', 'GET', {}, promise);
      await promise.catch(() => {});
      await Promise.resolve();
      expect(getPendingRequest('/status', 'GET', {})).toBeUndefined();
    });

    it('clears synchronously when its signal aborts, not just when the rejection later propagates', () => {
      // This is the fix for a real bug: usePolling aborts the previous
      // request's controller before issuing the next one. Under React 18
      // StrictMode's dev-mode double-invoke of effects, the *first* mount's
      // request gets aborted by the immediate cleanup, and the *second*
      // mount's fetchData() call re-enters cachedGet synchronously — before
      // the first promise's rejection has had a chance to propagate as a
      // microtask. Without a synchronous abort listener, that second call
      // would be handed back the doomed first promise and inherit its
      // failure, even though its own signal was never aborted.
      const controller = new AbortController();
      const promise = new Promise(() => {}); // never settles on its own
      setPendingRequest('/status', 'GET', {}, promise, controller.signal);

      expect(getPendingRequest('/status', 'GET', {})).toBe(promise);
      controller.abort();
      // No await, no microtask flush — this must be synchronous.
      expect(getPendingRequest('/status', 'GET', {})).toBeUndefined();
    });

    it('does not clear a newer entry that has since replaced an aborted one', () => {
      const controllerA = new AbortController();
      const promiseA = new Promise(() => {});
      setPendingRequest('/status', 'GET', {}, promiseA, controllerA.signal);

      // A second caller (e.g. the retried fetch after the abort above)
      // registers its own, unrelated pending entry for the same key.
      const promiseB = new Promise(() => {});
      setPendingRequest('/status', 'GET', {}, promiseB);

      // Aborting the first (already-superseded) controller must not evict
      // the second entry.
      controllerA.abort();
      expect(getPendingRequest('/status', 'GET', {})).toBe(promiseB);
    });
  });
});
