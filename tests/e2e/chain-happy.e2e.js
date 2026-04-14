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

  // Chain rendered: ≥2 event cards + ≥1 VIA divider.
  const cards = page.locator('.event-card');
  await expect(cards).toHaveCount(6); // verified locally; allow tolerance below if fragile
  const dividers = page.locator('.chain-divider');
  await expect(dividers.first()).toContainText('VIA');

  // Share URL updated with namespace prefix per OV-14.
  const url = new URL(page.url());
  expect(url.searchParams.get('from')).toMatch(/^event:/);
  expect(url.searchParams.get('to')).toMatch(/^event:/);
});
