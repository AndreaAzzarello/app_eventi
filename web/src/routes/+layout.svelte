<script lang="ts">
	import '@fontsource/fraunces/latin-600.css';
	import '../app.css';
	import frauncesUrl from '@fontsource/fraunces/files/fraunces-latin-600-normal.woff2?url';
	import { onMount } from 'svelte';
	import { dev } from '$app/environment';
	import { page } from '$app/state';
	import Icon from '$lib/components/Icon.svelte';
	import { favorites, session } from '$lib/session.svelte';
	import { KEYS, readJson, writeJson } from '$lib/storage';
	import { dismiss, toasts } from '$lib/toast.svelte';

	let { children } = $props();
	let theme = $state<'light' | 'dark' | null>(null);

	onMount(() => {
		theme = readJson(KEYS.theme, null);
		favorites.load();
		session.resume();
		if (!dev && 'serviceWorker' in navigator) navigator.serviceWorker.register('/service-worker.js');
	});

	function toggleTheme() {
		const current =
			theme ?? (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
		theme = current === 'dark' ? 'light' : 'dark';
		document.documentElement.dataset.theme = theme;
		writeJson(KEYS.theme, theme);
	}

	const nav = [
		{ href: '/proponi', label: 'Proponi', icon: 'plus' },
		{ href: '/preferiti', label: 'Preferiti', icon: 'heart' }
	] as const;
	const active = (href: string) => page.url.pathname.startsWith(href);
</script>

<svelte:head>
	<link rel="preload" href={frauncesUrl} as="font" type="font/woff2" crossorigin="anonymous" />
</svelte:head>

<a class="skip" href="#main">Vai al contenuto</a>

<header class="site-header">
	<div class="container bar">
		<a class="brand" href="/" aria-label="Eventi Vicini, home">
			<svg viewBox="0 0 32 32" width="30" height="30" aria-hidden="true">
				<path fill="var(--brand)" d="M16 2a11 11 0 0 0-11 11c0 8.2 11 17 11 17s11-8.8 11-17A11 11 0 0 0 16 2z" />
				<rect x="10.5" y="9" width="11" height="10" rx="2" fill="none" stroke="var(--brand-ink)" stroke-width="2" />
				<path d="M10.5 12.5h11M13.5 7.5v3M18.5 7.5v3" stroke="var(--brand-ink)" stroke-width="2" stroke-linecap="round" />
			</svg>
			<span>Eventi <em>Vicini</em></span>
		</a>
		<nav aria-label="Principale">
			{#each nav as item (item.href)}
				<a href={item.href} class="nav-link" aria-current={active(item.href) ? 'page' : undefined}>
					<Icon name={item.icon} size={18} />
					<span class="nav-text">{item.label}</span>
					{#if item.href === '/preferiti' && favorites.ids.length}<span class="count">{favorites.ids.length}</span>{/if}
				</a>
			{/each}
			{#if session.user}
				<a href="/account" class="nav-link" aria-current={active('/account') ? 'page' : undefined}>
					<span class="avatar" aria-hidden="true">{(session.user.name || session.user.email || '?')[0].toUpperCase()}</span>
					<span class="nav-text">Account</span>
				</a>
				{#if session.user.isAdmin}
					<a href="/admin" class="nav-link" aria-current={active('/admin') ? 'page' : undefined}>
						<Icon name="sliders" size={18} /><span class="nav-text">Admin</span>
					</a>
				{/if}
			{:else}
				<a href="/accedi" class="nav-link" aria-current={active('/accedi') ? 'page' : undefined}>
					<Icon name="user" size={18} /><span class="nav-text">Accedi</span>
				</a>
			{/if}
			<button class="nav-link theme" onclick={toggleTheme} aria-label="Cambia tema chiaro/scuro">
				<span class="sun"><Icon name="sun" size={18} /></span><span class="moon"><Icon name="moon" size={18} /></span>
			</button>
		</nav>
	</div>
</header>

<main id="main" tabindex="-1">
	{@render children()}
</main>

<footer class="site-footer">
	<div class="container foot">
		<div>
			<p class="foot-brand">Eventi <em>Vicini</em></p>
			<p class="muted">L’agenda degli eventi vicino a te. Gratis, senza pubblicità e senza tracciamento.</p>
		</div>
		<nav aria-label="Informazioni">
			<a href="/proponi">Proponi un evento</a>
			<a href="/privacy">Privacy</a>
			<a href="/termini">Termini</a>
		</nav>
		<p class="muted small">
			Eventi dai siti istituzionali dei Comuni (fonte citata in ogni scheda) e dagli utenti. Mappe ©
			<a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>.
		</p>
	</div>
</footer>

<div class="toasts" aria-live="polite" aria-atomic="false">
	{#each toasts as t (t.id)}
		<div class="toast" role="status">
			<span>{t.text}</span>
			{#if t.action}<a class="btn btn-primary btn-sm" href={t.action.href} onclick={() => dismiss(t.id)}>{t.action.label}</a>{/if}
			<button class="btn btn-ghost btn-sm close" onclick={() => dismiss(t.id)} aria-label="Chiudi avviso"><Icon name="x" size={16} /></button>
		</div>
	{/each}
</div>

<style>
	.skip {
		position: absolute;
		left: 8px;
		top: -60px;
		z-index: 100;
		padding: 0.6rem 1rem;
		background: var(--text);
		color: var(--bg);
		border-radius: var(--radius-sm);
	}
	.skip:focus {
		top: 8px;
	}
	.site-header {
		position: sticky;
		top: 0;
		z-index: 1000;
		background: color-mix(in srgb, var(--bg) 88%, transparent);
		backdrop-filter: saturate(1.4) blur(10px);
		-webkit-backdrop-filter: saturate(1.4) blur(10px);
		border-bottom: 1px solid var(--border);
	}
	.bar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.5rem;
		height: var(--header-h);
	}
	.brand {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		color: var(--text);
		text-decoration: none;
		font: 650 1.2rem/1 var(--font-display);
		white-space: nowrap;
		min-width: 0;
	}
	.brand span {
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.brand svg {
		flex-shrink: 0;
	}
	.brand em,
	.foot-brand em {
		font-style: italic;
		color: var(--brand);
	}
	nav[aria-label='Principale'] {
		display: flex;
		align-items: center;
		gap: 0.15rem;
		flex-shrink: 0;
	}
	.nav-link {
		position: relative;
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		min-height: 44px;
		min-width: 44px;
		justify-content: center;
		padding: 0 0.6rem;
		border: none;
		border-radius: 999px;
		background: none;
		color: var(--text);
		font: 600 0.92rem var(--font-body);
		text-decoration: none;
		cursor: pointer;
	}
	.nav-link:hover {
		background: var(--surface-2);
		color: var(--text);
	}
	.nav-link[aria-current='page'] {
		color: var(--brand);
	}
	.nav-text {
		position: absolute;
		width: 1px;
		height: 1px;
		overflow: hidden;
		clip: rect(0 0 0 0);
		white-space: nowrap;
	}
	.count {
		position: absolute;
		top: 4px;
		right: 2px;
		min-width: 18px;
		height: 18px;
		padding: 0 4px;
		border-radius: 999px;
		background: var(--brand);
		color: var(--brand-ink);
		font-size: 0.7rem;
		line-height: 18px;
		text-align: center;
	}
	.avatar {
		display: grid;
		place-items: center;
		width: 26px;
		height: 26px;
		border-radius: 50%;
		background: var(--brand);
		color: var(--brand-ink);
		font-size: 0.8rem;
	}
	.theme .moon {
		display: none;
	}
	:global([data-theme='dark']) .theme .sun {
		display: none;
	}
	:global([data-theme='dark']) .theme .moon {
		display: inline;
	}
	@media (prefers-color-scheme: dark) {
		:global(:root:not([data-theme='light'])) .theme .sun {
			display: none;
		}
		:global(:root:not([data-theme='light'])) .theme .moon {
			display: inline;
		}
	}
	@media (max-width: 419px) {
		.brand {
			font-size: 1.05rem;
			gap: 0.4rem;
		}
		nav[aria-label='Principale'] {
			gap: 0;
		}
		.nav-link {
			padding: 0;
		}
	}
	@media (min-width: 720px) {
		.nav-text {
			position: static;
			width: auto;
			height: auto;
			overflow: visible;
			clip: auto;
		}
		.count {
			position: static;
		}
	}
	main {
		min-height: calc(100vh - var(--header-h) - 200px);
		outline: none;
	}
	.site-footer {
		margin-top: 4rem;
		border-top: 1px solid var(--border);
		background: var(--surface-2);
		padding: 2rem 0 5rem;
	}
	.foot {
		display: grid;
		gap: 1rem;
	}
	.foot-brand {
		font: 650 1.15rem var(--font-display);
		margin: 0 0 0.3rem;
	}
	.foot nav {
		display: flex;
		flex-wrap: wrap;
		gap: 0.25rem 1.25rem;
	}
	.foot nav a {
		display: inline-flex;
		align-items: center;
		min-height: 44px;
		color: var(--text);
		font-weight: 600;
	}
	.small {
		font-size: 0.85rem;
	}
	.small a {
		color: inherit;
	}
	@media (min-width: 720px) {
		.foot {
			grid-template-columns: 2fr 1fr;
		}
		.small {
			grid-column: 1 / -1;
		}
	}
	.toasts {
		position: fixed;
		left: 50%;
		bottom: max(16px, env(safe-area-inset-bottom));
		transform: translateX(-50%);
		z-index: 2000;
		display: grid;
		gap: 0.5rem;
		width: min(560px, calc(100vw - 32px));
	}
	.toast {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 0.5rem 0.75rem;
		padding: 0.7rem 0.6rem 0.7rem 1rem;
		border-radius: var(--radius);
		background: var(--text);
		color: var(--bg);
		box-shadow: var(--shadow-lift);
		animation: rise 0.25s var(--ease);
	}
	.toast span {
		flex: 1 1 200px;
	}
	.toast .close {
		--b-fg: var(--bg);
	}
	@keyframes rise {
		from {
			transform: translateY(12px);
			opacity: 0;
		}
	}
</style>
