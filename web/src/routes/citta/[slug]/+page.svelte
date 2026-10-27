<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import EventList from '$lib/components/EventList.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import { compareEvents } from '$lib/event';

	let { data } = $props();
	let now = $state(Date.now());
	onMount(() => (now = Date.now()));
	const where = $derived(data.province ? `${data.city} (${data.province})` : data.city);
	const visible = $derived(data.events.filter((e) => e.endTime >= now).sort(compareEvents(now)));
</script>

<Seo
	title={`Eventi a ${data.city}`}
	description={`${data.events.length} eventi in programma a ${where}${data.region ? `, ${data.region}` : ''}: concerti, sagre, mostre, mercatini e attività per bambini.`}
	path={page.url.pathname}
/>

<div class="container narrow">
	<nav class="crumbs" aria-label="Percorso">
		<a href="/">Eventi Vicini</a> <span aria-hidden="true">›</span>
		{#if data.region}<span>{data.region}</span> <span aria-hidden="true">›</span>{/if}
		<span aria-current="page">{data.city}</span>
	</nav>
	<h1>Eventi a {data.city}</h1>
	<p class="muted lead">
		{visible.length === 1 ? 'Un evento in programma' : `${visible.length} eventi in programma`} a {where}.
	</p>
	<EventList events={visible} {now}>
		{#snippet empty()}
			<h2>Per ora niente in programma</h2>
			<p class="muted">Conosci un evento a {data.city}? <a href="/proponi">Proponilo</a>.</p>
		{/snippet}
	</EventList>
</div>

<style>
	.crumbs {
		display: flex;
		flex-wrap: wrap;
		gap: 0.4rem;
		padding: 1.25rem 0 0.5rem;
		font-size: 0.9rem;
		color: var(--muted);
	}
	.lead {
		font-size: 1.05rem;
		margin-bottom: 1.25rem;
	}
</style>
