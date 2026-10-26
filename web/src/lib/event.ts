// Modello Event: stessi campi della versione Flutter + geohash e località normalizzate.
// I limiti coincidono con firebase/firestore.rules (validEventFields).

export const CATEGORIES = {
	music: 'Musica',
	food: 'Cibo e sagre',
	sport: 'Sport',
	culture: 'Cultura',
	kids: 'Bambini',
	market: 'Mercati',
	other: 'Altro'
} as const;
export type Category = keyof typeof CATEGORIES;

export const PRICE_TYPES = { free: 'Gratis', low: 'Economico', premium: 'A pagamento' } as const;
export type PriceType = keyof typeof PRICE_TYPES;

export const LIMITS = {
	title: 200,
	shortDescription: 1000,
	venueName: 200,
	address: 300,
	url: 500,
	tags: 10,
	tag: 30,
	city: 80
} as const;

/** Campi modificabili da form (admin e proposte). */
export interface EventInput {
	title: string;
	shortDescription: string;
	category: Category;
	priceType: PriceType;
	startTime: number; // ms epoch
	endTime: number;
	venueName: string;
	address: string;
	lat: number;
	lng: number;
	imageUrl: string;
	ticketUrl: string;
	tags: string[];
	geohash: string;
	city: string;
	citySlug: string;
	province: string; // sigla, es. "MO"
	region: string;
}

export interface Event extends EventInput {
	id: string;
	source: 'manual' | 'scraper' | 'user';
	sourceUrl: string;
	createdAt?: number;
	updatedAt?: number;
}

const str = (v: unknown, fallback = '') => (v == null ? fallback : String(v));
const num = (v: unknown) => (typeof v === 'number' ? v : Number(v) || 0);

/** Documento Firestore → Event. Ignora i campi interni (submittedBy). Default come Event.fromMap in Dart. */
export function fromData(id: string, m: Record<string, unknown>): Event {
	const start = num(m.startTime);
	const category = str(m.category, 'other');
	const priceType = str(m.priceType, 'free');
	const source = str(m.source, 'manual');
	return {
		id,
		title: str(m.title),
		shortDescription: str(m.shortDescription),
		category: (category in CATEGORIES ? category : 'other') as Category,
		priceType: (priceType in PRICE_TYPES ? priceType : 'free') as PriceType,
		startTime: start,
		endTime: m.endTime == null ? start : num(m.endTime),
		venueName: str(m.venueName),
		address: str(m.address),
		lat: num(m.lat),
		lng: num(m.lng),
		imageUrl: safeUrl(str(m.imageUrl)),
		ticketUrl: safeUrl(str(m.ticketUrl)),
		tags: Array.isArray(m.tags) ? m.tags.map((t) => String(t)) : [],
		geohash: str(m.geohash),
		city: str(m.city),
		citySlug: str(m.citySlug),
		province: str(m.province),
		region: str(m.region),
		source: (['manual', 'scraper', 'user'].includes(source) ? source : 'manual') as Event['source'],
		sourceUrl: safeUrl(str(m.sourceUrl)),
		createdAt: m.createdAt == null ? undefined : num(m.createdAt),
		updatedAt: m.updatedAt == null ? undefined : num(m.updatedAt)
	};
}

/** Solo link http(s) assoluti; tutto il resto diventa stringa vuota. */
export function safeUrl(s: string): string {
	try {
		const u = new URL(s.trim());
		return (u.protocol === 'https:' || u.protocol === 'http:') && u.host ? u.href : '';
	} catch {
		return '';
	}
}

export const isFree = (e: Pick<Event, 'priceType'>) => e.priceType === 'free';
export const isForKids = (e: Pick<Event, 'category' | 'tags'>) =>
	e.category === 'kids' || e.tags.includes('kids') || e.tags.includes('family');

export function slugify(s: string): string {
	return s
		.normalize('NFD')
		.replace(/[̀-ͯ]/g, '')
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, '-')
		.replace(/^-+|-+$/g, '')
		.slice(0, 70)
		.replace(/-+$/, '');
}

/** /eventi/titolo-dell-evento-<id>: l'id sta dopo l'ultimo "-" (gli id Firestore non ne contengono). */
export const eventPath = (e: Pick<Event, 'id' | 'title'>) =>
	`/eventi/${slugify(e.title) || 'evento'}-${e.id}`;
export const idFromSlug = (slug: string) => slug.slice(slug.lastIndexOf('-') + 1);
export const cityPath = (citySlug: string) => `/citta/${citySlug}`;

/** "Live, outdoor , ,kids" → [live, outdoor, kids], minuscoli e senza doppioni (come parseTags in Dart). */
export const parseTags = (raw: string) => [
	...new Set(
		raw
			.split(',')
			.map((t) => t.trim().toLowerCase())
			.filter(Boolean)
	)
];

export type EventErrors = Partial<Record<keyof EventInput | 'place', string>>;

/** Validazione del form: messaggi in italiano, vuoto = valido. Rispecchia le regole Firestore. */
export function validateEvent(e: EventInput): EventErrors {
	const err: EventErrors = {};
	const required = (k: 'title' | 'address', max: number) => {
		const v = e[k].trim();
		if (!v) err[k] = 'Campo obbligatorio';
		else if (v.length > max) err[k] = `Massimo ${max} caratteri`;
	};
	required('title', LIMITS.title);
	required('address', LIMITS.address);
	if (e.shortDescription.length > LIMITS.shortDescription)
		err.shortDescription = `Massimo ${LIMITS.shortDescription} caratteri`;
	if (e.venueName.length > LIMITS.venueName) err.venueName = `Massimo ${LIMITS.venueName} caratteri`;
	if (!(e.category in CATEGORIES)) err.category = 'Scegli una categoria';
	if (!(e.priceType in PRICE_TYPES)) err.priceType = 'Scegli un prezzo';
	if (!Number.isInteger(e.startTime) || e.startTime <= 0) err.startTime = 'Data di inizio non valida';
	if (!Number.isInteger(e.endTime) || e.endTime <= 0) err.endTime = 'Data di fine non valida';
	else if (e.endTime < e.startTime) err.endTime = "La fine deve essere dopo l'inizio";
	for (const k of ['imageUrl', 'ticketUrl'] as const) {
		const v = e[k].trim();
		if (v && (!safeUrl(v) || v.length > LIMITS.url)) err[k] = 'Inserisci un link che inizi con https://';
	}
	if (e.tags.length > LIMITS.tags) err.tags = `Massimo ${LIMITS.tags} tag`;
	else if (e.tags.some((t) => t.length > LIMITS.tag)) err.tags = `Ogni tag al massimo ${LIMITS.tag} caratteri`;
	const badCoords =
		!Number.isFinite(e.lat) ||
		!Number.isFinite(e.lng) ||
		(e.lat === 0 && e.lng === 0) ||
		Math.abs(e.lat) > 90 ||
		Math.abs(e.lng) > 180;
	if (badCoords || e.geohash.length < 5) err.place = 'Imposta la posizione: cerca l’indirizzo o sposta il segnaposto';
	else if (!e.city.trim() || !e.citySlug) err.place = 'Non riesco a capire il comune: sposta il segnaposto';
	return err;
}
