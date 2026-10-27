<script lang="ts">
	import { formatTime, romeParts, shortDate, shortDay } from '$lib/dates';
	import { CATEGORIES, eventPath, isForKids, isFree, runningLabel, type Event } from '$lib/event';
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
			{shortDay(event.startTime, now)} · {formatTime(event.startTime)}{#if running === 'Mostra'} · fino al {shortDate(event.endTime)}{/if}
		</p>
		<h3><a href={eventPath(event)} class="stretched">{event.title}</a></h3>
		<p class="where">
			{#if event.approxLocation}
				{event.venueName ? `${event.venueName} · ` : ''}<span class="approx">Luogo da confermare</span>{#if event.city}, {event.city}{/if}
			{:else}
				{event.venueName || event.address}{#if event.city && !(event.venueName || event.address).includes(event.city)}, {event.city}{/if}
			{/if}
			{#if km != null}<span class="km"> · {km < 1 ? '< 1' : Math.round(km)} km</span>{/if}
		</p>
		<div class="tags">
			<span class="badge badge-brand">{CATEGORIES[event.category]}</span>
			{#if running}<span class="badge">{running}</span>{/if}
			{#if isFree(event)}<span class="badge badge-free">Gratis</span>{/if}
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
		gap: 0.9rem;
		padding: 0.9rem 3.2rem 0.9rem 0.9rem;
		transition:
			transform 0.18s var(--ease),
			box-shadow 0.18s var(--ease),
			border-color 0.18s;
	}
	.ev:hover,
	.highlighted {
		transform: translateY(-2px);
		box-shadow: var(--shadow-lift);
		border-color: color-mix(in srgb, var(--brand) 35%, var(--border));
	}
	.ev:focus-within {
		border-color: var(--brand);
	}
	.date {
		display: grid;
		place-content: center;
		width: 3.4rem;
		height: 3.6rem;
		border-radius: var(--radius-sm);
		background: var(--brand-soft);
		color: var(--brand-strong);
		text-align: center;
		line-height: 1;
	}
	:global([data-theme='dark']) .date {
		color: var(--brand);
	}
	@media (prefers-color-scheme: dark) {
		:global(:root:not([data-theme='light'])) .date {
			color: var(--brand);
		}
	}
	.d {
		font: 650 1.45rem/1 var(--font-display);
	}
	.m {
		font-size: 0.72rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		margin-top: 0.2rem;
	}
	.body {
		min-width: 0;
	}
	.when {
		margin: 0 0 0.15rem;
		font-size: 0.82rem;
		font-weight: 600;
		color: var(--muted);
		text-transform: capitalize;
	}
	.live {
		color: var(--ok);
	}
	h3 {
		margin: 0 0 0.2rem;
		font-size: 1.08rem;
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
		outline: 3px solid var(--brand);
		outline-offset: 2px;
	}
	.where {
		margin: 0 0 0.45rem;
		font-size: 0.9rem;
		color: var(--muted);
		overflow-wrap: anywhere;
	}
	.approx {
		font-style: italic;
	}
	.km {
		white-space: nowrap;
	}
	.tags {
		display: flex;
		flex-wrap: wrap;
		gap: 0.35rem;
	}
	.thumb {
		width: 72px;
		height: 72px;
		object-fit: cover;
		border-radius: var(--radius-sm);
		background: var(--surface-2);
		align-self: center;
	}
	.fav {
		position: absolute;
		top: 0.4rem;
		right: 0.4rem;
		z-index: 1;
	}
	@media (min-width: 520px) {
		.thumb {
			width: 96px;
			height: 96px;
		}
	}
</style>
