<script lang="ts">
	import { CATEGORY_ICONS } from '$lib/categoryIcons';
	import { CATEGORIES, type Category } from '$lib/event';
	import { EMPTY_FILTER, type Filter } from '$lib/filters';
	import { RADII_KM } from '$lib/geo';
	import X from '@lucide/svelte/icons/x';

	import type { Snippet } from 'svelte';

	let { filter, onchange, children }: { filter: Filter; onchange: (f: Filter) => void; children?: Snippet } = $props();

	const set = (patch: Partial<Filter>) => onchange({ ...filter, ...patch });
	const active = $derived(
		filter.q !== '' || filter.when !== 'any' || filter.free || filter.kids || filter.running || filter.category !== null
	);

	function reset() {
		onchange({ ...EMPTY_FILTER, radiusKm: filter.radiusKm });
	}
</script>

<form class="filters" role="search" onsubmit={(e) => e.preventDefault()}>
	{@render children?.()}
	<div class="row" role="group" aria-label="Filtri rapidi">
		<button type="button" class="chip" aria-pressed={filter.when === 'today'} onclick={() => set({ when: filter.when === 'today' ? 'any' : 'today' })}>Oggi</button>
		<button type="button" class="chip" aria-pressed={filter.when === 'weekend'} onclick={() => set({ when: filter.when === 'weekend' ? 'any' : 'weekend' })}>Weekend</button>
		<button type="button" class="chip" aria-pressed={filter.free} onclick={() => set({ free: !filter.free })}>Gratis</button>
		<button type="button" class="chip" aria-pressed={filter.kids} onclick={() => set({ kids: !filter.kids })}>Bambini</button>
		<button type="button" class="chip" aria-pressed={filter.running} onclick={() => set({ running: !filter.running })}>Mostre ed eventi in corso</button>
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
	<div class="row" role="group" aria-label="Categorie">
		{#each Object.entries(CATEGORIES) as [value, label] (value)}
			{@const Icon = CATEGORY_ICONS[value as Category]}
			<button
				type="button"
				class="chip"
				aria-pressed={filter.category === value}
				onclick={() => set({ category: filter.category === value ? null : (value as Category) })}
			>
				<Icon size={16} aria-hidden="true" />{label}
			</button>
		{/each}
	</div>
</form>

<style>
	.filters {
		display: grid;
		gap: var(--space-3);
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
