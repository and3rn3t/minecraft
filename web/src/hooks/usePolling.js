import { useEffect, useRef, useCallback, useState } from 'react';

/**
 * Custom hook for polling data at regular intervals
 * @param {Function} fetchFn - Function to fetch data
 * @param {number} intervalMs - Polling interval in milliseconds
 * @param {Array} deps - Dependencies array (like useEffect)
 * @returns {Object} - { data, loading, error, refetch }
 */
export function usePolling(fetchFn, intervalMs = 5000, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);
  const mountedRef = useRef(true);

  const fetchData = useCallback(async () => {
    try {
      setError(null);
      const result = await fetchFn();
      if (mountedRef.current) {
        setData(result);
        setLoading(false);
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err);
        setLoading(false);
      }
    }
  }, [fetchFn]);

  useEffect(() => {
    mountedRef.current = true;
    fetchData();

    if (intervalMs > 0) {
      intervalRef.current = setInterval(fetchData, intervalMs);
    }

    return () => {
      mountedRef.current = false;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetchData, intervalMs, ...deps]);

  const refetch = useCallback(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch };
}
