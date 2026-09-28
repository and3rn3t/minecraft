# Web UI Testing Guide

This document outlines the web UI testing strategy and coverage for the Minecraft Server Management web interface.

## Test Structure

```text
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

Every source JavaScript/JSX file under `src/` counts, including ones no test imports
(they show as 0%); test files, `src/test/` and `main.jsx` are excluded. The thresholds
in `vitest.config.js` are a ratchet a point or two under the measured totals, and CI
and `make test` fail below them: raise them as coverage grows.

### How the runner is set up

- `pool: 'vmThreads'` builds jsdom once per worker instead of once per file, which
  halves the run time. `src/test/vm-globals.js` loads first to supply the web
  streams jsdom lacks and MSW needs.
- `@testing-library/react`, `@testing-library/user-event` and
  `@testing-library/dom` must resolve to **one** copy of `@testing-library/dom`
  (`npm ls @testing-library/dom`). With two, user-event's interactions are not
  wrapped in `act()`, which produced hundreds of warnings.

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

### 3. E2E Tests (Playwright)

Browser tests in `web/tests/e2e/` drive the built app with the API mocked via
`page.route`. See [E2E Workflow Tests](#e2e-workflow-tests).

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

End-to-end user journeys are covered by the Playwright specs in `web/tests/e2e/`
(`user-journey.spec.js`, `analytics.spec.js`). The BATS versions that used to live in
`tests/e2e/` were removed: every test in them was skipped unconditionally, so they
never ran. Their scenarios are listed as a backlog in [tests/README.md](../tests/README.md).

### How the browser tests run

- They drive the production build in Chromium with the API mocked in the page by
  `tests/e2e/mock-api.js`, so no backend is needed. `mockApi(page, { user })`
  answers the endpoints the pages call; `user: null` starts signed out, and a
  register or login call signs in. Pass `routes` to change single endpoints.
- Wait for the request itself (`page.waitForRequest`) rather than setting a flag
  in a route handler and asserting it after a click: the flag is checked before the
  request is made.
- Firefox and WebKit are opt-in: `PW_ALL_BROWSERS=1 npm run test:playwright`.
- CI runs them on every pull request, in the official Playwright image.

### Screenshot tests

`visual-regression.spec.js` compares full-page screenshots with baselines in
`visual-regression.spec.js-snapshots/`. Fonts and antialiasing differ between
machines, so the baselines are rendered in the Playwright image and the tests only
run there (`PW_VISUAL=1`); `npm run test:playwright` on a Mac skips them.

```bash
make test-visual          # everything, in the container, as CI runs it
make test-visual-update   # after an intended UI change: re-render what changed
```

Look at the re-rendered PNGs before committing them: a baseline is only as right as
the page it captured. The tolerance is 20 pixels, because renders in the same image
are identical; a looser one let a changed number pass.

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

### settle

`AuthProvider`, and most pages, start a request on mount. A test that asserts
straight after rendering and returns leaves that request to update state after
the test, outside `act()`, which prints a warning against whatever runs next.
End such a test with `await settle()`, which lets pending promises resolve
inside `act()`; a test that already awaits the page's loaded state (`findBy*`,
`waitFor`) doesn't need it.

```javascript
import { renderWithRouter, settle } from '../../test/utils';

it('has link to login page', async () => {
  renderWithRouter(<Register />);
  expect(screen.getByText(/login here/i)).toHaveAttribute('href', '/login');
  await settle();
});
```

With fake timers, advance them inside `act()` too:
`await act(() => vi.advanceTimersByTimeAsync(5000))`.

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

The enforced minimums are the `coverage.thresholds` in `vitest.config.js`. For
current figures run `npm run test:coverage` (the summary table, plus an HTML report
in `web/coverage/`), or download the `web-coverage` artifact from a CI run. The
per-file table shows where coverage is thinnest; raise the thresholds as those
areas are covered.

## Running Specific Test Suites

### Analytics Tests Only

```bash
npm test Analytics
```

### Integration Tests Only

```bash
npm test integration
```

### E2E Tests (Playwright)

```bash
npm run test:playwright
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
