<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { Event } from '$lib/event';
	import type { LatLng } from '$lib/geo';
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
				<div class="skeleton" style="width:3.4rem;height:3.6rem"></div>
				<div>
					<div class="skeleton" style="width:40%;height:.8rem;margin-bottom:.5rem"></div>
					<div class="skeleton" style="width:85%;height:1.1rem;margin-bottom:.5rem"></div>
					<div class="skeleton" style="width:60%;height:.8rem"></div>
				</div>
			</li>
		{/each}
	</ul>
	<p class="visually-hidden" role="status">Caricamento degli eventi…</p>
{:else if error}
	<div class="state" role="alert">
		<svg viewBox="0 0 64 64" width="64" height="64" aria-hidden="true"
			><circle cx="32" cy="32" r="28" fill="var(--danger-soft)" /><path
				d="M32 18v18M32 44v2"
				stroke="var(--danger)"
				stroke-width="4"
				stroke-linecap="round"
			/></svg
		>
		<h2>Qualcosa è andato storto</h2>
		<p class="muted">{error}</p>
		{#if onretry}<button class="btn btn-primary" onclick={onretry}>Riprova</button>{/if}
	</div>
{:else if events.length === 0}
	<div class="state">
		<svg viewBox="0 0 64 64" width="72" height="72" aria-hidden="true">
			<rect x="10" y="14" width="44" height="40" rx="6" fill="var(--brand-soft)" />
			<path d="M10 26h44M22 10v8M42 10v8" stroke="var(--brand)" stroke-width="3" stroke-linecap="round" />
			<circle cx="32" cy="40" r="5" fill="none" stroke="var(--brand)" stroke-width="3" />
		</svg>
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
		gap: 0.75rem;
	}
	.sk {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 0.9rem;
		padding: 0.9rem;
	}
	.state {
		display: grid;
		justify-items: center;
		text-align: center;
		gap: 0.4rem;
		padding: 2.5rem 1rem;
	}
	.state :global(h2) {
		margin: 0.5rem 0 0;
	}
	.state :global(p) {
		max-width: 40ch;
	}
</style>
