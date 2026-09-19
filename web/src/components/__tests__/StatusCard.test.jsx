import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import StatusCard from '../StatusCard';

describe('StatusCard', () => {
  it('renders with title and value', () => {
    render(<StatusCard title="Test Title" value="Test Value" status="success" icon="🟢" />);

    expect(screen.getByText('Test Title')).toBeInTheDocument();
    expect(screen.getByText('Test Value')).toBeInTheDocument();
  });

  it('displays the correct icon', () => {
    render(<StatusCard title="Test" value="Value" status="info" icon="📊" />);

    expect(screen.getByText('📊')).toBeInTheDocument();
  });

  it('applies correct status color class', () => {
    const { container } = render(
      <StatusCard title="Test" value="Value" status="success" icon="🟢" />
    );

    const statusDot = container.querySelector('.bg-minecraft-grass-DEFAULT');
    expect(statusDot).not.toBeNull();
    expect(statusDot).toBeInstanceOf(HTMLElement);
  });

  it('handles different status types', () => {
    const statuses = ['success', 'error', 'warning', 'info'];
    statuses.forEach(status => {
      const { container } = render(
        <StatusCard title="Test" value="Value" status={status} icon="🟢" />
      );

      // Find the status dot by looking for elements with border-2 class (status indicator)
      const statusDots = container.querySelectorAll('.border-2');
      expect(statusDots.length).toBeGreaterThan(0);

      // Verify at least one status dot exists
      const statusDot = Array.from(statusDots).find(
        dot => dot.classList.contains('w-4') && dot.classList.contains('h-4')
      );
      expect(statusDot).not.toBeNull();
      expect(statusDot).toBeInstanceOf(HTMLElement);
    });
  });
});
