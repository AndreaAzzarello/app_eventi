<script lang="ts">
	import { onMount } from 'svelte';
	import { replaceState } from '$app/navigation';
	import { page } from '$app/state';
	import EventList from '$lib/components/EventList.svelte';
	import EventsMap from '$lib/components/EventsMap.svelte';
	import FilterBar from '$lib/components/FilterBar.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import LocationPicker, { type ChosenPlace } from '$lib/components/LocationPicker.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import { SITE_NAME } from '$lib/config';
	import type { Event } from '$lib/event';
	import { applyFilter, filterFromParams, filterToParams, type Filter } from '$lib/filters';
	import { DEFAULT_PLACE, distanceKm, SNAP_MARGIN_KM, snapCoord } from '$lib/geo';
	import { homePlace } from '$lib/session.svelte';
	import { KEYS, readJson, writeJson } from '$lib/storage';

	let { data } = $props();

	let filter = $state<Filter>(filterFromParams(page.url.searchParams));
	let place = $state<ChosenPlace>({ ...DEFAULT_PLACE });
	let events = $derived<Event[]>(data.events);
	let fetched = $derived(data.fetched);
	let loading = $state(false);
	let error = $derived(data.error);
	let now = $state(Date.now());
	let view = $state<'list' | 'map'>('list');
	let wide = $state(false);
	let highlighted = $state<string | null>(null);
	let picker: LocationPicker | undefined = $state();
	/** Primo accesso senza posizione salvata né permesso di geolocalizzazione: si sceglie regione → comune. */
	let needsPlace = $state(false);

	const visible = $derived(applyFilter(events, filter, now, place));
	const covered = $derived(
		distanceKm(place, fetched) + filter.radiusKm <= fetched.km
	);

	onMount(() => {
		const saved = readJson<ChosenPlace | null>(KEYS.place, null);
		if (saved && Number.isFinite(saved.lat) && Number.isFinite(saved.lng)) place = saved;
		else firstVisit();
		const mq = matchMedia('(min-width: 960px)');
		wide = mq.matches;
		mq.onchange = (e) => (wide = e.matches);
		const tick = setInterval(() => (now = Date.now()), 60_000);
		return () => clearInterval(tick);
	});

	// Al login la zona del profilo vince su quella locale.
	$effect(() => {
		const p = homePlace.value;
		if (p && (p.lat !== place.lat || p.lng !== place.lng)) {
			place = p;
			needsPlace = false;
			picker?.close(); // il dialogo si era aperto prima che arrivasse il profilo
		}
	});

	/** Con il permesso già concesso si parte dalla posizione; altrimenti si chiede dove cercare, senza partire da Modena. */
	async function firstVisit() {
		const granted = await navigator.permissions
			?.query({ name: 'geolocation' })
			.then((s) => s.state === 'granted')
			.catch(() => false);
		if (granted) {
			navigator.geolocation.getCurrentPosition(
				({ coords }) => setPlace({ lat: coords.latitude, lng: coords.longitude, label: 'La tua posizione' }),
				ask,
				{ timeout: 10000, maximumAge: 600000 }
			);
		} else ask();
	}

	function ask() {
		needsPlace = true;
		picker?.open();
	}

	// Ricarica solo se la zona richiesta esce da quella già scaricata.
	$effect(() => {
		if (!covered) load();
	});

	async function load() {
		loading = true;
		error = '';
		const lat = snapCoord(place.lat);
		const lng = snapCoord(place.lng);
		const r = filter.radiusKm;
		try {
			const res = await fetch(`/api/events?lat=${lat}&lng=${lng}&r=${r}`);
			if (!res.ok) throw new Error(String(res.status));
			events = await res.json();
			fetched = { lat, lng, km: r + SNAP_MARGIN_KM };
		} catch {
			error = 'Non riesco a caricare gli eventi. Controlla la connessione e riprova.';
		} finally {
			loading = false;
		}
	}

	function setFilter(f: Filter) {
		filter = f;
		const qs = filterToParams(f).toString();
		replaceState(qs ? `?${qs}` : page.url.pathname, {});
	}

	function setPlace(p: ChosenPlace) {
		place = p;
		needsPlace = false;
		writeJson(KEYS.place, p);
		homePlace.save(p);
	}

	const summary = $derived(
		`${visible.length === 1 ? '1 evento' : `${visible.length} eventi`} entro ${filter.radiusKm} km`
	);
</script>

<Seo title={SITE_NAME} path="/" />

