import { act, renderHook, screen } from '@testing-library/react';
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

  it('falls back to a generic message', () => {
    const { result } = renderHook(() => useErrorHandler(), { wrapper });

    act(() => result.current({}));

    expect(screen.getByText('An error occurred')).toBeInTheDocument();
  });
});
