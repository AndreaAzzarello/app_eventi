import { describe, expect, it } from 'vitest';
import { romeTime } from './dates';
import { fromData } from './event';
import { EMPTY_FILTER, applyFilter, filterFromParams, filterToParams, type Filter } from './filters';

const now = romeTime(2026, 10, 28, 12); // mercoledì
const ev = (id: string, over: Record<string, unknown>) =>
	fromData(id, {
		title: id,
		startTime: romeTime(2026, 10, 28, 20),
		endTime: romeTime(2026, 10, 28, 23),
		lat: 44.65,
		lng: 10.93,
		category: 'music',
		priceType: 'low',
		...over
	});

const events = [
	ev('stasera', {}),
	ev('finito', { startTime: now - 7200_000, endTime: now - 3600_000 }),
	ev('sabato', { startTime: romeTime(2026, 10, 31, 10), endTime: romeTime(2026, 10, 31, 12), priceType: 'free' }),
	ev('bimbi', { category: 'kids', startTime: romeTime(2026, 11, 5, 10), endTime: romeTime(2026, 11, 5, 12) }),
	ev('mostra', { title: 'Mostra di foto', category: 'culture', startTime: now - 21 * 86400_000, endTime: romeTime(2026, 12, 20, 18) }),
	ev('lontano', { lat: 41.9, lng: 12.5 }),
	ev('sagra', { title: 'Sagra del Gnocco Fritto', category: 'food', tags: ['family'], startTime: romeTime(2026, 10, 28, 19) })
];
const origin = { lat: 44.6471, lng: 10.9252 };
const ids = (f: Partial<Filter>) => applyFilter(events, { ...EMPTY_FILTER, ...f }, now, origin).map((e) => e.id);

describe('applyFilter', () => {
	it('esclude finiti e lontani, ordina per inizio', () => expect(ids({})).toEqual(['sagra', 'stasera', 'mostra', 'sabato', 'bimbi']));
	it('oggi', () => expect(ids({ when: 'today' })).toEqual(['sagra', 'stasera', 'mostra']));
	it('weekend', () => expect(ids({ when: 'weekend' })).toEqual(['mostra', 'sabato']));
	it('gratis', () => expect(ids({ free: true })).toEqual(['sabato']));
	it('bambini (categoria o tag family)', () => expect(ids({ kids: true })).toEqual(['sagra', 'bimbi']));
	it('mostre ed eventi in corso', () => expect(ids({ running: true })).toEqual(['mostra']));
	it('ricerca e chip trovano una mostra lunga (caso Doisneau, Modena 25 km)', () => {
		const doisneau = ev('doisneau', {
			title: 'Robert Doisneau in mostra a Modena', category: 'culture',
			startTime: romeTime(2026, 9, 24, 10), endTime: romeTime(2027, 1, 24, 18)
		});
		expect(doisneau.longRunning).toBe(true); // ricavato dalla durata anche senza il flag
		const f = { ...EMPTY_FILTER, radiusKm: 25 };
		expect(applyFilter([doisneau], { ...f, q: 'Doisneau' }, now, origin)).toHaveLength(1);
		expect(applyFilter([doisneau], { ...f, running: true }, now, origin)).toHaveLength(1);
	});
	it('categoria', () => expect(ids({ category: 'food' })).toEqual(['sagra']));
	it('ricerca senza accenti', () => expect(ids({ q: 'gnòcco' })).toEqual(['sagra']));
	it('Roma resta fuori anche a 100 km', () => expect(ids({ radiusKm: 100 })).not.toContain('lontano'));
	it('senza origine niente filtro di distanza', () =>
		expect(applyFilter(events, EMPTY_FILTER, now, null).map((e) => e.id)).toContain('lontano'));
});

describe('URL', () => {
	it('andata e ritorno', () => {
		const f: Filter = { q: 'jazz', when: 'weekend', free: true, kids: true, running: true, category: 'music', radiusKm: 50 };
		expect(filterFromParams(filterToParams(f))).toEqual(f);
		expect(filterToParams(EMPTY_FILTER).toString()).toBe('');
	});
	it('valori sconosciuti tornano ai default', () =>
		expect(filterFromParams(new URLSearchParams('cat=party&r=7&quando=ieri'))).toEqual(EMPTY_FILTER));
	it('i vecchi link con cat=kids diventano il filtro rapido Bambini', () =>
		expect(filterFromParams(new URLSearchParams('cat=kids'))).toEqual({ ...EMPTY_FILTER, kids: true }));
});
