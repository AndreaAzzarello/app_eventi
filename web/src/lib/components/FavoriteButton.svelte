<script lang="ts">
	import Heart from '@lucide/svelte/icons/heart';
	import { favorites } from '$lib/session.svelte';
	import { toast } from '$lib/toast.svelte';

	let { id, title, label = false }: { id: string; title: string; label?: boolean } = $props();
	const on = $derived(favorites.has(id));

	async function click(e: MouseEvent) {
		e.preventDefault();
		e.stopPropagation();
		try {
			await favorites.toggle(id);
		} catch {
			toast('Non sono riuscito a salvare il preferito. Riprova.');
		}
	}
</script>

<button
	type="button"
	class="fav"
	class:on
	class:with-label={label}
	aria-pressed={on}
	aria-label={label ? undefined : on ? `Togli “${title}” dai preferiti` : `Aggiungi “${title}” ai preferiti`}
	onclick={click}
>
	<Heart size={label ? 16 : 20} fill={on ? 'currentColor' : 'none'} aria-hidden="true" />
	{#if label}<span>{on ? 'Nei preferiti' : 'Salva'}</span>{/if}
</button>

<style>
	.fav {
		display: inline-grid;
		place-items: center;
		grid-auto-flow: column;
		gap: var(--space-2);
		min-width: var(--control);
		min-height: var(--control);
		border-radius: var(--radius);
		border: 1px solid transparent;
		background: var(--surface);
		color: var(--muted);
		cursor: pointer;
		transition:
			color var(--dur),
			background-color var(--dur);
	}
	.fav:hover {
		color: var(--accent);
		background: var(--surface-2);
	}
	.on {
		color: var(--accent);
	}
	.with-label {
		padding: 0 var(--space-3);
		border-color: var(--border);
		font: var(--fw-strong) var(--text-md) var(--font-body);
		color: var(--text);
	}
	.with-label.on {
		color: var(--accent);
		border-color: currentColor;
	}
</style>
