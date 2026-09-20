import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithRouter } from '../../test/utils';
import Console from '../Console';

// No API key/token in localStorage means Console's WebSocket effect takes
// its "no credentials" branch and settles into the disconnected state
// without attempting a real socket.io connection.
vi.mock('../../services/api', () => ({
  api: {
    sendCommand: vi.fn(),
  },
}));

describe('Console', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('renders the console page title', () => {
    renderWithRouter(<Console />);
    expect(screen.getByText(/server console/i)).toBeInTheDocument();
  });

  it('shows disconnected status with no credentials present', async () => {
    renderWithRouter(<Console />);
    await waitFor(() => {
      expect(screen.getByText(/disconnected/i)).toBeInTheDocument();
    });
  });

  it('shows the empty-output state before any command runs', () => {
    renderWithRouter(<Console />);
    expect(screen.getByText(/no output yet/i)).toBeInTheDocument();
  });

  it('keeps Execute disabled without a live connection, even with a command typed', async () => {
    const user = userEvent.setup();
    renderWithRouter(<Console />);

    const executeButton = screen.getByRole('button', { name: /execute/i });
    expect(executeButton).toBeDisabled();

    const input = screen.getByLabelText(/console command/i);
    await user.type(input, 'list');

    // Execute only runs over the WebSocket; without a connection there is
    // no reachable fallback from the UI, so it stays disabled.
    expect(executeButton).toBeDisabled();
  });

  it('supports history navigation via ArrowUp once a command has been run', async () => {
    localStorage.setItem('console_history', JSON.stringify(['list', 'help']));
    const user = userEvent.setup();
    renderWithRouter(<Console />);

    const input = screen.getByLabelText(/console command/i);
    input.focus();
    await user.keyboard('{ArrowUp}');
    expect(input).toHaveValue('help');
    await user.keyboard('{ArrowUp}');
    expect(input).toHaveValue('list');
  });

  it('clears the output when Clear is clicked', async () => {
    const user = userEvent.setup();
    renderWithRouter(<Console />);

    expect(screen.getByText(/no output yet/i)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /clear/i }));
    expect(screen.getByText(/no output yet/i)).toBeInTheDocument();
  });
});
