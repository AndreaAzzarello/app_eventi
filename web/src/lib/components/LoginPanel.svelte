<script lang="ts">
	import { authMessage, sendEmailLink, signInWithGoogle } from '$lib/auth';
	import Mail from '@lucide/svelte/icons/mail';
	import ErrorMessage from './ErrorMessage.svelte';

	let { next = '/', title = 'Accedi', intro = '' }: { next?: string; title?: string; intro?: string } = $props();

	let email = $state('');
	let sent = $state(false);
	let busy = $state<'google' | 'email' | null>(null);
	let error = $state('');

	async function google() {
		busy = 'google';
		error = '';
		try {
			await signInWithGoogle();
		} catch (e) {
			error = authMessage(e);
		} finally {
			busy = null;
		}
	}

	async function emailLink(e: SubmitEvent) {
		e.preventDefault();
		busy = 'email';
		error = '';
		try {
			await sendEmailLink(email, `/accedi?next=${encodeURIComponent(next)}`);
			sent = true;
		} catch (err) {
			error = authMessage(err);
		} finally {
			busy = null;
		}
	}
</script>

<section class="login card" aria-labelledby="login-title">
	<h2 id="login-title">{title}</h2>
	{#if intro}<p class="muted">{intro}</p>{/if}

	{#if sent}
		<div class="notice" role="status">
			<p><strong>Controlla la posta.</strong> Ti abbiamo mandato un link di accesso a <strong>{email}</strong>.</p>
			<p>Aprilo da questo dispositivo. Se non lo trovi, guarda nello spam.</p>
		</div>
		<button class="btn btn-ghost" onclick={() => (sent = false)}>Usa un’altra email</button>
	{:else}
		<button class="btn google" onclick={google} disabled={busy !== null}>
			<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"
				><path fill="currentColor" d="M12 10.2v3.9h5.4c-.2 1.3-1.6 3.8-5.4 3.8-3.2 0-5.9-2.7-5.9-6s2.7-6 5.9-6c1.9 0 3.1.8 3.8 1.5l2.6-2.5C16.7 3.4 14.6 2.4 12 2.4 6.7 2.4 2.4 6.7 2.4 12s4.3 9.6 9.6 9.6c5.5 0 9.2-3.9 9.2-9.4 0-.6-.1-1.1-.2-1.6H12z" /></svg
			>
			{busy === 'google' ? 'Apro Google…' : 'Continua con Google'}
		</button>

		<p class="or"><span>oppure</span></p>

		<form onsubmit={emailLink}>
			<div class="field">
				<label for="login-email">Ricevi un link via email</label>
				<input
					id="login-email"
					type="email"
					autocomplete="email"
					required
					bind:value={email}
					placeholder="nome@esempio.it"
					aria-describedby="login-hint"
				/>
				<span id="login-hint" class="hint">Niente password: ti mandiamo un link che vale una volta.</span>
			</div>
			<button class="btn btn-primary wide" disabled={busy !== null}>
				<Mail size={20} aria-hidden="true" />
				{busy === 'email' ? 'Invio…' : 'Mandami il link'}
			</button>
		</form>
	{/if}

	{#if error}<ErrorMessage>{error}</ErrorMessage>{/if}

	<p class="legal">
		Accedendo accetti i <a href="/termini">Termini</a> e confermi di aver letto l’<a href="/privacy">informativa privacy</a>.
		Serve avere almeno 14 anni.
	</p>
</section>

<style>
	.login {
		padding: var(--space-4);
		max-width: var(--w-dialog);
	}
	.google,
	.wide {
		width: 100%;
	}
	.or {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		margin: var(--space-3) 0;
		color: var(--muted);
		font-size: var(--text-sm);
	}
	.or::before,
	.or::after {
		content: '';
		flex: 1;
		height: 1px;
		background: var(--border);
	}
	.legal {
		margin: var(--space-4) 0 0;
		font-size: var(--text-sm);
		color: var(--muted);
	}
	.notice p {
		margin: 0 0 var(--space-2);
	}
</style>
