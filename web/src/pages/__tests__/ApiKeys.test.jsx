import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from '../../services/api';
import { renderWithRouter } from '../../test/utils';
import ApiKeys from '../ApiKeys';

vi.mock('../../services/api', () => ({
  api: {
    listApiKeys: vi.fn(),
    createApiKey: vi.fn(),
    deleteApiKey: vi.fn(),
    enableApiKey: vi.fn(),
    disableApiKey: vi.fn(),
    updateApiKeyScope: vi.fn(),
  },
}));

const mockConfirm = vi.fn();
globalThis.confirm = mockConfirm;

describe('ApiKeys', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockConfirm.mockReturnValue(true);
  });

  const mockKey = {
    id: 'key-1',
    name: 'Webhook',
    description: 'CI integration',
    role: 'user',
    enabled: true,
    created: '2024-01-01',
  };

  it('renders the title and lists keys', async () => {
    api.api.listApiKeys.mockResolvedValue({ keys: [mockKey] });
    renderWithRouter(<ApiKeys />);
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /api keys/i })).toBeInTheDocument();
      expect(screen.getByText('Webhook')).toBeInTheDocument();
    });
  });

  it('shows the empty state when there are no keys', async () => {
    api.api.listApiKeys.mockResolvedValue({ keys: [] });
    renderWithRouter(<ApiKeys />);
    await waitFor(() => {
      expect(screen.getByText(/no api keys found/i)).toBeInTheDocument();
    });
  });

  it('opens the create form as a real dialog', async () => {
    api.api.listApiKeys.mockResolvedValue({ keys: [] });
    const user = userEvent.setup();
    renderWithRouter(<ApiKeys />);

    await waitFor(() => expect(screen.getByText(/no api keys found/i)).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /create api key/i }));

    const dialog = screen.getByRole('dialog', { name: /create new api key/i });
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(screen.getByLabelText(/^key name/i)).toBeInTheDocument();
  });

  it('creates a key and shows it once, in its own dialog', async () => {
    api.api.listApiKeys.mockResolvedValue({ keys: [] });
    api.api.createApiKey.mockResolvedValue({ key: 'mc_abc123def456', message: 'Created' });
    const user = userEvent.setup();
    // user-event's own setup() installs its clipboard emulation, overwriting
    // anything set up before it — so this has to come after.
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: vi.fn().mockResolvedValue() },
      writable: true,
      configurable: true,
    });
    renderWithRouter(<ApiKeys />);

    await waitFor(() => expect(screen.getByText(/no api keys found/i)).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /create api key/i }));
    await user.type(screen.getByLabelText(/^key name/i), 'Webhook');
    await user.click(screen.getByRole('button', { name: /^create key$/i }));

    await waitFor(() => {
      expect(api.api.createApiKey).toHaveBeenCalledWith('Webhook', '', 'user');
      expect(screen.getByRole('dialog', { name: /new api key created/i })).toBeInTheDocument();
      expect(screen.getByText('mc_abc123def456')).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /copy/i }));
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('mc_abc123def456');

    await user.click(screen.getByRole('button', { name: /saved the key/i }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('toggles and deletes a key', async () => {
    api.api.listApiKeys.mockResolvedValue({ keys: [mockKey] });
    api.api.disableApiKey.mockResolvedValue({ success: true, message: 'Disabled' });
    api.api.deleteApiKey.mockResolvedValue({ success: true, message: 'Deleted' });
    const user = userEvent.setup();
    renderWithRouter(<ApiKeys />);

    await waitFor(() => expect(screen.getByText('Webhook')).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /disable/i }));
    await waitFor(() => expect(api.api.disableApiKey).toHaveBeenCalledWith('key-1'));

    await user.click(screen.getByRole('button', { name: /delete/i }));
    await waitFor(() => {
      expect(mockConfirm).toHaveBeenCalled();
      expect(api.api.deleteApiKey).toHaveBeenCalledWith('key-1');
    });
  });

  it('surfaces a fetch failure', async () => {
    api.api.listApiKeys.mockRejectedValue(new Error('network error'));
    renderWithRouter(<ApiKeys />);
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/failed to load api keys/i);
    });
  });
});
