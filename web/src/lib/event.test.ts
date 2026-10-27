import { describe, expect, it } from 'vitest';
import { eventPath, fromData, idFromSlug, parseTags, safeUrl, slugify, validateEvent, type EventInput } from './event';

const sample = (over: Partial<EventInput> = {}): EventInput => ({
	title: 'Concerto in piazza',
	shortDescription: '',
	category: 'music',
	priceType: 'free',
	startTime: 1_800_000_000_000,
	endTime: 1_800_003_600_000,
	venueName: 'Piazza Grande',
	address: 'Piazza Grande, Modena',
	lat: 44.6458,
	lng: 10.9256,
	imageUrl: '',
	ticketUrl: '',
	tags: [],
	geohash: 'srbj4w1t0q',
	city: 'Modena',
	citySlug: 'modena',
	province: 'MO',
	region: 'Emilia-Romagna',
	...over
});

describe('validateEvent', () => {
	it('evento completo valido', () => expect(validateEvent(sample())).toEqual({}));
	it.each([
		['title', { title: '  ' }, 'Campo obbligatorio'],
		['title', { title: 'x'.repeat(201) }, 'Massimo 200 caratteri'],
		['endTime', { endTime: 1_700_000_000_000 }, "La fine deve essere dopo l'inizio"],
		['ticketUrl', { ticketUrl: 'javascript:alert(1)' }, 'Inserisci un link che inizi con https://'],
		['imageUrl', { imageUrl: 'ftp://x.it/a.png' }, 'Inserisci un link che inizi con https://'],
		['tags', { tags: Array.from({ length: 11 }, (_, i) => `t${i}`) }, 'Massimo 10 tag']
	])('%s non valido', (field, over, msg) => {
		expect(validateEvent(sample(over as Partial<EventInput>))[field as keyof EventInput]).toBe(msg);
	});
	it('approxLocation: default false, true solo se booleano true', () => {
		expect(fromData('x', {}).approxLocation).toBe(false);
		expect(fromData('x', { approxLocation: 'true' }).approxLocation).toBe(false);
		expect(fromData('x', { approxLocation: true }).approxLocation).toBe(true);
	});
	it('coordinate mancanti o comune sconosciuto', () => {
		expect(validateEvent(sample({ lat: 0, lng: 0 })).place).toMatch(/posizione/);
		expect(validateEvent(sample({ geohash: '' })).place).toMatch(/posizione/);
		expect(validateEvent(sample({ city: '' })).place).toMatch(/comune/);
	});
});

describe('url e slug', () => {
	it('safeUrl accetta solo http(s)', () => {
		expect(safeUrl('https://a.it/x')).toBe('https://a.it/x');
		expect(safeUrl(' http://a.it ')).toBe('http://a.it/');
		expect(safeUrl('javascript:alert(1)')).toBe('');
		expect(safeUrl('data:text/html,x')).toBe('');
		expect(safeUrl('/relativo')).toBe('');
	});
	it('slugify toglie accenti e simboli', () => {
		expect(slugify("Sagra dell'Uva & Città Più Bella!")).toBe('sagra-dell-uva-citta-piu-bella');
		expect(slugify('Reggio nell’Emilia')).toBe('reggio-nell-emilia');
	});
	it('percorso evento e id', () => {
		const p = eventPath({ id: 'abc123XYZ', title: 'Festa di San Geminiano' });
		expect(p).toBe('/eventi/festa-di-san-geminiano-abc123XYZ');
		expect(idFromSlug(p.split('/')[2])).toBe('abc123XYZ');
	});
	it('parseTags', () => expect(parseTags('Live, outdoor , ,kids,live')).toEqual(['live', 'outdoor', 'kids']));
});

describe('fromData', () => {
	it('default come in Dart e campi interni ignorati', () => {
		const e = fromData('x', { title: 'T', startTime: 10, submittedBy: 'uid-segreto', ticketUrl: 'javascript:x' });
		expect(e).toMatchObject({ id: 'x', category: 'other', priceType: 'free', endTime: 10, source: 'manual', ticketUrl: '' });
		expect('submittedBy' in e).toBe(false);
	});
});
