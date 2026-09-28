import { expect, test } from '@playwright/test';
import { mockApi, SIGNED_IN } from './mock-api';

test.describe('User journeys', () => {
  test('a new user registers and lands on the dashboard', async ({ page }) => {
    await mockApi(page, { user: null });

    await page.goto('/register');
    await page.getByRole('textbox', { name: 'USERNAME' }).fill('newplayer');
    await page.getByRole('textbox', { name: 'PASSWORD', exact: true }).fill('correct-horse-battery');
    await page.getByRole('textbox', { name: 'CONFIRM PASSWORD' }).fill('correct-horse-battery');

    const registered = page.waitForRequest(r => r.url().endsWith('/api/auth/register') && r.method() === 'POST');
    await page.getByRole('button', { name: 'REGISTER' }).click();
    expect((await registered).postDataJSON()).toMatchObject({ username: 'newplayer' });

    await expect(page).toHaveURL(/\/dashboard$/);
    await expect(page.getByRole('heading', { name: 'DASHBOARD' })).toBeVisible();
  });

  test('a returning user signs in', async ({ page }) => {
    await mockApi(page, { user: null });

    await page.goto('/login');
    await page.getByRole('textbox', { name: 'USERNAME' }).fill('steve');
    await page.getByRole('textbox', { name: 'PASSWORD' }).fill('correct-horse-battery');
    await page.getByRole('button', { name: /^LOG ?IN$/ }).click();

    await expect(page).toHaveURL(/\/dashboard$/);
    await expect(page.getByRole('heading', { name: 'DASHBOARD' })).toBeVisible();
  });

  test('a signed-out visitor is sent to the login page', async ({ page }) => {
    await mockApi(page, { user: null });

    await page.goto('/dashboard');

    await expect(page).toHaveURL(/\/login$/);
  });

  test('a signed-in user can reach every main page from the nav', async ({ page }) => {
    await mockApi(page, { user: SIGNED_IN });
    await page.goto('/dashboard');
    await expect(page.getByRole('heading', { name: 'DASHBOARD' })).toBeVisible();

    for (const [link, heading] of [
      ['ANALYTICS', 'ANALYTICS DASHBOARD'],
      ['PLAYERS', 'PLAYER MANAGEMENT'],
      ['BACKUPS', 'BACKUPS'],
      ['WORLDS', 'WORLD MANAGEMENT'],
    ]) {
      await page.getByRole('link', { name: link, exact: true }).click();
      await expect(page.getByRole('heading', { name: heading })).toBeVisible();
    }
  });

  test('starting the server from the dashboard calls the API', async ({ page }) => {
    await mockApi(page, {
      user: SIGNED_IN,
      routes: { status: { running: false, status: 'Exited' } },
    });
    await page.goto('/dashboard');

    const started = page.waitForRequest(r => r.url().endsWith('/api/server/start') && r.method() === 'POST');
    // Anchored: "RESTART SERVER" contains "START SERVER" too
    await page.getByRole('button', { name: /^\W*START SERVER$/ }).click();

    expect((await started).method()).toBe('POST');
  });
});
