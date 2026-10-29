import { afterEach, describe, expect, it, vi } from 'vitest';
import { PER_CELL_LIMIT, eventsNear } from './firestore';

vi.mock('$env/dynamic/private', () => ({ env: {} }));
vi.mock('$env/dynamic/public', () => ({ env: { PUBLIC_FIREBASE_PROJECT_ID: 'p', PUBLIC_FIREBASE_API_KEY: 'k' } }));

const center = { lat: 44.65, lng: 10.93 };
const H = 3_600_000;

// Doc Firestore REST di prova; geohash in ordine inverso rispetto alla fine, così il vecchio taglio per geohash li perderebbe.
const doc = (i: number, endTime: number) => ({
	name: `projects/p/databases/(default)/documents/events/e${i}`,
	fields: {
		title: { stringValue: `e${i}` },
		startTime: { integerValue: String(endTime - H) },
		endTime: { integerValue: String(endTime) },
		lat: { doubleValue: center.lat },
		lng: { doubleValue: center.lng },
		geohash: { stringValue: `srbj${String(9999 - i).padStart(4, '0')}` }
	}
});

/** Finto Firestore: applica orderBy e limit della query come farebbe il server. */
function fakeFirestore(docs: ReturnType<typeof doc>[]) {
	const queries: { orderBy: string[]; limit: number; long: boolean }[] = [];
	vi.stubGlobal(
		'fetch',
		vi.fn(async (_url: string, init: { body: string }) => {
			if (!init?.body) return new Response('{}', { status: 404 }); // bundles/coverage assente: si usano le query
			const q = JSON.parse(init.body).structuredQuery;
			const orderBy: string[] = q.orderBy.map((o: { field: { fieldPath: string } }) => o.field.fieldPath);
			// Filtro longRunning == true: il finto server restituisce solo i documenti con il flag.
			const filters: { fieldFilter: { field: { fieldPath: string } } }[] = q.where.compositeFilter
				? q.where.compositeFilter.filters
				: [q.where];
			const long = filters.some((x) => x.fieldFilter.field.fieldPath === 'longRunning');
			queries.push({ orderBy, limit: q.limit, long });
			const pool = long
				? docs.filter((d) => (d.fields as Record<string, { booleanValue?: boolean }>).longRunning?.booleanValue)
				: docs;
			const val = (d: ReturnType<typeof doc>, k: string) => {
				const v = (d.fields as Record<string, { stringValue?: string; integerValue?: string }>)[k];
				return v.stringValue ?? Number(v.integerValue);
			};
			const rows = [...pool]
				.sort((a, b) => {
					for (const k of orderBy) {
						const [x, y] = [val(a, k), val(b, k)];
						if (x !== y) return x < y ? -1 : 1;
					}
					return 0;
				})
				.slice(0, q.limit)
				.map((document) => ({ document }));
			return new Response(JSON.stringify(rows));
		})
	);
	return queries;
}

afterEach(() => vi.unstubAllGlobals());

describe('eventsNear: cella densa', () => {
	it('il limite per cella tiene gli eventi più imminenti, non i primi per geohash', async () => {
		const now = Date.now();
		const dense = Array.from({ length: PER_CELL_LIMIT * 2 }, (_, i) => doc(i, now + (i + 1) * H));
		// Il più imminente ha il geohash "ultimo": col vecchio ordine sarebbe stato tagliato.
		const queries = fakeFirestore(dense);
		const ids = (await eventsNear(center, 1.234)).map((e) => e.id);
		expect(queries.filter((q) => !q.long).every((q) => q.limit === PER_CELL_LIMIT && q.orderBy[0] === 'endTime')).toBe(true);
		expect(ids).toContain('e0');
		expect(ids).toContain(`e${PER_CELL_LIMIT - 1}`);
		expect(ids).not.toContain(`e${PER_CELL_LIMIT}`);
		// L'ordine finale resta per inizio crescente.
		expect(ids.slice(0, 3)).toEqual(['e0', 'e1', 'e2']);
	});
});