<div class="container">
	<section class="intro" aria-labelledby="h1">
		<h1 id="h1">Cosa succede <span class="accent">vicino a te</span></h1>
		<LocationPicker bind:this={picker} place={needsPlace ? { label: 'Scegli la zona' } : place} onchange={setPlace} />
	</section>

	{#if needsPlace}
		<section class="first-visit" aria-labelledby="first-title">
			<h2 id="first-title">Dove cerchi eventi?</h2>
			<p class="muted">Scegli la tua regione e il tuo comune, oppure usa la tua posizione.</p>
			<button class="btn btn-primary" onclick={() => picker?.open()}>Scegli la zona</button>
		</section>
	{:else}
	<FilterBar {filter} onchange={setFilter} />

	<div class="toolbar">
		<p class="summary" aria-live="polite">{loading ? 'Cerco eventi…' : summary}</p>
		<div class="tabs" role="tablist" aria-label="Vista">
			<button role="tab" id="tab-list" aria-controls="panel-list" aria-selected={view === 'list'} onclick={() => (view = 'list')}>
				<Icon name="list" size={18} /> Lista
			</button>
			<button role="tab" id="tab-map" aria-controls="panel-map" aria-selected={view === 'map'} onclick={() => (view = 'map')}>
				<Icon name="map" size={18} /> Mappa
			</button>
		</div>
	</div>

	<div class="split" data-view={view}>
		<div id="panel-list" class="list-pane" role="tabpanel" aria-labelledby="tab-list">
			<h2 class="visually-hidden">Eventi in programma</h2>
			<EventList
				events={visible}
				{now}
				origin={place}
				{loading}
				{error}
				{highlighted}
				onhover={(id) => (highlighted = id)}
				onretry={load}
			>
				{#snippet empty()}
					<h2>Nessun evento con questi filtri</h2>
					<p class="muted">Prova ad allargare la distanza o a togliere qualche filtro.</p>
					<div class="actions">
						{#if filter.radiusKm < 100}
							<button class="btn btn-primary" onclick={() => setFilter({ ...filter, radiusKm: filter.radiusKm < 50 ? 50 : 100 })}>
								Cerca più lontano
							</button>
						{/if}
						<a class="btn" href="/proponi">Proponi un evento</a>
					</div>
				{/snippet}
			</EventList>
		</div>
		<div id="panel-map" class="map-pane" role="tabpanel" aria-labelledby="tab-map">
			{#if wide || view === 'map'}
				<EventsMap
					events={visible}
					center={place}
					radiusKm={filter.radiusKm}
					{highlighted}
					onhover={(id) => (highlighted = id)}
				/>
			{/if}
		</div>
	</div>
	{/if}
</div>

<style>
	.first-visit {
		margin: 1.5rem 0;
		padding: 1.5rem 1.25rem;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		background: var(--surface);
		display: grid;
		justify-items: start;
		gap: 0.5rem;
	}
	.first-visit h2,
	.first-visit p {
		margin: 0;
	}
	.intro {
		display: flex;
		flex-wrap: wrap;
		align-items: end;
		justify-content: space-between;
		gap: 0.75rem 1.5rem;
		padding: 1.5rem 0 1.1rem;
	}
	.intro h1 {
		margin: 0;
	}
	.accent {
		color: var(--brand);
		font-style: italic;
	}
	.toolbar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		margin: 1rem 0 0.75rem;
	}
	.summary {
		margin: 0;
		font-weight: 600;
		color: var(--muted);
	}
	.tabs {
		display: inline-flex;
		padding: 3px;
		border-radius: 999px;
		background: var(--surface-2);
		border: 1px solid var(--border);
	}
	.tabs button {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		min-height: 40px;
		padding: 0 0.9rem;
		border: none;
		border-radius: 999px;
		background: none;
		color: var(--text);
		font: 600 0.9rem var(--font-body);
		cursor: pointer;
	}
	.tabs [aria-selected='true'] {
		background: var(--surface);
		box-shadow: var(--shadow);
		color: var(--brand);
	}
	.split[data-view='list'] .map-pane,
	.split[data-view='map'] .list-pane {
		display: none;
	}
	.map-pane {
		height: calc(100dvh - var(--header-h) - 140px);
		min-height: 360px;
	}
	.actions {
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		gap: 0.5rem;
	}
	@media (min-width: 960px) {
		.tabs {
			display: none;
		}
		.split {
			display: grid;
			grid-template-columns: minmax(0, 1fr) minmax(0, 1.05fr);
			gap: 1.5rem;
			align-items: start;
		}
		.split .list-pane,
		.split .map-pane {
			display: block !important;
		}
		.map-pane {
			position: sticky;
			top: calc(var(--header-h) + 16px);
			height: calc(100vh - var(--header-h) - 32px);
		}
	}
</style>
