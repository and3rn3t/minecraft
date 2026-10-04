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
      // The API's own message first: an Axios error always has a `message` ("Request failed
      // with status code 500"), which would otherwise hide the reason the server returned
      const message = err?.response?.data?.error || err?.message || defaultMessage;
      showError(message);
    },
    [showError]
  );

  return handleError;
}
