import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from '../../services/api';
import { renderWithRouter } from '../../test/utils';
import Oracle from '../Oracle';

vi.mock('../../services/api', () => ({
  api: {
    getOracleStatus: vi.fn(),
    getOracleExchanges: vi.fn(),
    getOracleQuests: vi.fn(),
    enableOracle: vi.fn(),
    disableOracle: vi.fn(),
    updateOracleSettings: vi.fn(),
  },
}));

const aStatus = (overrides = {}) => ({
  enabled: true,
  allowlist: ['Jonah', 'Silas'],
  rate_limit_per_minute: 4,
  color: 'aqua',
  has_api_key: true,
  has_responder: true,
  ...overrides,
});

const anExchange = (overrides = {}) => ({
  player: 'Jonah',
  message: 'how do I make a beacon',
  outcome: 'banter',
  summary: 'Mine a nether star from the Wither!',
  timestamp: '2026-09-19T12:00:00+00:00',
  ...overrides,
});

const aQuest = (overrides = {}) => ({
  id: 'abc123',
  player: 'Silas',
  title: 'Diamond Dash',
  description: 'Mine 5 diamonds before sundown.',
  objective_type: 'gather',
  target: 'diamond',
  quantity: 5,
  difficulty: 'easy',
  reward_suggestion: 'a glowing pickaxe',
  delivered: true,
  claimed: false,
  ...overrides,
});

const setup = ({ status = aStatus(), exchanges = [], quests = [] } = {}) => {
  api.api.getOracleStatus.mockResolvedValue(status);
  api.api.getOracleExchanges.mockResolvedValue(exchanges);
  api.api.getOracleQuests.mockResolvedValue(quests);
};

