<script lang="ts">
	import { favorites } from '$lib/session.svelte';
	import { toast } from '$lib/toast.svelte';
	import Icon from './Icon.svelte';

	let { id, title, label = false }: { id: string; title: string; label?: boolean } = $props();
	const on = $derived(favorites.has(id));
	let pop = $state(false);

	async function click(e: MouseEvent) {
		e.preventDefault();
		e.stopPropagation();
		try {
			if (await favorites.toggle(id)) {
				pop = true;
				setTimeout(() => (pop = false), 400);
			}
		} catch {
			toast('Non sono riuscito a salvare il preferito. Riprova.');
		}
	}
</script>

<button
	type="button"
	class="fav"
	class:on
	class:pop
	class:with-label={label}
	aria-pressed={on}
	aria-label={label ? undefined : on ? `Togli “${title}” dai preferiti` : `Aggiungi “${title}” ai preferiti`}
	onclick={click}
>
	<Icon name="heart" filled={on} size={label ? 18 : 20} />
	{#if label}<span>{on ? 'Nei preferiti' : 'Salva'}</span>{/if}
</button>

<style>
	.fav {
		display: inline-grid;
		place-items: center;
		grid-auto-flow: column;
		gap: 0.4em;
		min-width: 44px;
		min-height: 44px;
		border-radius: 999px;
		border: 1px solid transparent;
		background: color-mix(in srgb, var(--surface) 88%, transparent);
		color: var(--muted);
		cursor: pointer;
		transition:
			color 0.15s,
			transform 0.2s var(--ease),
			background-color 0.15s;
	}
	.fav:hover {
		color: var(--brand);
		background: var(--surface-2);
	}
	.on {
		color: var(--brand);
	}
	.pop {
		transform: scale(1.18);
	}
	.with-label {
		padding: 0 1rem;
		border-color: var(--border);
		font: 600 0.95rem var(--font-body);
		color: var(--text);
	}
	.with-label.on {
		color: var(--brand);
		border-color: currentColor;
	}
</style>
