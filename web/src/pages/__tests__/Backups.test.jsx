import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithRouter } from '../../test/utils'
import Backups from '../Backups'
import * as api from '../../services/api'

vi.mock('../../services/api', () => ({
  api: {
    listBackups: vi.fn(),
    createBackup: vi.fn(),
  },
}))

describe('Backups', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders backups page title', () => {
    api.api.listBackups.mockResolvedValue({ backups: [] })

    renderWithRouter(<Backups />)
    expect(screen.getByText('Backups')).toBeInTheDocument()
  })

  it('displays loading state initially', () => {
    api.api.listBackups.mockImplementation(() => new Promise(() => {}))

    renderWithRouter(<Backups />)
    expect(screen.getByText('Loading backups...')).toBeInTheDocument()
  })

  it('displays backup list', async () => {
    const mockBackups = [
      {
        name: 'minecraft_backup_20250115.tar.gz',
        size: 104857600,
        created: '2025-01-15T10:30:00Z',
      },
    ]

    api.api.listBackups.mockResolvedValue({ backups: mockBackups })

    renderWithRouter(<Backups />)

    await waitFor(() => {
      expect(screen.getByText(mockBackups[0].name)).toBeInTheDocument()
    })
  })

  it('formats backup size correctly', async () => {
    const mockBackups = [
      {
        name: 'backup.tar.gz',
        size: 104857600, // 100 MB
        created: '2025-01-15T10:30:00Z',
      },
    ]

    api.api.listBackups.mockResolvedValue({ backups: mockBackups })

    renderWithRouter(<Backups />)

    await waitFor(() => {
      expect(screen.getByText(/100\.00 MB/)).toBeInTheDocument()
    })
  })

  it('creates backup when button is clicked', async () => {
    const user = userEvent.setup()
    api.api.listBackups.mockResolvedValue({ backups: [] })
    api.api.createBackup.mockResolvedValue({ success: true })

    // Mock window.alert
    window.alert = vi.fn()

    renderWithRouter(<Backups />)

    await waitFor(() => {
      const createButton = screen.getByText('Create Backup')
      expect(createButton).toBeInTheDocument()
    })

    const createButton = screen.getByText('Create Backup')
    await user.click(createButton)

    await waitFor(() => {
      expect(api.api.createBackup).toHaveBeenCalled()
    })
  })

  it('displays no backups message when empty', async () => {
    api.api.listBackups.mockResolvedValue({ backups: [] })

    renderWithRouter(<Backups />)

    await waitFor(() => {
      expect(screen.getByText('No backups found')).toBeInTheDocument()
    })
  })
})

