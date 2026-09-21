import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  clearAllCache,
  clearCache,
  getCachedResponse,
  getPendingRequest,
  setCachedResponse,
  setPendingRequest,
  subscribeToPendingRequest,
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
      setPendingRequest('/status', 'GET', {}, promise, new AbortController());
      expect(getPendingRequest('/status', 'GET', {})).toBe(promise);
    });

    it('unregisters itself once the promise resolves', async () => {
      const promise = Promise.resolve({ running: true });
      setPendingRequest('/status', 'GET', {}, promise, new AbortController());
      await promise;
      // The cleanup runs in a microtask queued by .then(); flush it.
      await Promise.resolve();
      expect(getPendingRequest('/status', 'GET', {})).toBeUndefined();
    });

    it('unregisters itself once the promise rejects', async () => {
      const promise = Promise.reject(new Error('network error'));
      setPendingRequest('/status', 'GET', {}, promise, new AbortController());
      await promise.catch(() => {});
      await Promise.resolve();
      expect(getPendingRequest('/status', 'GET', {})).toBeUndefined();
    });

    it('clears synchronously once the underlying controller aborts, not just when the rejection later propagates', () => {
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
      setPendingRequest('/status', 'GET', {}, promise, controller);

      expect(getPendingRequest('/status', 'GET', {})).toBe(promise);
      controller.abort();
      // No await, no microtask flush — this must be synchronous.
      expect(getPendingRequest('/status', 'GET', {})).toBeUndefined();
    });

    it('does not clear a newer entry that has since replaced an aborted one', () => {
      const controllerA = new AbortController();
      const promiseA = new Promise(() => {});
      setPendingRequest('/status', 'GET', {}, promiseA, controllerA);

      // A second caller (e.g. the retried fetch after the abort above)
      // registers its own, unrelated pending entry for the same key.
      const promiseB = new Promise(() => {});
      setPendingRequest('/status', 'GET', {}, promiseB, new AbortController());

      // Aborting the first (already-superseded) controller must not evict
      // the second entry.
      controllerA.abort();
      expect(getPendingRequest('/status', 'GET', {})).toBe(promiseB);
    });
  });

  describe('subscribeToPendingRequest', () => {
    it('returns null when nothing is pending for this key', () => {
      expect(subscribeToPendingRequest('/nonexistent', 'GET', {}, undefined)).toBeNull();
    });

    it("one subscriber aborting doesn't cancel the request for another still relying on it", async () => {
      // The bug this fixes: Dashboard and Players can both poll /players.
      // The old code issued the shared axios call with whichever caller's
      // signal happened to create it — so that caller unmounting aborted
      // the request for the other one too, even though its own signal was
      // never touched.
      const controller = new AbortController();
      const promise = new Promise(() => {}); // never settles on its own
      setPendingRequest('/players', 'GET', {}, promise, controller);

      const ownerSignal = new AbortController();
      const joinerSignal = new AbortController();
      const owned = subscribeToPendingRequest('/players', 'GET', {}, ownerSignal.signal);
      const joined = subscribeToPendingRequest('/players', 'GET', {}, joinerSignal.signal);

      ownerSignal.abort();
      // The owner's own wait ends locally...
      await expect(owned).rejects.toMatchObject({ name: 'AbortError' });
      // ...but the shared request must survive for the joiner.
      expect(controller.signal.aborted).toBe(false);
      expect(getPendingRequest('/players', 'GET', {})).toBe(promise);

      joinerSignal.abort();
      await expect(joined).rejects.toMatchObject({ name: 'AbortError' });
    });

    it('aborts the underlying controller once every subscriber has released', async () => {
      const controller = new AbortController();
      const promise = new Promise(() => {});
      setPendingRequest('/players', 'GET', {}, promise, controller);

      const subA = new AbortController();
      const subB = new AbortController();
      const a = subscribeToPendingRequest('/players', 'GET', {}, subA.signal);
      const b = subscribeToPendingRequest('/players', 'GET', {}, subB.signal);

      subA.abort();
      await expect(a).rejects.toMatchObject({ name: 'AbortError' });
      expect(controller.signal.aborted).toBe(false);

      subB.abort();
      await expect(b).rejects.toMatchObject({ name: 'AbortError' });
      expect(controller.signal.aborted).toBe(true);
    });

    it('rejects immediately when given an already-aborted signal', async () => {
      const controller = new AbortController();
      const promise = new Promise(() => {});
      setPendingRequest('/players', 'GET', {}, promise, controller);

      const already = new AbortController();
      already.abort();
      const result = subscribeToPendingRequest('/players', 'GET', {}, already.signal);
      await expect(result).rejects.toMatchObject({ name: 'AbortError' });
    });

    it('with no signal, resolves like the shared promise and releases without aborting anything', async () => {
      const controller = new AbortController();
      const promise = Promise.resolve({ players: [] });
      setPendingRequest('/players', 'GET', {}, promise, controller);

      const result = subscribeToPendingRequest('/players', 'GET', {}, undefined);
      await expect(result).resolves.toEqual({ players: [] });
    });
  });
});
