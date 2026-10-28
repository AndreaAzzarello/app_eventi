import { expect, test } from '@playwright/test';

// Comuni bilingui: nome ufficiale italiano nell'URL, ricerca e pagine che trovano anche l'alias (Bozen, Aoste).
test.use({ storageState: { cookies: [], origins: [] }, viewport: { width: 360, height: 740 } });

for (const c of [
	{ region: 'Trentino-Alto Adige', slug: 'bolzano', name: 'Bolzano', alt: 'Bozen', query: 'bozen', event: 'Mercatino di Natale' },
	{ region: "Valle d'Aosta", slug: 'aosta', name: 'Aosta', alt: 'Aoste', query: 'aoste', event: 'Concerto al Teatro Romano' }
]) {
	test(`${c.name} / ${c.alt}: scelta regione → comune, pagina città e alias`, async ({ page }) => {
		await page.goto('/');
		const dialog = page.getByRole('dialog', { name: 'Dove cerchi eventi?' });
		await dialog.getByLabel('Oppure scegli la regione').selectOption({ label: c.region });
		// l'alias trova il comune, che si mostra con entrambi i nomi
		await dialog.getByLabel('Cerca il comune').fill(c.query);
		await dialog.getByRole('button', { name: new RegExp(`${c.name} / ${c.alt}`) }).click();
		await expect(dialog).toBeHidden();
		const saved = await page.evaluate(() => JSON.parse(localStorage.getItem('ev:place')!));
		expect(saved).toMatchObject({ label: c.name, slug: c.slug, region: c.region });

		await page.goto(`/citta/${c.slug}`);
		await expect(page.getByRole('heading', { level: 1, name: `Eventi a ${c.name} / ${c.alt}` })).toBeVisible();
		await expect(page.getByText(c.event)).toBeVisible();

		// l'indirizzo con l'alias porta a quello canonico
		await page.goto(`/citta/${c.alt.toLowerCase()}`);
		await expect(page).toHaveURL(new RegExp(`/citta/${c.slug}$`));

		const regionSlug = c.region.toLowerCase().replace(/[^a-z]+/g, '-');
		await page.goto(`/regione/${regionSlug}`);
		await expect(page.getByRole('link', { name: new RegExp(`${c.name} / ${c.alt}`) })).toBeVisible();
		const xml = await (await page.request.get('/sitemap.xml')).text();
		expect(xml).toContain(`/regione/${regionSlug}`);
	});
}
