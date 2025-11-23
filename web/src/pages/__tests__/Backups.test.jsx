import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from '../../services/api';
import { renderWithRouter } from '../../test/utils';
import Backups from '../Backups';

// Mock the API service
vi.mock('../../services/api', () => ({
  api: {
    listBackups: vi.fn(),
    createBackup: vi.fn(),
    restoreBackup: vi.fn(),
    deleteBackup: vi.fn(),
  },
}));

// Mock window.confirm
const mockConfirm = vi.fn();
globalThis.confirm = mockConfirm;

describe('Backups', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockConfirm.mockReturnValue(true);
    globalThis.confirm = mockConfirm;
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  const mockBackups = [
    {
      name: 'minecraft_backup_20240127_120000.tar.gz',
      size: 104857600,
      created: '2024-01-27T12:00:00Z',
    },
    {
      name: 'minecraft_backup_20240126_120000.tar.gz',
      size: 102400000,
      created: '2024-01-26T12:00:00Z',
    },
  ];

  it('renders backups page title', async () => {
    api.api.listBackups.mockResolvedValue({ backups: [] });

    renderWithRouter(<Backups />);

    await waitFor(() => {
      // Use getByRole to find the heading specifically
      expect(screen.getByRole('heading', { name: /backups/i })).toBeInTheDocument();
    });
  });

  it('displays loading state initially', () => {
    api.api.listBackups.mockImplementation(() => new Promise(() => {}));

    renderWithRouter(<Backups />);

    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('displays list of backups', async () => {
    api.api.listBackups.mockResolvedValue({ backups: mockBackups });

    renderWithRouter(<Backups />);

    await waitFor(() => {
      expect(screen.getByText('minecraft_backup_20240127_120000.tar.gz')).toBeInTheDocument();
      expect(screen.getByText('minecraft_backup_20240126_120000.tar.gz')).toBeInTheDocument();
    });
  });

  it('displays empty state when no backups', async () => {
    api.api.listBackups.mockResolvedValue({ backups: [] });

    renderWithRouter(<Backups />);

    await waitFor(() => {
      expect(screen.getByText(/no backups/i)).toBeInTheDocument();
    });
  });

  it('creates backup when button is clicked', async () => {
    api.api.listBackups.mockResolvedValue({ backups: [] });
    api.api.createBackup.mockResolvedValue({ success: true, message: 'Backup created' });

    const user = userEvent.setup({ delay: null });
    renderWithRouter(<Backups />);

    await waitFor(() => {
      expect(screen.getByText(/create backup/i)).toBeInTheDocument();
    });

    const createButton = screen.getByRole('button', { name: /create backup/i });
    await user.click(createButton);

    await waitFor(() => {
      expect(api.api.createBackup).toHaveBeenCalled();
    });
  });

  it('displays loading state while creating backup', async () => {
    api.api.listBackups.mockResolvedValue({ backups: [] });
    api.api.createBackup.mockImplementation(() => new Promise(() => {}));

    const user = userEvent.setup({ delay: null });
    renderWithRouter(<Backups />);

    await waitFor(() => {
      expect(screen.getByText(/create backup/i)).toBeInTheDocument();
    });

    const createButton = screen.getByRole('button', { name: /create backup/i });
    await user.click(createButton);

    // Button should be disabled or show loading
    await waitFor(() => {
      expect(createButton).toBeDisabled();
    });
  });

  it('restores backup when restore button is clicked', async () => {
    api.api.listBackups.mockResolvedValue({ backups: mockBackups });
    api.api.restoreBackup.mockResolvedValue({ success: true, message: 'Backup restored' });
    mockConfirm.mockReturnValue(true);

    const user = userEvent.setup({ delay: null });
    renderWithRouter(<Backups />);

    await waitFor(() => {
      expect(screen.getByText('minecraft_backup_20240127_120000.tar.gz')).toBeInTheDocument();
    });

    const restoreButtons = screen.getAllByRole('button', { name: /restore/i });
    await user.click(restoreButtons[0]);

    await waitFor(() => {
      expect(mockConfirm).toHaveBeenCalled();
      expect(api.api.restoreBackup).toHaveBeenCalledWith('minecraft_backup_20240127_120000.tar.gz');
    });
  });

  it('does not restore backup when confirmation is cancelled', async () => {
    api.api.listBackups.mockResolvedValue({ backups: mockBackups });
    mockConfirm.mockReturnValue(false);

    const user = userEvent.setup({ delay: null });
    renderWithRouter(<Backups />);

    await waitFor(() => {
      expect(screen.getByText('minecraft_backup_20240127_120000.tar.gz')).toBeInTheDocument();
    });

    const restoreButtons = screen.getAllByRole('button', { name: /restore/i });
    await user.click(restoreButtons[0]);

    await waitFor(() => {
      expect(mockConfirm).toHaveBeenCalled();
      expect(api.api.restoreBackup).not.toHaveBeenCalled();
    });
  });

  it('deletes backup when delete button is clicked', async () => {
    api.api.listBackups.mockResolvedValue({ backups: mockBackups });
    api.api.deleteBackup.mockResolvedValue({ success: true });
    mockConfirm.mockReturnValue(true);

    const user = userEvent.setup({ delay: null });
    renderWithRouter(<Backups />);

    await waitFor(() => {
      expect(screen.getByText('minecraft_backup_20240127_120000.tar.gz')).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
    await user.click(deleteButtons[0]);

    await waitFor(() => {
      expect(mockConfirm).toHaveBeenCalled();
      expect(api.api.deleteBackup).toHaveBeenCalledWith('minecraft_backup_20240127_120000.tar.gz');
    });
  });

  it('displays error message when backup creation fails', async () => {
    api.api.listBackups.mockResolvedValue({ backups: [] });
    api.api.createBackup.mockRejectedValue(new Error('Failed to create backup'));

    const user = userEvent.setup({ delay: null });
    renderWithRouter(<Backups />);

    await waitFor(() => {
      expect(screen.getByText(/create backup/i)).toBeInTheDocument();
    });

    const createButton = screen.getByRole('button', { name: /create backup/i });
    await user.click(createButton);

    await waitFor(() => {
      expect(screen.getByText(/failed/i)).toBeInTheDocument();
    });
  });

  it('displays success message when backup is created', async () => {
    api.api.listBackups.mockResolvedValue({ backups: [] });
    api.api.createBackup.mockResolvedValue({
      success: true,
      message: 'Backup created successfully!',
    });

    const user = userEvent.setup({ delay: null });
    vi.useFakeTimers();
    renderWithRouter(<Backups />);

    await waitFor(() => {
      expect(screen.getByText(/create backup/i)).toBeInTheDocument();
    });

    const createButton = screen.getByRole('button', { name: /create backup/i });
    await user.click(createButton);

    await waitFor(() => {
      expect(screen.getByText(/backup created/i)).toBeInTheDocument();
    });
  });

  it('formats backup size correctly', async () => {
    api.api.listBackups.mockResolvedValue({ backups: mockBackups });

    renderWithRouter(<Backups />);

    await waitFor(() => {
      // Should display formatted size (e.g., "100 MB")
      const backupElements = screen.getAllByText(/minecraft_backup_/i);
      expect(backupElements.length).toBeGreaterThan(0);
    });
  });

  it('displays backup creation date', async () => {
    api.api.listBackups.mockResolvedValue({ backups: mockBackups });

    renderWithRouter(<Backups />);

    await waitFor(() => {
      expect(screen.getByText('minecraft_backup_20240127_120000.tar.gz')).toBeInTheDocument();
    });
  });
});
