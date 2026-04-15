// K-shortest paths E2E: when alternates exist, the TRACE A DIFFERENT
// PATH button is visible, clicking it advances the seed in the URL,
// and reloading a seeded URL reproduces the same chain (deterministic
// per URL).
//
// We use JFK → Phoenix Lights because the post-expansion graph
// reliably returns multiple alternatives for that pair.
import { expect, test } from '@playwright/test';

test('Alt-paths: TRACE A DIFFERENT PATH button shows + advances seed in URL', async ({ page }) => {
  await page.goto('/?from=event:1963-jfk-assassinated-in-dallas&to=event:1997-the-phoenix-lights');

  // Wait for chain to render
  await expect(page.locator('.pin-card').first()).toBeVisible({ timeout: 10_000 });

  // Alt-paths button should be visible (corpus expansion guarantees ≥1 alt for this pair)
  const altButton = page.locator('#alt-path-button');
  await expect(altButton).toBeVisible();
  await expect(altButton).toContainText(/TRACE A DIFFERENT PATH/);

  // Snapshot current chain titles for diff comparison
  const initialTitles = await page.locator('.pin-card h3').allTextContents();
  expect(initialTitles.length).toBeGreaterThan(1);

  // Click re-roll
  await altButton.click();

  // URL should now contain seed=1
  const url = new URL(page.url());
  expect(url.searchParams.get('seed')).toBe('1');

  // Chain content should differ — at minimum the events list changed
  const newTitles = await page.locator('.pin-card h3').allTextContents();
  expect(newTitles).not.toEqual(initialTitles);
});

test('Seeded URL is deterministic across reloads', async ({ page, context }) => {
  await page.goto('/?from=event:1963-jfk-assassinated-in-dallas&to=event:1997-the-phoenix-lights&seed=2');
  await expect(page.locator('.pin-card').first()).toBeVisible({ timeout: 10_000 });
  const titlesA = await page.locator('.pin-card h3').allTextContents();

  // Open same URL in a fresh page
  const page2 = await context.newPage();
  await page2.goto('/?from=event:1963-jfk-assassinated-in-dallas&to=event:1997-the-phoenix-lights&seed=2');
  await expect(page2.locator('.pin-card').first()).toBeVisible({ timeout: 10_000 });
  const titlesB = await page2.locator('.pin-card h3').allTextContents();

  expect(titlesA).toEqual(titlesB);
});

test('Default URL (no seed) shows seed=0 path; seed param renders alternative', async ({ page }) => {
  await page.goto('/?from=event:1963-jfk-assassinated-in-dallas&to=event:1997-the-phoenix-lights');
  await expect(page.locator('.pin-card').first()).toBeVisible({ timeout: 10_000 });
  const default_ = await page.locator('.pin-card h3').allTextContents();

  await page.goto('/?from=event:1963-jfk-assassinated-in-dallas&to=event:1997-the-phoenix-lights&seed=1');
  await expect(page.locator('.pin-card').first()).toBeVisible({ timeout: 10_000 });
  const seeded = await page.locator('.pin-card h3').allTextContents();

  expect(seeded).not.toEqual(default_);
});
