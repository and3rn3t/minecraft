import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from '../../services/api';
import { renderWithRouter } from '../../test/utils';
import Worlds from '../Worlds';

// Mock the API service
vi.mock('../../services/api', () => ({
  api: {
    listWorlds: vi.fn(),
  },
}));

describe('Worlds', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders worlds page title', async () => {
    api.api.listWorlds.mockResolvedValue({ worlds: [] });

    renderWithRouter(<Worlds />);

    await waitFor(() => {
      expect(screen.getByText(/world management/i)).toBeInTheDocument();
    });
  });

  it('displays loading state initially', () => {
    api.api.listWorlds.mockImplementation(() => new Promise(() => {}));

    renderWithRouter(<Worlds />);

    expect(screen.getByText(/loading worlds/i)).toBeInTheDocument();
  });

  it('displays list of worlds', async () => {
    api.api.listWorlds.mockResolvedValue({
      worlds: [
        { name: 'world', size: '120M', type: 'overworld', active: true },
        { name: 'world_nether', size: '40M', type: 'nether', active: false },
        { name: 'world_the_end', size: '15M', type: 'end', active: false },
      ],
    });

    renderWithRouter(<Worlds />);

    await waitFor(() => {
      expect(screen.getByText('world')).toBeInTheDocument();
      expect(screen.getByText('world_nether')).toBeInTheDocument();
      expect(screen.getByText('world_the_end')).toBeInTheDocument();
    });
  });

  it('displays empty state when no worlds', async () => {
    api.api.listWorlds.mockResolvedValue({ worlds: [] });

    renderWithRouter(<Worlds />);

    await waitFor(() => {
      expect(screen.getByText(/no worlds found/i)).toBeInTheDocument();
    });
  });

  it('displays switch and backup buttons for each world', async () => {
    api.api.listWorlds.mockResolvedValue({
      worlds: [
        { name: 'world', size: '120M', type: 'overworld', active: true },
        { name: 'survival', size: '80M', type: 'overworld', active: false },
      ],
    });

    renderWithRouter(<Worlds />);

    await waitFor(() => {
      const switchButtons = screen.getAllByRole('button', { name: /switch/i });
      const backupButtons = screen.getAllByRole('button', { name: /backup/i });
      expect(switchButtons.length).toBe(2);
      expect(backupButtons.length).toBe(2);
    });
  });

  it('handles API errors gracefully', async () => {
    api.api.listWorlds.mockRejectedValue(new Error('API Error'));

    renderWithRouter(<Worlds />);

    // Component should still render, even with errors
    await waitFor(() => {
      expect(screen.getByText(/world management/i)).toBeInTheDocument();
    });

    // The error is surfaced, not swallowed into a misleading empty state
    expect(screen.getByRole('alert')).toHaveTextContent(/could not load worlds/i);
    expect(screen.queryByText(/no worlds found/i)).not.toBeInTheDocument();
  });

  it('retries after an error and recovers once it succeeds', async () => {
    api.api.listWorlds.mockRejectedValueOnce(new Error('API Error'));
    api.api.listWorlds.mockResolvedValueOnce({
      worlds: [{ name: 'world', size: '120M', type: 'overworld', active: true }],
    });

    renderWithRouter(<Worlds />);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: /retry/i }));

    await waitFor(() => {
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
      expect(screen.getByText('world')).toBeInTheDocument();
    });
  });
});
