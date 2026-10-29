import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('$env/dynamic/private', () => ({ env: {} }));
vi.mock('$env/dynamic/public', () => ({ env: { PUBLIC_FIREBASE_PROJECT_ID: 'p', PUBLIC_FIREBASE_API_KEY: 'k' } }));

const H = 3_600_000;
const center = { lat: 44.65, lng: 10.95 };
const row = (id: string) => [
	{
		document: {
			name: `projects/p/databases/(default)/documents/events/${id}`,
			fields: {
				title: { stringValue: id },
				startTime: { integerValue: String(Date.now() + H) },
				endTime: { integerValue: String(Date.now() + 2 * H) },
				lat: { doubleValue: center.lat },
				lng: { doubleValue: center.lng },
				geohash: { stringValue: 'srbj0000' }
			}
		}
	}
];

/** Cache API finta, condivisa tra "isolate" (i moduli ricaricati) come quella di un data center. */
const store = new Map<string, Response>();
const fakeCaches = {
	default: {
		match: async (r: Request) => store.get(r.url)?.clone(),
		put: async (r: Request, res: Response) => void store.set(r.url, res)
	}
};

let fetchMock: ReturnType<typeof vi.fn>;
let status = 200;
beforeEach(() => {
	store.clear();
	status = 200;
	vi.resetModules();
	vi.useFakeTimers({ toFake: ['Date'] });
	vi.stubGlobal('caches', fakeCaches);
	fetchMock = vi.fn(async () =>
		status === 200 ? new Response(JSON.stringify(row('e1'))) : new Response('quota', { status })
	);
	vi.stubGlobal('fetch', fetchMock);
});
afterEach(() => {
	vi.useRealTimers();
	vi.unstubAllGlobals();
});

describe('cache dei dati Firestore', () => {
	it('un altro isolate (moduli nuovi) legge dalla Cache API: zero richieste a Firestore', async () => {
		await (await import('./firestore')).eventsAround(center, 25);
		const calls = fetchMock.mock.calls.length;
		expect(calls).toBeGreaterThan(0);
		vi.resetModules();
		const again = await (await import('./firestore')).eventsAround(center, 25);
		expect(again.events[0].id).toBe('e1');
		expect(fetchMock.mock.calls.length).toBe(calls);
	});

	it('home e /api/events usano la stessa chiave: due punti vicini della stessa cella costano una volta sola', async () => {
		const f = await import('./firestore');
		const a = await f.eventsAround({ lat: 44.64, lng: 10.93 }, 25);
		const calls = fetchMock.mock.calls.length;
		const b = await f.eventsAround({ lat: 44.66, lng: 10.96 }, 25);
		expect(b.fetched).toEqual(a.fetched);
		expect(fetchMock.mock.calls.length).toBe(calls);
	});

	it('quota esaurita (429) dopo la scadenza: serve l’ultima copia e per 10 minuti non richiama Firestore', async () => {
		const f = await import('./firestore');
		await f.eventsAround(center, 25);
		vi.setSystemTime(Date.now() + 7 * H); // oltre la freschezza
		status = 429;
		fetchMock.mockClear();
		const stale = await f.eventsAround(center, 25);
		expect(stale.events[0].id).toBe('e1');
		const afterFail = fetchMock.mock.calls.length;
		expect(afterFail).toBeGreaterThan(0);
		await f.eventsAround(center, 25);
		expect(fetchMock.mock.calls.length).toBe(afterFail); // interruttore aperto
	});

	it('429 senza nessuna copia: l’errore arriva a chi chiama (la home mostra «riprova tra poco»)', async () => {
		status = 429;
		const f = await import('./firestore');
		await expect(f.eventsAround(center, 25)).rejects.toThrow('429');
	});

	it('429 sulla query degli eventi lunghi non diventa una lista vuota in cache', async () => {
		const f = await import('./firestore');
		fetchMock.mockImplementation(async (_u: string, init: { body: string }) =>
			init.body.includes('longRunning') ? new Response('quota', { status: 429 }) : new Response(JSON.stringify(row('e1')))
		);
		await expect(f.eventsAround(center, 25)).rejects.toThrow('429');
		expect(store.size).toBe(0);
	});
});
