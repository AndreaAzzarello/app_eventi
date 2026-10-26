import { DEFAULT_PLACE, DEFAULT_RADIUS_KM } from '$lib/geo';
import { eventsNear } from '$lib/server/firestore';
import type { PageServerLoad } from './$types';

// SSR sulla zona predefinita e raggio predefinito; i filtri si applicano nel browser,
// la posizione dell'utente (solo nel suo localStorage) fa ripartire la ricerca via /api/events.
export const load: PageServerLoad = async ({ setHeaders }) => {
	setHeaders({ 'cache-control': 'public, max-age=60, s-maxage=1800, stale-while-revalidate=86400' });
	const fetched = { lat: DEFAULT_PLACE.lat, lng: DEFAULT_PLACE.lng, km: DEFAULT_RADIUS_KM };
	try {
		return { events: await eventsNear(DEFAULT_PLACE, DEFAULT_RADIUS_KM), fetched, error: '' };
	} catch (e) {
		console.error(e);
		return { events: [], fetched, error: 'Non riesco a caricare gli eventi in questo momento.' };
	}
};
