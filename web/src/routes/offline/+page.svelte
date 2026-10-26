<svelte:head>
	<title>Sei offline · Eventi Vicini</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<div class="container narrow off">
	<svg viewBox="0 0 64 64" width="80" height="80" aria-hidden="true">
		<circle cx="32" cy="32" r="28" fill="var(--brand-soft)" />
		<path d="M18 28a20 20 0 0 1 28 0M23 34a12 12 0 0 1 18 0M29 40a4 4 0 0 1 6 0" fill="none" stroke="var(--brand)" stroke-width="3.5" stroke-linecap="round" />
		<path d="M16 16l32 32" stroke="var(--brand)" stroke-width="3.5" stroke-linecap="round" />
	</svg>
	<h1>Sei offline</h1>
	<p class="muted">Questa pagina non è disponibile senza connessione. Le pagine che hai già aperto restano consultabili.</p>
	<button class="btn btn-primary" onclick={() => location.reload()}>Riprova</button>
</div>

<style>
	.off {
		display: grid;
		justify-items: center;
		text-align: center;
		gap: 0.5rem;
		padding: 4rem 16px;
	}
</style>
