import { fireEvent, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../../services/api';
import { renderWithRouter } from '../../test/utils';
import ConfigFiles from '../ConfigFiles';

vi.mock('../../services/api');

describe('ConfigFiles', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders config files page title', async () => {
    api.listConfigFiles.mockResolvedValue({ files: [] });
    // Mock API call that AuthProvider makes on mount
    api.getCurrentUser.mockRejectedValue(new Error('Not authenticated'));

    renderWithRouter(<ConfigFiles />);
    // Wait for both AuthProvider and ConfigFiles to finish loading
    await waitFor(() => {
      expect(screen.getByText(/configuration files/i)).toBeInTheDocument();
    });
  });

  it('displays loading state initially', () => {
    api.listConfigFiles.mockImplementation(() => new Promise(() => {}));

    renderWithRouter(<ConfigFiles />);
    expect(screen.getByText(/loading configuration files/i)).toBeInTheDocument();
  });

  it('displays config file list', async () => {
    const mockFiles = [
      {
        name: 'server.properties',
        path: 'data/server.properties',
        exists: true,
        size: 1024,
      },
      {
        name: 'docker-compose.yml',
        path: 'docker-compose.yml',
        exists: true,
        size: 2048,
      },
    ];

    api.listConfigFiles.mockResolvedValue({ files: mockFiles });

    renderWithRouter(<ConfigFiles />);

    await waitFor(() => {
      expect(screen.getByText('server.properties')).toBeInTheDocument();
      expect(screen.getByText('docker-compose.yml')).toBeInTheDocument();
    });
  });

  it('loads file content when file is selected', async () => {
    const mockFiles = [
      {
        name: 'server.properties',
        path: 'data/server.properties',
        exists: true,
        size: 1024,
      },
    ];

    api.listConfigFiles.mockResolvedValue({ files: mockFiles });
    api.getConfigFile.mockResolvedValue({
      name: 'server.properties',
      content: '# Test config\nkey=value\n',
      size: 1024,
    });

    renderWithRouter(<ConfigFiles />);

    await waitFor(() => {
      expect(screen.getByText('server.properties')).toBeInTheDocument();
    });

    const fileButton = screen.getByText('server.properties').closest('button');
    await userEvent.click(fileButton);

    await waitFor(() => {
      expect(api.getConfigFile).toHaveBeenCalledWith('server.properties');
    });
  });

  it('displays error message when file load fails', async () => {
    const mockFiles = [
      {
        name: 'server.properties',
        path: 'data/server.properties',
        exists: true,
        size: 1024,
      },
    ];

    api.listConfigFiles.mockResolvedValue({ files: mockFiles });
    api.getConfigFile.mockRejectedValue(new Error('File not found'));

    renderWithRouter(<ConfigFiles />);

    await waitFor(() => {
      const fileButton = screen.getByText('server.properties').closest('button');
      fireEvent.click(fileButton);
    });

    await waitFor(() => {
      expect(screen.getByText(/File not found/i)).toBeInTheDocument();
    });
  });

  it('displays no file selected message initially', async () => {
    api.listConfigFiles.mockResolvedValue({ files: [] });

    renderWithRouter(<ConfigFiles />);

    await waitFor(() => {
      expect(screen.getByText(/no file selected/i)).toBeInTheDocument();
    });
  });
});
