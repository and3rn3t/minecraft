# Web Admin Panel Guide

This guide covers the web-based admin panel for managing your Minecraft server.

## Overview

The web admin panel provides a modern, user-friendly interface for:

- Monitoring server status and metrics
- Viewing real-time logs
- Managing players
- Creating and managing backups
- Switching between worlds
- Managing plugins
- Configuring settings

## Quick Start

### Prerequisites

1. **API Server Running**:

   ```bash
   ./scripts/api-server.sh start
   ```

2. **API Key**:

   ```bash
   ./scripts/api-key-manager.sh create web-panel "Web interface"
   ```

3. **Node.js 18+** installed

### Installation

```bash
cd web
npm install
npm run dev
```

The web interface will be available at `http://localhost:3000`

### Configuration

1. **Set API Key**:
   - Open the web interface
   - Navigate to Settings
   - Enter your API key
   - Click "Save API Key"

2. **Environment Variables** (optional):
   Create `web/.env`:

   ```env
   VITE_API_URL=http://localhost:8080/api
   VITE_API_KEY=your-api-key-here
   ```

## Features

### Dashboard

The dashboard provides:

- **Server Status**: Online/offline indicator
- **Player Count**: Current players online
- **Uptime**: Server uptime information
- **Server Controls**: Start, stop, restart buttons
- **Metrics**: CPU and memory usage charts
- **Online Players**: List of currently online players

**Auto-refresh**: Updates every 5 seconds

### Log Viewer

Features:

- **Real-time Logs**: Streams server logs
- **Filtering**: Search/filter logs by text
- **Auto-scroll**: Automatically scrolls to latest logs
- **Color Coding**:
  - Red: Errors and warnings
  - Blue: Info messages
  - Gray: Normal logs

**Auto-refresh**: Updates every 2 seconds

### Player Management

View and manage players:

- **Online Players**: See who's currently online
- **Player Actions**: Kick players (coming soon)
- **Whitelist Management**: (coming soon)
- **Ban Management**: (coming soon)

### Backup Management

- **List Backups**: View all available backups
- **Create Backup**: One-click backup creation
- **Backup Info**: Size and creation date
- **Restore**: Restore from backup (coming soon)
- **Delete**: Remove old backups (coming soon)

### World Management

- **List Worlds**: View all available worlds
- **Switch Worlds**: Change active world (coming soon)
- **World Backup**: Backup specific world (coming soon)

### Plugin Management

- **List Plugins**: View installed plugins
- **Enable/Disable**: Toggle plugin status (coming soon)
- **Plugin Info**: View plugin details (coming soon)

### Settings

- **API Configuration**: Set API key
- **Preferences**: User preferences (coming soon)

## Development

### Project Structure

```
web/
├── src/
│   ├── components/      # Reusable UI components
│   │   ├── Layout.jsx
│   │   ├── StatusCard.jsx
│   │   └── MetricsChart.jsx
│   ├── pages/           # Page components
│   │   ├── Dashboard.jsx
│   │   ├── Logs.jsx
│   │   ├── Players.jsx
│   │   ├── Backups.jsx
│   │   ├── Worlds.jsx
│   │   ├── Plugins.jsx
│   │   └── Settings.jsx
│   ├── services/        # API integration
│   │   └── api.js
│   ├── App.jsx          # Main app component
│   └── main.jsx         # Entry point
├── public/              # Static assets
├── index.html           # HTML template
├── vite.config.js       # Vite configuration
└── package.json         # Dependencies
```

### Available Scripts

```bash
# Development
npm run dev          # Start dev server (http://localhost:3000)

# Production
npm run build        # Build for production
npm run preview      # Preview production build

# Code Quality
npm run lint         # Run ESLint
npm run format       # Format with Prettier
```

### Adding New Features

1. **Create Page Component**:

   ```jsx
   // src/pages/NewPage.jsx
   import { api } from '../services/api'

   const NewPage = () => {
     // Component logic
     return <div>New Page</div>
   }

   export default NewPage
   ```

2. **Add Route**:

   ```jsx
   // src/App.jsx
   import NewPage from './pages/NewPage'

   <Route path="/new-page" element={<NewPage />} />
   ```

3. **Add Navigation**:

   ```jsx
   // src/components/Layout.jsx
   { path: '/new-page', label: 'New Page', icon: '📄' }
   ```

## API Integration

The web panel uses the REST API. All API calls are handled through `src/services/api.js`:

```javascript
import { api } from '../services/api'

// Get server status
const status = await api.getStatus()

// Send command
await api.sendCommand('list')

// Create backup
await api.createBackup()
```

## Styling

The project uses **Tailwind CSS** for styling:

- **Colors**: Custom primary color scheme
- **Dark Theme**: Gray-800/900 background
- **Responsive**: Mobile-friendly design
- **Components**: Reusable styled components

## Building for Production

```bash
npm run build
```

Output will be in `web/dist/` directory.

### Deployment

1. **Build the project**:

   ```bash
   cd web
   npm run build
   ```

2. **Serve static files**:
   - Use nginx, Apache, or any static file server
   - Point to `web/dist/` directory
   - Configure proxy for `/api` to API server

3. **Nginx Example**:

   ```nginx
   server {
       listen 80;
       server_name minecraft-admin.local;

       root /path/to/web/dist;
       index index.html;

       location / {
           try_files $uri $uri/ /index.html;
       }

       location /api {
           proxy_pass http://localhost:8080;
       }
   }
   ```

## Troubleshooting

### API Connection Failed

**Problem**: Can't connect to API

**Solutions**:

1. Check API server is running: `./scripts/api-server.sh status`
2. Verify API URL in Settings or `.env`
3. Check API key is correct
4. Verify CORS is enabled in `config/api.conf`

### Build Errors

**Problem**: `npm run build` fails

**Solutions**:

1. Clear node_modules: `rm -rf node_modules && npm install`
2. Check Node.js version: `node --version` (needs 18+)
3. Check for syntax errors: `npm run lint`

### Page Not Loading

**Problem**: Blank page or errors

**Solutions**:

1. Check browser console for errors
2. Verify API key is set
3. Check API server is accessible
4. Clear browser cache

## Future Enhancements

- [ ] WebSocket support for real-time updates
- [ ] User authentication system
- [ ] Role-based access control
- [ ] File browser for server files
- [ ] Configuration file editor
- [ ] Performance graphs with historical data
- [ ] Mobile-responsive improvements
- [ ] Dark/light theme toggle

## Technologies

- **React 18** - UI framework
- **Vite** - Build tool
- **React Router** - Routing
- **Axios** - HTTP client
- **Tailwind CSS** - Styling
- **Recharts** - Charts

---

For API documentation, see [API.md](API.md)
