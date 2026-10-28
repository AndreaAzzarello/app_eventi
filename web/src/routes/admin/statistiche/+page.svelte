<script lang="ts">
	import { onMount } from 'svelte';
	import ErrorMessage from '$lib/components/ErrorMessage.svelte';
	import { listStats, type RegionMonth } from '$lib/admin';
	import { fmtNum, monthDelta, monthKeys, monthName } from '$lib/format';

	const keys = monthKeys();
	let rows: { name: string; cur: RegionMonth; prev: RegionMonth | null }[] | null = $state(null);
	let failed = $state(false);

	onMount(async () => {
		try {
			const all = await listStats([keys.cur, keys.prev]);
			rows = all
				.filter((r) => r.month === keys.cur)
				.map((cur) => ({ name: cur.name, cur, prev: all.find((p) => p.month === keys.prev && p.region === cur.region) ?? null }))
				.sort((a, b) => a.name.localeCompare(b.name, 'it'));
		} catch {
			failed = true;
		}
	});
</script>

<h1>Statistiche</h1>
<p class="muted">Eventi attivi a {monthName(keys.cur)} per regione, contati ogni giorno dall’import. La variazione è rispetto a {monthName(keys.prev)}.</p>

{#if failed}
	<ErrorMessage>Non riesco a leggere le statistiche.</ErrorMessage>
{:else if !rows}
	<p class="muted" role="status">Carico…</p>
{:else if !rows.length}
	<p class="muted">Nessuna statistica per {monthName(keys.cur)}: compaiono dopo il prossimo import.</p>
{:else}
	<div class="scroll">
	<table>
		<thead>
			<tr>
				<th scope="col">Regione</th>
				<th scope="col" class="num">Eventi</th>
				<th scope="col" class="num">Variazione</th>
				<th scope="col" class="num">Comuni</th>
				<th scope="col" class="cities">Città principali</th>
			</tr>
		</thead>
		<tbody>
			{#each rows as r (r.cur.region)}
				<tr>
					<th scope="row"><a href="/regione/{r.cur.region}">{r.name}</a></th>
					<td class="num">{fmtNum(r.cur.events)}</td>
					<td class="num">{monthDelta(r.cur.events, r.prev?.events ?? null) || '–'}</td>
					<td class="num">{fmtNum(r.cur.comuni)}</td>
					<td class="cities">{r.cur.cities.slice(0, 3).map((c) => `${c.name} ${fmtNum(c.n)}`).join(', ')}</td>
				</tr>
			{/each}
		</tbody>
	</table>
	</div>
{/if}

<style>
	.scroll {
		overflow-x: auto;
	}
	@media (max-width: 479px) {
		.cities {
			display: none;
		}
		th,
		td {
			padding-inline: var(--space-1);
		}
	}
	table {
		width: 100%;
		border-collapse: collapse;
		font-size: var(--text-sm);
	}
	th,
	td {
		padding: var(--space-2) var(--space-3);
		border-bottom: 1px solid var(--border);
		text-align: left;
		vertical-align: top;
	}
	thead th {
		font-weight: var(--fw-strong);
		color: var(--muted);
	}
	tbody th {
		font-weight: var(--fw-regular);
	}
	.num {
		text-align: right;
		font-variant-numeric: tabular-nums;
	}
</style>
