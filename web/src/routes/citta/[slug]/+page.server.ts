import { HTML_CACHE } from '$lib/server/cache';
import { error, redirect } from '@sveltejs/kit';
import { cityPath, slugify } from '$lib/event';
import { inItaly, placeToParams } from '$lib/places';
import { coverage, eventsInCity, regionCoverage } from '$lib/server/firestore';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, setHeaders }) => {
	if (params.slug !== slugify(params.slug)) error(404, 'Città non trovata');
	const events = await eventsInCity(params.slug);
	// Senza eventi non sappiamo nemmeno il nome della città: 404 vero, non una pagina vuota indicizzata.
	if (!events.length) {
		// /citta/bozen o /citta/bolzano-bozen: l'indirizzo canonico è quello col nome italiano
		const alias = (await coverage().catch(() => [])).flatMap((r) => r.comuni).find(
			(c) => c.alt && [c.alt, `${c.name} ${c.alt}`, `${c.alt} ${c.name}`].some((n) => slugify(n) === params.slug)
		);
		if (alias) redirect(301, cityPath(alias.slug));
		error(404, 'Nessun evento in programma per questa città.');
	}
	setHeaders({ 'cache-control': HTML_CACHE });
	const { city, province, region } = events[0];
	// Link alla pagina regione solo se esiste (regione coperta): niente breadcrumb che portano a un 404.
	const regionSlug = region ? slugify(region) : '';
	const regionPage = regionSlug ? await regionCoverage(regionSlug).catch(() => null) : null;
	const cityAlt = events.find((e) => e.cityAlt)?.cityAlt ?? '';
	return { events, city, cityAlt, province, region, regionSlug: regionPage ? regionSlug : '', mapQuery: await mapQuery(params.slug, city, events) };
};

/**
 * Query della home centrata su questa città. `?luogo=` vale solo per i comuni nella copertura: gli altri (una città con
 * eventi ma non coperta) tornerebbero al luogo predefinito, quindi si passano nome e coordinate medie degli eventi.
 */
async function mapQuery(slug: string, city: string, events: Awaited<ReturnType<typeof eventsInCity>>) {
	if ((await coverage().catch(() => [])).some((r) => r.comuni.some((c) => c.slug === slug))) return `luogo=${slug}`;
	const at = events.filter((e) => inItaly(e.lat, e.lng));
	if (!at.length) return ''; // senza coordinate attendibili niente link, meglio che una mappa sul posto sbagliato
	const mean = (k: 'lat' | 'lng') => at.reduce((n, e) => n + e[k], 0) / at.length;
	return placeToParams({ label: city, lat: mean('lat'), lng: mean('lng') }).toString();
};
