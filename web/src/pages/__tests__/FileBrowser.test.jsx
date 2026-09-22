import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from '../../services/api';
import { renderWithRouter } from '../../test/utils';
import FileBrowser from '../FileBrowser';

vi.mock('../../services/api', () => ({
  api: {
    listFiles: vi.fn(),
    readFile: vi.fn(),
    writeFile: vi.fn(),
    deleteFile: vi.fn(),
    uploadFile: vi.fn(),
    downloadFile: vi.fn(),
  },
}));

// Mock window.confirm and window.alert, both used directly by FileBrowser
const mockConfirm = vi.fn();
globalThis.confirm = mockConfirm;
globalThis.alert = vi.fn();

describe('FileBrowser', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockConfirm.mockReturnValue(true);
  });

  const mockFiles = [
    { name: 'config', type: 'directory', path: 'config' },
    { name: 'server.properties', type: 'file', path: 'server.properties', size: 2048 },
  ];

  it('renders the file browser title', async () => {
    api.api.listFiles.mockResolvedValue({ success: true, files: [], path: '' });
    renderWithRouter(<FileBrowser />);
    await waitFor(() => {
      expect(screen.getByText(/file browser/i)).toBeInTheDocument();
    });
  });

  it('lists files and directories', async () => {
    api.api.listFiles.mockResolvedValue({ success: true, files: mockFiles, path: '' });
    renderWithRouter(<FileBrowser />);
    await waitFor(() => {
      expect(screen.getByText('config')).toBeInTheDocument();
      expect(screen.getByText('server.properties')).toBeInTheDocument();
    });
  });

  it('shows the empty state when a directory has no files', async () => {
    api.api.listFiles.mockResolvedValue({ success: true, files: [], path: '' });
    renderWithRouter(<FileBrowser />);
    await waitFor(() => {
      expect(screen.getByText(/no files/i)).toBeInTheDocument();
    });
  });

  it('opens a file on click and shows its content', async () => {
    api.api.listFiles.mockResolvedValue({ success: true, files: mockFiles, path: '' });
    api.api.readFile.mockResolvedValue({ success: true, content: 'motd=A Minecraft Server' });
    const user = userEvent.setup();
    renderWithRouter(<FileBrowser />);

    await waitFor(() => expect(screen.getByText('server.properties')).toBeInTheDocument());
    await user.click(screen.getByText('server.properties'));

    await waitFor(() => {
      expect(api.api.readFile).toHaveBeenCalledWith('server.properties');
      expect(screen.getByText('motd=A Minecraft Server')).toBeInTheDocument();
    });
  });

  it('opens a file via keyboard (Enter), not just click', async () => {
    api.api.listFiles.mockResolvedValue({ success: true, files: mockFiles, path: '' });
    api.api.readFile.mockResolvedValue({ success: true, content: 'motd=A Minecraft Server' });
    const user = userEvent.setup();
    renderWithRouter(<FileBrowser />);

    await waitFor(() => expect(screen.getByText('server.properties')).toBeInTheDocument());
    screen.getByText('server.properties').closest('[role="button"]').focus();
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(api.api.readFile).toHaveBeenCalledWith('server.properties');
    });
  });

  it('deletes a file after confirmation', async () => {
    api.api.listFiles.mockResolvedValue({ success: true, files: mockFiles, path: '' });
    api.api.deleteFile.mockResolvedValue({ success: true });
    const user = userEvent.setup();
    renderWithRouter(<FileBrowser />);

    await waitFor(() => expect(screen.getByText('server.properties')).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /delete server.properties/i }));

    await waitFor(() => {
      expect(mockConfirm).toHaveBeenCalled();
      expect(api.api.deleteFile).toHaveBeenCalledWith('server.properties');
    });
  });

  it('surfaces a fetch failure', async () => {
    api.api.listFiles.mockRejectedValue({ response: { data: { error: 'Permission denied' } } });
    renderWithRouter(<FileBrowser />);
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Permission denied');
    });
  });
});
