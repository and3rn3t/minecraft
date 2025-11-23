import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import OAuthButtons from '../components/OAuthButtons';
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
    <div className="min-h-screen flex items-center justify-center bg-minecraft-background-DEFAULT">
      <div className="card-minecraft p-8 w-full max-w-md">
        <h1 className="text-xl font-minecraft text-minecraft-grass-light mb-6 text-center leading-tight">
          MINECRAFT ADMIN
        </h1>
        <h2 className="text-sm font-minecraft text-minecraft-text-light mb-6 text-center">
          REGISTER
        </h2>

        {error && (
          <div className="bg-[#C62828] border-2 border-[#B71C1C] p-4 mb-6 text-white text-[10px] font-minecraft">
            {error}
          </div>
        )}

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
              minLength={3}
              maxLength={32}
              className="input-minecraft w-full"
              placeholder="Enter username (3-32 characters)"
            />
          </div>

          <div>
            <label
              htmlFor="email"
              className="block text-[10px] font-minecraft text-minecraft-text-light mb-2"
            >
              EMAIL (OPTIONAL)
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="input-minecraft w-full"
              placeholder="Enter email"
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
              minLength={8}
              className="input-minecraft w-full"
              placeholder="Enter password (min 8 characters)"
            />
          </div>

          <div>
            <label
              htmlFor="confirmPassword"
              className="block text-[10px] font-minecraft text-minecraft-text-light mb-2"
            >
              CONFIRM PASSWORD
            </label>
            <input
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={e => setConfirmPassword(e.target.value)}
              required
              minLength={8}
              className="input-minecraft w-full"
              placeholder="Confirm password"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn-minecraft-primary w-full text-[10px] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'REGISTERING...' : 'REGISTER'}
          </button>
        </form>

        <OAuthButtons />

        <div className="mt-6 text-center text-[10px] font-minecraft text-minecraft-text-dark">
          ALREADY HAVE AN ACCOUNT?{' '}
          <Link
            to="/login"
            className="text-minecraft-grass-light hover:text-minecraft-grass-DEFAULT"
          >
            LOGIN HERE
          </Link>
        </div>
      </div>
    </div>
  );
};

export default Register;
