import { describe, expect, it } from 'vitest';
import { distanceKm, geohashOf, placeFromNominatim, radiusBounds, roundCoord } from './geo';

describe('geo', () => {
	it('geohash di riferimento (stesso vettore del test Python)', () => {
		expect(geohashOf({ lat: 57.64911, lng: 10.40744 })).toBe('u4pruydqqv');
	});
	it('i bound coprono il centro e un punto a ~20 km', () => {
		const c = { lat: 44.6471, lng: 10.9252 };
		const near = { lat: 44.8, lng: 11.05 };
		expect(distanceKm(c, near)).toBeGreaterThan(15);
		const bounds = radiusBounds(c, 25);
		for (const p of [c, near]) {
			const h = geohashOf(p);
			expect(bounds.some(([s, e]) => h >= s && h <= e)).toBe(true);
		}
		expect(bounds.length).toBeLessThanOrEqual(9);
	});
	it('roundCoord a ~1 km', () => expect(roundCoord(44.64712)).toBe(44.65));
	it('località da Nominatim', () => {
		expect(
			placeFromNominatim({ town: 'Formigine', county: 'Modena', 'ISO3166-2-lvl6': 'IT-MO', state: 'Emilia-Romagna' })
		).toEqual({ city: 'Formigine', citySlug: 'formigine', province: 'MO', region: 'Emilia-Romagna' });
		expect(placeFromNominatim({ state: 'Lazio' })).toBeNull();
		expect(placeFromNominatim(undefined)).toBeNull();
	});
});
