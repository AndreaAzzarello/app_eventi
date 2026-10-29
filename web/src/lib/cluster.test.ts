import { describe, expect, it } from 'vitest';
import { clusterPoints } from './cluster';

// Proiezione di prova: 1 grado = 10 pixel
const project = (p: { lat: number; lng: number }) => ({ x: p.lng * 10, y: p.lat * 10 });
const pt = (id: string, lat: number, lng: number) => ({ id, lat, lng });

describe('clusterPoints', () => {
	it('i punti vicini fanno un gruppo con il centro medio, quelli lontani restano soli', () => {
		const out = clusterPoints([pt('a', 1, 1), pt('b', 1.5, 1.5), pt('c', 10, 10)], project, 40);
		expect(out.map((c) => c.items.map((i) => i.id))).toEqual([['a', 'b'], ['c']]);
		expect(out[0]).toMatchObject({ lat: 1.25, lng: 1.25 });
		expect(out[1]).toMatchObject({ lat: 10, lng: 10 });
	});

	it('punti identici stanno nello stesso gruppo a qualunque zoom', () => {
		const out = clusterPoints([pt('a', 44.6, 10.9), pt('b', 44.6, 10.9)], (p) => ({ x: p.lng * 1e6, y: p.lat * 1e6 }), 40);
		expect(out).toHaveLength(1);
		expect(out[0].items).toHaveLength(2);
	});

	it('più zoom (più pixel per grado) separa i gruppi', () => {
		const list = [pt('a', 1, 1), pt('b', 1.5, 1.5)];
		expect(clusterPoints(list, project, 40)).toHaveLength(1);
		expect(clusterPoints(list, (p) => ({ x: p.lng * 100, y: p.lat * 100 }), 40)).toHaveLength(2);
	});

	it('lista vuota', () => expect(clusterPoints([], project, 40)).toEqual([]));
});
