import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithRouter } from '../../test/utils'
import Logs from '../Logs'
import * as api from '../../services/api'

vi.mock('../../services/api', () => ({
  api: {
    getLogs: vi.fn(),
  },
}))

describe('Logs', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders logs page title', () => {
    api.api.getLogs.mockResolvedValue({ logs: [] })

    renderWithRouter(<Logs />)
    expect(screen.getByText('Server Logs')).toBeInTheDocument()
  })

  it('displays loading state initially', () => {
    api.api.getLogs.mockImplementation(() => new Promise(() => {}))

    renderWithRouter(<Logs />)
    expect(screen.getByText('Loading logs...')).toBeInTheDocument()
  })

  it('displays logs when loaded', async () => {
    const mockLogs = [
      '[10:30:00] [Server thread/INFO] Starting server',
      '[10:30:01] [Server thread/INFO] Server started',
    ]

    api.api.getLogs.mockResolvedValue({ logs: mockLogs })

    renderWithRouter(<Logs />)

    await waitFor(() => {
      expect(screen.getByText(mockLogs[0])).toBeInTheDocument()
      expect(screen.getByText(mockLogs[1])).toBeInTheDocument()
    })
  })

  it('filters logs when filter input is used', async () => {
    const user = userEvent.setup()
    const mockLogs = [
      '[10:30:00] [Server thread/INFO] Starting server',
      '[10:30:01] [Server thread/ERROR] Error occurred',
    ]

    api.api.getLogs.mockResolvedValue({ logs: mockLogs })

    renderWithRouter(<Logs />)

    await waitFor(() => {
      expect(screen.getByText(mockLogs[0])).toBeInTheDocument()
    }, { timeout: 3000 })

    const filterInput = screen.getByPlaceholderText('Filter logs...')
    await user.type(filterInput, 'ERROR')

    await waitFor(() => {
      expect(screen.queryByText(mockLogs[0])).not.toBeInTheDocument()
      expect(screen.getByText(mockLogs[1])).toBeInTheDocument()
    }, { timeout: 3000 })
  })

  it('toggles auto-scroll checkbox', async () => {
    const user = userEvent.setup()
    api.api.getLogs.mockResolvedValue({ logs: [] })

    renderWithRouter(<Logs />)

    await waitFor(() => {
      const checkbox = screen.getByLabelText('Auto-scroll')
      expect(checkbox).toBeChecked()
    }, { timeout: 3000 })

    const checkbox = screen.getByLabelText('Auto-scroll')
    await user.click(checkbox)

    await waitFor(() => {
      expect(checkbox).not.toBeChecked()
    })
  })

  it('calls getLogs when refresh button is clicked', async () => {
    const user = userEvent.setup()
    api.api.getLogs.mockResolvedValue({ logs: [] })

    renderWithRouter(<Logs />)

    await waitFor(() => {
      expect(api.api.getLogs).toHaveBeenCalled()
    }, { timeout: 3000 })

    // Clear the mock call count
    vi.clearAllMocks()
    api.api.getLogs.mockResolvedValue({ logs: [] })

    const refreshButton = screen.getByText('Refresh')
    await user.click(refreshButton)

    await waitFor(() => {
      expect(api.api.getLogs).toHaveBeenCalled()
    }, { timeout: 3000 })
  })

  it('displays no logs message when empty', async () => {
    api.api.getLogs.mockResolvedValue({ logs: [] })

    renderWithRouter(<Logs />)

    await waitFor(() => {
      expect(screen.getByText('No logs found')).toBeInTheDocument()
    }, { timeout: 3000 })
  })
})

