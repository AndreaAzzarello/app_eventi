import { expect, test } from '@playwright/test';

test('su desktop lista e mappa sono affiancate', async ({ page }) => {
	await page.goto('/');
	await expect(page.getByRole('tab', { name: 'Mappa' })).toBeHidden();
	await expect(page.getByRole('link', { name: 'Jazz in Piazza Grande' })).toBeVisible();
	await expect(page.getByRole('region', { name: 'Mappa degli eventi' })).toBeVisible();
	// Navigazione da tastiera: il primo Tab porta al link "Vai al contenuto".
	await page.keyboard.press('Tab');
	await expect(page.getByRole('link', { name: 'Vai al contenuto' })).toBeFocused();
});
