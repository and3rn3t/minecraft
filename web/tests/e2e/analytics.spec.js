import { expect, test } from '@playwright/test';

test.describe('Analytics Page', () => {
  test.beforeEach(async ({ page }) => {
    // Mock API responses
    await page.route('**/api/analytics/report*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          report: {
            generated_at: '2024-01-27T12:00:00',
            period_hours: 24,
            player_behavior: {
              unique_players: 5,
              peak_hour: 20,
              hourly_distribution: { 20: 10, 21: 8 },
            },
            performance: {
              tps: {
                current: 20.0,
                average: 19.8,
                trend: { direction: 'stable' },
              },
              cpu: { current: 50.0 },
              memory: { current: 1000 },
            },
            summary: {
              status: 'healthy',
              warnings: [],
              recommendations: [],
            },
          },
        }),
      });
    });

    await page.route('**/api/analytics/trends*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          trends: {
            tps: { current: 20.0, trend: { direction: 'stable' } },
            cpu: { current: 50.0 },
            memory: { current: 1000 },
          },
        }),
      });
    });

    await page.route('**/api/analytics/anomalies*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ anomalies: [] }),
      });
    });

    await page.route('**/api/analytics/predictions*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          prediction: { predicted: 1200, confidence: 85.0 },
        }),
      });
    });

    await page.route('**/api/analytics/player-behavior*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          behavior: { unique_players: 5, peak_hour: 20 },
        }),
      });
    });

    // Mock authentication
    await page.goto('/analytics');
    await page.evaluate(() => {
      localStorage.setItem('api_key', 'test-api-key');
    });
  });

  test('should load analytics dashboard', async ({ page }) => {
    await page.goto('/analytics');
    await expect(page.getByText('Analytics Dashboard')).toBeVisible();
  });

  test('should display overview tab by default', async ({ page }) => {
    await page.goto('/analytics');
    await expect(page.getByText('Summary')).toBeVisible();
    await expect(page.getByText('Current TPS')).toBeVisible();
  });

  test('should switch to performance tab', async ({ page }) => {
    await page.goto('/analytics');
    await page.click('button:has-text("Performance")');
    await expect(page.getByText('TPS (Ticks Per Second)')).toBeVisible();
  });

  test('should switch to players tab', async ({ page }) => {
    await page.goto('/analytics');
    await page.click('button:has-text("Players")');
    await expect(page.getByText('Player Behavior')).toBeVisible();
  });

  test('should change time period', async ({ page }) => {
    await page.goto('/analytics');
    await page.selectOption('select', '6');
    await expect(page.getByText('Summary')).toBeVisible();
  });

  test('should collect analytics data', async ({ page }) => {
    let collectCalled = false;
    await page.route('**/api/analytics/collect', async route => {
      collectCalled = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, message: 'Data collected' }),
      });
    });

    await page.goto('/analytics');
    await page.click('button:has-text("Collect Data")');
    await expect(collectCalled).toBeTruthy();
  });

  test('should generate custom report', async ({ page }) => {
    let generateCalled = false;
    await page.route('**/api/analytics/custom-report', async route => {
      generateCalled = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          report: {},
          saved_as: 'custom_report.json',
        }),
      });
    });

    await page.goto('/analytics');
    await page.click('button:has-text("Generate Report")');
    await expect(generateCalled).toBeTruthy();
  });
});
