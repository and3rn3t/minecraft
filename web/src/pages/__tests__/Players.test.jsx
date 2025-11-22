import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { renderWithRouter } from '../../test/utils'
import Players from '../Players'
import * as api from '../../services/api'

vi.mock('../../services/api', () => ({
  api: {
    getPlayers: vi.fn(),
  },
}))

describe('Players', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders players page title', () => {
    api.api.getPlayers.mockResolvedValue({ players: [] })

    renderWithRouter(<Players />)
    expect(screen.getByText('Player Management')).toBeInTheDocument()
  })

  it('displays loading state initially', () => {
    api.api.getPlayers.mockImplementation(() => new Promise(() => {}))

    renderWithRouter(<Players />)
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('displays online players', async () => {
    const mockPlayers = ['Player1', 'Player2', 'Player3']

    api.api.getPlayers.mockResolvedValue({ players: mockPlayers })

    renderWithRouter(<Players />)

    await waitFor(() => {
      expect(screen.getByText(`Online Players (${mockPlayers.length})`)).toBeInTheDocument()
      mockPlayers.forEach((player) => {
        expect(screen.getByText(player)).toBeInTheDocument()
      })
    })
  })

  it('displays no players message when empty', async () => {
    api.api.getPlayers.mockResolvedValue({ players: [] })

    renderWithRouter(<Players />)

    await waitFor(() => {
      expect(screen.getByText('No players online')).toBeInTheDocument()
    })
  })

  it('displays player count in header', async () => {
    const mockPlayers = ['Player1', 'Player2']

    api.api.getPlayers.mockResolvedValue({ players: mockPlayers })

    renderWithRouter(<Players />)

    await waitFor(() => {
      expect(screen.getByText('Online Players (2)')).toBeInTheDocument()
    })
  })
})

