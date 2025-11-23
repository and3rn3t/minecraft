import * as matchers from '@testing-library/jest-dom/matchers';
import { cleanup } from '@testing-library/react';
import { afterAll, afterEach, beforeAll, expect, vi } from 'vitest';
import { server } from './mocks/server';
import { toHaveNoViolations } from './vitest-axe';

// Extend Vitest's expect with jest-dom matchers
expect.extend(matchers);
// Extend Vitest's expect with accessibility matchers
expect.extend({ toHaveNoViolations });

// Mock ResizeObserver (needed for Recharts)
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

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
