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
  const [twoFactorStatus, setTwoFactorStatus] = useState(null);
  const [twoFactorSetup, setTwoFactorSetup] = useState(null);
  const [twoFactorToken, setTwoFactorToken] = useState('');
  const [disablePassword, setDisablePassword] = useState('');

  useEffect(() => {
    // Check auth on mount
    checkAuth();
    load2FAStatus();
  }, [checkAuth]);

  const load2FAStatus = async () => {
    try {
      const data = await api.get2FAStatus();
      if (data.success) {
        setTwoFactorStatus(data);
      }
    } catch (err) {
      console.error('Failed to load 2FA status:', err);
    }
  };

  const handleSetup2FA = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.setup2FA();
      if (data.success) {
        setTwoFactorSetup(data);
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to setup 2FA');
    } finally {
      setLoading(false);
    }
  };

  const handleVerify2FA = async () => {
    if (!twoFactorToken || twoFactorToken.length !== 6) {
      setError('Please enter a valid 6-digit code');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const data = await api.verify2FASetup(twoFactorToken);
      if (data.success) {
        setMessage('2FA enabled successfully!');
        setTwoFactorSetup(null);
        setTwoFactorToken('');
        await load2FAStatus();
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Invalid verification code');
    } finally {
      setLoading(false);
    }
  };

  const handleDisable2FA = async () => {
    if (!disablePassword) {
      setError('Password required to disable 2FA');
      return;
    }

    if (
      !window.confirm(
        'Are you sure you want to disable 2FA? This will make your account less secure.'
      )
    ) {
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const data = await api.disable2FA(disablePassword);
      if (data.success) {
        setMessage('2FA disabled successfully');
        setDisablePassword('');
        await load2FAStatus();
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to disable 2FA');
    } finally {
      setLoading(false);
    }
  };

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
              setError(
                err.response?.data?.error || err.message || `Failed to link ${provider} account`
              );
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
      <h1 className="text-2xl font-minecraft text-minecraft-grass-light mb-8 leading-tight">
        SETTINGS
      </h1>

      {/* Messages */}
      {message && (
        <div className="bg-minecraft-grass-DEFAULT border-2 border-minecraft-grass-dark p-4 mb-6 text-white text-[10px] font-minecraft">
          {message}
        </div>
      )}

      {error && (
        <div className="bg-[#C62828] border-2 border-[#B71C1C] p-4 mb-6 text-white text-[10px] font-minecraft">
          {error}
        </div>
      )}

      {/* Account Settings */}
      <div className="card-minecraft p-6 max-w-2xl mb-6">
        <h2 className="text-sm font-minecraft text-minecraft-text-light mb-4 uppercase">
          ACCOUNT INFORMATION
        </h2>

        {user && (
          <div className="space-y-2 mb-4">
            <div className="text-[10px] font-minecraft">
              <span className="text-minecraft-text-dark">USERNAME:</span>{' '}
              <span className="text-minecraft-text-light">{user.username}</span>
            </div>
            {user.email && (
              <div className="text-[10px] font-minecraft">
                <span className="text-minecraft-text-dark">EMAIL:</span>{' '}
                <span className="text-minecraft-text-light">{user.email}</span>
              </div>
            )}
            <div className="text-[10px] font-minecraft">
              <span className="text-minecraft-text-dark">ROLE:</span>{' '}
              <span className="text-minecraft-text-light uppercase">{user.role || 'user'}</span>
            </div>
          </div>
        )}
      </div>

      {/* Two-Factor Authentication */}
      <div className="card-minecraft p-6 max-w-2xl mb-6">
        <h2 className="text-sm font-minecraft text-minecraft-text-light mb-4 uppercase">
          TWO-FACTOR AUTHENTICATION
        </h2>

        {twoFactorStatus && (
          <div className="mb-4">
            <div className="text-[10px] font-minecraft mb-2">
              <span className="text-minecraft-text-dark">STATUS:</span>{' '}
              <span
                className={
                  twoFactorStatus.enabled
                    ? 'text-minecraft-grass-light'
                    : 'text-minecraft-text-light'
                }
              >
                {twoFactorStatus.enabled ? 'ENABLED' : 'DISABLED'}
              </span>
            </div>
          </div>
        )}

        {twoFactorSetup ? (
          <div className="space-y-4">
            <div className="text-[10px] font-minecraft text-minecraft-text-light">
              Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.):
            </div>
            {twoFactorSetup.qr_code && (
              <div className="flex justify-center p-4 bg-white">
                <img
                  src={`data:image/png;base64,${twoFactorSetup.qr_code}`}
                  alt="2FA QR Code"
                  className="w-48 h-48"
                />
              </div>
            )}
            <div className="text-[10px] font-minecraft text-minecraft-text-dark">
              Or enter this secret manually:{' '}
              <code className="bg-minecraft-dirt-DEFAULT px-2 py-1">{twoFactorSetup.secret}</code>
            </div>
            <div>
              <label className="block text-[10px] font-minecraft text-minecraft-text-light mb-2">
                ENTER VERIFICATION CODE
              </label>
              <input
                type="text"
                value={twoFactorToken}
                onChange={e => setTwoFactorToken(e.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="000000"
                maxLength={6}
                className="input-minecraft w-full"
                autoComplete="one-time-code"
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleVerify2FA}
                disabled={loading || twoFactorToken.length !== 6}
                className="btn-minecraft-primary text-[10px] disabled:opacity-50"
              >
                VERIFY & ENABLE
              </button>
              <button
                onClick={() => {
                  setTwoFactorSetup(null);
                  setTwoFactorToken('');
                }}
                className="btn-minecraft text-[10px]"
              >
                CANCEL
              </button>
            </div>
          </div>
        ) : twoFactorStatus?.enabled ? (
          <div className="space-y-4">
            <div className="text-[10px] font-minecraft text-minecraft-text-light">
              2FA is currently enabled. To disable it, enter your password below.
            </div>
            <div>
              <label className="block text-[10px] font-minecraft text-minecraft-text-light mb-2">
                PASSWORD
              </label>
              <input
                type="password"
                value={disablePassword}
                onChange={e => setDisablePassword(e.target.value)}
                placeholder="Enter password to disable 2FA"
                className="input-minecraft w-full"
              />
            </div>
            <button
              onClick={handleDisable2FA}
              disabled={loading || !disablePassword}
              className="btn-minecraft-danger text-[10px] disabled:opacity-50"
            >
              DISABLE 2FA
            </button>
          </div>
        ) : (
          <div>
            <div className="text-[10px] font-minecraft text-minecraft-text-light mb-4">
              Two-factor authentication adds an extra layer of security to your account.
            </div>
            <button
              onClick={handleSetup2FA}
              disabled={loading}
              className="btn-minecraft-primary text-[10px] disabled:opacity-50"
            >
              SETUP 2FA
            </button>
          </div>
        )}
      </div>

      {/* OAuth Account Linking */}
      <div className="card-minecraft p-6 max-w-2xl mb-6">
        <h2 className="text-sm font-minecraft text-minecraft-text-light mb-4 uppercase">
          CONNECTED ACCOUNTS
        </h2>

        <div className="space-y-4">
          {/* Google */}
          <div className="flex items-center justify-between p-4 bg-minecraft-dirt-DEFAULT border-2 border-[#5D4037]">
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
                <div className="text-sm font-minecraft text-minecraft-text-light">GOOGLE</div>
                <div className="text-[10px] font-minecraft text-minecraft-text-dark">
                  {hasOAuthProvider('google') ? 'CONNECTED' : 'NOT CONNECTED'}
                </div>
              </div>
            </div>
            {hasOAuthProvider('google') ? (
              <button
                onClick={() => handleUnlinkOAuth('google')}
                disabled={loading}
                className="btn-minecraft-danger text-[10px] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                UNLINK
              </button>
            ) : (
              <button
                onClick={() => handleLinkOAuth('google')}
                disabled={linking !== null}
                className="btn-minecraft text-[10px] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {linking === 'google' ? 'LINKING...' : 'LINK ACCOUNT'}
              </button>
            )}
          </div>

          {/* Apple */}
          <div className="flex items-center justify-between p-4 bg-minecraft-dirt-DEFAULT border-2 border-[#5D4037]">
            <div className="flex items-center gap-3">
              <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                <path d="M17.05 20.28c-.98.95-2.05.88-3.08.4-1.09-.5-2.08-.48-3.24 0-1.44.62-2.2.44-3.06-.4C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.24 2.31-.93 3.57-.84 1.51.12 2.65.72 3.4 1.8-3.12 1.87-2.38 5.98.48 7.13-.57 1.5-1.31 2.99-2.54 4.09l.01-.01zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z" />
              </svg>
              <div>
                <div className="text-sm font-minecraft text-minecraft-text-light">APPLE</div>
                <div className="text-[10px] font-minecraft text-minecraft-text-dark">
                  {hasOAuthProvider('apple') ? 'CONNECTED' : 'NOT CONNECTED'}
                </div>
              </div>
            </div>
            {hasOAuthProvider('apple') ? (
              <button
                onClick={() => handleUnlinkOAuth('apple')}
                disabled={loading}
                className="btn-minecraft-danger text-[10px] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                UNLINK
              </button>
            ) : (
              <button
                onClick={() => handleLinkOAuth('apple')}
                disabled={linking !== null}
                className="btn-minecraft text-[10px] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {linking === 'apple' ? 'LINKING...' : 'LINK ACCOUNT'}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* API Configuration */}
      <div className="card-minecraft p-6 max-w-2xl">
        <h2 className="text-sm font-minecraft text-minecraft-text-light mb-4 uppercase">
          API CONFIGURATION
        </h2>

        <div className="mb-4">
          <label className="block text-[10px] font-minecraft text-minecraft-text-light mb-2">
            API KEY
          </label>
          <input
            type="password"
            value={apiKey}
            onChange={e => setApiKey(e.target.value)}
            placeholder="ENTER YOUR API KEY"
            className="input-minecraft w-full"
          />
          <p className="text-[10px] font-minecraft text-minecraft-text-dark mt-2">
            GET YOUR API KEY BY RUNNING: ./scripts/api-key-manager.sh create
          </p>
        </div>

        <button onClick={handleSaveApiKey} className="btn-minecraft-primary text-[10px]">
          SAVE API KEY
        </button>
      </div>
    </div>
  );
};

export default Settings;
