import { act, fireEvent, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../../services/api';
import { renderWithRouter } from '../../test/utils';
import { AuthProvider, useAuth } from '../AuthContext';

// Mock API service
vi.mock('../../services/api');

const TestComponent = () => {
  const { user, loading, isAuthenticated, login, register, logout } = useAuth();

  return (
    <div>
      {loading && <div>Loading...</div>}
      {user && <div>User: {user.username}</div>}
      {isAuthenticated && <div>Authenticated</div>}
      <button onClick={() => login('testuser', 'password')}>Login</button>
      <button onClick={() => register('newuser', 'password', 'email@test.com')}>Register</button>
      <button onClick={() => logout()}>Logout</button>
    </div>
  );
};

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('provides authentication context', () => {
    api.getCurrentUser.mockRejectedValue(new Error('Not authenticated'));

    renderWithRouter(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    expect(screen.getByText(/Loading/i)).toBeInTheDocument();
  });

  it('loads user on mount if authenticated', async () => {
    api.getCurrentUser.mockResolvedValue({
      username: 'testuser',
      role: 'admin',
      email: 'test@example.com',
    });

    renderWithRouter(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/testuser/i)).toBeInTheDocument();
      expect(screen.getByText(/Authenticated/i)).toBeInTheDocument();
    });
  });

  it('clears user state when not authenticated', async () => {
    api.getCurrentUser.mockRejectedValue(new Error('Not authenticated'));

    renderWithRouter(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.queryByText(/testuser/i)).not.toBeInTheDocument();
    });
  });

  it('handles login successfully', async () => {
    api.getCurrentUser.mockRejectedValue(new Error('Not authenticated'));
    api.login.mockResolvedValue({
      success: true,
      user: { username: 'testuser', role: 'user' },
      token: 'token123',
    });

    renderWithRouter(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(() => {
      const loginButton = screen.getByText(/Login/i);
      expect(loginButton).toBeInTheDocument();
    });

    const loginButton = screen.getByText(/Login/i);
    await act(async () => {
      fireEvent.click(loginButton);
    });

    await waitFor(() => {
      expect(api.login).toHaveBeenCalledWith('testuser', 'password', null);
      expect(localStorage.getItem('auth_token')).toBe('token123');
    });
  });

  it('handles registration successfully', async () => {
    api.getCurrentUser.mockRejectedValue(new Error('Not authenticated'));
    api.register.mockResolvedValue({
      success: true,
      user: { username: 'newuser', role: 'user' },
      token: 'token123',
    });

    renderWithRouter(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(() => {
      const registerButton = screen.getByText(/Register/i);
      expect(registerButton).toBeInTheDocument();
    });

    const registerButton = screen.getByText(/Register/i);
    await act(async () => {
      fireEvent.click(registerButton);
    });

    await waitFor(() => {
      expect(api.register).toHaveBeenCalledWith('newuser', 'password', 'email@test.com');
      expect(localStorage.getItem('auth_token')).toBe('token123');
    });
  });

  it('handles logout', async () => {
    localStorage.setItem('auth_token', 'token123');
    api.getCurrentUser.mockResolvedValue({
      username: 'testuser',
      role: 'admin',
    });
    api.logout.mockResolvedValue({ success: true });

    renderWithRouter(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(() => {
      const logoutButton = screen.getByText(/Logout/i);
      expect(logoutButton).toBeInTheDocument();
    });

    const logoutButton = screen.getByText(/Logout/i);
    await act(async () => {
      fireEvent.click(logoutButton);
    });

    await waitFor(() => {
      expect(api.logout).toHaveBeenCalled();
      expect(localStorage.getItem('auth_token')).toBeNull();
    });
  });
});
