import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAuth } from '../../contexts/AuthContext';
import ProtectedRoute from '../ProtectedRoute';

vi.mock('../../contexts/AuthContext', () => ({ useAuth: vi.fn() }));

const renderAt = () =>
  render(
    <MemoryRouter initialEntries={['/dashboard']}>
      <Routes>
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <p>secret dashboard</p>
            </ProtectedRoute>
          }
        />
        <Route path="/login" element={<p>login page</p>} />
      </Routes>
    </MemoryRouter>
  );

describe('ProtectedRoute', () => {
  beforeEach(() => localStorage.clear());

  it('shows a loading state while the session is being checked', () => {
    useAuth.mockReturnValue({ isAuthenticated: false, loading: true });
    renderAt();

    expect(screen.getByText('Loading...')).toBeInTheDocument();
    expect(screen.queryByText('secret dashboard')).not.toBeInTheDocument();
  });

  it('sends a signed-out visitor to the login page', () => {
    useAuth.mockReturnValue({ isAuthenticated: false, loading: false });
    renderAt();

    expect(screen.getByText('login page')).toBeInTheDocument();
    expect(screen.queryByText('secret dashboard')).not.toBeInTheDocument();
  });

  it('shows the page to a signed-in user', () => {
    useAuth.mockReturnValue({ isAuthenticated: true, loading: false });
    renderAt();

    expect(screen.getByText('secret dashboard')).toBeInTheDocument();
  });

  it('lets a browser holding an API key through', () => {
    useAuth.mockReturnValue({ isAuthenticated: false, loading: false });
    localStorage.setItem('api_key', 'k');
    renderAt();

    expect(screen.getByText('secret dashboard')).toBeInTheDocument();
  });
});
