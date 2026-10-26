import { distanceBetween, geohashForLocation, geohashQueryBounds } from 'geofire-common';
import { slugify } from './event';

export interface LatLng {
	lat: number;
	lng: number;
}

export const RADII_KM = [10, 25, 50, 100] as const;
export const DEFAULT_RADIUS_KM = 25;
/** Centro di partenza finché l'utente non sceglie: i dati iniziali sono nel modenese. */
export const DEFAULT_PLACE = { lat: 44.6471, lng: 10.9252, label: 'Modena' };

export const distanceKm = (a: LatLng, b: LatLng) => distanceBetween([a.lat, a.lng], [b.lat, b.lng]);
export const geohashOf = (p: LatLng) => geohashForLocation([p.lat, p.lng]);

/** Intervalli di geohash [inizio, fine] che coprono il cerchio: una query Firestore ciascuno. */
export const radiusBounds = (c: LatLng, km: number) => geohashQueryBounds([c.lat, c.lng], km * 1000);

/** Griglia di 0,05° (~5 km) per la cache delle ricerche: chi è vicino condivide la stessa risposta. */
export const snapCoord = (n: number) => Math.round(n * 20) / 20;
/** Margine da aggiungere al raggio quando si interroga dal punto della griglia (metà diagonale ≈ 3,5 km). */
export const SNAP_MARGIN_KM = 4;

export interface Place {
	city: string;
	citySlug: string;
	province: string;
	region: string;
}

/** Risposta Nominatim con addressdetails=1 → comune, sigla provincia, regione. */
export function placeFromNominatim(address: Record<string, string> | undefined): Place | null {
	if (!address) return null;
	const city =
		address.city || address.town || address.village || address.municipality || address.hamlet || '';
	if (!city) return null;
	const iso = address['ISO3166-2-lvl6'] || '';
	return {
		city,
		citySlug: slugify(city),
		province: iso.startsWith('IT-') ? iso.slice(3) : '',
		region: address.state || ''
	};
}
