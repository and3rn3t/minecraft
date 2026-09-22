import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
// import OAuthButtons from '../components/OAuthButtons'; // Disabled for future development
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { ErrorState } from '../components/ui/Alert';
import { Input } from '../components/ui/FormField';
import { useAuth } from '../contexts/AuthContext';

const Register = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [email, setEmail] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const { register, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    // Redirect if already authenticated
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate]);

  const handleSubmit = async e => {
    e.preventDefault();
    setError(null);

    // Validation
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    if (username.length < 3 || username.length > 32) {
      setError('Username must be 3-32 characters');
      return;
    }

    setLoading(true);

    try {
      const result = await register(username, password, email);
      if (result.success) {
        navigate('/dashboard');
      } else {
        setError(result.error || 'Registration failed');
      }
    } catch (err) {
      setError(err.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-minecraft-background">
      <Card padding="lg" className="w-full max-w-md p-8">
        <h1 className="text-xl font-minecraft text-minecraft-grass-light mb-6 text-center leading-tight">
          MINECRAFT ADMIN
        </h1>
        <h2 className="text-sm font-minecraft text-minecraft-text-light mb-6 text-center">
          REGISTER
        </h2>

        {error && <ErrorState message={error} />}

        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="USERNAME"
            type="text"
            value={username}
            onChange={e => setUsername(e.target.value)}
            required
            minLength={3}
            maxLength={32}
            placeholder="Enter username (3-32 characters)"
          />

          <Input
            label="EMAIL (OPTIONAL)"
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            placeholder="Enter email"
          />

          <Input
            label="PASSWORD"
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
            minLength={8}
            placeholder="Enter password (min 8 characters)"
          />

          <Input
            label="CONFIRM PASSWORD"
            type="password"
            value={confirmPassword}
            onChange={e => setConfirmPassword(e.target.value)}
            required
            minLength={8}
            placeholder="Confirm password"
          />

          <Button type="submit" variant="primary" className="w-full" disabled={loading}>
            {loading ? 'REGISTERING...' : 'REGISTER'}
          </Button>
        </form>

        {/* OAuth buttons disabled for future development */}
        {/* <OAuthButtons /> */}

        <div className="mt-6 text-center text-[10px] font-minecraft text-minecraft-text-dark">
          ALREADY HAVE AN ACCOUNT?{' '}
          <Link
            to="/login"
            className="text-minecraft-grass-light hover:text-minecraft-grass"
          >
            LOGIN HERE
          </Link>
        </div>
      </Card>
    </div>
  );
};

export default Register;
