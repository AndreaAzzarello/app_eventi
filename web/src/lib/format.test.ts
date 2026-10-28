import { describe, expect, it } from 'vitest';
import { fmtNum, monthKeys, monthLine } from './format';

describe('fmtNum', () => {
	it('separa le migliaia con il punto, anche a quattro cifre', () => {
		expect(fmtNum(1234)).toBe('1.234');
		expect(fmtNum(12)).toBe('12');
		expect(fmtNum(1234567)).toBe('1.234.567');
	});
});

describe('mesi', () => {
	const keys = { cur: '2026-11', prev: '2026-10' };

	it('chiavi del mese corrente e precedente a ora di Roma', () => {
		expect(monthKeys(new Date('2026-11-15T10:00:00Z'))).toEqual(keys);
		expect(monthKeys(new Date('2026-12-31T23:30:00Z'))).toEqual({ cur: '2027-01', prev: '2026-12' }); // già 1 gennaio a Roma
		expect(monthKeys(new Date('2026-01-10T10:00:00Z')).prev).toBe('2025-12');
	});

	it('riga di confronto in testo semplice', () => {
		expect(monthLine(412, 374, keys)).toBe('412 eventi a novembre · +38 rispetto a ottobre');
		expect(monthLine(1200, 1500, keys)).toBe('1.200 eventi a novembre · −300 rispetto a ottobre');
		expect(monthLine(5, 5, keys)).toBe('5 eventi a novembre · stesso numero rispetto a ottobre');
		expect(monthLine(1, null, keys)).toBe('1 evento a novembre');
		expect(monthLine(3, 2, { cur: '2026-04', prev: '2026-03' })).toBe('3 eventi ad aprile · +1 rispetto a marzo');
	});
});
