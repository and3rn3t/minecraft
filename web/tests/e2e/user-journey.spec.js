import { expect, test } from '@playwright/test';

test.describe('Complete User Journey', () => {
  test('user can register, login, and access dashboard', async ({ page }) => {
    const testUser = `testuser_${Date.now()}`;
    const testPassword = 'TestPassword123!';

    // Step 1: Register
    await page.goto('/register');
    await page.fill('input[name="username"]', testUser);
    await page.fill('input[name="password"]', testPassword);
    await page.fill('input[name="confirmPassword"]', testPassword);
    await page.click('button:has-text("Register")');

    // Step 2: Login
    await page.goto('/login');
    await page.fill('input[name="username"]', testUser);
    await page.fill('input[name="password"]', testPassword);
    await page.click('button:has-text("Login")');

    // Step 3: Access Dashboard
    await page.waitForURL('/dashboard');
    await expect(page.getByText('Dashboard')).toBeVisible();
  });

  test('user can navigate through all main pages', async ({ page }) => {
    // Mock authentication
    await page.evaluate(() => {
      localStorage.setItem('api_key', 'test-api-key');
    });

    // Mock API responses
    await page.route('**/api/**', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({}),
      });
    });

    await page.goto('/dashboard');
    await expect(page.getByText('Dashboard')).toBeVisible();

    // Navigate to Analytics
    await page.click('a:has-text("Analytics")');
    await expect(page.getByText('Analytics Dashboard')).toBeVisible();

    // Navigate to Players
    await page.click('a:has-text("Players")');
    await expect(page.getByText('Player Management')).toBeVisible();

    // Navigate to Backups
    await page.click('a:has-text("Backups")');
    await expect(page.getByText(/backup/i)).toBeVisible();

    // Navigate to Worlds
    await page.click('a:has-text("Worlds")');
    await expect(page.getByText('World Management')).toBeVisible();
  });

  test('user can manage server from dashboard', async ({ page }) => {
    await page.evaluate(() => {
      localStorage.setItem('api_key', 'test-api-key');
    });

    let startCalled = false;
    await page.route('**/api/server/start', async route => {
      startCalled = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true }),
      });
    });

    await page.route('**/api/status', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ running: false, status: 'Stopped' }),
      });
    });

    await page.goto('/dashboard');
    await page.click('button:has-text("Start Server")');
    await expect(startCalled).toBeTruthy();
  });
});
