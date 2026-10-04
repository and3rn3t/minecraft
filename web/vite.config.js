import react from '@vitejs/plugin-react';
import path from 'path';
import { fileURLToPath } from 'url';
import { defineConfig } from 'vite';

// ES module equivalent of __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Rolldown groups modules by path, not by package name, so each vendor chunk lists
// the packages that belong to it, including the ones those packages pull in. If a
// package is missing here its code lands in the main chunk, which is only a caching
// loss, not a build failure.
const REACT_VENDOR_PACKAGES = [
  'react',
  'react-dom',
  'scheduler', // react-dom's scheduler
  'react-router', // react-router-dom's core
  'react-router-dom',
];
const SOCKET_VENDOR_PACKAGES = [
  'socket.io-client',
  'socket.io-parser',
  'engine.io-client',
  'engine.io-parser',
  '@socket.io/component-emitter',
];

// Matches a file inside node_modules/<package>/ on both POSIX and Windows paths
const SEP = '[\\\\/]';
const escapeRegExp = text => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const vendorPattern = packages =>
  new RegExp(
    `node_modules${SEP}(${packages.map(name => escapeRegExp(name).replaceAll('/', SEP)).join('|')})${SEP}`
  );

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
      // Socket.IO's default handshake path (see api/server.py's SocketIO(...)
      // call, which doesn't override it). The client connects to its own
      // origin, so this is the path that needs proxying in dev too.
      '/socket.io': {
        target: 'ws://localhost:8080',
        ws: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
    rolldownOptions: {
      output: {
        // Separate vendor chunks for better caching
        codeSplitting: {
          groups: [
            { name: 'react-vendor', test: vendorPattern(REACT_VENDOR_PACKAGES) },
            { name: 'socket-vendor', test: vendorPattern(SOCKET_VENDOR_PACKAGES) },
          ],
        },
      },
    },
    // Left at Vite's default (500kb): recharts (381KB) used to trip this and
    // the limit was raised to silence it rather than fix it. Now that it's
    // gone, keep the default so a future regression actually warns.
  },
});
