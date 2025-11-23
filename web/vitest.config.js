import react from '@vitejs/plugin-react';
import path from 'path';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.js'],
    testMatch: ['**/__tests__/**/*.test.{js,jsx}', '**/test/**/*.test.{js,jsx}'],
    // Exclude Playwright E2E tests
    exclude: ['**/node_modules/**', '**/dist/**', '**/tests/e2e/**', '**/*.spec.js'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.config.js',
        '**/main.jsx',
        '**/*.test.{js,jsx}',
      ],
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
