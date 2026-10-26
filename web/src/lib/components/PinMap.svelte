<script lang="ts">
	import { onMount } from 'svelte';
	import { baseMap, cssVar, loadLeaflet } from '$lib/leaflet';

	// Mini-mappa con un segnaposto. Con onmove il segnaposto si trascina (o si sposta toccando la mappa).
	let {
		lat,
		lng,
		zoom = 15,
		label = 'Mappa del luogo',
		onmove
	}: { lat: number; lng: number; zoom?: number; label?: string; onmove?: (lat: number, lng: number) => void } = $props();

	let el: HTMLDivElement;
	let map: import('leaflet').Map | null = null;
	let marker: import('leaflet').Marker | null = null;
	let loaded = $state(false);

	onMount(() => {
		let cancelled = false;
		loadLeaflet().then((L) => {
			if (cancelled) return;
			map = baseMap(L, el, { interactive: true });
			const icon = L.divIcon({
				className: 'pin-icon',
				html: `<svg viewBox="0 0 24 24" width="36" height="36" aria-hidden="true"><path fill="${cssVar('--brand')}" stroke="#fff" stroke-width="1.5" d="M12 2a7 7 0 0 0-7 7c0 5.2 7 13 7 13s7-7.8 7-13a7 7 0 0 0-7-7z"/><circle cx="12" cy="9" r="2.6" fill="#fff"/></svg>`,
				iconSize: [36, 36],
				iconAnchor: [18, 34]
			});
			marker = L.marker([lat, lng], { icon, draggable: !!onmove, keyboard: !!onmove, title: label }).addTo(map);
			map.setView([lat, lng], zoom);
			if (onmove) {
				marker.on('dragend', () => {
					const p = marker!.getLatLng();
					onmove(p.lat, p.lng);
				});
				map.on('click', (e) => {
					marker!.setLatLng(e.latlng);
					onmove(e.latlng.lat, e.latlng.lng);
				});
			}
			loaded = true;
		});
		return () => {
			cancelled = true;
			map?.remove();
		};
	});

	// Coordinate cambiate da fuori (es. ricerca indirizzo): sposta segnaposto e vista.
	$effect(() => {
		const [la, ln] = [lat, lng];
		if (!loaded || !marker || !map) return;
		const cur = marker.getLatLng();
		if (Math.abs(cur.lat - la) > 1e-6 || Math.abs(cur.lng - ln) > 1e-6) {
			marker.setLatLng([la, ln]);
			map.setView([la, ln], Math.max(map.getZoom(), 14));
		}
	});
</script>

<div class="wrap">
	<div bind:this={el} class="map" role="region" aria-label={label}></div>
	{#if !loaded}<div class="skeleton cover" aria-hidden="true"></div>{/if}
</div>

<style>
	.wrap {
		position: relative;
		height: 240px;
		border-radius: var(--radius);
		overflow: hidden;
		border: 1px solid var(--border);
		background: var(--surface-2);
	}
	.map,
	.cover {
		position: absolute;
		inset: 0;
		border-radius: 0;
	}
	.wrap :global(.pin-icon) {
		background: none;
		border: none;
	}
</style>
