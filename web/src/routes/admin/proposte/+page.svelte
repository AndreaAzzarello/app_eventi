<script lang="ts">
	import { approve, pendingSubmissions, reject } from '$lib/admin';
	import Icon from '$lib/components/Icon.svelte';
	import PinMap from '$lib/components/PinMap.svelte';
	import { formatWhen } from '$lib/dates';
	import { CATEGORIES, PRICE_TYPES, eventPath } from '$lib/event';
	import type { Submission } from '$lib/submissions';
	import { toast } from '$lib/toast.svelte';

	let subs = $state<Submission[] | null>(null);
	let error = $state('');
	let open = $state<string | null>(null);
	let rejecting = $state<Submission | null>(null);
	let reason = $state('');
	let busy = $state(false);
	let dialog: HTMLDialogElement;

	async function load() {
		error = '';
		try {
			subs = await pendingSubmissions();
		} catch (e) {
			console.error(e);
			error = 'Non riesco a caricare le proposte.';
		}
	}
	load();

	async function doApprove(s: Submission) {
		busy = true;
		try {
			const id = await approve(s);
			subs = subs?.filter((x) => x.id !== s.id) ?? null;
			toast(`Pubblicato “${s.title}”.`, { label: 'Vedi', href: eventPath({ id, title: s.title }) });
		} catch (e) {
			console.error(e);
			toast('Approvazione non riuscita.');
		} finally {
			busy = false;
		}
	}

	function askReject(s: Submission) {
		rejecting = s;
		reason = '';
		dialog.showModal();
	}

	async function doReject(e: SubmitEvent) {
		e.preventDefault();
		const s = rejecting!;
		busy = true;
		try {
			await reject(s, reason);
			subs = subs?.filter((x) => x.id !== s.id) ?? null;
			toast('Proposta rifiutata: l’autore vedrà il motivo.');
			dialog.close();
		} catch (err) {
			console.error(err);
			toast('Rifiuto non riuscito.');
		} finally {
			busy = false;
		}
	}
</script>

<h1>Proposte in attesa</h1>

{#if error}
	<p class="notice notice-error" role="alert">{error} <button class="btn btn-sm" onclick={load}>Riprova</button></p>
{:else if subs === null}
	<div class="skeleton" style="height: 200px" aria-hidden="true"></div>
{:else if subs.length === 0}
	<p class="notice">Nessuna proposta da revisionare. 🎉</p>
{:else}
	<ul class="list">
		{#each subs as s (s.id)}
			<li class="card item">
				<div class="top">
					<div>
						<span class="badge badge-brand">{CATEGORIES[s.category]}</span>
						<span class="badge">{PRICE_TYPES[s.priceType]}</span>
						<h2>{s.title}</h2>
						<p class="muted">{formatWhen(s.startTime, s.endTime)} · {s.venueName ? `${s.venueName}, ` : ''}{s.address} ({s.city}{s.province ? `, ${s.province}` : ''})</p>
					</div>
					<button class="btn btn-sm" aria-expanded={open === s.id} onclick={() => (open = open === s.id ? null : s.id)}>
						{open === s.id ? 'Chiudi anteprima' : 'Anteprima'}
					</button>
				</div>
				{#if open === s.id}
					<div class="preview">
						{#if s.imageUrl}<img src={s.imageUrl} alt="Immagine proposta per {s.title}" loading="lazy" referrerpolicy="no-referrer" />{/if}
						{#if s.shortDescription}<p class="desc">{s.shortDescription}</p>{/if}
						<dl>
							{#if s.ticketUrl}<dt>Link</dt><dd><a href={s.ticketUrl} target="_blank" rel="noopener noreferrer nofollow">{s.ticketUrl}</a></dd>{/if}
							{#if s.tags.length}<dt>Tag</dt><dd>{s.tags.join(', ')}</dd>{/if}
							<dt>Regione</dt><dd>{s.region || '—'}</dd>
						</dl>
						<PinMap lat={s.lat} lng={s.lng} label="Posizione proposta" />
					</div>
				{/if}
				<div class="actions">
					<button class="btn btn-danger" onclick={() => askReject(s)} disabled={busy}><Icon name="x" size={18} /> Rifiuta</button>
					<button class="btn btn-primary" onclick={() => doApprove(s)} disabled={busy}><Icon name="check" size={18} /> Approva</button>
				</div>
			</li>
		{/each}
	</ul>
{/if}

<dialog bind:this={dialog} aria-labelledby="rej-title">
	<form onsubmit={doReject}>
		<h2 id="rej-title">Rifiuta “{rejecting?.title}”</h2>
		<div class="field">
			<label for="rej-reason">Motivo (lo vedrà l’autore)</label>
			<textarea id="rej-reason" bind:value={reason} required minlength="3" maxlength="500" placeholder="Es. evento già presente, date non verificabili…"></textarea>
		</div>
		<div class="actions">
			<button type="button" class="btn" onclick={() => dialog.close()}>Annulla</button>
			<button class="btn btn-danger" disabled={busy || reason.trim().length < 3}>Rifiuta</button>
		</div>
	</form>
</dialog>

<style>
	.list {
		list-style: none;
		padding: 0;
		margin: 0;
		display: grid;
		gap: 1rem;
		max-width: 860px;
	}
	.item {
		padding: 1rem 1.25rem;
	}
	.top {
		display: flex;
		justify-content: space-between;
		align-items: start;
		gap: 1rem;
	}
	.top h2 {
		margin: 0.5rem 0 0.2rem;
		font-size: 1.2rem;
	}
	.preview {
		display: grid;
		gap: 0.75rem;
		margin: 1rem 0;
	}
	.preview img {
		max-height: 240px;
		object-fit: cover;
		border-radius: var(--radius-sm);
	}
	.desc {
		white-space: pre-line;
		overflow-wrap: anywhere;
	}
	dl {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 0.25rem 1rem;
		margin: 0;
	}
	dt {
		font-weight: 600;
	}
	dd {
		margin: 0;
		overflow-wrap: anywhere;
	}
	.actions {
		display: flex;
		justify-content: flex-end;
		gap: 0.5rem;
		margin-top: 0.75rem;
	}
</style>