describe('Oracle', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the page title', async () => {
    setup();
    renderWithRouter(<Oracle />);

    await waitFor(() => {
      expect(screen.getByText(/^THE ORACLE$/)).toBeInTheDocument();
    });
  });

  it('shows a loading state first', () => {
    api.api.getOracleStatus.mockImplementation(() => new Promise(() => {}));
    api.api.getOracleExchanges.mockImplementation(() => new Promise(() => {}));
    api.api.getOracleQuests.mockImplementation(() => new Promise(() => {}));
    renderWithRouter(<Oracle />);

    expect(screen.getByText(/consulting the oracle/i)).toBeInTheDocument();
  });

  it('shows ENABLED and a DISABLE button when on', async () => {
    setup();
    renderWithRouter(<Oracle />);

    await waitFor(() => {
      expect(screen.getByText('ENABLED')).toBeInTheDocument();
      expect(screen.getByText('DISABLE')).toBeInTheDocument();
    });
  });

  it('shows DISABLED and an ENABLE button when off', async () => {
    setup({ status: aStatus({ enabled: false }) });
    renderWithRouter(<Oracle />);

    await waitFor(() => {
      expect(screen.getByText('DISABLED')).toBeInTheDocument();
      expect(screen.getByText('ENABLE')).toBeInTheDocument();
    });
  });

  it('warns when enabled but no API key is configured', async () => {
    setup({ status: aStatus({ has_api_key: false }) });
    renderWithRouter(<Oracle />);

    await waitFor(() => {
      expect(screen.getByText(/no anthropic_api_key is set/i)).toBeInTheDocument();
    });
  });

  it('disables the Oracle and shows the result', async () => {
    const user = userEvent.setup();
    setup();
    api.api.disableOracle.mockResolvedValue({
      success: true,
      status: aStatus({ enabled: false }),
    });

    renderWithRouter(<Oracle />);
    await waitFor(() => expect(screen.getByText('DISABLE')).toBeInTheDocument());

    await user.click(screen.getByText('DISABLE'));

    await waitFor(() => {
      expect(screen.getByText('DISABLED')).toBeInTheDocument();
    });
  });

  it('shows the reason when a control is refused', async () => {
    const user = userEvent.setup();
    setup();
    api.api.disableOracle.mockRejectedValue({
      response: { status: 409, data: { error: 'Cannot disable right now' } },
    });

    renderWithRouter(<Oracle />);
    await waitFor(() => expect(screen.getByText('DISABLE')).toBeInTheDocument());

    await user.click(screen.getByText('DISABLE'));

    await waitFor(() => {
      expect(screen.getByText(/cannot disable right now/i)).toBeInTheDocument();
    });
  });

  it('treats a server error as an error, not a refusal', async () => {
    const user = userEvent.setup();
    setup();
    api.api.disableOracle.mockRejectedValue({
      response: { status: 500, data: { error: 'Internal server error' } },
    });

    renderWithRouter(<Oracle />);
    await waitFor(() => expect(screen.getByText('DISABLE')).toBeInTheDocument());

    await user.click(screen.getByText('DISABLE'));

    await waitFor(() => {
      expect(screen.getByText(/internal server error/i)).toBeInTheDocument();
    });
    const alert = screen.getByText(/internal server error/i).closest('[role="alert"]');
    expect(alert.className).toMatch(/bg-minecraft-danger/);
  });

  it('pre-fills the settings form from the loaded status', async () => {
    setup({ status: aStatus({ allowlist: ['Jonah'], rate_limit_per_minute: 7 }) });
    renderWithRouter(<Oracle />);

    await waitFor(() => {
      expect(screen.getByDisplayValue('Jonah')).toBeInTheDocument();
      expect(screen.getByDisplayValue('7')).toBeInTheDocument();
    });
  });

  it('saves settings with a parsed allowlist and rate limit', async () => {
    const user = userEvent.setup();
    setup();
    api.api.updateOracleSettings.mockResolvedValue({
      success: true,
      status: aStatus({ allowlist: ['Jonah', 'Silas', 'Matt'], rate_limit_per_minute: 10 }),
    });

    renderWithRouter(<Oracle />);
    await waitFor(() => expect(screen.getByText('SAVE SETTINGS')).toBeInTheDocument());

    const allowlistField = screen.getByLabelText(/allowlist/i);
    await user.clear(allowlistField);
    await user.type(allowlistField, 'Jonah, Silas, Matt');

    const rateLimitField = screen.getByLabelText(/rate limit/i);
    await user.clear(rateLimitField);
    await user.type(rateLimitField, '10');

    await user.click(screen.getByText('SAVE SETTINGS'));

    await waitFor(() => {
      expect(api.api.updateOracleSettings).toHaveBeenCalledWith({
        allowlist: ['Jonah', 'Silas', 'Matt'],
        rate_limit_per_minute: 10,
      });
    });
  });

  it('shows recent exchanges', async () => {
    setup({ exchanges: [anExchange()] });
    renderWithRouter(<Oracle />);

    await waitFor(() => {
      expect(screen.getByText(/how do i make a beacon/i)).toBeInTheDocument();
      expect(screen.getByText(/mine a nether star/i)).toBeInTheDocument();
      expect(screen.getByText('banter')).toBeInTheDocument();
    });
  });

  it('says nothing yet when there are no exchanges', async () => {
    setup();
    renderWithRouter(<Oracle />);

    await waitFor(() => {
      expect(screen.getByText('NOTHING YET')).toBeInTheDocument();
    });
  });

  it('shows recent quests', async () => {
    setup({ quests: [aQuest()] });
    renderWithRouter(<Oracle />);

    await waitFor(() => {
      expect(screen.getByText('Diamond Dash')).toBeInTheDocument();
      expect(screen.getByText('DELIVERED')).toBeInTheDocument();
      expect(screen.getByText(/for silas/i)).toBeInTheDocument();
    });
  });

  it('shows a not-delivered badge for an undelivered quest', async () => {
    setup({ quests: [aQuest({ delivered: false })] });
    renderWithRouter(<Oracle />);

    await waitFor(() => {
      expect(screen.getByText('NOT DELIVERED')).toBeInTheDocument();
    });
  });

  it('loads once on mount, not twice', async () => {
    setup();
    renderWithRouter(<Oracle />);

    await waitFor(() => expect(api.api.getOracleStatus).toHaveBeenCalled());
    expect(api.api.getOracleStatus).toHaveBeenCalledTimes(1);
  });

  it('reports a load failure', async () => {
    api.api.getOracleStatus.mockRejectedValue(new Error('network down'));
    api.api.getOracleExchanges.mockResolvedValue([]);
    api.api.getOracleQuests.mockResolvedValue([]);
    renderWithRouter(<Oracle />);

    await waitFor(() => {
      expect(screen.getByText(/could not load the oracle/i)).toBeInTheDocument();
    });
  });
});
