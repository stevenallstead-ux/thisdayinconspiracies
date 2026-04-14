// Error state: no path between endpoints → NO KNOWN CONNECTION.
//
// We can't easily force "no path" between two real seeded events because
// the graph is densely connected. Simulate by navigating to a share URL
// pointing at one valid event and one valid-but-disconnected entity that
// produces no edges. As a stable fallback: hit the share-URL with one
// real event and an entity that has zero events — apply the OV-7 quarantine
// path or trigger the empty-targets branch.
//
// Simpler: use entity:something-that-doesnt-exist on the URL — that hits
// the stale-URL error path. To specifically exercise NO KNOWN CONNECTION,
// we mock the graph load so the events become isolated.
import { expect, test } from '@playwright/test';

test('No path: two unconnected events show NO KNOWN CONNECTION', async ({ page }) => {
  // Force an empty edges payload so every event becomes isolated.
  // This guarantees graph.shortestPath returns null for the test inputs.
  await page.route('**/dist/edges.json', async (route) => {
    const original = await route.fetch();
    const body = await original.json();
    // Strip every neighbor list to simulate a corpus with no edges.
    const isolated = Object.fromEntries(Object.keys(body).map((k) => [k, []]));
    await route.fulfill({ json: isolated });
  });

  await page.goto('/');
  await expect(page.locator('#find-button .cta-label')).toHaveText('FIND THE CONNECTION', { timeout: 10_000 });

  await page.fill('#from-input', 'JFK Assassinated');
  await page.locator('.ac-row[data-kind="event"]').first().waitFor();
  await page.locator('.ac-row[data-kind="event"]').first().click();

  await page.fill('#to-input', 'Phoenix Lights');
  await page.locator('.ac-row[data-kind="event"]').first().waitFor();
  await page.locator('.ac-row[data-kind="event"]').first().click();

  await page.click('#find-button');

  const errorTitle = page.locator('.error-title');
  await expect(errorTitle).toHaveText('NO KNOWN CONNECTION.');
  await expect(page.locator('.error-body')).toContainText('THE FILE ENDS HERE.');
});
