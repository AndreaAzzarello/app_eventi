// Tutti i comuni italiani (src/lib/data/comuni.json, generato da tools/importer/build_comuni.py): normalizzazione, punteggio
// e unione con la copertura. Puro: il file JSON lo importa il chiamante (il browser al primo focus, il server solo per ?luogo=).
import { slugify } from './event';
import type { ChosenPlace } from './geo';
import type { CoverageRegion } from './places';

/** Riga del file: [nome, nome altra lingua|'', sigla, indice regione, lat, lng, popolazione, slug|'' (se diverso da slugify(nome))]. */
export interface RawComuni {
	v: number;
	regioni: string[];
	c: (string | number)[][];
}

export interface Comune {
	name: string;
	/** Nome nell'altra lingua ufficiale (Bozen, Aoste). */
	alt: string;
	province: string;
	region: string;
	lat: number;
	lng: number;
	pop: number;
	slug: string;
	/** Eventi nella copertura (0 se il comune non è coperto). */
	events: number;
	/** Nomi normalizzati (nome, alias, "nome alias") nella forma piena e in quella con "S." per San/Santa… */
	full: string[];
	short: string[];
}

/** Senza accenti, minuscolo; apostrofi, punti e trattini diventano spazi ("Reggio nell'Emilia" = "reggio nell emilia"). */
export const fold = (s: string) =>
	s
		.normalize('NFD')
		.replace(/[̀-ͯ]/g, '')
		.toLowerCase()
		.replace(/['’`´.-]/g, ' ')
		.replace(/\s+/g, ' ')
		.trim();

const SAINT = new Set(['san', 'santa', 'santo', 'sant', 'santi', 'ss', 's']);
/** "san giovanni" → "s giovanni": "S. Giovanni", "Sant'Angelo" e "San Giovanni" si equivalgono. Parte dal testo già normalizzato. */
export const shorten = (folded: string) =>
	folded
		.split(' ')
		.map((t) => (SAINT.has(t) ? 's' : t))
		.join(' ');

/** 0 esatto, 1 prefisso, 2 inizio di parola, 3 contenuto; null se non corrisponde. `n` e `q` già normalizzati. */
export function foldedScore(n: string, q: string): number | null {
	if (n === q) return 0;
	if (n.startsWith(q)) return 1;
	if (n.includes(` ${q}`)) return 2;
	return n.includes(q) ? 3 : null;
}

/** Il punteggio migliore del comune per il testo (forma piena con forma piena, abbreviata con abbreviata). */
export function scoreComune(c: Comune, q: string, qShort: string): number | null {
	let best: number | null = null;
	for (let i = 0; i < c.full.length; i++)
		for (const s of [foldedScore(c.full[i], q), foldedScore(c.short[i], qShort)])
			if (s !== null && (best === null || s < best)) best = s;
	return best;
}

function makeComune(name: string, alt: string, province: string, region: string, lat: number, lng: number, pop: number, slug: string, events = 0): Comune {
	const full = (alt ? [name, alt, `${name} ${alt}`] : [name]).map(fold);
	return { name, alt, province, region, lat, lng, pop, slug, events, full, short: full.map(shorten) };
}

export function decodeComuni(raw: RawComuni): Comune[] {
	return raw.c.map((r) => makeComune(r[0] as string, r[1] as string, r[2] as string, raw.regioni[r[3] as number], r[4] as number, r[5] as number, r[6] as number, (r[7] as string) || slugify(r[0] as string)));
}

/**
 * Dataset + copertura: ai comuni con eventi si aggiungono numero di eventi e slug della copertura (i link esistenti non cambiano).
 * Chiave: nome (slug) e sigla. Un comune coperto che il dataset non ha resta in elenco.
 */
export function withCoverage(list: Comune[], regions: CoverageRegion[]): Comune[] {
	if (!list.length) return [];
	const covered = new Map<string, { slug: string; events: number }>();
	for (const r of regions) for (const c of r.comuni) covered.set(`${slugify(c.name)}|${c.province}`, { slug: c.slug, events: c.events });
	const seen = new Set<string>();
	const merged = list.map((c) => {
		const key = `${slugify(c.name)}|${c.province}`;
		const hit = covered.get(key);
		if (!hit) return c;
		seen.add(key);
		return { ...c, slug: hit.slug, events: hit.events };
	});
	for (const r of regions)
		for (const c of r.comuni)
			if (!seen.has(`${slugify(c.name)}|${c.province}`)) merged.push(makeComune(c.name, c.alt ?? '', c.province, r.name, c.lat, c.lng, 0, c.slug, c.events));
	return merged;
}

export const comunePlace = (c: Comune): ChosenPlace => ({ lat: c.lat, lng: c.lng, label: c.name, slug: c.slug, region: c.region });

/**
 * Il comune del file con questo slug, senza decodificare tutto il file (lo usa il server: pochi millisecondi di CPU).
 * Il confronto parte dalla prima lettera, che nei nomi dei comuni coincide con quella dello slug (verificato dal test su tutto il file).
 */
export function comuneBySlug(raw: RawComuni, slug: string): ChosenPlace | null {
	for (const r of raw.c) {
		const name = r[0] as string;
		const own = (r[7] as string) || (name[0].toLowerCase() === slug[0] ? slugify(name) : '');
		if (own === slug)
			return { lat: r[4] as number, lng: r[5] as number, label: name, slug, region: raw.regioni[r[3] as number] };
	}
	return null;
}
