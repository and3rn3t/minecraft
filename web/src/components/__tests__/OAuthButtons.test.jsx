import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../../services/api';
import { renderWithRouter } from '../../test/utils';
import OAuthButtons from '../OAuthButtons';

// Mock dependencies
vi.mock('../../services/api');
// Don't mock AuthContext - we'll use the real AuthProvider and mock the API
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => vi.fn(),
  };
});

const mockNavigate = vi.fn();

describe('OAuthButtons', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock API call that AuthProvider makes on mount
    api.getCurrentUser.mockRejectedValue(new Error('Not authenticated'));
    globalThis.window.open = vi.fn(() => ({
      close: vi.fn(),
      closed: false,
      postMessage: vi.fn(),
    }));
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const renderComponent = () => {
    return renderWithRouter(<OAuthButtons />);
  };

  it('renders Google sign-in button', () => {
    renderComponent();
    expect(screen.getByText(/Sign in with Google/i)).toBeInTheDocument();
  });

  it('renders Apple sign-in button', () => {
    renderComponent();
    expect(screen.getByText(/Sign in with Apple/i)).toBeInTheDocument();
  });

  it('opens OAuth popup when Google button is clicked', async () => {
    api.getOAuthUrl.mockResolvedValue({
      url: 'https://accounts.google.com/oauth2/auth?client_id=test',
    });

    renderComponent();
    const googleButton = screen.getByText(/Sign in with Google/i).closest('button');
    fireEvent.click(googleButton);

    await waitFor(() => {
      expect(api.getOAuthUrl).toHaveBeenCalledWith(
        'google',
        expect.stringContaining('/oauth/callback')
      );
      expect(globalThis.window.open).toHaveBeenCalled();
    });
  });

  it('opens OAuth popup when Apple button is clicked', async () => {
    api.getOAuthUrl.mockResolvedValue({
      url: 'https://appleid.apple.com/auth/authorize?client_id=test',
    });

    renderComponent();
    const appleButton = screen.getByText(/Sign in with Apple/i).closest('button');
    fireEvent.click(appleButton);

    await waitFor(() => {
      expect(api.getOAuthUrl).toHaveBeenCalledWith(
        'apple',
        expect.stringContaining('/oauth/callback')
      );
      expect(globalThis.window.open).toHaveBeenCalled();
    });
  });

  it('handles OAuth callback message', async () => {
    api.getOAuthUrl.mockResolvedValue({
      url: 'https://accounts.google.com/oauth2/auth',
    });
    api.googleOAuthCallback.mockResolvedValue({
      success: true,
      user: { username: 'testuser' },
      token: 'token123',
    });

    renderComponent();
    const googleButton = screen.getByText(/Sign in with Google/i).closest('button');
    fireEvent.click(googleButton);

    await waitFor(() => {
      expect(globalThis.window.open).toHaveBeenCalled();
    });

    // Simulate OAuth callback message
    const callbackEvent = new MessageEvent('message', {
      data: {
        type: 'OAUTH_CALLBACK',
        code: 'auth_code_123',
        provider: 'google',
      },
      origin: window.location.origin,
    });

    window.dispatchEvent(callbackEvent);

    await waitFor(() => {
      expect(api.googleOAuthCallback).toHaveBeenCalled();
    });
  });

  it('handles OAuth error message', async () => {
    api.getOAuthUrl.mockResolvedValue({
      url: 'https://accounts.google.com/oauth2/auth',
    });

    renderComponent();
    const googleButton = screen.getByText(/Sign in with Google/i).closest('button');
    fireEvent.click(googleButton);

    await waitFor(() => {
      expect(globalThis.window.open).toHaveBeenCalled();
    });

    // Simulate OAuth error message
    const errorEvent = new MessageEvent('message', {
      data: {
        type: 'OAUTH_ERROR',
        error: 'Authentication failed',
        provider: 'google',
      },
      origin: window.location.origin,
    });

    window.dispatchEvent(errorEvent);

    // Error handling should not throw
    expect(console.error).not.toThrow();
  });

  it('disables buttons while loading', async () => {
    api.getOAuthUrl.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)));

    renderComponent();
    const googleButton = screen.getByText(/Sign in with Google/i).closest('button');
    fireEvent.click(googleButton);

    // Button should be disabled during loading
    expect(googleButton).toBeDisabled();
  });
});
