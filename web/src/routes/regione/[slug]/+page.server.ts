import { error } from '@sveltejs/kit';
import { slugify } from '$lib/event';
import { HTML_CACHE } from '$lib/server/cache';
import { regionCoverage } from '$lib/server/firestore';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, setHeaders }) => {
	if (params.slug !== slugify(params.slug)) error(404, 'Regione non trovata');
	const region = await regionCoverage(params.slug);
	if (!region?.comuni.length) error(404, 'Regione non ancora coperta.');
	setHeaders({ 'cache-control': HTML_CACHE });
	return { name: region.name, comuni: region.comuni, total: region.comuni.reduce((n, c) => n + c.events, 0) };
};
