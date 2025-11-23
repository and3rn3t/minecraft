import { useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';

const OAuthCallback = () => {
  const [searchParams] = useSearchParams();

  useEffect(() => {
    // Extract OAuth callback parameters from URL
    const code = searchParams.get('code');
    const error = searchParams.get('error');
    const errorDescription = searchParams.get('error_description');
    const state = searchParams.get('state');
    const idToken = searchParams.get('id_token');
    const userData = searchParams.get('user');

    // Get provider from state or try to detect from URL
    let provider = 'google';
    if (window.location.href.includes('appleid.apple.com')) {
      provider = 'apple';
    } else if (state) {
      // Provider could be encoded in state
      try {
        const stateData = JSON.parse(atob(state));
        provider = stateData.provider || provider;
      } catch {
        // Ignore parse errors
      }
    }

    // Handle errors
    if (error) {
      const errorMsg = errorDescription || error || 'OAuth authentication failed';
      window.opener?.postMessage(
        {
          type: 'OAUTH_ERROR',
          error: errorMsg,
          provider,
        },
        window.location.origin
      );
      window.close();
      return;
    }

    // Handle success
    if (code || idToken) {
      try {
        const user = userData ? JSON.parse(decodeURIComponent(userData)) : null;

        if (window.opener && !window.opener.closed) {
          window.opener.postMessage(
            {
              type: 'OAUTH_CALLBACK',
              code,
              id_token: idToken,
              provider,
              user,
            },
            window.location.origin
          );
        }

        // Close popup after a short delay to ensure message is sent
        setTimeout(() => {
          if (!window.closed) {
            window.close();
          }
        }, 500);
      } catch (err) {
        console.error('OAuth callback error:', err);
        if (window.opener && !window.opener.closed) {
          window.opener.postMessage(
            {
              type: 'OAUTH_ERROR',
              error: 'Failed to process OAuth callback',
              provider,
            },
            window.location.origin
          );
        }
        setTimeout(() => {
          if (!window.closed) {
            window.close();
          }
        }, 1000);
      }
    } else {
      // No code or token, assume error
      if (window.opener && !window.opener.closed) {
        window.opener.postMessage(
          {
            type: 'OAUTH_ERROR',
            error: 'No authorization code received',
            provider,
          },
          window.location.origin
        );
      }
      setTimeout(() => {
        if (!window.closed) {
          window.close();
        }
      }, 1000);
    }
  }, [searchParams]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900">
      <div className="text-center">
        <div className="animate-spin text-4xl mb-4">⏳</div>
        <p className="text-gray-400">Completing authentication...</p>
      </div>
    </div>
  );
};

export default OAuthCallback;
