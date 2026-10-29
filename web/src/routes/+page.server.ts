import { HTML_CACHE } from '$lib/server/cache';
import { filterFromParams } from '$lib/filters';
import { DEFAULT_PLACE, type ChosenPlace } from '$lib/geo';
import { placeFromEvents, placeFromParams } from '$lib/places';
import { coverage, eventsInCity, eventsNear } from '$lib/server/firestore';
import type { PageServerLoad } from './$types';

// SSR sul luogo dell'URL (?luogo=slug oppure ?nome=&lat=&lng=) o, senza, sulla zona predefinita.
// I filtri si applicano nel browser; la posizione salvata dall'utente (solo nel suo localStorage)
// riporta qui con un link al luogo.
export const load: PageServerLoad = async ({ url, setHeaders }) => {
	setHeaders({ 'cache-control': HTML_CACHE });
	const radiusKm = filterFromParams(url.searchParams).radiusKm;
	const wanted = url.searchParams.has('luogo') || url.searchParams.has('lat');
	const regions = wanted ? await coverage().catch(() => []) : [];
	const slug = url.searchParams.get('luogo') ?? '';
	let fromUrl = wanted ? placeFromParams(url.searchParams, regions) : null;
	// Città con eventi ma (ancora) fuori dalla copertura: si ricava il luogo dagli eventi, mai il predefinito in silenzio.
	if (wanted && !fromUrl && /^[a-z0-9-]{1,80}$/.test(slug)) fromUrl = placeFromEvents(slug, await eventsInCity(slug, 20).catch(() => []));
	const place: ChosenPlace = fromUrl ?? { ...DEFAULT_PLACE };
	const fetched = { lat: place.lat, lng: place.lng, km: radiusKm };
	const base = { place, fromUrl: !!fromUrl, unknownPlace: wanted && !fromUrl ? slug : null, view: url.searchParams.get('vista') === 'mappa' ? ('map' as const) : ('list' as const) };
	try {
		return { ...base, events: await eventsNear(place, radiusKm), fetched, error: '' };
	} catch (e) {
		console.error(e);
		return { ...base, events: [], fetched, error: 'Non riesco a caricare gli eventi in questo momento.' };
	}
};
