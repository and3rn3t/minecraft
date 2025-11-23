import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import Logs from '../../pages/Logs';
import * as api from '../../services/api';
import { renderWithRouter } from '../utils';

// Mock the API service
vi.mock('../../services/api', () => ({
  api: {
    getLogs: vi.fn(),
  },
}));

describe('Logs Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('loads and displays logs', async () => {
    // Set up mock response
    api.api.getLogs.mockResolvedValue({
      logs: [
        '[10:30:00] [Server thread/INFO] Starting minecraft server',
        '[10:30:01] [Server thread/ERROR] Test error message',
        '[10:30:02] [Server thread/WARN] Warning message',
      ],
      lines: 3,
    });

    renderWithRouter(<Logs />);

    await waitFor(
      () => {
        expect(screen.getByText(/Starting minecraft server/)).toBeInTheDocument();
        expect(screen.getByText(/Test error message/)).toBeInTheDocument();
        expect(screen.getByText(/Warning message/)).toBeInTheDocument();
      },
      { timeout: 5000 }
    );
  });

  it('filters logs correctly', async () => {
    const user = userEvent.setup();

    // Set up mock response
    api.api.getLogs.mockResolvedValue({
      logs: [
        '[10:30:00] [Server thread/INFO] Starting minecraft server',
        '[10:30:01] [Server thread/ERROR] Test error message',
        '[10:30:02] [Server thread/WARN] Warning message',
      ],
      lines: 3,
    });

    renderWithRouter(<Logs />);

    await waitFor(
      () => {
        expect(screen.getByText(/Starting minecraft server/)).toBeInTheDocument();
      },
      { timeout: 5000 }
    );

    const filterInput = screen.getByPlaceholderText(/filter logs/i);
    await user.type(filterInput, 'ERROR');

    await waitFor(
      () => {
        expect(screen.queryByText(/Starting minecraft server/)).not.toBeInTheDocument();
        expect(screen.getByText(/Test error message/)).toBeInTheDocument();
      },
      { timeout: 3000 }
    );
  });

  it('refreshes logs on button click', async () => {
    const user = userEvent.setup();

    // Set up mock response
    api.api.getLogs.mockResolvedValue({
      logs: [
        '[10:30:00] [Server thread/INFO] Starting minecraft server',
        '[10:30:01] [Server thread/ERROR] Test error message',
        '[10:30:02] [Server thread/WARN] Warning message',
      ],
      lines: 3,
    });

    renderWithRouter(<Logs />);

    await waitFor(
      () => {
        expect(screen.getByText(/Starting minecraft server/)).toBeInTheDocument();
      },
      { timeout: 5000 }
    );

    const refreshButton = screen.getByRole('button', { name: /refresh/i });
    await user.click(refreshButton);

    // Should reload logs - verify API was called again
    expect(api.api.getLogs).toHaveBeenCalledTimes(2);

    // Logs should still be visible
    await waitFor(
      () => {
        expect(screen.getByText(/Starting minecraft server/)).toBeInTheDocument();
      },
      { timeout: 3000 }
    );
  });
});
