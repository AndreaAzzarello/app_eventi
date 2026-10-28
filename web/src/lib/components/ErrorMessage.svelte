<script lang="ts">
	import CircleAlert from '@lucide/svelte/icons/circle-alert';
	import type { Snippet } from 'svelte';

	// L'errore non è mai solo colore: icona e testo vanno sempre insieme.
	let { children, id }: { children: Snippet; id?: string } = $props();
</script>

<p class="error" role="alert" {id}>
	<CircleAlert size={16} aria-hidden="true" />
	<span>{@render children()}</span>
</p>

<style>
	.error {
		display: flex;
		align-items: flex-start;
		gap: var(--space-2);
		margin: 0;
		color: var(--danger);
		font-size: var(--text-sm);
	}
	.error :global(svg) {
		flex: none;
		margin-top: var(--space-1);
	}
</style>
