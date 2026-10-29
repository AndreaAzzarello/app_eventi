import { test } from '@playwright/test';

// Screenshot di revisione della ricerca: REVIEW_SHOTS=before|after → web/.review/<valore>/ (non committata).
const OUT = process.env.REVIEW_SHOTS;
test.skip(!OUT, 'impostare REVIEW_SHOTS=before|after');

const SIZES: [string, number, number][] = [['360', 360, 740], ['390', 390, 844], ['desktop', 1280, 800]];

for (const theme of ['light', 'dark']) {
	test(`ricerca ${theme}`, async ({ page }) => {
		await page.addInitScript((t) => localStorage.setItem('ev:theme', JSON.stringify(t)), theme);
		for (const [size, w, h] of SIZES) {
			await page.setViewportSize({ width: w, height: h });
			await page.goto('/');
			await page.waitForLoadState('networkidle');
			const q = page.locator('#q');
			await q.click();
			await q.pressSequentially('Bolzano');
			await page.waitForTimeout(800);
			await page.screenshot({ path: `.review/${OUT}/ricerca-${size}-${theme}.png`, fullPage: true });
		}
	});
}
