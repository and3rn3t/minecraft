import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../../services/api';
import { renderWithRouter } from '../../test/utils';
import Login from '../Login';

// Mock API service but not AuthContext - we'll use real AuthProvider
vi.mock('../../services/api');
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => vi.fn(),
  };
});

describe('Login', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock API call that AuthProvider makes on mount
    api.getCurrentUser.mockRejectedValue(new Error('Not authenticated'));
    // Mock login API call
    api.login = vi.fn();
  });

  const renderComponent = () => {
    return renderWithRouter(<Login />);
  };

  it('renders login form', async () => {
    renderComponent();
    // Wait for form elements to be available (after AuthProvider finishes loading)
    await waitFor(() => {
      expect(screen.getByLabelText(/Username/i)).toBeInTheDocument();
    });
    expect(screen.getByLabelText(/Password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
  });

  it('submits login form with credentials', async () => {
    const user = userEvent.setup();
    api.login.mockResolvedValue({
      success: true,
      user: { username: 'testuser', role: 'user' },
      token: 'token123',
    });

    renderComponent();

    const usernameInput = screen.getByLabelText(/Username/i);
    const passwordInput = screen.getByLabelText(/Password/i);
    const submitButton = screen.getByRole('button', { name: /login/i });

    await user.type(usernameInput, 'testuser');
    await user.type(passwordInput, 'password123');
    await user.click(submitButton);

    await waitFor(() => {
      expect(api.login).toHaveBeenCalledWith('testuser', 'password123', null);
    });
  });

  it('displays error message when login fails', async () => {
    const user = userEvent.setup();
    api.login.mockRejectedValue({ response: { data: { error: 'Invalid credentials' } } });

    renderComponent();

    const usernameInput = screen.getByLabelText(/Username/i);
    const passwordInput = screen.getByLabelText(/Password/i);
    const submitButton = screen.getByRole('button', { name: /login/i });

    await user.type(usernameInput, 'testuser');
    await user.type(passwordInput, 'wrongpassword');
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Invalid credentials/i)).toBeInTheDocument();
    });
  });

  it('disables submit button while loading', async () => {
    const user = userEvent.setup();
    api.login.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)));

    renderComponent();

    const usernameInput = screen.getByLabelText(/Username/i);
    const passwordInput = screen.getByLabelText(/Password/i);
    const submitButton = screen.getByRole('button', { name: /login/i });

    await user.type(usernameInput, 'testuser');
    await user.type(passwordInput, 'password123');
    await user.click(submitButton);

    expect(screen.getByText(/logging in/i)).toBeInTheDocument();
    expect(submitButton).toBeDisabled();
  });

  it('has link to register page', () => {
    renderComponent();
    const registerLink = screen.getByText(/Register here/i);
    expect(registerLink).toBeInTheDocument();
    expect(registerLink.closest('a')).toHaveAttribute('href', '/register');
  });
});
