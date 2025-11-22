import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Logs from './pages/Logs'
import Players from './pages/Players'
import Settings from './pages/Settings'
import Backups from './pages/Backups'
import Worlds from './pages/Worlds'
import Plugins from './pages/Plugins'

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/logs" element={<Logs />} />
          <Route path="/players" element={<Players />} />
          <Route path="/backups" element={<Backups />} />
          <Route path="/worlds" element={<Worlds />} />
          <Route path="/plugins" element={<Plugins />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App

