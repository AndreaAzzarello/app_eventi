import { json } from '@sveltejs/kit';
import { coverage } from '$lib/server/firestore';
import type { RequestHandler } from './$types';

// GET /api/places → regioni coperte con i loro comuni (centro e numero di eventi), per la scelta del luogo.
// Cambia una volta al giorno (import): un'ora all'edge.
export const GET: RequestHandler = async ({ setHeaders }) => {
	setHeaders({ 'cache-control': 'public, max-age=300, s-maxage=3600, stale-while-revalidate=86400' });
	return json(await coverage());
};
