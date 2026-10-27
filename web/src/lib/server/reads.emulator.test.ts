// Letture Firestore per visita, misurate sull'emulatore con i dati di seed (scripts/seed-emulator.mjs).
// Si salta senza emulatore. Lancio: npm run test:reads
import { execFileSync } from 'node:child_process';
import { beforeAll, describe, expect, it, vi } from 'vitest';

const HOST = process.env.FIRESTORE_EMULATOR_HOST;

vi.mock('$env/dynamic/private', () => ({ env: { FIRESTORE_EMULATOR_HOST: process.env.FIRESTORE_EMULATOR_HOST } }));
vi.mock('$env/dynamic/public', () => ({ env: { PUBLIC_FIREBASE_PROJECT_ID: 'demo-eventi', PUBLIC_FIREBASE_API_KEY: 'k' } }));

type Query = { from: { collectionId: string }[]; where?: unknown; limit?: number };

describe.skipIf(!HOST)('letture per visita (emulatore)', () => {
	const queries: Query[] = [];

	beforeAll(() => {
		execFileSync('node', ['scripts/seed-emulator.mjs'], { env: process.env, stdio: 'ignore' });
		const real = globalThis.fetch;
		vi.stubGlobal('fetch', (url: string, init?: { body?: string }) => {
			if (init?.body) queries.push(JSON.parse(init.body).structuredQuery);
			return real(url, init as RequestInit);
		});
	});

	/** Letture di una chiamata: documenti restituiti (minimo 1 per query vuota) come li conta Firestore. */
	async function measure(label: string, fn: () => Promise<unknown>) {
		const { readCount } = await import('./firestore');
		const before = readCount;
		const q0 = queries.length;
		await fn();
		const after = (await import('./firestore')).readCount;
		console.log(`LETTURE ${label}: ${after - before} (${queries.length - q0} query)`);
		return { reads: after - before, queries: queries.slice(q0) };
	}

	it('home: tutte le query sono limitate al raggio (intervallo di geohash) e agli eventi non finiti', async () => {
		const { eventsNear } = await import('./firestore');
		const r = await measure('home (Modena, 25 km)', () => eventsNear({ lat: 44.65, lng: 10.93 }, 29));
		expect(r.queries.length).toBeGreaterThan(0);
		for (const q of r.queries) {
			const filters = JSON.stringify(q.where);
			expect(q.from[0].collectionId).toBe('events');
			expect(filters).toContain('"geohash"');
			expect(filters).toContain('GREATER_THAN_OR_EQUAL');
			expect(filters).toContain('LESS_THAN_OR_EQUAL');
			expect(filters).toContain('"endTime"');
			expect(q.limit).toBeGreaterThan(0);
		}
		// Nessuna scansione della collezione: poche query (intervalli di geohash × 2) e poche letture.
		expect(r.queries.length).toBeLessThanOrEqual(24);
		expect(r.reads).toBeLessThan(40);
	});

	it('pagina città, pagina regione, elenco comuni, evento', async () => {
		const f = await import('./firestore');
		const city = await measure('/citta/modena', () => f.eventsInCity('modena'));
		const region = await measure('/regione/emilia-romagna', () => f.regionCoverage('emilia-romagna'));
		const places = await measure('/api/places (scelta del luogo)', () => f.coverage());
		const event = await measure('/eventi/[slug]', () => f.getEvent('seedJazz'));
		expect(city.reads).toBeLessThan(10);
		expect(region.reads).toBe(1);
		expect(places.reads).toBe(2);
		expect(event.reads).toBe(1);
		// Seconda richiesta uguale: servita dalla cache in memoria, zero letture.
		expect((await measure('/regione (cache)', () => f.regionCoverage('emilia-romagna'))).reads).toBe(0);
	});
});
