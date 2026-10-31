import { test, expect } from '@playwright/test';

for (const lang of ['en', 'ru', 'kk', 'ar']) {
  test(`375px layout and text keyboard controls: ${lang}`, async ({ page }, testInfo) => {
    await page.goto('/labs/interactive/');
    const lab = page.locator('.interactive-lab');
    await lab.locator('select').selectOption(lang);
    await expect(lab).toHaveAttribute('lang', lang);
    await expect(lab.locator('.interactive-parts button')).toHaveCount(3);
    await expect(lab).toHaveAttribute('dir', lang === 'ar' ? 'rtl' : 'ltr');
    await lab.locator('summary').focus();
    await page.keyboard.press('Enter');
    await expect(lab.locator('details')).toHaveAttribute('open', '');
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    const part = lab.locator('.interactive-parts button').nth(1);
    await part.focus();
    await page.keyboard.press('Enter');
    await expect(part).toBeFocused();
    await expect(part).toHaveAttribute('aria-pressed', 'true');
    expect(await part.evaluate(el => getComputedStyle(el).outlineStyle)).not.toBe('none');
    await page.screenshot({ path: testInfo.outputPath(`${lang}-375.png`), fullPage: true });
  });
}

test('viewer stays unloaded until requested; failed chunk restores keyboard focus', async ({ page }) => {
  const requests: string[] = [];
  page.on('request', req => { if (/\/model-viewer-[^/]+\.js/.test(req.url())) requests.push(req.url()); });
  await page.route('**/model-viewer-*.js', route => route.abort('failed'));
  await page.goto('/labs/interactive/');
  const load = page.getByRole('button', { name: 'Load 3D model', exact: true });
  await expect(load).toBeVisible();
  expect(requests).toHaveLength(0);
  await load.focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('alert')).toContainText('could not start');
  expect(requests.length).toBeGreaterThan(0);
  await expect(load).toBeFocused();
  await expect(page.locator('.interactive-parts button')).toHaveCount(3);
});

test('real viewer loads the local GLB and keeps text controls usable', async ({ page }, testInfo) => {
  await page.goto('/labs/interactive/');
  await page.getByRole('button', { name: 'Load 3D model', exact: true }).click();
  await page.waitForFunction(() => (document.querySelector('model-viewer') as HTMLElement & { loaded?: boolean })?.loaded);
  await expect(page.locator('.interactive-parts button')).toHaveCount(3);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath('viewer-375.png'), fullPage: true });
});
