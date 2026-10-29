import { describe, expect, it } from 'vitest';
import { EMPTY_FILTER } from './filters';
import {
	fold,
	homeUrl,
	nearCovered,
	nearestComune,
	placeFromParams,
	placeToParams,
	popularPlaces,
	rankPlaces,
	regionCenter,
	strongPlace,
	type CoverageRegion
} from './places';

const REGIONS: CoverageRegion[] = [
	{
		slug: 'emilia-romagna',
		name: 'Emilia-Romagna',
		comuni: [
			{ name: 'Modena', slug: 'modena', province: 'MO', lat: 44.6458, lng: 10.9256, events: 30 },
			{ name: 'Bologna', slug: 'bologna', province: 'BO', lat: 44.4939, lng: 11.3428, events: 10 },
			{ name: "Reggio nell'Emilia", slug: 'reggio-nell-emilia', province: 'RE', lat: 44.698, lng: 10.63, events: 5 },
			{ name: 'Forlì', slug: 'forli', province: 'FC', lat: 44.22, lng: 12.04, events: 0 }
		]
	},
	{
		slug: 'trentino-alto-adige',
		name: 'Trentino-Alto Adige',
		comuni: [
			{ name: 'Bolzano', slug: 'bolzano', alt: 'Bozen', province: 'BZ', lat: 46.4983, lng: 11.3548, events: 4 },
			{ name: 'Trento', slug: 'trento', province: 'TN', lat: 46.0679, lng: 11.1211, events: 0 }
		]
	}
];
const labels = (q: string) => rankPlaces(q, REGIONS).map((h) => h.place.label);

describe('fold', () => {
	it('toglie accenti, maiuscole, apostrofi e trattini', () => {
		expect(fold('Forlì')).toBe('forli');
		expect(fold("Reggio nell'Emilia")).toBe('reggio nell emilia');
		expect(fold('Reggio nell’Emilia')).toBe('reggio nell emilia');
		expect(fold('  Emilia-Romagna ')).toBe('emilia romagna');
	});
});

describe('rankPlaces', () => {
	it('non cerca sotto i due caratteri', () => expect(labels('b')).toEqual([]));
	it('è tollerante ad accenti e maiuscole', () => expect(labels('FORLI')).toEqual(['Forlì']));
	it('trova il nome bilingue: Bozen → Bolzano', () => {
		const [hit] = rankPlaces('bozen', REGIONS);
		expect(hit.place).toMatchObject({ label: 'Bolzano', slug: 'bolzano', region: 'Trentino-Alto Adige' });
		expect(hit.detail).toContain('Bozen');
	});
	it('gestisce gli apostrofi in entrambe le direzioni', () => {
		expect(labels("nell'emilia")).toContain("Reggio nell'Emilia");
		expect(labels('nell emilia')).toContain("Reggio nell'Emilia");
	});
	it('ordina: esatto, prefisso, contenuto; a parità più eventi', () => {
		expect(labels('emilia')[0]).toBe('Emilia-Romagna'); // prefisso batte il contenuto di "Reggio nell'Emilia"
		expect(labels('bo')).toEqual(['Bologna', 'Bolzano']); // stesso score: più eventi prima
		expect(labels('modena')[0]).toBe('Modena');
	});
	it('a pari punteggio il comune precede la regione', () => {
		const regions: CoverageRegion[] = [{ slug: 'lazio', name: 'Lazio', comuni: [{ name: 'Lazio', slug: 'lazio-c', province: '', lat: 41, lng: 12, events: 1 }] }];
		expect(rankPlaces('lazio', regions).map((h) => h.kind)).toEqual(['comune', 'regione']);
	});
	it('rispetta il limite', () => expect(rankPlaces('an', REGIONS, 1)).toHaveLength(1));
});

describe('strongPlace e popularPlaces', () => {
	it('strongPlace solo per esatto o prefisso', () => {
		expect(strongPlace('Bolzano', REGIONS)?.place.slug).toBe('bolzano');
		expect(strongPlace('olzan', REGIONS)).toBeNull(); // contenuto, non prefisso
		expect(strongPlace('concerto', REGIONS)).toBeNull();
	});
	it('popularPlaces ordina per eventi', () => {
		expect(popularPlaces(REGIONS, 2).map((h) => h.place.label)).toEqual(['Modena', 'Bologna']);
	});
});

