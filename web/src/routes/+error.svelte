<script lang="ts">
	import { page } from '$app/state';
	import Seo from '$lib/components/Seo.svelte';
</script>

<Seo title={page.status === 404 ? 'Pagina non trovata' : 'Errore'} noindex />

<div class="container narrow err">
	<p class="code" aria-hidden="true">{page.status}</p>
	<h1>{page.status === 404 ? 'Qui non c’è niente' : 'Qualcosa è andato storto'}</h1>
	<p class="muted">{page.error?.message}</p>
	<a class="btn btn-primary" href="/">Torna agli eventi</a>
</div>

<style>
	.err {
		padding: var(--space-7) var(--space-3);
		text-align: center;
	}
	.code {
		font-family: var(--font-display);
		font-weight: var(--fw-strong);
		font-size: var(--text-3xl);
		line-height: var(--lh-tight);
		color: var(--accent);
		margin: 0 0 var(--space-2);
	}
</style>
