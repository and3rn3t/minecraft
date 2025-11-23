import { defineConfig, devices } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

/**
 * Playwright configuration for end-to-end tests
 * Tests are located in tests/e2e/browser/
 */

// ES module equivalent of __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default defineConfig({
  // Test directory - point to the actual test location (relative to web/)
  testDir: path.join(__dirname, '../tests/e2e/browser'),

  // Test match pattern - only match .spec.js files
  testMatch: /.*\.spec\.js/,

  // Exclude Vitest files and source files from Playwright
  testIgnore: [
    '**/node_modules/**',
    '**/src/**',
    '**/vitest.config.js',
    '**/src/test/**',
    '**/*.test.jsx',
    '**/*.test.js',
    '**/web/src/**',
  ],

  // Resolve modules from web/node_modules
  resolve: {
    modules: [path.join(__dirname, 'node_modules')],
  },

  // Maximum time one test can run for
  timeout: 30 * 1000,

  // Test execution
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,

  // Reporter configuration
  reporter: [['html', { outputFolder: 'playwright-report' }], ['list']],

  // Shared settings for all projects
  use: {
    // Base URL for tests
    baseURL: 'http://localhost:5173',

    // Collect trace when retrying the failed test
    trace: 'on-first-retry',

    // Screenshot on failure
    screenshot: 'only-on-failure',
  },

  // Configure projects for major browsers
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],

  // Run your local dev server before starting the tests
  // In CI, use production build for faster and more reliable startup
  webServer: process.env.CI
    ? {
        command: 'npm run build && npx vite preview --port 5173 --host 0.0.0.0',
        url: 'http://localhost:5173',
        reuseExistingServer: false,
        timeout: 300 * 1000, // 5 minutes for build + serve
        stdout: 'pipe',
        stderr: 'pipe',
      }
    : {
        command: 'npm run dev -- --port 5173',
        url: 'http://localhost:5173',
        reuseExistingServer: true,
        timeout: 120 * 1000,
      },
});
