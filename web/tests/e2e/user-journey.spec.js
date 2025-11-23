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
          body: JSON.stringify({
            success: true,
            token: 'test-token',
            user: { username: testUser, role: 'user' },
          }),
        });
      } else if (url.includes('/login')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            token: 'test-token',
            user: { username: testUser, role: 'user' },
          }),
        });
      } else if (url.includes('/user') || url.includes('/current')) {
        // Mock getCurrentUser for AuthContext
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ username: testUser, role: 'user' }),
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
    await page.waitForSelector('#username', { state: 'visible', timeout: 10000 });
    await page.fill('#username', testUser);
    await page.fill('#password', testPassword);
    await page.fill('#confirmPassword', testPassword);

    // Submit registration form
    await Promise.all([
      page.waitForResponse(resp => resp.url().includes('/register') && resp.status() === 200),
      page.click('button:has-text("REGISTER"), button:has-text("Register")'),
    ]);

    // Wait for navigation after registration (registration should redirect to dashboard)
    try {
      await page.waitForURL('/dashboard', { timeout: 15000 });
    } catch {
      // If registration doesn't auto-navigate, try login
      await page.goto('/login');
      await page.waitForLoadState('networkidle');
      await page.waitForSelector('#username', { state: 'visible', timeout: 10000 });
      await page.fill('#username', testUser);
      await page.fill('#password', testPassword);

      // Submit login form
      await Promise.all([
        page.waitForResponse(resp => resp.url().includes('/login') && resp.status() === 200),
        page.click('button:has-text("LOGIN"), button:has-text("Login")'),
      ]);

      await page.waitForURL('/dashboard', { timeout: 15000 });
    }

    // Step 3: Access Dashboard
    await page.waitForURL('/dashboard', { timeout: 10000 });
    await page.waitForLoadState('networkidle');
    // Wait for loading to complete and dashboard to render
    await page
      .waitForSelector('text=/DASHBOARD/i, text=/Loading/i', { state: 'visible', timeout: 10000 })
      .catch(() => {});
    await page
      .waitForSelector('text=/Loading/i', { state: 'hidden', timeout: 10000 })
      .catch(() => {});
    await expect(page.getByText(/DASHBOARD/i)).toBeVisible({ timeout: 10000 });
  });

  test('user can navigate through all main pages', async ({ page }) => {
    // Set localStorage before navigation
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('api_key', 'test-api-key');
    });

    // Mock API responses
    await page.route('**/api/**', async route => {
      const url = route.request().url();
      if (url.includes('/user') || url.includes('/current')) {
        // Mock getCurrentUser for AuthContext
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ username: 'testuser', role: 'user' }),
        });
      } else if (url.includes('/status')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ running: true, status: 'Up' }),
        });
      } else if (url.includes('/metrics')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ metrics: {} }),
        });
      } else if (url.includes('/players')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ players: [] }),
        });
      } else if (url.includes('/analytics')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            report: {},
            trends: {},
            anomalies: [],
            prediction: {},
            behavior: {},
          }),
        });
      } else if (url.includes('/backups')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ backups: [] }),
        });
      } else if (url.includes('/worlds')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ worlds: [] }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({}),
        });
      }
    });

    // Navigate to dashboard
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
    // Wait for loading to complete
    await page
      .waitForSelector('text=/dashboard/i, text=/Loading/i', { state: 'visible', timeout: 10000 })
      .catch(() => {});
    await page
      .waitForSelector('text=/Loading/i', { state: 'hidden', timeout: 10000 })
      .catch(() => {});

    await expect(page.getByText(/DASHBOARD/i)).toBeVisible({ timeout: 10000 });

    // Navigate to Analytics
    await page.click('a:has-text("Analytics"), a[href="/analytics"]');
    await page.waitForLoadState('networkidle');
    await page
      .waitForSelector('text=/Loading/i', { state: 'hidden', timeout: 10000 })
      .catch(() => {});
    await expect(page.getByText(/ANALYTICS/i)).toBeVisible({ timeout: 10000 });

    // Navigate to Players
    await page.click('a:has-text("Players"), a[href="/players"]');
    await page.waitForLoadState('networkidle');
    await page
      .waitForSelector('text=/Loading/i', { state: 'hidden', timeout: 10000 })
      .catch(() => {});
    await expect(page.getByText(/PLAYER MANAGEMENT/i)).toBeVisible({ timeout: 10000 });

    // Navigate to Backups
    await page.click('a:has-text("Backups"), a[href="/backups"]');
    await page.waitForLoadState('networkidle');
    await page
      .waitForSelector('text=/Loading/i', { state: 'hidden', timeout: 10000 })
      .catch(() => {});
    await expect(page.getByText(/BACKUP/i)).toBeVisible({ timeout: 10000 });

    // Navigate to Worlds
    await page.click('a:has-text("Worlds"), a[href="/worlds"]');
    await page.waitForLoadState('networkidle');
    await page
      .waitForSelector('text=/Loading/i', { state: 'hidden', timeout: 10000 })
      .catch(() => {});
    await expect(page.getByText(/WORLD MANAGEMENT/i)).toBeVisible({ timeout: 10000 });
  });

  test('user can manage server from dashboard', async ({ page }) => {
    // Set localStorage before navigation
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('api_key', 'test-api-key');
    });

    let startCalled = false;
    await page.route('**/api/**', async route => {
      const url = route.request().url();
      if (url.includes('/server/start')) {
        startCalled = true;
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true }),
        });
      } else if (url.includes('/status')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ running: false, status: 'Stopped' }),
        });
      } else if (url.includes('/user') || url.includes('/current')) {
        // Mock getCurrentUser for AuthContext
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ username: 'testuser', role: 'user' }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({}),
        });
      }
    });

    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
    // Wait for loading to complete
    await page
      .waitForSelector('text=/Loading/i', { state: 'hidden', timeout: 10000 })
      .catch(() => {});

    // Wait for button to be visible and clickable
    await page.waitForSelector('button:has-text("Start Server"), button:has-text("START SERVER")', {
      state: 'visible',
      timeout: 5000,
    });
    await page.click('button:has-text("Start Server"), button:has-text("START SERVER")');
    await expect(startCalled).toBeTruthy();
  });
});
