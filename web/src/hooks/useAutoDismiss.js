import { useEffect } from 'react';

/**
 * Custom hook for automatically dismissing messages after a delay
 * @param {any} message - The message to watch (can be string, object, etc.)
 * @param {Function} dismissFn - Function to call to dismiss the message
 * @param {number} delay - Delay in milliseconds before dismissing
 * @returns {void}
 */
export function useAutoDismiss(message, dismissFn, delay = 5000) {
  useEffect(() => {
    if (!message) {
      return;
    }

    const timer = setTimeout(() => {
      dismissFn();
    }, delay);

    return () => clearTimeout(timer);
  }, [message, dismissFn, delay]);
}
