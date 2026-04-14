// E2E: the WITHHELD Easter egg fires when a decoy entity is one (or
// both) endpoints. Verifies autocomplete tag, document rendering,
// share URL namespace, and the both-withheld variant copy.
import { expect, test } from '@playwright/test';

test('Autocomplete surfaces WITHHELD decoys with the correct tag', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('#find-button .cta-label')).toHaveText('FIND THE CONNECTION', { timeout: 10_000 });

  await page.fill('#from-input', 'MJ-12');

  const withheldRow = page.locator('.ac-row[data-kind="withheld"]').first();
  await expect(withheldRow).toBeVisible();
  await expect(withheldRow.locator('.ac-tag-withheld')).toHaveText('WITHHELD');
});

test('Selecting a withheld decoy renders the FOIA document', async ({ page }) => {
  await page.goto('/?from=withheld:mj-12-documents&to=event:1947-the-roswell-incident');

  const doc = page.locator('.withheld-document');
  await expect(doc).toBeVisible({ timeout: 10_000 });
  await expect(doc.locator('.classified-stamp-large')).toHaveText('CLASSIFIED');
  await expect(doc.locator('.denial-stamp')).toHaveText('DECLASSIFICATION DENIED');
  await expect(doc).toContainText('SUBJECT: MJ-12 Documents');
  await expect(doc).toContainText('The Roswell Incident');
  await expect(doc).toContainText('FILE WITHHELD UNDER EXEMPTION (b)(1)');
  // No event cards, no chain dividers, no re-roll button.
  await expect(page.locator('.event-card')).toHaveCount(0);
  await expect(page.locator('#alt-path-button')).toHaveCount(0);
});

test('Both-withheld renders the BOTH FILES WITHHELD variant', async ({ page }) => {
  await page.goto('/?from=withheld:mj-12-documents&to=withheld:recipe-for-coca-cola');

  await expect(page.locator('.withheld-document')).toBeVisible({ timeout: 10_000 });
  await expect(page.locator('.withheld-document')).toContainText('BOTH FILES WITHHELD');
});

test('Withheld share URL is deterministic', async ({ page, context }) => {
  await page.goto('/?from=withheld:mj-12-documents&to=event:1947-the-roswell-incident');
  await expect(page.locator('.withheld-document')).toBeVisible({ timeout: 10_000 });
  const fileNoA = await page.locator('.file-meta').textContent();

  const page2 = await context.newPage();
  await page2.goto('/?from=withheld:mj-12-documents&to=event:1947-the-roswell-incident');
  await expect(page2.locator('.withheld-document')).toBeVisible({ timeout: 10_000 });
  const fileNoB = await page2.locator('.file-meta').textContent();

  expect(fileNoA).toEqual(fileNoB);
});
