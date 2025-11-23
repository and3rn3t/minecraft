import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../services/api';

const OAuthButtons = () => {
  const [loading, setLoading] = useState(null);
  const { checkAuth } = useAuth();
  const navigate = useNavigate();

  const getRedirectUri = () => {
    const protocol = window.location.protocol;
    const host = window.location.host;
    return `${protocol}//${host}/oauth/callback`;
  };

  const handleGoogleOAuth = async () => {
    try {
      setLoading('google');
      const redirectUri = getRedirectUri();
      const response = await api.getOAuthUrl('google', redirectUri);

      if (response.url) {
        // Open OAuth popup
        const width = 500;
        const height = 600;
        const left = window.screen.width / 2 - width / 2;
        const top = window.screen.height / 2 - height / 2;

        const popup = window.open(
          response.url,
          'Google Sign In',
          `width=${width},height=${height},left=${left},top=${top},resizable=yes,scrollbars=yes`
        );

        // Listen for OAuth callback
        const messageListener = event => {
          if (event.origin !== window.location.origin) {
            return;
          }

          if (event.data.type === 'OAUTH_CALLBACK') {
            handleOAuthCallback(event.data.code, 'google', redirectUri);
            window.removeEventListener('message', messageListener);
            popup.close();
          }
        };

        window.addEventListener('message', messageListener);

        // Check if popup was closed
        const checkClosed = setInterval(() => {
          if (popup.closed) {
            clearInterval(checkClosed);
            window.removeEventListener('message', messageListener);
            setLoading(null);
          }
        }, 1000);
      }
    } catch (error) {
      console.error('Google OAuth error:', error);
      setLoading(null);
    }
  };

  const handleAppleOAuth = async () => {
    try {
      setLoading('apple');
      const redirectUri = getRedirectUri();
      const response = await api.getOAuthUrl('apple', redirectUri);

      if (response.url) {
        // Open OAuth popup
        const width = 500;
        const height = 600;
        const left = window.screen.width / 2 - width / 2;
        const top = window.screen.height / 2 - height / 2;

        const popup = window.open(
          response.url,
          'Apple Sign In',
          `width=${width},height=${height},left=${left},top=${top},resizable=yes,scrollbars=yes`
        );

        // Listen for OAuth callback
        const messageListener = async event => {
          if (event.origin !== window.location.origin) {
            return;
          }

          if (event.data.type === 'OAUTH_CALLBACK') {
            try {
              await handleOAuthCallback(
                event.data.code,
                'apple',
                redirectUri,
                event.data.id_token,
                event.data.user
              );
              window.removeEventListener('message', messageListener);
            } catch (error) {
              console.error('OAuth callback failed:', error);
              alert(`Apple Sign-In failed: ${error.message || 'Unknown error'}`);
              window.removeEventListener('message', messageListener);
            }
            if (popup && !popup.closed) {
              popup.close();
            }
          }
        };

        window.addEventListener('message', messageListener);

        // Check if popup was closed
        const checkClosed = setInterval(() => {
          if (popup.closed) {
            clearInterval(checkClosed);
            window.removeEventListener('message', messageListener);
            setLoading(null);
          }
        }, 1000);
      }
    } catch (error) {
      console.error('Apple OAuth error:', error);
      alert(
        `Apple Sign-In failed: ${error.response?.data?.error || error.message || 'Unknown error'}`
      );
      setLoading(null);
    }
  };

  const handleOAuthCallback = async (
    code,
    provider,
    redirectUri,
    idToken = null,
    userData = null
  ) => {
    try {
      let result;
      if (provider === 'google') {
        result = await api.googleOAuthCallback(code, redirectUri);
      } else if (provider === 'apple') {
        result = await api.appleOAuthCallback(code, redirectUri, idToken, userData);
      }

      if (result && result.success) {
        // Save token
        if (result.token) {
          localStorage.setItem('auth_token', result.token);
        }

        // Refresh auth state
        await checkAuth();

        // Navigate to dashboard
        navigate('/dashboard');
      } else {
        throw new Error(result?.error || 'OAuth authentication failed');
      }
    } catch (error) {
      console.error('OAuth callback error:', error);
      // Error will be shown in OAuthButtons error handling
      throw error;
    } finally {
      setLoading(null);
    }
  };

  useEffect(() => {
    // Listen for OAuth errors from popup
    const errorListener = event => {
      if (event.origin !== window.location.origin) {
        return;
      }

      if (event.data.type === 'OAUTH_ERROR') {
        setLoading(null);
        console.error('OAuth Error:', event.data.error);
        // Error handling is done in the callback handlers
      }
    };

    window.addEventListener('message', errorListener);

    return () => {
      window.removeEventListener('message', errorListener);
    };
  }, []);

  return (
    <div className="space-y-3 mt-6">
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-gray-600"></div>
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="px-2 bg-gray-800 text-gray-400">Or continue with</span>
        </div>
      </div>

      <button
        onClick={handleGoogleOAuth}
        disabled={loading !== null}
        className="w-full flex items-center justify-center gap-3 px-4 py-2 bg-white hover:bg-gray-100 disabled:bg-gray-600 disabled:cursor-not-allowed text-gray-900 rounded transition-colors"
      >
        {loading === 'google' ? (
          <span className="animate-spin">⏳</span>
        ) : (
          <>
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              />
            </svg>
            Sign in with Google
          </>
        )}
      </button>

      <button
        onClick={handleAppleOAuth}
        disabled={loading !== null}
        className="w-full flex items-center justify-center gap-3 px-4 py-2 bg-black hover:bg-gray-900 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded transition-colors"
      >
        {loading === 'apple' ? (
          <span className="animate-spin">⏳</span>
        ) : (
          <>
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M17.05 20.28c-.98.95-2.05.88-3.08.4-1.09-.5-2.08-.48-3.24 0-1.44.62-2.2.44-3.06-.4C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.24 2.31-.93 3.57-.84 1.51.12 2.65.72 3.4 1.8-3.12 1.87-2.38 5.98.48 7.13-.57 1.5-1.31 2.99-2.54 4.09l.01-.01zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z" />
            </svg>
            Sign in with Apple
          </>
        )}
      </button>
    </div>
  );
};

export default OAuthButtons;
