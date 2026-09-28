import { expect, test } from './fixtures';

const isPost = path => request => request.url().endsWith(`/api/${path}`) && request.method() === 'POST';

test.describe('Analytics page', () => {
  test.beforeEach(async ({ page, api }) => {
    await api({
      routes: {
        'analytics/collect': { success: true, message: 'Data collected' },
        'analytics/custom-report': { report: {}, saved_as: 'custom_report.json' },
      },
    });
    await page.goto('/analytics');
    await expect(page.getByRole('heading', { name: 'ANALYTICS DASHBOARD' })).toBeVisible();
  });

  test('opens on the overview', async ({ page }) => {
    await expect(page.getByText('Summary')).toBeVisible();
    await expect(page.getByText('Current TPS')).toBeVisible();
  });

  test('switches to the performance tab', async ({ page }) => {
    await page.getByRole('button', { name: /performance/i }).click();
    await expect(page.getByText('TPS (Ticks Per Second)')).toBeVisible();
  });

  test('switches to the players tab', async ({ page }) => {
    await page.getByRole('button', { name: /players/i }).click();
    await expect(page.getByText('Player Behavior')).toBeVisible();
  });

  test('reloads the report for a new time period', async ({ page }) => {
    const reloaded = page.waitForRequest(r => r.url().includes('/api/analytics/report') && r.url().includes('hours=6'));
    await page.locator('select').selectOption('6');

    await reloaded;
    await expect(page.getByText('Summary')).toBeVisible();
  });

  // These used to set a flag inside the route handler and assert it straight
  // after the click, before the request had been made: a race they usually lost.
  test('collects analytics data on demand', async ({ page }) => {
    const collected = page.waitForRequest(isPost('analytics/collect'));
    await page.getByRole('button', { name: /collect data/i }).click();

    await collected;
    await expect(page.getByText(/collected successfully/i)).toBeVisible();
  });

  test('generates a custom report on demand', async ({ page }) => {
    const generated = page.waitForRequest(isPost('analytics/custom-report'));
    await page.getByRole('button', { name: /generate report/i }).click();

    expect((await generated).postDataJSON()).toEqual({ hours: 24, metrics: ['performance', 'players'] });
    await expect(page.getByText('Custom report generated: custom_report.json')).toBeVisible();
  });
});
