import { lazy, Suspense } from 'react';
import { Navigate, Route, BrowserRouter as Router, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import { ToastProvider } from './components/ToastContainer';

// Lazy load components for code splitting
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Analytics = lazy(() => import('./pages/Analytics'));
const Logs = lazy(() => import('./pages/Logs'));
const Console = lazy(() => import('./pages/Console'));
const Players = lazy(() => import('./pages/Players'));
const Backups = lazy(() => import('./pages/Backups'));
const Worlds = lazy(() => import('./pages/Worlds'));
const Plugins = lazy(() => import('./pages/Plugins'));
const ConfigFiles = lazy(() => import('./pages/ConfigFiles'));
const FileBrowser = lazy(() => import('./pages/FileBrowser'));
const Settings = lazy(() => import('./pages/Settings'));
const ApiKeys = lazy(() => import('./pages/ApiKeys'));
const Users = lazy(() => import('./pages/Users'));
const AuditLogs = lazy(() => import('./pages/AuditLogs'));
const Scheduler = lazy(() => import('./pages/Scheduler'));
const DynamicDNS = lazy(() => import('./pages/DynamicDNS'));
const Login = lazy(() => import('./pages/Login'));
const Register = lazy(() => import('./pages/Register'));
const OAuthCallback = lazy(() => import('./pages/OAuthCallback'));

// Loading component for Suspense fallback
const PageLoading = () => (
  <div className="min-h-screen flex items-center justify-center bg-gray-900">
    <div className="text-minecraft-text-light font-minecraft text-sm">LOADING...</div>
  </div>
);

function App() {
  return (
    <ToastProvider>
      <Router>
        <Routes>
          {/* Public routes */}
          <Route
            path="/login"
            element={
              <Suspense fallback={<PageLoading />}>
                <Login />
              </Suspense>
            }
          />
          <Route
            path="/register"
            element={
              <Suspense fallback={<PageLoading />}>
                <Register />
              </Suspense>
            }
          />
          <Route
            path="/oauth/callback"
            element={
              <Suspense fallback={<PageLoading />}>
                <OAuthCallback />
              </Suspense>
            }
          />

          {/* Protected routes */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout>
                  <Suspense fallback={<PageLoading />}>
                    <Navigate to="/dashboard" replace />
                  </Suspense>
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Layout>
                  <Suspense fallback={<PageLoading />}>
                    <Dashboard />
                  </Suspense>
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/logs"
            element={
              <ProtectedRoute>
                <Layout>
                  <Suspense fallback={<PageLoading />}>
                    <Logs />
                  </Suspense>
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/console"
            element={
              <ProtectedRoute>
                <Layout>
                  <Suspense fallback={<PageLoading />}>
                    <Console />
                  </Suspense>
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/players"
            element={
              <ProtectedRoute>
                <Layout>
                  <Suspense fallback={<PageLoading />}>
                    <Players />
                  </Suspense>
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/backups"
            element={
              <ProtectedRoute>
                <Layout>
                  <Suspense fallback={<PageLoading />}>
                    <Backups />
                  </Suspense>
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/worlds"
            element={
              <ProtectedRoute>
                <Layout>
                  <Suspense fallback={<PageLoading />}>
                    <Worlds />
                  </Suspense>
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/plugins"
            element={
              <ProtectedRoute>
                <Layout>
                  <Suspense fallback={<PageLoading />}>
                    <Plugins />
                  </Suspense>
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/config"
            element={
              <ProtectedRoute>
                <Layout>
                  <Suspense fallback={<PageLoading />}>
                    <ConfigFiles />
                  </Suspense>
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/files"
            element={
              <ProtectedRoute>
                <Layout>
                  <Suspense fallback={<PageLoading />}>
                    <FileBrowser />
                  </Suspense>
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/settings"
            element={
              <ProtectedRoute>
                <Layout>
                  <Suspense fallback={<PageLoading />}>
                    <Settings />
                  </Suspense>
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/api-keys"
            element={
              <ProtectedRoute>
                <Layout>
                  <Suspense fallback={<PageLoading />}>
                    <ApiKeys />
                  </Suspense>
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/users"
            element={
              <ProtectedRoute>
                <Layout>
                  <Suspense fallback={<PageLoading />}>
                    <Users />
                  </Suspense>
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/audit"
            element={
              <ProtectedRoute>
                <Layout>
                  <Suspense fallback={<PageLoading />}>
                    <AuditLogs />
                  </Suspense>
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/scheduler"
            element={
              <ProtectedRoute>
                <Layout>
                  <Suspense fallback={<PageLoading />}>
                    <Scheduler />
                  </Suspense>
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/ddns"
            element={
              <ProtectedRoute>
                <Layout>
                  <Suspense fallback={<PageLoading />}>
                    <DynamicDNS />
                  </Suspense>
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/analytics"
            element={
              <ProtectedRoute>
                <Layout>
                  <Suspense fallback={<PageLoading />}>
                    <Analytics />
                  </Suspense>
                </Layout>
              </ProtectedRoute>
            }
          />
        </Routes>
      </Router>
    </ToastProvider>
  );
}

export default App;
