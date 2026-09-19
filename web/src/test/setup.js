// Vitest setup file - should only be loaded by Vitest
// This file is specified in vitest.config.js setupFiles

import * as matchers from '@testing-library/jest-dom/matchers';
import { cleanup } from '@testing-library/react';
import { afterAll, afterEach, beforeAll, expect, vi } from 'vitest';
import { server } from './mocks/server';
import { toHaveNoViolations } from './vitest-axe';

// Guard against multiple loads (prevents "Cannot redefine property" error)
if (globalThis.__VITEST_SETUP_LOADED__) {
  // Already loaded, skip
} else {
  // Extend Vitest's expect with jest-dom matchers
  expect.extend(matchers);
  // Extend Vitest's expect with accessibility matchers
  expect.extend({ toHaveNoViolations });

  // Mock ResizeObserver (needed for Recharts). A plain class rather than
  // vi.fn().mockImplementation(): Recharts calls `new ResizeObserver(...)`,
  // and whether a mock function is constructible is a vitest implementation
  // detail that changed in v5.
  globalThis.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };

  // Mock scrollIntoView (needed for Logs component)
  Element.prototype.scrollIntoView = vi.fn();

  // Setup MSW server
  beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));

  // Cleanup after each test
  afterEach(() => {
    cleanup();
    server.resetHandlers();
    vi.clearAllMocks();
  });

  // Cleanup after all tests
  afterAll(() => server.close());

  globalThis.__VITEST_SETUP_LOADED__ = true;
}
