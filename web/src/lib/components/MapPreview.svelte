<script lang="ts">
	import Clock from '@lucide/svelte/icons/clock';
	import MapPin from '@lucide/svelte/icons/map-pin';
	import Ticket from '@lucide/svelte/icons/ticket';
	import { CATEGORY_ICONS } from '$lib/categoryIcons';
	import { formatWhen } from '$lib/dates';
	import { CATEGORIES, eventPath, PRICE_TYPES, type Event } from '$lib/event';

	// Anteprima al tocco di un marker: la stessa grammatica della card (categoria, titolo, quando, dove, prezzo).
	let { event }: { event: Event } = $props();
	const Icon = $derived(CATEGORY_ICONS[event.category]);
</script>

<div class="preview" data-cat={event.category}>
	<p class="kicker"><Icon size={16} aria-hidden="true" />{CATEGORIES[event.category]}</p>
	<a class="title" href={eventPath(event)}>{event.title}</a>
	<ul>
		<li><Clock size={16} aria-hidden="true" /><span>{formatWhen(event.startTime, event.endTime)}</span></li>
		<li><MapPin size={16} aria-hidden="true" /><span>{event.approxLocation ? 'Luogo da confermare' : event.venueName || event.city}</span></li>
		<li><Ticket size={16} aria-hidden="true" /><span>{PRICE_TYPES[event.priceType]}</span></li>
	</ul>
</div>

<style>
	.preview {
		display: grid;
		gap: var(--space-1);
		min-width: 0;
		padding-left: var(--space-2);
		border-left: var(--space-1) solid var(--ink);
	}
	.kicker {
		display: flex;
		align-items: center;
		gap: var(--space-1);
		margin: 0;
		font-size: var(--text-sm);
		font-weight: var(--fw-strong);
		color: var(--ink);
	}
	.title {
		font: var(--fw-strong) var(--text-md) / var(--lh-tight) var(--font-display);
		color: var(--text);
		text-decoration: none;
		overflow-wrap: anywhere;
	}
	.title:hover,
	.title:focus-visible {
		text-decoration: underline;
	}
	ul {
		display: grid;
		gap: var(--space-1);
		margin: 0;
		padding: 0;
		list-style: none;
		font-size: var(--text-sm);
		color: var(--muted);
	}
	li {
		display: flex;
		align-items: flex-start;
		gap: var(--space-1);
	}
	li :global(svg) {
		flex: none;
		margin-top: 2px;
	}
</style>
