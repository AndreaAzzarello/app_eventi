<script lang="ts">
	import { debounce, reversePlace, searchPlaces, type GeoResult } from '$lib/geocode';
	import Icon from './Icon.svelte';

	export interface ChosenPlace {
		lat: number;
		lng: number;
		label: string;
		/** Solo se scelto dall'elenco dei comuni coperti. */
		slug?: string;
		region?: string;
	}

	interface Region {
		slug: string;
		name: string;
		comuni: { name: string; slug: string; province: string; lat: number; lng: number; events: number }[];
	}

	let { place, onchange }: { place: Pick<ChosenPlace, 'label'>; onchange: (p: ChosenPlace) => void } = $props();

	let dialog: HTMLDialogElement;
	let input: HTMLInputElement | undefined = $state();
	let q = $state('');
	let results = $state<GeoResult[]>([]);
	let busy = $state(false);
	let message = $state('');
	let regions = $state<Region[]>([]);
	let regionSlug = $state('');
	let filter = $state('');
	let loadedRegions = false;

	const region = $derived(regions.find((r) => r.slug === regionSlug));
	// Confronto senza accenti né maiuscole: "forli" trova "Forlì".
	const fold = (s: string) => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
	const comuni = $derived(region ? region.comuni.filter((c) => fold(c.name).includes(fold(filter.trim()))) : []);

	async function loadRegions() {
		if (loadedRegions) return;
		loadedRegions = true;
		try {
			const res = await fetch('/api/places');
			if (!res.ok) throw new Error(String(res.status));
			regions = await res.json();
			if (regions.length === 1) regionSlug = regions[0].slug;
		} catch {
			loadedRegions = false; // riprova alla prossima apertura; la ricerca libera funziona comunque
		}
	}

	export function open() {
		q = '';
		results = [];
		message = '';
		filter = '';
		dialog.showModal();
		loadRegions();
	}

	export function close() {
		dialog.close();
	}

	function choose(p: ChosenPlace) {
		onchange(p);
		dialog.close();
	}

	const search = debounce(async (text: string) => {
		if (text.trim().length < 2) {
			results = [];
			return;
		}
		busy = true;
		message = '';
		try {
			results = await searchPlaces(text, 'city');
			if (!results.length) message = 'Nessun comune trovato. Prova con un altro nome.';
		} catch (e) {
			message = (e as Error).message;
		} finally {
			busy = false;
		}
	});

	function locate() {
		if (!('geolocation' in navigator)) {
			message = 'Il browser non supporta la geolocalizzazione.';
			return;
		}
		busy = true;
		message = '';
		navigator.geolocation.getCurrentPosition(
			async (pos) => {
				const { latitude: lat, longitude: lng } = pos.coords;
				let label = 'La tua posizione';
				try {
					const hit = await reversePlace(lat, lng);
					if (hit?.place) label = `Vicino a ${hit.place.city}`;
				} catch {
					// etichetta generica: la posizione basta
				}
				busy = false;
				choose({ lat, lng, label });
			},
			(err) => {
				busy = false;
				message =
					err.code === err.PERMISSION_DENIED
						? 'Permesso negato. Puoi cercare la tua città qui sotto.'
						: 'Posizione non disponibile. Cerca la tua città qui sotto.';
			},
			{ enableHighAccuracy: false, timeout: 10000, maximumAge: 600000 }
		);
	}
</script>

<button type="button" class="place-btn" onclick={open} aria-haspopup="dialog">
	<Icon name="pin" size={18} />
	<span class="lbl">{place.label}</span>
	<span class="change">Cambia</span>
</button>

