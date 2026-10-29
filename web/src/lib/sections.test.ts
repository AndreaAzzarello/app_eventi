import { describe, expect, it } from 'vitest';
import { romeTime } from './dates';
import { sections } from './sections';

const ev = (id: string, start: number, endH = 2, longRunning = false) => ({
	id,
	startTime: start,
	endTime: start + endH * 3600_000,
	longRunning
});
const keys = (list: ReturnType<typeof sections<ReturnType<typeof ev>>>) => list.map((s) => `${s.key}:${s.events.map((e) => e.id).join(',')}`);

describe('sections', () => {
	const wed = romeTime(2026, 10, 28, 15); // mercoledì 15:00

	it('mercoledì: oggi, stasera, prossimi giorni, weekend, più avanti, in corso', () => {
		const list = [
			ev('mattina', romeTime(2026, 10, 28, 10), 8), // già iniziato, ancora in corso: oggi
			ev('pomeriggio', romeTime(2026, 10, 28, 16)),
			ev('sera', romeTime(2026, 10, 28, 21)),
			ev('giovedi', romeTime(2026, 10, 29, 10)),
			ev('sabato', romeTime(2026, 10, 31, 20)),
			ev('domenica', romeTime(2026, 11, 1, 11)),
			ev('lunedi', romeTime(2026, 11, 2, 11)),
			ev('mostra', romeTime(2026, 10, 1, 9), 24 * 60, true)
		];
		expect(keys(sections(list, wed))).toEqual([
			'today:mattina,pomeriggio',
			'tonight:sera',
			'soon:giovedi',
			'weekend:sabato,domenica',
			'later:lunedi',
			'running:mostra'
		]);
		expect(sections(list, wed).map((s) => s.title)).toEqual(['Oggi', 'Stasera', 'Prossimi giorni', 'Questo weekend', 'Più avanti', 'In corso']);
	});

	it('ogni evento sta in una sola sezione', () => {
		const list = [ev('a', romeTime(2026, 10, 28, 18)), ev('b', romeTime(2026, 10, 31, 9)), ev('c', romeTime(2026, 11, 20, 9))];
		expect(sections(list, wed).flatMap((s) => s.events).map((e) => e.id).sort()).toEqual(['a', 'b', 'c']);
	});

	it('sezioni vuote nascoste e lista vuota', () => {
		expect(sections([], wed)).toEqual([]);
		expect(keys(sections([ev('x', romeTime(2026, 10, 28, 19))], wed))).toEqual(['tonight:x']);
	});

	it('sabato: il resto del weekend è weekend, da lunedì "Prossimi giorni"', () => {
		const sat = romeTime(2026, 10, 31, 12);
		const list = [ev('oggi', romeTime(2026, 10, 31, 15)), ev('dom', romeTime(2026, 11, 1, 10)), ev('lun', romeTime(2026, 11, 2, 10))];
		const out = sections(list, sat);
		expect(keys(out)).toEqual(['today:oggi', 'weekend:dom', 'later:lun']);
		expect(out[2].title).toBe('Prossimi giorni');
	});

	it('domenica: il weekend in corso non apre una sezione dopo oggi', () => {
		const sun = romeTime(2026, 11, 1, 12);
		expect(keys(sections([ev('sera', romeTime(2026, 11, 1, 20)), ev('mar', romeTime(2026, 11, 3, 10))], sun))).toEqual(['tonight:sera', 'later:mar']);
	});

	it('venerdì: sabato è weekend e non c’è "Prossimi giorni"', () => {
		const fri = romeTime(2026, 10, 30, 12);
		expect(keys(sections([ev('sab', romeTime(2026, 10, 31, 10))], fri))).toEqual(['weekend:sab']);
	});

	it('una sagra iniziata ieri e ancora aperta (non lunga) è "Oggi"', () => {
		expect(keys(sections([ev('sagra', romeTime(2026, 10, 27, 20), 48)], wed))).toEqual(['today:sagra']);
	});

	it('cambio ora legale: la sera del 25 ottobre resta "Stasera"', () => {
		const sun = romeTime(2026, 10, 25, 9);
		expect(keys(sections([ev('sera', romeTime(2026, 10, 25, 18, 30))], sun))).toEqual(['tonight:sera']);
	});
});
