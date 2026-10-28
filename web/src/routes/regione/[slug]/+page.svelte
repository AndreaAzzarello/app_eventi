<script lang="ts">
	import { page } from '$app/state';
	import Seo from '$lib/components/Seo.svelte';
	import { cityPath } from '$lib/event';
	import { fmtNum } from '$lib/format';

	let { data } = $props();
	const withEvents = $derived(data.comuni.filter((c) => c.events > 0));
	const without = $derived(data.comuni.filter((c) => !c.events));
	const count = (n: number) => (n === 1 ? '1 evento' : `${fmtNum(n)} eventi`);
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
	{#if data.month}<p class="month">{data.month}</p>{/if}

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
	.month {
		margin: 0 0 var(--space-4);
		font-variant-numeric: tabular-nums;
	}
	.crumbs {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
		padding: var(--space-4) 0 var(--space-2);
		font-size: var(--text-sm);
		color: var(--muted);
	}
	.lead {
		font-size: var(--text-md);
		margin-bottom: var(--space-4);
	}
	.comuni {
		list-style: none;
		margin: 0 0 var(--space-4);
		padding: 0;
		display: grid;
		gap: var(--space-2);
	}
	.comune {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: var(--space-3);
		min-height: var(--control);
		padding: var(--space-2) var(--space-3);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		background: var(--surface);
		color: var(--text);
		text-decoration: none;
	}
	.comune:hover {
		border-color: var(--accent);
	}
	.name {
		font-weight: var(--fw-strong);
		min-width: 0;
		overflow-wrap: anywhere;
	}
	.n {
		color: var(--muted);
		font-size: var(--text-sm);
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
	}
</style>
