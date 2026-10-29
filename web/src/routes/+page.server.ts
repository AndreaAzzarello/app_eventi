import { HTML_CACHE } from '$lib/server/cache';
import { filterFromParams } from '$lib/filters';
import { DEFAULT_PLACE, type ChosenPlace } from '$lib/geo';
import { placeFromParams } from '$lib/places';
import { coverage, eventsNear } from '$lib/server/firestore';
import type { PageServerLoad } from './$types';

// SSR sul luogo dell'URL (?luogo=slug oppure ?nome=&lat=&lng=) o, senza, sulla zona predefinita.
// I filtri si applicano nel browser; la posizione salvata dall'utente (solo nel suo localStorage)
// riporta qui con un link al luogo.
export const load: PageServerLoad = async ({ url, setHeaders }) => {
	setHeaders({ 'cache-control': HTML_CACHE });
	const radiusKm = filterFromParams(url.searchParams).radiusKm;
	const wanted = url.searchParams.has('luogo') || url.searchParams.has('lat');
	const regions = wanted ? await coverage().catch(() => []) : [];
	const fromUrl = wanted ? placeFromParams(url.searchParams, regions) : null;
	const place: ChosenPlace = fromUrl ?? { ...DEFAULT_PLACE };
	const fetched = { lat: place.lat, lng: place.lng, km: radiusKm };
	const base = { place, fromUrl: !!fromUrl, view: url.searchParams.get('vista') === 'mappa' ? ('map' as const) : ('list' as const) };
	try {
		return { ...base, events: await eventsNear(place, radiusKm), fetched, error: '' };
	} catch (e) {
		console.error(e);
		return { ...base, events: [], fetched, error: 'Non riesco a caricare gli eventi in questo momento.' };
	}
};
