import { HTML_CACHE } from '$lib/server/cache';
import { filterFromParams } from '$lib/filters';
import { DEFAULT_PLACE, type ChosenPlace } from '$lib/geo';
import { placeFromEvents, placeFromParams, popularPlaces } from '$lib/places';
import { coverage, eventsInCity, eventsNear } from '$lib/server/firestore';
import type { PageServerLoad } from './$types';

// SSR sul luogo dell'URL (?luogo=slug oppure ?nome=&lat=&lng=). I filtri si applicano nel browser; la posizione salvata
// dall'utente (solo nel suo localStorage) riporta qui con un link al luogo.
// Senza luogo il server non sceglie al posto dell'utente: niente eventi, ma i link alle regioni e alle città con più eventi
// (per chi non ha JavaScript e per i motori di ricerca); il browser porta al luogo salvato o chiede dove cercare.
export const load: PageServerLoad = async ({ url, setHeaders }) => {
	setHeaders({ 'cache-control': HTML_CACHE });
	const radiusKm = filterFromParams(url.searchParams).radiusKm;
	const wanted = url.searchParams.has('luogo') || url.searchParams.has('lat');
	const regions = await coverage().catch(() => []);
	const slug = url.searchParams.get('luogo') ?? '';
	let fromUrl = wanted ? placeFromParams(url.searchParams, regions) : null;
	// Città con eventi ma (ancora) fuori dalla copertura: si ricava il luogo dagli eventi, mai il predefinito in silenzio.
	if (wanted && !fromUrl && /^[a-z0-9-]{1,80}$/.test(slug)) fromUrl = placeFromEvents(slug, await eventsInCity(slug, 20).catch(() => []));
	const place: ChosenPlace = fromUrl ?? { ...DEFAULT_PLACE };
	const view = url.searchParams.get('vista') === 'mappa' ? ('map' as const) : ('list' as const);
	const base = { place, fromUrl: !!fromUrl, unknownPlace: wanted && !fromUrl ? slug : null, noPlace: !wanted, view };

	if (!wanted) {
		const sum = (r: (typeof regions)[number]) => r.comuni.reduce((n, c) => n + c.events, 0);
		const popular = {
			regions: regions
				.map((r) => ({ slug: r.slug, name: r.name, events: sum(r) }))
				.filter((r) => r.events > 0)
				.sort((a, b) => b.events - a.events || a.name.localeCompare(b.name, 'it')),
			cities: popularPlaces(regions, 12)
				.filter((h) => h.events > 0)
				.map((h) => ({ slug: h.place.slug!, name: h.place.label, events: h.events }))
		};
		// km: 0 → mai "coperto": il browser scarica gli eventi solo dopo aver saputo il luogo
		return { ...base, events: [], fetched: { lat: place.lat, lng: place.lng, km: 0 }, error: '', popular };
	}

	const fetched = { lat: place.lat, lng: place.lng, km: radiusKm };
	try {
		return { ...base, events: await eventsNear(place, radiusKm), fetched, error: '', popular: null };
	} catch (e) {
		console.error(e);
		return { ...base, events: [], fetched, error: 'Non riesco a caricare gli eventi in questo momento. Riprova tra poco.', popular: null };
	}
};
