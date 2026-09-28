import react from '@vitejs/plugin-react';
import path from 'path';
import { fileURLToPath } from 'url';
import { defineConfig } from 'vitest/config';

// ES module equivalent of __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    pool: 'vmThreads',
    setupFiles: ['./src/test/vm-globals.js', './src/test/setup.js'],
    testMatch: ['**/__tests__/**/*.test.{js,jsx}', '**/test/**/*.test.{js,jsx}'],
    // Exclude Playwright E2E tests
    exclude: ['**/node_modules/**', '**/dist/**', '**/tests/e2e/**', '**/*.spec.js'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'json-summary'],
      // Without include, only files some test imports are reported, so code
      // with no tests at all is invisible rather than counted as 0%.
      include: ['src/**/*.{js,jsx}'],
      exclude: [
        'node_modules/',
        'src/test/**',
        '**/*.config.js',
        '**/main.jsx',
        '**/*.test.{js,jsx}',
      ],
      // A ratchet, a point or two under the measured totals (65.5 / 62 / 62.9 /
      // 67.2 in September 2026), mirroring fail_under for the API. Raise these
      // as coverage grows; never lower them to make a change pass.
      thresholds: {
        statements: 64,
        branches: 60,
        functions: 61,
        lines: 66,
      },
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
