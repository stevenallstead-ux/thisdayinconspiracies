// Regression: the daily-entry page MOVED from / to /today/ in Phase C.
// Verify it still loads, renders today's entries (or the empty state),
// and exposes the back-link to the Connect-Any-Two homepage.
import { expect, test } from '@playwright/test';

test('/today/ regression: daily-entry page loads with back-link', async ({ page }) => {
  await page.goto('/today/');

  // Page title + back-link + file banner present.
  await expect(page).toHaveTitle(/Today's File/i);
  await expect(page.locator('.back-to-connect')).toContainText('Connect Two Files');
  await expect(page.locator('.file-banner')).toBeVisible();

  // At least one file-card renders — either today's entries OR the
  // "archive is silent" empty state (both use .file-card markup).
  const cards = await page.locator('.file-card').count();
  expect(cards).toBeGreaterThan(0);

  // Month timeline section is wired up — at least one <li> from the
  // seed corpus (April has many entries; this asserts the page hydrated).
  await expect(page.locator('#month-events li').first()).toBeVisible({ timeout: 10_000 });
});

test('/today/ → back-link returns to Connect-Any-Two homepage', async ({ page }) => {
  await page.goto('/today/');
  await page.click('.back-to-connect');
  await expect(page).toHaveURL(/\/$/);
  await expect(page.locator('#find-button')).toBeVisible();
});
