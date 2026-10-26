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
	ev('lontano', { lat: 41.9, lng: 12.5 }),
	ev('sagra', { title: 'Sagra del Gnocco Fritto', category: 'food', tags: ['family'], startTime: romeTime(2026, 10, 28, 19) })
];
const origin = { lat: 44.6471, lng: 10.9252 };
const ids = (f: Partial<Filter>) => applyFilter(events, { ...EMPTY_FILTER, ...f }, now, origin).map((e) => e.id);

describe('applyFilter', () => {
	it('esclude finiti e lontani, ordina per inizio', () => expect(ids({})).toEqual(['sagra', 'stasera', 'sabato', 'bimbi']));
	it('oggi', () => expect(ids({ when: 'today' })).toEqual(['sagra', 'stasera']));
	it('weekend', () => expect(ids({ when: 'weekend' })).toEqual(['sabato']));
	it('gratis', () => expect(ids({ free: true })).toEqual(['sabato']));
	it('bambini (categoria o tag family)', () => expect(ids({ kids: true })).toEqual(['sagra', 'bimbi']));
	it('categoria', () => expect(ids({ category: 'food' })).toEqual(['sagra']));
	it('ricerca senza accenti', () => expect(ids({ q: 'gnòcco' })).toEqual(['sagra']));
	it('Roma resta fuori anche a 100 km', () => expect(ids({ radiusKm: 100 })).not.toContain('lontano'));
	it('senza origine niente filtro di distanza', () =>
		expect(applyFilter(events, EMPTY_FILTER, now, null).map((e) => e.id)).toContain('lontano'));
});

describe('URL', () => {
	it('andata e ritorno', () => {
		const f: Filter = { q: 'jazz', when: 'weekend', free: true, kids: true, category: 'music', radiusKm: 50 };
		expect(filterFromParams(filterToParams(f))).toEqual(f);
		expect(filterToParams(EMPTY_FILTER).toString()).toBe('');
	});
	it('valori sconosciuti tornano ai default', () =>
		expect(filterFromParams(new URLSearchParams('cat=party&r=7&quando=ieri'))).toEqual(EMPTY_FILTER));
});
