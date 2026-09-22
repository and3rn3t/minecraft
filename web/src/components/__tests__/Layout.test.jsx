import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from '../../services/api';
import { renderWithRouter } from '../../test/utils';
import Layout from '../Layout';

vi.mock('../../services/api', () => ({
  api: {
    getCurrentUser: vi.fn(),
    logout: vi.fn(),
  },
}));

describe('Layout', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.api.getCurrentUser.mockResolvedValue({ username: 'matt', role: 'admin' });
  });

  it('renders the sidebar nav and the page content', async () => {
    renderWithRouter(
      <Layout>
        <div>PAGE CONTENT</div>
      </Layout>
    );
    await waitFor(() => {
      expect(screen.getByText('PAGE CONTENT')).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /dashboard/i })).toBeInTheDocument();
    });
  });

  it('marks the active nav link with aria-current', async () => {
    renderWithRouter(
      <Layout>
        <div>PAGE CONTENT</div>
      </Layout>,
      { route: '/backups' }
    );
    await waitFor(() => {
      const backupsLink = screen.getByRole('link', { name: /backups/i });
      expect(backupsLink).toHaveAttribute('aria-current', 'page');
      const dashboardLink = screen.getByRole('link', { name: /dashboard/i });
      expect(dashboardLink).not.toHaveAttribute('aria-current');
    });
  });

  it('toggles the mobile sidebar with an accessible, closeable overlay', async () => {
    const user = userEvent.setup();
    renderWithRouter(
      <Layout>
        <div>PAGE CONTENT</div>
      </Layout>
    );

    const menuButton = screen.getByRole('button', { name: /menu/i });
    expect(menuButton).toHaveAttribute('aria-expanded', 'false');

    await user.click(menuButton);
    expect(menuButton).toHaveAttribute('aria-expanded', 'true');

    const overlay = screen.getByRole('button', { name: /close sidebar/i });
    await user.click(overlay);
    expect(menuButton).toHaveAttribute('aria-expanded', 'false');
  });

  it('logs out via a real button', async () => {
    api.api.logout.mockResolvedValue({ success: true });
    const user = userEvent.setup();
    renderWithRouter(
      <Layout>
        <div>PAGE CONTENT</div>
      </Layout>
    );

    const logoutButton = await screen.findByRole('button', { name: /logout/i });
    await user.click(logoutButton);

    await waitFor(() => {
      expect(api.api.logout).toHaveBeenCalled();
    });
  });
});
