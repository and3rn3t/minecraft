import { act, renderHook, screen } from '@testing-library/react';
import { AxiosError } from 'axios';
import { describe, expect, it } from 'vitest';
import { ToastProvider } from '../../components/ToastContainer';
import { useErrorHandler } from '../useErrorHandler';

const wrapper = ({ children }) => <ToastProvider>{children}</ToastProvider>;

describe('useErrorHandler', () => {
  it.each([
    ['an Error', new Error('Disk full'), 'Disk full'],
    ['an API error body', { response: { data: { error: 'Permission denied' } } }, 'Permission denied'],
    ['anything else', undefined, 'Could not load backups'],
  ])('shows %s as an error toast', (_, err, expected) => {
    const { result } = renderHook(() => useErrorHandler(), { wrapper });

    act(() => result.current(err, 'Could not load backups'));

    expect(screen.getByText(expected)).toBeInTheDocument();
    expect(screen.getByText(expected).closest('.toast')).toHaveClass('toast-error');
  });

  // The cases above pass plain objects, which have no `message`. A real Axios error always does
  // ("Request failed with status code 500"), and that must not hide the reason the API returned.
  it('shows the API reason, not Axios generic message, for a failed request', () => {
    const response = { status: 500, data: { error: 'Backup creation failed (tar exit 2, gzip exit 0)' } };
    const err = new AxiosError('Request failed with status code 500', 'ERR_BAD_RESPONSE', undefined, undefined, response);
    const { result } = renderHook(() => useErrorHandler(), { wrapper });

    act(() => result.current(err, 'Failed to create backup'));

    expect(screen.getByText('Backup creation failed (tar exit 2, gzip exit 0)')).toBeInTheDocument();
    expect(screen.queryByText('Request failed with status code 500')).not.toBeInTheDocument();
  });

  it('still shows the Error message when the request never got a response', () => {
    const err = new AxiosError('Network Error', 'ERR_NETWORK');
    const { result } = renderHook(() => useErrorHandler(), { wrapper });

    act(() => result.current(err, 'Failed to create backup'));

    expect(screen.getByText('Network Error')).toBeInTheDocument();
  });

  it('falls back to a generic message', () => {
    const { result } = renderHook(() => useErrorHandler(), { wrapper });

    act(() => result.current({}));

    expect(screen.getByText('An error occurred')).toBeInTheDocument();
  });
});
