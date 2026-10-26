import { error, json } from '@sveltejs/kit';
import { RADII_KM, SNAP_MARGIN_KM, snapCoord } from '$lib/geo';
import { eventsNear } from '$lib/server/firestore';
import { getEvents } from '$lib/server/firestore';
import type { RequestHandler } from './$types';

// GET /api/events?lat=&lng=&r=  → eventi nel raggio dal punto della griglia di ~5 km più vicino
//                                  (il browser rifiltra sulla distanza vera): poche chiavi di cache.
// GET /api/events?ids=a,b,c     → eventi per id (preferiti di chi non ha l'account)
export const GET: RequestHandler = async ({ url, setHeaders }) => {
	const ids = url.searchParams.get('ids');
	if (ids != null) {
		const list = await getEvents(ids.split(',').filter(Boolean));
		setHeaders({ 'cache-control': 'public, max-age=60, s-maxage=600' });
		return json(list);
	}
	const lat = snapCoord(Number(url.searchParams.get('lat')));
	const lng = snapCoord(Number(url.searchParams.get('lng')));
	const r = Number(url.searchParams.get('r'));
	if (!Number.isFinite(lat) || !Number.isFinite(lng) || Math.abs(lat) > 90 || Math.abs(lng) > 180)
		error(400, 'Coordinate non valide');
	if (!(RADII_KM as readonly number[]).includes(r)) error(400, 'Raggio non valido');
	const events = await eventsNear({ lat, lng }, r + SNAP_MARGIN_KM);
	setHeaders({ 'cache-control': 'public, max-age=300, s-maxage=1800, stale-while-revalidate=86400' });
	return json(events);
};
