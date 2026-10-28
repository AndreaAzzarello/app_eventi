// Letture Firestore lato server via API REST pubblica: niente Admin SDK nel Worker.
// La collezione events è a lettura pubblica (firestore.rules), quindi basta la API key web.
import { env } from '$env/dynamic/private';
import { env as pub } from '$env/dynamic/public';
import { compareEvents, fromData, type Event } from '$lib/event';
import { distanceKm, radiusBounds, type LatLng } from '$lib/geo';

type Value = {
	stringValue?: string;
	integerValue?: string;
	doubleValue?: number;
	booleanValue?: boolean;
	timestampValue?: string;
	nullValue?: null;
	arrayValue?: { values?: Value[] };
	mapValue?: { fields?: Record<string, Value> };
};
type Doc = { name: string; fields?: Record<string, Value> };

export function decode(v: Value): unknown {
	if ('stringValue' in v) return v.stringValue;
	if ('integerValue' in v) return Number(v.integerValue);
	if ('doubleValue' in v) return v.doubleValue;
	if ('booleanValue' in v) return v.booleanValue;
	if ('timestampValue' in v) return Date.parse(v.timestampValue!);
	if ('arrayValue' in v) return (v.arrayValue!.values ?? []).map(decode);
	if ('mapValue' in v) return decodeFields(v.mapValue!.fields);
	return null;
}
const decodeFields = (f: Record<string, Value> = {}) =>
	Object.fromEntries(Object.entries(f).map(([k, v]) => [k, decode(v)]));
// removedAt: l'importer ha marcato l'evento come sparito dalla fonte (dopo 2 import); non si cancella subito.
const visible = (d: Doc) => !d.fields?.removedAt;
const toEvent = (d: Doc) => fromData(d.name.slice(d.name.lastIndexOf('/') + 1), decodeFields(d.fields));

function root() {
	const host = env.FIRESTORE_EMULATOR_HOST;
	const project = pub.PUBLIC_FIREBASE_PROJECT_ID;
	return {
		url: `${host ? `http://${host}` : 'https://firestore.googleapis.com'}/v1/projects/${project}/databases/(default)/documents`,
		name: `projects/${project}/databases/(default)/documents`,
		key: host ? '' : `key=${pub.PUBLIC_FIREBASE_API_KEY}`
	};
}

export let readCount = 0; // per i test e per la stima delle letture

async function call<T>(path: string, body?: unknown): Promise<T | null> {
	const r = root();
	const sep = path.includes('?') ? '&' : '?';
	const res = await fetch(`${r.url}${path}${r.key ? sep + r.key : ''}`, {
		method: body ? 'POST' : 'GET',
		headers: body ? { 'content-type': 'application/json' } : undefined,
		body: body ? JSON.stringify(body) : undefined
	});
	if (res.status === 404) return null;
	if (!res.ok) throw new Error(`Firestore ${res.status}: ${(await res.text()).slice(0, 300)}`);
	return res.json() as Promise<T>;
}

// Cache per isolate: copre le richieste ravvicinate anche dove la Cache API di Cloudflare non c'è.
// shortcut: memoria per singolo isolate, non condivisa tra data center; KV costerebbe scritture limitate.
const memo = new Map<string, { at: number; value: unknown }>();
const TTL_MS = 5 * 60_000; // i dati cambiano una volta al giorno (import) o a mano dall'admin
async function cached<T>(key: string, load: () => Promise<T>): Promise<T> {
	const hit = memo.get(key);
	if (hit && Date.now() - hit.at < TTL_MS) return hit.value as T;
	const value = await load();
	if (memo.size > 300) memo.delete(memo.keys().next().value!);
	memo.set(key, { at: Date.now(), value });
	return value;
}

type Filter = { fieldFilter: { field: { fieldPath: string }; op: string; value: Value } };
const f = (field: string, op: string, value: Value): Filter => ({
	fieldFilter: { field: { fieldPath: field }, op, value }
});
const int = (n: number): Value => ({ integerValue: String(n) });

