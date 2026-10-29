<script lang="ts">
	import { debounce, reversePlace, searchPlaces, type GeoResult } from '$lib/geocode';
	import MapPin from '@lucide/svelte/icons/map-pin';
	import X from '@lucide/svelte/icons/x';
	import LocateFixed from '@lucide/svelte/icons/locate-fixed';
	import { fmtNum } from '$lib/format';

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
		comuni: { name: string; slug: string; province: string; lat: number; lng: number; events: number; alt?: string }[];
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
	const comuni = $derived(region ? region.comuni.filter((c) => [c.name, c.alt ?? ''].some((n) => fold(n).includes(fold(filter.trim())))) : []);

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
	<MapPin size={20} aria-hidden="true" />
	<span class="lbl">{place.label}</span>
	<span class="change">Cambia</span>
</button>

<dialog bind:this={dialog} aria-labelledby="loc-title" onclick={(e) => e.target === dialog && dialog.close()}>
	<div class="head">
		<h2 id="loc-title">Dove cerchi eventi?</h2>
		<button class="btn btn-ghost btn-sm" onclick={() => dialog.close()} aria-label="Chiudi"><X size={20} aria-hidden="true" /></button>
	</div>
	<button class="btn btn-primary wide" onclick={locate} disabled={busy}>
		<LocateFixed size={20} aria-hidden="true" /> Usa la mia posizione
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
							<MapPin size={16} aria-hidden="true" />
							<span class="grow">{c.name}{c.alt ? ` / ${c.alt}` : ''}{c.province ? ` (${c.province})` : ''}</span>
							<span class="n">{fmtNum(c.events)}</span>
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
						<MapPin size={16} aria-hidden="true" />
						{r.label}
					</button>
				</li>
			{/each}
		</ul>
	{/if}
	<p class="hint attribution">Ricerca: &copy; OpenStreetMap / Nominatim</p>
</dialog>

<style>
	.place-btn {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		min-height: var(--control);
		max-width: 100%;
		padding: var(--space-1) var(--space-3);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		background: var(--surface);
		color: var(--text);
		font-family: var(--font-body);
		font-size: var(--text-md);
		font-weight: var(--fw-strong);
		cursor: pointer;
		transition: border-color var(--dur) var(--ease);
	}
	.place-btn:hover {
		border-color: var(--accent);
	}
	.place-btn:focus-visible,
	.result:focus-visible {
		outline: 2px solid var(--focus);
		outline-offset: 2px;
	}
	.place-btn :global(svg) {
		color: var(--accent);
	}
	.lbl {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.change {
		color: var(--accent);
		font-weight: var(--fw-regular);
		font-size: var(--text-sm);
	}
	dialog {
		width: 100%;
		/* ancorato in alto: non si ricentra quando arrivano le regioni (CLS) */
		margin: var(--space-5) auto auto;
	}
	.head {
		display: flex;
		justify-content: space-between;
		align-items: start;
		gap: var(--space-3);
	}
	.wide {
		width: 100%;
	}
	.results {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: var(--space-1);
	}
	.result {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		width: 100%;
		min-height: var(--control);
		padding: var(--space-2) var(--space-3);
		border: none;
		border-radius: var(--radius-sm);
		background: var(--surface-2);
		color: var(--text);
		font: inherit;
		text-align: left;
		cursor: pointer;
	}
	.result:hover {
		outline: 1px solid var(--accent);
	}
	.comuni {
		max-height: var(--w-dialog);
		overflow-y: auto;
		margin-bottom: var(--space-3);
	}
	.grow {
		flex: 1;
		min-width: 0;
		overflow-wrap: anywhere;
	}
	.n {
		color: var(--muted);
		font-size: var(--text-sm);
		font-variant-numeric: tabular-nums;
	}
	.attribution {
		margin: var(--space-3) 0 0;
		font-size: var(--text-xs);
	}
</style>
