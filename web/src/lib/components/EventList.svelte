<script lang="ts">
	import CalendarSearch from '@lucide/svelte/icons/calendar-search';
	import type { Snippet } from 'svelte';
	import type { Event } from '$lib/event';
	import type { LatLng } from '$lib/geo';
	import ErrorMessage from './ErrorMessage.svelte';
	import EventCard from './EventCard.svelte';

	let {
		events,
		now,
		origin = null,
		loading = false,
		error = '',
		highlighted = null,
		onhover,
		onretry,
		empty
	}: {
		events: Event[];
		now: number;
		origin?: LatLng | null;
		loading?: boolean;
		error?: string;
		highlighted?: string | null;
		onhover?: (id: string | null) => void;
		onretry?: () => void;
		empty?: Snippet;
	} = $props();
</script>

{#if loading}
	<ul class="list" aria-hidden="true">
		{#each { length: 5 } as _, i (i)}
			<li class="sk card">
				<div class="skeleton" style="width: var(--space-6); height: var(--space-6)"></div>
				<div class="sk-lines">
					<div class="skeleton" style="width: 40%; height: var(--space-3)"></div>
					<div class="skeleton" style="width: 85%; height: var(--space-4)"></div>
					<div class="skeleton" style="width: 60%; height: var(--space-3)"></div>
				</div>
			</li>
		{/each}
	</ul>
	<p class="visually-hidden" role="status">Caricamento degli eventi…</p>
{:else if error}
	<div class="state">
		<h2>Qualcosa è andato storto</h2>
		<ErrorMessage>{error}</ErrorMessage>
		{#if onretry}<button class="btn btn-primary" onclick={onretry}>Riprova</button>{/if}
	</div>
{:else if events.length === 0}
	<div class="state">
		<CalendarSearch size={24} aria-hidden="true" />
		{#if empty}{@render empty()}{:else}<h2>Nessun evento</h2>{/if}
	</div>
{:else}
	<ul class="list">
		{#each events as event (event.id)}
			<li><EventCard {event} {now} {origin} highlighted={highlighted === event.id} {onhover} /></li>
		{/each}
	</ul>
{/if}

<style>
	.list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: var(--space-3);
	}
	.sk {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: var(--space-3);
		padding: var(--space-3);
	}
	.sk-lines {
		display: grid;
		gap: var(--space-2);
	}
	.state {
		display: grid;
		justify-items: center;
		text-align: center;
		gap: var(--space-2);
		padding: var(--space-6) var(--space-3);
	}
	.state :global(h2) {
		margin: var(--space-2) 0 0;
	}
	.state :global(p) {
		max-width: 40ch;
	}
</style>
