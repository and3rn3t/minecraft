import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import StatusCard from '../StatusCard'

describe('StatusCard', () => {
  it('renders with title and value', () => {
    render(
      <StatusCard
        title="Test Title"
        value="Test Value"
        status="success"
        icon="🟢"
      />
    )

    expect(screen.getByText('Test Title')).toBeInTheDocument()
    expect(screen.getByText('Test Value')).toBeInTheDocument()
  })

  it('displays the correct icon', () => {
    render(
      <StatusCard
        title="Test"
        value="Value"
        status="info"
        icon="📊"
      />
    )

    expect(screen.getByText('📊')).toBeInTheDocument()
  })

  it('applies correct status color class', () => {
    const { container } = render(
      <StatusCard
        title="Test"
        value="Value"
        status="success"
        icon="🟢"
      />
    )

    const statusDot = container.querySelector('.bg-green-600')
    expect(statusDot).toBeInTheDocument()
  })

  it('handles different status types', () => {
    const statuses = ['success', 'error', 'warning', 'info']

    statuses.forEach((status) => {
      const { container } = render(
        <StatusCard
          title="Test"
          value="Value"
          status={status}
          icon="🟢"
        />
      )

      const statusDot = container.querySelector(`.bg-${status === 'success' ? 'green' : status === 'error' ? 'red' : status === 'warning' ? 'yellow' : 'blue'}-600`)
      expect(statusDot).toBeInTheDocument()
    })
  })
})

