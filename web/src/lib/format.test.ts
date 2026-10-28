import { describe, expect, it } from 'vitest';
import { fmtNum } from './format';

describe('fmtNum', () => {
	it('separa le migliaia con il punto, anche a quattro cifre', () => {
		expect(fmtNum(1234)).toBe('1.234');
		expect(fmtNum(12)).toBe('12');
		expect(fmtNum(1234567)).toBe('1.234.567');
	});
});
