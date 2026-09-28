import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import MetricsChart from '../MetricsChart';

describe('MetricsChart', () => {
  it('shows CPU as a percentage, as the API sends it without the % sign', () => {
    render(<MetricsChart metrics={{ metrics: { cpu_percent: '12.50', memory_usage: '1.2GiB / 4GiB', memory_percent: '30.00' } }} />);

    expect(screen.getByText('12.5%')).toBeInTheDocument();
    expect(screen.getByText('1.2GiB / 4GiB')).toBeInTheDocument();
    expect(screen.getByText('30%')).toBeInTheDocument();
  });

  it('says N/A when docker stats are unavailable', () => {
    render(<MetricsChart metrics={{ metrics: {} }} />);

    expect(screen.getAllByText('N/A')).toHaveLength(2);
  });
});
