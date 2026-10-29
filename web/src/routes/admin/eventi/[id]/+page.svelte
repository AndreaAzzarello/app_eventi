<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { loadEvent, saveEvent } from '$lib/admin';
	import EventForm from '$lib/components/EventForm.svelte';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import { LISTING_NOTE, eventPath, type Event, type EventInput } from '$lib/event';
	import { toast } from '$lib/toast.svelte';

	const id = page.params.id === 'nuovo' ? null : page.params.id!;
	let existing = $state<Event | null | undefined>(id ? undefined : null);
	if (id) loadEvent(id).then((e) => (existing = e));

	async function save(input: EventInput) {
		const savedId = await saveEvent(id, input);
		toast(`${id ? 'Evento aggiornato.' : 'Evento creato.'} ${LISTING_NOTE}`, { label: 'Vedi', href: eventPath({ id: savedId, title: input.title }) }, 12000);
		await goto('/admin');
	}
</script>

<a class="back" href="/admin"><ArrowLeft size={20} aria-hidden="true" /> Tutti gli eventi</a>
<h1>{id ? 'Modifica evento' : 'Nuovo evento'}</h1>

{#if existing === undefined}
	<div class="skeleton" style="height: calc(var(--space-7) * 6)" aria-hidden="true"></div>
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
		gap: var(--space-2);
		min-height: var(--control);
		color: var(--muted);
		font-weight: var(--fw-strong);
		text-decoration: none;
	}
	.notice {
		margin-bottom: var(--space-3);
		max-width: var(--w-prose);
	}
	.narrow {
		max-width: var(--w-prose);
	}
</style>
