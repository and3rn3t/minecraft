import React from 'react';
import ReactDOM from 'react-dom/client';
// Self-hosted (latin subset only) so the pixel fonts don't cost a
// render-blocking third-party round trip to Google Fonts on first paint.
// Press Start 2P is the *display* face (headings, nav, buttons); VT323 is
// the body face (everywhere else) — Press Start 2P is a blocky display font
// and was unreadable at the 8-10px sizes most of the app renders it at.
import '@fontsource/press-start-2p/latin.css';
import '@fontsource/vt323/latin.css';
import App from './App.jsx';
import { AuthProvider } from './contexts/AuthContext';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </React.StrictMode>
);
