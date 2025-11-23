import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../../services/api';
import { renderWithRouter } from '../../test/utils';
import Backups from '../Backups';

vi.mock('../../services/api');

describe('Backups', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders backups page title', () => {
    api.listBackups.mockResolvedValue({ backups: [] });

    renderWithRouter(<Backups />);
    expect(screen.getByText('Backups')).toBeInTheDocument();
  });

  it('displays loading state initially', () => {
    api.listBackups.mockImplementation(() => new Promise(() => {}));

    renderWithRouter(<Backups />);
    expect(screen.getByText('Loading backups...')).toBeInTheDocument();
  });

  it('displays backup list', async () => {
    const mockBackups = [
      {
        name: 'minecraft_backup_20250115.tar.gz',
        size: 104857600,
        created: '2025-01-15T10:30:00Z',
      },
    ];

    api.listBackups.mockResolvedValue({ backups: mockBackups });

    renderWithRouter(<Backups />);

    await waitFor(() => {
      expect(screen.getByText(mockBackups[0].name)).toBeInTheDocument();
    });
  });

  it('formats backup size correctly', async () => {
    const mockBackups = [
      {
        name: 'backup.tar.gz',
        size: 104857600, // 100 MB
        created: '2025-01-15T10:30:00Z',
      },
    ];

    api.listBackups.mockResolvedValue({ backups: mockBackups });

    renderWithRouter(<Backups />);

    await waitFor(() => {
      expect(screen.getByText(/100\.00 MB/)).toBeInTheDocument();
    });
  });

  it('creates backup when button is clicked', async () => {
    const user = userEvent.setup();
    api.listBackups.mockResolvedValue({ backups: [] });
    api.createBackup.mockResolvedValue({ success: true, message: 'Backup created' });

    renderWithRouter(<Backups />);

    await waitFor(() => {
      const createButton = screen.getByText('Create Backup');
      expect(createButton).toBeInTheDocument();
    });

    const createButton = screen.getByText('Create Backup');
    await user.click(createButton);

    await waitFor(() => {
      expect(api.createBackup).toHaveBeenCalled();
    });
  });

  it('restores backup when restore button is clicked', async () => {
    const user = userEvent.setup();
    const mockBackups = [
      {
        name: 'minecraft_backup_20250115.tar.gz',
        size: 104857600,
        created: '2025-01-15T10:30:00Z',
      },
    ];

    api.listBackups.mockResolvedValue({ backups: mockBackups });
    api.restoreBackup.mockResolvedValue({ success: true });

    // Mock window.confirm
    window.confirm = vi.fn(() => true);

    renderWithRouter(<Backups />);

    await waitFor(() => {
      const restoreButton = screen.getByText('Restore');
      expect(restoreButton).toBeInTheDocument();
    });

    const restoreButton = screen.getByText('Restore');
    await user.click(restoreButton);

    await waitFor(() => {
      expect(window.confirm).toHaveBeenCalled();
      expect(api.restoreBackup).toHaveBeenCalled();
    });
  });

  it('deletes backup when delete button is clicked', async () => {
    const user = userEvent.setup();
    const mockBackups = [
      {
        name: 'minecraft_backup_20250115.tar.gz',
        size: 104857600,
        created: '2025-01-15T10:30:00Z',
      },
    ];

    api.listBackups.mockResolvedValue({ backups: mockBackups });
    api.deleteBackup.mockResolvedValue({ success: true });

    // Mock window.confirm
    window.confirm = vi.fn(() => true);

    renderWithRouter(<Backups />);

    await waitFor(() => {
      const deleteButton = screen.getByText('Delete');
      expect(deleteButton).toBeInTheDocument();
    });

    const deleteButton = screen.getByText('Delete');
    await user.click(deleteButton);

    await waitFor(() => {
      expect(window.confirm).toHaveBeenCalled();
      expect(api.deleteBackup).toHaveBeenCalled();
    });
  });

  it('displays no backups message when empty', async () => {
    api.listBackups.mockResolvedValue({ backups: [] });

    renderWithRouter(<Backups />);

    await waitFor(() => {
      expect(screen.getByText('No backups found')).toBeInTheDocument();
    });
  });
});
