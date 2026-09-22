import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from '../../services/api';
import { renderWithRouter } from '../../test/utils';
import Users from '../Users';

vi.mock('../../services/api', () => ({
  api: {
    getCurrentUser: vi.fn(),
    listUsers: vi.fn(),
    listRoles: vi.fn(),
    updateUserRole: vi.fn(),
    deleteUser: vi.fn(),
    enableUser: vi.fn(),
    disableUser: vi.fn(),
  },
}));

const mockConfirm = vi.fn();
globalThis.confirm = mockConfirm;

describe('Users', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockConfirm.mockReturnValue(true);
    api.api.getCurrentUser.mockResolvedValue({ username: 'matt', role: 'admin' });
    api.api.listRoles.mockResolvedValue({
      roles: {
        admin: { permission_count: 20 },
        operator: { permission_count: 10 },
        user: { permission_count: 3 },
      },
    });
  });

  const mockUsers = [
    { username: 'matt', role: 'admin', enabled: true, email: 'matt@example.com', created: '2024-01-01' },
    { username: 'silas', role: 'user', enabled: true, email: '', created: '2024-01-02' },
  ];

  it('renders the title and lists users', async () => {
    api.api.listUsers.mockResolvedValue({ users: mockUsers });
    renderWithRouter(<Users />);
    await waitFor(() => {
      expect(screen.getByText(/user management/i)).toBeInTheDocument();
      expect(screen.getByText('matt')).toBeInTheDocument();
      expect(screen.getByText('silas')).toBeInTheDocument();
    });
  });

  it('shows the empty state when there are no users', async () => {
    api.api.listUsers.mockResolvedValue({ users: [] });
    renderWithRouter(<Users />);
    await waitFor(() => {
      expect(screen.getByText(/no users found/i)).toBeInTheDocument();
    });
  });

  it("disables actions on the current user's own row", async () => {
    api.api.listUsers.mockResolvedValue({ users: mockUsers });
    renderWithRouter(<Users />);

    await waitFor(() => expect(screen.getByText('matt')).toBeInTheDocument());
    const row = screen.getByText('matt').closest('tr');
    for (const button of row.querySelectorAll('button')) {
      expect(button).toBeDisabled();
    }
  });

  it('opens the role modal as a real dialog and changes role', async () => {
    api.api.listUsers.mockResolvedValue({ users: mockUsers });
    api.api.updateUserRole.mockResolvedValue({ success: true, message: 'Role updated' });
    const user = userEvent.setup();
    renderWithRouter(<Users />);

    await waitFor(() => expect(screen.getByText('silas')).toBeInTheDocument());
    const row = screen.getByText('silas').closest('tr');
    await user.click(within(row).getByRole('button', { name: /change role/i }));

    const dialog = screen.getByRole('dialog', { name: /change role for silas/i });
    expect(dialog).toHaveAttribute('aria-modal', 'true');

    await user.click(within(dialog).getByRole('button', { name: /^operator/i }));

    await waitFor(() => {
      expect(api.api.updateUserRole).toHaveBeenCalledWith('silas', 'operator');
      expect(screen.getByText('Role updated')).toBeInTheDocument();
    });
  });

  it('closes the role modal on Escape', async () => {
    api.api.listUsers.mockResolvedValue({ users: mockUsers });
    const user = userEvent.setup();
    renderWithRouter(<Users />);

    await waitFor(() => expect(screen.getByText('silas')).toBeInTheDocument());
    const row = screen.getByText('silas').closest('tr');
    await user.click(within(row).getByRole('button', { name: /change role/i }));

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('toggles enable/disable for another user', async () => {
    api.api.listUsers.mockResolvedValue({ users: mockUsers });
    api.api.disableUser.mockResolvedValue({ success: true, message: 'User disabled successfully' });
    const user = userEvent.setup();
    renderWithRouter(<Users />);

    await waitFor(() => expect(screen.getByText('silas')).toBeInTheDocument());
    const row = screen.getByText('silas').closest('tr');
    await user.click(within(row).getByRole('button', { name: /disable/i }));

    await waitFor(() => {
      expect(api.api.disableUser).toHaveBeenCalledWith('silas');
    });
  });

  it('deletes a user after confirmation', async () => {
    api.api.listUsers.mockResolvedValue({ users: mockUsers });
    api.api.deleteUser.mockResolvedValue({ success: true, message: 'User deleted successfully' });
    const user = userEvent.setup();
    renderWithRouter(<Users />);

    await waitFor(() => expect(screen.getByText('silas')).toBeInTheDocument());
    const row = screen.getByText('silas').closest('tr');
    await user.click(within(row).getByRole('button', { name: /delete/i }));

    await waitFor(() => {
      expect(mockConfirm).toHaveBeenCalled();
      expect(api.api.deleteUser).toHaveBeenCalledWith('silas');
    });
  });

  it('surfaces a fetch failure', async () => {
    api.api.listUsers.mockRejectedValue(new Error('network error'));
    renderWithRouter(<Users />);
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/failed to load users/i);
    });
  });
});
