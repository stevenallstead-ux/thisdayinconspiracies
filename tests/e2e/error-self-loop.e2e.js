// Error state: same FROM and TO → THE FILE REFERS TO ITSELF.
// Renders the single event card with a typewriter note above it.
import { expect, test } from '@playwright/test';

test('Self-loop: same event for FROM and TO renders THE FILE REFERS TO ITSELF', async ({ page }) => {
  await page.goto('/?from=event:1963-jfk-assassinated-in-dallas&to=event:1963-jfk-assassinated-in-dallas');

  await expect(page.locator('.self-loop-note')).toHaveText('THE FILE REFERS TO ITSELF.', {
    timeout: 10_000,
  });
  // Single event card renders.
  await expect(page.locator('.event-card')).toHaveCount(1);
});
