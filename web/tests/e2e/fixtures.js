import { expect, test as base } from '@playwright/test';
import { mockApi } from './mock-api';

/**
 * `test` with an `api` fixture: `await api({ user, routes })` mocks the API
 * for the page (see mock-api.js), and the test fails afterwards if the page
 * called an endpoint the mock doesn't answer. Specs import `test` and
 * `expect` from here, not from @playwright/test.
 */
export const test = base.extend({
  api: async ({ page }, use) => {
    let mocked;
    await use(async options => {
      mocked = await mockApi(page, options);
      return mocked;
    });
    if (mocked) {
      expect(mocked.unhandled, 'API calls with no mock (add them to mock-api.js)').toEqual([]);
    }
  },
});

export { expect };
