import { expect, test } from '@playwright/test';
import { getDocument, signInByEmail, uidOf } from './helpers';

// Primo accesso: nessuna posizione salvata, geolocalizzazione non concessa, schermo da 360 px.
test.use({ storageState: { cookies: [], origins: [] }, viewport: { width: 360, height: 740 } });

const noOverflow = (page: import('@playwright/test').Page) =>
	page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth);

test('senza posizione si sceglie regione e comune, non si parte da Modena', async ({ page }) => {
	await page.goto('/');
	const dialog = page.getByRole('dialog', { name: 'Dove cerchi eventi?' });
	await expect(dialog).toBeVisible();
	const box = await dialog.boundingBox();
	expect(box!.x).toBeGreaterThanOrEqual(0);
	expect(box!.x + box!.width).toBeLessThanOrEqual(360);
	// La home dietro non mostra gli eventi di Modena come se fossero i suoi.
	await expect(page.getByRole('link', { name: 'Jazz in Piazza Grande' })).toHaveCount(0);

	await dialog.getByLabel('Oppure scegli la regione').selectOption({ label: 'Emilia-Romagna' });
	await dialog.getByLabel('Cerca il comune').fill('formig');
	await expect(dialog.getByRole('button', { name: /Modena/ })).toHaveCount(0);
	await dialog.getByRole('button', { name: /Formigine/ }).click();

	await expect(dialog).toBeHidden();
	await expect(page.getByRole('button', { name: /Formigine/ })).toBeVisible();
	await expect(page.getByRole('link', { name: /Letture animate/ })).toBeVisible();
	expect(await noOverflow(page)).toBe(true);
	const saved = await page.evaluate(() => JSON.parse(localStorage.getItem('ev:place')!));
	expect(saved).toMatchObject({ label: 'Formigine', slug: 'formigine', region: 'Emilia-Romagna' });

	// Al ritorno la scelta resta: niente dialogo.
	await page.reload();
	await expect(page.getByRole('button', { name: /Formigine/ })).toBeVisible();
	await expect(page.getByRole('dialog')).toBeHidden();
});

test('chiudendo la scelta resta un invito a sceglierla', async ({ page }) => {
	await page.goto('/');
	await page.getByRole('dialog').getByRole('button', { name: 'Chiudi' }).click();
	await expect(page.getByRole('heading', { name: 'Dove cerchi eventi?', level: 2 })).toBeVisible();
	await page.getByRole('button', { name: 'Scegli la zona' }).last().click();
	await expect(page.getByRole('dialog')).toBeVisible();
});

test('pagina regione e breadcrumb della città', async ({ page }) => {
	await page.goto('/regione/emilia-romagna');
	await expect(page.getByRole('heading', { level: 1, name: 'Eventi in Emilia-Romagna' })).toBeVisible();
	await expect(page.getByRole('link', { name: /Modena/ })).toBeVisible();
	expect(await noOverflow(page)).toBe(true);

	await page.goto('/regione/lombardia');
	await expect(page.getByText('Como, Lecco')).toBeVisible();

	expect((await page.goto('/regione/inesistente'))!.status()).toBe(404);

	await page.goto('/citta/modena');
	await page.getByRole('navigation', { name: 'Percorso' }).getByRole('link', { name: 'Emilia-Romagna' }).click();
	await expect(page).toHaveURL(/\/regione\/emilia-romagna$/);

	const xml = await (await page.request.get('/sitemap.xml')).text();
	expect(xml).toContain('/regione/emilia-romagna');
});

test('la zona scelta va nel profilo al login e si ritrova su un altro dispositivo', async ({ page, browser }) => {
	await page.goto('/');
	const dialog = page.getByRole('dialog', { name: 'Dove cerchi eventi?' });
	await dialog.getByLabel('Oppure scegli la regione').selectOption({ label: 'Emilia-Romagna' });
	await dialog.getByRole('button', { name: /Bologna/ }).click();

	await signInByEmail(page, 'zona@example.org', '/');
	const uid = await uidOf(page);
	await expect.poll(async () => (await getDocument(`users/${uid}`))?.fields.homePlace).toBeTruthy();
	const stored = (await getDocument(`users/${uid}`))!.fields.homePlace as { mapValue: { fields: Record<string, { stringValue?: string }> } };
	expect(stored.mapValue.fields.label.stringValue).toBe('Bologna');

	// Altro dispositivo: nessun localStorage, stesso account → la zona del profilo, senza dialogo.
	const other = await browser.newContext({ storageState: { cookies: [], origins: [] }, viewport: { width: 360, height: 740 } });
	const page2 = await other.newPage();
	await signInByEmail(page2, 'zona@example.org', '/');
	await expect(page2.getByRole('button', { name: /Bologna/ })).toBeVisible();
	await expect(page2.getByRole('dialog')).toBeHidden();
	await other.close();
});
