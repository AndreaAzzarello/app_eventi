import { error } from '@sveltejs/kit';
import { slugify } from '$lib/event';
import { HTML_CACHE } from '$lib/server/cache';
import { monthKeys, monthLine } from '$lib/format';
import { monthStats, regionCoverage } from '$lib/server/firestore';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, setHeaders }) => {
	if (params.slug !== slugify(params.slug)) error(404, 'Regione non trovata');
	const region = await regionCoverage(params.slug);
	if (!region?.comuni.length) error(404, 'Regione non ancora coperta.');
	const keys = monthKeys();
	const { cur, prev } = await monthStats(params.slug, keys);
	setHeaders({ 'cache-control': HTML_CACHE });
	return {
		slug: params.slug,
		name: region.name,
		comuni: region.comuni,
		total: region.comuni.reduce((n, c) => n + c.events, 0),
		// Il confronto compare solo se il mese corrente ha dati; senza il precedente resta il solo numero.
		month: cur ? monthLine(cur.events, prev?.events ?? null, keys) : null
	};
};
