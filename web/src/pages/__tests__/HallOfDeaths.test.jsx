import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from '../../services/api';
import { renderWithRouter } from '../../test/utils';
import HallOfDeaths from '../HallOfDeaths';

vi.mock('../../services/api', () => ({
  api: {
    getDeaths: vi.fn(),
    getDeathsLeaderboard: vi.fn(),
  },
}));

const aDeath = (overrides = {}) => ({
  player: 'Jonah',
  cause: 'was slain by Zombie',
  category: 'combat',
  culprit: 'Zombie',
  epitaph: 'Here lies Jonah, who met Zombie and did not come to an arrangement.',
  timestamp: '2026-09-19T10:00:00+00:00',
  ...overrides,
});

const withDeaths = (deaths, stats = null, leaderboard = []) => {
  api.api.getDeaths.mockResolvedValue({
    deaths,
    stats: stats || {
      total_deaths: deaths.length,
      players: 1,
      categories: {},
      most_common_cause: 'combat',
    },
  });
  api.api.getDeathsLeaderboard.mockResolvedValue({ leaderboard });
};

describe('HallOfDeaths', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the page title', async () => {
    withDeaths([]);
    renderWithRouter(<HallOfDeaths />);

    await waitFor(() => {
      expect(screen.getByText(/hall of deaths/i)).toBeInTheDocument();
    });
  });

  it('shows a loading state first', () => {
    api.api.getDeaths.mockImplementation(() => new Promise(() => {}));
    api.api.getDeathsLeaderboard.mockImplementation(() => new Promise(() => {}));

    renderWithRouter(<HallOfDeaths />);

    expect(screen.getByText(/consulting the records/i)).toBeInTheDocument();
  });

  it('displays each epitaph', async () => {
    withDeaths([aDeath()]);
    renderWithRouter(<HallOfDeaths />);

    await waitFor(() => {
      expect(screen.getByText(/did not come to an arrangement/i)).toBeInTheDocument();
    });
  });

  it('shows the cause and the culprit on the entry', async () => {
    // 'Slain' also appears in the summary tile, so match the metadata line
    // that carries the cause, the culprit and the time together.
    withDeaths([aDeath()]);
    renderWithRouter(<HallOfDeaths />);

    await waitFor(() => {
      expect(screen.getByText(/Slain\s*·\s*Zombie/)).toBeInTheDocument();
    });
  });

  it('omits the culprit when the death had none', async () => {
    withDeaths([aDeath({ category: 'fall', culprit: null, epitaph: 'Jonah fell.' })]);
    renderWithRouter(<HallOfDeaths />);

    await waitFor(() => {
      expect(screen.getByText(/Jonah fell\./)).toBeInTheDocument();
    });
    expect(screen.queryByText(/·\s*Zombie/)).not.toBeInTheDocument();
  });

  it('renders summary stats', async () => {
    withDeaths([aDeath()], {
      total_deaths: 12,
      players: 2,
      categories: {},
      most_common_cause: 'fall',
    });
    renderWithRouter(<HallOfDeaths />);

    await waitFor(() => {
      expect(screen.getByText('12')).toBeInTheDocument();
      expect(screen.getByText(/fell/i)).toBeInTheDocument();
    });
  });

  it('shows a friendly empty state when nobody has died', async () => {
    withDeaths([]);
    renderWithRouter(<HallOfDeaths />);

    await waitFor(() => {
      expect(screen.getByText(/nobody has died yet/i)).toBeInTheDocument();
    });
  });

  it('renders the leaderboard', async () => {
    withDeaths(
      [aDeath()],
      null,
      [
        { player: 'Jonah', deaths: 7, favourite_cause: 'fall', last_epitaph: 'x' },
        { player: 'Silas', deaths: 3, favourite_cause: 'drowning', last_epitaph: 'y' },
      ]
    );
    renderWithRouter(<HallOfDeaths />);

    await waitFor(() => {
      expect(screen.getByText(/1\. Jonah/)).toBeInTheDocument();
      expect(screen.getByText(/2\. Silas/)).toBeInTheDocument();
      expect(screen.getByText('7')).toBeInTheDocument();
    });
  });

  it('filters by player', async () => {
    const user = userEvent.setup();
    withDeaths([aDeath()]);
    renderWithRouter(<HallOfDeaths />);

    await waitFor(() => expect(api.api.getDeaths).toHaveBeenCalled());

    await user.type(screen.getByPlaceholderText(/filter by player/i), 'Silas');

    await waitFor(() => {
      expect(api.api.getDeaths).toHaveBeenLastCalledWith(
        expect.objectContaining({ player: 'Silas' })
      );
    });
  });

  it('reports a load failure instead of staying blank', async () => {
    api.api.getDeaths.mockRejectedValue(new Error('network down'));
    api.api.getDeathsLeaderboard.mockRejectedValue(new Error('network down'));

    renderWithRouter(<HallOfDeaths />);

    await waitFor(() => {
      expect(screen.getByText(/could not load the hall of deaths/i)).toBeInTheDocument();
    });
  });

  it('says MOSTLY only when a cause actually repeated', async () => {
    withDeaths([aDeath()], null, [
      { player: 'Silas', deaths: 4, favourite_cause: 'drowning', favourite_cause_count: 3 },
    ]);
    renderWithRouter(<HallOfDeaths />);

    await waitFor(() => {
      expect(screen.getByText(/MOSTLY.*Drowned/i)).toBeInTheDocument();
    });
  });

  it('says LATELY when every death was different', async () => {
    // Three deaths three ways has no mode, so 'mostly' would be a small lie.
    withDeaths([aDeath()], null, [
      {
        player: 'Jonah',
        deaths: 3,
        favourite_cause: 'drowning',
        favourite_cause_count: 1,
        last_category: 'explosion',
      },
    ]);
    renderWithRouter(<HallOfDeaths />);

    await waitFor(() => {
      expect(screen.getByText(/LATELY.*Exploded/i)).toBeInTheDocument();
    });
    expect(screen.queryByText(/MOSTLY/i)).not.toBeInTheDocument();
  });

  it('falls back to a default icon for an unknown category', async () => {
    withDeaths([aDeath({ category: 'something-new', culprit: null })]);
    renderWithRouter(<HallOfDeaths />);

    await waitFor(() => {
      expect(screen.getByText(/mysterious/i)).toBeInTheDocument();
    });
  });
});
