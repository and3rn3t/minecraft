import { Navigate, Route, BrowserRouter as Router, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import ApiKeys from './pages/ApiKeys';
import AuditLogs from './pages/AuditLogs';
import Backups from './pages/Backups';
import ConfigFiles from './pages/ConfigFiles';
import Console from './pages/Console';
import Dashboard from './pages/Dashboard';
import DynamicDNS from './pages/DynamicDNS';
import FileBrowser from './pages/FileBrowser';
import Login from './pages/Login';
import Logs from './pages/Logs';
import OAuthCallback from './pages/OAuthCallback';
import Players from './pages/Players';
import Plugins from './pages/Plugins';
import Register from './pages/Register';
import Scheduler from './pages/Scheduler';
import Settings from './pages/Settings';
import Users from './pages/Users';
import Worlds from './pages/Worlds';

function App() {
  return (
    <Router>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/oauth/callback" element={<OAuthCallback />} />

        {/* Protected routes */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout>
                <Navigate to="/dashboard" replace />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Layout>
                <Dashboard />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/logs"
          element={
            <ProtectedRoute>
              <Layout>
                <Logs />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/console"
          element={
            <ProtectedRoute>
              <Layout>
                <Console />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/players"
          element={
            <ProtectedRoute>
              <Layout>
                <Players />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/backups"
          element={
            <ProtectedRoute>
              <Layout>
                <Backups />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/worlds"
          element={
            <ProtectedRoute>
              <Layout>
                <Worlds />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/plugins"
          element={
            <ProtectedRoute>
              <Layout>
                <Plugins />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/config"
          element={
            <ProtectedRoute>
              <Layout>
                <ConfigFiles />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/files"
          element={
            <ProtectedRoute>
              <Layout>
                <FileBrowser />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/settings"
          element={
            <ProtectedRoute>
              <Layout>
                <Settings />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/api-keys"
          element={
            <ProtectedRoute>
              <Layout>
                <ApiKeys />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/users"
          element={
            <ProtectedRoute>
              <Layout>
                <Users />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/audit"
          element={
            <ProtectedRoute>
              <Layout>
                <AuditLogs />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/scheduler"
          element={
            <ProtectedRoute>
              <Layout>
                <Scheduler />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/ddns"
          element={
            <ProtectedRoute>
              <Layout>
                <DynamicDNS />
              </Layout>
            </ProtectedRoute>
          }
        />
      </Routes>
    </Router>
  );
}

export default App;
