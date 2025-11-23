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
    { path: '/users', label: 'Users & Roles', icon: '👤' },
    { path: '/settings', label: 'Settings', icon: '⚙️' },
  ];

  return (
    <div className="min-h-screen bg-minecraft-background-DEFAULT text-minecraft-text-DEFAULT">
      {/* Sidebar */}
      <aside className="fixed left-0 top-0 h-full w-64 card-minecraft flex flex-col">
        <div className="p-6 border-b-2 border-[#5D4037]">
          <h1 className="text-lg font-minecraft text-minecraft-grass-light leading-tight">
            MINECRAFT
          </h1>
          <p className="text-[8px] font-minecraft text-minecraft-text-dark mt-2 leading-tight">
            SERVER ADMIN
          </p>
        </div>
        <nav className="mt-4 flex-1 overflow-y-auto">
          {navItems.map(item => {
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center px-4 py-3 text-[10px] font-minecraft ${
                  isActive
                    ? 'bg-minecraft-grass-DEFAULT text-white border-r-4 border-minecraft-grass-light'
                    : 'text-minecraft-text-dark hover:bg-minecraft-dirt-DEFAULT hover:text-white'
                }`}
              >
                <span className="mr-2 text-xs">{item.icon}</span>
                {item.label.toUpperCase()}
              </Link>
            );
          })}
        </nav>
        <div className="p-4 border-t-2 border-[#5D4037]">
          {isAuthenticated && user && (
            <div className="mb-3 text-[8px] font-minecraft">
              <div className="text-minecraft-text-dark mb-1">LOGGED IN AS</div>
              <div className="text-[10px] text-minecraft-text-light">{user.username}</div>
              {user.role && (
                <div className="text-[8px] text-minecraft-text-dark mt-1 uppercase">
                  {user.role}
                </div>
              )}
            </div>
          )}
          {isAuthenticated && (
            <button onClick={handleLogout} className="btn-minecraft w-full text-[10px]">
              LOGOUT
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
