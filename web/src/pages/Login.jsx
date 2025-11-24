import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
// import OAuthButtons from '../components/OAuthButtons'; // Disabled for future development
import { useToast } from '../components/ToastContainer';
import { useAuth } from '../contexts/AuthContext';

const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [totpToken, setTotpToken] = useState('');
  const [requires2FA, setRequires2FA] = useState(false);
  const [loading, setLoading] = useState(false);
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const { error: showError, info } = useToast();

  useEffect(() => {
    // Redirect if already authenticated
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate]);

  const handleSubmit = async e => {
    e.preventDefault();
    setLoading(true);

    try {
      const result = await login(username, password, requires2FA ? totpToken : null);
      if (result.success) {
        navigate('/dashboard');
      } else {
        if (result.requires_2fa) {
          setRequires2FA(true);
          info('Please enter your 2FA code');
        } else {
          showError(result.error || 'Login failed');
        }
      }
    } catch (err) {
      showError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-minecraft-background-DEFAULT p-4">
      <div className="card-minecraft p-8 w-full max-w-md animate-fadeIn shadow-2xl">
        <div className="text-center mb-8">
          <h1 className="text-xl lg:text-2xl font-minecraft text-minecraft-grass-light mb-2 leading-tight drop-shadow-lg">
            MINECRAFT ADMIN
          </h1>
          <h2 className="text-sm font-minecraft text-minecraft-text-light">LOGIN</h2>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="username"
              className="block text-[10px] font-minecraft text-minecraft-text-light mb-2"
            >
              USERNAME
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
              className="input-minecraft w-full"
              placeholder="Enter username"
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="block text-[10px] font-minecraft text-minecraft-text-light mb-2"
            >
              PASSWORD
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              className="input-minecraft w-full"
              placeholder="Enter password"
            />
          </div>

          {requires2FA && (
            <div>
              <label
                htmlFor="totp"
                className="block text-[10px] font-minecraft text-minecraft-text-light mb-2"
              >
                2FA CODE
              </label>
              <input
                id="totp"
                type="text"
                value={totpToken}
                onChange={e => setTotpToken(e.target.value.replaceAll(/\D/g, '').slice(0, 6))}
                required
                className="input-minecraft w-full"
                placeholder="000000"
                maxLength={6}
                autoComplete="one-time-code"
              />
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn-minecraft-primary w-full text-[10px] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'LOGGING IN...' : 'LOGIN'}
          </button>
        </form>

        {/* OAuth buttons disabled for future development */}
        {/* <OAuthButtons /> */}

        <div className="mt-6 text-center text-[10px] font-minecraft text-minecraft-text-dark">
          DON&apos;T HAVE AN ACCOUNT?{' '}
          <Link
            to="/register"
            className="text-minecraft-grass-light hover:text-minecraft-grass-DEFAULT"
          >
            REGISTER HERE
          </Link>
        </div>

        <div className="mt-4 text-center text-[8px] font-minecraft text-minecraft-text-dark">
          <Link to="/dashboard" className="hover:text-minecraft-text-light">
            CONTINUE WITH API KEY
          </Link>
        </div>
      </div>
    </div>
  );
};

export default Login;
