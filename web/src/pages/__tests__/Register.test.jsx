import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../../services/api';
import { renderWithRouter } from '../../test/utils';
import Register from '../Register';

// Mock API service but not AuthContext - we'll use real AuthProvider
vi.mock('../../services/api');
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => vi.fn(),
  };
});

describe('Register', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock API call that AuthProvider makes on mount
    api.getCurrentUser.mockRejectedValue(new Error('Not authenticated'));
    // Mock register API call
    api.register = vi.fn();
  });

  const renderComponent = () => {
    return renderWithRouter(<Register />);
  };

  it('renders registration form', async () => {
    renderComponent();
    // Wait for form elements to be available (after AuthProvider finishes loading)
    await waitFor(() => {
      expect(screen.getByLabelText(/Username/i)).toBeInTheDocument();
    });
    expect(screen.getByLabelText(/^Password$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Confirm Password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /register/i })).toBeInTheDocument();
  });

  it('validates password match', async () => {
    const user = userEvent.setup();

    renderComponent();

    // Wait for form to render after AuthProvider finishes loading
    await waitFor(() => {
      expect(screen.getByLabelText(/Username/i)).toBeInTheDocument();
    });

    const usernameInput = screen.getByLabelText(/Username/i);
    const passwordInput = screen.getByLabelText(/^Password$/i);
    const confirmPasswordInput = screen.getByLabelText(/Confirm Password/i);
    const submitButton = screen.getByRole('button', { name: /register/i });

    await user.type(usernameInput, 'testuser');
    await user.type(passwordInput, 'password123');
    await user.type(confirmPasswordInput, 'different');
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Passwords do not match/i)).toBeInTheDocument();
    });
  });

  it('validates password length', async () => {
    const user = userEvent.setup();

    renderComponent();

    const usernameInput = screen.getByLabelText(/Username/i);
    const passwordInput = screen.getByLabelText(/^Password$/i);
    const confirmPasswordInput = screen.getByLabelText(/Confirm Password/i);
    const submitButton = screen.getByRole('button', { name: /register/i });

    await user.type(usernameInput, 'testuser');
    await user.type(passwordInput, 'short');
    await user.type(confirmPasswordInput, 'short');
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Password must be at least 8 characters/i)).toBeInTheDocument();
    });
  });

  it('submits registration form with valid data', async () => {
    const user = userEvent.setup();
    api.register.mockResolvedValue({
      success: true,
      user: { username: 'newuser', role: 'user' },
      token: 'token123',
    });

    renderComponent();

    const usernameInput = screen.getByLabelText(/Username/i);
    const emailInput = screen.getByLabelText(/Email/i);
    const passwordInput = screen.getByLabelText(/^Password$/i);
    const confirmPasswordInput = screen.getByLabelText(/Confirm Password/i);
    const submitButton = screen.getByRole('button', { name: /register/i });

    await user.type(usernameInput, 'newuser');
    await user.type(emailInput, 'test@example.com');
    await user.type(passwordInput, 'password123');
    await user.type(confirmPasswordInput, 'password123');
    await user.click(submitButton);

    await waitFor(() => {
      expect(api.register).toHaveBeenCalledWith('newuser', 'password123', 'test@example.com');
    });
  });

  it('has link to login page', () => {
    renderComponent();
    const loginLink = screen.getByText(/Login here/i);
    expect(loginLink).toBeInTheDocument();
    expect(loginLink.closest('a')).toHaveAttribute('href', '/login');
  });
});
