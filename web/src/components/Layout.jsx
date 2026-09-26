import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from './ui/Button';

// Static across every render — building this and its filtered groups fresh
// on every Layout render (every route change, every auth-context update) was
// pure waste.
const NAV_ITEMS = [
  { path: '/dashboard', label: 'Dashboard', icon: '📊', category: 'main' },
  { path: '/analytics', label: 'Analytics', icon: '📈', category: 'main' },
  { path: '/logs', label: 'Logs', icon: '📝', category: 'main' },
  { path: '/console', label: 'Console', icon: '💻', category: 'main' },
  { path: '/scheduler', label: 'Scheduler', icon: '⏰', category: 'main' },
  { path: '/bedtime', label: 'Bedtime', icon: '🌙', category: 'main' },
  { path: '/players', label: 'Players', icon: '👥', category: 'server' },
  { path: '/deaths', label: 'Hall of Deaths', icon: '💀', category: 'server' },
  { path: '/backups', label: 'Backups', icon: '💾', category: 'server' },
  { path: '/worlds', label: 'Worlds', icon: '🌍', category: 'server' },
  { path: '/plugins', label: 'Plugins', icon: '🔌', category: 'server' },
  { path: '/datapacks', label: 'Datapacks', icon: '📦', category: 'server' },
  { path: '/config', label: 'Config Files', icon: '📄', category: 'server' },
  { path: '/files', label: 'File Browser', icon: '📂', category: 'tools' },
  { path: '/ddns', label: 'Dynamic DNS', icon: '🌐', category: 'tools' },
  { path: '/api-keys', label: 'API Keys', icon: '🔑', category: 'admin' },
  { path: '/users', label: 'Users & Roles', icon: '👤', category: 'admin' },
  { path: '/audit', label: 'Audit Logs', icon: '📋', category: 'admin' },
  { path: '/settings', label: 'Settings', icon: '⚙️', category: 'admin' },
];

const GROUPED_ITEMS = {
  main: NAV_ITEMS.filter(item => item.category === 'main'),
  server: NAV_ITEMS.filter(item => item.category === 'server'),
  tools: NAV_ITEMS.filter(item => item.category === 'tools'),
  admin: NAV_ITEMS.filter(item => item.category === 'admin'),
};

const Layout = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, isAuthenticated, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-minecraft-background text-minecraft-text">
      {/* Mobile Menu Button */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="lg:hidden fixed top-4 left-4 z-50 btn-minecraft text-[10px]"
        aria-expanded={sidebarOpen}
        aria-controls="sidebar-nav"
      >
        {sidebarOpen ? '✕' : '☰'} MENU
      </button>

      {/* Sidebar Overlay (Mobile) */}
      {sidebarOpen && (
        <button
          type="button"
          className="lg:hidden fixed inset-0 bg-black bg-opacity-50 z-40 cursor-default"
          onClick={() => setSidebarOpen(false)}
          aria-label="Close sidebar"
        />
      )}

      {/* Sidebar */}
      <aside
        id="sidebar-nav"
        className={`fixed left-0 top-0 h-full w-64 card-minecraft flex flex-col z-40 transform transition-transform duration-300 ease-in-out ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        <div className="p-6 border-b-2 border-[#5D4037] bg-gradient-to-br from-[#6D4C41] to-[#5D4037]">
          <h1 className="text-lg font-minecraft text-minecraft-grass-light leading-tight drop-shadow-lg">
            MINECRAFT
          </h1>
          <p className="text-[8px] font-minecraft text-minecraft-text-dark mt-2 leading-tight">
            SERVER ADMIN
          </p>
        </div>
        <nav className="mt-4 flex-1 overflow-y-auto pb-4">
          {Object.entries(GROUPED_ITEMS).map(([category, items]) => (
            <div key={category} className="mb-4">
              <div className="px-4 py-2 text-[8px] font-minecraft text-minecraft-text-dark uppercase border-b border-[#5D4037] mb-2">
                {category}
              </div>
              {items.map(item => {
                const isActive = location.pathname === item.path;
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    onClick={() => setSidebarOpen(false)}
                    aria-current={isActive ? 'page' : undefined}
                    className={`flex items-center px-4 py-3 text-[10px] font-minecraft transition-all duration-150 ${
                      isActive
                        ? 'bg-gradient-to-r from-minecraft-grass to-minecraft-grass-light text-white border-r-4 border-minecraft-grass-light shadow-lg'
                        : 'text-minecraft-text-dark hover:bg-minecraft-dirt hover:text-white hover:pl-6'
                    }`}
                  >
                    <span className="mr-2 text-xs transition-transform duration-150 hover:scale-110" aria-hidden="true">
                      {item.icon}
                    </span>
                    {item.label.toUpperCase()}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>
        <div className="p-4 border-t-2 border-[#5D4037] bg-gradient-to-t from-[#5D4037] to-[#6D4C41]">
          {isAuthenticated && user && (
            <div className="mb-3 text-[8px] font-minecraft p-3 bg-minecraft-dirt rounded border border-[#5D4037]">
              <div className="text-minecraft-text-dark mb-1">LOGGED IN AS</div>
              <div className="text-[10px] text-minecraft-text-light font-bold">{user.username}</div>
              {user.role && (
                <div className="text-[8px] text-minecraft-grass-light mt-1 uppercase bg-[#558B2F] bg-opacity-20 px-2 py-1 inline-block rounded">
                  {user.role}
                </div>
              )}
            </div>
          )}
          {isAuthenticated && (
            <Button className="w-full" onClick={handleLogout}>
              LOGOUT
            </Button>
          )}
        </div>
      </aside>

      {/* Main Content */}
      <main className="lg:ml-64 p-4 lg:p-8 pt-16 lg:pt-8 max-w-7xl mx-auto">{children}</main>
    </div>
  );
};

export default Layout;
