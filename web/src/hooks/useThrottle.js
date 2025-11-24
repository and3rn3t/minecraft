import { useEffect, useRef, useState } from 'react';

/**
 * Custom hook for throttling values
 * @param {any} value - The value to throttle
 * @param {number} limit - Time limit in milliseconds
 * @returns {any} - Throttled value
 */
export function useThrottle(value, limit = 1000) {
  const [throttledValue, setThrottledValue] = useState(value);
  const lastRan = useRef(Date.now());

  useEffect(() => {
    const handler = setTimeout(
      () => {
        if (Date.now() - lastRan.current >= limit) {
          setThrottledValue(value);
          lastRan.current = Date.now();
        }
      },
      limit - (Date.now() - lastRan.current)
    );

    return () => {
      clearTimeout(handler);
    };
  }, [value, limit]);

  return throttledValue;
}
