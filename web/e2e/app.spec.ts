import { expect, test } from '@playwright/test';
import { accountExists, getDocument, mockGeocode, signInByEmail } from './helpers';

test.describe.configure({ mode: 'serial' });

test('ricerca e filtri in home', async ({ page }) => {
	await page.goto('/');
	await expect(page.getByRole('heading', { level: 1 })).toContainText('vicino a te');
	await expect(page.getByRole('link', { name: 'Jazz in Piazza Grande' })).toBeVisible();
	// Lontani ed eventi finiti non compaiono.
	await expect(page.getByText('Festa del barocco leccese')).toHaveCount(0);
	await expect(page.getByText('Evento già concluso')).toHaveCount(0);

	await page.getByLabel('Cerca eventi').fill('gnocco');
	await expect(page.getByRole('link', { name: 'Sagra del gnocco fritto' })).toBeVisible();
	await expect(page.getByRole('link', { name: 'Jazz in Piazza Grande' })).toHaveCount(0);
	await expect(page).toHaveURL(/q=gnocco/);

	await page.getByLabel('Cerca eventi').fill('');
	await page.getByRole('button', { name: 'Bambini' }).click();
	await expect(page.getByRole('link', { name: /Letture animate/ })).toBeVisible();
	await expect(page.getByRole('link', { name: 'Jazz in Piazza Grande' })).toHaveCount(0);

	await page.getByRole('tab', { name: 'Mappa' }).click();
	await expect(page.getByRole('region', { name: 'Mappa degli eventi' })).toBeVisible();
});

test('dettaglio: SEO, calendario e condivisione', async ({ page, context }) => {
	await page.goto('/');
	await page.getByRole('link', { name: 'Jazz in Piazza Grande' }).click();
	await expect(page).toHaveURL(/\/eventi\/jazz-in-piazza-grande-seedJazz$/);
	await expect(page.getByRole('heading', { level: 1, name: 'Jazz in Piazza Grande' })).toBeVisible();
	await expect(page.locator('link[rel=canonical]')).toHaveAttribute('href', /jazz-in-piazza-grande-seedJazz$/);
	const ld = JSON.parse((await page.locator('script[type="application/ld+json"]').textContent())!);
	expect(ld).toMatchObject({ '@type': 'Event', name: 'Jazz in Piazza Grande' });
	expect(JSON.stringify(ld)).not.toContain('submittedBy');
	await expect(page.getByRole('link', { name: 'Biglietti' })).toHaveAttribute('href', 'https://example.org/biglietti');
	await expect(page.getByRole('link', { name: 'Comune di Modena' })).toBeVisible();

	const download = page.waitForEvent('download');
	await page.getByRole('button', { name: 'Aggiungi al calendario' }).click();
	const file = await download;
	expect(file.suggestedFilename()).toMatch(/\.ics$/);

	// Senza Web Share API: copia il link.
	await context.grantPermissions(['clipboard-read', 'clipboard-write']);
	await page.evaluate(() => Object.defineProperty(navigator, 'share', { value: undefined }));
	await page.getByRole('button', { name: 'Condividi' }).click();
	await expect(page.getByText('Link copiato negli appunti.')).toBeVisible();
});

test('slug sbagliato reindirizza al canonico, id inesistente dà 404', async ({ page }) => {
	await page.goto('/eventi/titolo-vecchio-seedJazz');
	await expect(page).toHaveURL(/jazz-in-piazza-grande-seedJazz$/);
	const res = await page.goto('/eventi/niente-zzzz');
	expect(res?.status()).toBe(404);
});

test('preferito senza account propone il login, che unisce i preferiti', async ({ page }) => {
	await page.goto('/');
	await page.getByRole('button', { name: /Aggiungi “Jazz in Piazza Grande” ai preferiti/ }).click();
	await expect(page.getByRole('link', { name: 'Accedi per non perderli' })).toBeVisible();
	await signInByEmail(page, 'mario@example.org', '/preferiti');
	await expect(page.getByRole('link', { name: 'Jazz in Piazza Grande' })).toBeVisible();
	const uid = await uidOf(page);
	await expect.poll(() => getDocument(`users/${uid}/favorites/seedJazz`)).not.toBeNull();
	// La copia locale viene svuotata dopo l'unione.
	expect(await page.evaluate(() => localStorage.getItem('ev:favorites'))).toBeNull();
});

