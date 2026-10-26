<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import LoginPanel from '$lib/components/LoginPanel.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import { session } from '$lib/session.svelte';

	let { children } = $props();
	onMount(() => {
		session.start();
	});
	const tabs = [
		{ href: '/admin', label: 'Eventi' },
		{ href: '/admin/proposte', label: 'Proposte' }
	];
</script>

<Seo title="Admin" noindex />

<div class="container page">
	{#if session.status !== 'ready'}
		<p class="muted" role="status">Verifico l’accesso…</p>
	{:else if !session.user}
		<h1>Area riservata</h1>
		<LoginPanel next={page.url.pathname} />
	{:else if !session.user.isAdmin}
		<h1>Area riservata</h1>
		<p class="notice">Questo account non ha i permessi di amministrazione.</p>
	{:else}
		<nav class="tabs" aria-label="Sezioni admin">
			{#each tabs as t (t.href)}
				<a href={t.href} aria-current={page.url.pathname === t.href ? 'page' : undefined}>{t.label}</a>
			{/each}
		</nav>
		{@render children()}
	{/if}
</div>

<style>
	.page {
		padding-top: 1.5rem;
	}
	.tabs {
		display: flex;
		gap: 0.25rem;
		border-bottom: 1px solid var(--border);
		margin-bottom: 1.5rem;
	}
	.tabs a {
		display: inline-flex;
		align-items: center;
		min-height: 44px;
		padding: 0 1rem;
		color: var(--muted);
		font-weight: 600;
		text-decoration: none;
		border-bottom: 3px solid transparent;
		margin-bottom: -1px;
	}
	.tabs a[aria-current='page'] {
		color: var(--brand);
		border-color: var(--brand);
	}
</style>
