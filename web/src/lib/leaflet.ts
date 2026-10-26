// Leaflet caricato solo quando una mappa entra in pagina (JS + CSS in un chunk separato).
export async function loadLeaflet() {
	const [L] = await Promise.all([import('leaflet'), import('leaflet/dist/leaflet.css')]);
	return L.default ?? L;
}

export type Leaflet = Awaited<ReturnType<typeof loadLeaflet>>;

// Tile standard di OpenStreetMap: gratuite, con attribuzione obbligatoria e uso moderato
// (https://operations.osmfoundation.org/policies/tiles/).
export const TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
export const ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

export function baseMap(L: Leaflet, el: HTMLElement, opts: { interactive?: boolean } = {}) {
	const interactive = opts.interactive ?? true;
	const map = L.map(el, {
		zoomControl: interactive,
		scrollWheelZoom: false,
		dragging: interactive,
		touchZoom: interactive,
		doubleClickZoom: interactive,
		keyboard: interactive,
		attributionControl: true
	});
	map.attributionControl.setPrefix(false);
	L.tileLayer(TILE_URL, { maxZoom: 19, attribution: ATTRIBUTION, crossOrigin: true }).addTo(map);
	return map;
}

export const cssVar = (name: string) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
