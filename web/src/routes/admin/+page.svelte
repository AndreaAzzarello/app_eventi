<script lang="ts">
	import { PAGE_SIZE, deleteEvent, listEvents } from '$lib/admin';
	import Icon from '$lib/components/Icon.svelte';
	import { formatWhen } from '$lib/dates';
	import { CATEGORIES, eventPath, type Event } from '$lib/event';
	import { toast } from '$lib/toast.svelte';

	let events = $state<Event[] | null>(null);
	let more = $state(false);
	let error = $state('');
	let q = $state('');
	let toDelete = $state<Event | null>(null);
	let dialog: HTMLDialogElement;

	async function load(append = false) {
		error = '';
		try {
			const page = await listEvents(append ? events?.at(-1) : undefined);
			events = append ? [...(events ?? []), ...page] : page;
			more = page.length === PAGE_SIZE;
		} catch (e) {
			console.error(e);
			error = 'Non riesco a caricare gli eventi.';
		}
	}
	load();

	const norm = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
	const shown = $derived(
		(events ?? []).filter((e) => !q.trim() || norm(`${e.title} ${e.venueName} ${e.city}`).includes(norm(q.trim())))
	);
	const SOURCE = { manual: 'Manuale', scraper: 'Importato', user: 'Utente' };

	function ask(e: Event) {
		toDelete = e;
		dialog.showModal();
	}
	async function confirmDelete() {
		const e = toDelete!;
		try {
			await deleteEvent(e.id);
			events = events?.filter((x) => x.id !== e.id) ?? null;
			toast(`Eliminato “${e.title}”.`);
		} catch {
			toast('Eliminazione non riuscita.');
		}
		dialog.close();
	}
</script>

<div class="head">
	<h1>Eventi</h1>
	<a class="btn btn-primary" href="/admin/eventi/nuovo"><Icon name="plus" size={18} /> Nuovo evento</a>
</div>

<div class="field search">
	<label for="admin-q">Cerca tra gli eventi caricati</label>
	<input id="admin-q" type="search" bind:value={q} placeholder="Titolo, luogo o città" />
</div>

{#if error}
	<p class="notice notice-error" role="alert">{error} <button class="btn btn-sm" onclick={() => load()}>Riprova</button></p>
{:else if events === null}
	<div class="skeleton" style="height: 240px" aria-hidden="true"></div>
{:else}
	<p class="muted" role="status">{shown.length} eventi{q ? ' trovati' : ''}</p>
	<ul class="rows">
		{#each shown as e (e.id)}
			<li class="card row">
				<div class="info">
					<a href={eventPath(e)} class="title">{e.title}</a>
					<span class="muted">{formatWhen(e.startTime, e.endTime)} · {e.city || e.address}</span>
					<span class="tags">
						<span class="badge">{CATEGORIES[e.category]}</span>
						<span class="badge" class:badge-warn={e.source === 'user'}>{SOURCE[e.source]}</span>
						{#if !e.geohash}<span class="badge badge-danger">Senza geohash</span>{/if}
					</span>
				</div>
				<div class="actions">
					<a class="btn btn-sm" href="/admin/eventi/{e.id}" aria-label="Modifica {e.title}"><Icon name="edit" size={16} /> Modifica</a>
					<button class="btn btn-sm btn-danger" onclick={() => ask(e)} aria-label="Elimina {e.title}"><Icon name="trash" size={16} /></button>
				</div>
			</li>
		{/each}
	</ul>
	{#if more}<button class="btn more" onclick={() => load(true)}>Carica altri</button>{/if}
{/if}

<dialog bind:this={dialog} aria-labelledby="adm-del">
	<h2 id="adm-del">Eliminare l’evento?</h2>
	<p>“{toDelete?.title}” sparirà dall’agenda. Se è importato, il prossimo import potrebbe ricrearlo.</p>
	<div class="dlg-actions">
		<button class="btn" onclick={() => dialog.close()}>Annulla</button>
		<button class="btn btn-danger" onclick={confirmDelete}>Elimina</button>
	</div>
</dialog>

<style>
	.head {
		display: flex;
		justify-content: space-between;
		align-items: center;
		flex-wrap: wrap;
		gap: 1rem;
	}
	.search {
		max-width: 480px;
	}
	.rows {
		list-style: none;
		padding: 0;
		margin: 0;
		display: grid;
		gap: 0.5rem;
	}
	.row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 1rem;
		padding: 0.75rem 1rem;
	}
	.info {
		display: grid;
		gap: 0.2rem;
		min-width: 0;
	}
	.title {
		font-weight: 600;
		color: var(--text);
		overflow-wrap: anywhere;
	}
	.tags {
		display: flex;
		gap: 0.3rem;
		flex-wrap: wrap;
	}
	.actions {
		display: flex;
		gap: 0.35rem;
		flex: none;
	}
	.more {
		margin-top: 1rem;
	}
	.dlg-actions {
		display: flex;
		justify-content: flex-end;
		gap: 0.5rem;
	}
</style>
