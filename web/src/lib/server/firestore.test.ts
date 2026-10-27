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
	const queries: { orderBy: string[]; limit: number }[] = [];
	vi.stubGlobal(
		'fetch',
		vi.fn(async (_url: string, init: { body: string }) => {
			const q = JSON.parse(init.body).structuredQuery;
			const orderBy: string[] = q.orderBy.map((o: { field: { fieldPath: string } }) => o.field.fieldPath);
			queries.push({ orderBy, limit: q.limit });
			const val = (d: ReturnType<typeof doc>, k: string) => {
				const v = (d.fields as Record<string, { stringValue?: string; integerValue?: string }>)[k];
				return v.stringValue ?? Number(v.integerValue);
			};
			const rows = [...docs]
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
		expect(queries.every((q) => q.limit === PER_CELL_LIMIT && q.orderBy[0] === 'endTime')).toBe(true);
		expect(ids).toContain('e0');
		expect(ids).toContain(`e${PER_CELL_LIMIT - 1}`);
		expect(ids).not.toContain(`e${PER_CELL_LIMIT}`);
		// L'ordine finale resta per inizio crescente.
		expect(ids.slice(0, 3)).toEqual(['e0', 'e1', 'e2']);
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
