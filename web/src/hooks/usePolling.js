import { useCallback, useEffect, useRef, useState } from 'react';

// Cap error backoff at 8x the base interval, so a dead endpoint on a fast
// poll (e.g. logs at 2s) doesn't settle into hammering the API at full rate
// forever, but also doesn't drift into multi-minute silence.
const MAX_BACKOFF_MULTIPLIER = 8;

function isAbortError(err) {
  return err?.name === 'CanceledError' || err?.name === 'AbortError' || err?.code === 'ERR_CANCELED';
}

/**
 * Custom hook for polling data at regular intervals.
 * - `fetchFn` is called with an `AbortSignal`; the previous request is
 *   aborted before the next one starts, and on unmount.
 * - Polling pauses while the tab is hidden and catches up immediately when
 *   it becomes visible again, so a background tab doesn't keep hitting the API.
 * - Consecutive failures back off (up to `MAX_BACKOFF_MULTIPLIER`x); a
 *   success resets the backoff to the base interval.
 *
 * @param {Function} fetchFn - Function to fetch data; receives an AbortSignal
 * @param {number} intervalMs - Base polling interval in milliseconds
 * @param {Array} deps - Dependencies array (like useEffect)
 * @returns {Object} - { data, loading, error, refetch }
 */
export function usePolling(fetchFn, intervalMs = 5000, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const timeoutRef = useRef(null);
  const mountedRef = useRef(true);
  const controllerRef = useRef(null);
  const consecutiveErrorsRef = useRef(0);
  const runTickRef = useRef(() => {});
  // Identifies which effect run's scheduling chain is current. React 18
  // StrictMode's dev-mode double-invoke (mount -> cleanup -> remount, all
  // synchronous) resets mountedRef back to true before the *first* mount's
  // `fetchData().then(scheduleNext)` settles, so that stale call can't tell
  // it's stale from mountedRef alone. It can still check its captured epoch
  // against the current one, since only a genuinely new effect run bumps it.
  const epochRef = useRef(0);

  const fetchData = useCallback(async () => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;

    try {
      setError(null);
      const result = await fetchFn(controller.signal);
      if (mountedRef.current) {
        consecutiveErrorsRef.current = 0;
        setData(result);
        setLoading(false);
      }
    } catch (err) {
      if (isAbortError(err)) {
        return;
      }
      if (mountedRef.current) {
        consecutiveErrorsRef.current += 1;
        setError(err);
        setLoading(false);
      }
    }
  }, [fetchFn]);

  useEffect(() => {
    mountedRef.current = true;
    const epoch = ++epochRef.current;
    const isCurrent = () => epoch === epochRef.current;

    const scheduleNext = () => {
      if (intervalMs <= 0 || !mountedRef.current || !isCurrent()) {
        return;
      }
      const backoff = Math.min(2 ** consecutiveErrorsRef.current, MAX_BACKOFF_MULTIPLIER);
      timeoutRef.current = setTimeout(runTick, intervalMs * backoff);
    };

    const runTick = async () => {
      if (!isCurrent()) {
        return;
      }
      if (document.visibilityState !== 'hidden') {
        await fetchData();
      }
      scheduleNext();
    };
    runTickRef.current = runTick;

    fetchData().then(() => {
      if (isCurrent()) {
        scheduleNext();
      }
    });

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && mountedRef.current) {
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
        }
        runTick();
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      mountedRef.current = false;
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      controllerRef.current?.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetchData, intervalMs, ...deps]);

  const refetch = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    runTickRef.current();
  }, []);

  return { data, loading, error, refetch };
}
