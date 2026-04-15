// Happy path: type two seeded events, click FIND THE CONNECTION, assert
// chain renders. Uses two events that we know connect through the seed
// graph (JFK + Phoenix Lights — verified locally to produce a 5-hop chain).
import { expect, test } from '@playwright/test';

test('Connect-Any-Two: JFK → Phoenix Lights renders a chain', async ({ page }) => {
  await page.goto('/');

  // Wait for the loading state to clear (button label flips off "INITIALIZING...").
  await expect(page.locator('#find-button .cta-label')).toHaveText('FIND THE CONNECTION', { timeout: 10_000 });

  await page.fill('#from-input', 'JFK Assassinated');
  // Wait for at least one autocomplete row, then click the first event row.
  await page.locator('.ac-row[data-kind="event"]').first().waitFor();
  await page.locator('.ac-row[data-kind="event"]').first().click();

  await page.fill('#to-input', 'Phoenix Lights');
  await page.locator('.ac-row[data-kind="event"]').first().waitFor();
  await page.locator('.ac-row[data-kind="event"]').first().click();

  await page.click('#find-button');

  // Chain rendered: ≥2 pin cards + ≥1 VIA tag on the string layer. Don't
  // assert exact hop count — corpus expansion can change which path is
  // optimal, and that's intentional. The contract: "a chain renders with
  // at least the two endpoints + at least one connecting hop."
  const cards = page.locator('.pin-card');
  await expect(cards.first()).toBeVisible();
  const cardCount = await cards.count();
  expect(cardCount).toBeGreaterThanOrEqual(2);
  const viaTags = page.locator('.via-tag');
  await expect(viaTags.first()).toContainText('VIA');

  // Share URL updated with namespace prefix per OV-14.
  const url = new URL(page.url());
  expect(url.searchParams.get('from')).toMatch(/^event:/);
  expect(url.searchParams.get('to')).toMatch(/^event:/);
});
