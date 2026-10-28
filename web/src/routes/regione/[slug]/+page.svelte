<script lang="ts">
	import { page } from '$app/state';
	import Seo from '$lib/components/Seo.svelte';
	import { cityPath } from '$lib/event';

	let { data } = $props();
	const withEvents = $derived(data.comuni.filter((c) => c.events > 0));
	const without = $derived(data.comuni.filter((c) => !c.events));
	const count = (n: number) => (n === 1 ? '1 evento' : `${n} eventi`);
</script>

<Seo
	title={`Eventi in ${data.name}`}
	description={`${count(data.total)} in programma in ${data.comuni.length} comuni di ${data.name}: concerti, sagre, mostre, mercatini e attività per bambini.`}
	path={page.url.pathname}
/>

<div class="container narrow">
	<nav class="crumbs" aria-label="Percorso">
		<a href="/">Eventi Vicini</a> <span aria-hidden="true">›</span>
		<span aria-current="page">{data.name}</span>
	</nav>
	<h1>Eventi in {data.name}</h1>
	<p class="muted lead">{count(data.total)} in programma in {data.comuni.length} comuni coperti.</p>

	<ul class="comuni">
		{#each withEvents as c (c.slug)}
			<li>
				<a class="comune" href={cityPath(c.slug)}>
					<span class="name">{c.name}{c.alt ? ` / ${c.alt}` : ''}{c.province ? ` (${c.province})` : ''}</span>
					<span class="n">{count(c.events)}</span>
				</a>
			</li>
		{/each}
	</ul>
	{#if without.length}
		<h2>Per ora senza eventi</h2>
		<p class="muted">{without.map((c) => (c.alt ? `${c.name} / ${c.alt}` : c.name)).join(', ')}.</p>
	{/if}
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
	.comuni {
		list-style: none;
		margin: 0 0 1.5rem;
		padding: 0;
		display: grid;
		gap: 0.4rem;
	}
	.comune {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 1rem;
		min-height: 44px;
		padding: 0.5rem 0.9rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		background: var(--surface);
		color: var(--text);
		text-decoration: none;
	}
	.comune:hover {
		border-color: var(--brand);
	}
	.name {
		font-weight: 600;
		min-width: 0;
		overflow-wrap: anywhere;
	}
	.n {
		color: var(--muted);
		font-size: 0.9rem;
		white-space: nowrap;
	}
</style>
