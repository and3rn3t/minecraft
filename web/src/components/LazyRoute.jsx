import { Suspense } from 'react';
import Layout from './Layout';
import ProtectedRoute from './ProtectedRoute';

const PageLoading = () => (
  <div className="min-h-screen flex items-center justify-center bg-minecraft-background">
    <div className="text-minecraft-text-light font-minecraft text-sm">LOADING...</div>
  </div>
);

/**
 * Wraps a lazy-loaded page in Suspense, and, by default, in the same
 * ProtectedRoute + Layout every authenticated route needs -- so App.jsx's
 * route list doesn't repeat that three-level wrapper per page.
 */
const LazyRoute = ({ component: Component, protectedRoute = true }) => {
  const content = (
    <Suspense fallback={<PageLoading />}>
      <Component />
    </Suspense>
  );

  if (!protectedRoute) {
    return content;
  }

  return (
    <ProtectedRoute>
      <Layout>{content}</Layout>
    </ProtectedRoute>
  );
};

export default LazyRoute;
