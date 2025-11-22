import { Link, useLocation } from 'react-router-dom'

const Layout = ({ children }) => {
  const location = useLocation()

  const navItems = [
    { path: '/dashboard', label: 'Dashboard', icon: '📊' },
    { path: '/logs', label: 'Logs', icon: '📝' },
    { path: '/players', label: 'Players', icon: '👥' },
    { path: '/backups', label: 'Backups', icon: '💾' },
    { path: '/worlds', label: 'Worlds', icon: '🌍' },
    { path: '/plugins', label: 'Plugins', icon: '🔌' },
    { path: '/settings', label: 'Settings', icon: '⚙️' },
  ]

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Sidebar */}
      <aside className="fixed left-0 top-0 h-full w-64 bg-gray-800 border-r border-gray-700">
        <div className="p-6">
          <h1 className="text-2xl font-bold text-primary-400">Minecraft Admin</h1>
          <p className="text-sm text-gray-400 mt-1">Server Management</p>
        </div>
        <nav className="mt-8">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path
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
            )
          })}
        </nav>
      </aside>

      {/* Main Content */}
      <main className="ml-64 p-8">
        {children}
      </main>
    </div>
  )
}

export default Layout