describe('regionCenter e nearCovered', () => {
	it('regionCenter pesa sugli eventi e non si divide per zero', () => {
		const c = regionCenter(REGIONS[0]);
		expect(c.lat).toBeCloseTo(44.6, 0);
		expect(c.lng).toBeLessThan(11); // più vicino a Modena (30 eventi) che a Bologna
		const empty = regionCenter({ slug: 'x', name: 'X', comuni: [{ ...REGIONS[0].comuni[3] }, { ...REGIONS[0].comuni[3], lng: 14.04 }] });
		expect(empty.lng).toBeCloseTo(13.04, 1);
	});
	it('nearCovered ignora i comuni senza eventi', () => {
		expect(nearCovered({ lat: 44.65, lng: 10.93 }, REGIONS)).toBe(true);
		expect(nearCovered({ lat: 44.22, lng: 12.04 }, REGIONS)).toBe(false); // Forlì ha 0 eventi
		expect(nearCovered({ lat: 40.35, lng: 18.17 }, REGIONS)).toBe(false);
	});
});

describe('nearestComune', () => {
	it('sceglie il comune coperto più vicino entro 30 km', () => {
		expect(nearestComune({ lat: 44.6, lng: 10.9 }, REGIONS)).toMatchObject({ slug: 'modena', label: 'Modena' });
		expect(nearestComune({ lat: 44.5, lng: 11.3 }, REGIONS)?.slug).toBe('bologna');
	});
	it('niente oltre il raggio: nessun comune, nessun parametro', () => {
		expect(nearestComune({ lat: 40.35, lng: 18.17 }, REGIONS)).toBeNull(); // Lecce non è coperta
		expect(nearestComune({ lat: 44.9, lng: 10.0 }, REGIONS, 30)).toBeNull();
		expect(nearestComune({ lat: 44.6, lng: 10.9 }, [])).toBeNull();
	});
});

describe('luogo nell’URL', () => {
	const parse = (qs: string) => placeFromParams(new URLSearchParams(qs), REGIONS);
	it('risolve comuni e regioni coperti per slug', () => {
		expect(parse('luogo=bolzano')).toMatchObject({ label: 'Bolzano', slug: 'bolzano' });
		expect(parse('luogo=emilia-romagna')).toMatchObject({ label: 'Emilia-Romagna', slug: 'emilia-romagna' });
		expect(parse('luogo=sconosciuto')).toBeNull();
		expect(parse('luogo=../etc')).toBeNull();
	});
	it('accetta coordinate italiane e rifiuta il resto', () => {
		expect(parse('nome=Lecce&lat=40.35&lng=18.17')).toEqual({ lat: 40.35, lng: 18.17, label: 'Lecce' });
		expect(parse('lat=40.35&lng=18.17')?.label).toBe('La tua posizione');
		expect(parse('lat=0&lng=0')).toBeNull();
		expect(parse('lat=abc&lng=10')).toBeNull();
		expect(parse('lat=44')).toBeNull();
		expect(parse('')).toBeNull();
	});
	it('taglia il nome a 80 caratteri', () => expect(parse(`nome=${'a'.repeat(200)}&lat=44&lng=11`)?.label).toHaveLength(80));
	it('andata e ritorno', () => {
		const bz = parse('luogo=bolzano')!;
		expect(placeToParams(bz).toString()).toBe('luogo=bolzano');
		const free = { lat: 40.3529, lng: 18.1743, label: 'Lecce' };
		expect(placeToParams(free).toString()).toBe('nome=Lecce&lat=40.35&lng=18.17');
	});
	it('la posizione del dispositivo non mette mai le coordinate nell’URL', () => {
		const exact = { lat: 44.60123, lng: 10.90456, label: 'La tua posizione', exact: true };
		expect(placeToParams(exact).toString()).toBe('');
		expect(homeUrl(EMPTY_FILTER, exact)).toBe('/');
		// con un comune coperto vicino resta solo lo slug
		const withComune = { ...exact, label: 'Vicino a Modena', slug: 'modena' };
		expect(homeUrl(EMPTY_FILTER, withComune)).toBe('/?luogo=modena');
		expect(homeUrl(EMPTY_FILTER, withComune)).not.toMatch(/44\.6|10\.9|lat=|lng=/);
	});
	it('homeUrl unisce luogo, filtri e vista', () => {
		expect(homeUrl(EMPTY_FILTER, null)).toBe('/');
		const bz = parse('luogo=bolzano')!;
		expect(homeUrl({ ...EMPTY_FILTER, q: 'mercatino', radiusKm: 50 }, bz, 'map')).toBe('/?luogo=bolzano&q=mercatino&r=50&vista=mappa');
	});
});
