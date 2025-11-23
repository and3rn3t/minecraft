# Browser E2E Tests

Browser automation tests using Playwright for real browser testing.

## Setup

### Install Dependencies

```bash
cd web
npm install
npx playwright install
```

### Configuration

- **Config File**: `playwright.config.js`
- **Browsers**: Chromium, Firefox, WebKit
- **Base URL**: http://localhost:5173

## Running Tests

### All Browser Tests

```bash
cd web
npx playwright test
```

### Specific Test File

```bash
npx playwright test tests/e2e/browser/analytics.spec.js
```

### With UI

```bash
npx playwright test --ui
```

### Visual Regression

```bash
npx playwright test tests/e2e/browser/visual-regression.spec.js
```

### Update Snapshots

```bash
npx playwright test --update-snapshots
```

## Test Files

### analytics.spec.js

Tests for Analytics page:

- Page loading
- Tab navigation
- Time period selection
- Data collection
- Report generation

### user-journey.spec.js

Complete user journey tests:

- Registration → Login → Dashboard
- Navigation through all pages
- Server management

### visual-regression.spec.js

Visual regression tests:

- Dashboard snapshot
- Analytics page snapshot
- Backups page snapshot
- Players page snapshot
- Worlds page snapshot
- Login page snapshot

## Writing Tests

### Basic Test Structure

```javascript
import { test, expect } from '@playwright/test';

test('test description', async ({ page }) => {
  await page.goto('/path');
  await expect(page.getByText('Expected')).toBeVisible();
});
```

### Mocking API

```javascript
await page.route('**/api/endpoint', async route => {
  await route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ data: 'value' }),
  });
});
```

### Visual Snapshots

```javascript
await expect(page).toHaveScreenshot('filename.png', {
  fullPage: true,
  maxDiffPixels: 100,
});
```

## CI/CD

Browser tests run in CI/CD:

- On pull requests
- On pushes to main
- Screenshots on failure
- HTML reports generated

## See Also

- [Playwright Documentation](https://playwright.dev/)
- [Testing Guide](../../README.md)
