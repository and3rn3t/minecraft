module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  extends: [
    'eslint:recommended',
    'plugin:react/recommended',
    'plugin:react/jsx-runtime',
    'plugin:react-hooks/recommended',
  ],
  ignorePatterns: ['dist', 'coverage', '.eslintrc.cjs'],
  parserOptions: { ecmaVersion: 'latest', sourceType: 'module' },
  settings: { react: { version: '18.2' } },
  plugins: ['react-refresh'],
  rules: {
    'react-refresh/only-export-components': [
      'warn',
      { allowConstantExport: true },
    ],
    'react/prop-types': 'off',
  },
  overrides: [
    {
      // Config files run in Node, not the browser
      files: ['*.config.js', '*.config.cjs', 'playwright.config.js'],
      env: { node: true, browser: false },
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
  ],
}
