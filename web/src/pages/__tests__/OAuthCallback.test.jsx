import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import OAuthCallback from '../OAuthCallback';

// The page runs in the sign-in popup: it reports the provider's result to the
// window that opened it, then closes itself.
const renderWith = query =>
  render(
    <MemoryRouter initialEntries={[`/oauth/callback${query}`]}>
      <OAuthCallback />
    </MemoryRouter>
  );

describe('OAuthCallback', () => {
  let opener;

  beforeEach(() => {
    vi.useFakeTimers();
    opener = { postMessage: vi.fn(), closed: false };
    // jsdom has no opener to spy on; define one for the page to talk to
    Object.defineProperty(window, 'opener', { configurable: true, writable: true, value: opener });
    vi.spyOn(window, 'close').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    delete window.opener;
  });

  it('says it is completing sign-in', () => {
    renderWith('?code=abc&state=s');
    expect(screen.getByText('COMPLETING AUTHENTICATION...')).toBeInTheDocument();
  });

  it('hands a Google code and state to the opener, only on this origin', () => {
    renderWith('?code=abc&state=s');

    expect(opener.postMessage).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'OAUTH_CALLBACK', code: 'abc', state: 's' }),
      window.location.origin
    );
  });

  it('hands an Apple ID token and user to the opener', () => {
    const user = encodeURIComponent(JSON.stringify({ name: { firstName: 'Silas' } }));
    renderWith(`?id_token=tok&state=s&user=${user}`);

    expect(opener.postMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'OAUTH_CALLBACK',
        id_token: 'tok',
        user: { name: { firstName: 'Silas' } },
      }),
      window.location.origin
    );
  });

  it('closes the popup shortly after reporting', () => {
    renderWith('?code=abc&state=s');

    expect(window.close).not.toHaveBeenCalled();
    vi.advanceTimersByTime(500);
    expect(window.close).toHaveBeenCalled();
  });

  it('reports a provider error with its description and closes at once', () => {
    renderWith('?error=access_denied&error_description=User%20cancelled');

    expect(opener.postMessage).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'OAUTH_ERROR', error: 'User cancelled' }),
      window.location.origin
    );
    expect(window.close).toHaveBeenCalled();
  });

  it('reports an error when neither a code nor a token arrived', () => {
    renderWith('?state=s');

    expect(opener.postMessage).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'OAUTH_ERROR', error: 'No authorization code received' }),
      window.location.origin
    );
  });

  it('reports malformed user data as an error rather than failing silently', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    renderWith('?id_token=tok&user=%7Bnot-json');

    expect(opener.postMessage).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'OAUTH_ERROR', error: 'Failed to process OAuth callback' }),
      window.location.origin
    );
  });

  it('does not post to an opener that has already closed', () => {
    opener.closed = true;
    renderWith('?code=abc&state=s');

    expect(opener.postMessage).not.toHaveBeenCalled();
  });
});
