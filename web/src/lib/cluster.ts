export interface Point {
	lat: number;
	lng: number;
}
export interface Cluster<T> {
	lat: number;
	lng: number;
	items: T[];
}

/**
 * Raggruppa i punti che a questo zoom cadrebbero nella stessa cella quadrata di `cell` pixel.
 * `project` porta un punto in pixel allo zoom corrente (per Leaflet: `map.project(latlng, zoom)`).
 * Il centro di un gruppo è la media dei suoi punti; i punti isolati restano gruppi da uno.
 * shortcut: griglia fissa, due punti a cavallo di una cella restano separati anche se vicini; basta per qualche centinaio di eventi.
 */
export function clusterPoints<T extends Point>(items: T[], project: (p: Point) => { x: number; y: number }, cell: number): Cluster<T>[] {
	const cells = new Map<string, T[]>();
	for (const item of items) {
		const { x, y } = project(item);
		const key = `${Math.floor(x / cell)}:${Math.floor(y / cell)}`;
		const list = cells.get(key);
		if (list) list.push(item);
		else cells.set(key, [item]);
	}
	return [...cells.values()].map((list) => ({
		lat: list.reduce((n, i) => n + i.lat, 0) / list.length,
		lng: list.reduce((n, i) => n + i.lng, 0) / list.length,
		items: list
	}));
}
