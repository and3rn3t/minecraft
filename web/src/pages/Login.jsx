import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import OAuthButtons from '../components/OAuthButtons';
import { useAuth } from '../contexts/AuthContext';

const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const { login, isAuthenticated } = useAuth();
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
    setLoading(true);

    try {
      const result = await login(username, password);
      if (result.success) {
        navigate('/dashboard');
      } else {
        setError(result.error || 'Login failed');
      }
    } catch (err) {
      setError(err.message || 'Login failed');
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
        <h2 className="text-sm font-minecraft text-minecraft-text-light mb-6 text-center">LOGIN</h2>

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

          <button
            type="submit"
            disabled={loading}
            className="btn-minecraft-primary w-full text-[10px] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'LOGGING IN...' : 'LOGIN'}
          </button>
        </form>

        <OAuthButtons />

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
