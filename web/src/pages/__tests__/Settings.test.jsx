import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from '../../services/api';
import { renderWithRouter } from '../../test/utils';
import Settings from '../Settings';

vi.mock('../../services/api', () => ({
  api: {
    getCurrentUser: vi.fn(),
    get2FAStatus: vi.fn(),
    setup2FA: vi.fn(),
    verify2FASetup: vi.fn(),
    disable2FA: vi.fn(),
  },
}));

const mockConfirm = vi.fn();
globalThis.confirm = mockConfirm;

describe('Settings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    mockConfirm.mockReturnValue(true);
    api.api.getCurrentUser.mockResolvedValue({
      username: 'matt',
      email: 'matt@example.com',
      role: 'admin',
    });
    api.api.get2FAStatus.mockResolvedValue({ success: true, enabled: false });
  });

  it('renders the settings title and account info', async () => {
    renderWithRouter(<Settings />);
    await waitFor(() => {
      expect(screen.getByText(/^settings$/i)).toBeInTheDocument();
      expect(screen.getByText('matt')).toBeInTheDocument();
      expect(screen.getByText('matt@example.com')).toBeInTheDocument();
    });
  });

  it('shows 2FA as disabled and offers setup', async () => {
    renderWithRouter(<Settings />);
    await waitFor(() => {
      expect(screen.getByText('DISABLED')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /setup 2fa/i })).toBeInTheDocument();
    });
  });

  it('walks through 2FA setup and verification', async () => {
    api.api.setup2FA.mockResolvedValue({
      success: true,
      qr_code: 'abc123',
      secret: 'SECRET123',
    });
    api.api.verify2FASetup.mockResolvedValue({ success: true });
    const user = userEvent.setup();
    renderWithRouter(<Settings />);

    await waitFor(() => expect(screen.getByRole('button', { name: /setup 2fa/i })).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /setup 2fa/i }));

    await waitFor(() => expect(screen.getByText('SECRET123')).toBeInTheDocument());

    const codeInput = screen.getByLabelText(/enter verification code/i);
    await user.type(codeInput, '123456');
    await user.click(screen.getByRole('button', { name: /verify & enable/i }));

    await waitFor(() => {
      expect(api.api.verify2FASetup).toHaveBeenCalledWith('123456');
      expect(screen.getByText(/2fa enabled successfully/i)).toBeInTheDocument();
    });
  });

  it('offers to disable 2FA when already enabled, and requires a password', async () => {
    api.api.get2FAStatus.mockResolvedValue({ success: true, enabled: true });
    api.api.disable2FA.mockResolvedValue({ success: true });
    const user = userEvent.setup();
    renderWithRouter(<Settings />);

    await waitFor(() => expect(screen.getByText('ENABLED')).toBeInTheDocument());

    const disableButton = screen.getByRole('button', { name: /disable 2fa/i });
    expect(disableButton).toBeDisabled();

    await user.type(screen.getByLabelText(/^password$/i), 'hunter2');
    expect(disableButton).not.toBeDisabled();
    await user.click(disableButton);

    await waitFor(() => {
      expect(mockConfirm).toHaveBeenCalled();
      expect(api.api.disable2FA).toHaveBeenCalledWith('hunter2');
    });
  });

  it('saves and removes the API key in localStorage', async () => {
    const user = userEvent.setup();
    renderWithRouter(<Settings />);

    await waitFor(() => expect(screen.getByLabelText(/api key/i)).toBeInTheDocument());
    await user.type(screen.getByLabelText(/api key/i), 'my-secret-key');
    await user.click(screen.getByRole('button', { name: /save api key/i }));

    expect(localStorage.getItem('api_key')).toBe('my-secret-key');
    expect(screen.getByText(/api key saved/i)).toBeInTheDocument();

    await user.clear(screen.getByLabelText(/api key/i));
    await user.click(screen.getByRole('button', { name: /save api key/i }));

    expect(localStorage.getItem('api_key')).toBeNull();
    expect(screen.getByText(/api key removed/i)).toBeInTheDocument();
  });
});
