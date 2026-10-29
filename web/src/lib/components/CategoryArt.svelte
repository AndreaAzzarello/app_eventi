<script lang="ts">
	import { CATEGORY_ICONS } from '$lib/categoryIcons';
	import type { Category } from '$lib/event';

	// Placeholder disegnato per chi non ha un'immagine: un motivo geometrico per categoria nella sua tinta, con l'icona in un medaglione.
	// Il riquadro prende dimensione e raggio dal genitore. È decorativo: il nome della categoria sta già nel testo accanto.
	let { category, size = 'card' }: { category: Category; size?: 'card' | 'hero' } = $props();
	const Icon = $derived(CATEGORY_ICONS[category]);
	const N = [0, 1, 2, 3, 4, 5];
	const CONFETTI = [
		[14, 20, 4],
		[44, 12, 3],
		[78, 24, 5],
		[24, 54, 3],
		[60, 50, 4],
		[86, 70, 3],
		[16, 84, 5],
		[50, 82, 3]
	];
</script>

<div class="art" data-cat={category} data-size={size} aria-hidden="true">
	<svg viewBox="0 0 96 96" preserveAspectRatio="xMidYMid slice" focusable="false">
		{#if category === 'music'}
			{#each N as i (i)}<path d="M-8 {10 + i * 16} q 10 -9 20 0 t 20 0 t 20 0 t 20 0 t 20 0 t 20 0" />{/each}
		{:else if category === 'food'}
			{#each N as r (r)}{#each N as c (c)}<circle class="fill" cx={8 + c * 16 + (r % 2) * 8} cy={8 + r * 16} r="2.5" />{/each}{/each}
		{:else if category === 'culture'}
			{#each [0, 1, 2, 3] as i (i)}<path d="M{i * 28 - 6} 100 V60 a11 11 0 0 1 22 0 V100" />{/each}
			<path d="M0 60 H96" />
		{:else if category === 'sport'}
			{#each N as i (i)}<path d="M{i * 20 - 24} 100 L{i * 20 + 72} 4" />{/each}
		{:else if category === 'kids'}
			{#each CONFETTI as [x, y, r], i (i)}
				{#if i % 2}<rect class="fill" x={x - r} y={y - r} width={r * 2} height={r * 2} transform="rotate(20 {x} {y})" />{:else}<circle class="fill" cx={x} cy={y} {r} />{/if}
			{/each}
		{:else if category === 'market'}
			{#each N as i (i)}<rect class="fill" x={i * 16} y="0" width="8" height="96" />{/each}
		{:else}
			{#each N as r (r)}{#each N as c (c)}<path d="M{c * 16 + 5} {r * 16 + 8} h6 M{c * 16 + 8} {r * 16 + 5} v6" />{/each}{/each}
		{/if}
	</svg>
	<span class="medal"><Icon size={size === 'hero' ? 24 : 20} aria-hidden="true" /></span>
</div>

<style>
	.art {
		position: relative;
		width: 100%;
		height: 100%;
		overflow: hidden;
		border-radius: inherit;
		background: var(--tint);
		color: var(--ink);
	}
	svg {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		fill: none;
		stroke: currentColor;
		stroke-width: 1.5;
		stroke-linecap: round;
		opacity: 0.35;
	}
	.fill {
		fill: currentColor;
		stroke: none;
	}
	.medal {
		position: absolute;
		inset: 0;
		margin: auto;
		display: grid;
		place-items: center;
		width: var(--control-sm);
		height: var(--control-sm);
		border-radius: var(--radius-full);
		background: var(--surface);
		border: 1px solid var(--border);
	}
	[data-size='hero'] .medal {
		width: var(--control);
		height: var(--control);
	}
</style>
