import { lazy } from 'react';
import { Navigate, Route, BrowserRouter as Router, Routes } from 'react-router-dom';
import LazyRoute from './components/LazyRoute';
import { ToastProvider } from './components/ToastContainer';

// Lazy load components for code splitting
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Analytics = lazy(() => import('./pages/Analytics'));
const Logs = lazy(() => import('./pages/Logs'));
const Console = lazy(() => import('./pages/Console'));
const Players = lazy(() => import('./pages/Players'));
const Backups = lazy(() => import('./pages/Backups'));
const Worlds = lazy(() => import('./pages/Worlds'));
const HallOfDeaths = lazy(() => import('./pages/HallOfDeaths'));
const Bedtime = lazy(() => import('./pages/Bedtime'));
const Oracle = lazy(() => import('./pages/Oracle'));
const Plugins = lazy(() => import('./pages/Plugins'));
const Datapacks = lazy(() => import('./pages/Datapacks'));
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
const NotFound = lazy(() => import('./pages/NotFound'));

const RedirectToDashboard = () => <Navigate to="/dashboard" replace />;

// Every protected page here, path -> component. Auth + layout + the
// Suspense fallback are LazyRoute's job, not repeated per route.
const PROTECTED_ROUTES = [
  ['/dashboard', Dashboard],
  ['/logs', Logs],
  ['/console', Console],
  ['/players', Players],
  ['/backups', Backups],
  ['/bedtime', Bedtime],
  ['/oracle', Oracle],
  ['/deaths', HallOfDeaths],
  ['/worlds', Worlds],
  ['/plugins', Plugins],
  ['/datapacks', Datapacks],
  ['/config', ConfigFiles],
  ['/files', FileBrowser],
  ['/settings', Settings],
  ['/api-keys', ApiKeys],
  ['/users', Users],
  ['/audit', AuditLogs],
  ['/scheduler', Scheduler],
  ['/ddns', DynamicDNS],
  ['/analytics', Analytics],
];

function App() {
  return (
    <ToastProvider>
      <Router>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LazyRoute component={Login} protectedRoute={false} />} />
          <Route path="/register" element={<LazyRoute component={Register} protectedRoute={false} />} />
          <Route path="/oauth/callback" element={<LazyRoute component={OAuthCallback} protectedRoute={false} />} />

          {/* Protected routes */}
          <Route path="/" element={<LazyRoute component={RedirectToDashboard} />} />
          {PROTECTED_ROUTES.map(([path, Component]) => (
            <Route key={path} path={path} element={<LazyRoute component={Component} />} />
          ))}

          {/* Catch-all for unknown URLs */}
          <Route path="*" element={<LazyRoute component={NotFound} protectedRoute={false} />} />
        </Routes>
      </Router>
    </ToastProvider>
  );
}

export default App;
