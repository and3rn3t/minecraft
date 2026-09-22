import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from '../../services/api';
import { renderWithRouter } from '../../test/utils';
import DynamicDNS from '../DynamicDNS';

vi.mock('../../services/api', () => ({
  api: {
    getDdnsStatus: vi.fn(),
    getDdnsConfig: vi.fn(),
    updateDdns: vi.fn(),
    saveDdnsConfig: vi.fn(),
  },
}));

describe('DynamicDNS', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.api.getDdnsStatus.mockResolvedValue({ success: true, status: 'Last updated: never' });
    api.api.getDdnsConfig.mockResolvedValue({ content: 'PROVIDER=none', is_example: false });
  });

  it('renders the title and current status', async () => {
    renderWithRouter(<DynamicDNS />);
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /dynamic dns/i })).toBeInTheDocument();
      expect(screen.getByText('Last updated: never')).toBeInTheDocument();
    });
  });

  it('flags an example config', async () => {
    api.api.getDdnsConfig.mockResolvedValue({ content: 'PROVIDER=none', is_example: true });
    renderWithRouter(<DynamicDNS />);
    await waitFor(() => {
      expect(screen.getByText(/using example config/i)).toBeInTheDocument();
    });
  });

  it('gives the config editor a real accessible label', async () => {
    renderWithRouter(<DynamicDNS />);
    await waitFor(() => {
      expect(screen.getByLabelText(/ddns configuration/i)).toHaveValue('PROVIDER=none');
    });
  });

  it('triggers an update and shows the result', async () => {
    api.api.updateDdns.mockResolvedValue({ success: true });
    const user = userEvent.setup();
    renderWithRouter(<DynamicDNS />);

    await waitFor(() => expect(screen.getByRole('button', { name: /update now/i })).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /update now/i }));

    await waitFor(() => {
      expect(api.api.updateDdns).toHaveBeenCalled();
      expect(screen.getByText(/ddns updated successfully/i)).toBeInTheDocument();
    });
  });

  it('saves edited configuration', async () => {
    api.api.saveDdnsConfig.mockResolvedValue({ success: true });
    const user = userEvent.setup();
    renderWithRouter(<DynamicDNS />);

    const textarea = await screen.findByLabelText(/ddns configuration/i);
    await user.clear(textarea);
    await user.type(textarea, 'PROVIDER=cloudflare');
    await user.click(screen.getByRole('button', { name: /save configuration/i }));

    await waitFor(() => {
      expect(api.api.saveDdnsConfig).toHaveBeenCalledWith('PROVIDER=cloudflare');
      expect(screen.getByText(/configuration saved successfully/i)).toBeInTheDocument();
    });
  });

  it('surfaces an update failure', async () => {
    api.api.updateDdns.mockResolvedValue({ success: false, error: 'No provider configured' });
    const user = userEvent.setup();
    renderWithRouter(<DynamicDNS />);

    await waitFor(() => expect(screen.getByRole('button', { name: /update now/i })).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /update now/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('No provider configured');
    });
  });
});
