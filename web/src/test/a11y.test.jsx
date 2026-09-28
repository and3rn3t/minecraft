import { act, render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ToastProvider } from '../components/ToastContainer';
import { AuthProvider } from '../contexts/AuthContext';
import Analytics from '../pages/Analytics';
import Backups from '../pages/Backups';
import Dashboard from '../pages/Dashboard';
import Login from '../pages/Login';
import Players from '../pages/Players';
import Worlds from '../pages/Worlds';
import { axe } from './vitest-axe';

// Mock API for components that need it
vi.mock('../services/api', () => ({
  api: {
    getStatus: vi.fn().mockResolvedValue({ running: true, status: 'Up' }),
    getMetrics: vi.fn().mockResolvedValue({ metrics: {} }),
    getPlayers: vi.fn().mockResolvedValue({ players: [] }),
    getAnalyticsReport: vi.fn().mockResolvedValue({
      report: {
        generated_at: '2024-01-27T12:00:00',
        period_hours: 24,
        summary: { status: 'healthy', warnings: [], recommendations: [] },
      },
    }),
    getAnalyticsTrends: vi.fn().mockResolvedValue({ trends: {}, period_hours: 24 }),
    getAnalyticsAnomalies: vi.fn().mockResolvedValue({ anomalies: [] }),
    getAnalyticsPredictions: vi.fn().mockResolvedValue({ prediction: {} }),
    getPlayerBehavior: vi.fn().mockResolvedValue({ behavior: {} }),
    listBackups: vi.fn().mockResolvedValue({ backups: [] }),
    listWorlds: vi.fn().mockResolvedValue({ worlds: [] }),
    getCurrentUser: vi.fn().mockRejectedValue(new Error('Not authenticated')),
  },
}));

// Renders, then lets the mocked API calls resolve before returning. Auditing
// straight after render() checked each page's loading skeleton, never the page
// itself, and left its state updates to land after the test (act() warnings).
const renderWithA11y = async component => {
  const result = render(
    <BrowserRouter>
      <ToastProvider>
        <AuthProvider>{component}</AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  );
  await act(() => new Promise(resolve => setTimeout(resolve, 0)));
  return result;
};

describe('Accessibility Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Analytics Page', () => {
    it('should have no accessibility violations', async () => {
      const { container } = await renderWithA11y(<Analytics />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe('Dashboard Page', () => {
    it('should have no accessibility violations', async () => {
      const { container } = await renderWithA11y(<Dashboard />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe('Backups Page', () => {
    it('should have no accessibility violations', async () => {
      const { container } = await renderWithA11y(<Backups />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe('Players Page', () => {
    it('should have no accessibility violations', async () => {
      const { container } = await renderWithA11y(<Players />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe('Worlds Page', () => {
    it('should have no accessibility violations', async () => {
      const { container } = await renderWithA11y(<Worlds />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe('Login Page', () => {
    it('should have no accessibility violations', async () => {
      const { container } = await renderWithA11y(<Login />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have proper form labels', async () => {
      await renderWithA11y(<Login />);

      // Check for form labels
      const usernameLabel = screen.getByLabelText(/username/i);
      const passwordLabel = screen.getByLabelText(/password/i);

      expect(usernameLabel).toBeInTheDocument();
      expect(passwordLabel).toBeInTheDocument();
    });
  });
});
