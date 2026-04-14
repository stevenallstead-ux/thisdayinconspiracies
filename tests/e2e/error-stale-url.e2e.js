// Error state: share URL with bogus event id → ARCHIVE ENTRY NOT FOUND.
// Validates OV-14 URL namespace parsing + OV-1 invariant guard.
import { expect, test } from '@playwright/test';

test('Stale share URL: bogus event id renders ARCHIVE ENTRY NOT FOUND', async ({ page }) => {
  await page.goto('/?from=event:bogus-id-that-does-not-exist&to=entity:cia');

  await expect(page.locator('.error-title')).toContainText('ARCHIVE ENTRY NOT FOUND', {
    timeout: 10_000,
  });
  await expect(page.locator('.error-link a')).toContainText('Return to archive home');
});

test('Malformed share URL: missing namespace prefix is rejected', async ({ page }) => {
  await page.goto('/?from=1963-jfk-assassinated-in-dallas&to=cia');

  await expect(page.locator('.error-title')).toContainText('ARCHIVE ENTRY NOT FOUND', {
    timeout: 10_000,
  });
});
