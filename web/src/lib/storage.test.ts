import { describe, expect, it } from 'vitest';
import { mergeFavorites, readJson, writeJson } from './storage';

describe('mergeFavorites', () => {
	it('carica solo i locali mancanti', () =>
		expect(mergeFavorites(['a', 'b', 'b', 'c'], ['c', 'd'])).toEqual({
			toUpload: ['a', 'b'],
			merged: ['c', 'd', 'a', 'b']
		}));
	it('niente locali', () => expect(mergeFavorites([], ['x'])).toEqual({ toUpload: [], merged: ['x'] }));
});

describe('storage senza localStorage', () => {
	it('non lancia e usa il fallback', () => {
		expect(readJson('x', 42)).toBe(42); // in Node localStorage non esiste
		expect(() => writeJson('x', 1)).not.toThrow();
	});
});
