<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { authMessage, completeEmailLink, isEmailLink, safeNext, savedEmail } from '$lib/auth';
	import LoginPanel from '$lib/components/LoginPanel.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import { session } from '$lib/session.svelte';

	const next = safeNext(page.url.searchParams.get('next'));
	let linkPending = $state(false);
	let email = $state('');
	let busy = $state(false);
	let error = $state('');

	onMount(async () => {
		await session.start();
		if (await isEmailLink(location.href)) {
			email = savedEmail();
			linkPending = true;
			// Stesso dispositivo: l'email è già nota, si entra subito.
			if (email) await finish();
		}
	});

	async function finish(e?: SubmitEvent) {
		e?.preventDefault();
		busy = true;
		error = '';
		try {
			await completeEmailLink(email, location.href);
			linkPending = false;
		} catch (err) {
			error = authMessage(err);
		} finally {
			busy = false;
		}
	}

	// Appena c'è un utente, torna dove era.
	$effect(() => {
		if (session.user && !linkPending) goto(next, { replaceState: true });
	});
</script>

<Seo title="Accedi" noindex />

<div class="container page">
	<div class="intro">
		<h1>Il tuo account</h1>
		<p class="muted">
			L’accesso è facoltativo: serve per ritrovare i preferiti su ogni dispositivo e per proporre eventi.
		</p>
	</div>
	{#if linkPending}
		<form class="card confirm" onsubmit={finish}>
			<h2>Conferma la tua email</h2>
			<p class="muted">Hai aperto il link su un altro dispositivo: scrivi l’email a cui l’hai ricevuto.</p>
			<div class="field">
				<label for="confirm-email">Email</label>
				<input id="confirm-email" type="email" autocomplete="email" required bind:value={email} />
			</div>
			<button class="btn btn-primary" disabled={busy}>{busy ? 'Accesso…' : 'Accedi'}</button>
			{#if error}<p class="error-text" role="alert">{error}</p>{/if}
		</form>
	{:else if session.status !== 'ready' || session.user}
		<p class="muted" role="status">Un momento…</p>
	{:else}
		<LoginPanel {next} />
	{/if}
</div>

<style>
	.page {
		display: grid;
		gap: 1.5rem;
		padding-top: 2rem;
		justify-items: start;
	}
	@media (min-width: 900px) {
		.page {
			grid-template-columns: 1fr 440px;
			align-items: start;
		}
	}
	.confirm {
		padding: 1.5rem;
		max-width: 440px;
		width: 100%;
	}
</style>
