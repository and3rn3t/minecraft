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

  if (entry && isCacheValid(entry)) {
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
 * Get or set pending request to prevent duplicate calls
 */
export function getPendingRequest(url, method = 'GET', params = {}) {
  const key = getCacheKey(url, method, params);
  return pendingRequests.get(key);
}

/**
 * Set pending request promise
 */
export function setPendingRequest(url, method = 'GET', params = {}, promise) {
  const key = getCacheKey(url, method, params);
  pendingRequests.set(key, promise);

  // Clean up when promise resolves/rejects
  promise
    .then(() => {
      pendingRequests.delete(key);
    })
    .catch(() => {
      pendingRequests.delete(key);
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
