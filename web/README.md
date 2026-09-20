# Minecraft Server Web Admin Panel

Modern web-based admin panel for managing your Minecraft server.

## Features

- 📊 **Dashboard** - Real-time server status and metrics
- 📝 **Log Viewer** - Real-time log streaming with filtering
- 👥 **Player Management** - View and manage online players
- 💾 **Backup Management** - Create and manage backups
- 🌍 **World Management** - Switch and manage multiple worlds
- 🔌 **Plugin Management** - View and manage plugins
- ⚙️ **Settings** - Configure API keys and preferences

## Quick Start

### Prerequisites

- Node.js 18+ and npm
- Running API server (see `../api/`)

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The web interface will be available at `http://localhost:3000`

### Configuration

1. **Set API Key**:
   - Go to Settings page
   - Enter your API key (get it from `./scripts/api-key-manager.sh create`)
   - Or set `VITE_API_KEY` in `.env`

2. **Configure API URL** (if different from default):
   - Create `.env` file:

     ```env
     VITE_API_URL=http://localhost:8080/api
     VITE_API_KEY=your-api-key-here
     ```

## Testing

### Run Tests

```bash
# Run all tests
npm test

# Run with UI
npm run test:ui

# Run with coverage
npm run test:coverage
```

### Test Structure

- **Unit Tests**: `src/components/__tests__/`, `src/pages/__tests__/`
- **Integration Tests**: `src/test/integration/`
- **API Tests**: `src/services/__tests__/`

### Test Coverage

Current coverage includes:

- ✅ Component rendering and props
- ✅ Page components with API integration
- ✅ API service methods
- ✅ User interactions
- ✅ Integration flows

## Development

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm test` - Run tests
- `npm run test:ui` - Run tests with UI
- `npm run test:coverage` - Run tests with coverage
- `npm run lint` - Run ESLint
- `npm run format` - Format code with Prettier

### Project Structure

```text
web/
├── src/
│   ├── components/     # Reusable components
│   ├── pages/          # Page components
│   ├── services/       # API service layer
│   ├── test/          # Test utilities and mocks
│   ├── App.jsx         # Main app component
│   └── main.jsx        # Entry point
├── public/             # Static assets
├── index.html          # HTML template
└── vite.config.js      # Vite configuration
```

## Building for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

## Integration with API

The web panel connects to the REST API server. Make sure:

1. API server is running (`./scripts/api-server.sh start`)
2. API key is configured (Settings page or environment variable)
3. CORS is enabled in API config (`config/api.conf`)

## Technologies

- **React 18** - UI framework
- **Vite** - Build tool and dev server
- **React Router** - Routing
- **Axios** - HTTP client
- **Tailwind CSS** - Styling
- **Recharts** - Charts and graphs
- **Vitest** - Testing framework
- **Testing Library** - Component testing
- **MSW** - API mocking

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

## License

Same as main project.
