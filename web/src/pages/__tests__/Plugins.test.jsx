import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from '../../services/api';
import { renderWithRouter } from '../../test/utils';
import Plugins from '../Plugins';

// Mock the API service
vi.mock('../../services/api', () => ({
  api: {
    listPlugins: vi.fn(),
  },
}));

describe('Plugins', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders plugins page title', async () => {
    api.api.listPlugins.mockResolvedValue({ plugins: [] });

    renderWithRouter(<Plugins />);

    await waitFor(() => {
      expect(screen.getByText(/plugin management/i)).toBeInTheDocument();
    });
  });

  it('displays loading state initially', () => {
    api.api.listPlugins.mockImplementation(() => new Promise(() => {}));

    renderWithRouter(<Plugins />);

    expect(screen.getByText(/loading plugins/i)).toBeInTheDocument();
  });

  it('displays list of plugins', async () => {
    api.api.listPlugins.mockResolvedValue({
      plugins: [
        { filename: 'a.jar', name: 'PluginA', version: '1.0', enabled: true },
        { filename: 'b.jar', name: 'PluginB', version: '2.0', enabled: false },
      ],
    });

    renderWithRouter(<Plugins />);

    await waitFor(() => {
      expect(screen.getByText('PluginA')).toBeInTheDocument();
      expect(screen.getByText('PluginB')).toBeInTheDocument();
    });
  });

  it('displays empty state when no plugins', async () => {
    api.api.listPlugins.mockResolvedValue({ plugins: [] });

    renderWithRouter(<Plugins />);

    await waitFor(() => {
      expect(screen.getByText(/no plugins installed/i)).toBeInTheDocument();
    });
  });

  it('surfaces a fetch failure instead of a misleading empty state', async () => {
    api.api.listPlugins.mockRejectedValue(new Error('API Error'));

    renderWithRouter(<Plugins />);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/could not load plugins/i);
    });
    expect(screen.queryByText(/no plugins installed/i)).not.toBeInTheDocument();
  });

  it('retries after an error and recovers once it succeeds', async () => {
    api.api.listPlugins.mockRejectedValueOnce(new Error('API Error'));
    api.api.listPlugins.mockResolvedValueOnce({
      plugins: [{ filename: 'a.jar', name: 'PluginA', version: '1.0', enabled: true }],
    });

    renderWithRouter(<Plugins />);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: /retry/i }));

    await waitFor(() => {
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
      expect(screen.getByText('PluginA')).toBeInTheDocument();
    });
  });
});
