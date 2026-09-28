import { renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useAutoDismiss } from '../useAutoDismiss';

describe('useAutoDismiss', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('dismisses a message after the delay', () => {
    const dismiss = vi.fn();
    renderHook(() => useAutoDismiss('Saved', dismiss, 3000));

    vi.advanceTimersByTime(2999);
    expect(dismiss).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(dismiss).toHaveBeenCalledTimes(1);
  });

  it('does nothing without a message', () => {
    const dismiss = vi.fn();
    renderHook(() => useAutoDismiss(null, dismiss, 3000));

    vi.advanceTimersByTime(10000);
    expect(dismiss).not.toHaveBeenCalled();
  });

  it('a new message restarts the countdown', () => {
    const dismiss = vi.fn();
    const { rerender } = renderHook(({ message }) => useAutoDismiss(message, dismiss, 3000), {
      initialProps: { message: 'first' },
    });

    vi.advanceTimersByTime(2000);
    rerender({ message: 'second' });
    vi.advanceTimersByTime(2000);
    expect(dismiss).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1000);
    expect(dismiss).toHaveBeenCalledTimes(1);
  });

  it('cancels on unmount', () => {
    const dismiss = vi.fn();
    const { unmount } = renderHook(() => useAutoDismiss('Saved', dismiss, 3000));

    unmount();
    vi.advanceTimersByTime(5000);
    expect(dismiss).not.toHaveBeenCalled();
  });
});
