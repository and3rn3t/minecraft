import js from '@eslint/js';
import globals from 'globals';
import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';

export default [
  { ignores: ['dist', 'coverage'] },
  js.configs.recommended,
  react.configs.flat.recommended,
  react.configs.flat['jsx-runtime'],
  {
    // The react plugin's recommended rules apply to every file, whatever its
    // extension, and warn on each lint run when no React version is configured
    settings: { react: { version: 'detect' } },
  },
  {
    files: ['**/*.{js,jsx}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: globals.browser,
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
      'react/prop-types': 'off',
    },
  },
  {
    // Config files run in Node, not the browser
    files: ['**/*.config.{js,cjs}'],
    languageOptions: { globals: globals.node },
  },
  {
    // Build-time scripts run in Node
    files: ['scripts/**/*.mjs'],
    languageOptions: { globals: globals.node },
  },
  {
    // Playwright specs run in Node, and a fixture's `use` callback is not a
    // React hook.
    files: ['tests/e2e/**/*.js'],
    languageOptions: { globals: globals.node },
    rules: { 'react-hooks/rules-of-hooks': 'off' },
  },
  {
    // Context modules intentionally export a provider component next to its
    // hook; splitting them would churn every consumer for a dev-only
    // fast-refresh nicety.
    files: [
      'src/contexts/*.jsx',
      'src/components/ToastContainer.jsx',
      'src/components/LazyRoute.jsx',
    ],
    rules: { 'react-refresh/only-export-components': 'off' },
  },
];
