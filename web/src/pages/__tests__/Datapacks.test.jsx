import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from '../../services/api';
import { renderWithRouter } from '../../test/utils';
import Datapacks from '../Datapacks';

vi.mock('../../services/api', () => ({
  api: {
    listDatapacks: vi.fn(),
    installDatapack: vi.fn(),
    enableDatapack: vi.fn(),
    disableDatapack: vi.fn(),
    deleteDatapack: vi.fn(),
  },
}));

const mockConfirm = vi.fn();
globalThis.confirm = mockConfirm;

describe('Datapacks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockConfirm.mockReturnValue(true);
  });

  const enabledPack = { name: 'family', enabled: true, world: 'world' };
  const availablePack = { name: 'treasure', enabled: false, world: 'world' };

  it('renders the datapacks title', async () => {
    api.api.listDatapacks.mockResolvedValue({ datapacks: [] });
    renderWithRouter(<Datapacks />);
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /datapacks/i })).toBeInTheDocument();
    });
  });

  it('displays loading state initially', () => {
    api.api.listDatapacks.mockImplementation(() => new Promise(() => {}));
    renderWithRouter(<Datapacks />);
    expect(screen.getByText(/loading datapacks/i)).toBeInTheDocument();
  });

  it('shows the empty state when there are no datapacks', async () => {
    api.api.listDatapacks.mockResolvedValue({ datapacks: [] });
    renderWithRouter(<Datapacks />);
    await waitFor(() => {
      expect(screen.getByText(/no datapacks yet/i)).toBeInTheDocument();
    });
  });

  it('lists datapacks with enabled/available status', async () => {
    api.api.listDatapacks.mockResolvedValue({ datapacks: [enabledPack, availablePack] });
    renderWithRouter(<Datapacks />);
    await waitFor(() => {
      expect(screen.getByText('family')).toBeInTheDocument();
      expect(screen.getByText('treasure')).toBeInTheDocument();
      expect(screen.getByText('ENABLED')).toBeInTheDocument();
      expect(screen.getByText('AVAILABLE')).toBeInTheDocument();
    });
  });

  it('surfaces a fetch failure', async () => {
    api.api.listDatapacks.mockRejectedValue({
      response: { data: { error: 'Datapacks unavailable' } },
    });
    renderWithRouter(<Datapacks />);
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Datapacks unavailable');
    });
  });

  it('opens the install form with real labels for every field', async () => {
    api.api.listDatapacks.mockResolvedValue({ datapacks: [] });
    const user = userEvent.setup();
    renderWithRouter(<Datapacks />);

    await waitFor(() => expect(screen.getByText(/no datapacks yet/i)).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /install datapack/i }));

    expect(screen.getByLabelText(/^name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/source/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/zip url/i)).toBeInTheDocument();
  });

  it('switches to a file input when source is set to upload', async () => {
    api.api.listDatapacks.mockResolvedValue({ datapacks: [] });
    const user = userEvent.setup();
    renderWithRouter(<Datapacks />);

    await waitFor(() => expect(screen.getByText(/no datapacks yet/i)).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /install datapack/i }));
    await user.selectOptions(screen.getByLabelText(/source/i), 'file');

    expect(screen.getByLabelText(/zip file/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/zip url/i)).not.toBeInTheDocument();
  });

  it('installs a datapack from a URL', async () => {
    api.api.listDatapacks.mockResolvedValue({ datapacks: [] });
    api.api.installDatapack.mockResolvedValue({ success: true });
    const user = userEvent.setup();
    renderWithRouter(<Datapacks />);

    await waitFor(() => expect(screen.getByText(/no datapacks yet/i)).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /install datapack/i }));
    await user.type(screen.getByLabelText(/^name/i), 'family');
    await user.type(screen.getByLabelText(/zip url/i), 'https://example.com/family.zip');
    await user.click(screen.getByRole('button', { name: /install & enable/i }));

    await waitFor(() => {
      expect(api.api.installDatapack).toHaveBeenCalledWith(
        expect.objectContaining({ name: 'family', url: 'https://example.com/family.zip', source: 'url' })
      );
    });
  });

  it('enables an available datapack', async () => {
    api.api.listDatapacks.mockResolvedValue({ datapacks: [availablePack] });
    api.api.enableDatapack.mockResolvedValue({ success: true });
    const user = userEvent.setup();
    renderWithRouter(<Datapacks />);

    await waitFor(() => expect(screen.getByText('treasure')).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /^enable$/i }));

    await waitFor(() => {
      expect(api.api.enableDatapack).toHaveBeenCalledWith('treasure');
    });
  });

  it('disables an enabled datapack', async () => {
    api.api.listDatapacks.mockResolvedValue({ datapacks: [enabledPack] });
    api.api.disableDatapack.mockResolvedValue({ success: true });
    const user = userEvent.setup();
    renderWithRouter(<Datapacks />);

    await waitFor(() => expect(screen.getByText('family')).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /^disable$/i }));

    await waitFor(() => {
      expect(api.api.disableDatapack).toHaveBeenCalledWith('family');
    });
  });

  it('deletes a datapack after confirmation', async () => {
    api.api.listDatapacks.mockResolvedValue({ datapacks: [enabledPack] });
    api.api.deleteDatapack.mockResolvedValue({ success: true });
    const user = userEvent.setup();
    renderWithRouter(<Datapacks />);

    await waitFor(() => expect(screen.getByText('family')).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /^delete$/i }));

    await waitFor(() => {
      expect(mockConfirm).toHaveBeenCalled();
      expect(api.api.deleteDatapack).toHaveBeenCalledWith('family');
    });
  });

  it('does not delete when the confirmation is declined', async () => {
    mockConfirm.mockReturnValue(false);
    api.api.listDatapacks.mockResolvedValue({ datapacks: [enabledPack] });
    const user = userEvent.setup();
    renderWithRouter(<Datapacks />);

    await waitFor(() => expect(screen.getByText('family')).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /^delete$/i }));

    expect(api.api.deleteDatapack).not.toHaveBeenCalled();
  });
});
