import { error, redirect } from '@sveltejs/kit';
import { eventPath, idFromSlug } from '$lib/event';
import { getEvent } from '$lib/server/firestore';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, setHeaders }) => {
	const event = await getEvent(idFromSlug(params.slug));
	if (!event) error(404, 'Evento non trovato: forse è stato rimosso.');
	// Titolo cambiato o slug sbagliato: un solo URL canonico.
	const canonical = eventPath(event);
	if (`/eventi/${params.slug}` !== canonical) redirect(301, canonical);
	setHeaders({ 'cache-control': 'public, max-age=300, s-maxage=3600, stale-while-revalidate=86400' });
	return { event };
};
