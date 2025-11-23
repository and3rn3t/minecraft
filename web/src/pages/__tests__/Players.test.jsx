import { screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from '../../services/api';
import { renderWithRouter } from '../../test/utils';
import Players from '../Players';

// Mock the API service
vi.mock('../../services/api', () => ({
  api: {
    getPlayers: vi.fn(),
  },
}));

describe('Players', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders players page title', async () => {
    api.api.getPlayers.mockResolvedValue({ players: [] });

    renderWithRouter(<Players />);

    await waitFor(() => {
      expect(screen.getByText(/player management/i)).toBeInTheDocument();
    });
  });

  it('displays loading state initially', () => {
    api.api.getPlayers.mockImplementation(() => new Promise(() => {}));

    renderWithRouter(<Players />);

    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('displays list of online players', async () => {
    api.api.getPlayers.mockResolvedValue({
      players: ['Player1', 'Player2', 'Player3'],
    });

    renderWithRouter(<Players />);

    await waitFor(() => {
      expect(screen.getByText('Player1')).toBeInTheDocument();
      expect(screen.getByText('Player2')).toBeInTheDocument();
      expect(screen.getByText('Player3')).toBeInTheDocument();
    });
  });

  it('displays player count', async () => {
    api.api.getPlayers.mockResolvedValue({
      players: ['Player1', 'Player2'],
    });

    renderWithRouter(<Players />);

    await waitFor(() => {
      expect(screen.getByText(/online players \(2\)/i)).toBeInTheDocument();
    });
  });

  it('displays empty state when no players', async () => {
    api.api.getPlayers.mockResolvedValue({ players: [] });

    renderWithRouter(<Players />);

    await waitFor(() => {
      expect(screen.getByText(/no players online/i)).toBeInTheDocument();
    });
  });

  it('updates player list periodically', async () => {
    api.api.getPlayers
      .mockResolvedValueOnce({ players: ['Player1'] })
      .mockResolvedValueOnce({ players: ['Player1', 'Player2'] });

    renderWithRouter(<Players />);

    await waitFor(() => {
      expect(screen.getByText('Player1')).toBeInTheDocument();
    });

    // Fast-forward time to trigger interval
    vi.advanceTimersByTime(5000);

    await waitFor(() => {
      expect(api.api.getPlayers).toHaveBeenCalledTimes(2);
    });
  });

  it('handles API errors gracefully', async () => {
    api.api.getPlayers.mockRejectedValue(new Error('API Error'));

    renderWithRouter(<Players />);

    // Component should still render, even with errors
    await waitFor(() => {
      expect(screen.getByText(/player management/i)).toBeInTheDocument();
    });
  });

  it('displays kick button for each player', async () => {
    api.api.getPlayers.mockResolvedValue({
      players: ['Player1', 'Player2'],
    });

    renderWithRouter(<Players />);

    await waitFor(() => {
      const kickButtons = screen.getAllByRole('button', { name: /kick/i });
      expect(kickButtons.length).toBe(2);
    });
  });
});
