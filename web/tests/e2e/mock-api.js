/**
 * One mock of the API for every browser test.
 *
 * The specs used to carry their own catch-all mocks keyed on URL fragments
 * such as "/user" and "/current", which the app never calls: it asks
 * /api/auth/me who is signed in. Every unmatched call got `200 {}`, which the
 * app reads as a signed-in user, so /register redirected to the dashboard and
 * the sign-up journey could never run.
 *
 * mockApi(page, { user }) answers the endpoints the pages actually use.
 * `user` null means signed out: /auth/me returns 401 until a register or login
 * call signs someone in. Pass `routes` to replace or add individual endpoints;
 * the key is the path after /api, the value an object (sent as JSON) or a
 * function (route, request) => handled.
 */

export const SIGNED_IN = { username: 'steve', role: 'admin', email: 'steve@example.com' };

const json = (route, body, status = 200) =>
  route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });

const DEFAULTS = {
  health: { status: 'healthy' },
  status: { running: true, status: 'Up 2 hours' },
  // Strings, as the API sends docker stats with the % stripped
  metrics: { metrics: { cpu_percent: '12.50', memory_usage: '1.2GiB / 4GiB', memory_percent: '30.00' } },
  players: { players: ['Alex', 'Steve'], online: 2, max: 10 },
  backups: { backups: [] },
  worlds: { worlds: [] },
  plugins: { plugins: [] },
  logs: { logs: ['[12:00:00] [Server thread/INFO]: Done'], lines: 1 },
  'analytics/report': {
    report: {
      generated_at: '2026-09-01T12:00:00',
      period_hours: 24,
      player_behavior: { unique_players: 5, peak_hour: 20, hourly_distribution: { 20: 10, 21: 8 } },
      performance: {
        tps: { current: 20.0, average: 19.8, trend: { direction: 'stable' } },
        cpu: { current: 50.0 },
        memory: { current: 1000 },
      },
      summary: { status: 'healthy', warnings: [], recommendations: [] },
    },
  },
  'analytics/trends': {
    trends: { tps: { current: 20.0, trend: { direction: 'stable' } }, cpu: { current: 50.0 }, memory: { current: 1000 } },
  },
  'analytics/anomalies': { anomalies: [] },
  'analytics/predictions': { prediction: { predicted: 1200, confidence: 85.0 } },
  'analytics/player-behavior': { behavior: { unique_players: 5, peak_hour: 20 } },
  'auth/2fa/status': { success: true, enabled: false, configured: false, has_password: true },
};

export async function mockApi(page, { user = SIGNED_IN, routes = {} } = {}) {
  let currentUser = user;
  const calls = [];

  const handlers = {
    ...DEFAULTS,
    'auth/me': route => (currentUser ? json(route, currentUser) : json(route, { error: 'Not authenticated' }, 401)),
    'auth/register': (route, request) => {
      const { username } = request.postDataJSON();
      currentUser = { username, role: 'user' };
      return json(route, { success: true, user: currentUser, token: 'test-token' });
    },
    'auth/login': (route, request) => {
      const { username } = request.postDataJSON();
      currentUser = { username, role: 'user' };
      return json(route, { success: true, user: currentUser, token: 'test-token' });
    },
    'auth/logout': route => {
      currentUser = null;
      return json(route, { success: true });
    },
    ...routes,
  };

  await page.route(/\/api\//, async (route, request) => {
    const path = new URL(request.url()).pathname.replace(/^.*?\/api\//, '');
    calls.push({ method: request.method(), path });
    const handler = handlers[path];
    if (typeof handler === 'function') {
      return handler(route, request);
    }
    if (handler !== undefined) {
      return json(route, handler);
    }
    // Anything a page asks for that isn't listed: an empty success, so a page
    // renders its empty state rather than an error.
    return json(route, {});
  });

  return { calls };
}

/** Store an API key before the app loads, the way a returning browser has one. */
export async function withApiKey(page) {
  await page.addInitScript(() => localStorage.setItem('api_key', 'test-api-key'));
}
