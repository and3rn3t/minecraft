# Web UI Testing Guide

This document outlines the web UI testing strategy and coverage for the Minecraft Server Management web interface.

## Test Structure

```
web/src/
├── pages/
│   └── __tests__/
│       ├── Analytics.test.jsx          # Analytics component tests
│       ├── Dashboard.test.jsx          # Dashboard tests
│       ├── Login.test.jsx               # Login tests
│       └── ...
├── components/
│   └── __tests__/
│       ├── StatusCard.test.jsx         # Component tests
│       └── ...
└── test/
    ├── integration/
    │   ├── analytics.integration.test.jsx  # Analytics integration tests
    │   └── ...
    ├── mocks/
    │   ├── handlers.js                 # MSW mock handlers
    │   └── server.js                   # MSW server setup
    └── utils.jsx                       # Test utilities
```

## Testing Framework

- **Vitest**: Test runner and framework
- **React Testing Library**: Component testing
- **MSW (Mock Service Worker)**: API mocking
- **@testing-library/user-event**: User interaction simulation

## Running Tests

### All Tests

```bash
cd web
npm test
```

### Watch Mode

```bash
npm test -- --watch
```

### Coverage

```bash
npm run test:coverage
```

### UI Mode

```bash
npm run test:ui
```

### Specific Test File

```bash
npm test Analytics.test.jsx
```

## Test Types

### 1. Component Tests

Test individual React components in isolation.

**Example**: `Analytics.test.jsx`

- Component rendering
- User interactions
- State management
- Error handling
- Loading states

### 2. Integration Tests

Test component interactions and workflows.

**Example**: `analytics.integration.test.jsx`

- Complete user workflows
- Multi-step interactions
- Data flow between components
- API integration

### 3. E2E Tests (API Simulation)

Test complete workflows via API calls (simulating UI interactions).

**Example**: `test-web-ui-workflow.sh`

- User registration → Login → Dashboard
- Analytics workflow
- Backup management
- Error handling

## Analytics Component Tests

### Coverage

✅ **Completed Tests**:

- Component rendering
- Tab navigation
- Time period selection
- Data collection
- Report generation
- Warnings and recommendations display
- Anomaly detection display
- Predictions display
- Error handling
- Periodic updates

### Test Cases

1. **Rendering Tests**

   - Dashboard title
   - Loading states
   - Default tab (overview)

2. **Navigation Tests**

   - Tab switching (overview, performance, players, anomalies, predictions)
   - Tab content display

3. **Data Display Tests**

   - Performance metrics
   - Player behavior
   - Anomalies
   - Predictions

4. **Interaction Tests**

   - Time period selection
   - Data collection button
   - Report generation button

5. **Error Handling Tests**
   - API errors
   - Missing data
   - Network failures

## E2E Workflow Tests

### Complete User Journey

**File**: `tests/e2e/test-complete-user-journey.sh`

Tests complete workflows:

1. User Registration
2. User Login
3. Dashboard Access
4. Analytics Data Collection
5. Analytics Report Generation
6. Player Behavior Analysis

### Web UI Workflow

**File**: `tests/e2e/test-web-ui-workflow.sh`

Tests UI workflows via API simulation:

1. Login page access
2. Registration workflow
3. Dashboard data loading
4. Analytics navigation
5. Backup management
6. Player management
7. Error handling
8. Session management

## Mock Data

### MSW Handlers

Mock API responses for testing:

```javascript
// web/src/test/mocks/handlers.js
- Health check
- Server status
- Server control
- Players
- Metrics
- Logs
- Backups
- Worlds
- Plugins
- Analytics endpoints (NEW)
```

### Mock Analytics Data

```javascript
{
  report: {
    generated_at: '2024-01-27T12:00:00',
    period_hours: 24,
    player_behavior: {...},
    performance: {...},
    summary: {...}
  }
}
```

## Test Utilities

### renderWithRouter

Custom render function that includes:

- BrowserRouter
- AuthProvider (optional)
- Route setup

```javascript
import { renderWithRouter } from '../../test/utils';

renderWithRouter(<Analytics />, { route: '/analytics' });
```

### Mock API Responses

```javascript
import * as api from '../../services/api';

vi.mock('../../services/api', () => ({
  api: {
    getAnalyticsReport: vi.fn(),
    // ...
  },
}));
```

## Best Practices

### 1. Test User Behavior

Test what users see and do, not implementation details:

```javascript
// Good
expect(screen.getByText('Analytics Dashboard')).toBeInTheDocument();

// Avoid
expect(component.state.loading).toBe(false);
```

### 2. Use waitFor for Async Operations

```javascript
await waitFor(() => {
  expect(screen.getByText('Summary')).toBeInTheDocument();
});
```

### 3. Mock External Dependencies

```javascript
vi.mock('../../services/api');
```

### 4. Clean Up After Tests

```javascript
afterEach(() => {
  vi.clearAllMocks();
});
```

### 5. Test Error States

```javascript
api.api.getAnalyticsReport.mockRejectedValue(new Error('API Error'));
```

## Coverage Goals

### Current Status

- **Component Tests**: ~40% coverage
- **Integration Tests**: ~30% coverage
- **E2E Tests**: ~25% coverage

### Target Goals

- **Component Tests**: 70%+ coverage
- **Integration Tests**: 60%+ coverage
- **E2E Tests**: 50%+ coverage

## Running Specific Test Suites

### Analytics Tests Only

```bash
npm test Analytics
```

### Integration Tests Only

```bash
npm test integration
```

### E2E Tests (Bash)

```bash
bats tests/e2e/test-complete-user-journey.sh
bats tests/e2e/test-web-ui-workflow.sh
```

## Debugging Tests

### Debug Mode

```bash
npm test -- --inspect-brk
```

### Verbose Output

```bash
npm test -- --reporter=verbose
```

### Run Single Test

```bash
npm test -- -t "renders analytics dashboard"
```

## CI/CD Integration

Tests run automatically on:

- Pull requests
- Pushes to main branch
- Manual workflow dispatch

See `.github/workflows/tests.yml` for configuration.

## Future Improvements

### High Priority

1. ✅ Analytics component tests - DONE
2. ✅ Analytics integration tests - DONE
3. ⚠️ More component tests (Backups, Players, Worlds)
4. ⚠️ Visual regression tests
5. ⚠️ Accessibility tests

### Medium Priority

6. Browser automation tests (Playwright/Cypress)
7. Performance tests
8. Cross-browser tests

### Low Priority

9. Visual snapshot tests
10. Mobile responsive tests

## See Also

- [Testing Guide](../tests/README.md)
- [Analytics Documentation](ANALYTICS.md)
- [API Documentation](API.md)
