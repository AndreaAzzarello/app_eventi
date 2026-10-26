import { HTML_CACHE } from '$lib/server/cache';
import { error } from '@sveltejs/kit';
import { slugify } from '$lib/event';
import { eventsInCity } from '$lib/server/firestore';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, setHeaders }) => {
	if (params.slug !== slugify(params.slug)) error(404, 'Città non trovata');
	const events = await eventsInCity(params.slug);
	// Senza eventi non sappiamo nemmeno il nome della città: 404 vero, non una pagina vuota indicizzata.
	if (!events.length) error(404, 'Nessun evento in programma per questa città.');
	setHeaders({ 'cache-control': HTML_CACHE });
	const { city, province, region } = events[0];
	return { events, city, province, region };
};