async function runQuery(where: Filter[], orderBy: string[], limit: number): Promise<Event[]> {
	const rows = await call<{ document?: Doc }[]>(':runQuery', {
		structuredQuery: {
			from: [{ collectionId: 'events' }],
			where: where.length === 1 ? where[0] : { compositeFilter: { op: 'AND', filters: where } },
			orderBy: orderBy.map((fieldPath) => ({ field: { fieldPath }, direction: 'ASCENDING' })),
			limit
		}
	});
	const docs = (rows ?? []).flatMap((r) => (r.document ? [r.document] : []));
	readCount += Math.max(docs.length, 1); // una query vuota costa comunque una lettura
	return docs.filter(visible).map(toEvent);
}

/** Minuto corrente: rende stabili le chiavi di cache. */
const nowMinute = () => Math.floor(Date.now() / 60_000) * 60_000;

/** Esportato per i test. */
export const PER_CELL_LIMIT = 150;

/** Limite per la query dedicata agli eventi lunghi (mostre, rassegne): sono pochi rispetto ai puntuali. */
const LONG_LIMIT = 100;
const TRUE: Value = { booleanValue: true };

/**
 * Eventi longRunning: i limiti delle query ordinano per fine più vicina e in una cella densa taglierebbero
 * proprio le mostre che finiscono tardi. Query a parte; se l'indice non c'è ancora (firestore.indexes.json
 * non pubblicato) si degrada al comportamento precedente invece di rompere la lista.
 */
async function longRunningQuery(where: Filter[], orderBy: string[]): Promise<Event[]> {
	try {
		return await runQuery([...where, f('longRunning', 'EQUAL', TRUE)], orderBy, LONG_LIMIT);
	} catch (err) {
		console.warn('query longRunning non riuscita (indice mancante?):', err);
		return [];
	}
}

/** Eventi non finiti entro km dal centro: una query per intervallo di geohash, mai l'intera collezione. */
export function eventsNear(center: LatLng, km: number): Promise<Event[]> {
	return cached(`near:${center.lat},${center.lng},${km}`, async () => {
		const now = nowMinute();
		const batches = await Promise.all(
			radiusBounds(center, km).flatMap(([start, end]) => {
				const where = [
					f('geohash', 'GREATER_THAN_OR_EQUAL', { stringValue: start }),
					f('geohash', 'LESS_THAN_OR_EQUAL', { stringValue: end }),
					f('endTime', 'GREATER_THAN_OR_EQUAL', int(now))
				];
				return [
					// Cella densa: il limite taglia per fine più vicina (imminenti e in corso), non per geohash.
					// Richiede l'indice (endTime, geohash) in firestore.indexes.json.
					// shortcut: a parità di endTime vale il geohash, non la distanza vera dal centro.
					runQuery(where, ['endTime', 'geohash'], PER_CELL_LIMIT),
					// Indice (longRunning, endTime, geohash).
					longRunningQuery(where, ['endTime', 'geohash'])
				];
			})
		);
		const seen = new Set<string>();
		return batches
			.flat()
			.filter((e) => !seen.has(e.id) && seen.add(e.id) && distanceKm(center, e) <= km)
			.sort(compareEvents(now));
	});
}

export function eventsInCity(citySlug: string, limit = 100): Promise<Event[]> {
	return cached(`city:${citySlug}`, async () => {
		const where = [f('citySlug', 'EQUAL', { stringValue: citySlug }), f('endTime', 'GREATER_THAN_OR_EQUAL', int(nowMinute()))];
		// Indice (citySlug, longRunning, endTime) per la seconda query.
		const [list, long] = await Promise.all([runQuery(where, ['endTime'], limit), longRunningQuery(where, ['endTime'])]);
		const seen = new Set<string>();
		return [...list, ...long].filter((e) => !seen.has(e.id) && seen.add(e.id)).sort(compareEvents(Date.now()));
	});
}

