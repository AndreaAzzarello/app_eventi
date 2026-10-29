import { expect, test, type Page } from '@playwright/test';
import { getDocument, signInByEmail, uidOf } from './helpers';

// Luogo scelto, lista e mappa devono muoversi insieme. Il centro si legge dai data-* della mappa.
const BOLOGNA = { lat: 44.4939, lng: 11.3428 };

async function mapCenter(page: Page) {
	const map = page.getByRole('region', { name: 'Mappa degli eventi' });
	await expect(map).toHaveAttribute('data-lat', /\d/);
	return {
		lat: Number(await map.getAttribute('data-lat')),
		lng: Number(await map.getAttribute('data-lng')),
		zoom: Number(await map.getAttribute('data-zoom'))
	};
}

test('da loggato, cambiare città sposta lista e mappa (regressione: il profilo ripristinava la zona vecchia)', async ({ page }) => {
	await signInByEmail(page, 'mappa@example.org', '/');
	// Utente che torna: il profilo ha già una zona (Modena, salvata al primo accesso).
	const uid = await uidOf(page);
	await expect.poll(async () => (await getDocument(`users/${uid}`))?.fields.homePlace).toBeTruthy();
	await page.reload();
	await page.getByRole('tab', { name: 'Mappa' }).click();
	const before = await mapCenter(page);
	expect(before.lat).toBeCloseTo(44.6471, 1);

	await page.getByRole('button', { name: /Modena/ }).click();
	const dialog = page.getByRole('dialog', { name: 'Dove cerchi eventi?' });
	await dialog.getByLabel('Oppure scegli la regione').selectOption({ label: 'Emilia-Romagna' });
	await dialog.getByRole('button', { name: /Bologna/ }).click();

	await expect(dialog).toBeHidden();
	await expect(page.getByRole('button', { name: /^Bologna/ })).toBeVisible();
	await expect.poll(async () => (await mapCenter(page)).lat, { timeout: 5000 }).toBeCloseTo(BOLOGNA.lat, 1);
	expect((await mapCenter(page)).lng).toBeCloseTo(BOLOGNA.lng, 1);
	// Resta lì (l'effetto del profilo non deve riportarla a Modena).
	await page.waitForTimeout(1500);
	expect((await mapCenter(page)).lat).toBeCloseTo(BOLOGNA.lat, 1);
});
