<script lang="ts">
	import FavoritesList from '$lib/components/FavoritesList.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import { session } from '$lib/session.svelte';
</script>

<Seo title="I tuoi preferiti" noindex />

<div class="container narrow page">
	<h1>I tuoi preferiti</h1>
	{#if session.status === 'ready' && !session.user}
		<p class="notice">
			Sono salvati solo su questo dispositivo.
			<a href="/accedi?next=/preferiti">Accedi</a> per ritrovarli ovunque: quelli che hai già verranno uniti al tuo account.
		</p>
	{/if}
	<FavoritesList />
</div>

<style>
	.page {
		padding-top: 1.5rem;
	}
	.notice {
		margin-bottom: 1.25rem;
	}
</style>
