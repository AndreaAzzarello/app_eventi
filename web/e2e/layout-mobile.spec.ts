import { expect, test } from '@playwright/test';

for (const [width, height] of [[360, 740], [390, 844]]) {
	test(`header e pagine senza overflow orizzontale a ${width}px`, async ({ page }) => {
		await page.setViewportSize({ width, height });
		for (const path of ['/', '/citta/modena', '/eventi/jazz-in-piazza-grande-seedJazz']) {
			await page.goto(path);
			await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
			const { sw, cw } = await page.evaluate(() => ({
				sw: document.documentElement.scrollWidth,
				cw: document.documentElement.clientWidth
			}));
			expect(sw, path).toBeLessThanOrEqual(cw);
			const box = await page.getByRole('button', { name: 'Cambia tema chiaro/scuro' }).boundingBox();
			expect(box!.x + box!.width, path).toBeLessThanOrEqual(width);
		}
	});
}
