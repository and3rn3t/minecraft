import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from '../../services/api';
import { renderWithRouter } from '../../test/utils';
import AuditLogs from '../AuditLogs';

vi.mock('../../services/api', () => ({
  api: {
    getAuditLogs: vi.fn(),
  },
}));

describe('AuditLogs', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockLogs = [
    {
      timestamp: '2024-01-27T12:00:00Z',
      username: 'matt',
      action: 'server.start',
      details: { reason: 'manual' },
      ip_address: '192.168.1.5',
    },
  ];

  it('renders the title and lists logs', async () => {
    api.api.getAuditLogs.mockResolvedValue({ success: true, logs: mockLogs, total: 1 });
    renderWithRouter(<AuditLogs />);
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /audit logs/i })).toBeInTheDocument();
      expect(screen.getByText('matt')).toBeInTheDocument();
      expect(screen.getByText('server.start')).toBeInTheDocument();
    });
  });

  it('shows the empty state when there are no logs', async () => {
    api.api.getAuditLogs.mockResolvedValue({ success: true, logs: [], total: 0 });
    renderWithRouter(<AuditLogs />);
    await waitFor(() => {
      expect(screen.getByText(/no audit logs found/i)).toBeInTheDocument();
    });
  });

  it('gives every filter a real accessible label', async () => {
    api.api.getAuditLogs.mockResolvedValue({ success: true, logs: [], total: 0 });
    renderWithRouter(<AuditLogs />);
    await waitFor(() => {
      expect(screen.getByLabelText(/action filter/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/username filter/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/^limit$/i)).toBeInTheDocument();
    });
  });

  it('filters by action, resetting to the first page', async () => {
    api.api.getAuditLogs.mockResolvedValue({ success: true, logs: mockLogs, total: 1 });
    const user = userEvent.setup();
    renderWithRouter(<AuditLogs />);

    await waitFor(() => expect(screen.getByText('matt')).toBeInTheDocument());
    await user.type(screen.getByLabelText(/action filter/i), 'server.start');

    await waitFor(() => {
      expect(api.api.getAuditLogs).toHaveBeenLastCalledWith(100, 0, 'server.start', null);
    });
  });

  it('paginates using the total count', async () => {
    api.api.getAuditLogs.mockResolvedValue({ success: true, logs: mockLogs, total: 250 });
    const user = userEvent.setup();
    renderWithRouter(<AuditLogs />);

    await waitFor(() => expect(screen.getByText(/showing 1-100 of 250/i)).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /next/i }));

    await waitFor(() => {
      expect(api.api.getAuditLogs).toHaveBeenLastCalledWith(100, 100, null, null);
    });
  });

  it('surfaces a fetch failure', async () => {
    api.api.getAuditLogs.mockRejectedValue({
      response: { data: { error: 'Audit log service unavailable' } },
    });
    renderWithRouter(<AuditLogs />);
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Audit log service unavailable');
    });
  });
});
