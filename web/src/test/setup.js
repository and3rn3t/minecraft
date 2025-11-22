import { expect, afterEach, beforeAll, afterAll, vi } from 'vitest'
import { cleanup } from '@testing-library/react'
import * as matchers from '@testing-library/jest-dom/matchers'
import { server } from './mocks/server'

// Extend Vitest's expect with jest-dom matchers
expect.extend(matchers)

// Mock ResizeObserver (needed for Recharts)
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock scrollIntoView (needed for Logs component)
Element.prototype.scrollIntoView = vi.fn()

// Setup MSW server
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))

// Cleanup after each test
afterEach(() => {
  cleanup()
  server.resetHandlers()
  vi.clearAllMocks()
})

// Cleanup after all tests
afterAll(() => server.close())
