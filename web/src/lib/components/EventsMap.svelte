<script lang="ts">
	import { onMount } from 'svelte';
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
	let markers: Record<string, import('leaflet').CircleMarker> = {};
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

	// Ridisegna marker e cerchio quando cambiano eventi, centro o raggio.
	$effect(() => {
		if (!L || !map || !layer) return;
		const brand = cssVar('--brand');
		layer.clearLayers();
		markers = {};
		map.fitBounds(L.latLng(center.lat, center.lng).toBounds(radiusKm * 2000), { padding: [12, 12] });
		L.circle([center.lat, center.lng], {
			radius: radiusKm * 1000,
			color: brand,
			weight: 1.5,
			opacity: 0.6,
			fillOpacity: 0.04,
			interactive: false
		}).addTo(layer);
		L.circleMarker([center.lat, center.lng], {
			radius: 6,
			color: '#fff',
			weight: 2,
			fillColor: '#2563eb',
			fillOpacity: 1,
			interactive: false
		}).addTo(layer);
		for (const e of events) {
			const m = L.circleMarker([e.lat, e.lng], {
				radius: 8,
				color: '#fff',
				weight: 2,
				fillColor: brand,
				fillOpacity: 0.95
			})
				.bindPopup(() => popup(e))
				.on('mouseover', () => onhover?.(e.id))
				.on('mouseout', () => onhover?.(null))
				.addTo(layer);
			markers[e.id] = m;
		}
	});

	$effect(() => {
		for (const [id, m] of Object.entries(markers)) m.setStyle({ radius: id === highlighted ? 12 : 8 });
		if (highlighted) markers[highlighted]?.bringToFront();
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
		min-height: 320px;
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
		font: 600 1rem var(--font-display);
	}
	.wrap :global(.leaflet-popup-content p) {
		margin: 0.3rem 0 0;
	}
</style>
