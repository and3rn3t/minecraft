import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from '../../services/api';
import { renderWithRouter } from '../../test/utils';
import Bedtime from '../Bedtime';

vi.mock('../../services/api', () => ({
  api: {
    getBedtime: vi.fn(),
    extendBedtime: vi.fn(),
    skipBedtime: vi.fn(),
    startBedtimeNow: vi.fn(),
  },
}));

const aStatus = (overrides = {}) => ({
  enabled: true,
  closed: false,
  skipped_tonight: false,
  next_bedtime: '2026-09-21T20:30',
  seconds_until_bedtime: 1800,
  opens_at: null,
  extensions_used: 0,
  extensions_allowed: 1,
  extend_minutes: 15,
  action: 'stop',
  weeknight_bedtime: '20:30',
  weekend_bedtime: '21:30',
  wake_time: '07:00',
  ...overrides,
});

describe('Bedtime', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the page title', async () => {
    api.api.getBedtime.mockResolvedValue(aStatus());
    renderWithRouter(<Bedtime />);

    await waitFor(() => {
      expect(screen.getByText(/^BEDTIME$/)).toBeInTheDocument();
    });
  });

  it('shows a loading state first', () => {
    api.api.getBedtime.mockImplementation(() => new Promise(() => {}));
    renderWithRouter(<Bedtime />);

    expect(screen.getByText(/checking the clock/i)).toBeInTheDocument();
  });

  it('shows the countdown in hours and minutes', async () => {
    api.api.getBedtime.mockResolvedValue(aStatus({ seconds_until_bedtime: 5400 }));
    renderWithRouter(<Bedtime />);

    await waitFor(() => expect(screen.getByText('1H 30M')).toBeInTheDocument());
  });

  it('shows minutes alone when under an hour', async () => {
    api.api.getBedtime.mockResolvedValue(aStatus({ seconds_until_bedtime: 600 }));
    renderWithRouter(<Bedtime />);

    await waitFor(() => expect(screen.getByText('10M')).toBeInTheDocument());
  });

  it('says the server is closed during the window', async () => {
    api.api.getBedtime.mockResolvedValue(
      aStatus({ closed: true, seconds_until_bedtime: null, opens_at: '2026-09-22T07:00' })
    );
    renderWithRouter(<Bedtime />);

    await waitFor(() => {
      expect(screen.getByText(/goodnight/i)).toBeInTheDocument();
      expect(screen.getByText(/opens at 07:00/i)).toBeInTheDocument();
    });
  });

  it('explains how to turn bedtime on when it is off', async () => {
    api.api.getBedtime.mockResolvedValue(aStatus({ enabled: false }));
    renderWithRouter(<Bedtime />);

    await waitFor(() => {
      expect(screen.getByText(/bedtime is off/i)).toBeInTheDocument();
      expect(screen.getByText(/bedtime\.conf/i)).toBeInTheDocument();
    });
  });

  it('extends bedtime and shows the result', async () => {
    const user = userEvent.setup();
    api.api.getBedtime.mockResolvedValue(aStatus());
    api.api.extendBedtime.mockResolvedValue({
      success: true,
      message: 'Extended by 15 minutes',
      status: aStatus({ extensions_used: 1 }),
    });

    renderWithRouter(<Bedtime />);
    await waitFor(() => expect(screen.getByText(/\+15 MINUTES/)).toBeInTheDocument());

    await user.click(screen.getByText(/\+15 MINUTES/));

    await waitFor(() => {
      expect(screen.getByText(/extended by 15 minutes/i)).toBeInTheDocument();
    });
  });

  it('disables the extend button when none are left', async () => {
    api.api.getBedtime.mockResolvedValue(aStatus({ extensions_used: 1 }));
    renderWithRouter(<Bedtime />);

    await waitFor(() => {
      expect(screen.getByText(/0 LEFT/)).toBeDisabled();
    });
  });

  it('shows the reason when a control is refused', async () => {
    // A 409 carries a reason worth reading, not a generic failure.
    const user = userEvent.setup();
    api.api.getBedtime.mockResolvedValue(aStatus());
    api.api.extendBedtime.mockRejectedValue({
      response: { status: 409, data: { error: 'No extensions left tonight' } },
    });

    renderWithRouter(<Bedtime />);
    await waitFor(() => expect(screen.getByText(/\+15 MINUTES/)).toBeInTheDocument());

    await user.click(screen.getByText(/\+15 MINUTES/));

    await waitFor(() => {
      expect(screen.getByText(/no extensions left tonight/i)).toBeInTheDocument();
    });
  });

  it('treats a server error as an error, not a refusal', async () => {
    // A 500 also carries an `error` field. Showing it as a friendly notice
    // would dress a server failure up as a normal refusal.
    const user = userEvent.setup();
    api.api.getBedtime.mockResolvedValue(aStatus());
    api.api.startBedtimeNow.mockRejectedValue({
      response: { status: 500, data: { error: 'Internal server error' } },
    });

    renderWithRouter(<Bedtime />);
    await waitFor(() => expect(screen.getByText(/bedtime now/i)).toBeInTheDocument());

    await user.click(screen.getByText(/bedtime now/i));

    await waitFor(() => {
      expect(screen.getByText(/internal server error/i)).toBeInTheDocument();
    });
    // The error banner is red; a refusal notice is not.
    expect(screen.getByText(/internal server error/i).className).toMatch(/text-red/);
  });

  it('treats a 503 as an error too', async () => {
    const user = userEvent.setup();
    api.api.getBedtime.mockResolvedValue(aStatus());
    api.api.skipBedtime.mockRejectedValue({
      response: { status: 503, data: { error: 'Bedtime mode is unavailable' } },
    });

    renderWithRouter(<Bedtime />);
    await waitFor(() => expect(screen.getByText(/skip tonight/i)).toBeInTheDocument());

    await user.click(screen.getByText(/skip tonight/i));

    await waitFor(() => {
      expect(screen.getByText(/bedtime mode is unavailable/i).className).toMatch(/text-red/);
    });
  });

  it('loads once on mount, not twice', async () => {
    // usePolling already fetches on mount; a separate effect would double it.
    api.api.getBedtime.mockResolvedValue(aStatus());
    renderWithRouter(<Bedtime />);

    await waitFor(() => expect(api.api.getBedtime).toHaveBeenCalled());
    expect(api.api.getBedtime).toHaveBeenCalledTimes(1);
  });

  it('skips tonight', async () => {
    const user = userEvent.setup();
    api.api.getBedtime.mockResolvedValue(aStatus());
    api.api.skipBedtime.mockResolvedValue({
      success: true,
      message: 'Bedtime skipped for tonight',
      status: aStatus({ skipped_tonight: true }),
    });

    renderWithRouter(<Bedtime />);
    await waitFor(() => expect(screen.getByText(/skip tonight/i)).toBeInTheDocument());

    await user.click(screen.getByText(/skip tonight/i));

    await waitFor(() => expect(screen.getByText(/^SKIPPED$/)).toBeInTheDocument());
  });

  it('shows the configured schedule', async () => {
    api.api.getBedtime.mockResolvedValue(aStatus());
    renderWithRouter(<Bedtime />);

    await waitFor(() => {
      expect(screen.getByText('20:30')).toBeInTheDocument();
      expect(screen.getByText('21:30')).toBeInTheDocument();
      expect(screen.getByText('STOP')).toBeInTheDocument();
    });
  });

  it('reports a load failure', async () => {
    api.api.getBedtime.mockRejectedValue(new Error('network down'));
    renderWithRouter(<Bedtime />);

    await waitFor(() => {
      expect(screen.getByText(/could not load bedtime status/i)).toBeInTheDocument();
    });
  });
});
