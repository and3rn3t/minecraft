import { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../services/api';

const Settings = () => {
  const { user, checkAuth } = useAuth();
  const [apiKey, setApiKey] = useState(localStorage.getItem('api_key') || '');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);
  const [linking, setLinking] = useState(null);

  useEffect(() => {
    // Check auth on mount
    checkAuth();
  }, [checkAuth]);

  const handleSaveApiKey = () => {
    if (apiKey) {
      localStorage.setItem('api_key', apiKey);
      setMessage('API key saved!');
      setTimeout(() => setMessage(null), 3000);
    } else {
      localStorage.removeItem('api_key');
      setMessage('API key removed!');
      setTimeout(() => setMessage(null), 3000);
    }
  };

  const getOAuthProviderName = provider => {
    if (provider.startsWith('google:')) return 'Google';
    if (provider.startsWith('apple:')) return 'Apple';
    return provider;
  };

  const handleLinkOAuth = async provider => {
    try {
      setLinking(provider);
      setError(null);
      setMessage(null);

      // Get OAuth URL
      const redirectUri = `${window.location.protocol}//${window.location.host}/oauth/callback`;
      const response = await api.getOAuthUrl(provider, redirectUri);

      if (response.url) {
        // Open OAuth popup for linking
        const width = 500;
        const height = 600;
        const left = window.screen.width / 2 - width / 2;
        const top = window.screen.height / 2 - height / 2;

        const popup = window.open(
          response.url,
          `${provider} Link Account`,
          `width=${width},height=${height},left=${left},top=${top},resizable=yes,scrollbars=yes`
        );

        // Listen for OAuth callback
        const messageListener = async event => {
          if (event.origin !== window.location.origin) {
            return;
          }

          if (event.data.type === 'OAUTH_CALLBACK') {
            try {
              // Link the OAuth account
              const result = await api.linkOAuthAccount(
                provider,
                event.data.code,
                redirectUri,
                event.data.id_token,
                event.data.user
              );

              if (result.success) {
                setMessage(`${provider} account linked successfully!`);
                await checkAuth(); // Refresh user data
              } else {
                setError(result.error || `Failed to link ${provider} account`);
              }
            } catch (err) {
              setError(err.response?.data?.error || err.message || `Failed to link ${provider} account`);
            } finally {
              setLinking(null);
              if (popup && !popup.closed) {
                popup.close();
              }
            }
            window.removeEventListener('message', messageListener);
          }

          if (event.data.type === 'OAUTH_ERROR') {
            setError(event.data.error || `Failed to link ${provider} account`);
            setLinking(null);
            if (popup && !popup.closed) {
              popup.close();
            }
            window.removeEventListener('message', messageListener);
          }
        };

        window.addEventListener('message', messageListener);

        // Check if popup was closed
        const checkClosed = setInterval(() => {
          if (popup.closed) {
            clearInterval(checkClosed);
            window.removeEventListener('message', messageListener);
            setLinking(null);
          }
        }, 1000);
      }
    } catch (err) {
      setError(err.response?.data?.error || err.message || `Failed to start ${provider} linking`);
      setLinking(null);
    }
  };

  const handleUnlinkOAuth = async provider => {
    if (!window.confirm(`Are you sure you want to unlink your ${provider} account?`)) {
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setMessage(null);

      const result = await api.unlinkOAuthAccount(provider);

      if (result.success) {
        setMessage(`${provider} account unlinked successfully!`);
        await checkAuth(); // Refresh user data
      } else {
        setError(result.error || `Failed to unlink ${provider} account`);
      }
    } catch (err) {
      setError(err.response?.data?.error || err.message || `Failed to unlink ${provider} account`);
    } finally {
      setLoading(false);
    }
  };

  const hasOAuthProvider = provider => {
    if (!user?.oauth_providers) return false;
    return user.oauth_providers.some(p => p.startsWith(`${provider}:`));
  };

  return (
    <div>
      <h1 className="text-3xl font-bold mb-8">Settings</h1>

      {/* Messages */}
      {message && (
        <div className="bg-green-900/50 border border-green-700 rounded p-4 mb-6 text-green-300">
          {message}
        </div>
      )}

      {error && (
        <div className="bg-red-900/50 border border-red-700 rounded p-4 mb-6 text-red-300">
          {error}
        </div>
      )}

      {/* Account Settings */}
      <div className="bg-gray-800 rounded-lg p-6 max-w-2xl mb-6">
        <h2 className="text-xl font-semibold mb-4">Account Information</h2>

        {user && (
          <div className="space-y-2 mb-4">
            <div>
              <span className="text-sm text-gray-400">Username:</span>{' '}
              <span className="font-medium">{user.username}</span>
            </div>
            {user.email && (
              <div>
                <span className="text-sm text-gray-400">Email:</span> <span>{user.email}</span>
              </div>
            )}
            <div>
              <span className="text-sm text-gray-400">Role:</span>{' '}
              <span className="capitalize">{user.role || 'user'}</span>
            </div>
          </div>
        )}
      </div>

      {/* OAuth Account Linking */}
      <div className="bg-gray-800 rounded-lg p-6 max-w-2xl mb-6">
        <h2 className="text-xl font-semibold mb-4">Connected Accounts</h2>

        <div className="space-y-4">
          {/* Google */}
          <div className="flex items-center justify-between p-4 bg-gray-700 rounded border border-gray-600">
            <div className="flex items-center gap-3">
              <svg className="w-6 h-6" viewBox="0 0 24 24">
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
              <div>
                <div className="font-medium">Google</div>
                <div className="text-sm text-gray-400">
                  {hasOAuthProvider('google') ? 'Connected' : 'Not connected'}
                </div>
              </div>
            </div>
            {hasOAuthProvider('google') ? (
              <button
                onClick={() => handleUnlinkOAuth('google')}
                disabled={loading}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded text-sm transition-colors"
              >
                Unlink
              </button>
            ) : (
              <button
                onClick={() => handleLinkOAuth('google')}
                disabled={linking !== null}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded text-sm transition-colors"
              >
                {linking === 'google' ? 'Linking...' : 'Link Account'}
              </button>
            )}
          </div>

          {/* Apple */}
          <div className="flex items-center justify-between p-4 bg-gray-700 rounded border border-gray-600">
            <div className="flex items-center gap-3">
              <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                <path d="M17.05 20.28c-.98.95-2.05.88-3.08.4-1.09-.5-2.08-.48-3.24 0-1.44.62-2.2.44-3.06-.4C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.24 2.31-.93 3.57-.84 1.51.12 2.65.72 3.4 1.8-3.12 1.87-2.38 5.98.48 7.13-.57 1.5-1.31 2.99-2.54 4.09l.01-.01zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z" />
              </svg>
              <div>
                <div className="font-medium">Apple</div>
                <div className="text-sm text-gray-400">
                  {hasOAuthProvider('apple') ? 'Connected' : 'Not connected'}
                </div>
              </div>
            </div>
            {hasOAuthProvider('apple') ? (
              <button
                onClick={() => handleUnlinkOAuth('apple')}
                disabled={loading}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded text-sm transition-colors"
              >
                Unlink
              </button>
            ) : (
              <button
                onClick={() => handleLinkOAuth('apple')}
                disabled={linking !== null}
                className="px-4 py-2 bg-black hover:bg-gray-900 disabled:bg-gray-600 disabled:cursor-not-allowed rounded text-sm transition-colors"
              >
                {linking === 'apple' ? 'Linking...' : 'Link Account'}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* API Configuration */}
      <div className="bg-gray-800 rounded-lg p-6 max-w-2xl">
        <h2 className="text-xl font-semibold mb-4">API Configuration</h2>

        <div className="mb-4">
          <label className="block text-sm font-medium mb-2">API Key</label>
          <input
            type="password"
            value={apiKey}
            onChange={e => setApiKey(e.target.value)}
            placeholder="Enter your API key"
            className="w-full bg-gray-700 text-white px-4 py-2 rounded border border-gray-600 focus:outline-none focus:border-primary-500"
          />
          <p className="text-sm text-gray-400 mt-2">
            Get your API key by running: ./scripts/api-key-manager.sh create
          </p>
        </div>

        <button
          onClick={handleSaveApiKey}
          className="px-4 py-2 bg-primary-600 hover:bg-primary-700 rounded transition-colors"
        >
          Save API Key
        </button>
      </div>
    </div>
  );
};

export default Settings;
