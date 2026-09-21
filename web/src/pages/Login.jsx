import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
// import OAuthButtons from '../components/OAuthButtons'; // Disabled for future development
import { useToast } from '../components/ToastContainer';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Input } from '../components/ui/FormField';
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
    <div className="min-h-screen flex items-center justify-center bg-minecraft-background p-4">
      <Card padding="lg" animateIn className="w-full max-w-md p-8 shadow-2xl">
        <div className="text-center mb-8">
          <h1 className="text-xl lg:text-2xl font-minecraft text-minecraft-grass-light mb-2 leading-tight drop-shadow-lg">
            MINECRAFT ADMIN
          </h1>
          <h2 className="text-sm font-minecraft text-minecraft-text-light">LOGIN</h2>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="USERNAME"
            type="text"
            value={username}
            onChange={e => setUsername(e.target.value)}
            required
            placeholder="Enter username"
          />

          <Input
            label="PASSWORD"
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
            placeholder="Enter password"
          />

          {requires2FA && (
            <Input
              label="2FA CODE"
              type="text"
              value={totpToken}
              onChange={e => setTotpToken(e.target.value.replaceAll(/\D/g, '').slice(0, 6))}
              required
              placeholder="000000"
              maxLength={6}
              autoComplete="one-time-code"
            />
          )}

          <Button type="submit" variant="primary" className="w-full" disabled={loading}>
            {loading ? 'LOGGING IN...' : 'LOGIN'}
          </Button>
        </form>

        {/* OAuth buttons disabled for future development */}
        {/* <OAuthButtons /> */}

        <div className="mt-6 text-center text-[10px] font-minecraft text-minecraft-text-dark">
          DON&apos;T HAVE AN ACCOUNT?{' '}
          <Link
            to="/register"
            className="text-minecraft-grass-light hover:text-minecraft-grass"
          >
            REGISTER HERE
          </Link>
        </div>

        <div className="mt-4 text-center text-[8px] font-minecraft text-minecraft-text-dark">
          <Link to="/dashboard" className="hover:text-minecraft-text-light">
            CONTINUE WITH API KEY
          </Link>
        </div>
      </Card>
    </div>
  );
};

export default Login;