test('proposta di un evento', async ({ page }) => {
	await mockGeocode(page);
	await signInByEmail(page, 'mario@example.org', '/proponi');
	await page.getByLabel('Titolo *').fill('Concerto di prova E2E');
	await page.getByLabel('Inizio *').fill('2030-05-10T21:00');
	await page.getByLabel('Fine').fill('2030-05-10T23:00');
	await page.getByLabel('Indirizzo *').fill('Via Emilia Centro 100, Modena');
	// Invio senza posizione: errore chiaro.
	await page.getByRole('button', { name: 'Invia la proposta' }).click();
	await expect(page.getByText('Controlla questi campi:')).toBeVisible();
	await page.getByRole('button', { name: 'Trova' }).click();
	await expect(page.getByText(/Trovato/)).toBeVisible();
	await page.getByLabel('Link biglietti o informazioni').fill('https://example.org/e2e');
	await page.getByRole('button', { name: 'Invia la proposta' }).click();
	await expect(page).toHaveURL(/\/account#proposte$/);
	await expect(page.getByText('Concerto di prova E2E')).toBeVisible();
	await expect(page.getByText('In revisione', { exact: true })).toBeVisible();
});

test('approvazione da parte dell’admin', async ({ page }) => {
	await signInByEmail(page, 'azzatubo@gmail.com', '/admin/proposte');
	await expect(page.getByRole('heading', { name: 'Proposte in attesa' })).toBeVisible();
	await expect(page.getByRole('heading', { name: 'Concerto di prova E2E' })).toBeVisible();
	await page.getByRole('button', { name: 'Approva' }).click();
	await expect(page.getByText('Pubblicato “Concerto di prova E2E”.')).toBeVisible();
	await page.getByRole('link', { name: 'Vedi' }).click();
	await expect(page.getByRole('heading', { level: 1, name: 'Concerto di prova E2E' })).toBeVisible();
	await expect(page.getByText('Segnalato da un utente')).toBeVisible();
	await expect(page.locator('body')).not.toContainText('mario@example.org');
});

test('un utente normale non entra in admin', async ({ page }) => {
	await signInByEmail(page, 'mario@example.org', '/admin');
	await expect(page.getByText('Questo account non ha i permessi di amministrazione.')).toBeVisible();
});

test('elimina account e dati', async ({ page }) => {
	await signInByEmail(page, 'mario@example.org', '/account');
	await expect(page.getByText('Pubblicata', { exact: true })).toBeVisible();
	const uid = await uidOf(page);
	await page.getByRole('button', { name: 'Elimina account e dati' }).click();
	await page.getByRole('button', { name: 'Sì, elimina tutto' }).click();
	await expect(page.getByText('Account e dati eliminati.')).toBeVisible();
	await expect(page).toHaveURL(/\/$/);
	expect(await getDocument(`users/${uid}`)).toBeNull();
	expect(await getDocument(`users/${uid}/favorites/seedJazz`)).toBeNull();
	expect(await accountExists('mario@example.org')).toBe(false);
});

async function uidOf(page: import('@playwright/test').Page): Promise<string> {
	return page.evaluate(async () => {
		const req = indexedDB.open('firebaseLocalStorageDb');
		const db: IDBDatabase = await new Promise((ok, ko) => ((req.onsuccess = () => ok(req.result)), (req.onerror = ko)));
		const all: { value: { uid: string } }[] = await new Promise((ok) => {
			const r = db.transaction('firebaseLocalStorage').objectStore('firebaseLocalStorage').getAll();
			r.onsuccess = () => ok(r.result);
		});
		return all.find((x) => x.value?.uid)!.value.uid;
	});
}
