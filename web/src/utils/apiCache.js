/**
 * Simple in-memory cache for API requests
 * Prevents duplicate requests and caches responses
 */

const cache = new Map();
const pendingRequests = new Map();

// Default TTL: 30 seconds
const DEFAULT_TTL = 30 * 1000;

/**
 * Generate cache key from request details
 */
function getCacheKey(url, method = 'GET', params = {}) {
  const paramsStr = JSON.stringify(params);
  return `${method}:${url}:${paramsStr}`;
}

/**
 * Check if cache entry is still valid
 */
function isCacheValid(entry, ttl = DEFAULT_TTL) {
  return Date.now() - entry.timestamp < ttl;
}

/**
 * Get cached response if available and valid
 */
export function getCachedResponse(url, method = 'GET', params = {}) {
  const key = getCacheKey(url, method, params);
  const entry = cache.get(key);

  if (entry && isCacheValid(entry, entry.ttl)) {
    return entry.data;
  }

  // Remove expired entry
  if (entry) {
    cache.delete(key);
  }

  return null;
}

/**
 * Cache a response
 */
export function setCachedResponse(url, method = 'GET', params = {}, data, ttl = DEFAULT_TTL) {
  const key = getCacheKey(url, method, params);
  cache.set(key, {
    data,
    timestamp: Date.now(),
    ttl,
  });
}

/**
 * Clear cache entry for a specific request
 */
export function clearCache(url, method = 'GET', params = {}) {
  const key = getCacheKey(url, method, params);
  cache.delete(key);
}

/**
 * Clear all cache entries
 */
export function clearAllCache() {
  cache.clear();
}

/**
 * Get the raw in-flight promise for a key, if any (no subscription).
 */
export function getPendingRequest(url, method = 'GET', params = {}) {
  const key = getCacheKey(url, method, params);
  return pendingRequests.get(key)?.promise;
}

function makeAbortError() {
  return new DOMException('The operation was aborted.', 'AbortError');
}

/**
 * Register a new shared, cancellable request. `controller` governs the
 * underlying network call and is owned by this entry alone — no external
 * caller's signal is ever attached to it directly. Every caller, including
 * the one creating the request, expresses "I don't need this any more"
 * through subscribeToPendingRequest instead, which only aborts `controller`
 * once every subscriber has walked away (see there for why).
 */
export function setPendingRequest(url, method = 'GET', params = {}, promise, controller) {
  const key = getCacheKey(url, method, params);
  const entry = { promise, controller, subscribers: 0 };
  pendingRequests.set(key, entry);

  // Only remove the entry if it's still this exact one — a newer call for
  // the same key may already have replaced it by the time this fires.
  const clearIfCurrent = () => {
    if (pendingRequests.get(key) === entry) {
      pendingRequests.delete(key);
    }
  };

  // Clean up when the promise settles...
  promise.then(clearIfCurrent, clearIfCurrent);

  // ...and also the instant every subscriber has released and the
  // underlying controller aborts as a result, synchronously, rather than
  // only once the resulting rejection has propagated (a later microtask).
  // A caller that aborts and immediately retries — which is exactly what
  // React 18 StrictMode's dev-mode double-invoke of effects does to
  // usePolling — can otherwise re-enter cachedGet before the doomed
  // promise has unregistered itself, and get handed back a promise that's
  // already going to reject, even though its own signal was never aborted.
  controller.signal.addEventListener('abort', clearIfCurrent, { once: true });
}

/**
 * Join whichever request (just-created or already in-flight) is registered
 * for this key. Returns a promise that resolves/rejects the same way as the
 * shared one, but also rejects early (with an AbortError) if `signal` fires
 * first — without ever cancelling the underlying request on any other
 * subscriber's behalf. The request is only actually aborted once every
 * subscriber has walked away: two components polling the same endpoint
 * (e.g. Dashboard and Players both fetching /players) can't have one's
 * unmount cancel the fetch the other is still waiting on. Returns null if
 * nothing is currently pending for this key.
 */
export function subscribeToPendingRequest(url, method = 'GET', params = {}, signal) {
  const key = getCacheKey(url, method, params);
  const entry = pendingRequests.get(key);
  if (!entry) {
    return null;
  }

  entry.subscribers += 1;
  let released = false;
  const release = () => {
    if (released) {
      return;
    }
    released = true;
    entry.subscribers -= 1;
    if (entry.subscribers <= 0) {
      entry.controller.abort();
    }
  };

  if (!signal) {
    return entry.promise.finally(release);
  }
  if (signal.aborted) {
    release();
    return Promise.reject(makeAbortError());
  }

  return new Promise((resolve, reject) => {
    const onAbort = () => {
      release();
      reject(makeAbortError());
    };
    signal.addEventListener('abort', onAbort, { once: true });
    entry.promise.then(
      value => {
        signal.removeEventListener('abort', onAbort);
        release();
        resolve(value);
      },
      err => {
        signal.removeEventListener('abort', onAbort);
        release();
        reject(err);
      }
    );
  });
}

/**
 * Clear expired cache entries (run periodically)
 */
export function cleanExpiredCache() {
  const now = Date.now();
  for (const [key, entry] of cache.entries()) {
    if (now - entry.timestamp >= entry.ttl) {
      cache.delete(key);
    }
  }
}

// Clean expired entries every minute
if (typeof window !== 'undefined') {
  setInterval(cleanExpiredCache, 60 * 1000);
}
