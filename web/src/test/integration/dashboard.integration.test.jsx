import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithRouter } from '../utils'
import Dashboard from '../../pages/Dashboard'
import * as api from '../../services/api'

// Mock the API service
vi.mock('../../services/api', () => ({
  api: {
    getStatus: vi.fn(),
    getMetrics: vi.fn(),
    getPlayers: vi.fn(),
    startServer: vi.fn(),
    stopServer: vi.fn(),
    restartServer: vi.fn(),
  },
}))

describe('Dashboard Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('loads and displays all dashboard data', async () => {
    // Set up mock responses
    api.api.getStatus.mockResolvedValue({
      running: true,
      status: 'Up 2 hours',
      timestamp: new Date().toISOString(),
    })
    api.api.getMetrics.mockResolvedValue({
      metrics: {
        cpu_percent: '45.2',
        memory_usage: '1.2GiB / 2.0GiB',
        memory_percent: '60.0',
      },
      timestamp: new Date().toISOString(),
    })
    api.api.getPlayers.mockResolvedValue({
      players: ['Player1', 'Player2'],
      count: 2,
    })

    renderWithRouter(<Dashboard />)

    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByText('Online')).toBeInTheDocument()
    })

    // Check all elements are present
    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument()
      expect(screen.getByText('Online')).toBeInTheDocument()
      expect(screen.getByText('2 / 10')).toBeInTheDocument()
      expect(screen.getByText('Player1')).toBeInTheDocument()
      expect(screen.getByText('Player2')).toBeInTheDocument()
    }, { timeout: 3000 })
  })

  it('handles server start action', async () => {
    const user = userEvent.setup()

    // Set up mock responses for offline server
    api.api.getStatus.mockResolvedValue({
      running: false,
      status: 'Stopped',
    })
    api.api.getMetrics.mockResolvedValue({
      metrics: {},
      timestamp: new Date().toISOString(),
    })
    api.api.getPlayers.mockResolvedValue({
      players: [],
      count: 0,
    })
    api.api.startServer.mockResolvedValue({
      success: true,
      message: 'Server starting',
    })

    renderWithRouter(<Dashboard />)

    // Wait for component to load and show offline status
    await waitFor(() => {
      expect(screen.getByText('Offline')).toBeInTheDocument()
    }, { timeout: 3000 })

    const startButton = screen.getByText('Start Server')
    expect(startButton).not.toBeDisabled()

    await user.click(startButton)

    // Verify the API was called
    expect(api.api.startServer).toHaveBeenCalledTimes(1)

    // After clicking, button should still be present
    await waitFor(() => {
      expect(screen.getByText('Start Server')).toBeInTheDocument()
    }, { timeout: 3000 })
  })

  it('updates metrics display', async () => {
    // Set up mock responses
    api.api.getStatus.mockResolvedValue({
      running: true,
      status: 'Up 2 hours',
    })
    api.api.getMetrics.mockResolvedValue({
      metrics: {
        cpu_percent: '45.2',
        memory_usage: '1.2GiB / 2.0GiB',
        memory_percent: '60.0',
      },
      timestamp: new Date().toISOString(),
    })
    api.api.getPlayers.mockResolvedValue({
      players: [],
      count: 0,
    })

    renderWithRouter(<Dashboard />)

    await waitFor(() => {
      expect(screen.getByText(/45\.2/)).toBeInTheDocument()
      expect(screen.getByText(/1\.2GiB/)).toBeInTheDocument()
    }, { timeout: 3000 })
  })
})

