<script lang="ts">
	import MapPin from '@lucide/svelte/icons/map-pin';
	import { mount, onMount, unmount } from 'svelte';
	import { baseMap, loadLeaflet } from '$lib/leaflet';

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
	let pin: ReturnType<typeof mount> | null = null;

	// La mappa (Leaflet + tessere OSM) si carica solo quando arriva vicino allo schermo.
	onMount(() => {
		let cancelled = false;
		const io = new IntersectionObserver(
			(entries) => {
				if (!entries.some((e) => e.isIntersecting)) return;
				io.disconnect();
				init();
			},
			{ rootMargin: '200px' }
		);
		io.observe(el);
		const init = () => loadLeaflet().then((L) => {
			if (cancelled) return;
			map = baseMap(L, el, { interactive: true });
			const pinEl = document.createElement('span');
			pinEl.className = 'pin';
			pin = mount(MapPin, { target: pinEl, props: { size: 24, 'aria-hidden': 'true' } });
			const icon = L.divIcon({ className: 'pin-icon', html: pinEl, iconSize: [24, 24], iconAnchor: [12, 22] });
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
			if (pin) unmount(pin);
			io.disconnect();
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
		height: calc(var(--space-7) * 4);
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
	.wrap :global(.pin) {
		display: block;
		color: var(--accent);
	}
	.wrap :global(.pin svg) {
		fill: var(--surface);
	}
</style>
