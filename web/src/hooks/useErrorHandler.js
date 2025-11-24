import { useCallback } from 'react';
import { useToast } from '../components/ToastContainer';

/**
 * Custom hook for consistent error handling across components
 * @returns {Function} - Error handler function
 */
export function useErrorHandler() {
  const { error: showError } = useToast();

  const handleError = useCallback(
    (err, defaultMessage = 'An error occurred') => {
      const message = err?.message || err?.response?.data?.error || defaultMessage;
      showError(message);
    },
    [showError]
  );

  return handleError;
}

