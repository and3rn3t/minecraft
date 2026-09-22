import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from '../../services/api';
import { renderWithRouter } from '../../test/utils';
import Scheduler from '../Scheduler';

vi.mock('../../services/api', () => ({
  api: {
    listSchedules: vi.fn(),
    createSchedule: vi.fn(),
    updateSchedule: vi.fn(),
    deleteSchedule: vi.fn(),
  },
}));

const mockConfirm = vi.fn();
globalThis.confirm = mockConfirm;

describe('Scheduler', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockConfirm.mockReturnValue(true);
  });

  const mockSchedule = {
    id: '1',
    command: 'say Server restart in 5 minutes',
    type: 'interval',
    enabled: true,
    interval_minutes: 60,
  };

  it('renders the scheduler title', async () => {
    api.api.listSchedules.mockResolvedValue({ success: true, schedules: [] });
    renderWithRouter(<Scheduler />);
    await waitFor(() => {
      expect(screen.getByText(/command scheduler/i)).toBeInTheDocument();
    });
  });

  it('shows the empty state when there are no schedules', async () => {
    api.api.listSchedules.mockResolvedValue({ success: true, schedules: [] });
    renderWithRouter(<Scheduler />);
    await waitFor(() => {
      expect(screen.getByText(/no schedules/i)).toBeInTheDocument();
    });
  });

  it('lists existing schedules with their description', async () => {
    api.api.listSchedules.mockResolvedValue({ success: true, schedules: [mockSchedule] });
    renderWithRouter(<Scheduler />);
    await waitFor(() => {
      expect(screen.getByText(mockSchedule.command)).toBeInTheDocument();
      expect(screen.getByText(/every 60 minutes/i)).toBeInTheDocument();
      expect(screen.getByText('Enabled')).toBeInTheDocument();
    });
  });

  it('opens the create form with real labels for every field', async () => {
    api.api.listSchedules.mockResolvedValue({ success: true, schedules: [] });
    const user = userEvent.setup();
    renderWithRouter(<Scheduler />);

    await waitFor(() => expect(screen.getByText(/no schedules/i)).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /create schedule/i }));

    expect(screen.getByLabelText(/^command/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/schedule type/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/interval \(minutes\)/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^enabled$/i)).toBeInTheDocument();
  });

  it('creates a schedule and shows it in the list', async () => {
    api.api.listSchedules.mockResolvedValue({ success: true, schedules: [] });
    api.api.createSchedule.mockResolvedValue({ success: true });
    const user = userEvent.setup();
    renderWithRouter(<Scheduler />);

    await waitFor(() => expect(screen.getByText(/no schedules/i)).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /create schedule/i }));
    await user.type(screen.getByLabelText(/^command/i), 'save-all');
    await user.click(screen.getByRole('button', { name: /^create$/i }));

    await waitFor(() => {
      expect(api.api.createSchedule).toHaveBeenCalledWith(
        expect.objectContaining({ command: 'save-all' })
      );
    });
  });

  it('switches to the weekly fields when schedule type changes', async () => {
    api.api.listSchedules.mockResolvedValue({ success: true, schedules: [] });
    const user = userEvent.setup();
    renderWithRouter(<Scheduler />);

    await waitFor(() => expect(screen.getByText(/no schedules/i)).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /create schedule/i }));
    await user.selectOptions(screen.getByLabelText(/schedule type/i), 'weekly');

    expect(screen.getByLabelText(/run time/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/day of week/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/interval \(minutes\)/i)).not.toBeInTheDocument();
  });

  it('deletes a schedule after confirmation', async () => {
    api.api.listSchedules.mockResolvedValue({ success: true, schedules: [mockSchedule] });
    api.api.deleteSchedule.mockResolvedValue({ success: true });
    const user = userEvent.setup();
    renderWithRouter(<Scheduler />);

    await waitFor(() => expect(screen.getByText(mockSchedule.command)).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /delete/i }));

    await waitFor(() => {
      expect(mockConfirm).toHaveBeenCalled();
      expect(api.api.deleteSchedule).toHaveBeenCalledWith('1');
    });
  });

  it('surfaces a fetch failure', async () => {
    api.api.listSchedules.mockRejectedValue({
      response: { data: { error: 'Scheduler unavailable' } },
    });
    renderWithRouter(<Scheduler />);
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Scheduler unavailable');
    });
  });
});