<dialog bind:this={dialog} aria-labelledby="loc-title" onclick={(e) => e.target === dialog && dialog.close()}>
	<div class="head">
		<h2 id="loc-title">Dove cerchi eventi?</h2>
		<button class="btn btn-ghost btn-sm" onclick={() => dialog.close()} aria-label="Chiudi"><Icon name="x" /></button>
	</div>
	<button class="btn btn-primary wide" onclick={locate} disabled={busy}>
		<Icon name="locate" /> Usa la mia posizione
	</button>
	<p class="hint">La posizione resta su questo dispositivo: non la salviamo sui nostri server.</p>
	{#if regions.length}
		<div class="field">
			<label for="region-q">Oppure scegli la regione</label>
			<select id="region-q" bind:value={regionSlug} onchange={() => (filter = '')}>
				<option value="">Scegli la regione</option>
				{#each regions as r (r.slug)}<option value={r.slug}>{r.name}</option>{/each}
			</select>
		</div>
		{#if region}
			<div class="field">
				<label for="comune-q">Cerca il comune</label>
				<input id="comune-q" type="search" bind:value={filter} placeholder="Es. {region.comuni[0]?.name ?? 'Modena'}" autocomplete="off" />
			</div>
			<ul class="results comuni">
				{#each comuni as c (c.slug)}
					<li>
						<button class="result" onclick={() => choose({ lat: c.lat, lng: c.lng, label: c.name, slug: c.slug, region: region.name })}>
							<Icon name="pin" size={16} />
							<span class="grow">{c.name}{c.province ? ` (${c.province})` : ''}</span>
							<span class="n">{c.events}</span>
						</button>
					</li>
				{:else}
					<li class="hint">Nessun comune con questo nome tra quelli coperti.</li>
				{/each}
			</ul>
		{/if}
	{/if}
	<div class="field">
		<label for="city-q">{regions.length ? 'Oppure cerca qualsiasi città' : 'Oppure cerca una città'}</label>
		<input
			id="city-q"
			type="search"
			bind:this={input}
			bind:value={q}
			oninput={() => search(q)}
			placeholder="Es. Bologna, Lecce, Bolzano"
			autocomplete="off"
			aria-describedby="loc-msg"
		/>
	</div>
	<p id="loc-msg" class="hint" role="status">{busy ? 'Cerco…' : message}</p>
	{#if results.length}
		<ul class="results">
			{#each results as r (r.lat + ',' + r.lng)}
				<li>
					<button class="result" onclick={() => choose({ lat: r.lat, lng: r.lng, label: r.label })}>
						<Icon name="pin" size={16} />
						{r.label}
					</button>
				</li>
			{/each}
		</ul>
	{/if}
	<p class="hint attribution">Ricerca: © OpenStreetMap / Nominatim</p>
</dialog>

<style>
	.place-btn {
		display: inline-flex;
		align-items: center;
		gap: 0.45rem;
		min-height: 44px;
		max-width: 100%;
		padding: 0.4rem 0.9rem;
		border: 1px solid var(--border);
		border-radius: 999px;
		background: var(--surface);
		color: var(--text);
		font: 600 0.95rem var(--font-body);
		cursor: pointer;
	}
	.place-btn:hover {
		border-color: var(--brand);
	}
	.place-btn :global(svg) {
		color: var(--brand);
	}
	.lbl {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.change {
		color: var(--brand);
		font-weight: 500;
		font-size: 0.85rem;
	}
	dialog {
		width: 100%;
	}
	.head {
		display: flex;
		justify-content: space-between;
		align-items: start;
		gap: 1rem;
	}
	.wide {
		width: 100%;
	}
	.results {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 0.25rem;
	}
	.result {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		width: 100%;
		min-height: 44px;
		padding: 0.5rem 0.75rem;
		border: none;
		border-radius: var(--radius-sm);
		background: var(--surface-2);
		color: var(--text);
		font: inherit;
		text-align: left;
		cursor: pointer;
	}
	.result:hover {
		background: var(--brand-soft);
	}
	.comuni {
		max-height: 14rem;
		overflow-y: auto;
		margin-bottom: 1rem;
	}
	.grow {
		flex: 1;
		min-width: 0;
		overflow-wrap: anywhere;
	}
	.n {
		color: var(--muted);
		font-size: 0.85rem;
	}
	.attribution {
		margin: 1rem 0 0;
		font-size: 0.75rem;
	}
</style>
