import { expect, test } from '@playwright/test';

test.describe('Visual Regression Tests', () => {
  test.beforeEach(async ({ page }) => {
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
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            running: true,
            status: 'Up',
            players: [],
            backups: [],
            worlds: [],
            metrics: {},
          }),
        });
      }
    });
  });

  test('dashboard visual snapshot', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
    // Wait for loading to complete
    await page.waitForSelector('text=/Loading/i', { state: 'hidden', timeout: 10000 }).catch(() => {});
    await expect(page).toHaveScreenshot('dashboard.png', {
      fullPage: true,
      maxDiffPixels: 100,
    });
  });

  test('analytics page visual snapshot', async ({ page }) => {
    await page.goto('/analytics');
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('text=/Loading/i', { state: 'hidden', timeout: 10000 }).catch(() => {});
    await expect(page).toHaveScreenshot('analytics.png', {
      fullPage: true,
      maxDiffPixels: 100,
    });
  });

  test('backups page visual snapshot', async ({ page }) => {
    await page.goto('/backups');
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('text=/Loading/i', { state: 'hidden', timeout: 10000 }).catch(() => {});
    await expect(page).toHaveScreenshot('backups.png', {
      fullPage: true,
      maxDiffPixels: 100,
    });
  });

  test('players page visual snapshot', async ({ page }) => {
    await page.goto('/players');
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('text=/Loading/i', { state: 'hidden', timeout: 10000 }).catch(() => {});
    await expect(page).toHaveScreenshot('players.png', {
      fullPage: true,
      maxDiffPixels: 100,
    });
  });

  test('worlds page visual snapshot', async ({ page }) => {
    await page.goto('/worlds');
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('text=/Loading/i', { state: 'hidden', timeout: 10000 }).catch(() => {});
    await expect(page).toHaveScreenshot('worlds.png', {
      fullPage: true,
      maxDiffPixels: 100,
    });
  });

  test('login page visual snapshot', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('text=/Loading/i', { state: 'hidden', timeout: 10000 }).catch(() => {});
    await expect(page).toHaveScreenshot('login.png', {
      fullPage: true,
      maxDiffPixels: 100,
    });
  });
});
