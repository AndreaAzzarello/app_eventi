import { describe, expect, it } from 'vitest';
import { comuneBySlug, decodeComuni, fold, shorten, withCoverage, type RawComuni } from './comuni';
import raw from './data/comuni.json';
import { slugify } from './event';
import { rankPlaces, strongPlace, type CoverageRegion } from './places';

const data = raw as unknown as RawComuni;
const all = decodeComuni(data);
const rank = (q: string, regions: CoverageRegion[] = [], limit = 6) => rankPlaces(q, regions, limit, withCoverage(all, regions));
const names = (q: string, regions: CoverageRegion[] = []) => rank(q, regions).map((h) => `${h.place.label} ${h.detail}`.trim());

describe('normalizzazione', () => {
	it('accenti, apostrofi, punti, trattini e maiuscole', () => {
		expect(fold("Sant'Agata de' Goti")).toBe('sant agata de goti');
		expect(fold('S.Giovanni')).toBe('s giovanni');
		expect(fold('Castel-San  Pietro')).toBe('castel san pietro');
		expect(fold('FORLÌ')).toBe('forli');
	});
	it('San, Santa, Sant, SS e "S." sono la stessa cosa', () => {
		for (const t of ['san giovanni', 'santa giovanni', 'sant giovanni', 'ss giovanni', 's giovanni']) expect(shorten(t)).toBe('s giovanni');
		expect(shorten('sandro')).toBe('sandro');
	});
});

describe('file dei comuni', () => {
	it('tutti i comuni, slug unici', () => {
		expect(all.length).toBeGreaterThanOrEqual(7800);
		expect(new Set(all.map((c) => c.slug)).size).toBe(all.length);
	});
	it('la prima lettera del nome è quella dello slug (ipotesi di comuneBySlug)', () => {
		for (const c of all) expect(slugify(c.name)[0], c.name).toBe(c.name[0].toLowerCase());
	});
	it('comuneBySlug trova anche omonimi, apostrofi e comuni piccoli', () => {
		expect(comuneBySlug(data, 'samone-to')).toMatchObject({ label: 'Samone', region: 'Piemonte', slug: 'samone-to' });
		expect(comuneBySlug(data, 'samone-tn')).toMatchObject({ label: 'Samone', region: 'Trentino-Alto Adige' });
		expect(comuneBySlug(data, 'l-aquila')?.label).toBe('L\'Aquila');
		expect(comuneBySlug(data, 'bolzano')).toMatchObject({ label: 'Bolzano' });
		expect(comuneBySlug(data, 'samone')).toBeNull(); // ambiguo: serve la sigla
		expect(comuneBySlug(data, 'non-esiste')).toBeNull();
	});
});

describe('ricerca su tutti i comuni', () => {
	it('trova un comune piccolo senza eventi', () => {
		expect(names('samone')).toEqual(['Samone (TO)', 'Samone (TN)']); // senza eventi: il più popoloso prima
	});
	it('omonimi: due voci con slug diversi', () => {
		const hits = rank('samone');
		expect(hits.map((h) => h.place.slug).sort()).toEqual(['samone-tn', 'samone-to']);
	});
	it('nomi bilingui: Bozen → Bolzano, Aoste → Aosta, Meran → Merano', () => {
		expect(rank('bozen')[0].place.label).toBe('Bolzano');
		expect(rank('aoste')[0].place.label).toBe('Aosta');
		expect(rank('Meran')[0]).toMatchObject({ detail: 'Meran (BZ)', place: { label: 'Merano' } });
	});
	it('tollera accenti, apostrofi, trattini e abbreviazioni', () => {
		expect(rank('forli')[0].place.label).toBe('Forlì');
		expect(rank("reggio nell'emilia")[0].place.label).toBe("Reggio nell'Emilia");
		expect(rank('sant angelo lodigiano')[0].place.label).toBe("Sant'Angelo Lodigiano");
		expect(names('S. Giovanni in Persiceto')[0]).toBe('San Giovanni in Persiceto (BO)');
		expect(names('s.giovanni in persiceto')[0]).toBe('San Giovanni in Persiceto (BO)');
		expect(rank('san giovanni in pers')[0].place.label).toBe('San Giovanni in Persiceto');
	});
	it('ordine: esatto, poi eventi, poi abitanti, poi alfabetico', () => {
		const regions: CoverageRegion[] = [
			{ slug: 'trentino-alto-adige', name: 'Trentino-Alto Adige', comuni: [{ name: 'Samone', slug: 'samone', province: 'TN', lat: 46.08, lng: 11.52, events: 3 }] }
		];
		expect(names('samone', regions)).toEqual(['Samone (TN)', 'Samone (TO)']); // Samone TN ha eventi, anche se è più piccolo
		// esatto prima di prefisso: Torino prima di Torino di Sangro
		expect(rank('torino')[0].place.label).toBe('Torino');
		// esatto prima di prefisso, anche se il prefisso ha più abitanti
		expect(rank('roma')[0].place.label).toBe('Roma');
		// a parità di tutto, alfabetico
		const tie = [
			{ ...all[0], name: 'Beta', full: ['beta'], short: ['beta'], pop: 10, events: 0 },
			{ ...all[0], name: 'Alfa', full: ['alfa'], short: ['alfa'], pop: 10, events: 0 }
		];
		expect(rankPlaces('al', [], 6, tie).length).toBe(1);
		expect(rankPlaces('a', [], 6, tie)).toEqual([]);
		const both = tie.map((c) => ({ ...c, full: ['xx ' + c.full[0]], short: ['xx ' + c.short[0]] }));
		expect(rankPlaces('xx', [], 6, both).map((h) => h.place.label)).toEqual(['Alfa', 'Beta']);
	});
	it('un comune con eventi porta lo slug e il conteggio della copertura', () => {
		const regions: CoverageRegion[] = [
			{ slug: 'emilia-romagna', name: 'Emilia-Romagna', comuni: [{ name: 'Modena', slug: 'modena', province: 'MO', lat: 44.6458, lng: 10.9256, events: 30 }] }
		];
		const [hit] = rank('modena', regions);
		expect(hit).toMatchObject({ kind: 'comune', events: 30, place: { slug: 'modena', label: 'Modena' } });
		// un comune coperto che il file non ha resta cercabile
		const extra: CoverageRegion[] = [{ slug: 'x', name: 'Altrove', comuni: [{ name: 'Nuovissimo', slug: 'nuovissimo', province: 'XX', lat: 44, lng: 11, events: 2 }] }];
		expect(rank('nuovissimo', extra)[0]).toMatchObject({ events: 2, place: { slug: 'nuovissimo' } });
	});
	it('strongPlace usa lo stesso elenco', () => {
		expect(strongPlace('samone', [], withCoverage(all, []))?.place.label).toBe('Samone');
		expect(strongPlace('samon', [], withCoverage(all, []))?.place.label).toBe('Samone');
		expect(strongPlace('zzzz', [], withCoverage(all, []))).toBeNull();
	});
	it('un testo di una lettera non cerca', () => {
		expect(rank('s')).toEqual([]);
	});
});
