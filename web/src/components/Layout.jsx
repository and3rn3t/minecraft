import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const Layout = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, isAuthenticated, logout } = useAuth();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const navItems = [
    { path: '/dashboard', label: 'Dashboard', icon: '📊' },
    { path: '/logs', label: 'Logs', icon: '📝' },
    { path: '/players', label: 'Players', icon: '👥' },
    { path: '/backups', label: 'Backups', icon: '💾' },
    { path: '/worlds', label: 'Worlds', icon: '🌍' },
    { path: '/plugins', label: 'Plugins', icon: '🔌' },
    { path: '/config', label: 'Config Files', icon: '📄' },
    { path: '/api-keys', label: 'API Keys', icon: '🔑' },
    { path: '/settings', label: 'Settings', icon: '⚙️' },
  ];

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Sidebar */}
      <aside className="fixed left-0 top-0 h-full w-64 bg-gray-800 border-r border-gray-700 flex flex-col">
        <div className="p-6">
          <h1 className="text-2xl font-bold text-primary-400">Minecraft Admin</h1>
          <p className="text-sm text-gray-400 mt-1">Server Management</p>
        </div>
        <nav className="mt-8 flex-1">
          {navItems.map(item => {
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center px-6 py-3 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-primary-600 text-white border-r-2 border-primary-400'
                    : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                }`}
              >
                <span className="mr-3 text-lg">{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="p-4 border-t border-gray-700">
          {isAuthenticated && user && (
            <div className="mb-3">
              <div className="text-xs text-gray-400 mb-1">Logged in as</div>
              <div className="text-sm font-medium">{user.username}</div>
              {user.role && <div className="text-xs text-gray-500 capitalize">{user.role}</div>}
            </div>
          )}
          {isAuthenticated && (
            <button
              onClick={handleLogout}
              className="w-full px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm transition-colors"
            >
              Logout
            </button>
          )}
        </div>
      </aside>

      {/* Main Content */}
      <main className="ml-64 p-8">{children}</main>
    </div>
  );
};

export default Layout;
