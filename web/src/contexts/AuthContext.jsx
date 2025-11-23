import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { api } from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is logged in
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const userData = await api.getCurrentUser();
      setUser(userData);
    } catch (error) {
      // User not authenticated, clear state
      setUser(null);
      localStorage.removeItem('auth_token');
    } finally {
      setLoading(false);
    }
  };

  const login = async (username, password, totpToken = null) => {
    try {
      const data = await api.login(username, password, totpToken);
      setUser(data.user);
      if (data.token) {
        localStorage.setItem('auth_token', data.token);
      }
      return { success: true, user: data.user };
    } catch (error) {
      const requires2FA = error.response?.data?.requires_2fa;
      return {
        success: false,
        error: error.response?.data?.error || error.message || 'Login failed',
        requires_2fa: requires2FA,
      };
    }
  };

  const register = async (username, password, email) => {
    try {
      const data = await api.register(username, password, email);
      setUser(data.user);
      if (data.token) {
        localStorage.setItem('auth_token', data.token);
      }
      return { success: true, user: data.user };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || error.message || 'Registration failed',
      };
    }
  };

  const logout = async () => {
    try {
      await api.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      setUser(null);
      localStorage.removeItem('auth_token');
    }
  };

  const value = useMemo(
    () => ({
      user,
      loading,
      isAuthenticated: !!user,
      login,
      register,
      logout,
      checkAuth,
    }),
    [user, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export default AuthContext;
