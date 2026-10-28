<script lang="ts">
	import { CATEGORIES, type Category } from '$lib/event';
	import { EMPTY_FILTER, type Filter } from '$lib/filters';
	import { RADII_KM } from '$lib/geo';
	import { debounce } from '$lib/geocode';
	import Search from '@lucide/svelte/icons/search';
	import X from '@lucide/svelte/icons/x';

	let { filter, onchange }: { filter: Filter; onchange: (f: Filter) => void } = $props();

	let q = $derived(filter.q);
	const setQ = debounce((v: string) => onchange({ ...filter, q: v }), 250);
	const set = (patch: Partial<Filter>) => onchange({ ...filter, ...patch });
	const active = $derived(
		filter.q !== '' || filter.when !== 'any' || filter.free || filter.kids || filter.running || filter.category !== null
	);

	function reset() {
		q = '';
		onchange({ ...EMPTY_FILTER, radiusKm: filter.radiusKm });
	}
</script>

<form class="filters" role="search" onsubmit={(e) => e.preventDefault()}>
	<div class="search">
		<label for="q" class="visually-hidden">Cerca eventi</label>
		<Search size={20} aria-hidden="true" />
		<input
			id="q"
			type="search"
			placeholder="Cerca concerti, sagre, mostre…"
			bind:value={q}
			oninput={() => setQ(q)}
			autocomplete="off"
			enterkeyhint="search"
		/>
	</div>
	<div class="row" role="group" aria-label="Filtri rapidi">
		<button type="button" class="chip" aria-pressed={filter.when === 'today'} onclick={() => set({ when: filter.when === 'today' ? 'any' : 'today' })}>Oggi</button>
		<button type="button" class="chip" aria-pressed={filter.when === 'weekend'} onclick={() => set({ when: filter.when === 'weekend' ? 'any' : 'weekend' })}>Weekend</button>
		<button type="button" class="chip" aria-pressed={filter.free} onclick={() => set({ free: !filter.free })}>Gratis</button>
		<button type="button" class="chip" aria-pressed={filter.kids} onclick={() => set({ kids: !filter.kids })}>Bambini</button>
		<button type="button" class="chip" aria-pressed={filter.running} onclick={() => set({ running: !filter.running })}>Mostre ed eventi in corso</button>
		<label class="select-chip">
			<span class="visually-hidden">Categoria</span>
			<select
				value={filter.category ?? ''}
				onchange={(e) => set({ category: (e.currentTarget.value || null) as Category | null })}
			>
				<option value="">Tutte le categorie</option>
				{#each Object.entries(CATEGORIES) as [value, label] (value)}
					<option {value}>{label}</option>
				{/each}
			</select>
		</label>
		<label class="select-chip">
			<span class="visually-hidden">Distanza massima</span>
			<select value={filter.radiusKm} onchange={(e) => set({ radiusKm: Number(e.currentTarget.value) })}>
				{#each RADII_KM as km (km)}
					<option value={km}>Entro {km} km</option>
				{/each}
			</select>
		</label>
		{#if active}
			<button type="button" class="chip reset" onclick={reset}><X size={16} aria-hidden="true" /> Azzera</button>
		{/if}
	</div>
</form>

<style>
	.filters {
		display: grid;
		gap: var(--space-3);
	}
	.search {
		position: relative;
		display: flex;
		align-items: center;
	}
	.search :global(svg) {
		position: absolute;
		left: var(--space-3);
		color: var(--muted);
		pointer-events: none;
	}
	.search input {
		padding-left: var(--space-6);
		min-height: var(--control);
		border-radius: var(--radius);
		font-size: var(--text-md);
	}
	.row {
		display: flex;
		gap: var(--space-2);
		overflow-x: auto;
		padding: 2px;
		margin: 0;
		scrollbar-width: none;
	}
	.row::-webkit-scrollbar {
		display: none;
	}
	.select-chip {
		position: relative; /* contiene il testo visually-hidden: fuori dallo scroller allargherebbe la pagina */
	}
	.select-chip select {
		min-height: var(--control);
		width: auto;
		padding: var(--space-1) var(--space-6) var(--space-1) var(--space-3);
		border-radius: var(--radius);
		font-size: var(--text-sm);
	}
	.reset {
		border-style: dashed;
	}
	@media (min-width: 900px) {
		.row {
			flex-wrap: wrap;
			overflow: visible;
		}
	}
</style>
