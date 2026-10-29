<script lang="ts">
	import { CATEGORY_ICONS } from '$lib/categoryIcons';
	import { allDay, formatTime, romeParts, sentence, shortDate, shortDay } from '$lib/dates';
	import { CATEGORIES, eventPath, isForKids, isFree, runningLabel, type Event } from '$lib/event';
	import { fmtNum } from '$lib/format';
	import { distanceKm, type LatLng } from '$lib/geo';
	import FavoriteButton from './FavoriteButton.svelte';

	let {
		event,
		origin = null,
		now,
		highlighted = false,
		onhover
	}: {
		event: Event;
		origin?: LatLng | null;
		now: number;
		highlighted?: boolean;
		onhover?: (id: string | null) => void;
	} = $props();

	const MONTHS = ['gen', 'feb', 'mar', 'apr', 'mag', 'giu', 'lug', 'ago', 'set', 'ott', 'nov', 'dic'];
	const start = $derived(romeParts(Math.max(event.startTime, Math.min(now, event.endTime))));
	const ongoing = $derived(event.startTime < now && event.endTime > now);
	const running = $derived(runningLabel(event));
	const km = $derived(origin ? distanceKm(origin, event) : null);
	const CategoryIcon = $derived(CATEGORY_ICONS[event.category]);
</script>

<article
	class="ev card"
	class:highlighted
	onmouseenter={() => onhover?.(event.id)}
	onmouseleave={() => onhover?.(null)}
>
	<div class="date" aria-hidden="true">
		<span class="d">{start.day}</span>
		<span class="m">{MONTHS[start.month - 1]}</span>
	</div>
	<div class="body">
		<p class="when">
			{#if ongoing}<span class="live">In corso</span> ·{/if}
			{sentence(shortDay(event.startTime, now))} · {allDay(event.startTime, event.endTime) ? 'Tutto il giorno' : formatTime(event.startTime)}{#if running === 'Mostra'} · fino al {shortDate(event.endTime)}{/if}
		</p>
		<h3><a href={eventPath(event)} class="stretched">{event.title}</a></h3>
		<p class="where">
			{#if event.approxLocation}
				{event.venueName ? `${event.venueName} · ` : ''}<span class="approx">Luogo da confermare</span>{#if event.city}, {event.city}{/if}
			{:else}
				{event.venueName || event.address}{#if event.city && !(event.venueName || event.address).includes(event.city)}, {event.city}{/if}
			{/if}
			{#if km != null}<span class="km"> · {km < 1 ? '< 1' : fmtNum(Math.round(km))} km</span>{/if}
		</p>
		<div class="tags">
			<span class="badge badge-cat"><CategoryIcon size={16} aria-hidden="true" />{CATEGORIES[event.category]}</span>
			{#if running}<span class="badge">{running}</span>{/if}
			{#if isFree(event)}<span class="badge">Gratis</span>{/if}
			{#if isForKids(event) && event.category !== 'kids'}<span class="badge">Per bambini</span>{/if}
		</div>
	</div>
	{#if event.imageUrl}
		<img class="thumb" src={event.imageUrl} alt="" loading="lazy" decoding="async" width="96" height="96" referrerpolicy="no-referrer" />
	{/if}
	<div class="fav"><FavoriteButton id={event.id} title={event.title} /></div>
</article>

<style>
	.ev {
		position: relative;
		display: grid;
		grid-template-columns: auto 1fr auto;
		gap: var(--space-3);
		padding: var(--space-3) var(--space-7) var(--space-3) var(--space-3);
		transition:
			border-color var(--dur),
			background-color var(--dur);
	}
	.ev:hover,
	.highlighted {
		border-color: var(--accent-border);
		background: var(--accent-soft);
	}
	.ev:focus-within {
		border-color: var(--accent);
	}
	.date {
		display: grid;
		place-content: center;
		width: var(--space-6);
		height: var(--space-6);
		border-radius: var(--radius-sm);
		background: var(--accent-soft);
		color: var(--accent-hover);
		text-align: center;
		line-height: 1;
	}
	.d {
		font: var(--fw-strong) var(--text-xl) / 1 var(--font-display);
	}
	.m {
		font-size: var(--text-xs);
		font-weight: var(--fw-regular);
		margin-top: var(--space-1);
	}
	.body {
		min-width: 0;
	}
	.when {
		margin: 0 0 var(--space-1);
		font-size: var(--text-sm);
		font-weight: var(--fw-strong);
		color: var(--muted);
	}
	.live {
		color: var(--text);
	}
	h3 {
		margin: 0 0 var(--space-1);
		font-size: var(--text-lg);
		overflow-wrap: anywhere;
	}
	h3 a {
		color: var(--text);
		text-decoration: none;
	}
	/* Tutta la card è cliccabile, ma resta un solo link per lo screen reader. */
	.stretched::after {
		content: '';
		position: absolute;
		inset: 0;
		border-radius: var(--radius);
	}
	.stretched:focus-visible {
		outline: none;
	}
	.stretched:focus-visible::after {
		outline: 2px solid var(--focus);
		outline-offset: 2px;
	}
	.where {
		margin: 0 0 var(--space-2);
		font-size: var(--text-sm);
		color: var(--muted);
		overflow-wrap: anywhere;
	}
	.km {
		white-space: nowrap;
		font-variant-numeric: tabular-nums;
	}
	.tags {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-1) var(--space-3);
	}
	.thumb {
		width: var(--space-7);
		height: var(--space-7);
		object-fit: cover;
		border-radius: var(--radius-sm);
		background: var(--surface-2);
		align-self: center;
	}
	.fav {
		position: absolute;
		top: var(--space-1);
		right: var(--space-1);
		z-index: 1;
	}
	@media (min-width: 520px) {
		.thumb {
			width: calc(var(--space-7) * 1.5);
			height: calc(var(--space-7) * 1.5);
		}
	}
</style>
