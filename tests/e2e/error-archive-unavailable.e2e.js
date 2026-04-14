// Error state: dist/edges.json (or any required asset) returns 500 →
// ARCHIVE TEMPORARILY UNAVAILABLE.
import { expect, test } from '@playwright/test';

test('Archive unavailable: 500 on edges.json renders error state', async ({ page }) => {
  await page.route('**/dist/edges.json', (route) =>
    route.fulfill({ status: 500, body: 'Internal Server Error' }),
  );

  await page.goto('/');

  const errorTitle = page.locator('.error-title');
  await expect(errorTitle).toHaveText('ARCHIVE TEMPORARILY UNAVAILABLE.', {
    timeout: 10_000,
  });
  // Today's File escape hatch is offered.
  await expect(page.locator('.error-link a')).toContainText("Today's File");
});
