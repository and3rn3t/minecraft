import { lazy, Suspense } from 'react';

/**
 * Wrapper component for lazy-loaded routes with Suspense
 * Provides consistent loading state for all lazy routes
 */
const PageLoading = () => (
  <div className="min-h-screen flex items-center justify-center bg-gray-900">
    <div className="text-minecraft-text-light font-minecraft text-sm">LOADING...</div>
  </div>
);

export function createLazyRoute(importFn) {
  const LazyComponent = lazy(importFn);
  return props => (
    <Suspense fallback={<PageLoading />}>
      <LazyComponent {...props} />
    </Suspense>
  );
}

export default PageLoading;