describe('eventsNear: mostre in una cella densa', () => {
	it('una mostra che finisce tardi non viene tagliata dal limite per cella', async () => {
		const now = Date.now();
		const dense = Array.from({ length: PER_CELL_LIMIT * 2 }, (_, i) => doc(i, now + (i + 1) * H));
		// Come "Robert Doisneau in mostra a Modena": finisce tra mesi, dopo tutti gli altri.
		const mostra = doc(9000, now + 120 * 24 * H);
		(mostra.fields as Record<string, unknown>).longRunning = { booleanValue: true };
		fakeFirestore([...dense, mostra]);
		const ids = (await eventsNear(center, 2.345)).map((e) => e.id);
		expect(ids).toContain('e9000');
		expect(ids).not.toContain(`e${PER_CELL_LIMIT}`); // i puntuali restano limitati
	});

	it('senza indice la lista funziona comunque (solo la query lunga fallisce)', async () => {
		const now = Date.now();
		const base = fakeFirestore([doc(1, now + H)]);
		const ok = globalThis.fetch;
		vi.stubGlobal('fetch', vi.fn(async (url: string, init: { body: string }) =>
			init?.body?.includes('longRunning') ? new Response('missing index', { status: 400 }) : ok(url, init)));
		void base;
		expect((await eventsNear(center, 3.456)).map((e) => e.id)).toEqual(['e1']);
	});
});

describe('eventi rimossi dalla fonte', () => {
	it('un evento con removedAt non compare nei risultati', async () => {
		const gone = doc(1, Date.now() + H);
		(gone.fields as Record<string, unknown>).removedAt = { integerValue: String(Date.now()) };
		fakeFirestore([gone, doc(2, Date.now() + 2 * H)]);
		const ids = (await eventsNear({ lat: 44.65, lng: 10.93 }, 5)).map((e) => e.id);
		expect(ids).toEqual(['e2']);
	});
});

describe('coverage', () => {
	const regionDoc = (slug: string, comuni: unknown[]) => ({
		name: `projects/p/databases/(default)/documents/coverage/${slug}`,
		fields: {
			name: { stringValue: slug === 'lombardia' ? 'Lombardia' : 'Emilia-Romagna' },
			comuni: {
				arrayValue: {
					values: comuni.map((c) => ({
						mapValue: {
							fields: Object.fromEntries(
								Object.entries(c as Record<string, string | number>).map(([k, v]) => [
									k,
									typeof v === 'string' ? { stringValue: v } : { integerValue: String(v) }
								])
							)
						}
					}))
				}
			}
		}
	});

	it('legge le regioni con una richiesta, chiave API dopo il parametro già presente', async () => {
		const urls: string[] = [];
		vi.stubGlobal(
			'fetch',
			vi.fn(async (url: string) => {
				urls.push(url);
				if (url.includes('/bundles/')) return new Response('{}', { status: 404 }); // bundle assente: ripiego sui documenti per regione
				return new Response(
					JSON.stringify({
						documents: [
							regionDoc('lombardia', [{ name: 'Lecco', slug: 'lecco', province: 'LC', lat: 45, lng: 9, events: 3 }]),
							regionDoc('emilia-romagna', [])
						]
					})
				);
			})
		);
		vi.resetModules();
		const { coverage, readCount } = await import('./firestore');
		const before = readCount;
		const regions = await coverage();
		expect(regions.map((r) => r.slug)).toEqual(['emilia-romagna', 'lombardia']); // ordinate per nome
		expect(regions[1].comuni[0]).toMatchObject({ name: 'Lecco', events: 3 });
		expect(urls).toHaveLength(2);
		expect(urls[1]).toMatch(/\/coverage\?pageSize=50&key=k$/);
		await coverage(); // dalla cache: nessuna nuova richiesta
		expect(urls).toHaveLength(2);
		expect((await import('./firestore')).readCount - before).toBe(3); // il bundle assente, poi una lettura per regione
	});

	it('regionCoverage: 404 → null, slug non valido senza richiesta', async () => {
		const fetchMock = vi.fn(async () => new Response('{}', { status: 404 }));
		vi.stubGlobal('fetch', fetchMock);
		vi.resetModules();
		const { regionCoverage } = await import('./firestore');
		expect(await regionCoverage('inesistente')).toBeNull();
		expect(await regionCoverage('../eventi')).toBeNull();
		expect(fetchMock).toHaveBeenCalledTimes(2); // bundle assente, poi il documento della regione
	});
});
