import { screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from '../../services/api';
import { renderWithRouter } from '../../test/utils';
import Dashboard from '../Dashboard';

// Mock the API service
vi.mock('../../services/api', () => ({
  api: {
    getStatus: vi.fn(),
    getMetrics: vi.fn(),
    getPlayers: vi.fn(),
    startServer: vi.fn(),
    stopServer: vi.fn(),
    restartServer: vi.fn(),
  },
}));

describe('Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders dashboard title', async () => {
    api.api.getStatus.mockResolvedValue({ running: true, status: 'Up' });
    api.api.getMetrics.mockResolvedValue({ metrics: {} });
    api.api.getPlayers.mockResolvedValue({ players: [] });

    renderWithRouter(<Dashboard />);

    await waitFor(
      () => {
        expect(screen.getByText(/dashboard/i)).toBeInTheDocument();
      },
      { timeout: 3000 }
    );
  });

  it('displays loading state initially', () => {
    api.api.getStatus.mockImplementation(() => new Promise(() => {}));
    api.api.getMetrics.mockImplementation(() => new Promise(() => {}));
    api.api.getPlayers.mockImplementation(() => new Promise(() => {}));

    const { container } = renderWithRouter(<Dashboard />);
    // Check for skeleton loaders - they have the "skeleton" class
    const skeletons = container.querySelectorAll('.skeleton');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('displays server status when online', async () => {
    api.api.getStatus.mockResolvedValue({
      running: true,
      status: 'Up 2 hours',
    });
    api.api.getMetrics.mockResolvedValue({ metrics: {} });
    api.api.getPlayers.mockResolvedValue({ players: [] });

    renderWithRouter(<Dashboard />);

    await waitFor(() => {
      // Check for the status card value specifically (not the heading)
      const statusCards = screen.getAllByText(/online/i);
      expect(statusCards.length).toBeGreaterThan(0);
    });
  });

  it('displays server status when offline', async () => {
    api.api.getStatus.mockResolvedValue({
      running: false,
      status: 'Stopped',
    });
    api.api.getMetrics.mockResolvedValue({ metrics: {} });
    api.api.getPlayers.mockResolvedValue({ players: [] });

    renderWithRouter(<Dashboard />);

    await waitFor(() => {
      // Check for the status card value specifically (not the heading)
      const statusCards = screen.getAllByText(/offline/i);
      expect(statusCards.length).toBeGreaterThan(0);
    });
  });

  it('displays player count', async () => {
    api.api.getStatus.mockResolvedValue({ running: true, status: 'Up' });
    api.api.getMetrics.mockResolvedValue({ metrics: {} });
    api.api.getPlayers.mockResolvedValue({
      players: ['Player1', 'Player2'],
    });

    renderWithRouter(<Dashboard />);

    await waitFor(
      () => {
        // Player count is shown in the StatusCard value and subtitle
        expect(screen.getByText('2')).toBeInTheDocument();
        expect(screen.getByText(/2 \/ 10/i)).toBeInTheDocument();
      },
      { timeout: 3000 }
    );
  });

  it('displays online players', async () => {
    api.api.getStatus.mockResolvedValue({ running: true, status: 'Up' });
    api.api.getMetrics.mockResolvedValue({ metrics: {} });
    api.api.getPlayers.mockResolvedValue({
      players: ['Player1', 'Player2'],
    });

    renderWithRouter(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('Player1')).toBeInTheDocument();
      expect(screen.getByText('Player2')).toBeInTheDocument();
    });
  });

  it('calls startServer when start button is clicked', async () => {
    api.api.getStatus.mockResolvedValue({ running: false, status: 'Stopped' });
    api.api.getMetrics.mockResolvedValue({ metrics: {} });
    api.api.getPlayers.mockResolvedValue({ players: [] });
    api.api.startServer.mockResolvedValue({ success: true });

    renderWithRouter(<Dashboard />);

    await waitFor(
      () => {
        const startButton = screen.getByRole('button', { name: /start server/i });
        expect(startButton).toBeInTheDocument();
        expect(startButton).not.toBeDisabled();
      },
      { timeout: 3000 }
    );

    const startButton = screen.getByRole('button', { name: /start server/i });
    startButton.click();

    await waitFor(() => {
      expect(api.api.startServer).toHaveBeenCalled();
    });
  });

  it('disables start button when server is running', async () => {
    api.api.getStatus.mockResolvedValue({ running: true, status: 'Up' });
    api.api.getMetrics.mockResolvedValue({ metrics: {} });
    api.api.getPlayers.mockResolvedValue({ players: [] });

    renderWithRouter(<Dashboard />);

    await waitFor(
      () => {
        const startButton = screen.getByRole('button', { name: /start server/i });
        expect(startButton).toBeDisabled();
      },
      { timeout: 3000 }
    );
  });

  it('disables stop button when server is offline', async () => {
    api.api.getStatus.mockResolvedValue({ running: false, status: 'Stopped' });
    api.api.getMetrics.mockResolvedValue({ metrics: {} });
    api.api.getPlayers.mockResolvedValue({ players: [] });

    renderWithRouter(<Dashboard />);

    await waitFor(() => {
      const stopButton = screen.getByRole('button', { name: /stop server/i });
      expect(stopButton).toBeDisabled();
    });
  });
});
