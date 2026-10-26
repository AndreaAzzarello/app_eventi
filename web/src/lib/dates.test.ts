import { describe, expect, it } from 'vitest';
import { formatWhen, fromLocalInput, romeParts, romeTime, shortDay, toLocalInput, windowRange } from './dates';

describe('ora italiana', () => {
	it('romeTime regge ora legale e solare', () => {
		expect(new Date(romeTime(2026, 7, 15, 21, 0)).toISOString()).toBe('2026-07-15T19:00:00.000Z');
		expect(new Date(romeTime(2026, 12, 15, 21, 0)).toISOString()).toBe('2026-12-15T20:00:00.000Z');
		// giorno del cambio d'ora (25 ottobre 2026): mezzanotte è ancora CEST
		expect(new Date(romeTime(2026, 10, 25)).toISOString()).toBe('2026-10-24T22:00:00.000Z');
	});
	it('romeParts', () =>
		expect(romeParts(Date.parse('2026-10-31T23:30:00Z'))).toMatchObject({ month: 11, day: 1, hour: 0, weekday: 0 }));
	it('datetime-local andata e ritorno', () => {
		const ms = romeTime(2026, 3, 29, 10, 30);
		expect(toLocalInput(ms)).toBe('2026-03-29T10:30');
		expect(fromLocalInput('2026-03-29T10:30')).toBe(ms);
		expect(fromLocalInput('')).toBeNaN();
	});
});

describe('finestre', () => {
	const wed = romeTime(2026, 10, 28, 15); // mercoledì
	const sun = romeTime(2026, 11, 1, 15); // domenica
	it('oggi', () => expect(windowRange('today', wed)).toEqual([romeTime(2026, 10, 28), romeTime(2026, 10, 29)]));
	it('weekend da mercoledì', () =>
		expect(windowRange('weekend', wed)).toEqual([romeTime(2026, 10, 31), romeTime(2026, 11, 2)]));
	it('weekend di domenica è quello in corso', () =>
		expect(windowRange('weekend', sun)).toEqual([romeTime(2026, 10, 31), romeTime(2026, 11, 2)]));
	it('qualsiasi', () => expect(windowRange('any', wed)).toBeNull());
});

describe('formattazione', () => {
	const now = romeTime(2026, 10, 28, 9);
	it('stesso giorno con orario', () =>
		expect(formatWhen(romeTime(2026, 11, 14, 21), romeTime(2026, 11, 14, 23, 30), now)).toBe(
			'sabato 14 novembre · 21:00–23:30'
		));
	it('tutto il giorno', () =>
		expect(formatWhen(romeTime(2026, 11, 14), romeTime(2026, 11, 14, 23, 59), now)).toBe(
			'sabato 14 novembre · tutto il giorno'
		));
	it('più giorni', () =>
		expect(formatWhen(romeTime(2026, 11, 12, 10), romeTime(2026, 11, 15, 18), now)).toBe('dal 12 nov al 15 nov'));
	it('anno diverso', () => expect(formatWhen(romeTime(2027, 1, 6, 10), romeTime(2027, 1, 6, 12), now)).toMatch(/2027/));
	it('oggi, domani, in corso', () => {
		expect(shortDay(romeTime(2026, 10, 28, 20), now)).toBe('Oggi');
		expect(shortDay(romeTime(2026, 10, 29, 20), now)).toBe('Domani');
		expect(shortDay(romeTime(2026, 10, 20, 20), now)).toBe('Oggi');
	});
});
