import { expect, test, type Page } from '@playwright/test';

// Ricerca su tutti i comuni italiani (file statico, nessuna lettura Firestore): comuni piccoli senza eventi, omonimi, nomi bilingui.
test.use({ storageState: { cookies: [], origins: [] }, viewport: { width: 360, height: 740 } });

const noOverflow = (page: Page) => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth);
const search = (page: Page) => page.getByRole('region', { name: 'Dove cerchi eventi?' }).getByRole('combobox');

test('comune piccolo senza eventi vicini: si allarga il raggio e lo si dice', async ({ page }) => {
	await page.goto('/');
	await search(page).fill('pavullo nel frig');
	await page.getByRole('option', { name: /Pavullo nel Frignano \(MO\)/ }).click();
	await expect(page).toHaveURL(/luogo=pavullo-nel-frignano/);
	await expect(page).toHaveURL(/r=50/); // il comune con eventi più vicino (Modena) è a ~35 km
	await expect(page.getByText('Nessun evento a Pavullo nel Frignano nei prossimi giorni.')).toBeVisible();
	await expect(page.getByText('Ti mostriamo gli eventi entro 50 km.')).toBeVisible();
	await expect(page.getByRole('link', { name: /Jazz in Piazza Grande/ })).toBeVisible();
	expect(await noOverflow(page)).toBe(true);
	expect(await page.evaluate(() => JSON.parse(localStorage.getItem('ev:place')!))).toMatchObject({ label: 'Pavullo nel Frignano', slug: 'pavullo-nel-frignano' });
});

test('omonimi: due voci distinte dalla sigla, ognuna col suo indirizzo', async ({ page }) => {
	await page.goto('/');
	await search(page).fill('samone');
	const options = page.getByRole('option');
	await expect(options).toHaveCount(2);
	await expect(page.getByRole('option', { name: /Samone \(TO\)/ })).toBeVisible();
	await expect(page.getByRole('option', { name: /Samone \(TN\)/ })).toBeVisible();
	expect(await noOverflow(page)).toBe(true);
	await page.getByRole('option', { name: /Samone \(TN\)/ }).click();
	await expect(page).toHaveURL(/luogo=samone-tn/);
	await expect(page.getByRole('button', { name: /^Samone/ })).toBeVisible();

	await page.goto('/?luogo=samone-to');
	await expect(page.getByRole('button', { name: /^Samone/ })).toBeVisible();
});

test('nome bilingue: Meran trova Merano, anche senza eventi', async ({ page }) => {
	await page.goto('/');
	await search(page).fill('Meran');
	await page.getByRole('option', { name: /Merano Meran \(BZ\)/ }).click();
	await expect(page).toHaveURL(/luogo=merano/);
	await expect(page.getByRole('button', { name: /^Merano/ })).toBeVisible();
	expect(await noOverflow(page)).toBe(true);
});

test('?luogo= di un comune senza eventi nemmeno a 100 km: messaggio e comuni più vicini', async ({ page }) => {
	await page.goto('/?luogo=lampedusa-e-linosa');
	await expect(page.getByRole('heading', { name: 'Nessun evento a Lampedusa e Linosa nei prossimi giorni' })).toBeVisible();
	await expect(page).not.toHaveURL(/r=/); // niente raggio che non serve a nulla
	const nearest = page.getByRole('button', { name: /· \d+ km$/ });
	await expect(nearest.first()).toBeVisible();
	expect(await noOverflow(page)).toBe(true);
	await nearest.first().click();
	await expect(page).toHaveURL(/luogo=/);
	await expect(page).not.toHaveURL(/lampedusa/);
});

test('luogo sconosciuto: invito a cercare, non Modena', async ({ page }) => {
	await page.goto('/?luogo=non-esiste-davvero');
	await expect(page.getByText(/Non trovo il luogo «non-esiste-davvero»/)).toBeVisible();
});

test('a 390 px la ricerca non sfora', async ({ page }) => {
	await page.setViewportSize({ width: 390, height: 844 });
	await page.goto('/');
	await search(page).fill('san giovanni');
	await expect(page.getByRole('option').first()).toBeVisible();
	expect(await noOverflow(page)).toBe(true);
});
