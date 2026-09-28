import { act, render, renderHook, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ToastProvider, useToast } from '../ToastContainer';

function Trigger({ type, message = 'Saved', duration }) {
  const toast = useToast();
  return <button onClick={() => toast[type](message, duration)}>show</button>;
}

const renderWith = props =>
  render(
    <ToastProvider>
      <Trigger {...props} />
    </ToastProvider>
  );

describe('toasts', () => {
  afterEach(() => vi.useRealTimers());

  it.each([
    ['success', 'toast-success', '✅'],
    ['error', 'toast-error', '❌'],
    ['info', 'toast-info', 'ℹ️'],
    ['warning', 'toast-warning', '⚠️'],
  ])('a %s toast is styled and labelled for its type', async (type, className, icon) => {
    const user = userEvent.setup();
    renderWith({ type });

    await user.click(screen.getByText('show'));

    const toast = screen.getByText('Saved').closest('.toast');
    expect(toast).toHaveClass(className);
    expect(toast).toHaveTextContent(icon);
  });

  it('are announced politely to screen readers', () => {
    renderWith({ type: 'info' });
    expect(screen.getByRole('status')).toHaveAttribute('aria-live', 'polite');
  });

  it('dismiss themselves after their duration', () => {
    vi.useFakeTimers();
    renderWith({ type: 'info', duration: 2000 });

    act(() => screen.getByText('show').click());
    expect(screen.getByText('Saved')).toBeInTheDocument();

    act(() => vi.advanceTimersByTime(2000));
    expect(screen.queryByText('Saved')).not.toBeInTheDocument();
  });

  it('stay until closed when the duration is 0', async () => {
    vi.useFakeTimers();
    renderWith({ type: 'error', duration: 0 });

    act(() => screen.getByText('show').click());
    act(() => vi.advanceTimersByTime(60000));
    expect(screen.getByText('Saved')).toBeInTheDocument();

    act(() => screen.getByRole('button', { name: 'Close' }).click());
    expect(screen.queryByText('Saved')).not.toBeInTheDocument();
  });

  it('stack, and closing one leaves the others', async () => {
    const user = userEvent.setup();
    render(
      <ToastProvider>
        <Trigger type="info" message="first" />
        <Trigger type="info" message="second" />
      </ToastProvider>
    );
    const [showFirst, showSecond] = screen.getAllByText('show');

    await user.click(showFirst);
    await user.click(showSecond);
    const closes = screen.getAllByRole('button', { name: 'Close' });
    await user.click(closes[0]);

    expect(screen.queryByText('first')).not.toBeInTheDocument();
    expect(screen.getByText('second')).toBeInTheDocument();
  });

  it('useToast outside a provider says so', () => {
    // React logs the thrown error and jsdom reports it as uncaught; both are
    // the expected outcome here, not noise worth printing.
    const quiet = event => event.preventDefault();
    window.addEventListener('error', quiet);
    vi.spyOn(console, 'error').mockImplementation(() => {});
    try {
      expect(() => renderHook(() => useToast())).toThrow('useToast must be used within ToastProvider');
    } finally {
      window.removeEventListener('error', quiet);
      console.error.mockRestore();
    }
  });
});
