// Regression: the daily-entry page MOVED from / to /today/ in Phase C.
// Verify it still loads, renders today's entries (or the empty state),
// and exposes the back-link to the Connect-Any-Two homepage.
import { expect, test } from '@playwright/test';

test('/today/ regression: daily-entry page loads with back-link', async ({ page }) => {
  await page.goto('/today/');

  // Page title + back-link + date banner present.
  await expect(page).toHaveTitle(/Today's File/i);
  await expect(page.locator('.back-to-connect')).toContainText('Connect Two Files');
  await expect(page.locator('.date-banner')).toBeVisible();

  // Either today has entries or the empty state renders. Both are valid;
  // the regression bug we're guarding against is the page itself failing.
  const hasEvents = await page.locator('.event-card').count();
  const hasEmpty = await page.locator('.empty-state').count();
  expect(hasEvents + hasEmpty).toBeGreaterThan(0);

  // Month list section is wired up — at least one .month-event from the
  // seed corpus (April has many entries; this asserts the page hydrated).
  await expect(page.locator('.month-event').first()).toBeVisible({ timeout: 10_000 });
});

test('/today/ → back-link returns to Connect-Any-Two homepage', async ({ page }) => {
  await page.goto('/today/');
  await page.click('.back-to-connect');
  await expect(page).toHaveURL(/\/$/);
  await expect(page.locator('#find-button')).toBeVisible();
});