export function upcomingEvents(limit: number): Promise<Event[]> {
	return cached(`upcoming:${limit}`, () =>
		runQuery([f('endTime', 'GREATER_THAN_OR_EQUAL', int(nowMinute()))], ['endTime'], limit)
	);
}

export interface CoverageComune {
	name: string;
	slug: string;
	province: string;
	lat: number;
	lng: number;
	events: number;
	/** Nome nell'altra lingua ufficiale (Bozen, Aoste), se il comune è bilingue. */
	alt?: string;
}
export interface Coverage {
	slug: string;
	name: string;
	comuni: CoverageComune[];
}

const toCoverage = (d: Doc): Coverage => {
	const f = decodeFields(d.fields) as Partial<Coverage>;
	return { slug: d.name.slice(d.name.lastIndexOf('/') + 1), name: f.name ?? '', comuni: f.comuni ?? [] };
};

/** Regioni coperte e loro comuni (scritto ogni giorno dall'importer): una lettura per regione, in cache 5 minuti. */
export function coverage(): Promise<Coverage[]> {
	return cached('coverage', async () => {
		const res = await call<{ documents?: Doc[] }>('/coverage?pageSize=50');
		const docs = res?.documents ?? [];
		readCount += Math.max(docs.length, 1);
		return docs.map(toCoverage).sort((a, b) => a.name.localeCompare(b.name, 'it'));
	});
}

export function regionCoverage(slug: string): Promise<Coverage | null> {
	if (!/^[a-z0-9-]{1,70}$/.test(slug)) return Promise.resolve(null);
	return cached(`region:${slug}`, async () => {
		readCount++;
		const doc = await call<Doc>(`/coverage/${slug}`);
		return doc ? toCoverage(doc) : null;
	});
}

export function getEvent(id: string): Promise<Event | null> {
	if (!/^[A-Za-z0-9_]{1,64}$/.test(id)) return Promise.resolve(null);
	return cached(`event:${id}`, async () => {
		readCount++;
		const doc = await call<Doc>(`/events/${id}`);
		return doc && visible(doc) ? toEvent(doc) : null;
	});
}

/** Più eventi per id in una richiesta (preferiti degli utenti non loggati). */
export async function getEvents(ids: string[]): Promise<Event[]> {
	const valid = ids.filter((id) => /^[A-Za-z0-9_]{1,64}$/.test(id)).slice(0, 100);
	if (!valid.length) return [];
	const r = root();
	const rows = await call<{ found?: Doc }[]>(':batchGet', {
		documents: valid.map((id) => `${r.name}/events/${id}`)
	});
	readCount += valid.length;
	return (rows ?? []).flatMap((x) => (x.found && visible(x.found) ? [toEvent(x.found)] : []));
}

export interface MonthStats {
	events: number;
	comuni: number;
}

/** Statistiche del mese corrente e del precedente di una regione (stats/{regione}_{AAAA-MM}, scritte dall'importer). */
export function monthStats(region: string, keys: { cur: string; prev: string }): Promise<{ cur: MonthStats | null; prev: MonthStats | null }> {
	if (!/^[a-z0-9-]{1,70}$/.test(region)) return Promise.resolve({ cur: null, prev: null });
	return cached(`stats:${region}:${keys.cur}`, async () => {
		const r = root();
		const names = [keys.cur, keys.prev].map((k) => `${r.name}/stats/${region}_${k}`);
		const rows = await call<{ found?: Doc }[]>(':batchGet', {
			documents: names,
			mask: { fieldPaths: ['events', 'comuni'] } // senza `ids`, che pesa decine di KB
		});
		readCount += names.length;
		const byName = new Map((rows ?? []).flatMap((x) => (x.found ? [[x.found.name, x.found] as const] : [])));
		const read = (n: string): MonthStats | null => {
			const f = byName.has(n) ? (decodeFields(byName.get(n)!.fields) as Partial<MonthStats>) : null;
			return f && typeof f.events === 'number' ? { events: f.events, comuni: f.comuni ?? 0 } : null;
		};
		return { cur: read(names[0]), prev: read(names[1]) };
	});
}
