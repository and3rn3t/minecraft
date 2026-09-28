import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { usePolling } from '../usePolling';

// Advance fake time and let the fetches that fall due settle
const advance = ms => act(() => vi.advanceTimersByTimeAsync(ms));
const flush = () => act(() => vi.advanceTimersByTimeAsync(0));

function defineVisibility(state) {
  Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => state });
}

function setVisibility(state) {
  defineVisibility(state);
  document.dispatchEvent(new Event('visibilitychange'));
}

describe('usePolling', () => {
  // Reset without firing visibilitychange: the hook from the test that just
  // ran is still mounted here (cleanup comes later), and the event would make
  // it fetch outside act().
  beforeEach(() => {
    vi.useFakeTimers();
    defineVisibility('visible');
  });

  afterEach(() => {
    vi.useRealTimers();
    defineVisibility('visible');
  });

  it('fetches straight away, then on every interval', async () => {
    let n = 0;
    const fetchFn = vi.fn(async () => ++n);
    const { result } = renderHook(() => usePolling(fetchFn, 1000));

    expect(result.current.loading).toBe(true);
    await flush();
    expect(result.current).toMatchObject({ data: 1, loading: false, error: null });

    await advance(1000);
    expect(result.current.data).toBe(2);
    await advance(1000);
    expect(fetchFn).toHaveBeenCalledTimes(3);
  });

  it('hands every fetch an AbortSignal', async () => {
    const fetchFn = vi.fn(async () => 'ok');
    renderHook(() => usePolling(fetchFn, 1000));
    await flush();

    expect(fetchFn.mock.calls[0][0]).toBeInstanceOf(AbortSignal);
  });

  it('backs off on consecutive failures, capped at 8x, and resets on success', async () => {
    let failing = true;
    const fetchFn = vi.fn(async () => {
      if (failing) throw new Error('down');
      return 'up';
    });
    const { result } = renderHook(() => usePolling(fetchFn, 1000));
    await flush();
    expect(result.current.error).toEqual(new Error('down'));

    // After the 1st failure the next tick waits 2x, then 4x, then 8x, then 8x
    for (const wait of [2000, 4000, 8000, 8000]) {
      const before = fetchFn.mock.calls.length;
      await advance(wait - 1);
      expect(fetchFn.mock.calls.length).toBe(before);
      await advance(1);
      expect(fetchFn.mock.calls.length).toBe(before + 1);
    }

    failing = false;
    await advance(8000);
    expect(result.current).toMatchObject({ data: 'up', error: null });

    // Healthy again: back to the base interval
    const before = fetchFn.mock.calls.length;
    await advance(1000);
    expect(fetchFn.mock.calls.length).toBe(before + 1);
  });

  it('pauses while the tab is hidden and catches up when it is shown', async () => {
    const fetchFn = vi.fn(async () => 'ok');
    renderHook(() => usePolling(fetchFn, 1000));
    await flush();

    setVisibility('hidden');
    await advance(5000);
    expect(fetchFn).toHaveBeenCalledTimes(1);

    await act(async () => setVisibility('visible'));
    await flush();
    expect(fetchFn).toHaveBeenCalledTimes(2);
  });

  it('refetch runs now and restarts the interval', async () => {
    const fetchFn = vi.fn(async () => 'ok');
    const { result } = renderHook(() => usePolling(fetchFn, 1000));
    await flush();
    await advance(600);

    await act(async () => result.current.refetch());
    await flush();
    expect(fetchFn).toHaveBeenCalledTimes(2);

    await advance(600);
    expect(fetchFn).toHaveBeenCalledTimes(2);
    await advance(400);
    expect(fetchFn).toHaveBeenCalledTimes(3);
  });

  it('aborts the request in flight and stops polling on unmount', async () => {
    const signals = [];
    const fetchFn = vi.fn(signal => {
      signals.push(signal);
      return new Promise(() => {});
    });
    const { unmount } = renderHook(() => usePolling(fetchFn, 1000));

    unmount();

    expect(signals[0].aborted).toBe(true);
    await advance(10000);
    expect(fetchFn).toHaveBeenCalledTimes(1);
  });

  it('treats an aborted request as neither data nor an error', async () => {
    const fetchFn = vi.fn(async () => {
      throw Object.assign(new Error('canceled'), { name: 'CanceledError' });
    });
    const { result } = renderHook(() => usePolling(fetchFn, 1000));
    await flush();

    expect(result.current.error).toBeNull();
  });

  it('fetches once and never again with an interval of 0', async () => {
    const fetchFn = vi.fn(async () => 'once');
    const { result } = renderHook(() => usePolling(fetchFn, 0));
    await flush();
    await advance(60000);

    expect(fetchFn).toHaveBeenCalledTimes(1);
    expect(result.current.data).toBe('once');
  });
});
