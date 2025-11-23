import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900">
        <div className="text-xl">Loading...</div>
      </div>
    );
  }

  // Allow access if authenticated OR if API key is set (backward compatibility)
  const hasApiKey = localStorage.getItem('api_key');
  if (!isAuthenticated && !hasApiKey) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

export default ProtectedRoute;
