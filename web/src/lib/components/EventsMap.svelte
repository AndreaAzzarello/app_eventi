<script lang="ts">
	import { mount, onMount, unmount } from 'svelte';
	import { CATEGORY_ICONS } from '$lib/categoryIcons';
	import { eventPath, type Event } from '$lib/event';
	import type { LatLng } from '$lib/geo';
	import { baseMap, cssVar, loadLeaflet, type Leaflet } from '$lib/leaflet';
	import { formatWhen } from '$lib/dates';

	let {
		events,
		center,
		radiusKm,
		highlighted = null,
		onhover
	}: {
		events: Event[];
		center: LatLng;
		radiusKm: number;
		highlighted?: string | null;
		onhover?: (id: string | null) => void;
	} = $props();

	let el: HTMLDivElement;
	let L: Leaflet | null = $state(null);
	let map: import('leaflet').Map | null = null;
	let layer: import('leaflet').LayerGroup | null = null;
	let markers: Record<string, import('leaflet').Marker> = {};
	let mounted: ReturnType<typeof mount>[] = [];
	let failed = $state(false);

	onMount(() => {
		let cancelled = false;
		loadLeaflet()
			.then((lib) => {
				if (cancelled) return;
				map = baseMap(lib, el);
				layer = lib.layerGroup().addTo(map);
				L = lib;
			})
			.catch(() => (failed = true));
		return () => {
			cancelled = true;
			mounted.forEach((m) => unmount(m));
			map?.remove();
		};
	});

	function popup(e: Event) {
		const div = document.createElement('div');
		const a = document.createElement('a');
		a.href = eventPath(e);
		a.textContent = e.title;
		a.className = 'map-popup-title';
		const p = document.createElement('p');
		p.textContent = `${formatWhen(e.startTime, e.endTime)} · ${e.venueName || e.city}`;
		div.append(a, p);
		return div;
	}

	// Marker neutro con l'icona della categoria: la categoria si legge dall'icona, non dal colore.
	function markerIcon(lib: Leaflet, e: Event) {
		const el = document.createElement('span');
		el.className = 'ev-marker';
		mounted.push(mount(CATEGORY_ICONS[e.category], { target: el, props: { size: 16, 'aria-hidden': 'true' } }));
		return lib.divIcon({ className: 'ev-marker-wrap', html: el, iconSize: [32, 32], iconAnchor: [16, 16] });
	}

	// Ridisegna marker e cerchio quando cambiano eventi, centro o raggio.
	$effect(() => {
		if (!L || !map || !layer) return;
		const accent = cssVar('--accent');
		layer.clearLayers();
		mounted.forEach((m) => unmount(m));
		mounted = [];
		markers = {};
		map.fitBounds(L.latLng(center.lat, center.lng).toBounds(radiusKm * 2000), { padding: [16, 16] });
		L.circle([center.lat, center.lng], {
			radius: radiusKm * 1000,
			color: accent,
			weight: 2,
			opacity: 0.6,
			fill: false,
			interactive: false
		}).addTo(layer);
		L.circleMarker([center.lat, center.lng], {
			radius: 6,
			color: cssVar('--surface'),
			weight: 2,
			fillColor: cssVar('--text'),
			fillOpacity: 1,
			interactive: false
		}).addTo(layer);
		for (const e of events) {
			markers[e.id] = L.marker([e.lat, e.lng], { icon: markerIcon(L, e), title: e.title })
				.bindPopup(() => popup(e))
				.on('mouseover', () => onhover?.(e.id))
				.on('mouseout', () => onhover?.(null))
				.addTo(layer);
		}
	});

	$effect(() => {
		for (const [id, m] of Object.entries(markers)) {
			m.getElement()?.classList.toggle('active', id === highlighted);
			m.setZIndexOffset(id === highlighted ? 1000 : 0);
		}
	});
</script>

<div class="wrap">
	<div bind:this={el} class="map" role="region" aria-label="Mappa degli eventi"></div>
	{#if !L && !failed}<div class="skeleton cover" aria-hidden="true"></div>{/if}
	{#if failed}<p class="cover fail">Mappa non disponibile in questo momento.</p>{/if}
</div>

<style>
	.wrap {
		position: relative;
		height: 100%;
		min-height: calc(var(--space-7) * 5);
		border-radius: var(--radius);
		overflow: hidden;
		border: 1px solid var(--border);
		background: var(--surface-2);
	}
	.map {
		position: absolute;
		inset: 0;
	}
	.cover {
		position: absolute;
		inset: 0;
		margin: 0;
		border-radius: 0;
	}
	.fail {
		display: grid;
		place-items: center;
		color: var(--muted);
	}
	.wrap :global(.map-popup-title) {
		font: var(--fw-strong) var(--text-md) var(--font-display);
	}
	.wrap :global(.leaflet-popup-content p) {
		margin: var(--space-1) 0 0;
	}
	.wrap :global(.ev-marker-wrap) {
		background: none;
		border: none;
	}
	.wrap :global(.ev-marker) {
		display: grid;
		place-items: center;
		width: var(--control-sm);
		height: var(--control-sm);
		border: 2px solid var(--border-strong);
		border-radius: var(--radius-full);
		background: var(--surface);
		color: var(--text);
	}
	.wrap :global(.ev-marker-wrap.active .ev-marker) {
		border-color: var(--accent);
		color: var(--accent);
	}
</style>
