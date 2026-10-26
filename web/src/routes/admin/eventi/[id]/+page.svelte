<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { loadEvent, saveEvent } from '$lib/admin';
	import EventForm from '$lib/components/EventForm.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import { eventPath, type Event, type EventInput } from '$lib/event';
	import { toast } from '$lib/toast.svelte';

	const id = page.params.id === 'nuovo' ? null : page.params.id!;
	let existing = $state<Event | null | undefined>(id ? undefined : null);
	if (id) loadEvent(id).then((e) => (existing = e));

	async function save(input: EventInput) {
		const savedId = await saveEvent(id, input);
		toast(id ? 'Evento aggiornato.' : 'Evento creato.', { label: 'Vedi', href: eventPath({ id: savedId, title: input.title }) });
		await goto('/admin');
	}
</script>

<a class="back" href="/admin"><Icon name="back" size={18} /> Tutti gli eventi</a>
<h1>{id ? 'Modifica evento' : 'Nuovo evento'}</h1>

{#if existing === undefined}
	<div class="skeleton" style="height: 400px" aria-hidden="true"></div>
{:else if id && existing === null}
	<p class="notice">Evento non trovato.</p>
{:else}
	{#if existing?.source === 'scraper'}
		<p class="notice">Evento importato: salvandolo diventa <strong>manuale</strong> e l’importer non lo sovrascriverà più.</p>
	{/if}
	<div class="narrow"><EventForm initial={existing ?? {}} submitLabel={id ? 'Salva le modifiche' : 'Crea evento'} onsubmit={save} /></div>
{/if}

<style>
	.back {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		min-height: 44px;
		color: var(--muted);
		font-weight: 600;
		text-decoration: none;
	}
	.notice {
		margin-bottom: 1rem;
		max-width: 760px;
	}
	.narrow {
		max-width: 760px;
	}
</style>
