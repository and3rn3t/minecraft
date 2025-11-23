import { expect, test } from '@playwright/test';

test.describe('Complete User Journey', () => {
  test('user can register, login, and access dashboard', async ({ page }) => {
    const testUser = `testuser_${Date.now()}`;
    const testPassword = 'TestPassword123!';

    // Mock API responses
    await page.route('**/api/**', async route => {
      const url = route.request().url();
      if (url.includes('/register')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, token: 'test-token' }),
        });
      } else if (url.includes('/login')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, token: 'test-token' }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({}),
        });
      }
    });

    // Step 1: Register
    await page.goto('/register');
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('#username', { state: 'visible' });
    await page.fill('#username', testUser);
    await page.fill('#password', testPassword);
    await page.fill('#confirmPassword', testPassword);
    await page.click('button:has-text("REGISTER"), button:has-text("Register")');

    // Wait for navigation after registration
    await page.waitForURL('/dashboard', { timeout: 10000 }).catch(() => {
      // If registration doesn't auto-navigate, go to login
    });

    // Step 2: Login (if not already logged in)
    if (page.url().includes('/login') || !page.url().includes('/dashboard')) {
      await page.goto('/login');
      await page.waitForLoadState('networkidle');
      await page.waitForSelector('#username', { state: 'visible' });
      await page.fill('#username', testUser);
      await page.fill('#password', testPassword);
      await page.click('button:has-text("LOGIN"), button:has-text("Login")');
    }

    // Step 3: Access Dashboard
    await page.waitForURL('/dashboard', { timeout: 10000 });
    await page.waitForLoadState('networkidle');
    await expect(page.getByText(/dashboard/i)).toBeVisible({ timeout: 5000 });
  });

  test('user can navigate through all main pages', async ({ page }) => {
    // Mock API responses
    await page.route('**/api/**', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({}),
      });
    });

    // Navigate to a page first, then set localStorage
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
    
    // Set localStorage after page is loaded
    await page.evaluate(() => {
      localStorage.setItem('api_key', 'test-api-key');
    });

    await expect(page.getByText(/dashboard/i)).toBeVisible({ timeout: 5000 });

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
    await page.waitForLoadState('networkidle');
    
    // Set localStorage after page is loaded
    await page.evaluate(() => {
      localStorage.setItem('api_key', 'test-api-key');
    });

    // Wait for button to be visible and clickable
    await page.waitForSelector('button:has-text("Start Server"), button:has-text("START SERVER")', { state: 'visible', timeout: 5000 });
    await page.click('button:has-text("Start Server"), button:has-text("START SERVER")');
    await expect(startCalled).toBeTruthy();
  });
});
