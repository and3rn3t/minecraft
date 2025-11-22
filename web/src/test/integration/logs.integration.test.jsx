import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithRouter } from '../utils'
import Logs from '../../pages/Logs'
import * as api from '../../services/api'

// Mock the API service
vi.mock('../../services/api', () => ({
  api: {
    getLogs: vi.fn(),
  },
}))

describe('Logs Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('loads and displays logs', async () => {
    // Set up mock response
    api.api.getLogs.mockResolvedValue({
      logs: [
        '[10:30:00] [Server thread/INFO] Starting minecraft server',
        '[10:30:01] [Server thread/ERROR] Test error message',
        '[10:30:02] [Server thread/WARN] Warning message',
      ],
      lines: 3,
    })

    renderWithRouter(<Logs />)

    await waitFor(() => {
      expect(screen.getByText(/Starting minecraft server/)).toBeInTheDocument()
      expect(screen.getByText(/Test error message/)).toBeInTheDocument()
      expect(screen.getByText(/Warning message/)).toBeInTheDocument()
    }, { timeout: 5000 })
  })

  it('filters logs correctly', async () => {
    const user = userEvent.setup()

    // Set up mock response
    api.api.getLogs.mockResolvedValue({
      logs: [
        '[10:30:00] [Server thread/INFO] Starting minecraft server',
        '[10:30:01] [Server thread/ERROR] Test error message',
        '[10:30:02] [Server thread/WARN] Warning message',
      ],
      lines: 3,
    })

    renderWithRouter(<Logs />)

    await waitFor(() => {
      expect(screen.getByText(/Starting minecraft server/)).toBeInTheDocument()
    }, { timeout: 5000 })

    const filterInput = screen.getByPlaceholderText('Filter logs...')
    await user.type(filterInput, 'ERROR')

    await waitFor(() => {
      expect(screen.queryByText(/Starting minecraft server/)).not.toBeInTheDocument()
      expect(screen.getByText(/Test error message/)).toBeInTheDocument()
    }, { timeout: 3000 })
  })

  it('refreshes logs on button click', async () => {
    const user = userEvent.setup()

    // Set up mock response
    api.api.getLogs.mockResolvedValue({
      logs: [
        '[10:30:00] [Server thread/INFO] Starting minecraft server',
        '[10:30:01] [Server thread/ERROR] Test error message',
        '[10:30:02] [Server thread/WARN] Warning message',
      ],
      lines: 3,
    })

    renderWithRouter(<Logs />)

    await waitFor(() => {
      expect(screen.getByText(/Starting minecraft server/)).toBeInTheDocument()
    }, { timeout: 5000 })

    const refreshButton = screen.getByText('Refresh')
    await user.click(refreshButton)

    // Should reload logs - verify API was called again
    expect(api.api.getLogs).toHaveBeenCalledTimes(2)

    // Logs should still be visible
    await waitFor(() => {
      expect(screen.getByText(/Starting minecraft server/)).toBeInTheDocument()
    }, { timeout: 3000 })
  })
})

