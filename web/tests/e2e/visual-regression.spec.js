/* eslint-env node */
import { expect, test } from '@playwright/test';
import { mockApi } from './mock-api';

// Screenshots only compare against baselines rendered the same way: fonts and
// antialiasing differ between macOS and Linux, and between Linux images. The
// baselines are rendered in the official Playwright image, CI runs these in
// that same image, and `make test-visual` runs them there locally. Elsewhere
// they are skipped rather than failing on pixels no change caused.
test.skip(process.env.PW_VISUAL !== '1', 'visual tests run in the Playwright container: make test-visual');

const PAGES = [
  ['dashboard', '/dashboard', 'DASHBOARD'],
  ['analytics', '/analytics', 'ANALYTICS DASHBOARD'],
  ['backups', '/backups', 'BACKUPS'],
  ['players', '/players', 'PLAYER MANAGEMENT'],
  ['worlds', '/worlds', 'WORLD MANAGEMENT'],
];

test.describe('Visual regression', () => {
  test.beforeEach(async ({ page }) => {
    // Pages print times ("SYNCED 12:00:00"); freeze the clock so they match
    await page.clock.setFixedTime(new Date('2026-09-01T12:00:00Z'));
  });

  for (const [name, path, heading] of PAGES) {
    test(`${name} page`, async ({ page }) => {
      await mockApi(page);
      await page.goto(path);
      await expect(page.getByRole('heading', { name: heading })).toBeVisible();
      await page.waitForLoadState('networkidle');

      await expect(page).toHaveScreenshot(`${name}.png`, { fullPage: true });
    });
  }

  test('login page', async ({ page }) => {
    await mockApi(page, { user: null });
    await page.goto('/login');
    await expect(page.getByRole('button', { name: 'LOGIN' })).toBeVisible();

    await expect(page).toHaveScreenshot('login.png', { fullPage: true });
  });
});
